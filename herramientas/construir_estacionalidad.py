# -*- coding: utf-8 -*-
"""Calcula la radiación mes a mes de cada país (data/processed/estacionalidad_pais.csv) sin reconstruir todos los artefactos.

Requiere data/raw/nasa_power/ghi_mensual_celdas.csv (herramientas/descargar_estacionalidad.py). construir_artefactos.py hace
lo mismo como parte del proceso completo.
"""
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from renovables import paises as pa  # noqa: E402

if __name__ == "__main__":
    nasa = RAIZ / "data" / "raw" / "nasa_power"
    est = pa.estacionalidad_pais(pd.read_csv(nasa / "puntos_por_pais.csv"), pd.read_csv(nasa / "ghi_mensual_celdas.csv"))
    est.to_csv(RAIZ / "data" / "processed" / "estacionalidad_pais.csv", index=False, encoding="utf-8")
    print(f"Países: {len(est)} | con invierno oscuro (mes más oscuro < {pa.UMBRAL_INVIERNO:.0f} % del promedio): {int(est['invierno_oscuro'].sum())}")
