# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import NIVELES, TECS, colores_puesto, colores_tec, encabezado, estilo_figura, hallazgo, leer, metricas, mostrar, plantas, tinta

encabezado("Qué modelo predice mejor y qué variables pesan más",
           "¿En qué medida la tecnología, la capacidad, la ubicación y la antigüedad permiten predecir el rendimiento de una planta?")
m = metricas()
AZUL, GRIS = colores_puesto()[2], tinta()["eje"]

rp, cp = m["regresion"]["prueba"], m["clasificacion"]["prueba"]
hallazgo(f"<b>Random Forest fue el mejor en las dos tareas.</b> Explica el {rp['Random Forest']['R²'] * 100:.0f} % de la variación del factor de planta "
         f"(R² = {rp['Random Forest']['R²']:.3f}, frente a {rp['Lineal base de la Fase 2']['R²']:.3f} del modelo base) y clasifica el nivel de desempeño con "
         f"F1-macro = {cp['Random Forest']['F1-macro']:.3f} (base: {cp['Logística base de la Fase 2']['F1-macro']:.3f}). "
         "El modelo se eligió con validación; el conjunto de prueba se usó una sola vez.")

tab1, tab2, tab3 = st.tabs(["Comparación de modelos", "Variables que más pesan", "Dónde acierta y dónde falla"])

with tab1:
    tarea = st.segmented_control("Tarea", ["Regresión (factor de planta)", "Clasificación (nivel de desempeño)"], default="Regresión (factor de planta)")
    if tarea and tarea.startswith("Regresión"):
        t = pd.DataFrame(rp).T.reset_index(names="Modelo")
        v = pd.DataFrame(m["regresion"]["validacion"]).T.reset_index(names="Modelo")[["Modelo", "R² CV (media)", "R² validación"]]
        t = t.merge(v, on="Modelo")
        metrica, formato = "R²", {"R²": "%.3f", "RMSE": "%.3f", "MAE": "%.3f", "R² CV (media)": "%.3f", "R² validación": "%.3f"}
        t = t[["Modelo", "R² CV (media)", "R² validación", "R²", "RMSE", "MAE"]].rename(columns={"R²": "R² prueba", "RMSE": "RMSE prueba", "MAE": "MAE prueba"})
        columna = "R² prueba"
        meta = 0.55
    else:
        t = pd.DataFrame(cp).T.reset_index(names="Modelo")[["Modelo", "F1-macro validación", "accuracy", "precisión", "recall", "F1-macro", "AUC-ROC"]]
        t = t.rename(columns={"accuracy": "Accuracy", "precisión": "Precisión", "recall": "Recall", "F1-macro": "F1-macro prueba", "AUC-ROC": "AUC-ROC prueba"})
        columna = "F1-macro prueba"
        meta = 0.70
    orden = t.sort_values(columna)
    colores = [AZUL if x == "Random Forest" else GRIS for x in orden["Modelo"]]
    fig = go.Figure(go.Bar(y=orden["Modelo"], x=orden[columna].clip(lower=0), orientation="h", marker=dict(color=colores),
                           text=(orden[columna].round(3) + 0.0).map("{:.3f}".format), textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:.3f}<extra></extra>"))
    fig.add_vline(x=meta, layer="below", line=dict(color=tinta()["secundaria"], dash="dot", width=1.5),
                  annotation_text=f"Meta SMART {meta:.2f}", annotation_position="top")
    estilo_figura(fig, alto=340, leyenda=False, titulo_x=columna, margen=dict(l=8, r=46, t=30, b=8))
    fig.update_yaxes(showgrid=False)
    fig.update_layout(bargap=0.32)
    mostrar(fig)
    numericas = [c for c in t.columns if c != "Modelo"]
    st.dataframe(t.assign(**{c: t[c].round(3) + 0.0 for c in numericas}).sort_values(columna, ascending=False), hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="%.3f") for c in numericas})
    st.caption("Hiperparámetros elegidos con validación cruzada de 5 pliegues agrupada por sitio. El MLP se entrenó en PyTorch con parada temprana.")

