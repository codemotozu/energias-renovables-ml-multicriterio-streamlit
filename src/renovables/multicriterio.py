"""Análisis multicriterio de la Fase 3 (14 criterios, Monte Carlo) con extensiones de la Fase 4:
pesos elegidos por el usuario, rendimiento y costo locales por país, y escenario de geotérmica de nueva generación."""
import numpy as np
import pandas as pd

from .datos import TECS

# Criterios externos verificados en la Fase 3 (fuentes en el informe)
EXTERNOS = pd.DataFrame({
    #                Solar   Eólica  Hidro    Geo      Biomasa
    "fp_irena":     [0.16,   0.36,   0.43,    0.85,    0.78],    # IRENA 2025: FP de plantas nuevas
    "lcoe_2025":    [44,     33,     62,      89,      86],      # IRENA 2026: costo nivelado, USD/MWh
    "lcoe_2024":    [43,     34,     57,      60,      87],      # IRENA 2025: costo nivelado, USD/MWh
    "cambio_costo": [-89,    -71,    41,      53,      -3],      # IRENA 2026: % de cambio del costo 2010–2025
    "co2_min":      [18,     7,      1,       6,       130],     # IPCC AR5, Anexo III: gCO2eq/kWh
    "co2_med":      [48,     11,     24,      38,      230],
    "co2_max":      [180,    56,     2200,    79,      420],
    "suelo_min":    [1,      70,     100,     10,      130],     # Lovering et al. (2022): ha/TWh/año
    "suelo_med":    [2000,   130,    650,     45,      2746],
    "suelo_max":    [2860,   12000,  15000,   195,     58000],
    "muertes":      [0.019,  0.035,  1.3,     np.nan,  4.63],    # Our World in Data: muertes/TWh
    "min_kg_mw":    [6790,   10160,  2750,    192990,  2670],    # IEA (2021): minerales críticos, kg/MW
    "min_f_lo":     [0.8,    0.8,    0.9,     0.8,     0.9],
    "min_f_hi":     [1.2,    1.2,    1.4,     1.2,     1.4],
    "recic_med":    [85,     87.5,   75,      85,      85],      # % de la masa recuperable al final de la vida
    "recic_min":    [80,     85,     50,      70,      74],
    "recic_max":    [95,     90,     95,      95,      96],
    "vida":         [25,     25,     50,      30,      40],      # IPCC AR5, Anexo III: vida útil (años)
    "f_alm":        [0.50,   0.25,   0.0,     0.0,     0.0],     # fracción de la energía que pasa por baterías
    "f_alm_min":    [0.30,   0.10,   0.0,     0.0,     0.0],
    "f_alm_max":    [0.60,   0.40,   0.0,     0.0,     0.0],
}, index=TECS)

BAT_KG_KWH, BAT_KG_KWH_MAX = 1.64, 2.21
CICLOS, CICLOS_MIN, CICLOS_MAX, DOD, GWH_POR_MW_ANIO = 5000, 3000, 7000, 0.90, 8.76
KG_GWH_BATERIA = BAT_KG_KWH / (CICLOS * DOD) * 1e6

CRITERIOS = ["Rendimiento", "Estabilidad", "Despachabilidad", "Costo", "Versatilidad", "Emisiones", "Uso de suelo",
             "Seguridad", "Minerales críticos", "Reciclabilidad", "Vida útil", "Dinamismo de costos", "Crecimiento",
             "Mejora del rendimiento"]
BENEFICIO = {c: c not in ("Costo", "Emisiones", "Uso de suelo", "Seguridad", "Minerales críticos") for c in CRITERIOS}
LOG = {"Emisiones", "Uso de suelo", "Seguridad", "Minerales críticos"}
ABSOLUTO = {"Reciclabilidad": (0, 100), "Despachabilidad": (0, 1)}
PILAR = dict(zip(CRITERIOS, ["Confiabilidad"] * 3 + ["Economía y acceso"] * 2 + ["Ambiente y seguridad"] * 3
                 + ["Materiales y circularidad"] * 3 + ["Trayectoria y futuro"] * 3))
