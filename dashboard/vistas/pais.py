# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import TECS, colores_tec, criterios, encabezado, escenario_a_tupla, estilo_figura, estilo_mapa, fp_local, hallazgo, mc, mostrar, recomendaciones, recomendar, resumen, tinta

encabezado("Qué le conviene a cada país", "Con el recurso y el rendimiento reales de cada país, ¿qué renovable conviene más?")
rec, fp_t = recomendaciones(), fp_local()
color = colores_tec()

c1, c2 = st.columns([1.1, 2])
escenario = c1.selectbox("Escenario", list(mc.ESCENARIOS_GEO), help="Los otros dos suponen que la geotérmica de roca supercaliente se vuelve viable en todos los países.")
regiones = sorted(rec["region"].dropna().unique())
region = c2.multiselect("Filtrar el mapa por región", regiones, placeholder="Todas las regiones")
hoy = rec[rec["escenario"] == escenario]
vista = hoy[hoy["region"].isin(region)] if region else hoy

conteo = hoy["recomendada"].value_counts()
k = st.columns(4)
k[0].metric("Países evaluados", len(hoy))
k[1].metric("Recomiendan solar", int(conteo.get("Solar", 0)))
k[2].metric("Recomiendan eólica", int(conteo.get("Eólica", 0)))
k[3].metric("Con ventaja clara", int((hoy["certeza"] == "Clara").sum()), delta=f"{int(hoy['provisional'].sum())} provisionales", delta_color="off", delta_arrow="off",
            help="Provisional: la tecnología recomendada no tiene suficiente capacidad instalada en el país para conocer su rendimiento local.")

fig = go.Figure()
for t in TECS:
    g = vista[vista["recomendada"] == t]
    if len(g):
        fig.add_choropleth(locations=g["iso3"], z=[1] * len(g), name=t, showlegend=True, showscale=False, colorscale=[[0, color[t]], [1, color[t]]],
                           marker=dict(line=dict(color=tinta()["superficie"], width=0.5)),
                           customdata=np.stack([g["pais"], g["pct_primera"], g["segunda"], g["pct_segunda"], g["certeza"]], axis=1),
                           hovertemplate="<b>%{customdata[0]}</b><br>" + t + ": %{customdata[1]:.0f} % de los escenarios<br>Segunda: %{customdata[2]} (%{customdata[3]:.0f} %)<br>Ventaja: %{customdata[4]}<extra></extra>")
mostrar(estilo_mapa(fig, alto=440))
st.caption("Color: la renovable que queda primera en más escenarios para ese país. En gris, territorios sin datos. Pasa el cursor para ver la segunda opción y qué tan clara es la ventaja.")

st.subheader("Análisis de un país")
nombres = sorted(hoy["pais"].unique())
a, b, c_ = st.columns([1.4, 1, 1])
pais = a.selectbox("País", nombres, index=nombres.index("Colombia"))
metodo = b.selectbox("Método", ["SAW", "TOPSIS"], format_func={"SAW": "Suma ponderada (SAW)", "TOPSIS": "TOPSIS"}.get)
baterias = c_.toggle("Contar baterías", value=True)
fila = hoy[hoy["pais"] == pais].iloc[0]
iso = fila["iso3"]
r = recomendar(iso, None, metodo, baterias, escenario_a_tupla(mc.ESCENARIOS_GEO[escenario]))
orden = r[r["elegible"]].sort_values("% n.º 1", ascending=False)
primera, segunda = orden.index[0], orden.index[1]
ventaja = orden["% n.º 1"].iloc[0] - orden["% n.º 1"].iloc[1]
certeza = "clara" if orden["% n.º 1"].iloc[0] >= 50 and ventaja >= 20 else ("moderada" if ventaja >= 10 else "reñida")
if certeza == "reñida":
    hallazgo(f"<b>En {pais} la decisión está reñida entre la {primera.lower()} ({orden['% n.º 1'].iloc[0]:.0f} %) y la {segunda.lower()} ({orden['% n.º 1'].iloc[1]:.0f} %).</b> "
             "Lo más razonable es combinar ambas: la elección depende de las prioridades del país.")
else:
    hallazgo(f"<b>En {pais} conviene más la {primera.lower()}</b>, primera en el {orden['% n.º 1'].iloc[0]:.0f} % de los escenarios, con ventaja {certeza} sobre la {segunda.lower()} ({orden['% n.º 1'].iloc[1]:.0f} %).")

