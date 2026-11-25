"""Escenario de geotérmica de roca supercaliente: qué pasaría, cómo se comportaría y cuál sería su potencial.

1. Qué pasaría: condiciones de costo, rendimiento y crecimiento con las que gana, y si resiste que sus rivales también se abaraten.
2. Cómo se comportaría: costo y recursos de abastecer un consumo constante, hora a hora, frente a solar, eólica y baterías.
3. Cuál sería su potencial: cuánto podría crecer si repite la expansión histórica de la eólica o de la solar.
"""
import json

import numpy as np
import pandas as pd

from . import multicriterio as mc
from .datos import SEMILLA

CASOS = {"COL": "Colombia", "DEU": "Alemania", "KEN": "Kenia", "CHL": "Chile", "USA": "Estados Unidos", "IND": "India"}
ANIOS_HORARIOS = (2022, 2023, 2024)

# Supuestos de la simulación horaria
CONFIABILIDAD = 0.95                 # igual a la definición de energía firme de IRENA (2026)
BAT_USD_KWH = 140                    # IRENA (2026), p. 141: batería de 4 h instalada en 2025
BAT_HORAS, BAT_EFICIENCIA = 4, 0.85  # energía/potencia y eficiencia de ida y vuelta
BAT_VIDA, TASA, BAT_OM = 15, 0.07, 0.02
CAIDA_2035 = 0.40                    # IRENA (2026), p. 24: reducción proyectada del costo firme a 2035
BAT_KG_KWH = mc.BAT_KG_KWH

# Supuestos del potencial
FP_POTENCIAL = 0.85                  # coincide con IRENA (plantas nuevas) y con la razón 6 000 TWh / 800 GW de la AIE
DEMANDA_2025_TWH = 10730 / 0.338     # Ember (2026): las renovables, 10 730 TWh, fueron el 33.8 % de la electricidad mundial
CO2_CARBON, CO2_GAS = 820, 490       # IPCC AR5, Anexo III: gCO2eq/kWh (medianas)
AIE_2050_GW, AIE_2050_TWH = 800, 6000


def abaratar_rivales(e, caida):
    """Reduce el costo actual de la solar y la eólica, y actualiza su tendencia de costos."""
    e = e.copy()
    for t in ("Solar", "Eólica"):
        e.loc[t, "cambio_costo"] = ((1 + e.loc[t, "cambio_costo"] / 100) * (1 - caida) - 1) * 100
        e.loc[t, ["lcoe_2024", "lcoe_2025"]] = e.loc[t, ["lcoe_2024", "lcoe_2025"]].astype(float) * (1 - caida)
    return e


def _primero(e, n, metodo="SAW"):
    return mc.resumen_puestos(mc.simular(e, n, np.random.default_rng(SEMILLA), metodo=metodo))["% n.º 1"]


def condiciones(d, n=20000):
    """% de escenarios en primer lugar de la geotérmica y de su mejor rival, según su costo, rendimiento y crecimiento."""
    filas = []
    for centro in np.arange(25, 80, 5):
        lcoe = (float(centro - 7.5), float(centro + 7.5))
        for fp in (0.60, 0.70, 0.80, 0.90):
            for crece in (True, False):
                r = _primero(mc.aplicar_escenario_geo(d, lcoe=lcoe, fp=fp, todos_los_paises=True, crece_como_eolica=crece), n)
                filas.append({"costo_medio": float(centro), "fp": fp, "crece_como_eolica": crece, "geotermica": r["Geotérmica"],
                              "mejor_rival": r.drop("Geotérmica").max(), "rival": r.drop("Geotérmica").idxmax()})
    return pd.DataFrame(filas)


def costo_de_quiebre(tabla, fp=0.90, crece=True):
    """Costo medio con el que la geotérmica iguala a su mejor rival (interpolación lineal); NaN si nunca lo alcanza."""
    t = tabla[(tabla["fp"] == fp) & (tabla["crece_como_eolica"] == crece)].sort_values("costo_medio")
    x, dif = t["costo_medio"].values, (t["geotermica"] - t["mejor_rival"]).values
    if dif[0] <= 0:
        return np.nan
    k = np.argmax(dif <= 0)
    return float(x[k - 1] + dif[k - 1] / (dif[k - 1] - dif[k]) * (x[k] - x[k - 1])) if dif[-1] <= 0 else float(x[-1])


