---
name: mdff-flexible-fitting
description: Run a full MDFF (molecular dynamics flexible fitting) pipeline docking a protein into a cryo-EM map, starting from a ChimeraX session with the structure overlaid on the map. Covers exporting structure/map from ChimeraX, building a CHARMM PSF with VMD autopsf, generating the MDFF grid potential/gridpdb and secondary-structure/cispeptide/chirality restraints, staged NAMD3 docking + refinement (with a block-extension pattern for convergence), and post-run fit checks (RMSD + cross-correlation) via VMD mdff. Includes a pixi.toml for portable, VMD.app-free VMD via conda-forge vmd-python. Use whenever the user wants to flexibly fit a model into a cryo-EM map, mentions MDFF, wants to dock/refine a structure against a density map with NAMD, or has a ChimeraX session overlaying structure on a map -- even without saying "MDFF" explicitly (e.g. "I have this structure overlaid on a cryo-EM map, can we flexibly fit it"). Automates the official MDFF tutorial's interactive VMD steps.
---

# MDFF flexible fitting

This skill takes a ChimeraX session (protein structure overlaid on a cryo-EM map) through the full MDFF pipeline: structure/map export, CHARMM structure prep, MDFF grid generation, restraint generation, staged NAMD3 docking + refinement, and fit-quality assessment. It was developed and validated end-to-end on a real dataset (a homotrimer docked into a ~12 A map) and encodes the gotchas that actually broke that run — most importantly, several VMD packages and one environment variable are NOT auto-loaded/set the way they are in interactive GUI use, and the MDFF grid potential file must not be confused with the original density map when checking fit quality.

**Reusable pipeline scripts and assets** are bundled with this skill at `<skill_dir>/scripts/*` and `<skill_dir>/assets/*`. Copy them into the project directory and edit the placeholder tokens (`PROTEIN`, `MAP`, `SESSION_FILE`, model numbers, `mapresolution`, stage names) to match this specific project — don't run them from the skill directory. If a project already has its own copies (from a previous run of this skill), prefer what's there over silently overwriting it — it may have been fixed or adapted for that project.

## Step 0 — Environment

Copy the bundled assets and scripts into the project directory:
```
cp <skill_dir>/assets/00_env.sh <skill_dir>/assets/mdff_template.namd <skill_dir>/assets/par_all36_prot.prm <skill_dir>/assets/pixi.toml <skill_dir>/assets/run_vmd_tcl.py <project_dir>/
cp <skill_dir>/scripts/*.tcl <skill_dir>/scripts/*.cxc <skill_dir>/scripts/*.sh <skill_dir>/scripts/mdff_stage_template.namd <project_dir>/
```

`00_env.sh` hardcodes this machine's tool locations (VMD, ChimeraX, NAMD) and helper functions (`run_vmd`, `run_vmd_pixi`, `run_chimerax`, `run_namd`) used by every step below. Verify the paths inside it still resolve (`ls` each binary) before relying on it — if the user has since moved/updated an install, ask for the new path rather than guessing.

**Two ways to run VMD** — pick based on what's actually needed:
- `run_vmd` (default, matches how this skill was validated): calls the standalone VMD.app install directly. Requires VMD.app to be installed on this machine.
- `run_vmd_pixi`: runs the same `*.tcl` scripts through a `pixi install`-managed `vmd-python` (conda-forge), no VMD.app install needed at all -- this is what makes the pipeline portable to a machine that only has `pixi`. Confirmed to produce identical output (same restraint/psf/grid file line counts and content) to the standalone path once its two gotchas are handled, both already wired into the bundled `pixi.toml`:
  - **tk build pin (macOS arm64)**: a newer conda-forge `tk` build breaks vmd-python's bundled psfgen/autopsf at dlopen time (`Symbol not found: _strstr`). `pixi.toml` pins the known-working build; if that build ever disappears from conda-forge, re-pin to whatever currently works (verify with a script that calls `autopsf`). Not confirmed whether linux-64/osx-64 need an equivalent pin -- this is a macOS-dylib-specific failure mode, so they may just work unpinned, but that's untested; check before assuming.
  - **STRIDE binary for ssrestraints**: conda-forge's vmd-python doesn't bundle the external STRIDE binary that `ssrestraints` (Step 5) needs for secondary-structure assignment, and the failure is silent -- it writes an *empty* extrabonds file with no error, not a crash. `pixi.toml`'s `[activation.env]` sets `STRIDE_BIN` to this machine's existing VMD.app-bundled copy as a default; on a machine without VMD.app, get STRIDE directly (free for academic/non-commercial use) from https://webclu.bio.wzw.tum.de/stride/ and point `STRIDE_BIN` at that instead. **Always check the output extrabonds file's line count after running Step 5 through `run_vmd_pixi`** -- don't infer success from a clean exit code alone.