datos_pais = fp_t[fp_t["iso3"] == iso].set_index("tecnologia").reindex(TECS)
if bool(fila["provisional"]) and primera == fila["recomendada"]:
    st.warning(f"**Recomendación provisional.** {pais} casi no tiene plantas de {primera.lower()}, así que su rendimiento local no se conoce bien. Antes de decidir hacen falta mediciones en sitio.", icon=":material/warning:")
if pd.isna(datos_pais.loc["Eólica", "cap_media"]) or datos_pais.loc["Eólica", "cap_media"] < 5:
    st.info("No hay parques eólicos suficientes en este país para medir su rendimiento, y la velocidad del viento de NASA no predijo bien el rendimiento eólico entre países. "
            "Por eso a la eólica se le asigna el valor mundial.", icon=":material/info:")

izq, der = st.columns([1, 1.7])
with izq:
    o = orden["% n.º 1"].sort_values()
    fig = go.Figure(go.Bar(x=o.values, y=o.index, orientation="h", marker=dict(color=[color[t] for t in o.index]), text=[f"{v:.1f} %" for v in o.values],
                           textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x:.1f} %<extra></extra>"))
    estilo_figura(fig, alto=270, leyenda=False, titulo_x="% de escenarios en primer lugar", margen=dict(l=8, r=50, t=8, b=8))
    fig.update_xaxes(range=[0, 100]); fig.update_yaxes(showgrid=False); fig.update_layout(bargap=0.3)
    mostrar(fig)
with der:
    t = pd.DataFrame({"Tecnología": TECS, "Viable": ["Sí" if e else "Sin evidencia" for e in r["elegible"]], "FP local": [f"{x:.3f}" if x == x else "—" for x in r["fp_local"].values],
                      "USD/MWh": [f"{x:.0f}" if x == x else "—" for x in r["costo_local"].values], "MW en 2025": datos_pais["cap_2025_mw"].values,
                      "Origen del dato": datos_pais["origen_fp"].values})
    if mc.ESCENARIOS_GEO[escenario]:
        t.loc[t["Tecnología"] == "Geotérmica", "Origen del dato"] = "supuesto del escenario"
    st.dataframe(t, hide_index=True, width="stretch", column_config={"FP local": st.column_config.TextColumn("FP local", help="Factor de planta del país"),
                 "USD/MWh": st.column_config.TextColumn("USD/MWh", help="Costo mundial ajustado por el rendimiento local"), "MW en 2025": st.column_config.NumberColumn(format="%.0f")})
    st.caption(f"Recurso NASA POWER (2001–2025): radiación {datos_pais['ghi_kwh_m2_dia'].iloc[0]:.2f} kWh/m²/día, viento a 50 m {datos_pais['viento_medio_ms'].iloc[0]:.1f} m/s, "
               f"precipitación {datos_pais['precip_mm_dia'].iloc[0]:.1f} mm/día. El costo ajusta el costo mundial según el rendimiento local.")

with st.expander("Cómo se calcula la recomendación"):
    cal = {c["tecnologia"] + c["variable"]: c for c in resumen()["calibracion"]}
    sol = cal["Solarghi_kwh_m2_dia"]
    st.markdown(f"""
- Se usan los **14 criterios** de la evaluación integral. Dos se vuelven locales: el **rendimiento** y el **costo**.
- **Rendimiento:** el factor de planta real del país en 2020–2024 según IRENA. Si no hay suficiente capacidad, en la solar se estima con la radiación de NASA POWER (validado: ρ = {sol['rho_spearman']:.2f}; el error baja de {sol['MAE_media_cv']:.3f} a {sol['MAE_cv']:.3f}).
- **Viento:** la velocidad de NASA **no** predijo el rendimiento eólico entre países, así que no se usa; se toma el valor mundial y se advierte.
- **Costo:** se ajusta en proporción inversa al rendimiento, entre la mitad y el doble del costo mundial.
- Hidroeléctrica, geotérmica y biomasa solo compiten si el país ya tiene esa tecnología, como evidencia de que el recurso existe.
- **No reemplaza** un estudio de planificación: no incluye la red, la demanda, el financiamiento ni la política de cada país.
""")

st.download_button("Descargar la tabla de todos los países (CSV)", hoy.drop(columns=[c for c in hoy.columns if c.startswith("pct_") and c not in ("pct_primera", "pct_segunda")]).to_csv(index=False).encode("utf-8"),
                   "recomendacion_por_pais.csv", "text/csv")
