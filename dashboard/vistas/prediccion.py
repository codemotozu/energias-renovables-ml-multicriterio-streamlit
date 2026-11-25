# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import (NIVELES, TECS, banda_arboles, centros_pais, colores_puesto, colores_tec, encabezado, estilo_figura, fila_planta, fmt, fp_local,
                   hallazgo, leer, metricas, mostrar, plantas, predecir, tinta)

encabezado("Predicción en vivo", "Describe una planta que todavía no existe: ¿cuánto rendiría?")

d = plantas()
nombres = fp_local()[["iso3", "pais"]].drop_duplicates().sort_values("pais")
centros = centros_pais()
lista = nombres[nombres["iso3"].isin(centros.index)]
iso_de = dict(zip(lista["pais"], lista["iso3"]))
pais_defecto = list(iso_de).index("Colombia")

entrada, salida = st.columns([1, 1.75], gap="large")
with entrada:
    with st.container(border=True):
        st.markdown("**Datos de la planta**")
        tec = st.selectbox("Tecnología", TECS, index=0)
        pais = st.selectbox("País", list(iso_de), index=pais_defecto)
        iso = iso_de[pais]
        capacidad = st.number_input("Capacidad (MW)", min_value=1.0, max_value=5000.0, value=50.0, step=10.0)
        anio = st.slider("Año de entrada en operación", 1950, 2019, 2019,
                         help="El modelo aprendió con plantas y generación hasta 2019.")
        ubic = st.toggle("Ajustar coordenadas", value=False, help="Por defecto se usa el punto del país con más capacidad instalada.")
        lat0, lon0 = float(centros.loc[iso, "lat"]), float(centros.loc[iso, "lon"])
        if ubic:
            la, lo = st.columns(2)
            lat = la.number_input("Latitud", -60.0, 75.0, lat0, step=0.5, key=f"lat_{iso}")
            lon = lo.number_input("Longitud", -180.0, 180.0, lon0, step=0.5, key=f"lon_{iso}")
        else:
            lat, lon = lat0, lon0
            st.caption(f"Ubicación usada: {lat:.1f}°, {lon:.1f}°")

fila = fila_planta(tec, iso, capacidad, anio, lat, lon)
fp, proba = predecir([fila])
fp, proba = float(fp[0]), proba[0]
bajo, alto = banda_arboles(fila)
nivel = NIVELES[int(proba.argmax())]
ent = d[d["conjunto"] == "entrenamiento"]
n_igual = int(((ent["country"] == iso) & (ent["tecnologia"] == tec)).sum())
tipica = ent.loc[ent["tecnologia"] == tec, "factor_planta_prom"].median()

