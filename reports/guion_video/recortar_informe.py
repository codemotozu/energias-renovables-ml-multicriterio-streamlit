# -*- coding: utf-8 -*-
"""Recorta del PDF del informe las figuras y tablas que se muestran en el video (con su pie), la portada y las conclusiones.

Uso: python reports/guion_video/recortar_informe.py   (requiere PyMuPDF)
"""
import re
from pathlib import Path

import pymupdf

RAIZ = Path(__file__).resolve().parents[2]
PDF = RAIZ / "reports" / "Ciencia_de_Datos_Fase4_Actividades_7_8_y_9_Rodriguez_Chacon_Carolina.pdf"
SALIDA = Path(__file__).parent / "img"
ZOOM = 3.0
PAD = 4


def guardar(pagina, rect, nombre):
    rect = pymupdf.Rect(rect.x0 - PAD, rect.y0 - PAD, rect.x1 + PAD, rect.y1 + PAD) & pagina.rect
    pagina.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), clip=rect).save(SALIDA / f"{nombre}.png")
    return pagina.number + 1


def lineas(pagina):
    out = []
    for b in pagina.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            texto = "".join(s["text"] for s in l["spans"]).strip()
            if texto:
                out.append((pymupdf.Rect(l["bbox"]), texto))
    return sorted(out, key=lambda x: (x[0].y0, x[0].x0))


def columna(pagina, x):
    mitad = pagina.rect.width / 2
    return (0, mitad) if x < mitad else (mitad, pagina.rect.width)


def figura(doc, n, nombre):
    for pagina in doc:
        for r, t in lineas(pagina):
            if re.match(rf"^Fig\.\s*{n}\.", t):
                c0, c1 = columna(pagina, r.x0)
                # el pie puede tener varias líneas
                pie = pymupdf.Rect(r)
                for r2, t2 in lineas(pagina):
                    if c0 - 2 <= r2.x0 and r2.x1 <= c1 + 2 and r.y0 <= r2.y0 <= pie.y1 + 3:
                        pie |= r2
                imgs = [pymupdf.Rect(i["bbox"]) for i in pagina.get_image_info() if pymupdf.Rect(i["bbox"]).y1 <= r.y0 + 2
                        and pymupdf.Rect(i["bbox"]).x0 >= c0 - 5 and pymupdf.Rect(i["bbox"]).x1 <= c1 + 5]
                img = max(imgs, key=lambda i: i.y1)
                return guardar(pagina, img | pie, nombre)
    raise ValueError(f"No encontré la Fig. {n}")


def tabla(doc, romano, nombre):
    for pagina in doc:
        ls = lineas(pagina)
        for k, (r, t) in enumerate(ls):
            if re.fullmatch(rf"(?i)tabla\s+{romano}", t):
                c0, c1 = columna(pagina, r.x0)
                propias = [(r2, t2) for r2, t2 in ls if c0 - 2 <= r2.x0 and r2.x1 <= c1 + 2 and r2.y0 >= r.y0 - 1]
                # líneas horizontales (booktabs) de esta columna, debajo del título
                reglas = sorted([d["rect"] for d in pagina.get_drawings() if d["rect"].height < 2 and d["rect"].width > 60
                                 and d["rect"].x0 >= c0 - 5 and d["rect"].x1 <= c1 + 5 and d["rect"].y0 > r.y1], key=lambda x: x.y0)
                # la tabla termina en su última regla antes del título de la tabla siguiente en la misma columna
                limite = min([r2.y0 for r2, t2 in propias if r2.y0 > r.y1 and re.fullmatch(r"(?i)tabla\s+[ivx]+", t2)] + [pagina.rect.y1])
                ultima = max((rr for rr in reglas if rr.y0 < limite), key=lambda x: x.y0)
                caja, fin = pymupdf.Rect(r), ultima.y1
                for rr in reglas:
                    if rr.y0 <= ultima.y0:
                        caja |= rr
                for r2, _ in propias[1:]:
                    if r2.y0 <= ultima.y1:          # texto dentro de la tabla
                        caja |= r2
                    elif r2.y0 - fin <= 6:          # nota al pie de la tabla, pegada a la última regla
                        caja |= r2
                        fin = r2.y1
                    else:
                        break
                return guardar(pagina, caja, nombre)
    raise ValueError(f"No encontré la Tabla {romano}")


def portada(doc, nombre):
    pagina = doc[0]
    ls = lineas(pagina)
    fin = next(r for r, t in ls if t.startswith("Noviembre de 2026"))
    titulo = next(r for r, t in ls if t.startswith("Desempeño integral"))
    caja = pymupdf.Rect(pagina.rect.x0 + 40, titulo.y0, pagina.rect.x1 - 40, fin.y1)
    return guardar(pagina, caja, nombre)


def conclusiones(doc, nombre):
    for pagina in doc:
        ls = lineas(pagina)
        inicio = [r for r, t in ls if "CONCLUSIONES" in t.upper() and "TRABAJO" in t.upper()]
        if inicio:
            r0 = inicio[0]
            c0, c1 = columna(pagina, r0.x0)
            fin = next(r for r, t in ls if t.startswith("Como trabajo futuro"))
            caja = pymupdf.Rect(r0)
            for r2, _ in ls:
                if c0 - 2 <= r2.x0 and r2.x1 <= c1 + 2 and r0.y0 <= r2.y0 < fin.y0:
                    caja |= r2
            return guardar(pagina, caja, nombre)
    raise ValueError("No encontré las conclusiones")


if __name__ == "__main__":
    SALIDA.mkdir(exist_ok=True)
    doc = pymupdf.open(PDF)
    paginas = {"portada": portada(doc, "portada"), "conclusiones": conclusiones(doc, "conclusiones")}
    for romano, nombre in (("I", "tabla1"), ("II", "tabla2"), ("III", "tabla3"), ("IV", "tabla4")):
        paginas[nombre] = tabla(doc, romano, nombre)
    for n in (1, 3, 4, 5, 6, 7, 8, 9, 11):
        paginas[f"fig{n}"] = figura(doc, n, f"fig{n}")
    for k, v in paginas.items():
        print(f"{k}: página {v}")
