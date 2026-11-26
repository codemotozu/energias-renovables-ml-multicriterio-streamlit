# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import (TECS, colores_tec, criterios, encabezado, escenario_a_tupla, estilo_figura, estilo_mapa, fp_local, hallazgo, leer, mc, mostrar, pa,
                   recomendaciones, recomendar, recomendar_futuro, resumen, sa, tinta)

encabezado("Qué le conviene a cada país", "Con el recurso y el rendimiento reales de cada país, ¿qué renovable conviene más?")
rec, fp_t = recomendaciones(), fp_local()
est = leer("estacionalidad_pais.csv").set_index("iso3")
MES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
rec = rec.assign(pct_mes_min=rec["iso3"].map(est["pct_mes_min"]), mes_min=rec["iso3"].map(est["mes_min"]),
                 invierno_oscuro=rec["iso3"].map(est["invierno_oscuro"]).astype("boolean").fillna(False))
color = colores_tec()

c1, c2 = st.columns([1.1, 2])
escenario = c1.selectbox("Escenario", list(mc.ESCENARIOS_GEO) + list(sa.ESCENARIOS_FUTURO),
                         help="«Prueba de concepto» y «Madura»: solo mejora la geotérmica de roca supercaliente (vista 8). «Todas mejoran»: además, la solar, la eólica, "
                              "la hidroeléctrica y la biomasa dan su salto de la vista 9. Los escenarios de futuro son exploratorios.")
futuro = escenario in sa.ESCENARIOS_FUTURO
regiones = sorted(rec["region"].dropna().unique())
region = c2.multiselect("Filtrar el mapa por región", regiones, placeholder="Todas las regiones")
hoy = rec[rec["escenario"] == escenario]
vista = hoy[hoy["region"].isin(region)] if region else hoy

conteo = hoy["recomendada"].value_counts()
top = (list(conteo.index[:2]) + [t for t in ("Solar", "Eólica") if t not in conteo.index[:2]])[:2]   # las dos más recomendadas en este escenario
k = st.columns(4)
k[0].metric("Países evaluados", len(hoy))
k[1].metric(f"Recomiendan {top[0].lower()}", int(conteo.get(top[0], 0)))
k[2].metric(f"Recomiendan {top[1].lower()}", int(conteo.get(top[1], 0)))
k[3].metric("Con ventaja clara", int((hoy["certeza"] == "Clara").sum()), delta=f"{int(hoy['provisional'].sum())} provisionales", delta_color="off", delta_arrow="off",
            help="Provisional: la tecnología recomendada no tiene suficiente capacidad instalada en el país para conocer su rendimiento local.")

fig = go.Figure()
for t in TECS:
    g = vista[vista["recomendada"] == t]
    if len(g):
        fig.add_choropleth(locations=g["iso3"], z=[1] * len(g), name=t, showlegend=True, showscale=False, colorscale=[[0, color[t]], [1, color[t]]],
                           marker=dict(line=dict(color=tinta()["superficie"], width=0.5)),
                           customdata=np.stack([g["pais"], g["pct_primera"], g["segunda"], g["pct_segunda"], g["certeza"],
                                                [f"{MES[int(m) - 1]}: {p:.0f} % del sol medio" if p == p else "sin dato" for m, p in zip(g["mes_min"].fillna(1), g["pct_mes_min"])]], axis=1),
                           hovertemplate="<b>%{customdata[0]}</b><br>" + t + ": %{customdata[1]:.0f} % de los escenarios<br>Segunda: %{customdata[2]} (%{customdata[3]:.0f} %)<br>Ventaja: %{customdata[4]}"
                                         "<br>Mes más oscuro: %{customdata[5]}<extra></extra>")
mostrar(estilo_mapa(fig, alto=440))
st.caption("Color: la renovable que queda primera en más escenarios para ese país. En gris, territorios sin datos. Pasa el cursor para ver la segunda opción, qué tan clara es la ventaja "
           "y cuánto sol llega en su mes más oscuro.")

if futuro:
    st.info(f"**Escenario de futuro exploratorio.** Suma el nivel «{sa.ESCENARIOS_FUTURO[escenario].lower()}» de la vista 9 para la solar, la eólica, la hidroeléctrica "
            "y la biomasa, y la geotérmica madura de la vista 8. En cada país, el rendimiento de la eólica y la hidroeléctrica sube en la misma proporción que el "
            "mundial. Los niveles son supuestos ilustrativos, no un pronóstico.", icon=":material/rocket_launch:")

