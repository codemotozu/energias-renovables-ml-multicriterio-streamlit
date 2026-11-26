# -*- coding: utf-8 -*-
"""Tablero del proyecto integrador. Ejecutar desde la raíz del repositorio con:  streamlit run dashboard/app.py"""
import importlib
import sys
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Renovables: desempeño integral", page_icon=":material/bolt:", layout="wide")

ORDEN_RECARGA = ["datos", "preprocesamiento", "multicriterio", "trayectoria", "geotermica", "paises", "saltos"]


def recargar_paquete():
    """Streamlit solo recarga los módulos de dashboard/. Tras cada push, recarga también los de src/renovables que cambiaron,
    para que el servidor no siga usando una versión vieja en memoria."""
    nombres = [n for n in sys.modules if n.startswith("renovables.")]
    for nombre in sorted(nombres, key=lambda n: ORDEN_RECARGA.index(n.split(".")[1]) if n.split(".")[1] in ORDEN_RECARGA else len(ORDEN_RECARGA)):
        modulo = sys.modules[nombre]
        archivo = getattr(modulo, "__file__", None)
        if not archivo or not Path(archivo).exists():
            continue
        fecha = Path(archivo).stat().st_mtime
        if getattr(modulo, "_fecha_cargada", None) != fecha:
            importlib.reload(modulo)
            modulo._fecha_cargada = fecha


recargar_paquete()
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
    ],
    "Cara al futuro": [
        st.Page("vistas/geotermica.py", title="8. ¿Y si la geotérmica despega?", icon=":material/volcano:"),
        st.Page("vistas/saltos.py", title="9. ¿Y si cada una da su gran salto?", icon=":material/rocket_launch:"),
    ],
    "Respaldo": [st.Page("vistas/metodo.py", title="10. Método y limitaciones", icon=":material/menu_book:")],
})

with st.sidebar:
    st.caption("Carolina Rodríguez Chacón · Maestría en Inteligencia Artificial · Universidad de La Salle · "
               "Ciencia de Datos, 2026-2 · Docente: Fabián Camilo Castro Riveros")

pagina.run()
