# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import TECS, colores_tec, encabezado, estilo_figura, hallazgo, leer, metricas, mostrar, plantas, resumen, tinta

encabezado("Segmentación de las plantas", "¿Qué grupos naturales de plantas aparecen, sin decirle al algoritmo cuál es la tecnología?")
d = plantas().dropna(subset=["grupo_kmeans"])
info, cl = resumen()["clustering"], metricas()["clustering"]
NOMBRE_K2 = {"G1": "G1 · Parque antiguo y gestionable", "G2": "G2 · Parque nuevo y estable"}
NOMBRE_K5 = {"S1": "S1 · Hidro antigua de alto rendimiento", "S2": "S2 · Eólica grande y reciente", "S3": "S3 · Hidro antigua e inestable",
             "S4": "S4 · Pequeñas de rendimiento variable", "S5": "S5 · Solar pequeña y estable"}
CORTO = {"Solar": "Solar", "Eólica": "Eólica", "Hidroeléctrica": "Hidro", "Geotérmica": "Geot.", "Biomasa": "Biom."}
COLOR_G = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6", "#eda100"]

hallazgo("<b>Hay dos grandes parques.</b> Uno antiguo, casi todo hidroeléctrico, con alto rendimiento pero variable; y otro nuevo, solar y eólico, "
         f"con menor rendimiento pero muy estable. La separación es moderada (silueta {cl['silueta_kmeans']:.2f}, por debajo de la meta de 0.35): "
         "las plantas forman más un continuo que grupos nítidos.")

k = st.columns(4)
k[0].metric("Plantas agrupadas", f"{info['n_plantas']:,}".replace(",", " "))
k[1].metric("Silueta K-Means (k = 2)", f"{cl['silueta_kmeans']:.3f}")
k[2].metric("Silueta Ward (k = 2)", f"{cl['silueta_ward']:.3f}")
k[3].metric("Atípicas según DBSCAN", f"{cl['dbscan_ruido_pct']:.1f} %")

c1, c2, c3, c4 = st.columns([1.25, 1, 1, 1])
seg = c1.segmented_control("Segmentación", ["k = 2 (elegida)", "k = 5 (exploratoria)"], default="k = 2 (elegida)")
colorear = c2.selectbox("Colorear por", ["Grupo", "Tecnología"])
vista = c3.selectbox("Vista", ["2D", "3D"])
sel_tec = c4.multiselect("Tecnología", TECS, placeholder="Todas")
fina = bool(seg) and seg.startswith("k = 5")
col, nombres = ("grupo_fino", NOMBRE_K5) if fina else ("grupo_kmeans", NOMBRE_K2)
solo_atipicas = st.checkbox("Mostrar solo las plantas atípicas (DBSCAN)")

v = d[d["tecnologia"].isin(sel_tec)] if sel_tec else d
if solo_atipicas:
    v = v[v["atipica_dbscan"].astype(bool)]
if v.empty:
    st.warning("Ninguna planta cumple estos filtros.")
    st.stop()

if colorear == "Grupo":
    claves = [g for g in sorted(d[col].unique()) if g in set(v[col])]
    series = [(nombres[g], v[v[col] == g], COLOR_G[sorted(d[col].unique()).index(g)]) for g in claves]
else:
    ct = colores_tec()
    series = [(t, v[v["tecnologia"] == t], ct[t]) for t in TECS if (v["tecnologia"] == t).any()]

var = info["pca_varianza"]
fig = go.Figure()
for nombre, g, color in series:
    datos = np.stack([g["name"], g["pais"], g["tecnologia"], g["capacity_mw"].round(1), g["edad_planta"].round(0), g["factor_planta_prom"].round(3)], axis=1)
    hover = "<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<br>%{customdata[3]} MW · %{customdata[4]} años · FP %{customdata[5]}<extra>" + nombre + "</extra>"
    if vista == "3D":
        fig.add_scatter3d(x=g["pc1"], y=g["pc2"], z=g["pc3"], mode="markers", name=nombre, customdata=datos, hovertemplate=hover,
                          marker=dict(size=2.6, color=color, opacity=0.75))
    else:
        fig.add_scattergl(x=g["pc1"], y=g["pc2"], mode="markers", name=nombre, customdata=datos, hovertemplate=hover,
                          marker=dict(size=6, color=color, opacity=0.62, line=dict(width=0.3, color=tinta()["superficie"])))
if vista == "3D":
    estilo_figura(fig, alto=540)
    t = tinta()
    eje = dict(gridcolor=t["reticula"], zerolinecolor=t["eje"], backgroundcolor="rgba(0,0,0,0)", color=t["tenue"])
    fig.update_layout(scene=dict(xaxis=dict(title=f"CP1 ({var[0] * 100:.0f} %)", **eje), yaxis=dict(title=f"CP2 ({var[1] * 100:.0f} %)", **eje),
                                 zaxis=dict(title=f"CP3 ({var[2] * 100:.0f} %)", **eje)))
else:
    estilo_figura(fig, alto=480, titulo_x=f"Componente 1 ({var[0] * 100:.0f} % de la varianza): más edad, FP e inestabilidad →",
                  titulo_y=f"Componente 2 ({var[1] * 100:.0f} %): plantas más grandes ↑")
mostrar(fig)
st.caption("Proyección en componentes principales (PCA) de cinco variables estandarizadas: escala, distancia al ecuador, edad, factor de planta e inestabilidad.")

st.subheader("Perfil promedio de cada grupo")
p = leer("perfiles_k5.csv" if fina else "perfiles_k2.csv")
p["grupo"] = p["grupo"].map(nombres)
t = p.rename(columns={"grupo": "Grupo", "plantas": "Plantas", "capacidad_mw": "MW", "edad": "Edad", "factor_planta": "FP", "cv": "CV",
                      "latitud_abs": "|Latitud|", **{f"pct_{x}": f"% {CORTO[x]}" for x in TECS}})
fmt_col = {"MW": "%.1f", "Edad": "%.0f", "FP": "%.3f", "CV": "%.3f", "|Latitud|": "%.1f", **{f"% {CORTO[x]}": "%.0f" for x in TECS}}
st.dataframe(t, hide_index=True, width="stretch", column_config={c: st.column_config.NumberColumn(format=f) for c, f in fmt_col.items()})
st.caption("Medianas por grupo: capacidad (MW), edad (años), factor de planta (FP), variabilidad interanual (CV) y distancia al ecuador (°). Los porcentajes muestran la composición por tecnología.")

st.markdown("**Para qué sirve:** muestra que el parque renovable se divide más por **edad y estabilidad** que por una sola variable. Quien planifica una red tiene "
            "dos activos distintos: uno gestionable que envejece y otro nuevo y constante que depende del clima. Las plantas atípicas de DBSCAN son "
            "justamente las que los modelos predicen peor (biomasa, geotérmica e hidroeléctricas grandes).")
