# -*- coding: utf-8 -*-
import json

import plotly.graph_objects as go
import streamlit as st

from comun import PROC, TECS, colores_tec, encabezado, escenario_a_tupla, estilo_figura, estilo_mapa, fmt, hallazgo, leer, mc, modo_oscuro, mostrar, recomendaciones, simular_global, tinta

encabezado("¿Y si la geotérmica despega?", "Si perforar con ondas milimétricas funciona: qué pasaría, cómo se comportaría y cuál sería su potencial.")
color = colores_tec()
t = tinta()
COLOR_BATERIA = "#9085e9" if modo_oscuro() else "#6250d6"
MEZCLA = "Solar + eólica + baterías"

st.markdown("""La geotermia convencional solo es viable donde hay calor cerca de la superficie. La idea de la **roca supercaliente** es perforar
a gran profundidad con **ondas milimétricas**, que evaporan la roca en lugar de triturarla, y obtener vapor casi en cualquier país.
**Hoy es una hipótesis:** ningún pozo perforado así ha producido electricidad.""")

res_geo = json.loads((PROC / "geo_resumen.json").read_text(encoding="utf-8"))
operacion = leer("geo_operacion.csv")
mezcla_total = operacion[operacion["mezcla"] == MEZCLA]
p_2030 = res_geo["potencial_2050"]["Como la eólica desde 2030"]
hallazgo(f"<b>Qué pasaría:</b> quedaría primera solo si cuesta menos de unos {res_geo['quiebre_con_crecimiento']:.0f} USD/MWh, llega a todos los países y crece como la eólica.<br>"
         f"<b>Cómo se comportaría:</b> entregaría energía a toda hora. Lograr lo mismo con solar, eólica y baterías cuesta hoy entre {mezcla_total['costo_firme_2025'].min():.0f} y "
         f"{mezcla_total['costo_firme_2025'].max():.0f} USD/MWh en los seis países estudiados.<br>"
         f"<b>Su potencial:</b> si repite la expansión de la eólica desde 2030, llegaría a unos {fmt(round(p_2030['gw'], -1))} GW en 2050, el equivalente al {p_2030['pct_demanda_2025']:.0f} % de la electricidad mundial de 2025.")

tab1, tab2, tab3 = st.tabs(["1. ¿Qué pasaría?", "2. ¿Cómo se comportaría?", "3. ¿Cuál sería su potencial?"])

