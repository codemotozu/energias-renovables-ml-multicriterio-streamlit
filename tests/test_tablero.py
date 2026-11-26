# -*- coding: utf-8 -*-
"""Pruebas del tablero con el probador oficial de Streamlit (AppTest).

Cada prueba abre una vista, mueve sus controles (incluidos casos límite como filtros vacíos o todos los pesos
en cero) y falla si la vista lanza una excepción. Ejecutar desde la raíz del repositorio:  pytest tests -v
"""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "dashboard"))          # las vistas importan comun.py como lo hace `streamlit run`
APP = str(RAIZ / "dashboard" / "app.py")
VISTAS = ["inicio", "panorama", "modelos", "prediccion", "segmentacion", "integral", "pais", "geotermica", "saltos", "metodo"]
ESPERA = 240                                          # segundos por ejecución; la primera carga entrena cachés


def abrir(vista):
    at = AppTest.from_file(APP, default_timeout=ESPERA)
    at.run()
    if vista != "inicio":
        at.switch_page(f"vistas/{vista}.py")
        at.run()
    return at


def paso(at, nombre):
    errores = [e.value for e in at.exception]
    assert not errores, f"{nombre}: " + " | ".join(e[:500] for e in errores)


def control(lista, etiqueta):
    return next(w for w in lista if w.label.startswith(etiqueta))


@pytest.mark.parametrize("vista", VISTAS)
def test_vista_carga_sin_errores(vista):
    paso(abrir(vista), f"abrir {vista}")


def test_panorama_filtros():
    at = abrir("panorama")
    control(at.multiselect, "Tecnología").set_value(["Geotérmica"]).run(); paso(at, "solo geotérmica")
    control(at.multiselect, "Tecnología").set_value([]).run(); paso(at, "sin tecnología (vacío)")
    control(at.multiselect, "Tecnología").set_value(["Solar"]).run()
    control(at.multiselect, "Región").set_value(["África al sur del Sahara"]).run(); paso(at, "solar en África")
    control(at.slider, "Factor").set_value((0.95, 1.0)).run(); paso(at, "filtro casi vacío")


def test_prediccion_controles():
    at = abrir("prediccion")
    for tec in ["Eólica", "Hidroeléctrica", "Geotérmica", "Biomasa"]:
        control(at.selectbox, "Tecnología").set_value(tec).run(); paso(at, tec)
    control(at.selectbox, "País").set_value("Estados Unidos").run(); paso(at, "EE. UU.")
    control(at.number_input, "Capacidad").set_value(5000.0).run(); paso(at, "capacidad máxima")
    control(at.slider, "Año").set_value(1950).run(); paso(at, "año mínimo")
    control(at.toggle, "Ajustar").set_value(True).run(); paso(at, "coordenadas manuales")
    control(at.selectbox, "País").set_value("Islandia").run(); paso(at, "cambia país con coordenadas manuales")


def test_segmentacion_controles():
    at = abrir("segmentacion")
    control(at.selectbox, "Vista").set_value("3D").run(); paso(at, "3D")
    control(at.selectbox, "Colorear").set_value("Tecnología").run(); paso(at, "color por tecnología")
    at.checkbox[0].set_value(True).run(); paso(at, "plantas atípicas")
    control(at.multiselect, "Tecnología").set_value(["Geotérmica"]).run(); paso(at, "atípicas geotérmicas")


def test_integral_controles():
    at = abrir("integral")
    at.radio[0].set_value("Definir mis prioridades").run(); paso(at, "mis prioridades")
    for s in at.slider:
        s.set_value(0)
    at.run(); paso(at, "todos los pilares en cero")
    at.slider[3].set_value(5).run(); paso(at, "solo materiales")
    control(at.selectbox, "Método").set_value("TOPSIS").run(); paso(at, "TOPSIS")
    control(at.toggle, "Contar").set_value(False).run(); paso(at, "sin baterías")
    control(at.selectbox, "¿Energía").set_value("Por material (GWh por 1 000 t)").run(); paso(at, "energía por material")


def test_pais_controles():
    at = abrir("pais")
    paises = control(at.selectbox, "País").options
    for p in ["Argentina", "Islandia", "Noruega", "Singapur", "Kenia", paises[0], paises[-1]]:
        control(at.selectbox, "País").set_value(p).run(); paso(at, p)
    control(at.selectbox, "Método").set_value("TOPSIS").run(); paso(at, "TOPSIS")
    for e in control(at.selectbox, "Escenario").options:
        control(at.selectbox, "Escenario").set_value(e).run(); paso(at, f"escenario {e}")
    control(at.multiselect, "Filtrar").set_value(["América Latina y el Caribe"]).run(); paso(at, "filtro de región")


def test_geotermica_escenario():
    at = abrir("geotermica")
    control(at.toggle, "Viable").set_value(False).run(); paso(at, "no viable en todos los países")
    control(at.slider, "Costo").set_value((15, 100)).run(); paso(at, "rango de costo extremo")


def test_saltos_controles():
    at = abrir("saltos")
    assert len(at.tabs) == 3, "la vista debe tener sus tres pestañas"
    for tec in ["Eólica", "Hidroeléctrica", "Biomasa", "Solar"]:
        control(at.button_group, "Tecnología").set_value(tec).run(); paso(at, f"salto de {tec}")
        for nivel in ["Hoy", "Avance esperado"]:
            control(at.button_group, "Punto de partida").set_value(nivel).run(); paso(at, f"{tec}: {nivel}")
    control(at.slider, "Cambio del costo").set_value(-80).run(); paso(at, "costo mínimo")
    control(at.slider, "Eficiencia").set_value(45).run(); paso(at, "eficiencia máxima")
    control(at.button_group, "Tecnología").set_value("Biomasa").run()
    control(at.toggle, "Captura").set_value(True).run(); paso(at, "biomasa con captura de carbono")
    control(at.toggle, "Crece").set_value(True).run(); paso(at, "biomasa crece como la solar")
    control(at.button_group, "Nivel para todas").set_value("Avance esperado").run(); paso(at, "todas: avance esperado")
    control(at.toggle, "Sumar la geotérmica").set_value(True).run(); paso(at, "todas con la geotérmica madura")


def test_geotermica_operacion():
    at = abrir("geotermica")
    for p in control(at.selectbox, "País de estudio").options:
        control(at.selectbox, "País de estudio").set_value(p).run(); paso(at, p)
    control(at.selectbox, "Alternativa").set_value("Solar + baterías").run(); paso(at, "solar + baterías")
    assert len(at.tabs) == 3, "la vista debe tener las tres pestañas de preguntas"
