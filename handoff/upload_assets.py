"""Upload committed Tree 2 bundle groups to the one authorized private release."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


PUBLISH = Path(__file__).resolve().parent
BUNDLE = PUBLISH.parent
TRANSFER = PUBLISH / "transfer_bundle"
REPO = "serg-alexv/broad-lab-phylogenomics-audit"
TAG = "tree2-audit-20261105"
FLAT = PUBLISH / "upload_staging"
SAFE_NAME = re.compile(r"[A-Za-z0-9_.-]+\Z")


def gh(*args):
    return subprocess.run(["gh", *args], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE).stdout


def write_json(path, data):
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def hash_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def index_files(groups, omissions=None):
    by_name = {}
    for group in groups:
        manifest = {**group["manifest"], "asset": f"manifest--{group['group']}.ndjson"}
        files = [manifest] + [{**part, "asset": Path(part["path"]).name} for part in group["parts"]]
        for item in files:
            name = item["asset"]
            if not SAFE_NAME.fullmatch(name) or name in by_name or not item["path"].startswith("payload/"):
                raise RuntimeError(f"Invalid or duplicate release member: {name}")
            by_name[name] = item
    if omissions:
        name = "inventory--omissions.ndjson"
        if not omissions["path"].startswith("inventory/"):
            raise RuntimeError("Omission ledger is outside the frozen inventory")
        by_name[name] = {**omissions, "asset": name}
    return by_name


def committed_groups():
    files = [path for path in (BUNDLE / "payload").glob("*/COMMITTED.json") if path.parent.name != "evidence"]
    clean = TRANSFER / "payload/evidence/COMMITTED.json"
    if clean.exists():
        files.append(clean)
    return [json.loads(path.read_text(encoding="utf-8")) for path in files]


def remote_assets(release_id):
    pages = json.loads(gh("api", "-X", "GET", f"repos/{REPO}/releases/{release_id}/assets",
                          "-F", "per_page=100", "--paginate", "--slurp"))
    return {item["name"]: item for page in pages for item in page}


def same(remote, item):
    return (remote["state"] == "uploaded" and remote["size"] == item["bytes"]
            and remote.get("digest") == "sha256:" + item["sha256"])


def upload(item):
    staged = TRANSFER / item["path"]
    source = (staged if staged.exists() else BUNDLE / item["path"]).resolve(strict=True)
    if not source.is_relative_to(BUNDLE) or source.stat().st_size != item["bytes"] or hash_file(source) != item["sha256"]:
        raise RuntimeError(f"Staged source failed its local digest: {item['path']}")
    link = FLAT / item["asset"]
    if not link.exists():
        os.link(source, link)
    if not link.samefile(source):
        raise RuntimeError(f"Unexpected release staging file: {link.name}")
    return subprocess.run(["gh", "release", "upload", TAG, "--repo", REPO, str(link)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")


def main():
    repo = json.loads(gh("repo", "view", REPO, "--json", "nameWithOwner,isPrivate"))
    if not repo["isPrivate"] or repo["nameWithOwner"] != REPO:
        raise RuntimeError("Release destination must be the authorized private repository")
    releases = json.loads(gh("api", f"repos/{REPO}/releases"))
    release, = [row for row in releases if row["tag_name"] == TAG and row["draft"]]
    release_id = release["id"]
    FLAT.mkdir(exist_ok=True)
    failures = {}
    remote = remote_assets(release_id)
    with ThreadPoolExecutor(max_workers=4) as pool:
        while True:
            verified = TRANSFER / "VERIFICATION.json"
            index_path = TRANSFER / "package_index.json"
            if index_path.exists():
                index = json.loads(index_path.read_text(encoding="utf-8"))
                desired = index_files(index["archives"], index["omissions"])
            else:
                desired = index_files(committed_groups())
            for name, row in remote.items():
                if name not in desired or not same(row, desired[name]):
                    raise RuntimeError(f"Unexpected asset or remote SHA mismatch: {name}")
            write_json(PUBLISH / "upload_progress.json", {
                "release_id": release_id, "remote_verified_assets": len(remote),
                "remote_verified_bytes": sum(row["size"] for row in remote.values()),
                "known_assets": len(desired), "bundle_index_complete": index_path.exists(),
            })
            pending = [item for name, item in desired.items() if name not in remote]
            if pending:
                batch = sorted(pending, key=lambda item: item["bytes"], reverse=True)[:4]
                results = list(pool.map(upload, batch))
                remote = remote_assets(release_id)
                for item, result in zip(batch, results, strict=True):
                    name = item["asset"]
                    if name in remote and same(remote[name], item):
                        print(f"GitHub verified {name} ({item['bytes']:,} bytes)", flush=True)
                        continue
                    failures[name] = failures.get(name, 0) + 1
                    if failures[name] >= 3:
                        raise RuntimeError(f"Upload failed repeatedly for {name}: {result.stderr.strip()[-600:]}")
                continue
            if verified.exists():
                receipt = json.loads(verified.read_text(encoding="utf-8"))
                if receipt["status"] != "PASS":
                    raise RuntimeError("Local bundle did not pass verification")
                if not index_path.exists():
                    raise RuntimeError("Verified package has no index")
                break
            time.sleep(15)

    write_json(PUBLISH / "release-assets.json", {
        "schema": "TREE2_PRIVATE_RELEASE_ASSET_INDEX_V001", "repo": REPO, "tag": TAG,
        "package_index_sha256": hash_file(index_path), "asset_count": len(desired),
        "assets": sorted(desired.values(), key=lambda item: item["path"]),
    })
    write_json(PUBLISH / "remote-asset-verification.json", {
        "status": "PASS", "release_id": release_id, "assets": len(remote),
        "bytes": sum(row["size"] for row in remote.values()),
        "sha256s_match_github_asset_metadata": True,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
