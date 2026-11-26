# -*- coding: utf-8 -*-
import math

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from comun import TECS, colores_tec, criterios, encabezado, estilo_figura, hallazgo, mc, mostrar, sa, saltos_a_tupla, simular_saltos, tinta

CUATRO = list(sa.PALANCAS)
encabezado("¿Y si cada una da su gran salto?",
           "El celular pasó de ladrillo a smartphone. ¿Puede pasar algo así con la solar, la eólica, la hidroeléctrica y la biomasa?")
color, t = colores_tec(), tinta()

# Tu ejemplo: un pedacito de panel de 2 × 2 cm
SOL_W_M2, AREA_M2, EF_HOY, CARGADOR_W = 1000, 0.02 * 0.02, 0.24, 20
p_max, p_hoy = SOL_W_M2 * AREA_M2, SOL_W_M2 * AREA_M2 * EF_HOY
lado_hoy, lado_ideal = math.sqrt(CARGADOR_W / (SOL_W_M2 * EF_HOY)) * 100, math.sqrt(CARGADOR_W / SOL_W_M2) * 100

ref, _ = simular_saltos(())
solo = {tec: simular_saltos(saltos_a_tupla({tec: sa.valores_nivel(tec, "Gran salto")}))[0] for tec in CUATRO}
todas, _ = simular_saltos(saltos_a_tupla({tec: sa.valores_nivel(tec, "Gran salto") for tec in CUATRO}))
gana_todas = todas["% n.º 1"].idxmax()

st.markdown("""La vista 8 explora el gran salto de la geotérmica. Aquí se hace lo mismo con las otras cuatro: qué tanto pueden mejorar todavía,
qué pasaría si una de ellas da un salto histórico y qué pasaría si todas lo dan a la vez. **Es un ejercicio exploratorio, no un pronóstico.**""")
hallazgo(f"<b>La física pone techo:</b> un panel de 2 × 2 cm recibe como máximo {p_max:.1f} W de sol, aunque fuera perfecto. El gran salto de las renovables está en el costo, la escala, la duración y el reciclaje.<br>"
         f"<b>Si una sola da el salto, puede ganar:</b> con un gran salto, la solar quedaría primera en el {solo['Solar'].loc['Solar', '% n.º 1']:.0f} % de los escenarios, "
         f"y la eólica subiría al {solo['Eólica'].loc['Eólica', '% n.º 1']:.0f} % y superaría a la solar.<br>"
         f"<b>Si todas lo dan a la vez,</b> gana la {gana_todas.lower()} ({todas.loc[gana_todas, '% n.º 1']:.0f} %): cuando todas mejoran, decide quién mejora más.")

tab1, tab2, tab3 = st.tabs(["1. ¿Cuánto pueden mejorar todavía?", "2. ¿Y si una da el salto?", "3. ¿Y si todas lo dan a la vez?"])

