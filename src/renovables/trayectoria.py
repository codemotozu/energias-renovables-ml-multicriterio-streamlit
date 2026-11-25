"""Serie mundial de IRENASTAT 2000–2025: capacidad, generación, FP mundial y tendencias (mismo cálculo de la Fase 3)."""
import numpy as np
import pandas as pd
from scipy import stats

from .datos import TECS

MAPA_IRENA = {"Solar": "Solar energy", "Eólica": "Wind energy", "Hidroeléctrica": "Renewable hydropower",
              "Geotérmica": "Geothermal energy", "Biomasa": "Bioenergy"}


def leer_serie_mundial(ruta):
    irena = pd.read_csv(ruta, encoding="latin-1")
    irena.columns = ["region", "tecnologia", "tipo", "anio", "valor"]
    irena["valor"] = pd.to_numeric(irena["valor"], errors="coerce")
    serie = (irena.assign(t=np.where(irena["tipo"].str.contains("Capacity"), "cap_mw", "gen_gwh"))
             .pivot_table(index=["tecnologia", "anio"], columns="t", values="valor").reset_index().sort_values(["tecnologia", "anio"]))
    serie["fp"] = serie["gen_gwh"] / (8.76 * serie.groupby("tecnologia")["cap_mw"].transform(lambda s: (s + s.shift(1)) / 2))
    serie = serie[serie["tecnologia"].isin(MAPA_IRENA.values())].replace({"tecnologia": {v: k for k, v in MAPA_IRENA.items()}})
    return serie


def calcular_trayectoria(serie):
    cap = serie.pivot(index="anio", columns="tecnologia", values="cap_mw")[TECS]
    fp_hist = serie.pivot(index="anio", columns="tecnologia", values="fp")[TECS]
    cagr = lambda a0, a1: ((cap.loc[a1] / cap.loc[a0]) ** (1 / (a1 - a0)) - 1) * 100
    t = pd.DataFrame({"crec_15_24": cagr(2015, 2024), "crec_20_24": cagr(2020, 2024), "cap_2025_gw": cap.loc[cap.index.max()] / 1e3})
    for tec in TECS:
        y = fp_hist[tec].loc[2005:2024].dropna()
        r = stats.linregress(y.index, y.values)
        t.loc[tec, ["fp_tend", "fp_tend_se", "fp_tend_p", "fp_2005", "fp_2024"]] = [r.slope * 1000, r.stderr * 1000, r.pvalue, y.iloc[0], y.iloc[-1]]
    return t.astype(float)