PILARES = list(dict.fromkeys(PILAR.values()))
LIM_FACTOR_COSTO = (0.5, 2.0)        # el costo local se limita a entre la mitad y el doble del costo mundial
BANDA_FP_LOCAL = 0.10                # incertidumbre relativa del FP local (± 10 %)

# Escenarios de geotérmica de roca supercaliente. Costo «madura»: CATF / LucidCatalyst y HERO (2022), USD 20–35/MWh.
ESCENARIOS_GEO = {
    "Hoy (datos de la Fase 3)": None,
    "Prueba de concepto": {"lcoe": (45, 70), "fp": 0.90, "todos_los_paises": True, "crece_como_eolica": False},
    "Madura (meta de la industria)": {"lcoe": (20, 35), "fp": 0.90, "todos_los_paises": True, "crece_como_eolica": True},
}


def tabla_criterios(gppd, trayectoria):
    """Une los criterios calculados con la GPPD, la trayectoria de IRENA y los criterios externos."""
    return gppd.reindex(TECS).join(trayectoria).join(EXTERNOS)


def criterios_gppd(universo):
    """Rendimiento, estabilidad y número de países de cada tecnología en la GPPD."""
    u = universo[universo["tecnologia"].isin(TECS)].assign(tecnologia=lambda x: x["tecnologia"].astype(str))
    fp_g = u[u["tiene_generacion"]]
    cv_g = fp_g[fp_g["cv_generacion"].notna()]
    return pd.DataFrame({
        "fp_gppd": fp_g.groupby("tecnologia")["factor_planta_prom"].median(),
        "cv_med": cv_g.groupby("tecnologia")["cv_generacion"].median(),
        "cv_q1": cv_g.groupby("tecnologia")["cv_generacion"].quantile(0.25),
        "cv_q3": cv_g.groupby("tecnologia")["cv_generacion"].quantile(0.75),
        "paises": u.groupby("tecnologia")["country"].nunique(),
    }).reindex(TECS)


def matriz_puntual(d, almacenamiento=True):
    m = pd.DataFrame(index=TECS)
    f_alm = d["f_alm"] if almacenamiento else d["f_alm"] * 0
    m["Rendimiento"] = (d["fp_gppd"] + d["fp_irena"]) / 2
    m["Estabilidad"] = 1 - d["cv_med"]
    m["Despachabilidad"] = 1 - f_alm
    m["Costo"], m["Versatilidad"] = d["lcoe_2025"], d["paises"]
    m["Emisiones"], m["Uso de suelo"], m["Seguridad"] = d["co2_med"], d["suelo_med"], d["muertes"].fillna(0.15)
    m["Minerales críticos"] = d["min_kg_mw"] / (m["Rendimiento"] * GWH_POR_MW_ANIO * d["vida"]) + f_alm * KG_GWH_BATERIA
    m["Reciclabilidad"], m["Vida útil"] = d["recic_med"], d["vida"]
    m["Dinamismo de costos"], m["Crecimiento"], m["Mejora del rendimiento"] = -d["cambio_costo"], d["crec_15_24"], d["fp_tend"]
    return m[CRITERIOS]


def normalizar(m):
    """1 = la mejor de las cinco en ese criterio; escala logarítmica en los que abarcan órdenes de magnitud."""
    z = m.copy().astype(float)
    for c in CRITERIOS:
        x = np.log10(z[c]) if c in LOG else z[c]
        if c in ABSOLUTO:
            x = (x - ABSOLUTO[c][0]) / (ABSOLUTO[c][1] - ABSOLUTO[c][0])
        else:
            x = (x - x.min()) / (x.max() - x.min())
        z[c] = x if BENEFICIO[c] else 1 - x
    return z


