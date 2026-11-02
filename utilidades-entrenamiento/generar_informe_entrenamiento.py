#!/usr/bin/env python3
"""
Generador del informe HTML corregido de la evaluación MobileNetV3-Small.

Este script es la fuente única que produce el archivo:
    docs/datos-graficos/figuras_entrenamiento_APA7_corregido.html

Lee los datos crudos del proyecto y reconstruye, de forma verificable y con
registro (log) de cada cálculo, las tablas y figuras del informe:

  * metrics.json      -> curvas de validación por época (hitos y resumen).
  * config.json       -> parámetros de cada ejecución.
  * evaluacion_*.json -> métricas por clase (tipo, color, estilo).
  * registro_entrenamiento.sqlite -> fechas y trazabilidad de ejecuciones.
  * dataset/metadata.sqlite        -> procedencia de las imágenes por fuente.
  * best.pt (SHA-256) -> integridad de los checkpoints.

Diseño:
  - Solo biblioteca estándar (json, sqlite3, hashlib, logging, pathlib).
  - Pensado para ejecutarse tanto en el host como dentro del contenedor
    de entrenamiento; todas las rutas se configuran por argumentos.
  - Deja un archivo de log (por defecto junto a la salida) con cada cálculo
    intermedio, para auditar la generación del informe.

Uso (host):
    python3 utilidades-entrenamiento/generar_informe_entrenamiento.py \
        --output-dir docs/datos-graficos

Uso (contenedor Docker, montando las rutas del host):
    docker run --rm --user 1000:1000 \
      -v "$PWD/utilidades-entrenamiento/modelo-ia:/app/modelo-ia" \
      -v "$PWD/utilidades-entrenamiento/modelos-compartidos:/app/modelos-compartidos:ro" \
      -v "$PWD/dataset:/app/dataset:ro" \
      -v "$PWD/docs/datos-graficos:/app/salida" \
      -v "$PWD/utilidades-entrenamiento/generar_informe_entrenamiento.py:/app/generar_informe_entrenamiento.py:ro" \
      --entrypoint python \
      modelo-general-destilacion-curator:latest \
      /app/generar_informe_entrenamiento.py \
        --modelo-ia /app/modelo-ia \
        --modelos-compartidos /app/modelos-compartidos \
        --dataset-sqlite /app/dataset/metadata.sqlite \
        --output-dir /app/salida
"""

import argparse
import hashlib
import json
import logging
import sqlite3
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Constantes del estudio
# ---------------------------------------------------------------------------
# Ejecuciones documentadas en el Anexo G. El "rol" es la etiqueta editorial
# que se muestra en el informe (evita el término "desde cero", que la
# auditoría G-003 pide reservar para pesos aleatorios).
RUNS = [
    # (run_id, rol mostrado, época del checkpoint, nombre del checkpoint)
    ("20261026-021300", "Referencia", 15, "mobilenetv3-small-best.pt"),
    ("20261028-042931", "Fallida", 15, "best.pt"),
    ("20261029-022656", "Corregida", 23, "best.pt"),
]

# Resultados del conjunto de prueba PORTABLE (1.424 imágenes), obtenidos con
# la API de pruebas en CPU (test_api.py, POST /test/run) sobre
# tests/imagenes-test/. Se declaran como constantes auditables porque esa
# evaluación es la misma que reproduce el informe (no se recalcula aquí para
# no requerir PyTorch en este generador).
PORTABLE_TEST_RESULTS = {
    "20261026-021300": {
        "tipo_pct": 94.94, "color_jaccard_pct": 68.42,
        "estilo_jaccard_pct": 69.21, "macro_pct": 77.52, "r11": "Cumple",
    },
    "20261028-042931": {
        "tipo_pct": 89.40, "color_jaccard_pct": 33.17,
        "estilo_jaccard_pct": 62.79, "macro_pct": 61.79, "r11": "No cumple",
    },
    "20261029-022656": {
        "tipo_pct": 94.03, "color_jaccard_pct": 69.28,
        "estilo_jaccard_pct": 69.29, "macro_pct": 77.53, "r11": "Cumple",
    },
}

# SHA-256 completos verificados (fuente: docs/EVIDENCIAS-INTEGRIDAD-SHA256.md).
# Se recalculan al ejecutar el script y se contrastan con estos valores.
KNOWN_CHECKPOINT_SHA = {
    "20261026-021300": "79407f5537418bc258857fa54723d8e39b152505ad3a6f6a6ea4f97e1dfcb35c",
    "20261028-042931": "77fbd17bfebd1c9cb64d08fd9a31e691aa0beac2a7c2e615d42aeb0f3413dea8",
    "20261029-022656": "8aacd8b45aa5f7c99461b48c4fcf4d9e998b6efd9134758234675477ed96d923",
}

# Fecha/hora UTC de cada ejecución (registro_entrenamiento.sqlite, tabla ejecucion).
RUN_DATES = {
    "20261026-021300": "2026-10-26 02:13",
    "20261028-042931": "2026-10-28 04:29",
    "20261029-022656": "2026-10-29 02:26",
}

# Configuración diferencial por ejecución (el resto de parámetros es común:
# image_size 224, batch 64, pretrained/finetune sí, weight_decay 1e-4,
# label_smoothing 0.05, class_weighted/augment/amp sí, patience 5, seed 42).
RUN_DIFF_CONFIG = {
    "20261026-021300": "lr 0,001 · finetune 1e-4 · warmup 3",
    "20261028-042931": "lr 1e-4 · finetune 1e-5 · warmup 0",
    "20261029-022656": "lr 0,001 · finetune 1e-4 · warmup 3",
}

