"""Resolve an amino-acid alphabet ambiguity using the original Prodigal translations."""
from itertools import product
import hashlib
from pathlib import Path

from build_bundle import BUNDLE, PROJECT, atomic_json, utc


ACCESSIONS = ("GCF_003885105.1", "GCF_005405125.1")
ANNOTATIONS = PROJECT / "analysis/uniform_annotation_v001/units"
CHECKM = PROJECT / "analysis/checkm1_lactobacillales_full919_v001"
CODONS = dict(zip((bytes(row) for row in product(b"TCAG", repeat=3)),
                  b"FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def records(path):
    output = []
    name = None
    sequence = bytearray()
    with path.open("rb") as stream:
        for row in stream:
            row = row.strip()
            if row.startswith(b">"):
                if name is not None:
                    output.append((name, bytes(sequence)))
                name = row[1:].split(maxsplit=1)[0]
                sequence.clear()
            elif row:
                require(name is not None, f"Missing FASTA identifier: {path}")
                sequence.extend(row.upper())
    if name is not None:
        output.append((name, bytes(sequence)))
    require(output and all(sequence for _, sequence in output), f"Empty FASTA record: {path}")
    require(len({name for name, _ in output}) == len(output), f"Duplicate FASTA identifier: {path}")
    return output


def evidence(path, reason):
    with path.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": path.relative_to(PROJECT).as_posix(), "sha256": sha, "bytes": path.stat().st_size, "reason": reason}


def main():
    proteins = []
    checks = []
    for accession in ACCESSIONS:
        (directory,) = (ANNOTATIONS / accession).glob("prodigal_attempt_*")
        peptide = directory / "prodigal.faa"
        canonical = directory / "proteins.faa"
        coding = directory / "prodigal.ffn"
        originals = records(peptide)
        cds = records(coding)
        normalized = records(canonical)
        require(len(originals) == len(cds) == len(normalized), f"Different gene counts: {accession}")
        for (gene, aa), (gene_nt, nt), (_, aa_norm) in zip(originals, cds, normalized, strict=True):
            require(gene == gene_nt and len(nt) % 3 == 0, f"CDS record mismatch: {accession}")
            translated = bytes(CODONS.get(nt[i:i + 3], ord("X")) for i in range(0, len(nt), 3))
            require(aa == translated or (aa.startswith(b"M") and aa[1:] == translated[1:]),
                    f"CDS translation mismatch: {accession} {gene!r}")
            require(aa.removesuffix(b"*") == aa_norm, f"Canonical protein mismatch: {accession}")
        source = evidence(peptide, "all_Prodigal_peptides_match_translated_CDS_under_table11")
        proteins.extend((source, evidence(canonical, "canonical_peptides_match_validated_Prodigal_translation")))
        (checkm_input,) = CHECKM.glob(f"batch_*/inputs/{accession}.faa")
        (checkm_copy,) = CHECKM.glob(f"batch_*/checkm_output/bins/{accession}/genes.faa")
        for copy in (checkm_input, checkm_copy):
            row = evidence(copy, "byte_identical_copy_of_validated_Prodigal_protein_FASTA")
            require(row["sha256"] == source["sha256"], f"CheckM copy differs: {copy}")
            proteins.append(row)
        checks.append({"accession": accession, "validated_translations": len(originals),
                       "excluded_CDS_evidence": evidence(coding, "nucleotide_input_omitted_by_policy")})
    atomic_json(BUNDLE / "verified_protein_derivatives.json", {
        "status": "PASS", "at_utc": utc(), "checks": checks, "proteins": proteins,
    })


if __name__ == "__main__":
    main()
