# -*- coding: utf-8 -*-
import streamlit as st

from comun import PREGUNTA, barras_puestos, criterios, fmt, metricas, mostrar, plantas, recomendaciones, resumen, simular_global

m, r = metricas(), resumen()
d = criterios()
rec = recomendaciones()
hoy = rec[rec["escenario"].str.startswith("Hoy")]
n_solar, n_eolica = int((hoy["recomendada"] == "Solar").sum()), int((hoy["recomendada"] == "Eólica").sum())
n_clara = int((hoy["certeza"] == "Clara").sum())
mc_ = m["multicriterio"]

st.markdown('<div class="etiqueta">Pregunta de investigación</div>', unsafe_allow_html=True)
st.markdown(f'<div class="pregunta-principal">{PREGUNTA}</div>', unsafe_allow_html=True)
st.markdown(f"""<p class="respuesta"><b>La solar y la eólica</b>, de forma compartida. Al combinar 14 criterios en 20 000 escenarios,
la solar queda primera en el {mc_['Solar']['% n.º 1 (SAW)']:.1f} % y la eólica en el {mc_['Eólica']['% n.º 1 (SAW)']:.1f} %.
Ninguna es la mejor en todo: ganan porque sus fortalezas en costo, seguridad y trayectoria compensan sus debilidades en vida útil, reciclaje y terreno.
<b>Entre plantas, lo que más explica el rendimiento</b> es la tecnología, seguida de la edad y la ubicación.</p>""",
            unsafe_allow_html=True)

c = st.columns(5)
c[0].metric("Plantas renovables", fmt(r["n_renovables"]), help="Global Power Plant Database v1.3.0 (WRI)")
c[1].metric("Plantas modeladas", fmt(r["n_plantas"]), help="Plantas con generación reportada y factor de planta válido")
c[2].metric("R² en prueba", f"{m['regresion']['prueba']['Random Forest']['R²']:.3f}",
            delta=f"+{m['regresion']['prueba']['Random Forest']['R²'] - m['regresion']['prueba']['Lineal base de la Fase 2']['R²']:.3f} sobre la base")
c[3].metric("F1-macro en prueba", f"{m['clasificacion']['prueba']['Random Forest']['F1-macro']:.3f}",
            delta=f"+{m['clasificacion']['prueba']['Random Forest']['F1-macro'] - m['clasificacion']['prueba']['Logística base de la Fase 2']['F1-macro']:.3f} sobre la base")
c[4].metric("Países evaluados", fmt(r["paises_recomendados"]))

st.subheader("Las tres preguntas prácticas")
a, b, e = st.columns(3)
with a.container(border=True):
    st.markdown('<div class="etiqueta">Ventajas y desventajas</div><div class="tarjeta-p">¿Cuál tiene más pros que contras?</div>'
                '<div class="tarjeta-r">Solar y eólica</div>'
                f'<div class="tarjeta-p">Las dos más baratas ({d.loc["Eólica", "lcoe_2025"]:.0f} y {d.loc["Solar", "lcoe_2025"]:.0f} USD/MWh) y de las más seguras. '
                'Su punto débil es el fin de vida: duran 25 años y casi no se recupera lo valioso de paneles y aspas.</div>', unsafe_allow_html=True)
    st.page_link("vistas/integral.py", label="Ver la evaluación integral", icon=":material/arrow_forward:")
with b.container(border=True):
    st.markdown('<div class="etiqueta">Futuro tecnológico</div><div class="tarjeta-p">¿Cuál tiene mejor proyección?</div>'
                '<div class="tarjeta-r">Eólica y solar</div>'
                f'<div class="tarjeta-p">Son las únicas cuyo rendimiento mundial sube ({d.loc["Eólica", "fp_tend"]:+.1f} y {d.loc["Solar", "fp_tend"]:+.1f} puntos por década). '
                f'La solar crece {d.loc["Solar", "crec_15_24"]:.1f} % al año y su costo cayó {abs(d.loc["Solar", "cambio_costo"]):.0f} % desde 2010.</div>', unsafe_allow_html=True)
    st.page_link("vistas/geotermica.py", label="Ver el escenario geotérmico", icon=":material/arrow_forward:")
with e.container(border=True):
    st.markdown('<div class="etiqueta">Conveniencia por país</div><div class="tarjeta-p">¿Cuál le conviene a cada país?</div>'
                f'<div class="tarjeta-r">Solar en {n_solar} países, eólica en {n_eolica}</div>'
                f'<div class="tarjeta-p">La ventaja es clara en {n_clara} de {len(hoy)} países. En los demás la decisión es más cerrada y depende de las prioridades de cada país.</div>',
                unsafe_allow_html=True)
    st.page_link("vistas/pais.py", label="Elegir un país", icon=":material/arrow_forward:")

st.subheader("En qué puesto queda cada tecnología")
st.caption("Porcentaje de los escenarios en que cada tecnología ocupa cada puesto (suma ponderada, pesos y datos inciertos).")
_, distribucion = simular_global(None, "SAW", True)
mostrar(barras_puestos(distribucion, alto=290))

with st.expander("Cómo recorrer este tablero"):
    st.markdown("""
1. **Panorama:** qué plantas hay, dónde están y cuánto rinden, con filtros.
2. **Modelos:** cuál predice mejor y qué variables pesan más.
3. **Predicción en vivo:** se describe una planta y el modelo estima su rendimiento.
4. **Segmentación:** qué grupos naturales de plantas existen.
5. **Evaluación integral:** se ajustan las prioridades y se ve cómo cambia el ranking.
6. **País:** qué renovable conviene en cada país.
7. **Geotérmica:** qué pasaría, cómo se comportaría y cuál sería su potencial si la perforación con ondas milimétricas funciona.
""")