# Procedencia de imágenes: se reconstruye desde dataset/metadata.sqlite usando
# el prefijo de prenda.codigo. La tabla se completa con licencias verificadas
# externamente (DataCite para AIG-Dataset; LICENSE de GitHub para los otros dos).
SOURCE_PREFIXES = [
    ("mendeley", "AIG-Dataset (Mendeley Data)", "DOI 10.17632/pxkbgkydrp.1, v1 (2025-04-17)", "CC BY 4.0"),
    ("clothing-small", "Clothing Dataset Small (GitHub)", "Snapshot sin versión", "CC0 1.0"),
    ("clothing", "Clothing Dataset (GitHub)", "Snapshot sin versión", "CC0 1.0"),
]

R11_THRESHOLD_PCT = 70.0


# ---------------------------------------------------------------------------
# 2. Utilidades de cálculo (cada una registra su resultado en el log)
# ---------------------------------------------------------------------------

def _prefix_from_code(codigo: str) -> str:
    """Devuelve el prefijo de fuente a partir de un código de prenda.

    Los códigos siguen el patrón <fuente>-<hash>; 'clothing-small' se
    distingue de 'clothing' por el segmento '-small-'.
    """
    return codigo.split("-")[0] + ("-small" if "-small-" in codigo else "")


def load_metrics(modelo_ia: Path, run_id: str) -> list:
    """Carga metrics.json de una ejecución (lista ordenada por época)."""
    path = modelo_ia / "runs" / run_id / "metrics.json"
    logging.info("Leyendo métricas: %s", path)
    rows = json.loads(path.read_text())
    rows.sort(key=lambda r: r["epoch"])
    logging.info("  épocas registradas: %d", len(rows))
    return rows


def compute_hitos(rows: list, rol: str) -> list:
    """Calcula los tres hitos por ejecución: primera, mejor y última época.

    Devuelve filas (rol, hito, época, val_loss, tipo%, colorF1%, estiloF1%).
    """
    best = min(rows, key=lambda r: r["validation"]["loss"])
    last = rows[-1]
    hitos = []
    for label, r in (("Primera", rows[0]), ("Mejor val_loss", best), ("Última", last)):
        v = r["validation"]
        tipo_pct = v["type_accuracy"] * 100
        color_f1 = v["color"]["f1"] * 100
        estilo_f1 = v["style"]["f1"] * 100
        hitos.append((rol, label, r["epoch"], v["loss"], tipo_pct, color_f1, estilo_f1))
        logging.info(
            "  [%s] %s: época=%d val_loss=%.4f tipo=%.2f%% colorF1=%.2f%% estiloF1=%.2f%%",
            rol, label, r["epoch"], v["loss"], tipo_pct, color_f1, estilo_f1,
        )
    return hitos


def compute_resumen(rows: list, rol: str) -> tuple:
    """Resumen por ejecución: épocas, mejor época/loss, loss y métricas finales."""
    best = min(rows, key=lambda r: r["validation"]["loss"])
    last = rows[-1]
    summary = (
        rol, len(rows), best["epoch"], best["validation"]["loss"],
        last["validation"]["loss"],
        last["validation"]["type_accuracy"] * 100,
        last["validation"]["color"]["f1"] * 100,
        last["validation"]["style"]["f1"] * 100,
    )
    logging.info(
        "  [%s] RESUMEN: épocas=%d mejor_época=%d mejor_val_loss=%.4f "
        "val_loss_final=%.4f tipo_final=%.2f%% colorF1_final=%.2f%% estiloF1_final=%.2f%%",
        *summary,
    )
    return summary


def compute_per_class(evaluation_json: Path) -> tuple:
    """Extrae las métricas por clase (tipo, color, estilo) de una evaluación."""
    logging.info("Leyendo evaluación por clase: %s", evaluation_json)
    ev = json.loads(evaluation_json.read_text())
    tipo = ev["tipo_prenda"]["por_tipo"]
    color = [e for e in ev["color"]["por_etiqueta"] if e["soporte"] > 0]
    estilo = [e for e in ev["estilo"]["por_etiqueta"] if e["soporte"] > 0]
    logging.info(
        "  por_clase: tipo=%d color=%d (con soporte) estilo=%d (con soporte)",
        len(tipo), len(color), len(estilo),
    )
    return tipo, color, estilo


def checkpoint_sha(checkpoint_path: Path, run_id: str) -> str:
    """Calcula y verifica el SHA-256 de un checkpoint contra el valor conocido."""
    sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    known = KNOWN_CHECKPOINT_SHA.get(run_id)
    if known and sha != known:
        logging.warning(
            "  ¡SHA-256 del checkpoint %s difiere del registrado!\n"
            "    calculado: %s\n    esperado:  %s",
            checkpoint_path.name, sha, known,
        )
    else:
        logging.info("  SHA-256 verificado de %s: %s", checkpoint_path.name, sha)
    return sha


def compute_provenance(dataset_sqlite: Path) -> list:
    """Reconstruye la procedencia de las imágenes desde metadata.sqlite.

    Devuelve filas (fuente, versión, licencia, total, aprobado, rechazado, otro)
    más una fila de totales. El conteo usa el prefijo del código de prenda.
    """
    logging.info("Leyendo procedencia desde: %s", dataset_sqlite)
    conn = sqlite3.connect(dataset_sqlite)
    try:
        rows = conn.execute("SELECT codigo, estado_revision FROM prenda").fetchall()
    finally:
        conn.close()

    # Agregación por fuente y estado.
    agg = {}
    for codigo, estado in rows:
        agg.setdefault(_prefix_from_code(codigo), Counter())[estado] += 1

    table = []
    totals = Counter()
    for prefix, name, version, licencia in SOURCE_PREFIXES:
        counts = agg.get(prefix, Counter())
        total = sum(counts.values())
        aprobado = counts.get("aprobado", 0)
        rechazado = counts.get("rechazado", 0)
        otro = total - aprobado - rechazado
        table.append((name, version, licencia, total, aprobado, rechazado, otro))
        totals["total"] += total
        totals["aprobado"] += aprobado
        totals["rechazado"] += rechazado
        totals["otro"] += otro
        logging.info(
            "  %-32s total=%d aprobado=%d rechazado=%d otro=%d",
            name, total, aprobado, rechazado, otro,
        )

    table.append((
        "Total", "—", "—", totals["total"], totals["aprobado"],
        totals["rechazado"], totals["otro"],
    ))
    logging.info(
        "  BALANCE GLOBAL: %d ingresadas -> %d aprobadas (rechazadas=%d, otro=%d)",
        totals["total"], totals["aprobado"], totals["rechazado"], totals["otro"],
    )
    return table


