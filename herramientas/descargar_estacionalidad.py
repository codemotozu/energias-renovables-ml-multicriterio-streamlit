# -*- coding: utf-8 -*-
"""Descarga la radiación solar mes a mes (climatología 2001–2025 de NASA POWER) en las mismas celdas de la recomendación por país.

El promedio anual esconde el invierno: en los países del norte, el mes más oscuro recibe una pequeña fracción del sol medio.
Resultado: data/raw/nasa_power/ghi_mensual_celdas.csv. Si ya existe, solo se consultan las celdas que faltan.
"""
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
API = ("https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=ALLSKY_SFC_SW_DWN"
       "&community=RE&longitude={lon}&latitude={lat}&format=JSON")
CABECERA = {"User-Agent": "proyecto-academico-renovables"}
MESES = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def consultar(celda):
    lat, lon = celda
    for intento in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(API.format(lat=lat, lon=lon), headers=CABECERA), timeout=60) as r:
                g = json.load(r)["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
            return {"lat": lat, "lon": lon, **{m: g[m] for m in MESES}, "ANN": g["ANN"]}
        except Exception:
            time.sleep(2 * (intento + 1))
    return {"lat": lat, "lon": lon, **{m: np.nan for m in MESES}, "ANN": np.nan}


if __name__ == "__main__":
    carpeta = RAIZ / "data" / "raw" / "nasa_power"
    salida = carpeta / "ghi_mensual_celdas.csv"
    celdas = pd.read_csv(carpeta / "puntos_por_pais.csv")[["lat", "lon"]].drop_duplicates()
    hechas = pd.read_csv(salida).dropna() if salida.exists() else pd.DataFrame(columns=["lat", "lon"])
    ya = set(zip(hechas["lat"], hechas["lon"]))
    faltan = [c for c in sorted(zip(celdas["lat"], celdas["lon"])) if c not in ya]
    print(f"Celdas: {len(celdas)} | por consultar: {len(faltan)}", flush=True)
    filas = hechas.to_dict("records")
    with ThreadPoolExecutor(max_workers=3) as ex:                 # pocas consultas simultáneas para no saturar el servicio
        for i, fila in enumerate(ex.map(consultar, faltan), 1):
            filas.append(fila)
            if i % 100 == 0 or i == len(faltan):
                pd.DataFrame(filas).to_csv(salida, index=False)
                print(f"  {i}/{len(faltan)}", flush=True)
    d = pd.read_csv(salida)
    print("Celdas guardadas:", len(d), "| sin dato:", int(d["ANN"].isna().sum()), flush=True)
    print("TERMINADO", flush=True)
