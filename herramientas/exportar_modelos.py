# -*- coding: utf-8 -*-
"""Pasa los modelos elegidos en la Fase 3 a un archivo comprimido que el tablero puede cargar.

En la Fase 3 las clases propias vivían en el cuaderno (__main__). Aquí se enlazan con src/renovables y se verifica
que cada predicción sea idéntica a la guardada en la Fase 3.
"""
import __main__
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from renovables.datos import NIVELES, PREDICTORES, cargar_gppd, preparar_modelado  # noqa: E402
from renovables.preprocesamiento import Interacciones, Winsorizador  # noqa: E402

__main__.Winsorizador, __main__.Interacciones = Winsorizador, Interacciones
F3 = RAIZ.parent / "Fase_3_Actividades_5_y_6_Ciencia_de_Datos"

_, dm = preparar_modelado(cargar_gppd(RAIZ / "data" / "raw" / "gppd_v1_3" / "global_power_plant_database.csv"))
X = dm[PREDICTORES].assign(tecnologia=lambda d: d["tecnologia"].astype(str))
guardado = pd.read_csv(F3 / "data" / "processed" / "gppd_predicciones_fase3.csv", encoding="utf-8").set_index("gppd_idnr")
guardado = guardado.loc[dm["gppd_idnr"]]

regresor = joblib.load(F3 / "models" / "fase3_regresor_elegido.joblib")
clasificador = joblib.load(F3 / "models" / "fase3_clasificador_elegido.joblib")
for modelo in (regresor, clasificador):
    modelo.named_steps["modelo"].n_jobs = 1             # el servidor del tablero tiene pocos núcleos

dif_reg = np.abs(regresor.predict(X) - guardado["fp_predicho"].values).max()
proba = clasificador.predict_proba(X)
dif_clf = np.abs(proba - guardado[["prob_bajo", "prob_medio", "prob_alto"]].values).max()
iguales = (np.array(NIVELES)[proba.argmax(1)] == guardado["nivel_predicho"].values).all()
assert dif_reg < 1e-9 and dif_clf < 1e-9 and iguales, (dif_reg, dif_clf, iguales)

(RAIZ / "models").mkdir(exist_ok=True)
for nombre, modelo in {"regresor_fp.joblib": regresor, "clasificador_nivel.joblib": clasificador}.items():
    joblib.dump(modelo, RAIZ / "models" / nombre, compress=("xz", 3))
    print(nombre, f"{(RAIZ / 'models' / nombre).stat().st_size / 1e6:.1f} MB")
print(f"Predicciones idénticas a la Fase 3 en {len(X):,} plantas (dif. máx. regresión {dif_reg:.1e}, clasificación {dif_clf:.1e})")