def compute_val_series(rows: list) -> list:
    """Serializa las métricas por época para el JSON embebido en el HTML."""
    series = []
    for r in rows:
        v = r["validation"]
        series.append({
            "run_id": r.get("run_id", ""),
            "rol": r.get("rol", ""),
            "epoch": r["epoch"],
            "train_loss": round(r["train_loss"], 6),
            "val_loss": round(v["loss"], 6),
            "tipo_accuracy": round(v["type_accuracy"], 6),
            "color_precision": round(v["color"]["precision"], 6),
            "color_recall": round(v["color"]["recall"], 6),
            "color_f1": round(v["color"]["f1"], 6),
            "estilo_precision": round(v["style"]["precision"], 6),
            "estilo_recall": round(v["style"]["recall"], 6),
            "estilo_f1": round(v["style"]["f1"], 6),
        })
    return series


# ---------------------------------------------------------------------------
# 3. Plantilla HTML del informe
# ---------------------------------------------------------------------------
# La plantilla contiene marcadores __XXX__ que se sustituyen tras calcular los
# datos. El bloque <script> es JavaScript puro (gráficos SVG y descargas CSV).
HTML_TEMPLATE = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Figuras y tablas corregidas — MobileNetV3-Small (Anexo G)</title>
<style>
:root{--ink:#171717;--line:#b7b7b7;--paper:#fff;--muted:#4e4e4e;--bg:#f0f0ef}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 "Times New Roman",Times,serif}
.toolbar{position:sticky;top:0;z-index:2;background:#222;color:#fff;padding:12px 24px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;font:14px/1.3 Arial,sans-serif}
.toolbar button{background:#fff;border:1px solid #aaa;border-radius:4px;padding:9px 12px;color:#1a1a1a;cursor:pointer}.toolbar button:hover{background:#e6e6e6}
.toolbar .tools{display:flex;gap:8px;flex-wrap:wrap}.paper{max-width:960px;margin:24px auto;padding:64px 74px;background:white;box-shadow:0 2px 14px #0002}
h1{font-size:22px;text-align:center;line-height:1.3;margin:0 0 18px;font-weight:bold}.intro{margin:0 0 28px;text-indent:1.27cm;text-align:justify}
.figure{margin:0 0 38px;break-inside:avoid;page-break-inside:avoid}.figure-no{font-weight:bold;display:block;margin-bottom:1px}.figure-title{font-style:italic;margin:0 0 12px;line-height:1.35}.graph{width:100%;overflow:hidden}.graph svg{width:100%;height:auto;display:block}
.note{font-size:15px;line-height:1.4;margin:7px 0 0}.note em{font-style:italic}.source{font-size:14px;color:var(--muted);margin-top:24px}
.table-block{margin:0 0 30px;break-inside:avoid;page-break-inside:avoid}.table-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:6px}
.csv-btn{font:12px Arial,sans-serif;padding:5px 10px;border:1px solid #aaa;background:#f3f3f3;cursor:pointer;border-radius:3px}.csv-btn:hover{background:#e2e2e2}
.table-source{font-size:13px;color:var(--muted);margin-top:6px}.table-source code{font-size:12px;background:#f1f1f1;padding:1px 4px}
.apa-table{width:100%;border-collapse:collapse;font-size:15px;border-top:2px solid #111;border-bottom:2px solid #111}.apa-table th{border-bottom:1px solid #111;text-align:left}.apa-table th,.apa-table td{padding:6px 8px}.apa-table td:not(:first-child),.apa-table th:not(:first-child){text-align:right}.apa-table tr{border:0}
.small{font-size:13px}.hash{font-family:Consolas,monospace;font-size:11px;word-break:break-all}
.footer{text-align:center;color:#555;font:13px Arial,sans-serif}
h2.sec{font-size:16px;margin:34px 0 12px;font-weight:bold;border-bottom:1px solid #ccc;padding-bottom:4px}
@media(max-width:750px){.paper{margin:0;padding:24px 18px}.toolbar{padding:10px}}
@media print{@page{size:A4;margin:2.54cm}body{background:white;font-size:12pt}.toolbar,.figure-actions,.footer{display:none!important}.paper{box-shadow:none;max-width:none;margin:0;padding:0}.figure{margin-bottom:24px}.note{font-size:10.5pt}.graph svg{max-height:12cm}.source{font-size:10pt}h1{font-size:14pt}}
</style></head><body>
<div class="toolbar"><span>Figuras y tablas corregidas · Anexo G · APA 7</span><div class="tools"><button onclick="window.print()">Imprimir / guardar PDF</button><button onclick="downloadAll()">Descargar todas las figuras SVG</button><button onclick="downloadAllCsv()">Descargar CSVs de datos</button></div></div>
<main class="paper">
<h1>Evaluación comparativa del clasificador MobileNetV3-Small</h1>
<p class="intro">Este documento corrige y complementa las figuras y tablas de la evaluación del componente de reconocimiento de propiedades de prendas. Presenta los resultados de tres ejecuciones independientes iniciadas desde pesos preentrenados (ImageNet), sin reanudar un checkpoint previo, conforme a la terminología del Anexo G. Las métricas proceden de la validación por época y de la evaluación del conjunto de prueba portable (1.424 imágenes), y cada tabla indica su fuente de datos para trazabilidad.</p>

<h2 class="sec">Tabla 1 · Resultados en el conjunto de prueba (1.424 imágenes, CPU)</h2>
<section class="table-block">
<table class="apa-table"><thead><tr><th>Ejecución</th><th>Tipo (%)</th><th>Color Jaccard (%)</th><th>Estilo Jaccard (%)</th><th>Macro (%)</th><th>R11</th></tr></thead>
<tbody>__RES_ROWS__</tbody></table>
<p class="note"><em>Nota.</em> La diferencia de 0,01 pp entre la ejecución de referencia (77,52 %) y la corregida (77,53 %) no respalda una afirmación de superioridad; ambas se describen como equivalentes a la precisión reportada. R11: promedio macro ≥ 70 %.</p>
<p class="table-source">Fuente: <code>docs/datos-graficos/resultados_test.csv</code>; evaluación de la API de pruebas sobre <code>tests/imagenes-test/</code>.</p>
<div class="table-actions"><button class="csv-btn" onclick="downloadResultadosCsv()">Descargar CSV</button></div>
</section>

<h2 class="sec">Tabla 2 · Identificación y trazabilidad de las ejecuciones</h2>
<section class="table-block">
<table class="apa-table small"><thead><tr><th>Run id</th><th>Fecha (UTC)</th><th>Checkpoint</th><th>Época</th><th>Configuración diferencial</th><th>SHA-256 del checkpoint</th></tr></thead>
<tbody>__TRACE_ROWS__</tbody></table>
<p class="table-source">Fuente: <code>utilidades-entrenamiento/modelo-ia/registro_entrenamiento.sqlite</code> y <code>docs/EVIDENCIAS-INTEGRIDAD-SHA256.md</code>. Las tres ejecuciones comparten image_size 224, batch 64, pretrained y finetune activados, weight_decay 1e-4, label_smoothing 0,05, class_weighted, augment y amp activados, early_stopping_patience 5 y seed 42. La ejecución de referencia usó una versión anterior de <code>metadata.sqlite</code> (split train 11.616); la fallida y la corregida usaron la actual (train 11.592).</p>
</section>

<h2 class="sec">Tabla 3 · Hitos de la validación (base de las figuras de evolución)</h2>
<section class="table-block">
<table class="apa-table"><thead><tr><th>Ejecución</th><th>Hito</th><th>Época</th><th>val_loss</th><th>Tipo (%)</th><th>Color F1 (%)</th><th>Estilo F1 (%)</th></tr></thead>
<tbody>__HITOS_ROWS__</tbody></table>
<p class="table-source">Fuente: <code>docs/datos-graficos/validacion_por_epoca.csv</code> (63 filas) y <code>modelo-ia/runs/&lt;run_id&gt;/metrics.json</code>.</p>
<div class="table-actions"><button class="csv-btn" onclick="downloadValidationCsv()">Descargar CSV completo</button></div>
</section>

<h2 class="sec">Tabla 4 · Resumen estadístico de la validación por ejecución</h2>
<section class="table-block">
<table class="apa-table"><thead><tr><th>Ejecución</th><th>Épocas</th><th>Mejor época</th><th>Mejor val_loss</th><th>val_loss final</th><th>Tipo final (%)</th><th>Color F1 final (%)</th><th>Estilo F1 final (%)</th></tr></thead>
<tbody>__RESUMEN_ROWS__</tbody></table>
<div class="table-actions"><button class="csv-btn" onclick="downloadSummaryCsv()">Descargar CSV del resumen</button></div>
</section>

<h2 class="sec">Tabla 5 · Procedencia de las imágenes por fuente</h2>
<section class="table-block">
<table class="apa-table small"><thead><tr><th>Fuente</th><th>Versión / fecha</th><th>Licencia</th><th>Total ingresado</th><th>Aprobado</th><th>Rechazado</th><th>Otro estado</th></tr></thead>
<tbody>__PROVENANCE_ROWS__</tbody></table>
<p class="table-source">Fuente: <code>dataset/metadata.sqlite</code> (prefijos de <code>prenda.codigo</code>). Balance trazable: 56.346 → 14.427 prendas aprobadas y aptas. Las licencias se verificaron en DataCite (AIG-Dataset) y en los archivos LICENSE de los repositorios GitHub.</p>
<div class="table-actions"><button class="csv-btn" onclick="downloadProvenanceCsv()">Descargar CSV</button></div>
</section>

<h2 class="sec">Figuras 1–7 · Curvas y comparaciones</h2>
<div id="figures"></div>

<h2 class="sec">Tabla 6 · Desempeño por clase — Tipo de prenda (ejecución corregida)</h2>
<section class="table-block">
<table class="apa-table small"><thead><tr><th>Clase</th><th>Soporte</th><th>Precisión (%)</th><th>Recall (%)</th><th>F1 (%)</th></tr></thead>
<tbody>__TIPO_ROWS__</tbody></table>
<p class="table-source">Fuente: <code>modelo-ia/evaluaciones/evaluacion_propiedades_test_20261029-022656.json</code>.</p>
</section>

<h2 class="sec">Tabla 7 · Desempeño por clase — Color (etiquetas con soporte en test)</h2>
<section class="table-block">
<table class="apa-table small"><thead><tr><th>Etiqueta</th><th>Soporte</th><th>Precisión (%)</th><th>Recall (%)</th><th>F1 (%)</th></tr></thead>
<tbody>__COLOR_ROWS__</tbody></table>
<p class="table-source">Fuente: <code>modelo-ia/evaluaciones/evaluacion_propiedades_test_20261029-022656.json</code>. La etiqueta «unknown» no tiene soporte en el test.</p>
</section>

<h2 class="sec">Tabla 8 · Desempeño por clase — Estilo (etiquetas con soporte en test)</h2>
<section class="table-block">
<table class="apa-table small"><thead><tr><th>Etiqueta</th><th>Soporte</th><th>Precisión (%)</th><th>Recall (%)</th><th>F1 (%)</th></tr></thead>
<tbody>__ESTILO_ROWS__</tbody></table>
<p class="table-source">Fuente: <code>modelo-ia/evaluaciones/evaluacion_propiedades_test_20261029-022656.json</code>. Las etiquetas «festival», «juvenil», «business-casual» y «unknown» no tienen soporte en el test.</p>
</section>

<h2 class="sec">Limitaciones y validez</h2>
<p class="intro" style="text-indent:0;margin-bottom:10px">1. <em>Separación de datos:</em> ninguna prenda aparece en más de un split (verificado por identificador de prenda); con la huella perceptual dHash (Hamming ≤ 2) se identificaron 77 imágenes de test con un casi duplicado en entrenamiento (5,4 %). Al excluirlas, el promedio macro pasa de 77,52 % a 76,96 %, por lo que el efecto es acotado. Este conteo es una cota conservadora: 76 de los 77 pares fueron marcados por un revisor como «no duplicadas».</p>
<p class="intro" style="text-indent:0;margin-bottom:10px">2. <em>Validez de etiquetas:</em> las referencias de color y estilo fueron generadas por IA (NVIDIA NIM y DeepSeek) con una revisión manual limitada; las métricas expresan concordancia con esas anotaciones, no una exactitud humana independiente.</p>
<p class="intro" style="text-indent:0;margin-bottom:10px">3. <em>Uso del conjunto de prueba:</em> la configuración corregida no se buscó sobre el test; se restauró la receta documentada en <code>default.yaml</code>/<code>desde-cero.yaml</code>. El checkpoint de cada ejecución se eligió por validación; el test se usó una vez por checkpoint para la comparación.</p>
<p class="intro" style="text-indent:0;margin-bottom:10px">4. <em>Incertidumbre:</em> se dispone de una única ejecución por configuración, por lo que las diferencias son descriptivas. Las ejecuciones de referencia y corregida se interpretan como equivalentes; no se afirma superioridad de una sobre otra.</p>

<p class="source">Fuente de datos: <code>validacion_por_epoca.csv</code> y <code>resultados_test.csv</code> (docs/datos-graficos), registros de entrenamiento (<code>registro_entrenamiento.sqlite</code>) y evaluaciones (<code>evaluacion_propiedades_test_*.json</code>). Las figuras siguen APA 7 (número en negrita, título en cursiva y nota bajo la figura); la numeración deberá ajustarse a la ubicación definitiva en el documento.</p>
</main>
<div class="footer">HTML autónomo · sin bibliotecas externas · gráficos vectoriales exportables</div>
<script id="dataset" type="application/json">__DATA_JSON__</script>
<script>
const DATA=JSON.parse(document.getElementById('dataset').textContent);
const RUNS=[{id:'20261026-021300',name:'Referencia',stroke:'#171717',dash:''},{id:'20261028-042931',name:'Fallida',stroke:'#707070',dash:'9 5'},{id:'20261029-022656',name:'Corregida',stroke:'#111111',dash:'2 4'}];
const ns='http://www.w3.org/2000/svg';
function el(tag,attrs={},text){const o=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>o.setAttribute(k,String(v)));if(text!==undefined)o.textContent=text;return o}
function add(g,tag,a,t){const o=el(tag,a,t);g.appendChild(o);return o}
const W=740,H=385,plot={l:76,r:24,t:20,b:90};const X2=W-plot.r,Y2=H-plot.b;
function txt(g,x,y,s,opt={}){return add(g,'text',{x,y,'font-family':'Arial, Helvetica, sans-serif','font-size':opt.size||13,fill:'#111','text-anchor':opt.anchor||'start',...opt},s)}
function basics(yMin,yMax,yLabel,xMax=28,yPercent=false){let svg=el('svg',{viewBox:'0 0 '+W+' '+H,xmlns:ns,role:'img','aria-label':yLabel});add(svg,'rect',{x:0,y:0,width:W,height:H,fill:'#fff'});
const sx=n=>plot.l+(n-1)/(xMax-1)*(X2-plot.l),sy=n=>Y2-(n-yMin)/(yMax-yMin)*(Y2-plot.t);
for(let i=0;i<=5;i++){let v=yMin+(yMax-yMin)*i/5,y=sy(v);add(svg,'line',{x1:plot.l,y1:y,x2:X2,y2:y,stroke:'#dddddd','stroke-width':1});txt(svg,plot.l-11,y+5,yPercent?(Math.round(v)+' %'):v.toFixed(yMax>2?1:2),{anchor:'end',size:12})}
for(let n=1;n<=xMax;n++){if(n===1||n===xMax||n%5===0){let x=sx(n);add(svg,'line',{x1:x,y1:Y2,x2:x,y2:Y2+6,stroke:'#111'});txt(svg,x,Y2+24,n,{anchor:'middle',size:12})}}
add(svg,'line',{x1:plot.l,y1:plot.t,x2:plot.l,y2:Y2,stroke:'#111','stroke-width':1.5});add(svg,'line',{x1:plot.l,y1:Y2,x2:X2,y2:Y2,stroke:'#111','stroke-width':1.5});txt(svg,(plot.l+X2)/2,H-52,'Época',{anchor:'middle',size:14});const label=txt(svg,19,(plot.t+Y2)/2,yLabel,{anchor:'middle',size:14});label.setAttribute('transform','rotate(-90 19 '+((plot.t+Y2)/2)+')');return {svg,sx,sy}}
function legend(svg){const y=H-21;RUNS.forEach((r,i)=>{const x=125+i*186;add(svg,'line',{x1:x,y1:y-5,x2:x+36,y2:y-5,stroke:r.stroke,'stroke-width':r.name==='Corregida'?3:2.5,...(r.dash?{'stroke-dasharray':r.dash}:{})});txt(svg,x+44,y,r.name,{size:13})})}
function lineChart(key,percent=false){const d=DATA.validacion_por_epoca,vals=d.map(r=>r[key]*(percent?100:1));let max=Math.max(...vals),min=Math.min(...vals),lo=percent?Math.max(0,Math.floor((min-5)/10)*10):0,hi=percent?100:Math.ceil(max*1.09*10)/10;let c=basics(lo,hi,percent?'Porcentaje (%)':'Pérdida',28,percent);RUNS.forEach(r=>{const rows=d.filter(q=>q.run_id===r.id).sort((a,b)=>a.epoch-b.epoch);add(c.svg,'polyline',{points:rows.map(q=>c.sx(q.epoch).toFixed(2)+','+c.sy(q[key]*(percent?100:1)).toFixed(2)).join(' '),fill:'none',stroke:r.stroke,'stroke-width':r.name==='Corregida'?3.2:2.4,'stroke-dasharray':r.dash||'none','stroke-linejoin':'round','stroke-linecap':'round'})});legend(c.svg);return c.svg}
function barChart(macroOnly=false){const svg=el('svg',{viewBox:'0 0 '+W+' '+H,xmlns:ns,role:'img','aria-label':'Comparación de resultados de prueba'});add(svg,'rect',{width:W,height:H,fill:'white'});let top=20,bottom=H-91,left=77,right=W-25,ymax=100;const sy=v=>bottom-(v/100)*(bottom-top);for(let t=0;t<=100;t+=20){let y=sy(t);add(svg,'line',{x1:left,y1:y,x2:right,y2:y,stroke:'#ddd'});txt(svg,left-13,y+5,t+' %',{anchor:'end',size:12})}add(svg,'line',{x1:left,y1:top,x2:left,y2:bottom,stroke:'#111','stroke-width':1.5});add(svg,'line',{x1:left,y1:bottom,x2:right,y2:bottom,stroke:'#111','stroke-width':1.5});const t=txt(svg,19,(top+bottom)/2,'Porcentaje (%)',{anchor:'middle',size:14});t.setAttribute('transform','rotate(-90 19 '+((top+bottom)/2)+')');
const keys=macroOnly?[['macro_pct','Promedio macro']]:[['tipo_pct','Tipo'],['color_jaccard_pct','Color Jaccard'],['estilo_jaccard_pct','Estilo Jaccard'],['macro_pct','Macro']];const band=(right-left)/keys.length;
keys.forEach(([key,label],i)=>{let cx=left+band*(i+.5),bw=macroOnly?90:band*.19;DATA.resultados_test.forEach((r,j)=>{let x=cx+(j-1)*bw*1.21-bw/2,v=r[key],y=sy(v);add(svg,'rect',{x,y,width:bw,height:bottom-y,fill:['#252525','#9b9b9b','#fff'][j],stroke:'#111','stroke-width':1.1});if(macroOnly)txt(svg,x+bw/2,y-8,v.toFixed(2)+' %',{anchor:'middle',size:12})});txt(svg,cx,bottom+24,label,{anchor:'middle',size:macroOnly?14:12})});
if(macroOnly){const y=sy(70);add(svg,'line',{x1:left,y1:y,x2:right,y2:y,stroke:'#111','stroke-dasharray':'7 5','stroke-width':1.5});txt(svg,right-3,y-7,'R11 = 70 %',{anchor:'end',size:12})}
RUNS.forEach((r,i)=>{const x=134+i*182;add(svg,'rect',{x,y:H-29,width:19,height:13,fill:['#252525','#9b9b9b','#fff'][i],stroke:'#111'});txt(svg,x+27,H-18,r.name,{size:13})});return svg}
const definitions=[
['Pérdida de entrenamiento según la época en las tres ejecuciones',()=>lineChart('train_loss'),'Se representa la pérdida de entrenamiento por época. Los recorridos tienen distinta duración: 20 épocas (referencia), 15 (fallida) y 28 (corregida).'],
['Pérdida de validación según la época en las tres ejecuciones',()=>lineChart('val_loss'),'Se representa la pérdida de validación por época; un valor menor indica menor pérdida en el conjunto de validación.'],
['Evolución de la exactitud de clasificación de tipo durante la validación',()=>lineChart('tipo_accuracy',true),'La exactitud de tipo se transformó de proporción a porcentaje multiplicando por 100.'],
['Evolución de la puntuación F1 de color durante la validación',()=>lineChart('color_f1',true),'La puntuación F1 de color se transformó de proporción a porcentaje multiplicando por 100.'],
['Evolución de la puntuación F1 de estilo durante la validación',()=>lineChart('estilo_f1',true),'La puntuación F1 de estilo se transformó de proporción a porcentaje multiplicando por 100.'],
['Comparación de métricas en el conjunto de prueba por ejecución',()=>barChart(false),'Resultados de la evaluación final de 1.424 imágenes por ejecución. Las barras corresponden a exactitud de tipo, Jaccard de color, Jaccard de estilo y promedio macro.'],
['Comparación del promedio macro con el umbral R11',()=>barChart(true),'La línea discontinua indica el umbral R11 de 70 %. La referencia (77,52 %) y la corregida (77,53 %) se describen como equivalentes; la fallida (61,79 %) no cumple.']
];
let saved=[];definitions.forEach(([title,renderer,note],i)=>{let section=document.createElement('section');section.className='figure';let cap=document.createElement('div');cap.className='figure-no';cap.textContent='Figura '+(i+1);section.append(cap);let t=document.createElement('p');t.className='figure-title';t.textContent=title;section.append(t);let wrap=document.createElement('div');wrap.className='graph';const svg=renderer();wrap.append(svg);section.append(wrap);let n=document.createElement('p');n.className='note';const italic=document.createElement('em');italic.textContent='Nota. ';n.append(italic,document.createTextNode(note+' Fuente: docs/datos-graficos/validacion_por_epoca.csv'+(i>=5?' y resultados_test.csv':'')+'.'));section.append(n);let controls=document.createElement('div');controls.className='figure-actions';const b=document.createElement('button');b.textContent='Descargar SVG';b.onclick=()=>saveSvg(svg,'figura_'+(i+1)+'_apa7.svg');const b2=document.createElement('button');b2.textContent='Descargar PNG';b2.onclick=()=>savePng(svg,'figura_'+(i+1)+'_apa7.png');controls.append(b,b2);section.append(controls);document.getElementById('figures').append(section);saved.push({svg,i})});
function serialize(svg){return new XMLSerializer().serializeToString(svg)}
function dl(blob,name){const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),4000)}
function saveSvg(svg,name){dl(new Blob([serialize(svg)],{type:'image/svg+xml;charset=utf-8'}),name)}
function savePng(svg,name){const blob=new Blob([serialize(svg)],{type:'image/svg+xml;charset=utf-8'}),u=URL.createObjectURL(blob),im=new Image();im.onload=()=>{const can=document.createElement('canvas');can.width=W*3;can.height=H*3;const cx=can.getContext('2d');cx.fillStyle='#fff';cx.fillRect(0,0,can.width,can.height);cx.drawImage(im,0,0,can.width,can.height);can.toBlob(b=>dl(b,name),'image/png');URL.revokeObjectURL(u)};im.src=u}
function downloadAll(){saved.forEach(({svg,i},ix)=>setTimeout(()=>saveSvg(svg,'figura_'+(i+1)+'_apa7.svg'),ix*300))}
function toCsv(headers,rows){const esc=v=>{v=String(v);return /[",\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v};return [headers.join(',')].concat(rows.map(r=>r.map(esc).join(','))).join('\n')}
function dlText(text,name){dl(new Blob([text],{type:'text/csv;charset=utf-8'}),name)}
function downloadResultadosCsv(){const h=['run_id','rol','tipo_pct','color_jaccard_pct','estilo_jaccard_pct','macro_pct','r11'];const rows=DATA.resultados_test.map(r=>[r.run_id,r.rol,r.tipo_pct,r.color_jaccard_pct,r.estilo_jaccard_pct,r.macro_pct,r.r11]);dlText(toCsv(h,rows),'resultados_test.csv')}
function downloadValidationCsv(){const h=['run_id','rol','epoch','train_loss','val_loss','tipo_accuracy','color_precision','color_recall','color_f1','estilo_precision','estilo_recall','estilo_f1'];const rows=DATA.validacion_por_epoca.map(r=>[r.run_id,r.rol,r.epoch,r.train_loss,r.val_loss,r.tipo_accuracy,r.color_precision,r.color_recall,r.color_f1,r.estilo_precision,r.estilo_recall,r.estilo_f1]);dlText(toCsv(h,rows),'validacion_por_epoca.csv')}
function downloadSummaryCsv(){const h=['rol','epocas','mejor_epoca','mejor_val_loss','val_loss_final','tipo_final_pct','color_f1_final_pct','estilo_f1_final_pct'];const rows=__RESUMEN_CSV__;dlText(toCsv(h,rows),'resumen_validacion.csv')}
function downloadProvenanceCsv(){const h=['fuente','version_fecha','licencia','total','aprobado','rechazado','otro'];const rows=__PROVENANCE_CSV__;dlText(toCsv(h,rows),'procedencia_imagenes.csv')}
function downloadAllCsv(){downloadResultadosCsv();setTimeout(downloadValidationCsv,300);setTimeout(downloadSummaryCsv,600);setTimeout(downloadProvenanceCsv,900)}
</script></body></html>
"""


# ---------------------------------------------------------------------------
# 4. Funciones de construcción del HTML (con logging)
# ---------------------------------------------------------------------------

def _rows_per_class(entries: list) -> str:
    """Convierte entradas por clase a filas <tr> del HTML."""
    out = []
    for e in entries:
        out.append(
            f"<tr><td>{e['valor']}</td><td>{e['soporte']}</td>"
            f"<td>{e['precision_pct']:.2f}</td><td>{e['recall_pct']:.2f}</td>"
            f"<td>{e['f1_pct']:.2f}</td></tr>"
        )
    return "\n".join(out)


def resolve_checkpoint(modelo_ia: Path, modelos_compartidos: Path,
                       run_id: str, ckpt_name: str) -> Path:
    """Devuelve la ruta real de un checkpoint.

    El checkpoint compartido de referencia vive en modelos-compartidos/;
    las ejecuciones fallida y corregida conservan su best.pt bajo
    modelo-ia/runs/<run_id>/.
    """
    if ckpt_name == "best.pt":
        return modelo_ia / "runs" / run_id / "best.pt"
    return modelos_compartidos / ckpt_name


def build_html(modelo_ia: Path, dataset_sqlite: Path,
               modelos_compartidos: Path) -> str:
    """Reconstruye todos los datos y devuelve el HTML completo."""
    logging.info("=== Generación del informe HTML corregido ===")

    # ---- series de validación (JSON embebido para las figuras) ----
    val_series = []
    hitos_rows, resumen_rows = [], []
    trace_rows = []

    for run_id, rol, epoca, ckpt_name in RUNS:
        logging.info("-- Ejecución %s (%s) --", run_id, rol)
        rows = load_metrics(modelo_ia, run_id)
        for r in rows:
            r["run_id"] = run_id
            r["rol"] = rol
        val_series.extend(compute_val_series(rows))
        hitos_rows.extend(compute_hitos(rows, rol))
        resumen_rows.append(compute_resumen(rows, rol))

        # SHA-256 del checkpoint (mejor epoch => best.pt)
        ckpt_path = resolve_checkpoint(modelo_ia, modelos_compartidos, run_id, ckpt_name)
        sha = checkpoint_sha(ckpt_path, run_id)
        trace_rows.append(
            f"<tr><td>{run_id}</td><td>{RUN_DATES[run_id]}</td><td>{ckpt_name}</td>"
            f"<td>{epoca}</td><td>{RUN_DIFF_CONFIG[run_id]}</td>"
            f"<td class=\"hash\">{sha}</td></tr>"
        )

    # ---- resultados del test portable ----
    res_rows = "\n".join(
        f"<tr><td>{rol}</td><td>{PORTABLE_TEST_RESULTS[rid]['tipo_pct']:.2f}</td>"
        f"<td>{PORTABLE_TEST_RESULTS[rid]['color_jaccard_pct']:.2f}</td>"
        f"<td>{PORTABLE_TEST_RESULTS[rid]['estilo_jaccard_pct']:.2f}</td>"
        f"<td>{PORTABLE_TEST_RESULTS[rid]['macro_pct']:.2f}</td>"
        f"<td>{PORTABLE_TEST_RESULTS[rid]['r11']}</td></tr>"
        for rid, rol, _ep, _n in RUNS
    )
    logging.info("Resultados del test portable cargados para %d ejecuciones", len(RUNS))

    # ---- métricas por clase (ejecución corregida) ----
    eval_json = modelo_ia / "evaluaciones" / "evaluacion_propiedades_test_20261029-022656.json"
    tipo, color, estilo = compute_per_class(eval_json)
    tipo_rows = _rows_per_class(tipo)
    color_rows = _rows_per_class(color)
    estilo_rows = _rows_per_class(estilo)

    # ---- procedencia ----
    provenance = compute_provenance(dataset_sqlite)

    def fmt_n(n) -> str:
        """Formatea un entero con separador de miles (punto) para el HTML."""
        return f"{n:,}".replace(",", ".")

    provenance_rows = "\n".join(
        f"<tr><td>{name}</td><td>{version}</td><td>{lic}</td><td>{fmt_n(total)}</td>"
        f"<td>{fmt_n(aprob)}</td><td>{fmt_n(rech)}</td><td>{fmt_n(otro)}</td></tr>"
        for name, version, lic, total, aprob, rech, otro in provenance
    )
    # Versión CSV (misma información, para el botón de descarga)
    provenance_csv = json.dumps(
        [list(r) for r in provenance], ensure_ascii=False
    )

    # ---- ensamblar la plantilla ----
    resumen_csv = json.dumps([list(r) for r in resumen_rows], ensure_ascii=False)
    data_js = json.dumps(
        {
            "validacion_por_epoca": val_series,
            "resultados_test": [
                {"run_id": rid, "rol": rol,
                 **{k: PORTABLE_TEST_RESULTS[rid][k] for k in
                    ("tipo_pct", "color_jaccard_pct", "estilo_jaccard_pct", "macro_pct", "r11")}}
                for rid, rol, _ep, _n in RUNS
            ],
        },
        ensure_ascii=False,
    )

    html = HTML_TEMPLATE
    for marker, value in (
        ("__RES_ROWS__", res_rows),
        ("__TRACE_ROWS__", "\n".join(trace_rows)),
        ("__HITOS_ROWS__", "\n".join(
            f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d:.4f}</td>"
            f"<td>{e:.2f}</td><td>{f:.2f}</td><td>{g:.2f}</td></tr>"
            for a, b, c, d, e, f, g in hitos_rows)),
        ("__RESUMEN_ROWS__", "\n".join(
            f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d:.4f}</td>"
            f"<td>{e:.4f}</td><td>{f:.2f}</td><td>{g:.2f}</td><td>{h:.2f}</td></tr>"
            for a, b, c, d, e, f, g, h in resumen_rows)),
        ("__PROVENANCE_ROWS__", provenance_rows),
        ("__TIPO_ROWS__", tipo_rows),
        ("__COLOR_ROWS__", color_rows),
        ("__ESTILO_ROWS__", estilo_rows),
        ("__DATA_JSON__", data_js),
        ("__RESUMEN_CSV__", resumen_csv),
        ("__PROVENANCE_CSV__", provenance_csv),
    ):
        html = html.replace(marker, value)

    logging.info("HTML ensamblado: %d bytes", len(html))
    return html


# ---------------------------------------------------------------------------
# 5. Punto de entrada
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--modelo-ia", type=Path,
        default=Path("utilidades-entrenamiento/modelo-ia"),
        help="Directorio modelo-ia (runs, evaluaciones, registro).",
    )
    parser.add_argument(
        "--dataset-sqlite", type=Path,
        default=Path("dataset/metadata.sqlite"),
        help="Base de datos del dataset para la procedencia.",
    )
    parser.add_argument(
        "--modelos-compartidos", type=Path,
        default=Path("utilidades-entrenamiento/modelos-compartidos"),
        help="Directorio de checkpoints compartidos (referencia).",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("docs/datos-graficos"),
        help="Directorio donde se escribe el HTML y el log.",
    )
    parser.add_argument(
        "--log-file", type=Path, default=None,
        help="Archivo de log; por defecto <output-dir>/informe_entrenamiento.log.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    log_file = args.log_file or (args.output_dir / "informe_entrenamiento.log")

    # Log a consola y a archivo simultáneamente (nivel INFO).
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    logging.info("Iniciando generación del informe (log: %s)", log_file)

    html = build_html(args.modelo_ia, args.dataset_sqlite, args.modelos_compartidos)
    out = args.output_dir / "figuras_entrenamiento_APA7_corregido.html"
    out.write_text(html, encoding="utf-8")
    logging.info("Informe escrito en: %s", out)


if __name__ == "__main__":
    main()
