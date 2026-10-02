# Generate secondary-structure, cis-peptide, and chirality restraints
# (extrabonds) that keep the model's stereochemistry sane during MDFF.
#
# EDIT: basename (must match 02_make_psf.tcl's).
#
# Run with:
#   run_vmd 04_make_restraints.tcl
# (see 00_env.sh)
#
# GOTCHA: none of ssrestraints/cispeptide/chirality are auto-loaded in
# batch/text mode -- omitting these `package require` lines fails with
# "invalid command name ssrestraints" etc.

package require ssrestraints
package require cispeptide
package require chirality

set basename PROTEIN
set pdbname "${basename}_autopsf.pdb"
set psfname "${basename}_autopsf.psf"

# note: this loads the molecule (important for the cispeptide/chirality
# commands below, which act on the top molecule)
ssrestraints -psf $psfname -pdb $pdbname -o ${basename}_extrabonds.txt -hbonds

cispeptide restrain -o ${basename}_extrabonds-cispeptide.txt

chirality restrain -o ${basename}_extrabonds-chirality.txt

quit
