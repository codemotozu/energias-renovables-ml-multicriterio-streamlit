"""Construye, desde los datos crudos, todas las tablas que usa el tablero y el informe final."""
import json
import shutil
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.inspection import permutation_importance
from sklearn.metrics import f1_score, mean_absolute_error, mean_squared_error, r2_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from . import multicriterio as mc
from . import paises as pa
from .datos import NIVELES, PREDICTORES, SEMILLA, TECS, cargar_gppd, preparar_modelado
from .geotermica import construir_geotermica
from .trayectoria import calcular_trayectoria, leer_serie_mundial

VARS_CLUSTER = {"log_capacidad": "Escala (log₁₀ MW)", "latitud_abs": "Distancia al ecuador (°)", "edad_planta": "Edad (años)",
                "factor_planta_prom": "Factor de planta", "log_cv": "Inestabilidad (log CV)"}
VARIABLES_ORIG = {"tecnologia": "Tecnología", "country": "País", "log_capacidad": "Capacidad", "irradiacion_relativa": "Irradiación relativa",
                  "densidad_misma_tec": "Densidad de plantas", "edad_planta": "Edad", "latitude": "Latitud", "longitude": "Longitud"}
PAISES_EXTRA = {"ATA": ("Antártida", "Otros territorios", ""), "ESH": ("Sáhara Occidental", "Oriente Medio, Norte de África, Afganistán y Pakistán", ""),
                "GUF": ("Guayana Francesa", "América Latina y el Caribe", ""), "KOS": ("Kosovo", "Europa y Asia central", ""),
                "TWN": ("Taiwán", "Asia oriental y el Pacífico", "")}
CANCHA_HA = 105 * 68 / 1e4
MATERIALES_DOE = pd.DataFrame({
    "Acero": [7900, 1800, 67, 3300, 310], "Concreto": [350, 8000, 14000, 1100, 760], "Cemento": [3700, 0, 0, 750, 0],
    "Vidrio": [2700, 92, 0, 0, 0], "Aluminio": [680, 35, 0, 100, 6], "Cobre": [850, 23, 1, 2, 0],
    "Hierro": [0, 120, 0, 9, 4], "Plástico": [210, 190, 0, 0, 0], "Silicio": [57, 0, 0, 0, 0]}, index=TECS)
SUELO_LOVERING = {"Solar": (2000, 2000), "Eólica": (130, 12000), "Hidroeléctrica": (650, 650), "Geotérmica": (45, 45), "Biomasa": (130, 58000)}


def tabla_paises(raiz):
    p = pd.read_csv(raiz / "data" / "raw" / "paises_banco_mundial.csv", encoding="utf-8")
    extra = pd.DataFrame([{"iso3": k, "pais": v[0], "region": v[1], "ingreso": v[2]} for k, v in PAISES_EXTRA.items()])
    p["pais"] = p["pais"].replace({"Kenya": "Kenia"})
    return pd.concat([p, extra], ignore_index=True).drop_duplicates("iso3")


def segmentar(dm):
    """Repite la segmentación de la Fase 3: K-Means k = 2 (elegido), k = 5 (codo), DBSCAN y proyección PCA."""
    dc = dm.dropna(subset=["edad_planta", "cv_generacion"]).copy()
    dc["log_cv"] = np.log(dc["cv_generacion"] + 0.01)
    Zc = StandardScaler().fit_transform(dc[list(VARS_CLUSTER)])
    km = KMeans(n_clusters=2, n_init=50, random_state=SEMILLA).fit(Zc)
    orden = dc.groupby(km.labels_)["factor_planta_prom"].median().sort_values(ascending=False).index.tolist()
    dc["grupo_kmeans"] = pd.Series(km.labels_, index=dc.index).map({g: f"G{i + 1}" for i, g in enumerate(orden)})
    fino = KMeans(n_clusters=5, n_init=50, random_state=SEMILLA).fit(Zc)
    orden_f = dc.groupby(fino.labels_)["factor_planta_prom"].median().sort_values(ascending=False).index.tolist()
    dc["grupo_fino"] = pd.Series(fino.labels_, index=dc.index).map({g: f"S{i + 1}" for i, g in enumerate(orden_f)})
    from sklearn.neighbors import NearestNeighbors
    dist = np.sort(NearestNeighbors(n_neighbors=10).fit(Zc).kneighbors(Zc)[0][:, -1])
    xn, yn = np.linspace(0, 1, len(dist)), (dist - dist.min()) / (dist.max() - dist.min())
    eps = float(dist[np.argmax(xn - yn)])
    dc["atipica_dbscan"] = DBSCAN(eps=eps, min_samples=10).fit(Zc).labels_ == -1
    pca = PCA(n_components=3, random_state=SEMILLA).fit(Zc)
    comp = pca.transform(Zc)
    for j in range(3):
        dc[f"pc{j + 1}"] = comp[:, j]
    info = {"silueta_k2": float(silhouette_score(Zc, km.labels_)), "silueta_k5": float(silhouette_score(Zc, fino.labels_)),
            "pca_varianza": pca.explained_variance_ratio_.round(4).tolist(), "eps_dbscan": eps,
            "pct_atipicas": float(dc["atipica_dbscan"].mean() * 100), "n_plantas": int(len(dc)),
            "cargas_pca": {lab: pca.components_[:, i].round(3).tolist() for i, lab in enumerate(VARS_CLUSTER.values())}}
    return dc, info


