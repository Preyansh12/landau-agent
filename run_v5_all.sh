#!/usr/bin/env bash
export PYTHONUTF8=1 LANDAU_PROTOCOL=v5 LANDAU_MLIP_MODEL=mace-matpes-r2scan-0
python -u run_benchmark.py CaTiO3 PbTiO3 LaAlO3 BaTiO3 SrTiO3 Ca3Ti2O7 Sr3Zr2O7 Sr3Ru2O7 Sr3Ti2O7 Ca3Mn2O7 Ca3Sn2O7 Sr3Sn2O7 Sr3Hf2O7