def rivales_se_abaratan(d, n=20000):
    madura = mc.aplicar_escenario_geo(d, **mc.ESCENARIOS_GEO["Madura (meta de la industria)"])
    filas = []
    for caida in np.arange(0, 0.61, 0.10):
        for metodo in ("SAW", "TOPSIS"):
            r = _primero(abaratar_rivales(madura, caida), n, metodo)
            filas.append({"caida_rivales": round(float(caida) * 100), "metodo": metodo, "Geotérmica": r["Geotérmica"], "Solar": r["Solar"], "Eólica": r["Eólica"]})
    return pd.DataFrame(filas)


def _curva_eolica(v):
    """Curva de potencia genérica: arranque 3 m/s, nominal 12 m/s y corte 25 m/s."""
    return np.where((v >= 3) & (v < 12), (v ** 3 - 27) / (12 ** 3 - 27), np.where((v >= 12) & (v < 25), 1.0, 0.0))


def _biseccion(f, objetivo, lo, hi, it=60):
    for _ in range(it):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if f(m) < objetivo else (lo, m)
    return (lo + hi) / 2


def perfiles_horarios(horario, puntos, iso3, fp_solar, fp_eolica):
    """Perfil de generación por MW, con la forma horaria de NASA y el nivel anual del FP del país."""
    p = puntos[(puntos["country"] == iso3) & (puntos["peso"] > 0)]
    celdas = horario.merge(p.groupby(["lat", "lon"], as_index=False)["peso"].sum(), on=["lat", "lon"])
    celdas["ghi_w_m2"] = celdas["ghi_w_m2"].where(celdas["ghi_w_m2"] > -900)
    celdas["viento_50m_ms"] = celdas["viento_50m_ms"].where(celdas["viento_50m_ms"] > -900)
    ghi = celdas.pivot(index="fecha_utc", columns=["lat", "lon"], values="ghi_w_m2").interpolate(limit_direction="both").clip(lower=0)
    vto = celdas.pivot(index="fecha_utc", columns=["lat", "lon"], values="viento_50m_ms").interpolate(limit_direction="both").clip(lower=0) * 2 ** 0.14
    pesos = p.groupby(["lat", "lon"])["peso"].sum().reindex(ghi.columns).values
    pesos = pesos / pesos.sum()
    G, V = ghi.values / 1000, vto.values
    solar = lambda a: (np.minimum(a * G, 1) * pesos).sum(1)
    eolica = lambda k: (_curva_eolica(k * V) * pesos).sum(1)
    a = _biseccion(lambda x: solar(x).mean(), fp_solar, 0.1, 5)
    k = _biseccion(lambda x: eolica(x).mean(), fp_eolica, 0.2, 6)
    return pd.DataFrame({"solar": solar(a), "eolica": eolica(k)}, index=ghi.index)


def costo_anual_bateria():
    crf = TASA * (1 + TASA) ** BAT_VIDA / ((1 + TASA) ** BAT_VIDA - 1)
    return BAT_USD_KWH * 1000 * (crf + BAT_OM)          # USD por MWh de capacidad al año


def _despachar(S, W, B, s, w, detalle=False):
    """Despacho hora a hora: la batería guarda el excedente y lo entrega cuando falta energía para 1 MW constante."""
    eta = BAT_EFICIENCIA ** 0.5
    S, W, B = np.asarray(S, float), np.asarray(W, float), np.asarray(B, float)
    e, tope, deficit = B / 2, B / BAT_HORAS, np.zeros_like(B)
    series = {"carga": [], "descarga": [], "deficit": []}
    for st, wt in zip(s, w):
        exceso = S * st + W * wt - 1
        falta = np.maximum(-exceso, 0)
        carga = np.minimum(np.minimum(np.maximum(exceso, 0), tope), (B - e) / eta)
        descarga = np.minimum(np.minimum(falta, tope), e * eta)
        e = e + carga * eta - descarga / eta
        deficit = deficit + falta - descarga
        if detalle:
            series["carga"].append(float(carga)); series["descarga"].append(float(descarga)); series["deficit"].append(float(falta - descarga))
    cobertura = 1 - deficit / len(s)
    return (cobertura, {k: np.array(v) for k, v in series.items()}) if detalle else cobertura