# ---------------------------------------------------------------------------------------------------------------------
with tab1:
    esc = leer("escenarios_geotermica.csv")
    base = esc[(esc["metodo"] == "SAW") & esc["con_baterias"]]

    st.subheader("Construye tu escenario")
    with st.container(border=True):
        PRE = list(mc.ESCENARIOS_GEO)
        preset = st.segmented_control("Punto de partida", PRE, default=PRE[2])
        cfg = mc.ESCENARIOS_GEO.get(preset) or {"lcoe": (60, 89), "fp": 0.85, "todos_los_paises": False, "crece_como_eolica": False}
        a, b, c_, d_ = st.columns([1.5, 1, 1, 1])
        lcoe = a.slider("Costo (USD/MWh)", 15, 100, tuple(int(x) for x in cfg["lcoe"]), key=f"l_{preset}")
        fp = b.slider("Factor de planta", 0.70, 0.95, float(cfg["fp"]), step=0.01, key=f"f_{preset}")
        todos = c_.toggle("Viable en todos los países", value=cfg["todos_los_paises"], key=f"t_{preset}")
        crece = d_.toggle("Crece como la eólica", value=cfg["crece_como_eolica"], key=f"c_{preset}")

    propio = {"lcoe": lcoe, "fp": fp, "todos_los_paises": todos, "crece_como_eolica": crece}
    res, _ = simular_global(None, "SAW", True, escenario_a_tupla(propio))
    ref, _ = simular_global(None, "SAW", True, None)

    izq, der = st.columns([1.15, 1])
    with izq:
        st.markdown("**% de escenarios en primer lugar: hoy (gris) frente a tu escenario (color)**")
        orden = res["% n.º 1"].sort_values().index
        fig = go.Figure()
        fig.add_bar(y=list(orden), x=ref.loc[orden, "% n.º 1"], name="Hoy", orientation="h", marker=dict(color=t["eje"]),
                    hovertemplate="%{y} hoy: %{x:.1f} %<extra></extra>")
        fig.add_bar(y=list(orden), x=res.loc[orden, "% n.º 1"], name="Tu escenario", orientation="h", marker=dict(color=[color[x] for x in orden]),
                    text=[f"{v:.1f} %" for v in res.loc[orden, "% n.º 1"]], textposition="outside", cliponaxis=False,
                    hovertemplate="%{y} en tu escenario: %{x:.1f} %<extra></extra>")
        fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
        estilo_figura(fig, alto=350, leyenda=False, margen=dict(l=8, r=52, t=8, b=8), titulo_x="% de escenarios")
        fig.update_xaxes(range=[0, 100]); fig.update_yaxes(showgrid=False)
        mostrar(fig)
    with der:
        st.markdown("**Qué tanto aporta cada mejora por separado**")
        o = base[base["tecnologia"] == "Geotérmica"].set_index("escenario")["% n.º 1"]
        etiquetas = {"Hoy (datos de la Fase 3)": "Hoy", "Solo llega a todos los países": "Solo llega a todos los países", "Solo baja el costo (20–35 USD/MWh)": "Solo baja el costo",
                     "Prueba de concepto": "Prueba de concepto", "Madura (meta de la industria)": "Madura (todo a la vez)"}
        o = o.reindex(list(etiquetas))[::-1]
        fig = go.Figure(go.Bar(y=[etiquetas[x] for x in o.index], x=o.values, orientation="h", marker=dict(color=color["Geotérmica"]), text=[f"{v:.1f} %" for v in o.values],
                               textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x:.1f} %<extra></extra>"))
        estilo_figura(fig, alto=350, leyenda=False, margen=dict(l=8, r=52, t=8, b=8), titulo_x="% de escenarios en que la geotérmica queda primera")
        fig.update_xaxes(range=[0, 100]); fig.update_yaxes(showgrid=False); fig.update_layout(bargap=0.32)
        mostrar(fig)

    st.subheader("¿Qué tendría que cumplirse para que gane?")
    izq, der = st.columns(2)
    with izq:
        st.markdown("**Según su costo** (llega a todos los países, FP de 0.90, crece como la eólica)")
        cond = leer("geo_condiciones.csv")
        g = cond[(cond["fp"] == 0.90) & cond["crece_como_eolica"]].sort_values("costo_medio")
        fig = go.Figure()
        fig.add_scatter(x=g["costo_medio"], y=g["geotermica"], name="Geotérmica", mode="lines+markers", line=dict(color=color["Geotérmica"], width=2), marker=dict(size=8),
                        hovertemplate="Costo %{x} USD/MWh<br>Geotérmica: %{y:.1f} %<extra></extra>")
        fig.add_scatter(x=g["costo_medio"], y=g["mejor_rival"], name="Mejor rival (solar)", mode="lines+markers", line=dict(color=color["Solar"], width=2), marker=dict(size=8),
                        hovertemplate="Costo %{x} USD/MWh<br>Mejor rival: %{y:.1f} %<extra></extra>")
        fig.add_vline(x=res_geo["quiebre_con_crecimiento"], line=dict(color=t["secundaria"], dash="dot", width=1.5), annotation_text=f"Empate: {res_geo['quiebre_con_crecimiento']:.0f}",
                      annotation_position="top right", annotation_font_color=t["secundaria"])
        fig.add_vline(x=50, line=dict(color=t["tenue"], dash="dash", width=1), annotation_text="Meta AIE: 50", annotation_position="top right", annotation_font_color=t["secundaria"])
        estilo_figura(fig, alto=340, titulo_x="Costo medio de la geotérmica (USD/MWh)", titulo_y="% de escenarios en primer lugar", margen=dict(l=8, r=12, t=34, b=8))
        fig.update_yaxes(rangemode="tozero")
        mostrar(fig)
    with der:
        st.markdown("**Si la solar y la eólica también se abaratan** (geotérmica madura)")
        riv = leer("geo_rivales.csv")
        riv = riv[riv["metodo"] == "SAW"]
        fig = go.Figure()
        for tec in ("Geotérmica", "Solar", "Eólica"):
            fig.add_scatter(x=riv["caida_rivales"], y=riv[tec], name=tec, mode="lines+markers", line=dict(color=color[tec], width=2), marker=dict(size=8),
                            hovertemplate=tec + "<br>Caída de %{x} %: %{y:.1f} %<extra></extra>")
        fig.add_vline(x=40, line=dict(color=t["tenue"], dash="dash", width=1), annotation_text="IRENA a 2035", annotation_position="top right", annotation_font_color=t["secundaria"])
        estilo_figura(fig, alto=340, titulo_x="Caída adicional del costo de la solar y la eólica (%)", titulo_y="% de escenarios en primer lugar", margen=dict(l=8, r=12, t=34, b=8))
        fig.update_yaxes(rangemode="tozero")
        mostrar(fig)

    rec = recomendaciones()
    m_ = rec[rec["escenario"].str.startswith("Madura")]
    st.subheader("Si madura, ¿qué recomendaría cada país?")
    fig = go.Figure()
    for t_ in TECS:
        g = m_[m_["recomendada"] == t_]
        if len(g):
            fig.add_choropleth(locations=g["iso3"], z=[1] * len(g), name=t_, showlegend=True, showscale=False, colorscale=[[0, color[t_]], [1, color[t_]]],
                               marker=dict(line=dict(color=t["superficie"], width=0.5)), text=g["pais"],
                               hovertemplate="<b>%{text}</b><br>" + t_ + "<extra></extra>")
    mostrar(estilo_mapa(fig, alto=380))
    st.caption(f"En el escenario maduro, la geotérmica sería la primera opción en {int((m_['recomendada'] == 'Geotérmica').sum())} de {len(m_)} países, a menudo por poco margen. "
               "Supone el mismo costo en todos, aunque la profundidad necesaria cambia con la geología.")

# ---------------------------------------------------------------------------------------------------------------------
with tab2:
    st.markdown("Su mayor diferencia no está en el costo por MWh, sino en **cuándo entrega la energía**. Aquí se abastece un consumo constante de **100 MW** durante "
                "2022–2024, hora a hora, con el 95 % de confiabilidad, y se compara con construir lo mismo con solar, eólica y baterías.")
    a, b = st.columns(2)
    paises = list(operacion["pais"].unique())
    pais = a.selectbox("País de estudio", paises, index=paises.index("Colombia"))
    alternativa = b.selectbox("Alternativa sin geotérmica", [MEZCLA, "Solar + baterías"])
    f = operacion[(operacion["pais"] == pais) & (operacion["mezcla"] == alternativa)].iloc[0]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Costo firme hoy", f"{f['costo_firme_2025']:.0f} USD/MWh")
    k2.metric("Costo firme en 2035", f"{f['costo_firme_2035']:.0f} USD/MWh", help="Con la caída del 40 % que proyecta IRENA.")
    k3.metric("Capacidad a instalar", f"{fmt(f['solar_mw'] + f['eolica_mw'])} MW", help=f"La geotérmica necesitaría {f['geo_mw']:.0f} MW.")
    k4.metric("Baterías", f"{fmt(f['bateria_mwh'])} MWh", help="La geotérmica no las necesita.")

    izq, der = st.columns([1.2, 1])
    with izq:
        st.markdown(f"**{pais}: la semana con menos sol y viento, con solar, eólica y baterías**")
        s_ = leer("geo_semana.csv")
        s_ = s_[s_["iso3"] == f["iso3"]]
        colores = {"Solar": color["Solar"], "Eólica": color["Eólica"], "Baterías": COLOR_BATERIA, "Déficit": t["eje"]}
        fig = go.Figure()
        for serie, col in colores.items():
            fig.add_scatter(x=s_["hora"] / 24, y=s_[serie], name=serie, mode="lines", stackgroup="uno", line=dict(width=0.4, color=col), fillcolor=col,
                            hovertemplate=serie + ": %{y:.0f} MW<extra></extra>")
        fig.add_scatter(x=[0, 7], y=[100, 100], name="Geotérmica (constante)", mode="lines", line=dict(color=color["Geotérmica"], width=2.5),
                        hovertemplate="Geotérmica: 100 MW<extra></extra>")
        estilo_figura(fig, alto=350, titulo_x="Día de la semana más difícil", titulo_y="MW entregados", margen=dict(l=8, r=12, t=34, b=8))
        fig.update_yaxes(range=[0, 112]); fig.update_xaxes(range=[0, 7], dtick=1)
        mostrar(fig)
    with der:
        st.markdown("**Costo de energía firme frente a la geotérmica**")
        g = operacion[operacion["mezcla"] == alternativa].sort_values("costo_firme_2025")
        fig = go.Figure()
        fig.add_bar(y=g["pais"], x=g["costo_firme_2035"], name="Mezcla en 2035", orientation="h", marker=dict(color=t["tenue"]), hovertemplate="%{y} en 2035: %{x:.0f} USD/MWh<extra></extra>")
        fig.add_bar(y=g["pais"], x=g["costo_firme_2025"], name="Mezcla hoy", orientation="h", marker=dict(color=t["secundaria"]), hovertemplate="%{y} hoy: %{x:.0f} USD/MWh<extra></extra>")
        fig.add_vrect(x0=20, x1=35, fillcolor=color["Geotérmica"], opacity=0.15, line_width=0)
        fig.add_vline(x=50, line=dict(color=color["Geotérmica"], dash="dash", width=1.5))
        fig.add_vline(x=89, line=dict(color=color["Geotérmica"], width=1.5))
        for x_, texto in ((27.5, "Meta"), (50, "AIE 50"), (89, "Actual 89")):
            fig.add_annotation(x=x_, y=1.0, yref="paper", yanchor="bottom", text=texto, showarrow=False, font=dict(color=t["secundaria"], size=12))
        fig.update_layout(barmode="group", bargap=0.25)
        estilo_figura(fig, alto=350, titulo_x="USD/MWh", margen=dict(l=8, r=30, t=62, b=8))
        fig.update_layout(legend=dict(y=1.09, traceorder="reversed"))
        fig.update_yaxes(showgrid=False)
        mostrar(fig)

    st.markdown("**Qué exige abastecer 100 MW constantes**")
    st.dataframe({"": ["Capacidad instalada (MW)", "Baterías (MWh)", "Terreno (ha)", "Minerales críticos (t)", "Energía que se desperdicia (%)"],
                  alternativa: [fmt(f["solar_mw"] + f["eolica_mw"]), fmt(f["bateria_mwh"]), fmt(f["terreno_ha"]), fmt(f["minerales_t"]), f"{f['vertida_pct']:.0f}"],
                  "Geotérmica": [fmt(f["geo_mw"]), "0", fmt(f["geo_terreno_ha"]), fmt(f["geo_minerales_t"]), "0"]}, width="stretch", hide_index=True)
    st.caption(f"FP usados en {pais}: solar {f['fp_solar']:.2f}, {f['origen_solar']}; eólica {f['fp_eolica']:.2f}, {f['origen_eolica']}. NASA aporta solo la forma hora a hora. "
               "Es una cota superior: una red real también cuenta con hidroeléctrica, gas e interconexiones.")

# ---------------------------------------------------------------------------------------------------------------------
with tab3:
    pot = leer("geo_potencial.csv")
    st.markdown("El calor disponible **no es el límite**: la Agencia Internacional de la Energía estima casi **600 TW** de potencial técnico a menos de 8 km, suficiente para cubrir "
                "140 veces la demanda eléctrica mundial. El límite es **qué tan rápido se puede construir**. Por eso se proyecta qué ocurriría si la geotérmica repitiera la expansión real de otra tecnología "
                "desde que tenía su tamaño actual.")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Capacidad en 2050", f"{fmt(p_2030['gw'])} GW", help="Si crece como la eólica desde 2030.")
    k2.metric("Energía al año", f"{fmt(p_2030['twh'])} TWh")
    k3.metric("Frente a la electricidad de 2025", f"{p_2030['pct_demanda_2025']:.0f} %")
    k4.metric("CO₂ evitado al año", f"{p_2030['gt_co2_gas']:.1f}–{p_2030['gt_co2_carbon']:.1f} Gt", help="Si reemplaza gas (mínimo) o carbón (máximo).")
    fig = go.Figure()
    estilos = {"Sigue como hoy": ("dot", t["tenue"]), "Como la eólica desde 2035": ("dash", color["Geotérmica"]), "Como la eólica desde 2030": ("solid", color["Geotérmica"]),
               "Como la solar desde 2035": ("dashdot", color["Geotérmica"])}
    for nombre, (dash, col) in estilos.items():
        g = pot[pot["trayectoria"] == nombre]
        fig.add_scatter(x=g["anio"], y=g["gw"], name=nombre, mode="lines", line=dict(color=col, dash=dash, width=2.2),
                        hovertemplate=nombre + "<br>%{x}: %{y:.0f} GW<extra></extra>")
    fig.add_scatter(x=[2050], y=[800], name="Proyección de la AIE", mode="markers", marker=dict(symbol="diamond", size=12, color=t["primaria"]),
                    hovertemplate="AIE 2050: 800 GW<extra></extra>")
    estilo_figura(fig, alto=400, titulo_x="Año", titulo_y="Capacidad geotérmica (GW)", margen=dict(l=8, r=12, t=48, b=8))
    fig.update_yaxes(rangemode="tozero")
    mostrar(fig)
    fin = pot[pot["anio"] == 2050].set_index("trayectoria").reindex(list(estilos))
    st.dataframe({"Trayectoria": list(fin.index), "GW en 2050": [fmt(x) for x in fin["gw"]], "TWh al año": [fmt(x) for x in fin["twh"]],
                  "% de la electricidad de 2025": [f"{x:.1f}" for x in fin["pct_demanda_2025"]]}, width="stretch", hide_index=True)
    st.caption("Es una analogía, no un pronóstico: la eólica y la solar crecieron con apoyo público y con fábricas en serie, mientras que cada pozo geotérmico es una obra. FP supuesto de 0.85.")

st.subheader("A favor y en contra")
p, q = st.columns(2)
with p.container(border=True):
    st.markdown("""**A favor**
- Entrega energía día y noche: no necesita baterías.
- Es la que menos terreno usa y la que más energía da por MW.
- Complementa a la solar y la eólica justo cuando no hay sol ni viento.
- Hasta el 80 % de la inversión usa capacidades de la industria petrolera.""")
with q.container(border=True):
    st.markdown("""**En contra**
- Es la que más minerales críticos usa por GWh (aceros con níquel y cromo).
- Riesgo de sismicidad inducida y costo de perforar a gran profundidad.
- Su rendimiento mundial ha bajado y aún no hay plantas comerciales de este tipo.
- Sus rivales también se abaratan: la solar con baterías podría caer 40 % a 2035.""")

with st.expander("Fuentes y estado real de la tecnología (noviembre de 2026)"):
    st.markdown("""
- **Costo de 20–35 USD/MWh:** proyección «a escala» que supone innovaciones aún no demostradas. LucidCatalyst y Hot Rock Energy Research Organization para Clean Air Task Force (2022). [Ver el informe](https://cdn.catf.us/wp-content/uploads/2022/12/30135200/SHRTechnoEconomic_Report.pdf)
- **Potencial, 800 GW, 6 000 TWh y costo de 50 USD/MWh a 2035:** Agencia Internacional de la Energía (2024), *The Future of Geothermal Energy*. [Ver el resumen](https://www.iea.org/reports/the-future-of-geothermal-energy/executive-summary)
- **Baterías (140 USD/kWh) y energía solar firme (54–82 USD/MWh, −40 % a 2035):** IRENA (2026), *Renewable Power Generation Costs in 2025*, pp. 24 y 141. [Ver el informe](https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2026/Jul/IRENA_TEC_RPGC_in_2025_2026.pdf)
- **Electricidad mundial de 2025:** Ember (2026), *Global Electricity Review*. [Ver el informe](https://ember-energy.org/latest-insights/global-electricity-review-2026/)
- **Avance en campo:** Quaise Energy perforó unos 118 m con ondas milimétricas en Texas (2025) y en julio de 2026 informó que se acerca a 1 km, sin confirmación independiente. [Geothermal Insider](https://geothermalinsider.com/learn/quaise-energy/)
- **Primera planta:** Proyecto Obsidian (Oregón), 50 MW en su primera fase, con meta de entregar electricidad en 2030. Sus primeros tramos se perforan de forma convencional.
- **Supuestos del escenario:** no cambian las emisiones, los minerales, la vida útil ni la seguridad de la geotérmica actual.
""")
