# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import TECS, colores_tec, encabezado, estilo_figura, estilo_mapa, fmt, hallazgo, mostrar, plantas

encabezado("Panorama de las plantas", "¿Qué plantas hay, dónde están y cuánto de su capacidad convierten en energía?")
d = plantas()
color = colores_tec()

with st.container(border=True):
    f1, f2, f3 = st.columns([1.2, 1.2, 1.2])
    tec = f1.multiselect("Tecnología", TECS, default=TECS)
    regiones = sorted(d["region"].unique())
    reg = f2.multiselect("Región", regiones, placeholder="Todas las regiones")
    base_p = d[d["region"].isin(reg)] if reg else d
    pais = f3.multiselect("País", sorted(base_p["pais"].unique()), placeholder="Todos los países")
    f4, f5, f6 = st.columns([1.2, 1.2, 1.2])
    anio_min, anio_max = int(d["anio_operacion"].min()), int(d["anio_operacion"].max())
    anios = f4.slider("Año de entrada en operación", anio_min, anio_max, (anio_min, anio_max))
    sin_anio = f4.checkbox("Incluir plantas sin año conocido", value=True)
    cap = f5.select_slider("Capacidad (MW)", options=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 25000], value=(1, 25000))
    fp = f6.slider("Factor de planta", 0.0, 1.0, (0.0, 1.0), step=0.05)

m = d["tecnologia"].isin(tec) & d["capacity_mw"].between(cap[0] if cap[0] > 1 else 0, cap[1]) & d["factor_planta_prom"].between(*fp)
m &= d["anio_operacion"].between(*anios) | (d["anio_operacion"].isna() & sin_anio)
if reg:
    m &= d["region"].isin(reg)
if pais:
    m &= d["pais"].isin(pais)
v = d[m]

if v.empty:
    st.warning("Ninguna planta cumple estos filtros. Amplía alguno para continuar.")
    st.stop()

c = st.columns(5)
c[0].metric("Plantas", fmt(len(v)), delta=f"{len(v) / len(d) * 100:.0f} % del total", delta_color="off", delta_arrow="off")
c[1].metric("Capacidad total", f"{fmt(v['capacity_mw'].sum() / 1000, 1)} GW")
c[2].metric("Factor de planta mediano", f"{v['factor_planta_prom'].median():.3f}")
c[3].metric("Edad mediana", f"{v['edad_planta'].median():.0f} años" if v["edad_planta"].notna().any() else "s. d.")
c[4].metric("Países", fmt(v["country"].nunique()))

if (v["country"] == "USA").mean() > 0.5:
    hallazgo(f"El {(v['country'] == 'USA').mean() * 100:.0f} % de estas plantas está en EE. UU., porque es el país que más reporta su generación. "
             "Por eso el modelo es más preciso allí y la recomendación por país usa además datos de IRENA y NASA.")

izq, der = st.columns([1.55, 1])
with izq:
    st.subheader("Dónde están")
    muestra = v.sample(3500, random_state=42) if len(v) > 3500 else v
    fig = go.Figure()
    for t in [x for x in TECS if x in tec]:
        g = muestra[muestra["tecnologia"] == t]
        fig.add_scattergeo(lat=g["latitude"], lon=g["longitude"], name=t, mode="markers",
                           marker=dict(size=np.clip(np.sqrt(g["capacity_mw"]) * 0.75, 4, 18), color=color[t], opacity=0.75, line=dict(width=0.4, color="#ffffff")),
                           customdata=np.stack([g["name"], g["pais"], g["capacity_mw"].round(1), g["factor_planta_prom"].round(3)], axis=1),
                           hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · " + t + "<br>%{customdata[2]} MW · FP %{customdata[3]}<extra></extra>")
    mostrar(estilo_mapa(fig, alto=430))
    if len(v) > 3500:
        st.caption(f"El mapa muestra una muestra de 3 500 de las {fmt(len(v))} plantas filtradas para que cargue rápido. Las cifras usan todas.")
with der:
    st.subheader("Cuánto rinden")
    fig = go.Figure()
    for t in [x for x in TECS if x in tec][::-1]:
        g = v[v["tecnologia"] == t]
        if len(g):
            fig.add_box(x=g["factor_planta_prom"], name=t, marker=dict(color=color[t], size=3), line=dict(width=1.4), boxpoints=False,
                        hovertemplate=t + ": %{x:.3f}<extra></extra>")
    estilo_figura(fig, alto=430, leyenda=False, titulo_x="Factor de planta")
    fig.update_yaxes(showgrid=False)
    mostrar(fig)

izq, der = st.columns(2)
with izq:
    st.subheader("Cuándo se construyeron")
    h = v.dropna(subset=["anio_operacion"]).assign(decada=lambda x: (x["anio_operacion"] // 10 * 10).astype(int))
    tabla = pd.crosstab(h["decada"], h["tecnologia"]).reindex(columns=[x for x in TECS if x in tec], fill_value=0)
    fig = go.Figure()
    for t in tabla.columns:
        fig.add_bar(x=tabla.index.astype(str), y=tabla[t], name=t, marker=dict(color=color[t]),
                    hovertemplate=t + " · década de %{x}: %{y} plantas<extra></extra>")
    fig.update_layout(barmode="stack", bargap=0.2)
    estilo_figura(fig, alto=330, titulo_x="Década de entrada en operación", titulo_y="Plantas")
    fig.update_xaxes(showgrid=False)
    mostrar(fig)
with der:
    st.subheader("Resumen por tecnología")
    r = v.groupby("tecnologia").agg(Plantas=("name", "size"), GW=("capacity_mw", lambda s: s.sum() / 1000), FP=("factor_planta_prom", "median"),
                                    Edad=("edad_planta", "median"), Países=("country", "nunique")).reindex([x for x in TECS if x in tec]).dropna(how="all")
    st.dataframe(r.reset_index().rename(columns={"tecnologia": "Tecnología", "FP": "FP mediano", "Edad": "Edad mediana"}), hide_index=True, width="stretch",
                 column_config={"GW": st.column_config.NumberColumn(format="%.1f"), "FP mediano": st.column_config.NumberColumn(format="%.3f"),
                                "Edad mediana": st.column_config.NumberColumn(format="%.0f")})
    st.caption("FP = factor de planta: la parte de la energía máxima teórica que la planta entrega en un año.")
    st.download_button("Descargar las plantas filtradas (CSV)", v.drop(columns=["pc1", "pc2", "pc3"]).to_csv(index=False).encode("utf-8"),
                       "plantas_filtradas.csv", "text/csv")
