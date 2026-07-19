---
name: gromacs-simulation
description: >
  Run a full GROMACS molecular dynamics (MD) simulation workflow starting from a PDB structure file.
  Guides the user through every stage: pixi environment setup, structure preparation, solvation,
  energy minimization, NVT and NPT equilibration, 1 ns production MD, and post-simulation analysis
  (PBC correction, RMSD calculation) using MDAnalysis with Jay_pdbtools and Jay_mdtools.
  Use this skill whenever the user wants to run a GROMACS simulation, set up an MD simulation,
  solvate and minimize a protein, run molecular dynamics, equilibrate a protein structure,
  or analyze an MD trajectory — even if they don't say "GROMACS" explicitly.
  Also use this skill when the user asks about preparing a protein for simulation, adding water
  and ions to a structure, or running NVT/NPT equilibration.
---

# GROMACS Simulation Workflow

This skill walks through a complete MD simulation pipeline using GROMACS inside a pixi environment.
All GROMACS commands use `pixi run gmx` (never bare `gmx`).

---

## Step 0: Environment Setup

1. Create a project folder and initialize pixi with Python 3.12:
   ```bash
   mkdir <project_name> && cd <project_name>
   pixi init --channel conda-forge . 
   # Edit pixi.toml to pin python = "3.12.*" if needed
   ```

2. Add required packages:
   ```bash
   pixi add gromacs mdanalysis
   ```
   Then add the Jay lab analysis tools as PyPI dependencies by appending to `pixi.toml`:
   ```toml
   [pypi-dependencies]
   Jay_pdbtools = { git = "https://github.com/jayunruh/Jay_pdbtools" }
   Jay_mdtools = { git = "https://github.com/jayunruh/Jay_mdtools" }
   ```
   Then run `pixi install` to install everything.