def _bateria_minima(Sg, Wg, s, w, confiabilidad):
    """Para cada par (S, W), la batería más pequeña que alcanza la confiabilidad (NaN si ninguna la alcanza)."""
    Bg = np.r_[0, np.geomspace(0.25, 240, 40)]
    SS, WW, BB = np.meshgrid(Sg, Wg, Bg, indexing="ij")
    cob = _despachar(SS.ravel(), WW.ravel(), BB.ravel(), s, w).reshape(SS.shape)
    ok = cob >= confiabilidad
    k = ok.argmax(2)
    i, j = np.indices(k.shape)
    B = Bg[k].astype(float)
    con_previo = k > 0
    c1, c0 = cob[i, j, k], cob[i, j, np.maximum(k - 1, 0)]
    frac = np.divide(confiabilidad - c0, c1 - c0, out=np.ones_like(c1), where=c1 > c0)
    B = np.where(con_previo, Bg[np.maximum(k - 1, 0)] + frac * (Bg[k] - Bg[np.maximum(k - 1, 0)]), B)
    return np.where(ok.any(2), B, np.nan)


def optimizar_firme(s, w, costo_s, costo_w, confiabilidad=CONFIABILIDAD, usar_solar=True, usar_eolica=True, factor_bateria=1.0):
    """Mezcla de menor costo que abastece 1 MW constante con la confiabilidad pedida (malla refinada y despacho horario).

    Se paga toda la generación, también la que se vierte.
    """
    c_s, c_w, c_b = costo_s * s.mean() * 8760, costo_w * w.mean() * 8760, costo_anual_bateria() * factor_bateria
    Sg = np.linspace(0, 6 / s.mean(), 25) if usar_solar else np.array([0.0])
    Wg = np.linspace(0, 6 / w.mean(), 25) if usar_eolica else np.array([0.0])
    for _ in range(3):
        B = _bateria_minima(Sg, Wg, s, w, confiabilidad)
        total = c_s * Sg[:, None] + c_w * Wg[None, :] + c_b * B
        i, j = np.unravel_index(np.nanargmin(total), total.shape)
        S, W = float(Sg[i]), float(Wg[j])
        paso_s = Sg[1] - Sg[0] if len(Sg) > 1 else 0.0
        paso_w = Wg[1] - Wg[0] if len(Wg) > 1 else 0.0
        Sg = np.linspace(max(S - paso_s, 0), S + paso_s, 13) if usar_solar else Sg
        Wg = np.linspace(max(W - paso_w, 0), W + paso_w, 13) if usar_eolica else Wg
    lo, hi = 0.0, float(np.nanmax(B[i, j])) * 1.05 + 0.01
    for _ in range(30):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if float(_despachar(S, W, m, s, w)) < confiabilidad else (lo, m)
    Bfin = hi
    cobertura, x = _despachar(S, W, Bfin, s, w, detalle=True)
    cobertura = float(cobertura)
    generada = S * s + W * w
    vertida = np.maximum(generada - 1, 0) - x["carga"]
    return {"solar_mw": S, "eolica_mw": W, "bateria_mwh": Bfin, "costo_firme": (c_s * S + c_w * W + c_b * Bfin) / (cobertura * 8760),
            "vertida_pct": float(vertida.sum() / generada.sum() * 100), "cobertura_pct": cobertura * 100, **x}


def costo_local(d, tec, fp):
    return float(d.loc[tec, ["lcoe_2024", "lcoe_2025"]].astype(float).mean() * np.clip(d.loc[tec, "fp_irena"] / fp, *mc.LIM_FACTOR_COSTO))


