# -*- coding: utf-8 -*-
"""Arma el guion del video (HTML y PDF en formato de celular): imagen de lo que debe verse, lo que haces y lo que dices.

Uso: python reports/guion_video/construir_guion.py
Requiere PyMuPDF, Pillow y Playwright (Microsoft Edge). Antes, capturar_tablero.py debe haber guardado las capturas.
"""
import html
import sys
from pathlib import Path

import pymupdf
from PIL import Image
from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(AQUI))
import recortar_informe as ri  # noqa: E402

IMG, CAPT = AQUI / "img", AQUI / "capturas"
PDF_SALIDA = RAIZ / "reports" / "Guion_Video_Fase4.pdf"
PALABRAS_POR_SEGUNDO = 2.3          # unas 140 palabras por minuto, ritmo tranquilo
SEGUNDOS_POR_ACCION = 6             # tiempo para hacer clic, cambiar de pestaña o esperar a que cargue
TABLERO = "https://renewable-energy-performance.streamlit.app"
REPO = "https://github.com/codemotozu/energias-renovables-ml-multicriterio-streamlit"
INFORME = "Ciencia_de_Datos_Fase4_Actividades_7_8_y_9_Rodriguez_Chacon_Carolina.pdf"

# Recortes de las capturas del tablero (x0, y0, x1, y1, en píxeles de la captura)
RECORTES = {"vista1": (540, 90, 2060, 1500), "vista4": (540, 120, 2060, 990), "vista6": (540, 120, 2060, 1400),
            "vista7": (540, 2120, 2060, 3320), "vista9": (540, 2120, 2060, 3020), "github": (160, 280, 1530, 1420)}

