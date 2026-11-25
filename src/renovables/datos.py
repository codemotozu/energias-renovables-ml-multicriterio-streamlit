"""Carga de la GPPD, indicadores de la Fase 1, variables y partición de la Fase 2 (mismo código y misma semilla)."""
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neighbors import BallTree

SEMILLA = 42
SHA256_GPPD = "4b1f93e0fd93664f18684d9b05d0a52ed9658c6a8cf0d21ff2520791379ba7fc"
MAPA_TEC = {"Solar": "Solar", "Wind": "Eólica", "Hydro": "Hidroeléctrica",
            "Geothermal": "Geotérmica", "Biomass": "Biomasa", "Wave and Tidal": "Mareomotriz/undimotriz"}
TEC_ORDEN = list(MAPA_TEC.values())
TECS = TEC_ORDEN[:5]
NIVELES = ["Bajo", "Medio", "Alto"]
ANIO_REFERENCIA = 2019
ANIOS = list(range(2013, 2020))
COLS_GEN = [f"generation_gwh_{a}" for a in ANIOS]
LIMITE_SUPERIOR_FP = {"Solar": 0.40, "Eólica": 0.65}
R_TIERRA_KM = 6371.0
VARS_NUM = ["log_capacidad", "irradiacion_relativa", "densidad_misma_tec", "edad_planta", "latitude", "longitude"]
PREDICTORES = ["tecnologia", "country"] + VARS_NUM


def cargar_gppd(ruta):
    """Lee el CSV original y verifica que sea exactamente la versión usada en todas las fases."""
    ruta = Path(ruta)
    huella = hashlib.sha256(ruta.read_bytes()).hexdigest()
    if huella != SHA256_GPPD:
        raise ValueError("El archivo no coincide con la GPPD v1.3.0 usada en el proyecto")
    return pd.read_csv(ruta, low_memory=False, encoding="utf-8")


def construir_indicadores(d):
    """Factor de planta (FP) válido por año, promedio, estabilidad y variables geográficas (Fase 1)."""
    d = d.copy()
    d["tecnologia"] = pd.Categorical(d["primary_fuel"].map(MAPA_TEC), categories=TEC_ORDEN)
    anio_op = np.floor(d["commissioning_year"])
    d["anio_operacion"] = anio_op
    d["posible_bombeo"] = d["name"].str.contains("pump", case=False, na=False) | (d[COLS_GEN] < 0).any(axis=1)
    fp = pd.DataFrame({a: d[f"generation_gwh_{a}"] / (d["capacity_mw"] * 8.76) for a in ANIOS}, index=d.index)
    anio_parcial = pd.DataFrame({a: anio_op.notna() & (anio_op >= a) for a in ANIOS}, index=d.index)
    valido = (fp.gt(0) & fp.le(1) & ~anio_parcial).apply(lambda col: col & ~d["posible_bombeo"])
    fp_valido = fp.where(valido)
    d["n_anios_generacion"] = fp_valido.notna().sum(axis=1)
    d["factor_planta_prom"] = fp_valido.mean(axis=1)
    d["cv_generacion"] = (fp_valido.std(axis=1, ddof=1) / fp_valido.mean(axis=1)).where(d["n_anios_generacion"] >= 3)
    d["tiene_generacion"] = d["n_anios_generacion"] > 0
    d["latitud_abs"] = d["latitude"].abs()
    return d


def densidad_misma_tecnologia(lat, lon, tecnologia, universo, radio_km=100, excluir_propia=True):
    """log(1 + plantas de la misma tecnología a menos de radio_km). Para una planta nueva, excluir_propia=False."""
    ref = universo[universo["tecnologia"].astype(str) == tecnologia]
    arbol = BallTree(np.radians(ref[["latitude", "longitude"]].values), metric="haversine")
    n = arbol.query_radius(np.radians([[lat, lon]]), r=radio_km / R_TIERRA_KM, count_only=True)[0]
    return float(np.log1p(n - 1 if excluir_propia else n))


def derivar_variables(d, universo, radio_km=100):
    """Variables derivadas deterministas de la Fase 2."""
    d = d.copy()
    d["log_capacidad"] = np.log10(d["capacity_mw"])
    d["edad_planta"] = ANIO_REFERENCIA - d["anio_operacion"]
    d["irradiacion_relativa"] = np.cos(np.radians(d["latitude"]))
    d["densidad_misma_tec"] = np.nan
    for tec, grupo in d.groupby("tecnologia", observed=True):
        ref = universo[universo["tecnologia"] == tec]
        arbol = BallTree(np.radians(ref[["latitude", "longitude"]].values), metric="haversine")
        n = arbol.query_radius(np.radians(grupo[["latitude", "longitude"]].values), r=radio_km / R_TIERRA_KM, count_only=True)
        d.loc[grupo.index, "densidad_misma_tec"] = np.log1p(n - 1)
    return d


def particionar(datos, semilla=SEMILLA):
    """Partición 70/15/15 estratificada por tecnología y nivel, y agrupada por sitio (Fase 2)."""
    tec = datos["tecnologia"].astype(str)
    estrato_completo = tec + " · " + datos["nivel_desempeno"].astype(str)
    minimo_por_tec = estrato_completo.value_counts().groupby(lambda e: e.split(" · ")[0]).min()
    tec_solo = minimo_por_tec.index[minimo_por_tec < 20]
    estrato = pd.Series(np.where(tec.isin(tec_solo), tec, estrato_completo), index=datos.index)
    estrato_sitio = estrato.groupby(datos["sitio"]).agg(lambda s: s.mode().iloc[0])
    s_ent, s_resto = train_test_split(estrato_sitio.index, test_size=0.30, stratify=estrato_sitio.values, random_state=semilla)
    s_val, s_pru = train_test_split(s_resto, test_size=0.50, stratify=estrato_sitio.loc[s_resto].values, random_state=semilla)
    return np.select([datos["sitio"].isin(s_pru), datos["sitio"].isin(s_val)], ["prueba", "validación"], default="entrenamiento")


def preparar_modelado(df_raw):
    """Devuelve (universo renovable, conjunto de modelado con partición) y verifica que coincide con la Fase 2."""
    df = construir_indicadores(df_raw[df_raw["primary_fuel"].isin(MAPA_TEC)].reset_index(drop=True))
    d2 = df[(df["tecnologia"] != "Mareomotriz/undimotriz") & df["tiene_generacion"]]
    limite = d2["tecnologia"].astype(str).map(LIMITE_SUPERIOR_FP).fillna(1.0)
    d3 = d2[(d2["factor_planta_prom"] <= limite) & (d2["factor_planta_prom"] >= 0.01)].copy()
    d3["sitio"] = d3.groupby([d3["latitude"].round(4), d3["longitude"].round(4), "tecnologia"], observed=True).ngroup()
    dm = derivar_variables(d3, df)
    dm["nivel_desempeno"] = pd.qcut(df.loc[df["tiene_generacion"], "factor_planta_prom"], 3, labels=NIVELES).reindex(dm.index)
    dm["conjunto"] = particionar(dm)
    tamanos = dm["conjunto"].value_counts().reindex(["entrenamiento", "validación", "prueba"]).tolist()
    if tamanos != [4202, 902, 907]:
        raise ValueError(f"La partición no coincide con la de la Fase 2: {tamanos}")
    return df, dm