def recursos_100mw(d, o):
    """Terreno y minerales críticos para 100 MW constantes; o = resultado por MW de consumo."""
    s_twh, w_twh = o["solar_mw"] * 100 * o["fp_solar"] * 8.76 / 1000, o["eolica_mw"] * 100 * o["fp_eolica"] * 8.76 / 1000
    terreno = s_twh * d.loc["Solar", "suelo_med"] + w_twh * d.loc["Eólica", "suelo_med"]
    minerales = (o["solar_mw"] * 100 * d.loc["Solar", "min_kg_mw"] + o["eolica_mw"] * 100 * d.loc["Eólica", "min_kg_mw"]
                 + o["bateria_mwh"] * 100 * 1000 * BAT_KG_KWH) / 1000
    return terreno, minerales


def fp_caso(fp_local, d, iso3, tec):
    """FP del país si es representativo (al menos 50 MW o estimado con un recurso validado); si no, el mundial de plantas nuevas."""
    f = fp_local[(fp_local["iso3"] == iso3) & (fp_local["tecnologia"] == tec)].iloc[0]
    if pd.notna(f["fp_local"]) and (str(f["origen_fp"]).startswith("estimado") or f["cap_media"] >= 50):
        return float(f["fp_local"]), str(f["origen_fp"])
    return float(d.loc[tec, "fp_irena"]), "valor mundial (IRENA, plantas nuevas)"


def operacion(d, fp_local, horario, puntos):
    filas, semanas = [], []
    geo_mw = 100 / 0.90
    geo_terreno = geo_mw * 0.90 * 8.76 / 1000 * d.loc["Geotérmica", "suelo_med"]
    geo_minerales = geo_mw * d.loc["Geotérmica", "min_kg_mw"] / 1000
    for iso, nombre in CASOS.items():
        (fs, origen_s), (fw, origen_w) = fp_caso(fp_local, d, iso, "Solar"), fp_caso(fp_local, d, iso, "Eólica")
        perfil = perfiles_horarios(horario, puntos, iso, fs, fw)
        s, w = perfil["solar"].values, perfil["eolica"].values
        cs, cw = costo_local(d, "Solar", fs), costo_local(d, "Eólica", fw)
        for mezcla, (us, uw) in {"Solar + baterías": (True, False), "Solar + eólica + baterías": (True, True)}.items():
            o = optimizar_firme(s, w, cs, cw, usar_solar=us, usar_eolica=uw)
            o.update(fp_solar=fs, fp_eolica=fw)
            # A 2035 IRENA proyecta -40 % en solar con baterías; la eólica se deja igual y la mezcla se vuelve a optimizar
            o_2035 = optimizar_firme(s, w, cs * (1 - CAIDA_2035), cw, usar_solar=us, usar_eolica=uw, factor_bateria=1 - CAIDA_2035)
            terreno, minerales = recursos_100mw(d, o)
            filas.append({"iso3": iso, "pais": nombre, "mezcla": mezcla, "fp_solar": fs, "fp_eolica": fw, "origen_solar": origen_s, "origen_eolica": origen_w, "costo_solar": cs, "costo_eolica": cw,
                          "solar_mw": o["solar_mw"] * 100, "eolica_mw": o["eolica_mw"] * 100, "bateria_mwh": o["bateria_mwh"] * 100,
                          "vertida_pct": o["vertida_pct"], "cobertura_pct": o["cobertura_pct"], "costo_firme_2025": o["costo_firme"],
                          "costo_firme_2035": o_2035["costo_firme"], "terreno_ha": terreno, "minerales_t": minerales,
                          "geo_mw": geo_mw, "geo_terreno_ha": geo_terreno, "geo_minerales_t": geo_minerales})
            if uw:
                gen = o["solar_mw"] * s + o["eolica_mw"] * w
                semanal = pd.Series(gen).rolling(168).mean().shift(-167)
                ini = int(semanal.idxmin())
                h = np.arange(ini, ini + 168)
                directa = np.minimum(gen[h], 1)
                semanas.append(pd.DataFrame({"iso3": iso, "hora": np.arange(168), "Solar": np.minimum(o["solar_mw"] * s[h], directa) * 100,
                                             "Eólica": np.maximum(directa - o["solar_mw"] * s[h], 0) * 100, "Baterías": np.minimum(o["descarga"][h], 1 - directa) * 100,
                                             "Déficit": o["deficit"][h] * 100, "inicio_utc": perfil.index[ini]}))
    return pd.DataFrame(filas), pd.concat(semanas, ignore_index=True)