# (sección, paso)  ·  cada paso: etiqueta, imagen, pie, acciones (HAZ) y texto (LO QUE DICES)
PASOS = [
    ("Saludo y presentación", dict(
        etiqueta="Portada", img="portada", pie="<b>Portada</b> · página {portada} del informe",
        dices="Cordial saludo, profesor Fabián. Soy Carolina Rodríguez Chacón, de la Maestría en Inteligencia Artificial. Le presento mi proyecto "
              "integrador de Ciencia de Datos: qué energía renovable tiene el mejor desempeño integral, con aprendizaje automático, análisis "
              "multicriterio y un tablero de decisión construido con 24 794 plantas.")),
    ("Pregunta y objetivos", dict(
        etiqueta="Tabla I", img="tabla1", pie="<b>Tabla I</b> · página {tabla1} del informe",
        dices="Mi pregunta es qué tecnología renovable tiene el mejor desempeño integral a escala de planta y qué factores técnicos y geográficos "
              "explican las diferencias entre plantas. La Tabla I muestra mis cuatro objetivos con su meta: cumplí tres. La meta de segmentación "
              "no la alcancé, y más adelante explico por qué.")),
    ("Los datos", dict(
        etiqueta="Tabla II", img="tabla2", pie="<b>Tabla II</b> · página {tabla2} del informe",
        dices="Uso la Global Power Plant Database del World Resources Institute, con licencia abierta, y la completo con IRENA, NASA POWER y "
              "fuentes de costos, emisiones, minerales y uso de suelo. La Tabla II resume para qué usé cada una.")),
    ("Los datos", dict(
        etiqueta="Fig. 1", img="fig1", pie="<b>Fig. 1</b> · página {fig1} del informe",
        dices="Mi métrica es el factor de planta: qué parte de la energía máxima posible entrega una planta. En la figura 1, la geotérmica y la "
              "biomasa rinden más por MW y la solar menos, pero la solar y la eólica son las más estables de un año a otro. El gran reto de "
              "calidad es que el 76 % de las plantas no reporta generación, y el 88 % de las que sí, está en Estados Unidos. No imputé esa "
              "variable, porque sería inventar justo lo que quiero predecir.")),
    ("Los modelos", dict(
        etiqueta="Tabla III", img="tabla3", pie="<b>Tabla III</b> · página {tabla3} del informe",
        dices="Quedaron 6 011 plantas, partidas 70, 15 y 15 por sitio, para que una misma central nunca quede en entrenamiento y en prueba a la "
              "vez; la prueba la usé una sola vez. En la Tabla III comparé modelos lineales regularizados, SVM, Random Forest, XGBoost y una red "
              "neuronal en PyTorch. Ganó Random Forest en las dos tareas: R cuadrado de 0,623 frente a 0,449 del modelo base, y F1 de 0,760 "
              "frente a 0,671.")),
    ("Los modelos", dict(
        etiqueta="Fig. 3", img="fig3", pie="<b>Fig. 3</b> · página {fig3} del informe",
        dices="La figura 3 muestra dónde falla: el error es mayor en la biomasa, la hidroeléctrica y la geotérmica, porque me faltan datos de "
              "hidrología, combustible y despacho.")),
    ("Los modelos", dict(
        etiqueta="Fig. 4", img="fig4", pie="<b>Fig. 4</b> · página {fig4} del informe",
        dices="Y la figura 4 explica qué pesa más en la predicción: la tecnología es lo más importante, seguida de la edad de la planta y su "
              "ubicación.")),
    ("Segmentación", dict(
        etiqueta="Fig. 5", img="fig5", pie="<b>Fig. 5</b> · página {fig5} del informe",
        dices="Sin decirle la tecnología, K-Means encontró dos grupos: un parque antiguo, casi todo hidroeléctrico y variable, y uno nuevo, solar "
              "y eólico, muy estable. La silueta fue 0,297 y no alcancé mi meta de 0,35: las plantas forman más un continuo que grupos nítidos, "
              "y preferí reportarlo así en vez de forzar el resultado.")),
    ("Evaluación integral", dict(
        etiqueta="Tabla IV", img="tabla4", pie="<b>Tabla IV</b> · página {tabla4} del informe",
        dices="Rendir mucho no basta. Combiné 14 criterios en cinco pilares, como costo, emisiones, terreno, minerales, reciclaje y trayectoria, "
              "en 20 000 escenarios con pesos al azar. La Tabla IV muestra que la solar queda primera en el 45,7 % de los escenarios y la eólica "
              "en el 35,9 %. Ninguna gana en todo: la hidroeléctrica lidera en materiales y la geotérmica, en confiabilidad.")),
    ("Evaluación integral", dict(
        etiqueta="Fig. 6", img="fig6", pie="<b>Fig. 6</b> · página {fig6} del informe",
        dices="La figura 6 muestra que con TOPSIS el orden se mantiene, y que la eólica es la más consistente: queda entre las dos mejores en el "
              "83 % de los escenarios.")),
    ("Qué conviene a cada país", dict(
        etiqueta="Fig. 7", img="fig7", pie="<b>Fig. 7</b> · página {fig7} del informe",
        dices="Para cada país usé el rendimiento real de IRENA y el recurso de NASA. En la figura 7, la radiación sí predice el rendimiento solar, "
              "con rho de 0,72, pero el viento no, así que no lo usé y lo reporto como un hallazgo honesto.")),
    ("Qué conviene a cada país", dict(
        etiqueta="Fig. 8", img="fig8", pie="<b>Fig. 8</b> · página {fig8} del informe",
        dices="El resultado está en la figura 8: la solar se recomienda en 141 de 166 países y la eólica en 25. Pero el mapa usa promedios "
              "anuales, y en 23 países del norte el invierno es muy oscuro; más adelante lo muestro en el tablero.")),
    ("Cara al futuro", dict(
        etiqueta="Fig. 9", img="fig9", pie="<b>Fig. 9</b> · página {fig9} del informe",
        dices="Me pregunté qué pasaría si la geotérmica con ondas milimétricas fuera un hecho. En la figura 9a, pasaría del 4 % al primer lugar, "
              "pero solo si llega a todos los países, crece como la eólica y cuesta menos de 39 dólares por MWh. Su valor real es entregar "
              "energía a toda hora: en la 9c, lograr lo mismo con solar, eólica y baterías cuesta entre 52 y 129 dólares por MWh. Y si despega "
              "en 2030, la 9d muestra unos 780 GW en 2050.")),
    ("Cara al futuro", dict(
        etiqueta="Fig. 11", img="fig11", pie="<b>Fig. 11</b> · página {fig11} del informe",
        dices="¿Y si todas las renovables mejoran? En la figura 11a, si solo la solar da un gran salto, queda primera en el 80 % de los "
              "escenarios; si todas lo dan a la vez, baja al 49 %. La 11b muestra que, si se prioriza la confiabilidad, gana la geotérmica "
              "madura. No hay una ganadora única: lo más probable es que se complementen.")),
    ("Demostración del tablero", dict(
        etiqueta="Tablero", img="vista1", pie="<b>Vista 1</b> · La pregunta y la respuesta",
        haz=["pasa a la segunda pestaña del navegador, la del tablero, en la vista «1. La pregunta y la respuesta»."],
        dices="Todo esto se puede explorar en el tablero que publiqué en Streamlit. Tiene diez vistas, y la primera pantalla responde la pregunta "
              "con los indicadores principales.")),
    ("Demostración del tablero", dict(
        etiqueta="Tablero", img="vista4", pie="<b>Vista 4</b> · Predicción en vivo",
        haz=["abre «4. Predicción en vivo» y elige Eólica, Estados Unidos y 100 MW, con el año en 2019.",
             "cuando hayas dicho la primera frase, mueve el año a 2000."],
        dices="En Predicción en vivo puedo evaluar una planta antes de construirla: una eólica de 100 MW en Estados Unidos tendría un factor de "
              "planta de 0,35 y unos 306 GWh al año. Si fuera del año 2000, bajaría a cerca de 0,27: el modelo aprendió el avance de las "
              "turbinas.")),
    ("Demostración del tablero", dict(
        etiqueta="Tablero", img="vista6", pie="<b>Vista 6</b> · Evaluación integral con mis prioridades",
        haz=["abre «6. Evaluación integral», marca «Definir mis prioridades», sube Materiales y circularidad a 5 y baja los demás pilares a 1."],
        dices="En Evaluación integral puedo poner mis propias prioridades: si lo que más importa son los materiales y el reciclaje, gana la "
              "hidroeléctrica en el 93 % de los escenarios.")),
    ("Demostración del tablero", dict(
        etiqueta="Tablero", img="vista7", pie="<b>Vista 7</b> · Análisis de un país: Alemania",
        haz=["abre «7. Qué le conviene a cada país», baja hasta «Análisis de un país» y elige Alemania."],
        dices="En la vista por país, a Alemania se le recomienda la solar, pero el tablero advierte que en diciembre llega solo el 19 % del sol "
              "promedio: allí la solar necesita el respaldo de otras fuentes en invierno.")),
    ("Demostración del tablero", dict(
        etiqueta="Tablero", img="vista9", pie="<b>Vista 9</b> · ¿Quién gana según lo que más importe?",
        haz=["abre «9. ¿Y si cada una da su gran salto?», entra a la pestaña 3, activa «Sumar la geotérmica madura de la vista 8» y baja hasta "
             "«¿Quién gana según lo que más importe?»."],
        dices="Y en la vista 9 está la carrera entre todas: según lo que más se valore, gana una tecnología distinta.")),
    ("Reproducibilidad", dict(
        etiqueta="GitHub", img="github", pie="<b>Repositorio</b> en GitHub",
        haz=["pasa a la tercera pestaña, la del repositorio en GitHub."],
        dices="Todo es reproducible: el código, los datos, los cuadernos y las pruebas automáticas están en GitHub, con semilla 42 y "
              "verificación entre fases. El informe tiene los enlaces al tablero, al repositorio y a los cuadernos en Colab.")),
    ("Conclusiones", dict(
        etiqueta="Sección VII", img="conclusiones", pie="<b>Sección VII</b> · página {conclusiones} del informe",
        haz=["vuelve a la primera pestaña, la del PDF del informe, en la sección VII."],
        dices="En conclusión: de manera holística, la solar y la eólica tienen el mejor desempeño integral; la tecnología, la edad y la ubicación "
              "explican el rendimiento de una planta; y cada país necesita su propia combinación. Mis principales límites son el sesgo hacia "
              "Estados Unidos, la falta de datos de hidrología y que el mapa por país no ve las estaciones. Aprendí que un buen promedio puede "
              "esconder lo importante, y que una meta no cumplida, bien explicada, también es un resultado. Muchas gracias, profesor.")),
]


