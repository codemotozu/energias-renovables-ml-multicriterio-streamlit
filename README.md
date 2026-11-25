# Desempeño integral de las energías renovables

Proyecto integrador de Ciencia de Datos · Maestría en Inteligencia Artificial · Universidad de La Salle
Autora: Carolina Rodríguez Chacón · Docente: Fabián Camilo Castro Riveros · Curso 2026-2_Ciencia de Datos_G2

**Pregunta de investigación:** ¿qué tecnología renovable presenta el mejor desempeño integral a escala de planta y qué factores técnicos y geográficos explican las diferencias entre plantas?

**Respuesta:** la solar y la eólica, de forma compartida. Al combinar 14 criterios en 20 000 escenarios, la solar queda primera en el 45.7 % y la eólica en el 35.9 %. Entre plantas, lo que más explica el rendimiento es la tecnología, seguida de la edad y la ubicación.

| Resultado | Valor |
|---|---|
| Regresión del factor de planta (Random Forest, prueba) | R² = 0.623 (IC 95 %: 0.573–0.669); base 0.449 |
| Clasificación del nivel de desempeño (Random Forest, prueba) | F1-macro = 0.760 (IC 95 %: 0.734–0.786); base 0.671 |
| Segmentación (K-Means, k = 2) | Silueta = 0.297 (meta de 0.35 no alcanzada) |
| Recomendación por país | Solar en 141 y eólica en 25 de 166 países; ventaja clara en 73 |
| Geotérmica hipotética | Quedaría primera solo con menos de 39 USD/MWh, en todos los países y creciendo como la eólica; unos 780 GW en 2050 si despega en 2030 |

## Ejecutar el tablero

**En Windows:** doble clic en `ejecutar_tablero.bat`. La primera vez instala lo necesario.

**En cualquier sistema** (Python 3.13):

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

**Publicarlo en Streamlit Community Cloud:** en [share.streamlit.io](https://share.streamlit.io), *Create app* → elegir este repositorio, rama `main`, archivo principal `dashboard/app.py` → en *Advanced settings* elegir Python 3.13 → *Deploy*.

## Vistas del tablero

| Vista | Qué responde | Módulo de la guía |
|---|---|---|
| 1. La pregunta y la respuesta | Pregunta, respuesta e indicadores | Tarjetas KPI |
| 2. Panorama | Qué plantas hay y cuánto rinden | Filtros dinámicos y KPI |
| 3. Modelos | Cuál predice mejor, qué variables pesan y dónde falla | Comparación e interpretabilidad |
| 4. Predicción en vivo | Cuánto rendiría una planta nueva | Predicción en vivo |
| 5. Segmentación | Qué grupos naturales existen | Clustering 2D/3D en PCA y perfiles |
| 6. Evaluación integral | Qué gana con distintas prioridades | Multicriterio |
| 7. País | Qué renovable conviene a cada país | Recomendación |
| 8. Geotérmica | Qué pasaría con las ondas milimétricas, cómo se comportaría y cuál sería su potencial | Escenario |
| 9. Método y limitaciones | De dónde salen los resultados | Respaldo |

## Estructura del repositorio

```text
├── dashboard/       Aplicación Streamlit (app.py, vistas y requirements.txt del despliegue)
├── data/
│   ├── raw/         GPPD v1.3.0, IRENASTAT, NASA POWER y nombres de países
│   └── processed/   Tablas que usa el tablero
├── models/          Random Forest de regresión y clasificación (Fase 3)
├── notebooks/       Cuadernos de las fases 1, 2, 3 y 4
├── src/renovables/  Datos, preprocesamiento, multicriterio, recomendación por país
├── herramientas/    Descarga de datos, construcción del cuaderno y compilación del informe
├── reports/         Informe final en PDF, guion de la sustentación y figuras
└── requirements.txt Versiones exactas de todo el proyecto
```

## Reproducir los resultados

```bash
pip install -r requirements.txt
python herramientas/descargar_datos_externos.py   # solo si faltan los datos de IRENA y NASA
python herramientas/descargar_datos_horarios.py   # solo si faltan los datos horarios de NASA
python herramientas/construir_artefactos.py       # regenera data/processed/ (unos 15 minutos)
python herramientas/construir_cuaderno_fase4.py --ejecutar
python herramientas/compilar_informe.py           # requiere pdflatex
```

Todo usa `SEMILLA = 42`. El código verifica con aserciones la huella SHA-256 de los datos, la partición de la Fase 2 (4 202 / 902 / 907), las métricas de los modelos y los porcentajes del multicriterio de la Fase 3.

## Datos y licencias

- **Global Power Plant Database v1.3.0**, World Resources Institute, CC BY 4.0: <https://datasets.wri.org/datasets/global-power-plant-database>. SHA-256 del CSV: `4b1f93e0fd93664f18684d9b05d0a52ed9658c6a8cf0d21ff2520791379ba7fc`
- **IRENASTAT** (edición 2026-H2), International Renewable Energy Agency: <https://pxweb.irena.org/pxweb/en/IRENASTAT>
- **Agencia Internacional de la Energía (2024)**, *The Future of Geothermal Energy*: <https://www.iea.org/reports/the-future-of-geothermal-energy>
- **IRENA (2026)**, *Renewable Power Generation Costs in 2025*: <https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2026/Jul/IRENA_TEC_RPGC_in_2025_2026.pdf>
- **Ember (2026)**, *Global Electricity Review*: <https://ember-energy.org/latest-insights/global-electricity-review-2026/>
- **NASA POWER**: estos datos se obtuvieron del proyecto POWER del NASA Langley Research Center, financiado por el programa NASA Earth Science/Applied Science: <https://power.larc.nasa.gov/>
- **Banco Mundial**: nombres de países y regiones: <https://api.worldbank.org/v2/es/country>

## Limitaciones

El 88 % de las plantas con generación está en EE. UU.; faltan hidrología, tipo de central y despacho; la GPPD llega hasta 2019. La recomendación por país es orientativa: no incluye red, demanda, financiamiento ni política. El escenario geotérmico es hipotético: la simulación horaria cubre seis países con un consumo constante, y el potencial es una analogía con la expansión de la eólica y la solar. El detalle está en el informe final y en la vista 9 del tablero.
