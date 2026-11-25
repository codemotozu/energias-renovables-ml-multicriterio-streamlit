"""Recomendación por país: factor de planta local (IRENA), recurso solar y eólico (NASA POWER) y Monte Carlo local."""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_val_predict

from .datos import LIMITE_SUPERIOR_FP, SEMILLA, TECS
from .multicriterio import aplicar_escenario_geo, resumen_puestos, simular

ANIOS_FP = (2020, 2024)
CAP_MIN_OBSERVADO = 5.0          # MW medios para considerar confiable el FP observado de un país
CAP_MIN_CALIBRAR = 50.0          # MW medios para entrar en la calibración recurso → FP
CAP_MIN_ELEGIBLE = 1.0           # MW instalados en 2025 para considerar que el recurso existe (hidro, geotérmica, biomasa)
SIEMPRE_ELEGIBLES = ("Solar", "Eólica")
RAZON_SOLAR = (0.50, 1.25)       # FP solar / (radiación media ÷ 24 h): fuera de este rango el dato no es físicamente creíble
RANGO_EOLICO = (0.10, 0.55)      # FP eólico nacional creíble: fuera de él, generación y capacidad reportadas no son compatibles
MEJORA_MINIMA = 0.05             # la calibración se usa solo si reduce el error de CV al menos 5 % frente a predecir la media


def fp_observado(irena):
    """FP medio 2020–2024 por país y tecnología: generación / (capacidad media del año × 8.76)."""
    a = irena.groupby(["iso3", "tecnologia", "medida", "anio"])["valor"].sum().unstack("medida").reset_index()
    a = a.sort_values(["iso3", "tecnologia", "anio"])
    a["cap_media"] = a.groupby(["iso3", "tecnologia"])["cap_mw"].transform(lambda s: (s + s.shift(1)) / 2)
    v = a[a["anio"].between(*ANIOS_FP) & (a["cap_media"] > 0) & a["gen_gwh"].notna()]
    g = v.groupby(["iso3", "tecnologia"]).agg(gen=("gen_gwh", "sum"), cap=("cap_media", "sum"), cap_media=("cap_media", "mean"))
    g["fp_obs"] = g["gen"] / (8.76 * g["cap"])
    limite = g.index.get_level_values("tecnologia").map(lambda t: LIMITE_SUPERIOR_FP.get(t, 1.0))
    g["fp_obs"] = g["fp_obs"].where((g["fp_obs"] >= 0.01) & (g["fp_obs"] <= limite))
    cap_2025 = a[a["anio"] == a["anio"].max()].set_index(["iso3", "tecnologia"])["cap_mw"].rename("cap_2025_mw")
    return g[["fp_obs", "cap_media"]].join(cap_2025, how="outer").reset_index()


def recurso_por_pais(puntos, celdas):
    """Radiación y precipitación ponderadas por capacidad; viento en el mejor punto, porque los parques buscan ese sitio."""
    p = puntos.merge(celdas.dropna(), on=["lat", "lon"], how="inner")
    p["peso"] = p["peso"] / p.groupby("country")["peso"].transform("sum")
    filas = []
    for pais, g in p.groupby("country"):
        filas.append({"iso3": pais, "ghi_kwh_m2_dia": np.average(g["ghi_kwh_m2_dia"], weights=g["peso"]),
                      "viento_medio_ms": np.average(g["viento_50m_ms"], weights=g["peso"]),
                      "viento_max_ms": g["viento_50m_ms"].max(),
                      "precip_mm_dia": np.average(g["precip_mm_dia"], weights=g["peso"]), "n_puntos": len(g)})
    return pd.DataFrame(filas)


def depurar_solar(obs, recurso):
    """Retira el FP solar observado que no es compatible con la radiación del país (error de capacidad o de generación)."""
    o = obs.merge(recurso[["iso3", "ghi_kwh_m2_dia"]], on="iso3", how="left")
    razon = o["fp_obs"] / (o["ghi_kwh_m2_dia"] / 24)
    malo = (o["tecnologia"] == "Solar") & razon.notna() & ~razon.between(*RAZON_SOLAR)
    o.loc[malo, "fp_obs"] = np.nan
    return o.drop(columns="ghi_kwh_m2_dia"), int(malo.sum())


def depurar_eolica(obs, recurso):
    """Retira el FP eólico nacional fuera del rango físico creíble (p. ej., Sudáfrica 0.01 o Kenia 0.02)."""
    o = obs.copy()
    malo = (o["tecnologia"] == "Eólica") & o["fp_obs"].notna() & ~o["fp_obs"].between(*RANGO_EOLICO)
    o.loc[malo, "fp_obs"] = np.nan
    return o, int((malo & o["iso3"].isin(recurso["iso3"])).sum())


def calibrar_recurso(obs, recurso, tecnologia, variable):
    """Ajusta FP = a + b · recurso con países de capacidad suficiente y mide su error con CV de 5 pliegues."""
    d = obs[(obs["tecnologia"] == tecnologia) & (obs["cap_media"] >= CAP_MIN_CALIBRAR)].dropna(subset=["fp_obs"]).merge(recurso, on="iso3")
    X, y = d[[variable]].values, d["fp_obs"].values
    cv = KFold(5, shuffle=True, random_state=SEMILLA)
    pred = cross_val_predict(LinearRegression(), X, y, cv=cv)
    base = cross_val_predict(LinearRegression(), np.zeros_like(X), y, cv=cv)
    modelo = LinearRegression().fit(X, y)
    return modelo, {"tecnologia": tecnologia, "variable": variable, "paises": len(d), "pendiente": float(modelo.coef_[0]),
                    "intercepto": float(modelo.intercept_), "rho_spearman": float(stats.spearmanr(X.ravel(), y)[0]),
                    "MAE_cv": float(np.abs(y - pred).mean()), "MAE_media_cv": float(np.abs(y - base).mean())}


