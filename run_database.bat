@echo off
REM Pre-registered database benchmark (SELECTION_RULE.md): protocol v5, r2SCAN model first, then the PBE baseline.
REM Skips materials whose result file already exists, so it can be stopped and restarted.
set PYTHONUTF8=1
set LANDAU_PROTOCOL=v5
set LANDAU_MLIP_MODEL=mace-matpes-r2scan-0
python -u run_benchmark.py --registry >> results\database_v5_r2scan_log.txt 2>&1
set LANDAU_MLIP_MODEL=medium
python -u run_benchmark.py --registry >> results\database_v5_pbe_log.txt 2>&1
python make_benchmark_table.py --database
