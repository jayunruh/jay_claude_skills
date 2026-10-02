# Visual sanity check: overlay the mdff gridpdb (the structure as NAMD's
# mgridForce will see it) on the mdff griddx potential (the grid NAMD will
# pull it toward), to confirm they're in the same frame and the fit looks
# reasonable before spending time on the actual namd3 run.
#
# EDIT: basename / mapbasename to match the earlier steps.
#
# Run with (GUI, not headless):
#   export VMDDIR=... ; export MASTERVMDDIR="$VMDDIR"   (see 00_env.sh)
#   $VMD_BIN -e 05_view_overlay.tcl
# or paste these commands into the VMD Tk Console after opening VMD.
#
# The isosurface level for the *_grid.dx potential is NOT the same scale
# as the original map -- mdff griddx clamps/negates/rescales it to [0,1]
# (see 06_analyze_fit.tcl's note on this). 0.8 is just a reasonable
# starting guess in that rescaled range; adjust live via Graphics ->
# Representations if the surface looks empty or fully solid.

set basename PROTEIN
set mapbasename MAP

mol new ${basename}_autopsf-grid.pdb type pdb waitfor all
mol modstyle 0 top NewCartoon
mol modcolor 0 top Chain

mol new ${mapbasename}-grid.dx type dx waitfor all
set mapmol [molinfo top]
mol modstyle 0 $mapmol Isosurface 0.8 0 0 1 1 1
mol modcolor 0 $mapmol ColorID 8
mol modmaterial 0 $mapmol Transparent

display resetview
