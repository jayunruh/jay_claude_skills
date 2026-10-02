#!/bin/bash
# Shared environment for the MDFF pipeline scripts. Source this, don't run it:
#   source 00_env.sh
set -euo pipefail

# --- installed tools ---
export VMDDIR=/Applications/VMD.app/Contents/vmd2/lib
export MASTERVMDDIR="$VMDDIR"
VMD_BIN=/Applications/VMD.app/Contents/vmd2/bin/vmd
CHIMERAX_BIN=/Applications/ChimeraX-1.12.app/Contents/MacOS/ChimeraX
NAMD_BIN="$HOME/NAMD_Git-2025-10-14_MacOS-universal-multicore/namd3"

run_vmd () {
  # run_vmd <script.tcl>
  # VMDDIR must be exported before calling the vmd wrapper script -- it
  # otherwise defaults to a build-machine path that doesn't exist here
  # and the wrapper silently tries to exec a nonexistent binary.
  "$VMD_BIN" -dispdev text -e "$1"
}

run_vmd_pixi () {
  # run_vmd_pixi <script.tcl>
  # Portable alternative to run_vmd -- runs through the project's
  # pixi-managed vmd-python (see pixi.toml) instead of the standalone
  # VMD.app install, so a machine without VMD.app can still run this
  # pipeline. Needs `pixi install` once first.
  # GOTCHA: ssrestraints (04_make_restraints.tcl) needs STRIDE_BIN set to
  # a real STRIDE binary (see pixi.toml's [activation.env] comment) or it
  # silently writes an EMPTY extrabonds file instead of erroring --
  # always check the output file's line count, not just the exit code.
  pixi run vmd "$1"
}

run_chimerax () {
  # run_chimerax <script.cxc>
  "$CHIMERAX_BIN" --nogui --offscreen --script "$1"
}

run_namd () {
  # run_namd <config.namd> <nprocs> <logfile>
  "$NAMD_BIN" +p"$2" "$1" > "$3" 2>&1
}
