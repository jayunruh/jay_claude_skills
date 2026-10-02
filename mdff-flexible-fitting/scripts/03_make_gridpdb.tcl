# Generate the MDFF potential map (griddx) and the mass-weighted gridpdb
# used to apply grid forces in NAMD.
#
# EDIT: basename (must match 02_make_psf.tcl's) and basemapname (must
# match the MAP.mrc filename from 01_export_from_session.cxc, minus
# the .mrc extension).
#
# Run with:
#   run_vmd 03_make_gridpdb.tcl
# (see 00_env.sh)
#
# GOTCHA: `mdff` is not auto-loaded in batch/text mode -- omitting this
# `package require` fails with "Type 'mdffi' for summary of usage" and
# no files get written.

package require mdff

set basename PROTEIN
set pdbname "${basename}_autopsf.pdb"
set psfname "${basename}_autopsf.psf"
set gridname "${basename}_autopsf-grid.pdb"
set basemapname MAP
set mrcname "${basemapname}.mrc"
set mapname "${basemapname}-grid.dx"

# make sure you have the psf generated before running this (02_make_psf.tcl)

mdff griddx -i $mrcname -o $mapname
mdff gridpdb -psf $psfname -pdb $pdbname -o $gridname

quit
