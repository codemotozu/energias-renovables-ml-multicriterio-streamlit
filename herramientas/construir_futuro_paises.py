# -*- coding: utf-8 -*-
"""Calcula la recomendación de cada país en los escenarios de futuro de la vista 7 (data/processed/recomendacion_pais_futuro.csv)
sin reconstruir todos los artefactos. construir_artefactos.py hace lo mismo como parte del proceso completo.
"""
import sys
import time
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from renovables import saltos as sa  # noqa: E402
from renovables.datos import TECS  # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    proc = RAIZ / "data" / "processed"
    d = pd.read_csv(proc / "criterios.csv", index_col=0).reindex(TECS)
    fp = pd.read_csv(proc / "fp_local.csv")
    nombres = pd.read_csv(proc / "recomendacion_pais.csv").drop_duplicates("iso3")[["iso3", "pais", "region", "ingreso"]]
    futuro = sa.recomendar_futuro(d, fp, n=4000).merge(nombres, on="iso3", how="left")
    futuro["pais"], futuro["region"] = futuro["pais"].fillna(futuro["iso3"]), futuro["region"].fillna("Otros territorios")
    futuro.round(2).to_csv(proc / "recomendacion_pais_futuro.csv", index=False, encoding="utf-8")
    for nombre, g in futuro.groupby("escenario", sort=False):
        print(f"{nombre}: {g['recomendada'].value_counts().to_dict()} | clara: {int((g['certeza'] == 'Clara').sum())} | reñida: {int((g['certeza'] == 'Reñida').sum())}")
    print(f"listo en {time.time() - t0:.0f} s")
