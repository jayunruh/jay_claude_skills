---
name: esmfold2-protein
description: >
  Predict 3D protein structures (single chains or multi-chain complexes) using the ESMFold2
  API from Biohub. Guides the user through setting up the pixi environment, collecting protein
  sequences and copy numbers, running the folding job, and producing an interactive HTML viewer
  with the predicted structure, PAE matrix, pLDDT plot, and confidence scores (pTM/ipTM).
  Use this skill any time the user wants to predict a protein structure or complex with ESMFold2,
  mentions protein folding, wants to run esmfold, asks about pLDDT/PAE/pTM/ipTM scores, or
  says things like "fold this sequence", "predict the structure of", "ESMFold", or "Biohub API".
---

# ESMFold2 Protein Structure Prediction

This skill walks through predicting protein structures (single chains or heteromeric/homomeric
complexes) via the ESMFold2 REST API, then visualising the result with an interactive HTML viewer.

---

## Step 0 — Set up the project environment

Create a project directory to hold scripts, inputs, and outputs:

```
esmfold2_project/
├── pixi.toml
├── run_esmfold2_protein_prediction.py
├── inputs/
└── esmfold2_predictions/
```

Initialize pixi with Python 3.13 and the ESM SDK from GitHub. The `pixi.toml` must include:

```toml
[project]
name = "esmfold2_project"
channels = ["conda-forge"]
platforms = ["osx-arm64", "linux-64"]

[dependencies]
python = "3.12.*"

[pypi-dependencies]
esm = { git = "https://github.com/Biohub/esm.git", rev = "main" }
```

Run `pixi install` to create the environment.

**API key**: Ask the user to confirm they have a Biohub API key saved in a plain text file
containing only the key (e.g. `~/.biohub_api_key.txt`). They can create one at
https://biohub.ai/developer-console/api-keys. Do not store the key anywhere in the project.

---

## Step 1 — Gather sequences and job information

Ask the user for:

1. **Each protein sequence** and **how many copies** (copy number) of that chain are in the complex.
   - Example: "Chain alpha: MKTLLLTLVVVTIVCLDLGYTK — 2 copies, Chain beta: GAAVGGLGGYMLGSAMSRPI — 1 copy"
2. **Output prefix** — a short name for this prediction (spaces and unsupported characters replaced with `_`).
3. **API key file path**.

### Build the input JSON

Assign chain IDs as consecutive capital letters starting at `A`. For homomeric copies, list all
letters for that chain as an array. IDs must be globally unique.

**Examples:**

| Sequences | Copy numbers | JSON ids |
|-----------|--------------|----------|
| Chain 1 only | 1 | `"id": "A"` |
| Chain 1, Chain 2 | 1 each | `"id": "A"`, `"id": "B"` |
| Chain 1 (×2), Chain 2 | 2, 1 | `"id": ["A","B"]`, `"id": "C"` |
| Chain 1 (×3) | 3 | `"id": ["A","B","C"]` |

Save to `inputs/{output_prefix}_sequences.json`:

```json
[
  {"id": "A", "sequence": "MKTLL..."},
  {"id": ["B", "C"], "sequence": "GAAVG..."}
]
```

---

## Step 2 — Write and run the prediction script

Save the following script as `run_esmfold2_protein_prediction.py` in the project root:

