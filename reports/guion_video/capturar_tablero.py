# -*- coding: utf-8 -*-
"""Captura las pantallas del tablero que se muestran en el video (página completa; luego se recortan).

Uso: python reports/guion_video/capturar_tablero.py   (requiere playwright con Microsoft Edge)
"""
import subprocess
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = Path(__file__).parent / "capturas"
URL = "http://localhost:8595"
REPO = "https://github.com/codemotozu/energias-renovables-ml-multicriterio-streamlit"


def esperar(pg, ms=5000):
    pg.wait_for_timeout(ms)


def elegir(pg, etiqueta, opcion):
    caja = pg.locator('[data-testid="stSelectbox"]').filter(has_text=etiqueta).first
    caja.click()
    pg.keyboard.type(opcion)
    pg.wait_for_timeout(600)
    pg.get_by_role("option", name=opcion, exact=True).click()
    esperar(pg, 3500)


if __name__ == "__main__":
    SALIDA.mkdir(exist_ok=True)
    srv = subprocess.Popen([str(RAIZ / ".venv" / "Scripts" / "python.exe"), "-m", "streamlit", "run", "dashboard/app.py", "--server.port", "8595",
                            "--server.headless", "true"], cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(90):
            try:
                urllib.request.urlopen(URL + "/_stcore/health", timeout=2)
                break
            except Exception:
                time.sleep(1)
        with sync_playwright() as p:
            b = p.chromium.launch(channel="msedge", headless=True)
            ctx = b.new_context(viewport={"width": 1440, "height": 2400}, color_scheme="light", device_scale_factor=1.5)
            pg = ctx.new_page()

            # Vista 1: la pregunta y la respuesta
            pg.goto(URL + "/", wait_until="networkidle", timeout=120000)
            pg.wait_for_selector('[data-testid="stMetricValue"]', timeout=120000)
            pg.wait_for_selector(".js-plotly-plot", timeout=120000)
            esperar(pg, 6000)
            pg.screenshot(path=str(SALIDA / "vista1.png"))

            # Vista 4: predicción en vivo (Eólica, Estados Unidos, 100 MW, 2019)
            pg.goto(URL + "/prediccion", wait_until="networkidle", timeout=120000)
            pg.wait_for_selector('[data-testid="stSelectbox"]', timeout=120000)
            esperar(pg, 5000)
            elegir(pg, "Tecnología", "Eólica")
            elegir(pg, "País", "Estados Unidos")
            cap = pg.locator('[data-testid="stNumberInput"]').filter(has_text="Capacidad").locator("input")
            cap.fill("100")
            cap.press("Enter")
            esperar(pg, 5000)
            pg.screenshot(path=str(SALIDA / "vista4.png"))

            # Vista 6: mis prioridades, Materiales = 5 y los demás = 1
            pg.goto(URL + "/integral", wait_until="networkidle", timeout=120000)
            pg.wait_for_selector(".js-plotly-plot", timeout=120000)
            esperar(pg, 5000)
            pg.get_by_text("Definir mis prioridades").click()
            esperar(pg, 3000)
            deslizadores = pg.locator('[data-testid="stSlider"] input[type="range"]')   # Streamlit 1.66 usa un rango oculto
            for i in range(deslizadores.count()):
                d = deslizadores.nth(i)
                d.focus()
                tecla = "ArrowRight" if "Materiales" in (d.get_attribute("aria-label") or "") else "ArrowLeft"
                for _ in range(2):                                   # de 3 a 5 (Materiales) o de 3 a 1 (los demás)
                    pg.keyboard.press(tecla)
                    esperar(pg, 1200)
            esperar(pg, 5000)
            pg.screenshot(path=str(SALIDA / "vista6.png"))

            # Vista 7: Alemania (sol mes a mes y aviso de invierno)
            pg.goto(URL + "/pais", wait_until="networkidle", timeout=120000)
            pg.wait_for_selector(".js-plotly-plot", timeout=120000)
            esperar(pg, 5000)
            elegir(pg, "País", "Alemania")
            esperar(pg, 4000)
            pg.screenshot(path=str(SALIDA / "vista7.png"))

            # Vista 9: la carrera con la geotérmica madura
            pg.goto(URL + "/saltos", wait_until="networkidle", timeout=120000)
            pg.wait_for_selector('[role="tab"]', timeout=120000)
            esperar(pg, 6000)
            pg.locator('[role="tab"]').nth(2).click()
            esperar(pg, 2500)
            pg.get_by_text("Sumar la geotérmica madura de la vista 8").click()
            esperar(pg, 6000)
            pg.screenshot(path=str(SALIDA / "vista9.png"))
            print("excepciones en el tablero:", pg.locator('[data-testid="stException"]').count())

            # Repositorio en GitHub
            gh = ctx.new_page()
            gh.set_viewport_size({"width": 1440, "height": 1300})
            gh.goto(REPO, wait_until="networkidle", timeout=120000)
            esperar(gh, 3000)
            gh.screenshot(path=str(SALIDA / "github.png"))
            b.close()
    finally:
        srv.terminate()
    print("ok")