3. Ask the user for their input PDB file. Suggest the AlphaFold Database (https://alphafold.ebi.ac.uk/) if they don't have one. Copy the PDB into the project folder.

4. Create `mdp_files/` and download the standard MDP parameter files:
   ```bash
   mkdir mdp_files
   curl -o mdp_files/ions.mdp   http://www.mdtutorials.com/gmx/lysozyme/Files/ions.mdp
   curl -o mdp_files/minim.mdp  http://www.mdtutorials.com/gmx/lysozyme/Files/minim.mdp
   curl -o mdp_files/nvt.mdp    http://www.mdtutorials.com/gmx/lysozyme/Files/nvt.mdp
   curl -o mdp_files/npt.mdp    http://www.mdtutorials.com/gmx/lysozyme/Files/npt.mdp
   curl -o mdp_files/md.mdp     http://www.mdtutorials.com/gmx/lysozyme/Files/md.mdp
   ```

5. Edit `mdp_files/md.mdp` and change `nsteps` to `500000` (this gives a 1 ns simulation; the default 5000000 would be 10 ns).

6. Edit `mdp_files/npt.mdp` and change `nsteps` to `50000` (this gives a 100 ps NPT equilibration; the default 250000 would be 500 ps).

---

## Step 1: Solvate and Minimize

### 1a. Initialize the molecule
```bash
pixi run gmx pdb2gmx -f <input.pdb> -o processed.gro -water tip3p -ignh
```
- When prompted, select the **CHARMM27** force field (usually option 1).
- If this fails due to PDB errors, inspect the error messages:
  - For C/N terminus issues, add `-ter` and select `NH3+` and `COO-` when prompted.
  - Other errors may require manually editing the PDB file.

### 1b. Define the simulation box
```bash
pixi run gmx editconf -f processed.gro -o newbox.gro -c -d 1.2 -bt cubic
```
Places the protein in a cubic box with a 1.2 nm minimum distance to the box edge.

### 1c. Add solvent
```bash
pixi run gmx solvate -cp newbox.gro -cs spc216.gro -o solv.gro -p topol.top
```

### 1d. Add ions to neutralize the system
```bash
pixi run gmx grompp -f mdp_files/ions.mdp -c solv.gro -p topol.top -o ions.tpr
pixi run gmx genion -s ions.tpr -o solv_ions.gro -p topol.top -pname NA -nname CL -neutral
```
When prompted for the group to replace, select **SOL** (the solvent group).

### 1e. Energy minimization
```bash
pixi run gmx grompp -f mdp_files/minim.mdp -c solv_ions.gro -p topol.top -o em.tpr
pixi run gmx mdrun -v -deffnm em
```
Show the user the output. The potential energy should be **negative and less than -10,000 kJ/mol** — this confirms a well-minimized structure.

---

## Step 2: Equilibration

> These steps are computationally intensive. Remind the user to keep their laptop plugged in.

**GPU acceleration** (if available): Insert these flags after `gmx mdrun`:
```
-nb gpu -pme gpu -bonded gpu -update gpu -ntmpi 1 -ntomp <ncpus> -pin on -pinstride 1
```
Replace `<ncpus>` with the number of CPU threads available.

### 2a. NVT equilibration (constant volume, 300 K)
```bash
pixi run gmx grompp -f mdp_files/nvt.mdp -c em.gro -r em.gro -p topol.top -o nvt.tpr -maxwarn 2
pixi run gmx mdrun -deffnm nvt
```

Run mdrun in the background and monitor progress every 30 seconds using the Monitor tool with this script:
```bash
LOG=nvt.log
while true; do
  if [ ! -f "$LOG" ]; then echo "[waiting for nvt.log...]"; sleep 10; continue; fi
  if grep -q "Finished mdrun" "$LOG" 2>/dev/null; then echo "NVT COMPLETE."; exit 0; fi
  if grep -qiE "Fatal error|Error:" "$LOG" 2>/dev/null; then grep -iE "Fatal error|Error:" "$LOG" | tail -2 | while read l; do echo "ERROR: $l"; done; exit 1; fi
  STEP=$(grep -A1 "Step.*Time" "$LOG" | grep -v "Step" | grep -v "^--$" | awk '{print $1}' | tail -1)
  TIME=$(grep -A1 "Step.*Time" "$LOG" | grep -v "Step" | grep -v "^--$" | awk '{print $2}' | tail -1)
  [ -n "$STEP" ] && echo "[NVT] step $STEP / ${TIME} ps" || echo "[NVT] Running — no step data yet..."
  sleep 30
done
```

After completion, confirm temperature is stable around **300 K**:
```bash
printf "Temperature\n0\n" | pixi run gmx energy -f nvt.edr -o nvt_temp.xvg
```
Look for `Average` near 300 K in the output.

### 2b. NPT equilibration (constant pressure)
```bash
pixi run gmx grompp -f mdp_files/npt.mdp -c nvt.gro -r nvt.gro -t nvt.cpt -p topol.top -o npt.tpr -maxwarn 2
pixi run gmx mdrun -deffnm npt
```

Monitor progress the same way (substituting `npt.log` for `nvt.log` in the script above).

After completion, confirm pressure fluctuates around **0 bar**:
```bash
printf "Pressure\n0\n" | pixi run gmx energy -f npt.edr -o npt_pressure.xvg
```
Look for `Average` near 0 bar — large fluctuations (±100 bar) are normal; the mean should be close to 0.

---

## Step 3: Production MD (1 ns)

> Also computationally intensive — remind the user to keep their laptop plugged in.

```bash
pixi run gmx grompp -f mdp_files/md.mdp -c npt.gro -t npt.cpt -p topol.top -o md_0_1.tpr -maxwarn 2
pixi run gmx mdrun -deffnm md_0_1
```

Run mdrun in the background and monitor with the Monitor tool (replace `TOTAL` with the actual nsteps from `md.mdp`):
```bash
LOG=md_0_1.log
TOTAL=500000
while true; do
  if [ ! -f "$LOG" ]; then echo "[waiting for md_0_1.log...]"; sleep 10; continue; fi
  if grep -q "Finished mdrun" "$LOG" 2>/dev/null; then echo "PRODUCTION MD COMPLETE."; exit 0; fi
  if grep -qiE "Fatal error|Error:" "$LOG" 2>/dev/null; then grep -iE "Fatal error|Error:" "$LOG" | tail -2 | while read l; do echo "ERROR: $l"; done; exit 1; fi
  STEP=$(grep -A1 "Step.*Time" "$LOG" | grep -v "Step" | grep -v "^--$" | awk '{print $1}' | tail -1)
  TIME=$(grep -A1 "Step.*Time" "$LOG" | grep -v "Step" | grep -v "^--$" | awk '{print $2}' | tail -1)
  PCT=$(awk "BEGIN {if ($STEP>0) printf \"%.1f\", $STEP/$TOTAL*100; else print \"0.0\"}" 2>/dev/null)
  [ -n "$STEP" ] && echo "[MD] step $STEP / ${TIME} ps — ${PCT}%" || echo "[MD] Running — no step data yet..."
  sleep 30
done
```

After completion, check `md_0_1.log` to verify potential energy is stable throughout.

### Option: Submit to a SLURM cluster for longer simulations

For multi-ns simulations, submit via `sbatch` rather than running locally. First run `grompp` locally to generate `md_0_1.tpr`, then create a job script. Ask the user for their cluster's partition name, time limit, and whether a GPU node is available.

**CPU-only template** (`run_md.sh`):
```bash
#!/bin/bash
#SBATCH --job-name=gromacs_md
#SBATCH --output=md_slurm_%j.log
#SBATCH --partition=<partition>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=<ncpus>
#SBATCH --time=<HH:MM:SS>

cd <project_dir>
pixi run gmx mdrun -deffnm md_0_1 -ntomp $SLURM_CPUS_PER_TASK
```

**GPU template** (`run_md_gpu.sh`):
```bash
#!/bin/bash
#SBATCH --job-name=gromacs_md_gpu
#SBATCH --output=md_slurm_%j.log
#SBATCH --partition=<gpu_partition>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=<ncpus>
#SBATCH --gres=gpu:1
#SBATCH --time=<HH:MM:SS>

cd <project_dir>
pixi run gmx mdrun -deffnm md_0_1 \
  -nb gpu -pme gpu -bonded gpu -update gpu \
  -ntmpi 1 -ntomp $SLURM_CPUS_PER_TASK -pin on -pinstride 1
```

Submit with:
```bash
sbatch run_md.sh
```

Monitor job status with `squeue -u $USER`. To restart from a checkpoint if the job times out:
```bash
pixi run gmx mdrun -deffnm md_0_1 -cpi md_0_1.cpt
```

**Output files:**
| File | Description |
|---|---|
| `md_0_1.log` | Simulation log |
| `md_0_1.gro` | Final structure |
| `md_0_1.xtc` | Trajectory |
| `md_0_1.edr` | Energy metrics |
| `md_0_1.cpt` | Checkpoint (for restarting) |

---

## Step 4: Analysis

### 4a. Periodic boundary correction (PBC)
```bash
pixi run gmx trjconv -s md_0_1.tpr -f md_0_1.xtc -o md_0_1_noPBC.xtc -pbc mol -center
```
- Select **Protein** for centering.
- Select **System** for output.
- For large trajectories, add `-skip <N>` to downsample frames.
- For multi-protein systems, use `-pbc nojump` instead to keep chains together.

### 4b. Visualization
Load `md_0_1.gro` + `md_0_1.xtc` in ChimeraX or VMD. Remove water first to speed up rendering.

### 4c. Python analysis: RMSD from first frame

Create and run `analyze_rmsd.py` (Jay lab tools are already installed via `pixi.toml`):
```python
import MDAnalysis as mda
import md_analysis_utils as mdu
import jpdbtools2 as jpt
import pandas as pd

grofile = "md_0_1.gro"
xtcfile = "md_0_1.xtc"

u = mda.Universe(grofile, xtcfile)
selu = u.select_atoms('protein')

pdbdfs, times = mdu.traj2pdbdfs(selu)
refca = jpt.getCA(pdbdfs[0])

aligndfs = []
rmsds = []
for i in range(len(pdbdfs)):
    qca = jpt.getCA(pdbdfs[i])
    _, _, trans, rmsd, com1, com2 = jpt.alignRMSD(refca, qca, angstroms=True)
    rmsds.append(rmsd)
    aligndf = jpt.transformpdbdf(pdbdfs[i], com2, trans, com1)
    aligndfs.append(aligndf)

pd.DataFrame({'time (ps)': times, 'rmsd (ang)': rmsds}).to_csv('aligned_rmsd.csv')

alignu = mdu.pdbdfs2traj(aligndfs)
mdu.writeTraj(alignu, 'aligned.pdb', 'aligned.xtc')
```

Run it with:
```bash
pixi run python analyze_rmsd.py
```

This produces:
- `aligned_rmsd.csv` — RMSD over time (angstroms vs. picoseconds)
- `aligned.pdb` + `aligned.xtc` — trajectory aligned to the first frame, water/ions removed

---

## Troubleshooting Tips

- **pdb2gmx fails**: Check for non-standard residues, missing atoms, or chain-break artifacts. The `-ignh` flag ignores existing hydrogens (recommended for AlphaFold structures). Use `-ter` for terminus issues.
- **Minimization doesn't converge**: Try increasing `nsteps` in `minim.mdp` or check for structural clashes in the input PDB.
- **High pressure in NPT**: Normal — pressure takes longer to equilibrate than temperature. Run longer NPT if needed.
- **Slow mdrun**: Confirm GPU flags are set if a GPU is present; check `ntomp` matches actual CPU count.