```python
import json
from esm.sdk import esmfold2_client
from esm.sdk.api import FoldingConfig
from esm.utils.structure import input_builder
from esm.utils.structure.input_builder import ProteinInput, StructurePredictionInput
import argparse
import os
import sys

parser = argparse.ArgumentParser(description='Run ESMFold2 protein prediction via the ESM SDK')
parser.add_argument('input_json', type=str, help='Path to input JSON file with protein sequences')
parser.add_argument('--key_file', type=str, required=True, help='Path to ESM API key file')
parser.add_argument('--outdir', type=str, default='esmfold2_predictions', help='Path to output folder')
parser.add_argument('--prediction_name', type=str, default='structure', help='Name of the predicted structure')
args = parser.parse_args()

with open(args.key_file) as f:
    token = f.read().strip()

print('establishing api connection')
client = esmfold2_client(model="esmfold2-fast-2026-05", url="https://biohub.ai", token=token)
if not client:
    print('connection failed')
    sys.exit(1)

config = FoldingConfig(num_loops=3, num_sampling_steps=32, include_pae=True)

print('reading sequences')
with open(args.input_json, 'r') as f:
    jdict = json.load(f)

protein_inputs = [input_builder.ProteinInput(id=entry['id'], sequence=entry['sequence']) for entry in jdict]
complex_inputs = input_builder.StructurePredictionInput(sequences=protein_inputs)
print('submitting folding job')
fold_result = client.fold_all_atom(complex_inputs, config=config)

os.makedirs(args.outdir, exist_ok=True)
pae = fold_result.pae.cpu().numpy()
plddt = fold_result.plddt.cpu().numpy()
score = {
    'ptm': fold_result.ptm,
    'iptm': fold_result.iptm,
    'plddt': plddt.tolist(),
    'pae': pae.tolist()
}
print('writing output to', args.outdir)
with open(os.path.join(args.outdir, f'{args.prediction_name}_confidence.json'), 'w') as f:
    json.dump(score, f)
with open(os.path.join(args.outdir, f'{args.prediction_name}_model.cif'), 'w') as f:
    f.write(fold_result.complex.to_mmcif())
print('done')
```

Run with pixi:

```bash
pixi run python run_esmfold2_protein_prediction.py inputs/{output_prefix}_sequences.json \
  --key_file {api_key_file} \
  --outdir esmfold2_predictions \
  --prediction_name {output_prefix}
```

Outputs written to:
- `esmfold2_predictions/{output_prefix}_model.cif` — predicted 3D structure
- `esmfold2_predictions/{output_prefix}_confidence.json` — pLDDT, PAE matrix, pTM, ipTM

---

## Step 3 — Generate the HTML viewer

After the prediction completes, generate a self-contained HTML file at
`esmfold2_predictions/{output_prefix}_viewer.html` that contains:

1. **3D structure viewer** using [3Dmol.js](https://3dmol.csb.pitt.edu/) — load the CIF, colour
   by pLDDT (blue = high confidence, red = low), add a spin toggle and style selector.
2. **pLDDT line plot** — residue index on x-axis, pLDDT score (0–100) on y-axis, colour-coded
   background bands (very high ≥90, high 70–90, low 50–70, very low <50).
3. **PAE heatmap** — symmetric matrix, colour scale from 0 (dark blue, low error) to 31.75 Å
   (yellow/white, high error). Label axes with residue indices.
4. **Confidence score summary** — display pTM and ipTM (or just pTM for monomers) prominently
   as badges at the top of the page.

The viewer must be fully self-contained (embed the confidence JSON inline as a JS variable so it
works when opened from the filesystem without a server). Use a CDN link for 3Dmol.js
(`https://3dmol.csb.pitt.edu/build/3Dmol-min.js`) and load the CIF from a relative path.

Write a small Python helper script `scripts/generate_viewer.py` that reads the CIF and confidence
JSON and writes the HTML. Run it with pixi:

```bash
pixi run python scripts/generate_viewer.py \
  --cif esmfold2_predictions/{output_prefix}_model.cif \
  --confidence esmfold2_predictions/{output_prefix}_confidence.json \
  --output esmfold2_predictions/{output_prefix}_viewer.html
```

Tell the user where the file is and suggest opening it in a browser.

---

## Notes

- **Monomer vs complex**: ipTM is only meaningful for complexes (>1 chain). For monomers, omit
  ipTM from the summary display and note it is not applicable.
- **Long sequences**: ESMFold2-fast has a sequence length limit. Warn the user if total residue
  count across all chains exceeds ~2000 residues.
- **pLDDT scale**: The API returns pLDDT on a 0–1 scale. The `generate_viewer.py` script auto-detects this and rescales to 0–100 for display. The prediction script stores the raw 0–1 values in the confidence JSON.
- **Platform note**: On macOS, use `osx-arm64` only (Apple Silicon). PyTorch has no wheels for `osx-64` (Intel) with Python 3.12+. On Intel Mac, use a Linux VM or remote compute instead.
- **Errors**: If the API call fails, print the error message and check: (1) API key is correct,
  (2) network access to biohub.ai, (3) the model string matches a currently available model.
