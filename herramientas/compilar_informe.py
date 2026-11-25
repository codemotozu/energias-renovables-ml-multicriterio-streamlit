# -*- coding: utf-8 -*-
"""Arma el informe final: completa tablas con los datos, ordena la bibliografía por orden de cita y compila con pdflatex."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from renovables import multicriterio as mc  # noqa: E402
from renovables.datos import TECS  # noqa: E402

TEX = RAIZ / "reports" / "articulo_ieee" / "Fase4_Informe_Tecnico_Final_Rodriguez.tex"
PDF_FINAL = RAIZ / "reports" / "Ciencia_de_Datos_Fase4_Actividades_7_8_y_9_Rodriguez_Chacon_Carolina.pdf"
ENLACES = RAIZ / "herramientas" / "enlaces.txt"
REFERENCIAS = RAIZ / "herramientas" / "referencias.json"
NUEVAS = {
    "nasapower": r"NASA Langley Research Center, «POWER: Prediction of Worldwide Energy Resources», climatología 2001--2025 y datos horarios 2022--2024, API v2. [En línea]. Disponible: \url{https://power.larc.nasa.gov/}",
    "catf2022": r"LucidCatalyst y Hotrock Research Organization, \emph{A Preliminary Techno-Economic Model of Superhot Rock Energy}. Boston, MA, EE.\,UU.: Clean Air Task Force, nov. 2022. [En línea]. Disponible: \url{https://cdn.catf.us/wp-content/uploads/2022/12/30135200/SHRTechnoEconomic_Report.pdf}",
    "quaise2025": r"Quaise Energy, «Quaise Energy achieves drilling milestone with millimeter wave technology», 2025. [En línea]. Disponible: \url{https://www.quaise.com/news/quaise-energy-achieves-drilling-milestone-with-millimeter-wave-technology}",
    "iea2024geo": r"Agencia Internacional de la Energía (AIE), \emph{The Future of Geothermal Energy}. París, Francia: IEA, dic. 2024. [En línea]. Disponible: \url{https://www.iea.org/reports/the-future-of-geothermal-energy}",
    "irena2026": r"IRENA, \emph{Renewable Power Generation Costs in 2025}. Abu Dabi, EAU: IRENA, 2026. [En línea]. Disponible: \url{https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2026/Jul/IRENA_TEC_RPGC_in_2025_2026.pdf}",
    "ember2026": r"Ember, \emph{Global Electricity Review 2026}. Londres, R.\,U.: Ember, 2026. [En línea]. Disponible: \url{https://ember-energy.org/latest-insights/global-electricity-review-2026/}",
    "geoinsider2026": r"Geothermal Insider, «Quaise Energy: millimeter-wave drilling profile», 1 sep. 2026. [En línea]. Disponible: \url{https://geothermalinsider.com/learn/quaise-energy/}",
    "streamlit": r"Snowflake Inc., «Streamlit», v1.66.1, biblioteca de código abierto, 2026. [En línea]. Disponible: \url{https://streamlit.io}",
}
PENDIENTE = r"\textit{(Enlace pendiente: se agrega al publicar.)}"


def bibliografia(texto):
    items = {**json.loads(REFERENCIAS.read_text(encoding="utf-8")), **NUEVAS}
    orden = []
    for grupo in re.findall(r"\\cite\{([^}]+)\}", texto):
        for k in grupo.split(","):
            if k.strip() not in orden:
                orden.append(k.strip())
    faltan = [k for k in orden if k not in items]
    if faltan:
        raise SystemExit(f"Referencias sin entrada: {faltan}")
    lineas = "\n".join(f"\\bibitem{{{k}}} {items[k]}" for k in orden)
    return "\\begin{thebibliography}{99}\n\\footnotesize\\setlength{\\itemsep}{0pt}\n" + lineas + "\n\\end{thebibliography}", len(orden)


def tabla_paises():
    r = pd.read_csv(RAIZ / "data" / "processed" / "recomendacion_pais.csv", encoding="utf-8")
    h = r[r["escenario"].str.startswith("Hoy")].set_index("iso3")
    nombres = {"COL": "Colombia", "BRA": "Brasil", "ARG": "Argentina", "CHL": "Chile", "MEX": "México", "USA": "EE.\\,UU.", "DEU": "Alemania",
               "GBR": "Reino Unido", "IND": "India", "KEN": "Kenia"}
    filas = []
    for iso, n in nombres.items():
        f = h.loc[iso]
        filas.append(f"{n} & {f['recomendada']} ({f['pct_primera']:.1f}) & {f['segunda']} ({f['pct_segunda']:.1f}) & {f['certeza']} \\\\")
    return "\n".join(filas)


def tabla_pilares():
    z = pd.read_csv(RAIZ / "data" / "processed" / "matriz_normalizada.csv", index_col=0, encoding="utf-8").loc[TECS]
    nombres = {"Confiabilidad": "Confiabilidad", "Economía y acceso": "Economía y acceso", "Ambiente y seguridad": "Ambiente y seguridad",
               "Materiales y circularidad": "Materiales y circularidad", "Trayectoria y futuro": "Trayectoria"}
    filas = []
    for p in mc.PILARES:
        v = z[[c for c in mc.CRITERIOS if mc.PILAR[c] == p]].mean(axis=1)
        celdas = [f"\\textbf{{{x:.2f}}}" if x == v.max() else f"{x:.2f}" for x in v]
        filas.append(f"{nombres[p]} & " + " & ".join(celdas) + " \\\\")
    return "\n".join(filas)


def enlaces():
    d = {}
    if ENLACES.exists():
        for l in ENLACES.read_text(encoding="utf-8").splitlines():
            if "=" in l:
                k, v = l.split("=", 1)
                d[k.strip()] = v.strip()
    return d


if __name__ == "__main__":
    t = (RAIZ / "herramientas" / "informe_fase4.tex").read_text(encoding="utf-8")
    e = enlaces()
    t = t.replace("%%ENLACE_TABLERO%%", f"\\url{{{e['tablero']}}}" if e.get("tablero") else PENDIENTE)
    t = t.replace("%%ENLACE_REPO%%", f"\\url{{{e['repositorio']}}}" if e.get("repositorio") else PENDIENTE)
    t = t.replace("%%TABLA_PAISES%%", tabla_paises()).replace("%%PILARES%%", tabla_pilares())
    bib, n = bibliografia(t)
    t = t.replace("%%BIBLIOGRAFIA%%", bib)
    TEX.parent.mkdir(parents=True, exist_ok=True)
    TEX.write_text(t, encoding="utf-8")
    salida = ""
    for _ in range(3):
        salida = subprocess.run(["pdflatex", "-interaction=nonstopmode", TEX.name], cwd=TEX.parent, capture_output=True, text=True,
                                encoding="utf-8", errors="replace").stdout
    errores = [l for l in salida.splitlines() if l.startswith("!")]
    pag = re.search(r"Output written on .*?\((\d+) pages", salida)
    avisos = sorted(set(re.findall(r"LaTeX Warning: (?:Citation|Reference) `([^']+)'", salida)))
    print("Páginas:", pag.group(1) if pag else "?", "| referencias:", n, "| errores:", errores[:4], "| sin resolver:", avisos,
          "| overfull:", len(re.findall(r"Overfull \\hbox \((\d{2,})", salida)))
    if pag and not errores:
        shutil.copy(TEX.with_suffix(".pdf"), PDF_FINAL)
