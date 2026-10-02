# Build a CHARMM PSF/PDB for the exported structure using VMD's autopsf
# (adds missing hydrogens, N/C-terminal patches, per-chain segments).
#
# EDIT: set basename to this project's protein name; PROTEIN.pdb must
# match the filename 01_export_from_session.cxc actually wrote.
#
# Run with:
#   run_vmd 02_make_psf.tcl
# (see 00_env.sh)
#
# GOTCHA: `autopsf` is not auto-loaded by VMD's batch/text-mode Tcl
# interpreter the way it is when you open the Extensions menu in the
# GUI -- omitting this `package require` fails with
# "invalid command name autopsf".
#
# NOTE: autopsf guesses coordinates for atoms it can't place directly
# (all added hydrogens, plus the terminal O/OXT it repositions per the
# CTER patch -- 2 heavy atoms per chain). Those atoms get occupancy 0.0
# in the output PDB. This is normal/expected and is why the tutorial
# runs a short minimization before MDFF proper.
#
# Always check the log for anything beyond the expected warnings above,
# and confirm chain breaks/termini were assigned as expected.

package require autopsf

set basename PROTEIN

mol new ${basename}.pdb
autopsf -mol top -prefix $basename

# autopsf writes ${basename}_formatted_autopsf.{psf,pdb}; rename to the
# ${basename}_autopsf.{psf,pdb} convention used by the rest of the pipeline.
file copy -force ${basename}_formatted_autopsf.psf ${basename}_autopsf.psf
file copy -force ${basename}_formatted_autopsf.pdb ${basename}_autopsf.pdb

quit
