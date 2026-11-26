"""Saltos tecnológicos de la solar, la eólica, la hidroeléctrica y la biomasa (Fase 4, vista exploratoria del tablero).

Cada salto se traduce en cambios de los criterios del multicriterio de la Fase 3 y se evalúa con el mismo Monte Carlo.
Los niveles «Avance esperado» y «Gran salto» son supuestos ilustrativos; los datos reales que los anclan están en FUENTES.
"""
import numpy as np
import pandas as pd

from .multicriterio import ESCENARIOS_GEO
from .paises import recomendar_todos

NIVELES = ["Hoy", "Avance esperado", "Gran salto"]
# Escenarios de futuro por país (vista 7): las cuatro tecnologías dan su salto y la geotérmica es la madura de la vista 8
ESCENARIOS_FUTURO = {"Todas mejoran: avance esperado (y geotérmica madura)": "Avance esperado",
                     "Todas mejoran: gran salto (y geotérmica madura)": "Gran salto"}
GEO_MADURA = "Madura (meta de la industria)"
EFICIENCIA_PANEL_HOY = 23.0        # % de los paneles comerciales de referencia (los mejores rondan el 24–25 %, dic. 2025)
EMISIONES_BECCS = (0.5, 1.0, 5.0)  # gCO2eq/kWh: las emisiones negativas no caben en la escala logarítmica del modelo

DESCRIPCION = {
    "Solar": ("Paneles tándem de perovskita sobre silicio",
              "Una capa de perovskita sobre la celda de silicio aprovecha colores de la luz que el silicio desperdicia. "
              "El récord de laboratorio es 35.5 % (LONGi, julio de 2026), frente a 24–25 % de los mejores paneles comerciales. "
              "El reto pendiente es que la perovskita dure décadas a la intemperie."),
    "Eólica": ("Turbinas gigantes y eólica marina",
               "Rotores más grandes y torres más altas alcanzan vientos más fuertes y constantes, y por eso suben el factor de planta. "
               "La turbina más grande ya conectada tiene 26 MW y un rotor de 310 m (Dongfang, 2025). "
               "Las aspas reciclables atacan su punto débil al final de la vida."),
    "Hidroeléctrica": ("Modernización y bombeo",
                       "Sus turbinas ya aprovechan más del 90 % de la energía del agua: casi no queda margen de eficiencia. "
                       "Su salto es renovar equipos viejos, que recupera de 3 a 6 % de energía, y bombear agua cuesta arriba para guardar "
                       "la energía de la solar y la eólica. Su límite son los ríos y los sitios disponibles."),
    "Biomasa": ("Residuos y captura de carbono",
                "Quemar residuos agrícolas, como el bagazo de caña, en lugar de cultivos sembrados para eso evita ocupar terreno. "
                "Con captura y almacenamiento de carbono (BECCS) podría retirar CO₂ del aire, pero hoy solo hay plantas piloto: "
                "el proyecto más avanzado, Drax (Reino Unido), se retrasó hasta 2030 o después."),
}

# Palancas de cada tecnología: valor en cada nivel (el de «Hoy» deja los criterios exactamente como en la Fase 3)
_COSTO = {"clave": "costo_pct", "etiqueta": "Cambio del costo (%)", "min": -80, "max": 20, "paso": 5,
          "ayuda": "Cambio del costo nivelado frente a 2025. Negativo = más barata."}
_CRECE = {"clave": "crece_como_solar", "etiqueta": "Crece como la solar (26 % al año)", "tipo": "toggle",
          "ayuda": "Supone que se instala al ritmo de la solar en 2015–2024. Para la hidroeléctrica es un supuesto extremo: quedan pocos sitios."}
