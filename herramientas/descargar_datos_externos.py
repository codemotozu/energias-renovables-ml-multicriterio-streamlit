# -*- coding: utf-8 -*-
"""Descarga los dos insumos nuevos de la Fase 4 para la recomendación por país.

1. IRENASTAT por país: capacidad y generación renovable, 2015–2025.
2. NASA POWER: climatología 2001–2025 de radiación solar, viento a 50 m y precipitación en hasta cinco puntos
   representativos de cada país (centros de K-Means de sus plantas, ponderados por capacidad).

Los resultados quedan guardados en data/raw/: si ya existen, no se vuelven a descargar.
"""
import io
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from renovables.datos import SEMILLA, cargar_gppd  # noqa: E402

API_IRENA = ("https://pxweb.irena.org/api/v1/en/IRENASTAT/Power%20Capacity%20and%20Generation/"
             "Country_ELECSTAT_2026_H2_PX.px")
TEC_IRENA = {"3": "Hidroeléctrica", "4": "Solar", "9": "Solar", "5": "Eólica", "21": "Eólica", "15": "Geotérmica",
             "8": "Biomasa", "10": "Biomasa", "12": "Biomasa", "20": "Biomasa"}
API_POWER = ("https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=ALLSKY_SFC_SW_DWN,WS50M,PRECTOTCORR"
             "&community=RE&longitude={lon}&latitude={lat}&format=JSON")
CABECERA = {"User-Agent": "proyecto-academico-renovables"}
MAX_PUNTOS = 5


def descargar_irena(ruta):
    if ruta.exists():
        return
    with urllib.request.urlopen(API_IRENA, timeout=120) as r:
        variables = json.load(r)["variables"]
    anios = [c for c, t in zip(variables[4]["values"], variables[4]["valueTexts"]) if int(t) >= 2015]
    seleccion = [variables[0]["values"], list(TEC_IRENA), variables[2]["values"], ["0"], anios]
    consulta = [{"code": v["code"], "selection": {"filter": "item", "values": s}} for v, s in zip(variables, seleccion)]
    pedido = urllib.request.Request(API_IRENA, headers={"Content-Type": "application/json"},
                                    data=json.dumps({"query": consulta, "response": {"format": "json-stat2"}}).encode())
    with urllib.request.urlopen(pedido, timeout=300) as r:
        js = json.load(r)
    dims = js["id"]
    categorias = [list(js["dimension"][d]["category"]["index"]) if isinstance(js["dimension"][d]["category"]["index"], list)
                  else sorted(js["dimension"][d]["category"]["index"], key=js["dimension"][d]["category"]["index"].get)
                  for d in dims]
    indice = pd.MultiIndex.from_product(categorias, names=dims)
    d = pd.DataFrame({"valor": js["value"]}, index=indice).reset_index()
    d.columns = ["iso3", "cod_tec", "cod_tipo", "red", "cod_anio", "valor"]
    d["anio"] = d["cod_anio"].map(dict(zip(variables[4]["values"], variables[4]["valueTexts"]))).astype(int)
    d["tecnologia"] = d["cod_tec"].map(TEC_IRENA)
    d["medida"] = d["cod_tipo"].map({"0": "gen_gwh", "1": "cap_mw"})
    d["fuente_irena"] = d["cod_tec"].map(dict(zip(variables[1]["values"], variables[1]["valueTexts"])))
    d = d.dropna(subset=["valor"])[["iso3", "tecnologia", "fuente_irena", "medida", "anio", "valor"]]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(ruta, index=False, encoding="utf-8")


def puntos_por_pais(gppd):
    """Hasta cinco centros por país, ponderados por capacidad y redondeados a la malla de 0.5° de POWER."""
    filas = []
    for pais, g in gppd.dropna(subset=["latitude", "longitude", "capacity_mw"]).groupby("country"):
        unicos = g[["latitude", "longitude"]].drop_duplicates()
        k = min(MAX_PUNTOS, len(unicos))
        km = KMeans(n_clusters=k, n_init=5, random_state=SEMILLA).fit(g[["latitude", "longitude"]], sample_weight=g["capacity_mw"])
        peso = g.groupby(km.labels_)["capacity_mw"].sum() / g["capacity_mw"].sum()
        for j, (lat, lon) in enumerate(km.cluster_centers_):
            filas.append({"country": pais, "punto": j, "lat": round(lat * 2) / 2, "lon": round(lon * 2) / 2, "peso": float(peso.get(j, 0))})
    return pd.DataFrame(filas)


def consultar_power(celda):
    lat, lon = celda
    for intento in range(6):
        try:
            pedido = urllib.request.Request(API_POWER.format(lat=lat, lon=lon), headers=CABECERA)
            with urllib.request.urlopen(pedido, timeout=60) as r:
                p = json.load(r)["properties"]["parameter"]
            return {"lat": lat, "lon": lon, "ghi_kwh_m2_dia": p["ALLSKY_SFC_SW_DWN"]["ANN"],
                    "viento_50m_ms": p["WS50M"]["ANN"], "precip_mm_dia": p["PRECTOTCORR"]["ANN"]}
        except Exception:
            time.sleep(2 * (intento + 1))
    return {"lat": lat, "lon": lon, "ghi_kwh_m2_dia": np.nan, "viento_50m_ms": np.nan, "precip_mm_dia": np.nan}


def descargar_power(gppd, ruta_puntos, ruta_celdas):
    puntos = puntos_por_pais(gppd)
    puntos.to_csv(ruta_puntos, index=False, encoding="utf-8")
    hechas = pd.read_csv(ruta_celdas) if ruta_celdas.exists() else pd.DataFrame(columns=["lat", "lon"])
    hechas = hechas.dropna() if len(hechas) else hechas
    ya = set(zip(hechas["lat"], hechas["lon"]))
    faltan = [c for c in sorted(set(zip(puntos["lat"], puntos["lon"]))) if c not in ya]
    print(f"Puntos: {len(puntos)} en {puntos['country'].nunique()} países | celdas por consultar: {len(faltan)}", flush=True)
    filas = hechas.to_dict("records")
    with ThreadPoolExecutor(max_workers=3) as ex:                 # pocas consultas simultáneas para no saturar el servicio
        for i, fila in enumerate(ex.map(consultar_power, faltan), 1):
            filas.append(fila)
            if i % 100 == 0 or i == len(faltan):
                pd.DataFrame(filas).to_csv(ruta_celdas, index=False)
                print(f"  {i}/{len(faltan)}", flush=True)
    return pd.DataFrame(filas)


if __name__ == "__main__":
    gppd = cargar_gppd(RAIZ / "data" / "raw" / "gppd_v1_3" / "global_power_plant_database.csv")
    ruta_irena = RAIZ / "data" / "raw" / "irenastat" / "irenastat_pais_tecnologia.csv"
    descargar_irena(ruta_irena)
    print("IRENASTAT por país:", pd.read_csv(ruta_irena).shape, flush=True)
    (RAIZ / "data" / "raw" / "nasa_power").mkdir(parents=True, exist_ok=True)
    celdas = descargar_power(gppd, RAIZ / "data" / "raw" / "nasa_power" / "puntos_por_pais.csv",
                             RAIZ / "data" / "raw" / "nasa_power" / "nasa_power_celdas.csv")
    print("Celdas de NASA POWER:", len(celdas), "| sin dato:", int(celdas["ghi_kwh_m2_dia"].isna().sum()), flush=True)
    print("TERMINADO", flush=True)