def calibracion_util(info):
    """Regla fijada de antemano: el recurso solo se usa si predice mejor que la media entre países."""
    return info["MAE_cv"] <= (1 - MEJORA_MINIMA) * info["MAE_media_cv"]


def tabla_fp_local(obs, recurso, modelos):
    """FP de cada país y tecnología: observado si hay capacidad; si no, estimado con un recurso validado."""
    base = pd.MultiIndex.from_product([sorted(recurso["iso3"]), TECS], names=["iso3", "tecnologia"]).to_frame(index=False)
    d = base.merge(obs, on=["iso3", "tecnologia"], how="left").merge(recurso, on="iso3", how="left")
    d["fp_estimado"] = np.nan
    for tec, (modelo, variable) in modelos.items():
        m = d["tecnologia"] == tec
        lim = LIMITE_SUPERIOR_FP[tec]
        d.loc[m, "fp_estimado"] = np.clip(modelo.predict(d.loc[m, [variable]].values), 0.05, lim)
    observado = d["fp_obs"].where(d["cap_media"] >= CAP_MIN_OBSERVADO)
    d["fp_local"] = observado.fillna(d["fp_estimado"])
    d["origen_fp"] = np.select([observado.notna(), d["fp_estimado"].notna()], ["observado (IRENA)", "estimado por recurso (NASA)"], default="valor mundial (sin dato local)")
    d["cap_2025_mw"] = d["cap_2025_mw"].fillna(0.0)
    d["elegible"] = d["tecnologia"].isin(SIEMPRE_ELEGIBLES) | (d["cap_2025_mw"] >= CAP_MIN_ELEGIBLE)
    return d


def matrices_pais(fp_tabla, iso3, escenario=None):
    """FP local y elegibilidad en el orden de TECS; el escenario geotérmico hace viable la tecnología en todo país."""
    g = fp_tabla[fp_tabla["iso3"] == iso3].set_index("tecnologia").reindex(TECS)
    fp = g["fp_local"].values.astype(float).copy()
    elegible = g["elegible"].values.astype(bool).copy()
    if escenario:
        j = TECS.index("Geotérmica")
        fp[j], elegible[j] = escenario["fp"], True
    fp[~elegible] = np.nan
    return fp, elegible


def recomendar_pais(d, fp_tabla, iso3, n=4000, metodo="SAW", pesos=None, escenario=None, almacenamiento=True, semilla=SEMILLA):
    criterios = aplicar_escenario_geo(d, **escenario) if escenario else d
    fp, elegible = matrices_pais(fp_tabla, iso3, escenario)
    rng = np.random.default_rng(semilla)
    P = simular(criterios, n, rng, metodo=metodo, almacenamiento=almacenamiento, pesos=pesos, fp_local=fp, elegibles=elegible)
    r = resumen_puestos(P)
    r["elegible"], r["fp_local"] = elegible, fp
    r["costo_local"] = np.where(elegible, ((criterios["lcoe_2024"] + criterios["lcoe_2025"]) / 2).values
                                * np.clip(criterios["fp_irena"].values / np.where(np.isnan(fp), criterios["fp_irena"].values, fp), 0.5, 2.0), np.nan)
    return r


def clasificar_certeza(primero, segundo):
    """Qué tan clara es la recomendación según la ventaja del primero sobre el segundo."""
    ventaja = primero - segundo
    return "Clara" if primero >= 50 and ventaja >= 20 else ("Moderada" if ventaja >= 10 else "Reñida")


def recomendar_todos(d, fp_tabla, n=4000, escenario=None):
    filas = []
    for iso3 in sorted(fp_tabla["iso3"].unique()):
        saw = recomendar_pais(d, fp_tabla, iso3, n=n, escenario=escenario)
        top = recomendar_pais(d, fp_tabla, iso3, n=n, metodo="TOPSIS", escenario=escenario)
        orden = saw["% n.º 1"].sort_values(ascending=False)
        local = fp_tabla[fp_tabla["iso3"] == iso3].set_index("tecnologia").loc[orden.index[0]]
        sin_dato = local["origen_fp"].startswith("valor mundial") or (
            local["origen_fp"].startswith("observado") and local["cap_media"] < CAP_MIN_CALIBRAR)
        sin_dato = bool(sin_dato) and not (escenario and orden.index[0] == "Geotérmica")
        fila = {"iso3": iso3, "provisional": sin_dato, "recomendada": orden.index[0], "pct_primera": orden.iloc[0], "segunda": orden.index[1],
                "pct_segunda": orden.iloc[1], "certeza": clasificar_certeza(orden.iloc[0], orden.iloc[1]),
                "recomendada_topsis": top["% n.º 1"].idxmax()}
        for t in TECS:
            fila[f"pct_{t}"] = saw.loc[t, "% n.º 1"]
        filas.append(fila)
    return pd.DataFrame(filas)
