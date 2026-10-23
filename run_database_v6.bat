@echo off
REM Protocol v6 on the database set (r2SCAN, then PBE), restartable. Run after run_database.bat has finished.
set PYTHONUTF8=1
set LANDAU_PROTOCOL=v6
set LANDAU_MLIP_MODEL=mace-matpes-r2scan-0
python -u run_benchmark.py --registry >> results\database_v6_r2scan_log.txt 2>&1
set LANDAU_MLIP_MODEL=medium
python -u run_benchmark.py --registry >> results\database_v6_pbe_log.txt 2>&1
python make_benchmark_table.py --database
