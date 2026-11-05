"""Download verified Tree 2 audit assets from the public GitHub release."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request
import uuid


ROOT = Path(__file__).resolve().parent
BLOCK = 1024 * 1024


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def matches(path, item):
    return path.is_file() and path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]


def destination(root, relative):
    pieces = relative.split("/")
    if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) and part not in (".", "..") for part in pieces):
        raise ValueError(f"Unsafe asset path: {relative}")
    target = root.joinpath(*pieces)
    if not target.resolve().is_relative_to(root):
        raise ValueError(f"Asset path leaves download directory: {relative}")
    return target


def fetch(root, url, item):
    path = destination(root, item["path"])
    if path.exists():
        if not matches(path, item):
            raise ValueError(f"Existing file differs from manifest: {path}")
        print(f"Verified existing {item['asset']}", flush=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.partial")
        try:
            request = urllib.request.Request(url + item["asset"], headers={"User-Agent": "tree2-audit-restore/1"})
            with urllib.request.urlopen(request, timeout=90) as response, temporary.open("xb") as stream:
                count = 0
                digest = hashlib.sha256()
                for data in iter(lambda: response.read(BLOCK), b""):
                    count += len(data)
                    if count > item["bytes"]:
                        raise ValueError(f"Unexpected extra bytes: {item['asset']}")
                    digest.update(data)
                    stream.write(data)
                if count != item["bytes"] or digest.hexdigest() != item["sha256"]:
                    raise ValueError(f"Downloaded SHA256 or size differs: {item['asset']}")
                stream.flush()
                os.fsync(stream.fileno())
            if path.exists():
                if not matches(path, item):
                    raise ValueError(f"A different file appeared during download: {path}")
            else:
                os.replace(temporary, path)
            print(f"Downloaded and verified {item['asset']}", flush=True)
            return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))
        finally:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("download_directory", type=Path)
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=4)
    args = parser.parse_args()
    mapping = json.loads((ROOT / "handoff/release-assets.json").read_bytes())
    package = ROOT / "handoff/package_index.json"
    if mapping["schema"] != "TREE2_PRIVATE_RELEASE_ASSET_INDEX_V001" or sha(package) != mapping["package_index_sha256"]:
        raise ValueError("Release asset index and package index do not match")
    repo, tag = mapping["repo"], mapping["tag"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not re.fullmatch(r"[A-Za-z0-9_.-]+", tag):
        raise ValueError("Unexpected repository or release tag")
    index = json.loads(package.read_bytes())
    refs = {item["path"]: (item["bytes"], item["sha256"]) for group in index["archives"] for item in (group["manifest"], *group["parts"])}
    omission = index["omissions"]
    refs[omission["path"]] = (omission["bytes"], omission["sha256"])
    assets = mapping["assets"]
    if len(assets) != len(refs) or len({item["asset"] for item in assets}) != len(assets):
        raise ValueError("Release asset count differs from the package index")
    for item in assets:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", item["asset"]) or refs.pop(item["path"], None) != (item["bytes"], item["sha256"]):
            raise ValueError("Release asset does not match the package index")
    root = args.download_directory.resolve()
    root.mkdir(parents=True, exist_ok=True)
    index_copy = root / "package_index.json"
    if index_copy.exists() and sha(index_copy) != mapping["package_index_sha256"]:
        raise ValueError("Destination already has a different package index")
    if not index_copy.exists():
        with index_copy.open("xb") as stream:
            stream.write(package.read_bytes())
    url = f"https://github.com/{repo}/releases/download/{tag}/"
    with ThreadPoolExecutor(max_workers=args.workers) as workers:
        for _ in workers.map(lambda item: fetch(root, url, item), assets):
            pass
    print(f"Verified download complete. Run python verify_and_restore.py {root}")


if __name__ == "__main__":
    main()