**NAMD cannot go in `pixi.toml`.** It's not on conda-forge or bioconda (checked: no package by that name on either), because NAMD's license restricts redistribution -- it requires registering and downloading directly from the NAMD site. `run_namd`'s path in `00_env.sh` must stay a manually-supplied local binary; there's no way to make that step fetch-and-install-portable the way VMD now is. ChimeraX (`run_chimerax`) is in the same boat (also license-gated, not on public conda channels) and wasn't investigated further since it wasn't asked about.

**GOTCHA — VMD wrapper script**: the installed VMD's `bin/vmd` wrapper script hardcodes a build-machine path as its default `VMDDIR` (e.g. `/Users/<builder>/software/vmd2/lib`), which doesn't exist on this machine. If `VMDDIR`/`MASTERVMDDIR` aren't exported before calling it, the wrapper silently tries to exec a nonexistent binary and fails. `00_env.sh` sets these; always `source` it (or otherwise export those two vars) before invoking vmd directly.

**GOTCHA — VMD package auto-loading**: in interactive GUI use, opening the Extensions menu auto-loads plugins like `autopsf`, `mdff`, `ssrestraints`, `cispeptide`, and `chirality`. In headless/batch `-e script.tcl` mode, none of those commands exist until you explicitly `package require` them first — every bundled script already does this, but if you write a new one, remember it (`invalid command name autopsf` / `invalid command name ssrestraints` / `mdffi` usage dump instead of running are the tells).

Confirm `namd3` is executable and note its path; confirm ChimeraX's actual app bundle name/version under `/Applications/` (it can differ from what's in `00_env.sh` if reinstalled) — `find /Applications -maxdepth 1 -iname "ChimeraX*"`.

## Step 1 — Gather inputs

Ask (don't guess), or inspect via the chimerax MCP tools if a live/loadable session is available:
- the ChimeraX session file (`.cxs`)
- which model number in that session is the atomic structure and which is the volume/map (`list_models` after opening it — don't assume #1 is the map and #2 is the structure; confirm for this session). Also check whether the atomic model or the map model was the one moved during fitting (this decides which one needs `relModel` in the export step — see 01_export_from_session.cxc's comment).
- **the map's actual resolution in Angstroms** (e.g. from the cryoSPARC/RELION job's FSC-based "Estimated Resolution"). This is required later for the CCC calculation and cannot be derived from the map file itself — a real mixup on this project: someone read off the voxel/pixel spacing (1.555 A) instead and typed that in, which is wrong by definition (true resolution must be at least ~2x pixel spacing by Nyquist). If the user gives a number suspiciously close to the map's voxel size, flag it and ask them to double check against the actual job output rather than accepting it.
- basenames to use for the protein and the map outputs (short, descriptive; avoid spaces)

## Step 2 — Export structure + map from the ChimeraX session

Edit `01_export_from_session.cxc` (session filename, model numbers, output filenames), then:
```
run_chimerax 01_export_from_session.cxc
```
Produces `PROTEIN.pdb` and `MAP.mrc`.

## Step 3 — Build the CHARMM structure

Edit `02_make_psf.tcl` (basename), then:
```
run_vmd 02_make_psf.tcl
```
Produces `PROTEIN_autopsf.psf`/`.pdb`. Read the log for anything beyond the expected "guessing coordinates for N atoms (6 non-hydrogen)" and terminal O/OXT warnings (normal — added hydrogens plus the CTER-patch terminal oxygens always get guessed coordinates); anything about unrecognized residues, failed patches, or unexpected segment counts means the input needs attention before continuing.

## Step 4 — Build the MDFF grid potential + gridpdb