PALANCAS = {
    "Solar": [
        {"clave": "eficiencia", "etiqueta": "Eficiencia del panel (%)", "min": 23, "max": 45, "paso": 1, "niveles": [23, 30, 40],
         "ayuda": "No cambia las horas de sol ni el factor de planta: reduce el terreno y los materiales por cada MWh."},
        {**_COSTO, "niveles": [0, -40, -60]},
        {"clave": "vida", "etiqueta": "Vida útil (años)", "min": 25, "max": 50, "paso": 1, "niveles": [25, 30, 40], "ayuda": None},
        {"clave": "reciclaje", "etiqueta": "Reciclaje (% de la masa)", "min": 85, "max": 99, "paso": 1, "niveles": [85, 90, 95],
         "ayuda": "Incluye recuperar la plata y el silicio, que hoy casi no se recuperan."},
    ],
    "Eólica": [
        {"clave": "fp", "etiqueta": "Factor de planta", "min": 0.36, "max": 0.60, "paso": 0.01, "niveles": [0.36, 0.42, 0.50],
         "ayuda": "Fracción del año en que entregaría su potencia máxima. Hoy, 0.36 en plantas nuevas (IRENA)."},
        {**_COSTO, "niveles": [0, -25, -50]},
        {"clave": "vida", "etiqueta": "Vida útil (años)", "min": 25, "max": 40, "paso": 1, "niveles": [25, 30, 35], "ayuda": None},
        {"clave": "reciclaje", "etiqueta": "Reciclaje (% de la masa)", "min": 87.5, "max": 99.0, "paso": 0.5, "niveles": [87.5, 92.0, 97.0],
         "ayuda": "Sube con aspas reciclables."},
        {**_CRECE, "niveles": [False, False, False]},
    ],
    "Hidroeléctrica": [
        {"clave": "repotenciacion", "etiqueta": "Energía extra por modernizar (%)", "min": 0, "max": 15, "paso": 1, "niveles": [0, 5, 10],
         "ayuda": "Renovar turbinas recupera de 3 a 6 % de energía en los casos documentados."},
        {**_COSTO, "niveles": [0, -10, -25]},
        {"clave": "vida", "etiqueta": "Vida útil (años)", "min": 50, "max": 100, "paso": 5, "niveles": [50, 60, 80], "ayuda": None},
        {**_CRECE, "niveles": [False, False, False]},
    ],
    "Biomasa": [
        {"clave": "residuos", "etiqueta": "Combustible de residuos (%)", "min": 0, "max": 100, "paso": 5, "niveles": [0, 50, 100],
         "ayuda": "0 = como hoy; 100 = solo residuos agrícolas o forestales, que no ocupan terreno adicional."},
        {"clave": "conversion", "etiqueta": "Mejora de la conversión (%)", "min": 0, "max": 50, "paso": 5, "niveles": [0, 15, 30],
         "ayuda": "Más electricidad por tonelada: menos terreno y menos emisiones por MWh."},
        {"clave": "beccs", "etiqueta": "Captura de carbono (BECCS)", "tipo": "toggle", "niveles": [False, False, True],
         "ayuda": "En el modelo pasa a ser la de menores emisiones. En la realidad podría retirar CO₂, a un costo mayor."},
        {**_COSTO, "niveles": [0, -10, 0]},
        {**_CRECE, "niveles": [False, False, False]},
    ],
}

# ¿Cuánto pueden mejorar todavía? % de la energía disponible que se aprovecha
TECHOS = [
    {"tecnologia": "Solar", "mide": "de la luz del sol que el panel convierte en electricidad", "hoy": (23, 25), "record": 35.5,
     "record_txt": "35.5 %: tándem de laboratorio (2026)", "techo": 45, "techo_txt": "≈ 45 % con dos capas (33.7 % con una sola)"},
    {"tecnologia": "Eólica", "mide": "de la energía del viento que atraviesa el rotor", "hoy": (45, 50), "record": None,
     "record_txt": None, "techo": 59.3, "techo_txt": "59.3 %: límite de Betz"},
    {"tecnologia": "Hidroeléctrica", "mide": "de la energía del agua que la turbina convierte", "hoy": (90, 92), "record": None,
     "record_txt": None, "techo": 100, "techo_txt": "100 %: ya está casi en el techo"},
    {"tecnologia": "Biomasa", "mide": "de la luz del sol que la planta guarda como biomasa", "hoy": (2.4, 3.7), "record": None,
     "record_txt": None, "techo": 6.0, "techo_txt": "4.6–6 %: límite de la fotosíntesis"},
]

FUENTES = [
    ("Récord de la celda tándem (35.5 %)", "pv magazine, 15 de julio de 2026", "https://www.pv-magazine.com/2026/07/15/longi-sets-new-world-record-with-35-5-efficient-perovskite-silicon-tandem-cell/"),
    ("Mejores paneles comerciales (24.8 % en dic. 2025)", "TaiyangNews, Top Solar Modules", "https://taiyangnews.info/technology/top-3-commercial-module-efficiencies"),
    ("Límite de una sola capa (33.7 %)", "W. Shockley y H. J. Queisser, J. Appl. Phys. 32, 510 (1961)", "https://doi.org/10.1063/1.1736034"),
    ("Turbina de 26 MW y rotor de 310 m", "People's Daily / Xinhua, 31 de octubre de 2025", "https://en.people.cn/n3/2025/1031/c90000-20384953.html"),
    ("Límite de Betz (59.3 %) y turbinas actuales (45–50 %)", "Ley de Betz", "https://en.wikipedia.org/wiki/Betz%27s_law"),
    ("Turbinas hidráulicas sobre 90 % y modernización (3–6 %)", "AIIB, Hydropower Modernization (2020)", "https://www.aiib.org/en/news-events/media-center/working-papers/pdf/AIIB-Working-Paper-Hydropower-Modernization_26August2020.pdf"),
    ("Límite de la fotosíntesis (4.6 % y 6 %)", "X.-G. Zhu, S. P. Long y D. R. Ort, Curr. Opin. Biotechnol. 19, 153 (2008)", "https://doi.org/10.1016/j.copbio.2008.02.004"),
    ("Estado de BECCS en Drax", "Ember (2025), Hot air: carbon removals in the UK", "https://ember-energy.org/latest-insights/hot-air-carbon-removals-risk-high-costs-and-underdelivery-in-the-uk/"),
    ("Caída del costo 2010–2025", "IRENA (2026), Renewable Power Generation Costs in 2025", "https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2026/Jul/IRENA_TEC_RPGC_in_2025_2026.pdf"),
]


