# Track fit quality over the MDFF trajectory: RMSD relative to the starting
# (pre-fitting) structure, and cross-correlation against the cryo-EM map.
#
# EDIT: basename, refpdb, mapname, mapresolution, and dcdfiles (add each
# new extension stage's .dcd, in run order, to get a continuous trace
# across all of them -- see mdff_stage_template.namd).
#
# Run with:
#   run_vmd 06_analyze_fit.tcl
# (see 00_env.sh)
#
# Run this after the NAMD stage(s) have produced their .dcd file(s).

package require mdff

set basename PROTEIN
set psfname "${basename}_autopsf.psf"
set refpdb "${basename}_autopsf.pdb"

# GOTCHA (cost real time to debug once, don't repeat it): use the
# ORIGINAL density map here, NOT the *-grid.dx potential from
# 03_make_gridpdb.tcl. `mdff griddx` clamps, NEGATES, and rescales that
# potential to [0,1] for mgridForce (see mdff_map.tcl's mdff_griddx --
# it's `voltool clamp` then `voltool smult -amt -1` then rescale). CCC
# against that inverted potential comes out strongly *negative* (e.g.
# -0.81) and is meaningless. CCC needs the real experimental density
# (the .mrc/.dx exported straight from ChimeraX/the original map file,
# before mdff griddx touched it).
set mapname MAP.mrc

# GOTCHA: this must be the map's actual reported resolution (e.g. the
# cryoSPARC/RELION job's FSC-based "Estimated Resolution (A)"), NOT the
# voxel/pixel spacing. A real case of this mixup: the map's voxel size
# was 1.555 A and someone typed that in as "the resolution" -- by
# Nyquist, true resolution must be at least ~2x the pixel size, so that
# value was nonsensically fine. Ask if it isn't already known; don't
# infer it from the grid.
set mapresolution 0.0
if {$mapresolution <= 0.0} {
  puts "ERROR: set mapresolution to the map's actual resolution (A) before running this script."
  quit
}

set dcdfiles {mdff_run1-step2.dcd}

mol new $psfname
foreach dcdfile $dcdfiles {
  mol addfile $dcdfile waitfor all
}

mdff check -mol top -frames all \
  -rmsd -refpdb $refpdb -rmsdseltext backbone -rmsdfile ${basename}_rmsd.dat \
  -ccc -map $mapname -res $mapresolution -cccseltext protein -cccfile ${basename}_ccc.dat

puts "Wrote ${basename}_rmsd.dat and ${basename}_ccc.dat"

quit