def muestrear_criterios(d, n, rng, almacenamiento=True, fp_local=None):
    """Sortea cada criterio dentro de su incertidumbre (arreglo n × tecnologías × criterios).

    fp_local (opcional): FP de cada tecnología en un país; NaN conserva el valor mundial. Cambia el rendimiento y,
    en proporción inversa, el costo nivelado.
    """
    T = len(TECS)
    entre = lambda a, b: rng.uniform(np.minimum(a, b), np.maximum(a, b), size=(n, T))
    tri_log = lambda lo, mo, hi: np.exp(rng.triangular(np.log(lo), np.log(mo), np.log(hi), size=(n, T)))
    col = {"Rendimiento": entre(d.fp_gppd.values, d.fp_irena.values),
           "Estabilidad": 1 - rng.uniform(d.cv_q1.values, d.cv_q3.values, size=(n, T))}
    f_alm = entre(d.f_alm_min.values, d.f_alm_max.values) if almacenamiento else np.zeros((n, T))
    col["Despachabilidad"] = 1 - f_alm
    col["Costo"] = entre(d.lcoe_2024.values, d.lcoe_2025.values)
    col["Versatilidad"] = np.tile(d.paises.values.astype(float), (n, 1))
    col["Emisiones"] = tri_log(d.co2_min.values, d.co2_med.values, d.co2_max.values)
    col["Uso de suelo"] = tri_log(d.suelo_min.values, d.suelo_med.values, d.suelo_max.values)
    seg = np.tile(d.muertes.values.astype(float), (n, 1))
    falta = np.isnan(seg)
    seg[falta] = np.exp(rng.uniform(np.log(0.019), np.log(1.3), size=falta.sum()))
    col["Seguridad"] = seg
    vida = rng.uniform(d.vida.values, 1.5 * d.vida.values, size=(n, T))
    intensidad = d.min_kg_mw.values * rng.uniform(d.min_f_lo.values, d.min_f_hi.values, size=(n, T))
    bat = rng.uniform(BAT_KG_KWH, BAT_KG_KWH_MAX, size=(n, 1)) / (rng.uniform(CICLOS_MIN, CICLOS_MAX, size=(n, 1)) * DOD) * 1e6
    if fp_local is not None:
        fp_local = np.asarray(fp_local, dtype=float)
        hay = ~np.isnan(fp_local)
        sorteo = np.where(hay, fp_local, 1.0) * rng.uniform(1 - BANDA_FP_LOCAL, 1 + BANDA_FP_LOCAL, size=(n, T))
        col["Rendimiento"] = np.where(hay, sorteo, col["Rendimiento"])
        factor = np.clip(d.fp_irena.values / np.where(hay, sorteo, d.fp_irena.values), *LIM_FACTOR_COSTO)
        col["Costo"] = col["Costo"] * factor
    col["Minerales críticos"] = intensidad / (col["Rendimiento"] * GWH_POR_MW_ANIO * vida) + f_alm * bat
    col["Reciclabilidad"] = rng.triangular(d.recic_min.values, d.recic_med.values, d.recic_max.values, size=(n, T))
    col["Vida útil"] = vida
    col["Dinamismo de costos"] = np.tile(-d.cambio_costo.values.astype(float), (n, 1))
    col["Crecimiento"] = entre(d.crec_15_24.values, d.crec_20_24.values)
    col["Mejora del rendimiento"] = rng.normal(d.fp_tend.values, d.fp_tend_se.values, size=(n, T))
    return np.stack([col[c] for c in CRITERIOS], axis=2)


def normalizar_sim(X):
    X = X.copy()
    for j, c in enumerate(CRITERIOS):
        x = np.log10(X[:, :, j]) if c in LOG else X[:, :, j]
        if c in ABSOLUTO:
            z = (x - ABSOLUTO[c][0]) / (ABSOLUTO[c][1] - ABSOLUTO[c][0])
        else:
            mn, mx = x.min(1, keepdims=True), x.max(1, keepdims=True)
            z = np.where(mx > mn, (x - mn) / np.where(mx > mn, mx - mn, 1), 0.5)
        X[:, :, j] = z if BENEFICIO[c] else 1 - z
    return X