def perfiles(dc, columna):
    g = dc.groupby(columna)
    p = g.agg(plantas=("gppd_idnr", "size"), capacidad_mw=("capacity_mw", "median"), edad=("edad_planta", "median"),
              factor_planta=("factor_planta_prom", "median"), cv=("cv_generacion", "median"), latitud_abs=("latitud_abs", "median"))
    comp = pd.crosstab(dc[columna], dc["tecnologia"].astype(str), normalize="index").reindex(columns=TECS, fill_value=0) * 100
    return p.join(comp.add_prefix("pct_")).reset_index().rename(columns={columna: "grupo"})


def errores_prueba(pl, cortes):
    filas = []
    prueba = pl[pl["conjunto"] == "prueba"]
    grupos = [("Todas", "Todas", prueba)] + [("Tecnología", t, prueba[prueba["tecnologia"] == t]) for t in TECS]
    grupos += [("Región", r, g) for r, g in prueba.groupby("region")]
    grupos += [("Alcance", "EE. UU.", prueba[prueba["country"] == "USA"]), ("Alcance", "Resto del mundo", prueba[prueba["country"] != "USA"])]
    for tipo, nombre, g in grupos:
        y, p = g["factor_planta_prom"], g["fp_predicho"]
        filas.append({"tipo": tipo, "grupo": nombre, "n": len(g), "RMSE": float(np.sqrt(mean_squared_error(y, p))),
                      "MAE": float(mean_absolute_error(y, p)), "sesgo": float((p - y).mean()),
                      "R2": float(r2_score(y, p)) if len(g) >= 20 else np.nan,
                      "F1": float(f1_score(g["nivel_real"], g["nivel_predicho"], average="macro")) if len(g) >= 20 else np.nan})
    return pd.DataFrame(filas)


def productividad(d):
    M = mc.matriz_puntual(d)
    total = MATERIALES_DOE.sum(axis=1)
    return pd.DataFrame({"factor de planta": M["Rendimiento"], "MWh por MW al año": M["Rendimiento"] * 8760,
                         "MWh por 1 000 USD": 1000 / d["lcoe_2025"],
                         "GWh/año por cancha (mejor caso)": [CANCHA_HA * 1000 / SUELO_LOVERING[t][0] for t in TECS],
                         "GWh/año por cancha (peor caso)": [CANCHA_HA * 1000 / SUELO_LOVERING[t][1] for t in TECS],
                         "GWh por 1 000 t de materiales": 1e6 / total,
                         "GWh por t de minerales críticos": 1000 / M["Minerales críticos"]}, index=TECS)


def escenarios_globales(d, n=20000):
    filas = []
    variantes = {"Hoy (datos de la Fase 3)": None,
                 "Solo llega a todos los países": {"todos_los_paises": True},
                 "Solo baja el costo (20–35 USD/MWh)": {"lcoe": (20, 35)},
                 "Prueba de concepto": mc.ESCENARIOS_GEO["Prueba de concepto"],
                 "Madura (meta de la industria)": mc.ESCENARIOS_GEO["Madura (meta de la industria)"]}
    for nombre, cambios in variantes.items():
        e = mc.aplicar_escenario_geo(d, **cambios) if cambios else d
        for metodo, bat in (("SAW", True), ("TOPSIS", True), ("SAW", False)):
            P = mc.simular(e, n, np.random.default_rng(SEMILLA), metodo=metodo, almacenamiento=bat)
            r = mc.resumen_puestos(P).reset_index(names="tecnologia")
            r["escenario"], r["metodo"], r["con_baterias"] = nombre, metodo, bat
            filas.append(r)
    return pd.concat(filas, ignore_index=True)


