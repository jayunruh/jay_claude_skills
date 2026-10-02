#!/bin/bash
# Structure-prep pipeline: ChimeraX session -> PSF/PDB -> MDFF grid files ->
# restraints. Stops before the actual namd3 run (see run_mdff.sh) and
# analysis (see 06_analyze_fit.tcl), which need user judgment calls
# (processor count, run duration, map resolution).
set -euo pipefail
cd "$(dirname "$0")"
source 00_env.sh

echo "=== 1/4 export protein + map from ChimeraX session ==="
run_chimerax 01_export_from_session.cxc

echo "=== 2/4 build CHARMM PSF (VMD autopsf) ==="
run_vmd 02_make_psf.tcl

echo "=== 3/4 build MDFF grid potential + gridpdb ==="
run_vmd 03_make_gridpdb.tcl

echo "=== 4/4 build secondary-structure/cispeptide/chirality restraints ==="
run_vmd 04_make_restraints.tcl

echo "Done. Next: review with 05_view_overlay.tcl, then run ./run_mdff.sh"