# ---------------------------------------------------------------------------------------------------------------------
with tab1:
    st.markdown("""El celular mejoró tanto porque sus transistores se encogen: hoy caben miles de millones en un chip. Las renovables no fabrican energía:
**recogen la que trae la naturaleza**, ya sea sol, viento, agua o plantas. Esa cantidad tiene un límite que ninguna tecnología puede superar.""")
    with st.container(border=True):
        st.markdown("**Tu ejemplo: un pedacito de panel solar de 2 × 2 cm**")
        k1, k2, k3 = st.columns(3)
        k1.metric("Sol que le llega a mediodía", f"{p_max:.1f} W", help=f"Con cielo despejado llegan unos {SOL_W_M2:,} W por m²; 4 cm² reciben {p_max:.1f} W.".replace(",", " "))
        k2.metric("Lo que entrega hoy", f"≈ {p_hoy:.1f} W", help=f"Con {EF_HOY * 100:.0f} % de eficiencia, la de los mejores paneles comerciales.")
        k3.metric(f"Panel para cargar un celular ({CARGADOR_W} W)", f"{lado_hoy:.0f} × {lado_hoy:.0f} cm",
                  help=f"A mediodía y con la eficiencia de hoy. Con una eficiencia imposible del 100 %, seguiría haciendo falta uno de {lado_ideal:.0f} × {lado_ideal:.0f} cm.")
        st.caption("Ni un panel perfecto lograría que un pedacito de 2 × 2 cm dé mucha energía, porque el sol no entrega más. "
                   "Por eso el salto de la solar no puede parecerse al del celular en potencia por centímetro.")

    izq, der = st.columns([1.25, 1])
    with izq:
        st.markdown("**Cuánto aprovechan hoy y cuál es su techo físico** (% de la energía disponible)")
        filas = sa.TECHOS[::-1]
        y = [f"<b>{f['tecnologia']}</b><br>hoy {f['hoy'][0]:g}–{f['hoy'][1]:g} % · techo {f['techo']:g} %" for f in filas]
        fig = go.Figure()
        fig.add_bar(y=y, x=[f["techo"] for f in filas], orientation="h", marker=dict(color=t["reticula"]), width=0.62, name="Techo físico",
                    customdata=[f["techo_txt"] for f in filas], hovertemplate="Techo: %{customdata}<extra></extra>")
        fig.add_bar(y=y, x=[f["hoy"][1] for f in filas], orientation="h", marker=dict(color=[color[f["tecnologia"]] for f in filas]), width=0.62, name="Hoy",
                    showlegend=False, customdata=[[f["hoy"][0], f["hoy"][1], f["mide"]] for f in filas],
                    hovertemplate="Hoy: %{customdata[0]}–%{customdata[1]} %<br>%{customdata[2]}<extra></extra>")
        rec = [(yy, f) for yy, f in zip(y, filas) if f["record"]]
        fig.add_scatter(y=[yy for yy, _ in rec], x=[f["record"] for _, f in rec], mode="markers", name="Récord de laboratorio",
                        marker=dict(symbol="diamond", size=13, color=t["primaria"], line=dict(color=t["superficie"], width=2)),
                        customdata=[f["record_txt"] for _, f in rec], hovertemplate="%{customdata}<extra></extra>")
        fig.update_layout(barmode="overlay", bargap=0.3)
        estilo_figura(fig, alto=340, titulo_x="% de la energía disponible que se aprovecha", margen=dict(l=8, r=16, t=34, b=8))
        fig.update_xaxes(range=[0, 101], tickvals=[0, 25, 50, 75, 100]); fig.update_yaxes(showgrid=False, tickfont=dict(size=12))
        mostrar(fig)
        st.caption("Solar: luz convertida en electricidad. Eólica: energía del viento que atraviesa el rotor. Hidroeléctrica: energía del agua que convierte la turbina. "
                   "Biomasa: luz que la planta guarda como biomasa (mejores cultivos medidos). Barra de color = hoy; barra gris = techo; rombo = récord de laboratorio.")
    with der:
        st.markdown("**Lo que ya pasó: cambio del costo entre 2010 y 2025**")
        cambio = criterios()["cambio_costo"].sort_values(ascending=False)
        fig = go.Figure(go.Bar(y=list(cambio.index), x=cambio.values, orientation="h", marker=dict(color=[color[x] for x in cambio.index]),
                               text=[f"{v:+.0f} %" for v in cambio.values], textposition="outside", cliponaxis=False,
                               hovertemplate="%{y}: %{x:+.0f} % entre 2010 y 2025<extra></extra>"))
        estilo_figura(fig, alto=330, leyenda=False, titulo_x="Cambio del costo nivelado (%)", margen=dict(l=8, r=48, t=34, b=8))
        fig.update_xaxes(range=[-115, 80]); fig.update_yaxes(showgrid=False)
        mostrar(fig)
        st.caption("Fuente: IRENA (2026). Negativo = más barata.")
    st.markdown(f"""**La solar ya tuvo su «momento smartphone», pero en el costo:** entre 2010 y 2025 se abarató {-criterios().loc['Solar', 'cambio_costo']:.0f} %,
y la eólica {-criterios().loc['Eólica', 'cambio_costo']:.0f} %, gracias a la producción en serie de paneles y turbinas. La hidroeléctrica y la geotérmica se encarecieron:
cada central es una obra a la medida. Por eficiencia, a la hidroeléctrica casi no le queda margen; a la solar y a la eólica les queda algo, y la biomasa es la menos eficiente
de todas, por eso ocupa tanto terreno.""")