def pesos_desde_pilares(prioridad):
    """Pesos fijos de los 14 criterios a partir de la prioridad de cada pilar (se reparte por igual dentro del pilar)."""
    total = sum(prioridad.values())
    if total <= 0:
        raise ValueError("Al menos un pilar debe tener prioridad mayor que cero")
    n_pilar = {p: sum(PILAR[c] == p for c in CRITERIOS) for p in PILARES}
    return np.array([prioridad[PILAR[c]] / total / n_pilar[PILAR[c]] for c in CRITERIOS])


def simular(d, n, rng, metodo="SAW", almacenamiento=True, criterios=None, pesos=None, fp_local=None, elegibles=None):
    """Puesto de cada tecnología en cada escenario (1 = mejor; 0 = no elegible en ese país).

    pesos=None sortea los pesos con una Dirichlet uniforme; con un vector de 14 pesos se fijan las prioridades.
    """
    Zs = normalizar_sim(muestrear_criterios(d, n, rng, almacenamiento, fp_local))
    if pesos is None:
        activos = [j for j, c in enumerate(CRITERIOS) if criterios is None or c in criterios]
        W = np.zeros((n, len(CRITERIOS)))
        W[:, activos] = rng.dirichlet(np.ones(len(activos)), size=n)
    else:
        W = np.tile(np.asarray(pesos, dtype=float), (n, 1))
    W = W[:, None, :]
    if metodo == "SAW":
        s = (Zs * W).sum(2)
    else:
        v = Zs * W
        d_menos = np.sqrt((v ** 2).sum(2))
        s = d_menos / (np.sqrt(((v - W) ** 2).sum(2)) + d_menos)
    if elegibles is None:
        return (-s).argsort(1).argsort(1) + 1
    elegibles = np.asarray(elegibles, dtype=bool)
    s = np.where(elegibles, s, -np.inf)
    puestos = (-s).argsort(1).argsort(1) + 1
    return np.where(elegibles, puestos, 0)


def resumen_puestos(P):
    """% de escenarios en primer lugar, % entre las dos mejores y puesto promedio, solo entre tecnologías elegibles."""
    validos = P > 0
    n = np.maximum(validos.sum(0), 1)
    return pd.DataFrame({
        "% n.º 1": (P == 1).sum(0) / n * 100,
        "% entre las 2 mejores": ((P >= 1) & (P <= 2)).sum(0) / n * 100,
        "puesto promedio": np.where(validos.any(0), (P * validos).sum(0) / n, np.nan),
    }, index=TECS)


def aplicar_escenario_geo(d, lcoe=None, fp=None, todos_los_paises=False, crece_como_eolica=False):
    """Devuelve una copia de los criterios con la geotérmica de nueva generación; las demás tecnologías no cambian."""
    e, G = d.copy(), "Geotérmica"
    e = e.astype({c: float for c in ("paises", "lcoe_2024", "lcoe_2025", "cambio_costo", "fp_irena")})
    costo_actual = tuple(sorted((d.loc[G, "lcoe_2024"], d.loc[G, "lcoe_2025"])))
    if lcoe is not None and tuple(sorted(lcoe)) != costo_actual:    # si el costo no cambia, su tendencia tampoco
        costo_2010 = d.loc[G, "lcoe_2025"] / (1 + d.loc[G, "cambio_costo"] / 100)
        e.loc[G, "lcoe_2024"], e.loc[G, "lcoe_2025"] = min(lcoe), max(lcoe)
        e.loc[G, "cambio_costo"] = (np.mean(lcoe) / costo_2010 - 1) * 100
    if fp is not None:
        e.loc[G, "fp_irena"] = fp
    if todos_los_paises:
        e.loc[G, "paises"] = d["paises"].max()
    if crece_como_eolica:
        e.loc[G, "crec_15_24"], e.loc[G, "crec_20_24"] = d.loc["Eólica", "crec_15_24"], d.loc["Eólica", "crec_20_24"]
    return e
