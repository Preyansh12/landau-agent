#!/usr/bin/env bash
export PYTHONUTF8=1 LANDAU_PROTOCOL=v5
LANDAU_MLIP_MODEL=mace-matpes-r2scan-0 python -u run_benchmark.py --registry 2>&1 | tee -a results/database_v5_r2scan_log.txt
LANDAU_MLIP_MODEL=medium python -u run_benchmark.py --registry 2>&1 | tee -a results/database_v5_pbe_log.txt
python make_benchmark_table.py --database
