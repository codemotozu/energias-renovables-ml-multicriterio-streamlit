# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import TECS, barras_puestos, colores_tec, criterios, encabezado, estilo_figura, hallazgo, leer, mc, metricas, mostrar, simular_global, tinta

encabezado("Evaluación integral", "Si se combinan rendimiento, costo, ambiente, materiales y futuro, ¿cuál gana? ¿Y si cambian las prioridades?")

with st.container(border=True):
    izq, der = st.columns([1, 2.5], gap="large")
    with izq:
        modo = st.radio("Prioridades", ["Todas las combinaciones posibles", "Definir mis prioridades"],
                        help="La primera opción sortea pesos al azar: no favorece ninguna visión. La segunda fija los pesos con los controles.")
        metodo = st.selectbox("Método de decisión", ["SAW", "TOPSIS"], format_func={"SAW": "Suma ponderada (SAW)", "TOPSIS": "Cercanía al ideal (TOPSIS)"}.get)
        baterias = st.toggle("Contar baterías", value=True, help="Incluye los minerales y la menor despachabilidad de la solar y la eólica cuando almacenan energía.")
    with der:
        st.markdown("**Importancia de cada pilar** (0 = no importa · 5 = lo más importante)")
        prioridad = {}
        cols = st.columns(5)
        for c, p in zip(cols, mc.PILARES):
            prioridad[p] = c.slider(p, 0, 5, 3, disabled=modo.startswith("Todas"))
        if modo.startswith("Definir") and sum(prioridad.values()) == 0:
            st.error("Al menos un pilar debe tener importancia mayor que cero.")
            st.stop()

clave = tuple(sorted(prioridad.items())) if modo.startswith("Definir") else None
res, dist = simular_global(clave, metodo, baterias)
gana = res["% n.º 1"].idxmax()
orden = res["% n.º 1"].sort_values(ascending=False)
if clave:
    hallazgo(f"<b>Con estas prioridades gana la {gana.lower()}</b> ({orden.iloc[0]:.1f} % de los escenarios), seguida de la {orden.index[1].lower()} ({orden.iloc[1]:.1f} %). "
             "Aquí solo varían los datos dentro de su incertidumbre, porque los pesos los fijaste tú.")
else:
    hallazgo(f"<b>Sin favorecer ninguna prioridad gana la {gana.lower()}</b> ({orden.iloc[0]:.1f} %), seguida de la {orden.index[1].lower()} ({orden.iloc[1]:.1f} %). "
             "Ninguna tecnología es la mejor en todos los criterios.")

tab1, tab2, tab3, tab4 = st.tabs(["Resultado", "Los 14 criterios", "Fin de vida y reciclaje", "Energía por recurso"])

with tab1:
    a, b = st.columns([1.5, 1])
    with a:
        st.markdown("**En qué puesto queda cada tecnología**")
        mostrar(barras_puestos(dist, alto=320))
    with b:
        st.markdown("**Resumen**")
        t = res.sort_values("% n.º 1", ascending=False).reset_index(names="Tecnología")
        st.dataframe(t, hide_index=True, width="stretch", column_config={"% n.º 1": st.column_config.ProgressColumn("% primer lugar", format="%.1f", min_value=0, max_value=100),
                     "% entre las 2 mejores": st.column_config.NumberColumn("% top 2", format="%.1f"), "puesto promedio": st.column_config.NumberColumn("Puesto", format="%.2f", help="Puesto promedio en todos los escenarios")})
    st.caption("20 000 escenarios. Con TOPSIS o sin baterías, el valor puede diferir en décimas del informe, porque cada cálculo aquí parte de la misma semilla.")

with tab2:
    z = leer("matriz_normalizada.csv", index_col=0).reindex(columns=mc.CRITERIOS).loc[TECS]
    st.markdown("**Valor de cada tecnología en cada criterio** (1 = la mejor de las cinco; 0 = la peor)")
    etiquetas = [f"{i + 1}. {c}" for i, c in enumerate(mc.CRITERIOS)]
    fig = go.Figure(go.Heatmap(z=z.T.values, x=TECS, y=etiquetas, colorscale=[[0, "#f4f8fd"], [0.5, "#3987e5"], [1, "#0d366b"]], zmin=0, zmax=1, xgap=2, ygap=2,
                               text=np.round(z.T.values, 2), texttemplate="%{text:.2f}", colorbar=dict(title="", thickness=10, len=0.7),
                               hovertemplate="%{x} · %{y}: %{z:.2f}<extra></extra>"))
    estilo_figura(fig, alto=520, leyenda=False)
    fig.update_yaxes(autorange="reversed", showgrid=False); fig.update_xaxes(side="top", showgrid=False)
    mostrar(fig)
    pil = pd.DataFrame({p: z[[c for c in mc.CRITERIOS if mc.PILAR[c] == p]].mean(axis=1) for p in mc.PILARES})
    st.markdown("**Puntaje promedio por pilar**")
    st.dataframe(pil.reset_index(names="Tecnología"), hide_index=True, width="stretch",
                 column_config={p: st.column_config.ProgressColumn(p, format="%.2f", min_value=0, max_value=1) for p in mc.PILARES})
    st.caption("Pilares: confiabilidad (1–3), economía y acceso (4–5), ambiente y seguridad (6–8), materiales y circularidad (9–11), trayectoria y futuro (12–14).")