with salida:
    k = st.columns(3)
    k[0].metric("Factor de planta estimado", f"{fp:.3f}", delta=f"{(fp - tipica) * 100:+.1f} pts frente a la mediana", delta_color="off", delta_arrow="off")
    k[1].metric("Energía al año", f"{fmt(fp * capacidad * 8.76)} GWh")
    k[2].metric("Nivel de desempeño", nivel, delta=f"probabilidad {proba.max() * 100:.0f} %", delta_color="off", delta_arrow="off")
    st.caption(f"El 80 % de los árboles del modelo estima entre {bajo:.3f} y {alto:.3f}. Error típico del modelo en plantas nuevas: ± 0.095 (RMSE).")

    if n_igual == 0:
        st.warning(f"**Estimación poco confiable.** El modelo no vio ninguna planta {tec.lower()} de {pais} al entrenar: está extrapolando desde otros países.", icon=":material/warning:")
    elif n_igual < 10:
        st.info(f"El modelo vio solo {n_igual} plantas de este tipo en {pais}. Conviene tomar la cifra como orientación.", icon=":material/info:")
    if tec in ("Hidroeléctrica", "Biomasa"):
        st.caption(f"En {tec.lower()} el error es mayor, porque el modelo no conoce la hidrología, el combustible ni el despacho.")

    izq, der = st.columns([1, 1.15])
    with izq:
        st.markdown("**Probabilidad de cada nivel**")
        ramp = dict(zip(NIVELES, [colores_puesto()[3], colores_puesto()[2], colores_puesto()[0]]))
        fig = go.Figure(go.Bar(x=proba * 100, y=NIVELES, orientation="h", marker=dict(color=[ramp[n] for n in NIVELES]),
                               text=[f"{p * 100:.0f} %" for p in proba], textposition="outside", cliponaxis=False,
                               hovertemplate="%{y}: %{x:.1f} %<extra></extra>"))
        estilo_figura(fig, alto=190, leyenda=False, margen=dict(l=4, r=38, t=4, b=4))
        fig.update_xaxes(range=[0, 100], showticklabels=False, showgrid=False); fig.update_yaxes(showgrid=False, autorange="reversed")
        fig.update_layout(bargap=0.3)
        mostrar(fig)
    with der:
        st.markdown("**Misma ubicación, otra tecnología**")
        filas = [fila_planta(t, iso, capacidad, anio, lat, lon) for t in TECS]
        comp, _ = predecir(filas)
        color = colores_tec()
        o = np.argsort(comp)
        fig = go.Figure(go.Bar(x=comp[o], y=[TECS[i] for i in o], orientation="h", marker=dict(color=[color[TECS[i]] for i in o]),
                               text=[f"{comp[i]:.2f}" for i in o], textposition="outside", cliponaxis=False,
                               hovertemplate="%{y}: FP %{x:.3f}<extra></extra>"))
        estilo_figura(fig, alto=190, leyenda=False, margen=dict(l=4, r=34, t=4, b=4))
        fig.update_xaxes(range=[0, 1], showticklabels=False, showgrid=False); fig.update_yaxes(showgrid=False)
        fig.update_layout(bargap=0.3)
        mostrar(fig)

st.subheader("¿Qué pasa si cambio una variable?")
a, b = st.columns(2)
linea = dict(color=colores_tec()[tec], width=2)
with a:
    caps = np.unique(np.round(np.geomspace(1, 2000, 22), 1))
    pred, _ = predecir([{**fila, "log_capacidad": np.log10(c)} for c in caps])
    fig = go.Figure(go.Scatter(x=caps, y=pred, mode="lines", line=linea, hovertemplate="%{x:.0f} MW: FP %{y:.3f}<extra></extra>"))
    fig.add_scatter(x=[capacidad], y=[fp], mode="markers", marker=dict(size=10, color=colores_tec()[tec], line=dict(color=tinta()["superficie"], width=2)),
                    hovertemplate="Esta planta: FP %{y:.3f}<extra></extra>")
    estilo_figura(fig, alto=280, leyenda=False, titulo_x="Capacidad (MW, escala logarítmica)", titulo_y="Factor de planta")
    fig.update_xaxes(type="log")
    mostrar(fig)
with b:
    anios = np.arange(1960, 2020, 3)
    pred, _ = predecir([{**fila, "edad_planta": 2019 - a_} for a_ in anios])
    fig = go.Figure(go.Scatter(x=anios, y=pred, mode="lines", line=linea, hovertemplate="%{x}: FP %{y:.3f}<extra></extra>"))
    fig.add_scatter(x=[anio], y=[fp], mode="markers", marker=dict(size=10, color=colores_tec()[tec], line=dict(color=tinta()["superficie"], width=2)),
                    hovertemplate="Esta planta: FP %{y:.3f}<extra></extra>")
    estilo_figura(fig, alto=280, leyenda=False, titulo_x="Año de entrada en operación", titulo_y="Factor de planta")
    mostrar(fig)
st.caption("Cada curva cambia solo una variable y deja fijas las demás. Muestra lo que aprendió el modelo; no prueba una relación de causa y efecto.")