def recortar_capturas():
    for nombre, caja in RECORTES.items():
        Image.open(CAPT / f"{nombre}.png").crop(caja).save(IMG / f"{nombre}.png")


def recortar_pdf():
    IMG.mkdir(exist_ok=True)
    doc = pymupdf.open(ri.PDF)
    paginas = {"portada": ri.portada(doc, "portada"), "conclusiones": ri.conclusiones(doc, "conclusiones")}
    for romano, nombre in (("I", "tabla1"), ("II", "tabla2"), ("III", "tabla3"), ("IV", "tabla4")):
        paginas[nombre] = ri.tabla(doc, romano, nombre)
    for n in (1, 3, 4, 5, 6, 7, 8, 9, 11):
        paginas[f"fig{n}"] = ri.figura(doc, n, f"fig{n}")
    return paginas


def mmss(s):
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def segundos(paso):
    return len(paso["dices"].split()) / PALABRAS_POR_SEGUNDO + SEGUNDOS_POR_ACCION * len(paso.get("haz", []))


def armar_html(paginas):
    # tiempos por sección
    secciones, t = [], 0.0
    for sec, paso in PASOS:
        if not secciones or secciones[-1][0] != sec:
            secciones.append([sec, t, t, []])
        t += segundos(paso)
        secciones[-1][2] = t
        secciones[-1][3].append(paso)
    total = t
    partes = [f"""<h1>Guion del video</h1>
<p class="sub">Proyecto integrador · Ciencia de Datos · Fase 4 · {len(PASOS)} pasos · duración estimada <b>{mmss(total)}</b> leyendo a ritmo
tranquilo. En cada paso: la imagen de lo que debe verse en pantalla, en amarillo lo que haces y con la barra verde lo que dices.</p>
<div class="caja"><b>Cómo grabar:</b> OBS Studio, Clipchamp (Grabar → Pantalla, con micrófono) o la Herramienta Recortes en modo video,
siempre con la <b>pantalla completa</b>. Antes de grabar, deja abiertos, en este orden:
<ol><li>El PDF del informe: <code>{INFORME}</code>.</li>
<li>El tablero: <a href="{TABLERO}">{TABLERO.replace('https://', '')}</a>. Recorre las vistas una vez para que carguen.</li>
<li>El repositorio: <a href="{REPO}">{REPO.replace('https://', '')}</a>.</li></ol>
Sube el video a OneDrive (o Google Drive), compártelo con «Cualquier persona con el vínculo puede ver», ábrelo en una ventana de incógnito para
comprobar que se reproduce sin iniciar sesión y pega el enlace en la actividad.</div>"""]
    n = 0
    for sec, t0, t1, pasos in secciones:
        partes.append(f'<div class="seccion"><span class="pildora">{mmss(t0)}–{mmss(t1)}</span><h2>{html.escape(sec)}</h2></div>')
        for p in pasos:
            n += 1
            pie = p["pie"].format(**paginas)
            donde = f" · PÁGINA {paginas[p['img']]} DEL INFORME" if p["img"] in paginas else ""
            partes.append(f'<div class="paso">PASO {n} · {html.escape(p["etiqueta"]).upper()}{donde}</div>')
            partes.append(f'<div class="figura"><img src="img/{p["img"]}.png" alt=""><div class="pie">{pie}</div></div>')
            for h in p.get("haz", []):
                partes.append(f'<div class="haz"><b>HAZ:</b> {html.escape(h)}</div>')
            partes.append(f'<div class="dices"><div class="etq">LO QUE DICES</div><p>{html.escape(p["dices"])}</p></div>')
    partes.append("""<div class="caja consejos"><b>Consejos:</b> habla con calma; si te equivocas, pausa y sigue (se puede cortar después).
Mientras explicas una tabla o figura, señálala con el mouse. Para ir a una página del PDF, escribe su número en la casilla de páginas del visor.
Si el tablero muestra que se durmió por inactividad, pulsa el botón para despertarlo y espera un minuto antes de grabar. Revisa la duración
del video antes de subirlo.</div>""")
    css = """
@page { size: 4.3in 9in; margin: 0.32in 0.3in 0.42in 0.3in; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", system-ui, sans-serif; color: #1f2328; margin: 0; }
h1 { color: #0b6b4a; font-size: 29pt; line-height: 1.08; margin: 0 0 8px; }
.sub { color: #5f5f5f; font-size: 13pt; line-height: 1.4; margin: 0 0 14px; }
.caja { background: #f2f1ee; border-radius: 14px; padding: 14px 16px; font-size: 12.2pt; line-height: 1.45; }
.caja ol { margin: 6px 0 8px; padding-left: 20px; } .caja li { margin: 3px 0; }
.caja code { background: #e6e4df; border-radius: 4px; padding: 0 3px; font-size: 10pt; word-break: break-all; }
.caja a { color: #0b6b4a; word-break: break-all; }
.consejos { background: #fdf3d7; margin-top: 18px; }
.seccion { display: flex; align-items: center; gap: 10px; margin: 22px 0 6px; break-after: avoid; page-break-after: avoid; }
.pildora { background: #0b6b4a; color: #fff; border-radius: 20px; padding: 5px 12px; font-weight: 700; font-size: 13pt; white-space: nowrap; }
.seccion h2 { font-size: 18pt; line-height: 1.1; margin: 0; }
.paso { color: #0b6b4a; font-weight: 800; font-size: 11pt; letter-spacing: .2px; margin: 14px 0 6px; break-after: avoid; page-break-after: avoid; }
.figura { background: #f2f1ee; border-radius: 14px; padding: 10px; text-align: center; break-inside: avoid; page-break-inside: avoid; }
.figura img { max-width: 100%; max-height: 4.9in; border: 1px solid #dcdad5; background: #fff; }
.figura .pie { font-size: 11pt; color: #555; margin-top: 6px; }
.haz { background: #fdf3d7; border-radius: 12px; padding: 10px 14px; font-size: 13pt; line-height: 1.4; margin: 10px 0; break-inside: avoid; }
.haz b { color: #8a5a00; }
.dices { border-left: 5px solid #1fae7a; padding: 2px 0 2px 14px; margin: 10px 0 4px; }
.dices .etq { color: #1fae7a; font-weight: 800; font-size: 11pt; letter-spacing: .3px; }
.dices p { font-size: 16.5pt; line-height: 1.45; margin: 4px 0; }
"""
    doc = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Guion del video · Fase 4</title><style>{css}</style></head>
<body>{''.join(partes)}</body></html>"""
    (AQUI / "guion_video.html").write_text(doc, encoding="utf-8")
    return total, secciones


def a_pdf():
    pie = '<div style="width:100%;text-align:center;font-size:9px;color:#666;font-family:Segoe UI"><span class="pageNumber"></span> / <span class="totalPages"></span></div>'
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page()
        pg.goto((AQUI / "guion_video.html").as_uri(), wait_until="networkidle")
        pg.pdf(path=str(PDF_SALIDA), width="4.3in", height="9in", print_background=True, display_header_footer=True,
               header_template="<div></div>", footer_template=pie, prefer_css_page_size=True)
        b.close()


if __name__ == "__main__":
    paginas = recortar_pdf()
    recortar_capturas()
    total, secciones = armar_html(paginas)
    a_pdf()
    for sec, t0, t1, _ in secciones:
        print(f"{mmss(t0)}–{mmss(t1)}  {sec}")
    print(f"Duración estimada: {mmss(total)} | PDF: {PDF_SALIDA.name} | páginas: {pymupdf.open(PDF_SALIDA).page_count}")