st.subheader("¿Tiene en cuenta la geografía de cada país?")
base = rec[rec["escenario"].str.startswith("Hoy")]          # el recuadro describe el método con el escenario de hoy
fp_nor, fp_mundo = fp_t.query("iso3 == 'NOR' and tecnologia == 'Solar'")["fp_local"].iloc[0], criterios().loc["Solar", "fp_irena"]
rec_nor = base.loc[base["iso3"] == "NOR", "recomendada"].iloc[0]
sin_hidro = fp_t.query("tecnologia == 'Hidroeléctrica' and not elegible")["iso3"].nunique()
oscuros = base[base["invierno_oscuro"]]
oscuros_solar = oscuros[oscuros["recomendada"] == "Solar"]
si, no = st.columns(2)
with si.container(border=True):
    st.markdown(f"""**Sí tiene en cuenta**
- **El rendimiento real de cada tecnología en el país.** En Noruega, un panel solar rinde un factor de planta de {fp_nor:.2f}, cerca de la mitad del mundial ({fp_mundo:.2f}); allí queda primera la {rec_nor.lower()}.
- **Qué recursos existen.** La hidroeléctrica, la geotérmica y la biomasa solo compiten donde ya hay plantas: en {sin_hidro} países, como Arabia Saudita, la hidroeléctrica ni siquiera entra en la comparación.
- **Qué tan segura es la elección.** De los {len(oscuros_solar)} países con invierno oscuro donde gana la solar, la ventaja es clara solo en {int((oscuros_solar['certeza'] == 'Clara').sum())}.""")
with no.container(border=True):
    st.markdown(f"""**No tiene en cuenta**
- **Las estaciones.** Usa el promedio del año. En {len(oscuros)} países el mes más oscuro recibe menos del {pa.UMBRAL_INVIERNO:.0f} % del sol promedio, y en {len(oscuros_solar)} de ellos igual queda primera la solar.
- **Las diferencias dentro del país.** Cada país es un solo dato, medido donde ya están sus plantas: el sur de Noruega y Lofoten cuentan igual.
- **Cuándo se consume la energía.** En los países fríos el consumo sube en invierno, justo cuando hay menos sol.
- **El resto de criterios es igual en todo el mundo.** Solo el rendimiento y el costo cambian por país; en criterios como la caída del costo y el crecimiento la solar es la mejor, por eso tiende a ganar casi en todas partes.""")
st.markdown("**Cómo leer el mapa:** es un punto de partida, no una receta. En los países con invierno oscuro, la solar puede aportar en verano, pero el resto del año "
            "necesita el respaldo de la eólica, la hidroeléctrica u otra fuente firme.")

st.subheader("Análisis de un país")
nombres = sorted(hoy["pais"].unique())
a, b, c_ = st.columns([1.4, 1, 1])
pais = a.selectbox("País", nombres, index=nombres.index("Colombia"))
metodo = b.selectbox("Método", ["SAW", "TOPSIS"], format_func={"SAW": "Suma ponderada (SAW)", "TOPSIS": "TOPSIS"}.get)
baterias = c_.toggle("Contar baterías", value=True)
fila = hoy[hoy["pais"] == pais].iloc[0]
iso = fila["iso3"]
if futuro:
    r = recomendar_futuro(iso, metodo, baterias, sa.ESCENARIOS_FUTURO[escenario])
else:
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
    if futuro:
        otras = t["Tecnología"] != "Geotérmica"
        t.loc[otras, "Origen del dato"] = t.loc[otras, "Origen del dato"] + " + salto (vista 9)"
    if futuro or mc.ESCENARIOS_GEO.get(escenario):
        t.loc[t["Tecnología"] == "Geotérmica", "Origen del dato"] = "supuesto del escenario"
    st.dataframe(t, hide_index=True, width="stretch", column_config={"FP local": st.column_config.TextColumn("FP local", help="Factor de planta del país"),
                 "USD/MWh": st.column_config.TextColumn("USD/MWh", help="Costo mundial ajustado por el rendimiento local"), "MW en 2025": st.column_config.NumberColumn(format="%.0f")})
    st.caption(f"Recurso NASA POWER (2001–2025): radiación {datos_pais['ghi_kwh_m2_dia'].iloc[0]:.2f} kWh/m²/día, viento a 50 m {datos_pais['viento_medio_ms'].iloc[0]:.1f} m/s, "
               f"precipitación {datos_pais['precip_mm_dia'].iloc[0]:.1f} mm/día. El costo ajusta el costo mundial según el rendimiento local.")

