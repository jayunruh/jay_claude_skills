---
name: chimerax-alignment
description: "Run a full AlphaFold + ChimeraX structural alignment workflow: take a FASTA file of UniProt sequences, perform a multiple sequence alignment with Clustal Omega, download the predicted structures from the AlphaFold Database, and guide the user through loading and coloring the structures by conservation in ChimeraX. Use this skill whenever the user wants to align protein sequences and visualize their structural conservation, mentions AlphaFold structures with sequence alignment, wants to color protein structures by conservation in ChimeraX, or says things like \"align these sequences in ChimeraX\", \"download AlphaFold structures for my FASTA\", \"structural alignment colored by conservation\", or \"run clustalo and load in ChimeraX\"."
---

# AlphaFold + ChimeraX Structural Alignment Workflow

**Version:** 0.0.1

This skill performs a pairwise/multiple alignment of protein sequences from a FASTA file, downloads predicted structures from the AlphaFold Database, and guides the user through structural alignment and conservation coloring in ChimeraX.

**Dependencies:** pixi, clustalo (via pixi), ChimeraX (installed separately)

---

## Step 0: Project Setup

1. Create a project folder for the analysis.
2. Write the following `pixi.toml` into it:

```toml
[workspace]
channels = ["conda-forge", "bioconda"]
platforms = ["osx-arm64"]
version = "0.1.0"

[tasks]

[dependencies]
python = "3.12.*"
clustalo = ">=1.2.4,<2"
requests = ">=2.34.2,<3"
```

3. Run `pixi install` inside the project folder to set up the environment.
4. Copy or upload the user's FASTA file into the project folder.

**FASTA header format check:** Headers must follow UniProt format, e.g.:
```
>tr|P12345|GENENAME_ORGANISM Description
>sp|Q9Y6K9|GENENAME_ORGANISM Description
```
If headers don't match this pattern, ask the user to reformat them before proceeding — the download script relies on parsing these IDs.

---

## Step 1: Run Clustal Omega Alignment

Run the multiple sequence alignment:

```bash
pixi run clustalo -i <fastafile> --outfmt=clustal --output-order=input-order --resno -o <fastafile>.aln
```

Replace `<fastafile>` with the actual filename. The output `.aln` file will be used in ChimeraX.

---

## Step 2: Download AlphaFold Structures

Copy the bundled script `scripts/download_alphafold.py` into the project folder, then run:

```bash
pixi run python download_alphafold.py <fastafile>
```

Structures will be saved to `alphafold_pdbs/` in the project folder.

- The script defaults to AlphaFold model version 6. Pass `--version 4` if v6 is unavailable for an entry.
- If a UniProt ID returns 404, there is no AlphaFold prediction for it — the user will need to either skip that sequence or provide a structure manually.
- Pass `--outdir <path>` to save PDB files elsewhere.

---

## Step 3: Load and Align in ChimeraX

Guide the user through these steps in ChimeraX:

1. **Open all downloaded PDB files:** File → Open, select all `.pdb` files in `alphafold_pdbs/`.
2. **Load the alignment:** File → Open, select the `.aln` file produced in Step 1. ChimeraX will associate the alignment with the open structures.
3. **Run Matchmaker** to superimpose the structures. In the ChimeraX command line:
   ```
   matchmaker #1 to #2
   ```
   (Adjust model numbers as needed; use `#1,2,3` etc. for more models.)
4. **Color by conservation** using the sequence alignment:
   ```
   color byattr seq_conservation protein palette cyanmaroon range -1.4,1.4
   ```
   This colors each residue from cyan (variable) to maroon (conserved) based on the alignment.

---

## Troubleshooting

- **clustalo not found:** Make sure `pixi install` completed successfully and you're running commands with `pixi run`.
- **AlphaFold 404 errors:** Not all UniProt entries have AlphaFold predictions. The script will report which ones are missing.
- **Alignment not loading in ChimeraX:** Confirm the `.aln` file is in Clustal format and that the sequence names in the alignment match the chain identifiers in the PDB files.
- **Color command fails:** The `color byattrseq_conservation` command requires the alignment to be loaded and associated with open models. Ensure the `.aln` file was opened after the PDB files.

---

## Changelog

### 0.0.1
- Initial development