with tab2:
    imp = leer("importancia.csv")
    hallazgo(f"<b>La tecnología pesa más que todo lo demás junto.</b> Si se desordena, el R² cae {imp.iloc[0]['caida_r2']:.2f}. "
             "Le siguen la edad y la ubicación (longitud, irradiación y latitud), y después la capacidad y el país.")
    elegir = st.segmented_control("Medida", ["Caída de R² (regresión)", "Caída de F1 (clasificación)"], default="Caída de R² (regresión)")
    col, sd = ("caida_f1", "sd_f1") if elegir and "F1" in elegir else ("caida_r2", "sd_r2")
    o = imp.sort_values(col)
    fig = go.Figure(go.Bar(y=o["variable"], x=o[col], orientation="h", marker=dict(color=AZUL),
                           error_x=dict(type="data", array=o[sd], color=tinta()["tenue"], thickness=1.2, width=3),
                           hovertemplate="%{y}: %{x:.3f}<extra></extra>"))
    estilo_figura(fig, alto=350, leyenda=False, titulo_x="Cuánto empeora el modelo al desordenar la variable (validación)")
    fig.update_yaxes(showgrid=False)
    fig.update_layout(bargap=0.32)
    mostrar(fig)
    st.markdown("**Cómo se lee:** se desordena una variable y se mide cuánto pierde el modelo. Cuanto más pierde, más dependía de ella. "
                "La latitud y la irradiación son casi la misma información, así que su importancia se reparte entre las dos.")

with tab3:
    d = plantas()
    p = d[d["conjunto"] == "prueba"]
    e = leer("errores_prueba.csv")
    izq, der = st.columns(2)
    with izq:
        st.subheader("Predicho frente a observado")
        color = colores_tec()
        fig = go.Figure()
        for t in TECS:
            g = p[p["tecnologia"] == t]
            fig.add_scattergl(x=g["factor_planta_prom"], y=g["fp_predicho"], mode="markers", name=t,
                              marker=dict(color=color[t], size=7, opacity=0.65, line=dict(width=0.4, color=tinta()["superficie"])),
                              customdata=g[["name", "pais"]].values,
                              hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]})<br>Observado %{x:.3f} · Predicho %{y:.3f}<extra>" + t + "</extra>")
        fig.add_shape(type="line", x0=0, y0=0, x1=1, y1=1, line=dict(color=tinta()["tenue"], dash="dash", width=1))
        estilo_figura(fig, alto=420, titulo_x="Factor de planta observado", titulo_y="Factor de planta predicho")
        fig.update_xaxes(range=[0, 1]); fig.update_yaxes(range=[0, 1], scaleanchor="x", scaleratio=1)
        mostrar(fig)
    with der:
        st.subheader("Error por tecnología y región")
        tipo = st.segmented_control("Agrupar por", ["Tecnología", "Región", "Alcance"], default="Tecnología")
        sub = e[e["tipo"] == (tipo or "Tecnología")].sort_values("RMSE")
        fig = go.Figure(go.Bar(y=sub["grupo"].str.replace("Oriente Medio, Norte de África, Afganistán y Pakistán", "Oriente Medio y N. de África"),
                               x=sub["RMSE"], orientation="h", marker=dict(color=AZUL),
                               text=[f"{x:.3f} (n = {n})" for x, n in zip(sub["RMSE"], sub["n"])], textposition="outside", cliponaxis=False,
                               hovertemplate="%{y}: RMSE %{x:.3f}<extra></extra>"))
        estilo_figura(fig, alto=340, leyenda=False, titulo_x="RMSE en prueba (puntos de factor de planta / 100)", margen=dict(l=8, r=92, t=8, b=8))
        fig.update_yaxes(showgrid=False)
        fig.update_layout(bargap=0.32)
        mostrar(fig)
        if (tipo or "Tecnología") == "Región":
            st.caption("Las regiones con pocas plantas de prueba tienen un error muy incierto; léase junto con su n.")
    hallazgo("<b>El modelo acierta más en la solar y la eólica, y falla más en la hidroeléctrica y la biomasa</b>, porque su rendimiento depende "
             "de la hidrología, el tipo de central y el despacho, que la base de datos no incluye. También es menos preciso fuera de EE. UU.")
    st.subheader("Matriz de confusión del clasificador (prueba)")
    mat = pd.crosstab(p["nivel_real"], p["nivel_predicho"], normalize="index").reindex(index=NIVELES, columns=NIVELES) * 100
    cuenta = pd.crosstab(p["nivel_real"], p["nivel_predicho"]).reindex(index=NIVELES, columns=NIVELES)
    texto = [[f"{mat.iloc[i, j]:.0f} %<br>({cuenta.iloc[i, j]})" for j in range(3)] for i in range(3)]
    ramp = [[0, "#f4f8fd"], [0.5, "#3987e5"], [1, "#0d366b"]]
    fig = go.Figure(go.Heatmap(z=mat.values, x=NIVELES, y=NIVELES, colorscale=ramp, zmin=0, zmax=100, showscale=False, text=texto, texttemplate="%{text}",
                               xgap=2, ygap=2, hovertemplate="Real %{y} · Predicho %{x}: %{z:.1f} %<extra></extra>"))
    estilo_figura(fig, alto=280, leyenda=False, titulo_x="Nivel predicho", titulo_y="Nivel real")
    fig.update_yaxes(autorange="reversed", showgrid=False); fig.update_xaxes(showgrid=False, side="bottom")
    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        mostrar(fig)
