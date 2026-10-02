"""Run a VMD Tcl script through the conda-forge vmd-python engine (pixi-managed,
headless -- no VMD.app/license download needed). Equivalent to
`vmd -dispdev text -e <script>.tcl`, used by all this pipeline's *.tcl scripts.

Usage: pixi run vmd <script.tcl>
"""
import sys
import vmd

with open(sys.argv[1]) as f:
    script = f.read()

try:
    vmd.evaltcl(script)
except ValueError as e:
    # `quit`/`exit` in the script raises an unmessaged ValueError from the
    # embedded interpreter on normal termination -- not a real failure.
    # A real Tcl error (e.g. a failed dlopen) carries a message; re-raise those.
    if str(e):
        raise