Edit `03_make_gridpdb.tcl` (basename, basemapname), then:
```
run_vmd 03_make_gridpdb.tcl
```
Produces `MAP-grid.dx` (the potential `mgridForce` reads) and `PROTEIN_autopsf-grid.pdb` (atomic masses in the beta column, used alongside it).

## Step 5 — Build restraints

Edit `04_make_restraints.tcl` (basename), then:
```
run_vmd 04_make_restraints.tcl
```
Produces `PROTEIN_extrabonds.txt` (secondary structure + h-bonds), `PROTEIN_extrabonds-cispeptide.txt`, `PROTEIN_extrabonds-chirality.txt`. "Phi dihedral angle... will not be restrained due to missing previous C atom" warnings for the first residue of each chain/segment are expected, not a problem.

`run_pipeline.sh` chains steps 2-5 for convenience once all four scripts are edited.

## Step 6 — Visual sanity check before running NAMD

Edit `05_view_overlay.tcl` (basename, mapbasename), then run it in GUI mode (not `run_vmd`, which forces `-dispdev text`):
```
source 00_env.sh   # for VMDDIR/MASTERVMDDIR only
$VMD_BIN -e 05_view_overlay.tcl
```
Confirm the gridpdb structure and the griddx isosurface actually overlap in the same frame before spending compute time on a run that turns out to be misaligned. If they don't overlap, suspect the export step's model-number/`relModel` choice, not this step.

## Step 7 — Staged NAMD3 run

Copy `mdff_stage_template.namd` per stage as `06_mdff_run1-stepN.namd`, filling in the `set` block per the template's own staging guidance (docking stage with restraints and dynamics, then refinement stage(s) that drop restraints and just minimize). List the stage files in order in `run_mdff.sh`'s `STAGES` array, then:
```
./run_mdff.sh [nprocs]
```

**Extending for convergence**: rather than guessing a total step count up front, run a stage, check the fit-quality trend (Step 8), and if CCC is still climbing at a meaningful rate, add another stage continuing from the last one's restart files (same shape as a refinement stage, new `INPUTNAME`/`OUTPUTNAME`). Repeat until the CCC-vs-step curve visibly flattens (e.g. the per-block gain drops to a fraction of the first block's gain), then stop — this is the actual convergence criterion, not a fixed step count. A 50k-100k step minimization block is cheap (order of 1-5 minutes on a modern multicore desktop) so this loop is worth running interactively rather than front-loading a huge single run.

## Step 8 — Check fit quality

Edit `06_analyze_fit.tcl` (basename, mapname, mapresolution, dcdfiles list — add each stage's `.dcd` in run order), then:
```
run_vmd 06_analyze_fit.tcl
```
Produces `PROTEIN_rmsd.dat` and `PROTEIN_ccc.dat` (one line per trajectory frame: frame index, value).

**GOTCHA — do not correlate against the `-grid.dx` file.** `mdff griddx` (Step 4) clamps, negates, and rescales the density into a [0,1] potential well for `mgridForce` — see `mdff_map.tcl`'s `mdff_griddx` (`voltool clamp` -> `voltool smult -amt -1` -> `voltool range -minmax {0 1}`). Correlating the model against that inverted potential gives a strongly *negative*, meaningless CCC (this actually happened on the reference run: -0.81 against the grid file vs. +0.80 against the real map). Always point `06_analyze_fit.tcl`'s `mapname` at the original exported map (Step 2's `MAP.mrc`), never the `*-grid.dx` file.

If asked to plot the CCC or RMSD trend, use the `dataviz` skill/`mcp__visualize` tooling for the chart — a single-series line chart of value vs. NAMD step (frame index * dcdfreq, typically 1000) is the right form; no categorical palette needed for one series.

## Throughout — note deviations from the template

If a project needs something the tutorial's standard two-stage protocol doesn't cover (multiple maps for multi-body fitting, positional constraints via `CONSPDB`, fixed atoms via `FIXPDB`, GBIS implicit solvent via `GBISON`), those hooks already exist in `mdff_template.namd` (see its `if {$GRIDON}` / `if {$CONSPDB != 0}` / `if {$FIXPDB != 0}` / `if {$GBISON}` blocks) — set the corresponding variable in the stage file rather than editing the shared template.
