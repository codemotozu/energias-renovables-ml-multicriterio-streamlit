# -*- coding: utf-8 -*-
"""Tablero del proyecto integrador. Ejecutar desde la raíz del repositorio con:  streamlit run dashboard/app.py"""
import streamlit as st

st.set_page_config(page_title="Renovables: desempeño integral", page_icon=":material/bolt:", layout="wide")

from comun import inyectar_estilos  # noqa: E402

inyectar_estilos()

pagina = st.navigation({
    "La historia": [
        st.Page("vistas/inicio.py", title="1. La pregunta y la respuesta", icon=":material/help:", default=True),
        st.Page("vistas/panorama.py", title="2. Panorama de las plantas", icon=":material/public:"),
    ],
    "Los modelos": [
        st.Page("vistas/modelos.py", title="3. Qué modelo y qué variables", icon=":material/query_stats:"),
        st.Page("vistas/prediccion.py", title="4. Predicción en vivo", icon=":material/bolt:"),
        st.Page("vistas/segmentacion.py", title="5. Segmentación", icon=":material/scatter_plot:"),
    ],
    "La decisión": [
        st.Page("vistas/integral.py", title="6. Evaluación integral", icon=":material/balance:"),
        st.Page("vistas/pais.py", title="7. Qué le conviene a cada país", icon=":material/flag:"),
        st.Page("vistas/geotermica.py", title="8. ¿Y si la geotérmica despega?", icon=":material/volcano:"),
    ],
    "Respaldo": [st.Page("vistas/metodo.py", title="9. Método y limitaciones", icon=":material/menu_book:")],
})

with st.sidebar:
    st.caption("Carolina Rodríguez Chacón · Maestría en Inteligencia Artificial · Universidad de La Salle · "
               "Ciencia de Datos, 2026-2 · Docente: Fabián Camilo Castro Riveros")

pagina.run()