if iso in est.index:
    e = est.loc[iso]
    meses = [e[f"ghi_{i:02d}"] for i in range(1, 13)]
    k_min = int(e["mes_min"]) - 1
    st.markdown(f"**Sol mes a mes en {pais}** (radiación media en los puntos donde están sus plantas, kWh/m² al día)")
    izq2, der2 = st.columns([1.7, 1])
    with izq2:
        fig = go.Figure(go.Bar(x=[m[:3].capitalize() for m in MES], y=meses, marker=dict(color=color["Solar"]),
                               text=[f"{v:.1f}" if i == k_min else "" for i, v in enumerate(meses)], textposition="outside", cliponaxis=False,
                               hovertemplate="%{x}: %{y:.2f} kWh/m² al día<extra></extra>"))
        fig.add_hline(y=e["ghi_anual"], line=dict(color=tinta()["secundaria"], dash="dash", width=1.5), annotation_text=f"Promedio del año: {e['ghi_anual']:.1f}",
                      annotation_position="top left", annotation_font_color=tinta()["secundaria"])
        estilo_figura(fig, alto=260, leyenda=False, titulo_y="kWh/m² al día", margen=dict(l=8, r=12, t=24, b=8))
        fig.update_yaxes(rangemode="tozero"); fig.update_xaxes(showgrid=False)
        mostrar(fig)
    with der2:
        if e["invierno_oscuro"]:
            st.warning(f"**Ojo con el invierno.** En {MES[k_min]} llega solo el {e['pct_mes_min']:.0f} % del sol promedio del año, y el factor de planta anual no muestra ese bache. "
                       "Para tener energía todo el año, la solar necesitaría el respaldo de la eólica, la hidroeléctrica u otra fuente. En la vista 8, abastecer 100 MW constantes "
                       "solo con solar y baterías costaría 332 USD/MWh en Alemania, frente a 69–99 en los otros cinco países estudiados.", icon=":material/ac_unit:")
        else:
            st.info(f"El sol se reparte de forma pareja durante el año: el mes más oscuro, {MES[k_min]}, recibe el {e['pct_mes_min']:.0f} % del promedio. "
                    "Aquí el promedio anual sí representa bien a la solar.", icon=":material/wb_sunny:")

with st.expander("Cómo se calcula la recomendación"):
    cal = {c["tecnologia"] + c["variable"]: c for c in resumen()["calibracion"]}
    sol = cal["Solarghi_kwh_m2_dia"]
    st.markdown(f"""
- Se usan los **14 criterios** de la evaluación integral. Dos se vuelven locales: el **rendimiento** y el **costo**.
- **Rendimiento:** el factor de planta real del país en 2020–2024 según IRENA. Si no hay suficiente capacidad, en la solar se estima con la radiación de NASA POWER (validado: ρ = {sol['rho_spearman']:.2f}; el error baja de {sol['MAE_media_cv']:.3f} a {sol['MAE_cv']:.3f}).
- **Viento:** la velocidad de NASA **no** predijo el rendimiento eólico entre países, así que no se usa; se toma el valor mundial y se advierte.
- **Costo:** se ajusta en proporción inversa al rendimiento, entre la mitad y el doble del costo mundial.
- Hidroeléctrica, geotérmica y biomasa solo compiten si el país ya tiene esa tecnología, como evidencia de que el recurso existe.
- **No ve las estaciones:** usa el promedio anual del recurso. La radiación mes a mes de NASA POWER se muestra aparte, como advertencia, y no cambia la recomendación.
- **No reemplaza** un estudio de planificación: no incluye la red, la demanda, el financiamiento ni la política de cada país.
""")

st.download_button("Descargar la tabla de todos los países (CSV)", hoy.drop(columns=[c for c in hoy.columns if c.startswith("pct_") and c not in ("pct_primera", "pct_segunda")]).to_csv(index=False).encode("utf-8"),
                   "recomendacion_por_pais.csv", "text/csv")
