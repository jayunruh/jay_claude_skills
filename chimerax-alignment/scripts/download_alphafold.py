"""
Download AlphaFold DB predictions for UniProt IDs found in a FASTA file.

Usage: pixi run python download_alphafold.py <fasta_file> [--outdir <dir>]
"""

import argparse
import re
import sys
from pathlib import Path

import requests


def parse_uniprot_ids(fasta_path: Path) -> list[str]:
    """Extract UniProt accessions from FASTA headers.

    Handles both Swiss-Prot (sp|ACC|) and TrEMBL (tr|ACC|) formats,
    as well as bare accession-only headers.
    """
    ids = []
    pattern = re.compile(r">(?:sp|tr)\|([A-Z0-9]+)\|")
    bare_pattern = re.compile(r">([A-Z][A-Z0-9]{5}(?:\d)?)")  # basic UniProt accession shape

    with open(fasta_path) as f:
        for line in f:
            if not line.startswith(">"):
                continue
            m = pattern.search(line)
            if m:
                ids.append(m.group(1))
            else:
                m = bare_pattern.match(line)
                if m:
                    ids.append(m.group(1))

    return ids


def download_alphafold(uniprot_id: str, outdir: Path, version: int = 6) -> Path | None:
    """Download AlphaFold predicted structure for a UniProt ID.

    Returns the path to the saved file, or None on failure.
    AlphaFold DB URL pattern:
      https://alphafold.ebi.ac.uk/files/AF-{ID}-F1-model_v{version}.pdb
    """
    url = f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v{version}.pdb"
    out_path = outdir / f"AF-{uniprot_id}-F1-model_v{version}.pdb"

    if out_path.exists():
        print(f"  [skip] {out_path.name} already exists")
        return out_path

    resp = requests.get(url, timeout=30)
    if resp.status_code == 200:
        out_path.write_bytes(resp.content)
        print(f"  [ok]   {out_path.name}")
        return out_path
    elif resp.status_code == 404:
        print(f"  [miss] {uniprot_id} — no AlphaFold entry (404)")
    else:
        print(f"  [err]  {uniprot_id} — HTTP {resp.status_code}")
    return None


def main():
    parser = argparse.ArgumentParser(description="Download AlphaFold structures for UniProt IDs in a FASTA file")
    parser.add_argument("fasta", type=Path, help="Input FASTA file")
    parser.add_argument("--outdir", type=Path, default=None, help="Output directory (default: alphafold_pdbs/ next to FASTA)")
    parser.add_argument("--version", type=int, default=6, help="AlphaFold model version (default: 6)")
    args = parser.parse_args()

    if not args.fasta.exists():
        sys.exit(f"Error: {args.fasta} not found")

    outdir = args.outdir or args.fasta.parent / "alphafold_pdbs"
    outdir.mkdir(parents=True, exist_ok=True)

    ids = parse_uniprot_ids(args.fasta)
    if not ids:
        sys.exit("No UniProt IDs found in FASTA headers")

    print(f"Found {len(ids)} UniProt ID(s): {', '.join(ids)}")
    print(f"Downloading to: {outdir}\n")

    downloaded = []
    for uid in ids:
        result = download_alphafold(uid, outdir, version=args.version)
        if result:
            downloaded.append(result)

    print(f"\nDone: {len(downloaded)}/{len(ids)} structures downloaded to {outdir}")


if __name__ == "__main__":
    main()