# ---------------------------------------------------------------------------------------------------------------------
with tab2:
    tec = st.segmented_control("Tecnología", CUATRO, default="Solar", key="tec_salto") or "Solar"
    nombre, texto = sa.DESCRIPCION[tec]
    st.markdown(f"**{nombre}.** {texto}")

    with st.container(border=True):
        nivel = st.segmented_control("Punto de partida", sa.NIVELES, default="Gran salto", key=f"nivel_{tec}") or "Gran salto"
        base = sa.valores_nivel(tec, nivel)
        valores = {}
        deslizadores = [p for p in sa.PALANCAS[tec] if p.get("tipo") != "toggle"]
        interruptores = [p for p in sa.PALANCAS[tec] if p.get("tipo") == "toggle"]
        for col, p in zip(st.columns(len(deslizadores)), deslizadores):
            valores[p["clave"]] = col.slider(p["etiqueta"], p["min"], p["max"], base[p["clave"]], step=p["paso"], key=f"{tec}_{nivel}_{p['clave']}", help=p["ayuda"])
        if interruptores:
            for col, p in zip(st.columns(len(deslizadores)), interruptores):
                valores[p["clave"]] = col.toggle(p["etiqueta"], value=base[p["clave"]], key=f"{tec}_{nivel}_{p['clave']}", help=p["ayuda"])

    res, d_salto = simular_saltos(saltos_a_tupla({tec: valores}))
    antes, despues = ref.loc[tec], res.loc[tec]
    ganadora = res["% n.º 1"].idxmax()
    k1, k2, k3 = st.columns(3)
    k1.metric(f"{tec}: % en primer lugar", f"{despues['% n.º 1']:.1f} %", f"{despues['% n.º 1'] - antes['% n.º 1']:+.1f} puntos frente a hoy")
    k2.metric("Su puesto promedio", f"{despues['puesto promedio']:.2f}", f"{despues['puesto promedio'] - antes['puesto promedio']:+.2f}", delta_color="inverse",
              help="De 1 (siempre primera) a 5 (siempre última).")
    k3.metric("Quedaría primera", f"{ganadora} · {res.loc[ganadora, '% n.º 1']:.1f} %", help="Tecnología que más veces queda primera en tu escenario.")

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
        st.markdown(f"**Qué cambia en los criterios de la {tec.lower()}**")
        m0, m1 = mc.matriz_puntual(criterios()).loc[tec], mc.matriz_puntual(d_salto).loc[tec]
        nombres = {"Rendimiento": ("Factor de planta", 2), "Costo": ("Costo (USD/MWh)", 0), "Uso de suelo": ("Terreno (ha por TWh al año)", 0),
                   "Minerales críticos": ("Minerales críticos (kg por GWh)", 1), "Emisiones": ("Emisiones (g CO₂ por kWh)", 1), "Reciclabilidad": ("Reciclaje (% de la masa)", 1),
                   "Vida útil": ("Vida útil (años)", 0), "Dinamismo de costos": ("Caída del costo desde 2010 (%)", 0), "Crecimiento": ("Crecimiento (% al año)", 1)}
        cambios = [c for c in nombres if not np.isclose(m0[c], m1[c])]
        if cambios:
            num = lambda x, c: f"{x:,.{nombres[c][1]}f}".replace(",", " ")
            st.dataframe({"Criterio": [nombres[c][0] for c in cambios], "Hoy": [num(m0[c], c) for c in cambios],
                          "Con el salto": [num(m1[c], c) for c in cambios]}, width="stretch", hide_index=True)
        else:
            st.info("Con «Hoy» no cambia nada: es el punto de partida de la evaluación integral.")
        if valores.get("beccs"):
            st.caption("Con captura de carbono, el modelo la toma como la de menores emisiones: las emisiones negativas no caben en su escala logarítmica.")
    st.caption("Mismo modelo de la evaluación integral: 14 criterios y 20 000 escenarios con pesos al azar (SAW). Solo cambia la tecnología elegida; "
               "las demás quedan como hoy. Los niveles son supuestos ilustrativos: ver «Fuentes y supuestos» al final.")