with tab3:
    fv = pd.DataFrame(metricas()["fin_de_vida"]).T.reindex(TECS)
    hallazgo("<b>El fin de vida es el punto débil de la solar y la eólica.</b> Por masa se reciclan parecido a las demás (85–88 %), pero duran la mitad que una "
             f"hidroeléctrica y usan más minerales críticos. Sin este pilar, la solar ganaría en el {fv.loc['Solar', '% n.º 1 general sin el pilar']:.1f} % de los escenarios; "
             f"con él gana en el {fv.loc['Solar', '% n.º 1 general (14 criterios)']:.1f} %: le cuesta diez puntos, pero no el primer lugar.")
    t = fv[["reciclabilidad (% de la masa)", "vida útil (años)", "minerales críticos con baterías (kg/GWh)", "% n.º 1 solo pilar de circularidad"]].reset_index(names="Tecnología")
    t.columns = ["Tecnología", "Reciclable (% masa)", "Vida útil (años)", "Minerales críticos (kg/GWh)", "% primer lugar si solo importa este pilar"]
    st.dataframe(t, hide_index=True, width="stretch", column_config={"Reciclable (% masa)": st.column_config.NumberColumn(format="%.1f"), "Vida útil (años)": st.column_config.NumberColumn(format="%.0f"),
                 "Minerales críticos (kg/GWh)": st.column_config.NumberColumn(format="%.0f"), "% primer lugar si solo importa este pilar": st.column_config.NumberColumn(format="%.1f")})
    st.markdown("""
| Tecnología | Lo que se recicla bien | Lo difícil al final de la vida |
|---|---|---|
| Solar | Vidrio y marco de aluminio | Plata, silicio y cobre: poco peso, pero la mayor parte del valor |
| Eólica | Torre, góndola y cimentación | Aspas de material compuesto, sin reciclaje industrial a gran escala |
| Hidroeléctrica | Turbinas y acero | La presa de concreto rara vez se desmantela |
| Geotérmica | Tuberías y aceros | Los pozos se sellan y no se recuperan |
| Biomasa | Calderas y turbinas | Cenizas de la combustión |
""")

with tab4:
    pr = leer("productividad.csv", index_col=0).reindex(TECS)
    medidas = {"Por dólar (MWh por 1 000 USD)": "MWh por 1 000 USD", "Por MW instalado (MWh al año)": "MWh por MW al año",
               "Por cancha de fútbol (GWh al año, mejor caso)": "GWh/año por cancha (mejor caso)", "Por material (GWh por 1 000 t)": "GWh por 1 000 t de materiales",
               "Por minerales críticos (GWh por t)": "GWh por t de minerales críticos"}
    m_ = st.selectbox("¿Energía por cada unidad de qué recurso?", list(medidas))
    col = medidas[m_]
    o = pr[col].sort_values()
    color = colores_tec()
    fig = go.Figure(go.Bar(x=o.values, y=o.index, orientation="h", marker=dict(color=[color[t] for t in o.index]), text=[f"{v:,.1f}".replace(",", " ") for v in o.values],
                           textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x:,.1f}<extra></extra>"))
    estilo_figura(fig, alto=300, leyenda=False, titulo_x=col, margen=dict(l=8, r=70, t=8, b=8))
    fig.update_yaxes(showgrid=False); fig.update_layout(bargap=0.3)
    mostrar(fig)
    if "material" in m_:
        st.caption("En la biomasa, la fuente solo cuenta la planta generadora y no la cadena del combustible: su valor no es comparable con los demás.")
    if "cancha" in m_:
        st.caption("Cancha de 105 × 68 m, como la de El Campín. En el peor caso, la eólica cuenta todo el espacio entre turbinas (que sigue sirviendo para cultivar) y la biomasa, cultivos dedicados.")
    st.markdown("**No hay una sola ganadora:** la eólica entrega más energía **por dólar**; la geotérmica, más **por MW, por terreno y por material**, pero es más cara y hoy solo es viable donde hay calor cerca de la superficie.")
