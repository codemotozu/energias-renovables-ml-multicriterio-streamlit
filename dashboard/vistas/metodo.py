# -*- coding: utf-8 -*-
import streamlit as st

from comun import ENLACE_REPOSITORIO, PREGUNTA, encabezado, metricas, resumen

encabezado("Método y limitaciones", "¿De dónde salen estos resultados y hasta dónde se puede confiar en ellos?")
m, r = metricas(), resumen()

st.markdown(f"**Pregunta principal:** {PREGUNTA}")
st.markdown("""
| Pregunta secundaria | Técnica | Resultado |
|---|---|---|
| **PS1.** ¿Cuánto explican la tecnología, la capacidad, la ubicación y la antigüedad el rendimiento? | Regresión | R² = 0.623 en prueba (IC 95 %: 0.573–0.669) |
| **PS2.** ¿Se puede clasificar el nivel de desempeño sin usar la generación? | Clasificación | F1-macro = 0.760 (IC 95 %: 0.734–0.786) |
| **PS3.** ¿Qué grupos naturales de plantas existen? | Clustering | 2 grupos; silueta = 0.297 (meta de 0.35 no alcanzada) |
""")

a, b = st.columns(2)
with a:
    st.subheader("Datos")
    st.markdown("""
- **Global Power Plant Database v1.3.0** (WRI), CC BY 4.0: plantas, capacidad, ubicación y generación hasta 2019.
- **IRENASTAT 2026-H2:** capacidad y generación por país y tecnología.
- **NASA POWER:** climatología 2001–2025 de radiación, viento y lluvia, y datos horarios 2022–2024 de seis países.
- **IRENA, IPCC, IEA, DOE y Lovering et al. (2022):** costos, emisiones, minerales, materiales y uso de suelo.
""")
    st.subheader("Cuidado metodológico")
    st.markdown("""
- Partición 70/15/15 agrupada por sitio: una misma central nunca queda en entrenamiento y prueba.
- Preprocesamiento dentro del *pipeline*, ajustado solo con entrenamiento, para evitar fuga de datos.
- Hiperparámetros con validación cruzada; modelo elegido en validación; prueba usada una sola vez.
- Robustez: 10 particiones, validación por bloques geográficos e intervalos *bootstrap*.
- Semilla 42 y huella SHA-256 de los datos.
""")
with b:
    st.subheader("Limitaciones")
    st.markdown("""
1. **Sesgo geográfico:** el 88 % de las plantas con generación está en EE. UU.; fuera de allí el R² baja a 0.41.
2. **Faltan variables** decisivas para la hidroeléctrica y la biomasa: hidrología, tipo de central, combustible y despacho.
3. **Datos hasta 2019:** el rendimiento actual de la solar y la eólica probablemente es mayor.
4. **La recomendación por país es orientativa:** no incluye red, demanda, financiamiento ni política.
5. **El recurso eólico de NASA no predijo** el rendimiento entre países; donde no hay parques, la eólica usa el valor mundial.
6. **El costo local es una aproximación:** supone que invertir cuesta lo mismo en todos los países.
7. **El escenario geotérmico es hipotético:** su costo es una meta de la industria. La simulación horaria supone un consumo constante y no incluye la red, la hidroeléctrica ni el gas.
8. **Datos de IRENA depurados:** se descartaron 25 FP solares y 8 eólicos físicamente imposibles. El filtro eólico se definió después de ver los datos y no cambió el número de países por tecnología.
9. **El clustering** no alcanza la meta de silueta: las plantas forman un continuo.
""")
    st.subheader("Trabajo futuro")
    st.markdown("""
- Medir el recurso eólico a la altura de la turbina con mayor resolución.
- Sumar generación de más países e hidrología.
- Agregar red, demanda y costo de capital por país.
""")
if ENLACE_REPOSITORIO:
    st.link_button("Ver el código en GitHub", ENLACE_REPOSITORIO)
