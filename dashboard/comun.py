# -*- coding: utf-8 -*-
"""Datos, modelos, colores y utilidades compartidas por todas las vistas del tablero."""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.neighbors import BallTree

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src"))

from renovables import multicriterio as mc  # noqa: E402
from renovables import paises as pa  # noqa: E402
from renovables import saltos as sa  # noqa: E402
from renovables.datos import ANIO_REFERENCIA, NIVELES, PREDICTORES, R_TIERRA_KM, TECS  # noqa: E402

PROC = RAIZ / "data" / "processed"
PREGUNTA = ("¿Qué tecnología renovable presenta el mejor desempeño integral a escala de planta "
            "y qué factores técnicos y geográficos explican las diferencias entre plantas?")
ENLACE_REPOSITORIO = "https://github.com/codemotozu/energias-renovables-ml-multicriterio-streamlit"

_COLOR_CLARO = {"Solar": "#eda100", "Eólica": "#1baf7a", "Hidroeléctrica": "#2a78d6", "Geotérmica": "#e34948", "Biomasa": "#008300"}
_COLOR_OSCURO = {"Solar": "#c98500", "Eólica": "#199e70", "Hidroeléctrica": "#3987e5", "Geotérmica": "#e66767", "Biomasa": "#0ca30c"}
_PUESTOS_CLARO = ["#0d366b", "#1c5cab", "#3987e5", "#86b6ef", "#d6e6fb"]
_PUESTOS_OSCURO = ["#d6e6fb", "#86b6ef", "#3987e5", "#1c5cab", "#104281"]


def modo_oscuro():
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False


def colores_tec():
    return _COLOR_OSCURO if modo_oscuro() else _COLOR_CLARO


def colores_puesto():
    return _PUESTOS_OSCURO if modo_oscuro() else _PUESTOS_CLARO


def tinta():
    return {"primaria": "#f0efec", "secundaria": "#c3c2b7", "tenue": "#898781", "reticula": "#2c2c2a", "eje": "#383835", "superficie": "#1a1a19"} \
        if modo_oscuro() else {"primaria": "#0b0b0b", "secundaria": "#52514e", "tenue": "#898781", "reticula": "#e1e0d9", "eje": "#c3c2b7", "superficie": "#fcfcfb"}


def estilo_figura(fig, alto=380, leyenda=True, titulo_x=None, titulo_y=None, margen=None):
    t = tinta()
    fig.update_layout(
        height=alto, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', size=13, color=t["secundaria"]),
        margin=margen or dict(l=8, r=12, t=12, b=8), showlegend=leyenda, barcornerradius=4,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, title_text="", font=dict(size=12), traceorder="normal"),
        hoverlabel=dict(bgcolor=t["superficie"], font=dict(color=t["primaria"], size=13), bordercolor=t["eje"]),
    )
    fig.update_xaxes(gridcolor=t["reticula"], linecolor=t["eje"], zerolinecolor=t["eje"], tickfont=dict(color=t["tenue"]), title_text=titulo_x)
    fig.update_yaxes(gridcolor=t["reticula"], linecolor=t["eje"], zerolinecolor=t["eje"], tickfont=dict(color=t["tenue"]), title_text=titulo_y)
    return fig


def mostrar(fig, **kw):
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}, **kw)


def estilo_mapa(fig, alto=430):
    t = tinta()
    fig.update_geos(projection_type="natural earth", showframe=False, showcoastlines=True, coastlinecolor=t["eje"], coastlinewidth=0.5,
                    showland=True, landcolor=t["reticula"], showocean=False, showcountries=True, countrycolor=t["eje"], countrywidth=0.3,
                    bgcolor="rgba(0,0,0,0)", lataxis_range=[-58, 84])
    fig.update_layout(height=alto, margin=dict(l=0, r=0, t=4, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', size=13, color=t["secundaria"]),
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title_text="", itemsizing="constant", traceorder="normal"),
                      hoverlabel=dict(bgcolor=t["superficie"], font=dict(color=t["primaria"], size=13), bordercolor=t["eje"]))
    return fig


def encabezado(titulo, pregunta=None):
    """Título de la vista y la pregunta que responde: el hilo de la narrativa."""
    st.title(titulo)
    if pregunta:
        st.markdown(f'<p class="pregunta-vista">{pregunta}</p>', unsafe_allow_html=True)


def hallazgo(texto):
    st.markdown(f'<div class="hallazgo">{texto}</div>', unsafe_allow_html=True)


def fmt(x, d=0):
    """Número con espacio de miles y punto decimal, igual que en el informe."""
    return f"{x:,.{d}f}".replace(",", " ")


@st.cache_data(show_spinner=False)
def plantas():
    d = pd.read_csv(PROC / "plantas.csv", encoding="utf-8")
    d["atipica_dbscan"] = d["atipica_dbscan"].astype("boolean")
    return d