def valores_nivel(tecnologia, nivel):
    """Valor de cada palanca en uno de los tres niveles."""
    k = NIVELES.index(nivel)
    return {p["clave"]: p["niveles"][k] for p in PALANCAS[tecnologia]}


def aplicar_salto(d, tecnologia, valores):
    """Copia de los criterios con el salto de una tecnología; las demás no cambian."""
    e, t = d.copy().astype(float), tecnologia
    v = valores
    if v.get("costo_pct", 0):
        costo_2010 = d.loc[t, "lcoe_2025"] / (1 + d.loc[t, "cambio_costo"] / 100)
        for c in ("lcoe_2024", "lcoe_2025"):
            e.loc[t, c] = d.loc[t, c] * (1 + v["costo_pct"] / 100)
        e.loc[t, "cambio_costo"] = ((e.loc[t, "lcoe_2024"] + e.loc[t, "lcoe_2025"]) / 2 / costo_2010 - 1) * 100
    fp_nuevo = v.get("fp", d.loc[t, "fp_irena"]) * (1 + v.get("repotenciacion", 0) / 100)
    if not np.isclose(fp_nuevo, d.loc[t, "fp_irena"]):
        f = fp_nuevo / d.loc[t, "fp_irena"]
        e.loc[t, "fp_irena"] = min(fp_nuevo, 0.95)
        e.loc[t, "fp_gppd"] = min(d.loc[t, "fp_gppd"] * f, 0.95)
    if v.get("residuos", 0):        # el terreno se acerca, en escala logarítmica, al de los residuos (mínimo de Lovering et al.)
        r, base = v["residuos"] / 100, d.loc[t, "suelo_min"]
        e.loc[t, "suelo_med"] = np.exp(np.log(d.loc[t, "suelo_med"]) * (1 - r) + np.log(1.5 * base) * r)
        e.loc[t, "suelo_max"] = np.exp(np.log(d.loc[t, "suelo_max"]) * (1 - r) + np.log(3 * base) * r)
    factor = v.get("eficiencia", EFICIENCIA_PANEL_HOY) / EFICIENCIA_PANEL_HOY * (1 + v.get("conversion", 0) / 100)
    if not np.isclose(factor, 1):
        for c in ("suelo_min", "suelo_med", "suelo_max"):
            e.loc[t, c] = e.loc[t, c] / factor
        afectadas = ("co2_min", "co2_med", "co2_max") if "conversion" in v else ("min_kg_mw",)
        for c in afectadas:
            e.loc[t, c] = e.loc[t, c] / factor
    if v.get("beccs"):
        e.loc[t, ["co2_min", "co2_med", "co2_max"]] = EMISIONES_BECCS
    if "vida" in v:
        e.loc[t, "vida"] = v["vida"]
    if "reciclaje" in v and not np.isclose(v["reciclaje"], d.loc[t, "recic_med"]):
        delta = v["reciclaje"] - d.loc[t, "recic_med"]
        for c in ("recic_min", "recic_med", "recic_max"):
            e.loc[t, c] = min(d.loc[t, c] + delta, 100.0)
    if v.get("crece_como_solar"):
        for c in ("crec_15_24", "crec_20_24"):
            e.loc[t, c] = d.loc["Solar", c]
    return e


def aplicar_saltos(d, saltos):
    """Aplica varios saltos a la vez: {tecnología: valores}."""
    for t, v in saltos.items():
        d = aplicar_salto(d, t, v)
    return d


def aplicar_saltos_pais(d, fp_tabla, nivel):
    """Criterios y FP locales con el salto de las cuatro tecnologías. El FP local sube en la misma proporción que el mundial;
    si no, el costo local, que se ajusta por la razón entre ambos, castigaría sin razón a la tecnología que mejora."""
    e = aplicar_saltos(d, {t: valores_nivel(t, nivel) for t in PALANCAS})
    fp = fp_tabla.copy()
    for t in PALANCAS:
        f = e.loc[t, "fp_irena"] / d.loc[t, "fp_irena"]
        if not np.isclose(f, 1):
            m = fp["tecnologia"] == t
            fp.loc[m, "fp_local"] = (fp.loc[m, "fp_local"] * f).clip(upper=0.95)
    return e, fp


def recomendar_futuro(d, fp_tabla, n=4000):
    """Recomendación de los países en los escenarios de futuro (mismo formato que la recomendación de hoy)."""
    filas = []
    for nombre, nivel in ESCENARIOS_FUTURO.items():
        d_f, fp_f = aplicar_saltos_pais(d, fp_tabla, nivel)
        r = recomendar_todos(d_f, fp_f, n=n, escenario=ESCENARIOS_GEO[GEO_MADURA])
        r["escenario"] = nombre
        filas.append(r)
    return pd.concat(filas, ignore_index=True)