# ---------------------------------------------------------------------------------------------------------------------
with tab3:
    st.markdown("Con los celulares no mejoró una sola marca: mejoraron todas. ¿Qué pasa si **todas las renovables** dan su salto al mismo tiempo?")
    a, b = st.columns([1.3, 1])
    nivel_t = a.segmented_control("Nivel para todas", sa.NIVELES[1:], default="Gran salto", key="nivel_todas") or "Gran salto"
    geo = b.toggle("Sumar la geotérmica madura de la vista 8", value=False)
    saltos = {tec_: sa.valores_nivel(tec_, nivel_t) for tec_ in CUATRO}
    res_t, _ = simular_saltos(saltos_a_tupla(saltos), geo_madura=geo)
    sola = {tec_: simular_saltos(saltos_a_tupla({tec_: saltos[tec_]}))[0].loc[tec_, "% n.º 1"] for tec_ in CUATRO}
    if geo:
        sola["Geotérmica"] = simular_saltos((), geo_madura=True)[0].loc["Geotérmica", "% n.º 1"]
    gana = res_t["% n.º 1"].idxmax()

    st.markdown("**% de escenarios en primer lugar: hoy (gris), si solo ella da el salto (color tenue) y si todas lo dan a la vez (color pleno)**")
    orden = res_t["% n.º 1"].sort_values().index
    fig = go.Figure()
    fig.add_bar(y=list(orden), x=ref.loc[orden, "% n.º 1"], name="Hoy", orientation="h", marker=dict(color=t["eje"]),
                hovertemplate="%{y} hoy: %{x:.1f} %<extra></extra>")
    fig.add_bar(y=list(orden), x=[sola.get(x, np.nan) for x in orden], name="Si solo ella da el salto", orientation="h",
                marker=dict(color=[color[x] for x in orden], opacity=0.45), hovertemplate="%{y}, si solo ella da el salto: %{x:.1f} %<extra></extra>")
    fig.add_bar(y=list(orden), x=res_t.loc[orden, "% n.º 1"], name="Si todas lo dan a la vez", orientation="h", marker=dict(color=[color[x] for x in orden]),
                text=[f"{v:.1f} %" for v in res_t.loc[orden, "% n.º 1"]], textposition="outside", cliponaxis=False,
                hovertemplate="%{y}, si todas lo dan a la vez: %{x:.1f} %<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.22, bargroupgap=0.06)
    estilo_figura(fig, alto=420, leyenda=False, titulo_x="% de escenarios en primer lugar", margen=dict(l=8, r=52, t=8, b=8))
    fig.update_xaxes(range=[0, 100]); fig.update_yaxes(showgrid=False)
    mostrar(fig)

    caida = {x: sola[x] - res_t.loc[x, "% n.º 1"] for x in sola}
    mas_pierde = max(caida, key=caida.get)
    st.markdown(f"""Si todas dan el salto, gana la **{gana.lower()}**, en el {res_t.loc[gana, '% n.º 1']:.1f} % de los escenarios. Pero ninguna llega tan lejos como si mejorara sola:
la {mas_pierde.lower()} pasaría del {sola[mas_pierde]:.0f} % al {res_t.loc[mas_pierde, '% n.º 1']:.0f} %. El modelo compara a las cinco entre sí, de modo que si todas mejoran,
la ventaja de cada una se diluye y gana la que mejora más en lo que más pesa. Es lo mismo que mostró la vista 8: si la solar y la eólica también se abaratan, la geotérmica pierde su ventaja.""")
    st.dataframe({"Tecnología": list(TECS), "Hoy (%)": [f"{ref.loc[x, '% n.º 1']:.1f}" for x in TECS],
                  "Si solo ella da el salto (%)": [f"{sola[x]:.1f}" if x in sola else "—" for x in TECS],
                  "Si todas lo dan a la vez (%)": [f"{res_t.loc[x, '% n.º 1']:.1f}" for x in TECS]}, width="stretch", hide_index=True)

with st.expander("Fuentes y supuestos"):
    st.markdown("**Datos reales que anclan los escenarios**")
    st.markdown("\n".join(f"- **{q}:** {fuente}. [Ver]({url})" for q, fuente, url in sa.FUENTES))
    st.markdown("""**Supuestos de cada nivel.** Son ilustrativos: algunos se apoyan en proyecciones, como la caída de 40 % del costo de la solar con baterías a 2035
(IRENA, 2026), y otros solo marcan la dirección del cambio. En «Hoy», todo queda como en la evaluación integral.""")
    filas_sup = []
    for tec_ in CUATRO:
        for p in sa.PALANCAS[tec_]:
            v = [("sí" if x else "no") if p.get("tipo") == "toggle" else f"{x:g}" for x in p["niveles"]]
            filas_sup.append({"Tecnología": tec_, "Palanca": p["etiqueta"], "Hoy": v[0], "Avance esperado": v[1], "Gran salto": v[2]})
    st.dataframe(filas_sup, width="stretch", hide_index=True)
