# -*- coding: utf-8 -*-
"""Descarga de NASA POWER la radiación y el viento HORARIOS (2022–2024) de seis países de estudio.

Usa los mismos puntos representativos de la recomendación por país (data/raw/nasa_power/puntos_por_pais.csv).
Si el archivo ya existe, no se vuelve a descargar.
"""
import gzip
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from renovables.geotermica import ANIOS_HORARIOS, CASOS  # noqa: E402

API = ("https://power.larc.nasa.gov/api/temporal/hourly/point?parameters=ALLSKY_SFC_SW_DWN,WS50M&community=RE"
       "&longitude={lon}&latitude={lat}&start={ini}0101&end={fin}1231&format=JSON&time-standard=UTC")
CABECERA = {"User-Agent": "proyecto-academico-renovables"}
SALIDA = RAIZ / "data" / "raw" / "nasa_power" / "horario_casos.csv.gz"


def consultar(celda):
    lat, lon = celda
    url = API.format(lat=lat, lon=lon, ini=ANIOS_HORARIOS[0], fin=ANIOS_HORARIOS[-1])
    for intento in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=CABECERA), timeout=180) as r:
                p = json.load(r)["properties"]["parameter"]
            return pd.DataFrame({"lat": lat, "lon": lon, "fecha_utc": list(p["WS50M"]), "ghi_w_m2": list(p["ALLSKY_SFC_SW_DWN"].values()),
                                 "viento_50m_ms": list(p["WS50M"].values())})
        except Exception as e:
            print(f"  reintento {intento + 1} en ({lat}, {lon}): {type(e).__name__}", flush=True)
            time.sleep(3 * (intento + 1))
    raise RuntimeError(f"No se pudo descargar la celda ({lat}, {lon})")


if __name__ == "__main__":
    if SALIDA.exists():
        print("Ya existe:", SALIDA.name)
        raise SystemExit
    puntos = pd.read_csv(RAIZ / "data" / "raw" / "nasa_power" / "puntos_por_pais.csv")
    puntos = puntos[puntos["country"].isin(CASOS)]
    celdas = sorted(set(zip(puntos["lat"], puntos["lon"])))
    print(f"{len(puntos)} puntos en {puntos['country'].nunique()} países | {len(celdas)} celdas", flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex:
        tablas = []
        for i, t in enumerate(ex.map(consultar, celdas), 1):
            tablas.append(t)
            print(f"  {i}/{len(celdas)}", flush=True)
    datos = pd.concat(tablas, ignore_index=True)
    with gzip.GzipFile(SALIDA, "wb", mtime=0) as f:
        f.write(datos.to_csv(index=False).encode("utf-8"))
    print("Filas:", len(datos), "| faltantes:", int((datos[["ghi_w_m2", "viento_50m_ms"]] <= -900).sum().sum()),
          "| MB:", round(SALIDA.stat().st_size / 1e6, 2), flush=True)
