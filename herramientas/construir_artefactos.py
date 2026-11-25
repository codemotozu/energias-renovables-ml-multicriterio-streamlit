# -*- coding: utf-8 -*-
"""Regenera todas las tablas de data/processed/ que usan el tablero y el informe final."""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from renovables.artefactos import construir  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(construir(RAIZ), ensure_ascii=False, indent=1))