def construir(raiz, n_pais=4000, verbose=True, reusar_operacion=False):
    raiz = Path(raiz)
    salida = raiz / "data" / "processed"
    salida.mkdir(parents=True, exist_ok=True)
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)

    df, dm = preparar_modelado(cargar_gppd(raiz / "data" / "raw" / "gppd_v1_3" / "global_power_plant_database.csv"))
    nombres = tabla_paises(raiz)
    regresor = joblib.load(raiz / "models" / "regresor_fp.joblib")
    clasificador = joblib.load(raiz / "models" / "clasificador_nivel.joblib")
    X = dm[PREDICTORES].assign(tecnologia=lambda x: x["tecnologia"].astype(str))
    ent = dm["conjunto"] == "entrenamiento"
    cortes = dm.loc[ent, "factor_planta_prom"].quantile([1 / 3, 2 / 3]).values
    clase = pd.cut(dm["factor_planta_prom"], [-np.inf, *cortes, np.inf], labels=False).astype(int)

    # --- Plantas con predicciones y segmentos ---
    pl = dm[["gppd_idnr", "name", "country", "capacity_mw", "latitude", "longitude", "anio_operacion", "edad_planta",
             "factor_planta_prom", "cv_generacion", "latitud_abs", "conjunto"]].copy()
    pl["tecnologia"] = dm["tecnologia"].astype(str)
    pl["fp_predicho"] = regresor.predict(X)
    proba = clasificador.predict_proba(X)
    pl["nivel_real"] = np.array(NIVELES)[clase.values]
    pl["nivel_predicho"] = np.array(NIVELES)[proba.argmax(1)]
    for k, nivel in enumerate(NIVELES):
        pl[f"prob_{nivel.lower()}"] = proba[:, k]
    dc, info_cluster = segmentar(dm)
    pl = pl.join(dc[["grupo_kmeans", "grupo_fino", "atipica_dbscan", "pc1", "pc2", "pc3"]])
    pl = pl.merge(nombres[["iso3", "pais", "region"]], left_on="country", right_on="iso3", how="left").drop(columns="iso3")
    pl["pais"], pl["region"] = pl["pais"].fillna(pl["country"]), pl["region"].fillna("Otros territorios")
    redondeo = {c: 4 for c in ("factor_planta_prom", "cv_generacion", "fp_predicho", "prob_bajo", "prob_medio", "prob_alto", "pc1", "pc2", "pc3", "latitude", "longitude")}
    pl.round(redondeo).to_csv(salida / "plantas.csv", index=False, encoding="utf-8")
    log("Plantas:", pl.shape)

    dcc = dc.assign(tecnologia=dc["tecnologia"].astype(str))
    perfiles(dcc, "grupo_kmeans").to_csv(salida / "perfiles_k2.csv", index=False, encoding="utf-8")
    perfiles(dcc, "grupo_fino").to_csv(salida / "perfiles_k5.csv", index=False, encoding="utf-8")
    errores_prueba(pl, cortes).to_csv(salida / "errores_prueba.csv", index=False, encoding="utf-8")

    # --- Universo para calcular la densidad de una planta nueva ---
    u = df[df["tecnologia"].isin(TECS)][["tecnologia", "latitude", "longitude"]].assign(tecnologia=lambda x: x["tecnologia"].astype(str))
    u.round(4).to_csv(salida / "universo_coordenadas.csv", index=False, encoding="utf-8")

    # --- Importancia por permutación en validación (mismos parámetros de la Fase 3) ---
    val = dm["conjunto"] == "validación"
    imp_r = permutation_importance(regresor, X[val], dm.loc[val, "factor_planta_prom"], scoring="r2", n_repeats=10, random_state=SEMILLA)
    imp_c = permutation_importance(clasificador, X[val], clase[val], scoring="f1_macro", n_repeats=10, random_state=SEMILLA)
    pd.DataFrame({"variable": [VARIABLES_ORIG[c] for c in X.columns], "caida_r2": imp_r.importances_mean, "sd_r2": imp_r.importances_std,
                  "caida_f1": imp_c.importances_mean, "sd_f1": imp_c.importances_std}).sort_values("caida_r2", ascending=False)\
        .to_csv(salida / "importancia.csv", index=False, encoding="utf-8")
    log("Importancia calculada")

    # --- Trayectoria y criterios ---
    serie = leer_serie_mundial(raiz / "data" / "raw" / "irenastat" / "irenastat_mundo_por_tecnologia.csv")
    serie.to_csv(salida / "serie_irena.csv", index=False, encoding="utf-8")
    tr = calcular_trayectoria(serie)
    d = mc.tabla_criterios(mc.criterios_gppd(df), tr)
    d.to_csv(salida / "criterios.csv", encoding="utf-8")
    mc.normalizar(mc.matriz_puntual(d)).to_csv(salida / "matriz_normalizada.csv", encoding="utf-8")
    productividad(d).to_csv(salida / "productividad.csv", encoding="utf-8")

    rng = np.random.default_rng(SEMILLA)
    P_saw = mc.simular(d, 20000, rng, "SAW")
    P_top = mc.simular(d, 20000, rng, "TOPSIS")
    P_sb = mc.simular(d, 20000, rng, "SAW", almacenamiento=False)
    verif = {t: [round((P_saw[:, i] == 1).mean() * 100, 2), round((P_top[:, i] == 1).mean() * 100, 2), round((P_sb[:, i] == 1).mean() * 100, 2)] for i, t in enumerate(TECS)}
    escenarios_globales(d).to_csv(salida / "escenarios_geotermica.csv", index=False, encoding="utf-8")
    log("Multicriterio y escenarios listos")

    # --- Recomendación por país ---
    irena = pd.read_csv(raiz / "data" / "raw" / "irenastat" / "irenastat_pais_tecnologia.csv", encoding="utf-8")
    irena["iso3"] = irena["iso3"].replace({"XKX": "KOS"})
    puntos = pd.read_csv(raiz / "data" / "raw" / "nasa_power" / "puntos_por_pais.csv")
    celdas = pd.read_csv(raiz / "data" / "raw" / "nasa_power" / "nasa_power_celdas.csv")
    obs = pa.fp_observado(irena)
    recurso = pa.recurso_por_pais(puntos, celdas)
    recurso = recurso[recurso["iso3"] != "ATA"]
    obs, n_solar_descartados = pa.depurar_solar(obs, recurso)
    obs, n_eolica_descartados = pa.depurar_eolica(obs, recurso)
    calibraciones = [pa.calibrar_recurso(obs, recurso, "Solar", "ghi_kwh_m2_dia"),
                     pa.calibrar_recurso(obs, recurso, "Eólica", "viento_medio_ms"),
                     pa.calibrar_recurso(obs, recurso, "Eólica", "viento_max_ms")]
    eolica = min(calibraciones[1:], key=lambda c: c[1]["MAE_cv"])
    modelos = {t: (m, i["variable"]) for t, (m, i) in {"Solar": calibraciones[0], "Eólica": eolica}.items() if pa.calibracion_util(i)}
    for _, info in calibraciones:
        info["se_usa"] = bool(pa.calibracion_util(info)) and info["variable"] in [v for _, v in modelos.values()]
    fp_tabla = pa.tabla_fp_local(obs, recurso, modelos).merge(nombres[["iso3", "pais", "region", "ingreso"]], on="iso3", how="left")
    fp_tabla["pais"], fp_tabla["region"] = fp_tabla["pais"].fillna(fp_tabla["iso3"]), fp_tabla["region"].fillna("Otros territorios")
    fp_tabla.to_csv(salida / "fp_local.csv", index=False, encoding="utf-8")
    filas = []
    for nombre, esc in mc.ESCENARIOS_GEO.items():
        r = pa.recomendar_todos(d, fp_tabla, n=n_pais, escenario=esc)
        r["escenario"] = nombre
        filas.append(r)
        log(f"Recomendación por país: {nombre} ({len(r)} países)")
    rec = pd.concat(filas, ignore_index=True).merge(nombres[["iso3", "pais", "region", "ingreso"]], on="iso3", how="left")
    rec["pais"], rec["region"] = rec["pais"].fillna(rec["iso3"]), rec["region"].fillna("Otros territorios")
    rec.round(2).to_csv(salida / "recomendacion_pais.csv", index=False, encoding="utf-8")

    resumen = {"verificacion_multicriterio": verif, "cortes_niveles": cortes.round(4).tolist(), "clustering": info_cluster,
               "calibracion": [c[1] for c in calibraciones], "recursos_validados": sorted(modelos), "fp_solar_descartados": n_solar_descartados, "fp_eolica_descartados": n_eolica_descartados,
               "paises_recomendados": int(rec["iso3"].nunique()),
               "n_plantas": int(len(pl)), "n_universo": int(len(u)), "n_renovables": int(len(df)), "n_paises_gppd": int(df["country"].nunique())}
    (salida / "resumen_fase4.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    construir_geotermica(raiz, verbose=verbose, reusar_operacion=reusar_operacion)
    log("Análisis geotérmico listo")
    return resumen