def trayectorias(serie):
    """Capacidad si la geotérmica repite la expansión observada de otra tecnología desde que tenía su tamaño actual."""
    cap = serie.pivot(index="anio", columns="tecnologia", values="cap_mw") / 1000
    g0 = float(cap.loc[2025, "Geotérmica"])
    tasa = (g0 / float(cap.loc[2015, "Geotérmica"])) ** (1 / 10) - 1
    anios = np.arange(2025, 2051)

    def analogo(tec, inicio):
        base = int((cap[tec] - g0).abs().idxmin())
        arranque = g0 * (1 + tasa) ** (inicio - 2025)      # hasta el despegue sigue su tendencia actual
        y = []
        for a in anios:
            k = a - inicio
            if k <= 0:
                y.append(g0 * (1 + tasa) ** (a - 2025))
            else:
                y.append(arranque * cap.loc[base + k, tec] / cap.loc[base, tec] if base + k <= 2025 else np.nan)
        return np.array(y)

    casos = {"Sigue como hoy": g0 * (1 + tasa) ** (anios - 2025),
             "Como la eólica desde 2035": analogo("Eólica", 2035),
             "Como la eólica desde 2030": analogo("Eólica", 2030),
             "Como la solar desde 2035": analogo("Solar", 2035)}
    filas = []
    for nombre, y in casos.items():
        for a, v in zip(anios, y):
            if np.isfinite(v):
                twh = v * FP_POTENCIAL * 8.76
                filas.append({"trayectoria": nombre, "anio": int(a), "gw": v, "twh": twh, "pct_demanda_2025": twh / DEMANDA_2025_TWH * 100,
                              "gt_co2_gas": twh * (CO2_GAS - 38) / 1e6, "gt_co2_carbon": twh * (CO2_CARBON - 38) / 1e6})
    return pd.DataFrame(filas), tasa


def construir_geotermica(raiz, n=20000, verbose=True, reusar_operacion=False):
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)
    proc = raiz / "data" / "processed"
    d = pd.read_csv(proc / "criterios.csv", index_col=0, encoding="utf-8")
    c = condiciones(d, n)
    c.round(3).to_csv(proc / "geo_condiciones.csv", index=False, encoding="utf-8")
    ra = rivales_se_abaratan(d, n)
    ra.round(3).to_csv(proc / "geo_rivales.csv", index=False, encoding="utf-8")
    log("Condiciones y rivales listos")
    if not (reusar_operacion and (proc / "geo_operacion.csv").exists() and (proc / "geo_semana.csv").exists()):   # tarda unos 10 minutos
        fp_local = pd.read_csv(proc / "fp_local.csv", encoding="utf-8")
        fp_local = fp_local[fp_local["iso3"].isin(CASOS)]
        horario = pd.read_csv(raiz / "data" / "raw" / "nasa_power" / "horario_casos.csv.gz")
        puntos = pd.read_csv(raiz / "data" / "raw" / "nasa_power" / "puntos_por_pais.csv")
        op, sem = operacion(d, fp_local, horario, puntos)
        op.round(3).to_csv(proc / "geo_operacion.csv", index=False, encoding="utf-8")
        sem.round(3).to_csv(proc / "geo_semana.csv", index=False, encoding="utf-8")
        log("Operación horaria lista")
    serie = pd.read_csv(proc / "serie_irena.csv", encoding="utf-8")
    tr, tasa = trayectorias(serie)
    tr.round(3).to_csv(proc / "geo_potencial.csv", index=False, encoding="utf-8")
    fin = tr[tr["anio"] == 2050].set_index("trayectoria")
    resumen = {"quiebre_con_crecimiento": costo_de_quiebre(c, 0.90, True), "quiebre_sin_crecimiento": costo_de_quiebre(c, 0.90, False),
               "quiebre_fp_070": costo_de_quiebre(c, 0.70, True), "tasa_geotermica_2015_2025": tasa * 100,
               "potencial_2050": fin[["gw", "twh", "pct_demanda_2025", "gt_co2_gas", "gt_co2_carbon"]].round(2).to_dict("index")}
    (proc / "geo_resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    return resumen
