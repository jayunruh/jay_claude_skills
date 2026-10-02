#!/bin/bash
# Run one or more MDFF NAMD stages sequentially with namd3. Each stage after
# the first restarts from the previous stage's restart files, so they can't
# run concurrently.
#
# EDIT the STAGES list below to the actual stage config filenames for this
# project (see mdff_stage_template.namd), in run order.
#
# Usage:
#   ./run_mdff.sh [nprocs]
set -euo pipefail
cd "$(dirname "$0")"
source 00_env.sh

NPROCS="${1:-4}"

STAGES=(06_mdff_run1-step1.namd 06_mdff_run1-step2.namd)

for stage in "${STAGES[@]}"; do
  logfile="${stage%.namd}.log"
  echo "=== namd3 +p${NPROCS} ${stage} ==="
  run_namd "$stage" "$NPROCS" "$logfile"
  echo "done, see ${logfile}"
done