@st.cache_data(show_spinner=False)
def leer(nombre, **kw):
    return pd.read_csv(PROC / nombre, encoding="utf-8", **kw)


@st.cache_data(show_spinner=False)
def criterios():
    return pd.read_csv(PROC / "criterios.csv", index_col=0, encoding="utf-8").reindex(TECS)


@st.cache_data(show_spinner=False)
def metricas():
    return json.loads((PROC / "metricas_fase3.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def resumen():
    return json.loads((PROC / "resumen_fase4.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def fp_local():
    return pd.read_csv(PROC / "fp_local.csv", encoding="utf-8")


@st.cache_data(show_spinner=False)
def recomendaciones():
    """Recomendación de hoy y de los escenarios geotérmicos, más los escenarios de futuro si ya se calcularon."""
    rec = pd.read_csv(PROC / "recomendacion_pais.csv", encoding="utf-8")
    futuro = PROC / "recomendacion_pais_futuro.csv"
    return pd.concat([rec, pd.read_csv(futuro, encoding="utf-8")], ignore_index=True) if futuro.exists() else rec


@st.cache_data(show_spinner=False)
def centros_pais():
    """Punto de mayor capacidad de cada país: ubicación inicial del simulador."""
    p = pd.read_csv(RAIZ / "data" / "raw" / "nasa_power" / "puntos_por_pais.csv")
    p = p.sort_values("peso", ascending=False).drop_duplicates("country").set_index("country")
    return p[["lat", "lon"]]


@st.cache_resource(show_spinner="Cargando los modelos de la Fase 3…")
def modelos():
    return joblib.load(RAIZ / "models" / "regresor_fp.joblib"), joblib.load(RAIZ / "models" / "clasificador_nivel.joblib")


@st.cache_resource(show_spinner=False)
def arboles_densidad():
    u = pd.read_csv(PROC / "universo_coordenadas.csv", encoding="utf-8")
    return {t: BallTree(np.radians(g[["latitude", "longitude"]].values), metric="haversine") for t, g in u.groupby("tecnologia")}


def fila_planta(tecnologia, pais, capacidad, anio, lat, lon):
    """Calcula las ocho variables del modelo igual que en la Fase 2, para una planta que todavía no existe."""
    n = arboles_densidad()[tecnologia].query_radius(np.radians([[lat, lon]]), r=100 / R_TIERRA_KM, count_only=True)[0]
    return {"tecnologia": tecnologia, "country": pais, "log_capacidad": np.log10(capacidad),
            "irradiacion_relativa": np.cos(np.radians(lat)), "densidad_misma_tec": float(np.log1p(n)),
            "edad_planta": ANIO_REFERENCIA - anio, "latitude": lat, "longitude": lon}


def predecir(filas):
    regresor, clasificador = modelos()
    X = pd.DataFrame(filas)[PREDICTORES]
    return regresor.predict(X), clasificador.predict_proba(X)


def banda_arboles(fila, inferior=10, superior=90):
    """Rango de lo que predicen los árboles del bosque: cuánto coinciden entre sí para esta planta."""
    regresor, _ = modelos()
    Xt = regresor.named_steps["prep"].transform(pd.DataFrame([fila])[PREDICTORES]).values
    pred = np.array([a.predict(Xt)[0] for a in regresor.named_steps["modelo"].estimators_])
    return float(np.percentile(pred, inferior)), float(np.percentile(pred, superior))


@st.cache_data(show_spinner=False)
def simular_global(prioridad, metodo, baterias, escenario=None, n=20000):
    """Monte Carlo con pesos al azar (prioridad=None) o con las prioridades elegidas por el usuario."""
    d = criterios()
    if escenario:
        d = mc.aplicar_escenario_geo(d, **dict(escenario))
    pesos = mc.pesos_desde_pilares(dict(prioridad)) if prioridad else None
    P = mc.simular(d, n, np.random.default_rng(42), metodo=metodo, almacenamiento=baterias, pesos=pesos)
    distribucion = pd.DataFrame({k: (P == k).mean(0) * 100 for k in range(1, 6)}, index=TECS)
    return mc.resumen_puestos(P), distribucion


@st.cache_data(show_spinner=False)
def recomendar(iso3, prioridad, metodo, baterias, escenario=None, n=4000):
    pesos = mc.pesos_desde_pilares(dict(prioridad)) if prioridad else None
    return pa.recomendar_pais(criterios(), fp_local(), iso3, n=n, metodo=metodo, pesos=pesos,
                              escenario=dict(escenario) if escenario else None, almacenamiento=baterias)


@st.cache_data(show_spinner=False)
def simular_saltos(saltos, metodo="SAW", geo_madura=False, prioridad=None, n=20000):
    """Monte Carlo global con saltos tecnológicos. saltos = ((tecnología, ((palanca, valor), ...)), ...);
    prioridad = ((pilar, peso), ...) fija los pesos; None los sortea al azar."""
    d = criterios()
    if geo_madura:
        d = mc.aplicar_escenario_geo(d, **mc.ESCENARIOS_GEO["Madura (meta de la industria)"])
    d = sa.aplicar_saltos(d, {t: dict(v) for t, v in saltos})
    pesos = mc.pesos_desde_pilares(dict(prioridad)) if prioridad else None
    P = mc.simular(d, n, np.random.default_rng(42), metodo=metodo, almacenamiento=True, pesos=pesos)
    return mc.resumen_puestos(P), d


def saltos_a_tupla(saltos):
    return tuple(sorted((t, tuple(sorted(v.items()))) for t, v in saltos.items()))


@st.cache_data(show_spinner=False)
def recomendar_futuro(iso3, metodo, baterias, nivel, n=4000):
    """Recomendación de un país si las cuatro tecnologías dan su salto (vista 9) y la geotérmica es la madura (vista 8)."""
    d, fp = sa.aplicar_saltos_pais(criterios(), fp_local(), nivel)
    return pa.recomendar_pais(d, fp, iso3, n=n, metodo=metodo, escenario=mc.ESCENARIOS_GEO[sa.GEO_MADURA], almacenamiento=baterias)


def escenario_a_tupla(e):
    return tuple(sorted(e.items())) if e else None


def barras_puestos(distribucion, alto=300):
    """Barra apilada al 100 %: en cuántos escenarios queda cada tecnología en cada puesto."""
    orden = distribucion.sort_values([1, 2], ascending=True).index.tolist()
    fig = go.Figure()
    t = tinta()
    for k, color in zip(range(1, 6), colores_puesto()):
        v = distribucion.loc[orden, k]
        claro = color in ("#d6e6fb", "#86b6ef")
        fig.add_bar(y=orden, x=v, name=f"{k}.º", orientation="h", marker=dict(color=color, line=dict(color=t["superficie"], width=2)),
                    text=[f"{x:.0f}" if x >= 9 else "" for x in v], textposition="inside", insidetextanchor="middle",
                    textfont=dict(color="#0b0b0b" if claro else "#ffffff", size=12),
                    hovertemplate="%{y}: puesto " + str(k) + " en %{x:.1f} % de los escenarios<extra></extra>")
    fig.update_layout(barmode="stack", bargap=0.28, barcornerradius=0)
    estilo_figura(fig, alto=alto, titulo_x="% de escenarios")
    fig.update_layout(barcornerradius=0)
    fig.update_xaxes(range=[0, 100], ticksuffix=" %")
    fig.update_yaxes(showgrid=False)
    return fig


def inyectar_estilos():
    t = tinta()
    st.markdown(f"""
<style>
  .block-container {{ padding-top: 3.6rem; max-width: 1280px; }}
  h1 {{ font-size: 1.85rem !important; line-height: 1.2 !important; font-weight: 650 !important; padding-bottom: .15rem !important; }}
  h2 {{ font-size: 1.25rem !important; font-weight: 620 !important; }}
  h3 {{ font-size: 1.05rem !important; font-weight: 620 !important; }}
  .pregunta-vista {{ color: {t['secundaria']}; font-size: 1.04rem; margin: -.2rem 0 1rem 0; }}
  .hallazgo {{ border-left: 3px solid #2a78d6; background: rgba(42,120,214,.09); padding: .7rem .95rem; border-radius: 0 6px 6px 0;
               margin: .35rem 0 1rem 0; font-size: .97rem; line-height: 1.5; color: {t['primaria']}; }}
  .pregunta-principal {{ font-size: 1.72rem; line-height: 1.18; font-weight: 680; margin: .2rem 0 .55rem 0; color: {t['primaria']}; letter-spacing: -.01em; }}
  .etiqueta {{ font-size: .78rem; letter-spacing: .05em; text-transform: uppercase; color: {t['tenue']}; font-weight: 600; }}
  .respuesta {{ font-size: 1.13rem; line-height: 1.42; color: {t['secundaria']}; max-width: 62rem; }}
  .tarjeta-p {{ font-size: .92rem; color: {t['secundaria']}; line-height: 1.45; }}
  .tarjeta-r {{ font-size: 1.14rem; font-weight: 640; color: {t['primaria']}; margin: .2rem 0 .3rem 0; line-height: 1.25; }}
  [data-testid="stMetricValue"] {{ font-size: 1.55rem; font-variant-numeric: tabular-nums; }}
  [data-testid="stMetricLabel"] p {{ font-size: .84rem; }}
  [data-testid="stSidebarNav"] {{ padding-top: .4rem; }}
</style>
""", unsafe_allow_html=True)
