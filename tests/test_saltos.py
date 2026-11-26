# -*- coding: utf-8 -*-
"""Pruebas del módulo de saltos tecnológicos: «Hoy» no cambia nada y cada salto mejora a su tecnología."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from renovables import multicriterio as mc, saltos as sa  # noqa: E402
from renovables.datos import TECS  # noqa: E402

D = pd.read_csv(RAIZ / "data" / "processed" / "criterios.csv", index_col=0).reindex(TECS)


def primer_lugar(d):
    return mc.resumen_puestos(mc.simular(d, 20000, np.random.default_rng(42)))["% n.º 1"]


def test_hoy_deja_los_criterios_intactos():
    hoy = sa.aplicar_saltos(D, {t: sa.valores_nivel(t, "Hoy") for t in sa.PALANCAS})
    assert np.allclose(hoy.values.astype(float), D.values.astype(float), equal_nan=True)


def test_hoy_reproduce_la_evaluacion_integral():
    r = primer_lugar(sa.aplicar_saltos(D, {t: sa.valores_nivel(t, "Hoy") for t in sa.PALANCAS}))
    assert round(r["Solar"], 1) == 45.7 and round(r["Eólica"], 1) == 35.9      # los valores de la Fase 3


@pytest.mark.parametrize("tecnologia", list(sa.PALANCAS))
def test_cada_salto_mejora_a_su_tecnologia(tecnologia):
    hoy = primer_lugar(D)[tecnologia]
    esperado = primer_lugar(sa.aplicar_salto(D, tecnologia, sa.valores_nivel(tecnologia, "Avance esperado")))[tecnologia]
    grande = primer_lugar(sa.aplicar_salto(D, tecnologia, sa.valores_nivel(tecnologia, "Gran salto")))[tecnologia]
    assert hoy < esperado < grande


def test_un_salto_no_toca_a_las_demas():
    e = sa.aplicar_salto(D, "Solar", sa.valores_nivel("Solar", "Gran salto"))
    otras = [t for t in TECS if t != "Solar"]
    assert np.allclose(e.loc[otras].values.astype(float), D.loc[otras].values.astype(float), equal_nan=True)


def test_niveles_dentro_de_los_rangos_de_los_controles():
    for t, palancas in sa.PALANCAS.items():
        for p in palancas:
            if p.get("tipo") != "toggle":
                assert all(p["min"] <= v <= p["max"] for v in p["niveles"]), (t, p["clave"])


def test_saltos_pais_suben_el_fp_local_en_proporcion():
    fp = pd.read_csv(RAIZ / "data" / "processed" / "fp_local.csv")
    d_f, fp_f = sa.aplicar_saltos_pais(D, fp, "Gran salto")
    for tec in ("Eólica", "Hidroeléctrica"):
        f = d_f.loc[tec, "fp_irena"] / D.loc[tec, "fp_irena"]
        antes = fp.loc[fp["tecnologia"] == tec, "fp_local"].dropna()
        despues = fp_f.loc[antes.index, "fp_local"]
        assert np.allclose(despues, (antes * f).clip(upper=0.95))
    solar = fp["tecnologia"] == "Solar"                              # la eficiencia del panel no cambia el FP
    assert fp_f.loc[solar, "fp_local"].equals(fp.loc[solar, "fp_local"])
