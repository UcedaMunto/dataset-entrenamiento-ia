#!/usr/bin/env python3
"""API de pruebas (DSR) para la API de descripción de prendas.

Ejecuta la prueba diseñada en docs/DSR-PRUEBA-API.md sobre el conjunto
portable de test (tests/imagenes-test/) y devuelve las métricas del informe:
exactitud de tipo, Jaccard de color y estilo, y promedio macro de propiedades.
No entrena ni modifica pesos; solo infiere en CPU.
"""
import hashlib
import json
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import torch
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from PIL import Image, UnidentifiedImageError
from torchvision import transforms

from evaluate_properties import macro_property_average, summarize_multilabel, summarize_types
from train import MultiTaskMobileNet


DEFAULT_CHECKPOINT = Path(__file__).resolve().parent / "modelos-compartidos" / "mobilenetv3-small-best.pt"
CHECKPOINT_PATH = Path(os.environ.get("MODEL_CHECKPOINT", str(DEFAULT_CHECKPOINT)))

# En Docker, TEST_IMAGES_ROOT se define en el Compose (por ejemplo /app/test-imagenes).
DEFAULT_TEST_ROOT = Path(__file__).resolve().parents[1] / "tests" / "imagenes-test"
TEST_IMAGES_ROOT = Path(os.environ.get("TEST_IMAGES_ROOT", str(DEFAULT_TEST_ROOT)))
MANIFEST_PATH = TEST_IMAGES_ROOT / "manifest.json"

DEFAULT_RESULTS_DIR = Path(__file__).resolve().parents[1] / "tests" / "resultados"
RESULTS_DIR = Path(os.environ.get("TEST_RESULTS_DIR", str(DEFAULT_RESULTS_DIR)))

DEFAULT_DESIGN_DOC = Path(__file__).resolve().parents[1] / "docs" / "DSR-PRUEBA-API.md"
DESIGN_DOC_PATH = Path(os.environ.get("TEST_DESIGN_DOC", str(DEFAULT_DESIGN_DOC)))

API_VERSION = "1.1.0"
R11_THRESHOLD_PCT = 70.0
TRAIN_IMAGES_DECLARED = int(os.environ.get("TRAIN_IMAGES_DECLARED", "11616"))
REFERENCE_RESULT = {
    "tipo_prenda_pct": 94.94,
    "color_jaccard_pct": 68.42,
    "estilo_jaccard_pct": 69.21,
    "promedio_macro_pct": 77.52,
    "criterio_R11_cumple": True,
}

RUN_LOCK = threading.Lock()
model = None
checkpoint = None
transform = None
manifest = None


def load_checkpoint(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"No existe el checkpoint: {path}")
    saved = torch.load(path, map_location="cpu", weights_only=True)
    classes = saved.get("classes")
    if not isinstance(classes, dict) or any(
        not isinstance(classes.get(key), list) or not classes[key]
        for key in ("tipo_prenda", "color", "estilo")
    ):
        raise ValueError("El checkpoint no contiene un catálogo de clases válido.")
    loaded_model = MultiTaskMobileNet(
        type_count=len(classes["tipo_prenda"]),
        color_count=len(classes["color"]),
        style_count=len(classes["estilo"]),
        pretrained=False,
    )
    loaded_model.load_state_dict(saved["state_dict"])
    loaded_model.to(torch.device("cpu")).eval()
    image_transform = transforms.Compose([
        transforms.Resize((saved["image_size"], saved["image_size"])),
        transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
    ])
    return loaded_model, saved, image_transform


def load_manifest(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"No existe el manifest de test: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    classes = data.get("classes")
    images = data.get("imagenes")
    if not isinstance(classes, dict) or any(
        not isinstance(classes.get(key), list) or not classes[key]
        for key in ("tipo_prenda", "color", "estilo")
    ):
        raise ValueError("El manifest no contiene un catálogo de clases válido.")
    if not isinstance(images, list) or not images:
        raise ValueError("El manifest no contiene imágenes de test.")
    missing = [entry.get("archivo") for entry in images if not (TEST_IMAGES_ROOT / entry.get("archivo", "")).is_file()]
    if missing:
        raise FileNotFoundError(f"Faltan {len(missing)} imágenes de test; primera: {missing[0]}")
    return data


def binarize(labels, classes: list[str]) -> torch.Tensor:
    label_set = set(labels or [])
    return torch.tensor([value in label_set for value in classes], dtype=torch.bool)


def checkpoint_sha256() -> str:
    return hashlib.sha256(CHECKPOINT_PATH.read_bytes()).hexdigest()


def manifest_sha256() -> str:
    return hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()


def manifest_summary() -> dict:
    classes = manifest["classes"]
    counts_by_type = {value: 0 for value in classes["tipo_prenda"]}
    no_color = 0
    no_style = 0
    for entry in manifest["imagenes"]:
        counts_by_type[entry["tipo_prenda"]] = counts_by_type.get(entry["tipo_prenda"], 0) + 1
        if not entry.get("colores"):
            no_color += 1
        if not entry.get("estilos"):
            no_style += 1
    return {
        "ruta": str(MANIFEST_PATH),
        "sha256": manifest_sha256(),
        "descripcion": manifest.get("descripcion"),
        "generado": manifest.get("generado"),
        "origen": manifest.get("origen"),
        "total_imagenes": len(manifest["imagenes"]),
        "umbral_multietiqueta": manifest.get("umbral_multietiqueta"),
        "image_size": manifest.get("image_size"),
        "classes": classes,
        "imagenes_por_tipo": counts_by_type,
        "imagenes_sin_color": no_color,
        "imagenes_sin_estilo": no_style,
    }


def checkpoint_info() -> dict:
    return {
        "ruta": str(CHECKPOINT_PATH),
        "sha256": checkpoint_sha256(),
        "arquitectura": checkpoint.get("architecture") if checkpoint else None,
        "epoca": checkpoint.get("epoch") if checkpoint else None,
        "image_size": checkpoint.get("image_size") if checkpoint else None,
        "umbral_multietiqueta": checkpoint.get("multilabel_threshold") if checkpoint else None,
        "validacion_checkpoint": checkpoint.get("validation") if checkpoint else None,
        "imagenes_entrenamiento_declaradas": TRAIN_IMAGES_DECLARED,
        "nota_imagenes_entrenamiento": (
            "Valor declarado en EVALUACION-ENTRENAMIENTO.md para el checkpoint compartido; "
            "no se deriva del archivo de pesos."
        ),
    }


def operational_definitions() -> dict:
    return {
        "exactitud_tipo": "Exactitud de tipo = (tipos correctos / T) · 100, con T el total de imágenes de prueba.",
        "jaccard_color_estilo": (
            "Jaccard promedio por imagen = (1/T) · Σ |P_i ∩ R_i| / |P_i ∪ R_i|, para color y estilo; "
            "si ambos conjuntos están vacíos vale 1."
        ),
        "promedio_macro": (
            "Media aritmética sin ponderar de exactitud de tipo, Jaccard de color y Jaccard de estilo; "
            "cada propiedad pesa 1/3."
        ),
        "delta_macro": "Δmacro = macro(checkpoint final) − macro(checkpoint inicial), expresado en puntos porcentuales.",
        "criterio_R11": f"promedio macro ≥ {R11_THRESHOLD_PCT:.0f} %.",
    }


def dsr_correspondence() -> dict:
    return {
        "1_identificacion_del_problema": (
            "Medir si la API de descripción de prendas reconoce tipo, color y estilo en imágenes no vistas, "
            "y reproducir la prueba en el equipo de producción."
        ),
        "2_objetivos": (
            "Obtener exactitud de tipo, Jaccard de color y estilo, y promedio macro; contrastar con el requisito R11."
        ),
        "3_diseno_y_desarrollo": (
            "API de pruebas test-api + conjunto portable tests/imagenes-test/ con manifest de etiquetas y SHA-256."
        ),
        "4_demostracion": "POST /test/run sobre las 1.424 imágenes; reporte JSON por ejecución.",
        "5_evaluacion": "Cálculo de las cuatro métricas y verificación del criterio R11 por checkpoint.",
        "6_comunicacion": (
            "Resultados en este JSON y en tests/resultados/reporte_*.json, para el informe y el Anexo G."
        ),
    }


def control_conditions() -> dict:
    return {
        "variables_constantes": [
            "1.424 imágenes de test (manifest.json con SHA-256 por imagen)",
            "Etiquetas de referencia generadas por NVIDIA NIM y DeepSeek",
            "Preprocesamiento (resize 224 y normalización ImageNet)",
            "Vocabulario de clases del checkpoint (tipo, color, estilo)",
            "Umbral multietiqueta 0.5",
            "Script de evaluación test_api.py",
            "Dispositivo de ejecución (CPU por defecto)",
        ],
        "variables_que_cambian": [
            "Checkpoint/época evaluada (C1 inicial, C2 intermedia opcional, C3 final)",
            "Número de imágenes de entrenamiento si la ejecución de entrenamiento difiere (factor adicional a declarar)",
        ],
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global model, checkpoint, transform, manifest
    thread_count = max(1, int(os.environ.get("API_CPU_THREADS", "4")))
    torch.set_num_threads(thread_count)
    model, checkpoint, transform = load_checkpoint(CHECKPOINT_PATH)
    manifest = load_manifest(MANIFEST_PATH)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="API de pruebas (DSR) de reconocimiento de prendas",
    version=API_VERSION,
    description=(
        "Ejecuta la prueba de la API de descripción de prendas definida en "
        "docs/DSR-PRUEBA-API.md sobre el conjunto portable tests/imagenes-test/."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8090", "http://localhost:8090"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def ensure_ready():
    if model is None or checkpoint is None or transform is None or manifest is None:
        raise HTTPException(status_code=503, detail="El modelo o el manifest todavía no están disponibles.")


def run_evaluation(device_name: str = "cpu", max_images: Optional[int] = None) -> dict:
    device = torch.device(device_name)
    classes = checkpoint["classes"]
    threshold = float(checkpoint["multilabel_threshold"])
    entries = manifest["imagenes"]
    if max_images is not None:
        entries = entries[:max_images]

    type_confusion = torch.zeros((len(classes["tipo_prenda"]),) * 2, dtype=torch.int64)
    color_predictions, color_targets = [], []
    style_predictions, style_targets = [], []
    errors = []
    started = time.perf_counter()

    with torch.inference_mode():
        for entry in entries:
            image_path = TEST_IMAGES_ROOT / entry["archivo"]
            try:
                with Image.open(image_path) as image:
                    tensor = transform(image.convert("RGB")).unsqueeze(0)
            except (OSError, UnidentifiedImageError) as error:
                errors.append({"archivo": entry["archivo"], "error": str(error)})
                continue

            outputs = model(tensor.to(device))
            predicted_type = int(outputs["type"].argmax(dim=1).item())
            true_type = entry["tipo_prenda"]
            type_index = classes["tipo_prenda"].index(true_type)
            type_confusion[type_index, predicted_type] += 1

            predicted_color = (outputs["color"].sigmoid()[0].cpu() >= threshold)
            predicted_style = (outputs["style"].sigmoid()[0].cpu() >= threshold)
            true_colors = entry.get("colores") or []
            true_styles = entry.get("estilos") or []
            if true_colors:
                color_predictions.append(predicted_color)
                color_targets.append(binarize(true_colors, classes["color"]))
            if true_styles:
                style_predictions.append(predicted_style)
                style_targets.append(binarize(true_styles, classes["estilo"]))

    def concatenate(parts, width):
        return torch.stack(parts) if parts else torch.zeros((0, width), dtype=torch.bool)

    color_pred = concatenate(color_predictions, len(classes["color"]))
    color_real = concatenate(color_targets, len(classes["color"]))
    style_pred = concatenate(style_predictions, len(classes["estilo"]))
    style_real = concatenate(style_targets, len(classes["estilo"]))

    type_summary = summarize_types(type_confusion, classes["tipo_prenda"])
    color_summary = summarize_multilabel(color_pred, color_real, classes["color"])
    style_summary = summarize_multilabel(style_pred, style_real, classes["estilo"])
    macro = macro_property_average(
        type_summary["accuracy_pct"],
        color_summary["coincidencia_parcial_jaccard_pct"],
        style_summary["coincidencia_parcial_jaccard_pct"],
    )
    return {
        "generado": datetime.now().astimezone().isoformat(timespec="seconds"),
        "software_version": f"test-api {API_VERSION}",
        "checkpoint": str(CHECKPOINT_PATH),
        "checkpoint_sha256": checkpoint_sha256(),
        "checkpoint_arquitectura": checkpoint.get("architecture"),
        "epoca_checkpoint": checkpoint.get("epoch"),
        "validacion_checkpoint": checkpoint.get("validation"),
        "imagenes_entrenamiento_declaradas": TRAIN_IMAGES_DECLARED,
        "device": device_name,
        "imagenes_evaluadas": len(entries) - len(errors),
        "imagenes_total_manifest": len(manifest["imagenes"]),
        "imagenes_con_error": errors,
        "umbral_multietiqueta": threshold,
        "sha256_manifest": manifest_sha256(),
        "promedio_macro_propiedades": macro,
        "criterio_R11": {
            "umbral_pct": R11_THRESHOLD_PCT,
            "promedio_macro_pct": macro["porcentaje"],
            "cumple": macro["porcentaje"] >= R11_THRESHOLD_PCT,
        },
        "manifest_resumen": manifest_summary(),
        "tipo_prenda": type_summary,
        "color": color_summary,
        "estilo": style_summary,
        "latencia_seg": round(time.perf_counter() - started, 2),
    }


def design_summary() -> dict:
    return {
        "metodologia": "Design Science Research (DSR)",
        "documento": str(DESIGN_DOC_PATH),
        "fases": {
            "1_problema": (
                "Medir si la API de descripción de prendas (MobileNetV3-Small) reconoce tipo, "
                "color y estilo en imágenes que no usó para entrenar, y reproducir la prueba "
                "en el equipo de producción, no solo en el nodo de entrenamiento."
            ),
            "2_objetivos": (
                "Reproducir las métricas del informe (tipo 94,94 %, color Jaccard 68,42 %, "
                "estilo Jaccard 69,21 %, macro 77,52 %) mediante una API."
            ),
            "3_artefacto": (
                "API de pruebas test-api (este servicio) + conjunto portable versionado en Git "
                "tests/imagenes-test/ con 1.424 imágenes y manifest.json."
            ),
            "4_demostracion": "POST /test/run (completo) o POST /test/run?max_images=10 (humo).",
            "5_evaluacion": {
                "tipo": "exactitud = tipos correctos / total",
                "color_estilo": "Jaccard parcial = media de |P∩R| / |P∪R| por imagen",
                "promedio_macro": "media simple de tipo, color y estilo (cada una pesa 1/3)",
                "criterio_aceptacion_R11": "macro ≥ 70 %",
            },
            "6_comunicacion": "JSON de resultados guardado en tests/resultados/ y diseño en docs/DSR-PRUEBA-API.md.",
        },
        "resultado_esperado": {
            "tipo_prenda_pct": 94.94,
            "color_jaccard_pct": 68.42,
            "estilo_jaccard_pct": 69.21,
            "promedio_macro_pct": 77.52,
        },
    }


def saved_reports() -> list[dict]:
    if not RESULTS_DIR.is_dir():
        return []
    reports = []
    for path in sorted(RESULTS_DIR.glob("reporte_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        data.setdefault("run_id", path.stem.removeprefix("reporte_"))
        data.setdefault("resultado_guardado", str(path))
        reports.append(data)
    return reports


def comparative_matrix(reports: list[dict]) -> list[dict]:
    rows = []
    for report in reports:
        macro = report.get("promedio_macro_propiedades", {}) or {}
        rows.append({
            "run_id": report.get("run_id"),
            "archivo": report.get("resultado_guardado"),
            "generado": report.get("generado"),
            "checkpoint": report.get("checkpoint"),
            "checkpoint_sha256": report.get("checkpoint_sha256"),
            "epoca_checkpoint": report.get("epoca_checkpoint"),
            "imagenes_entrenamiento_declaradas": report.get("imagenes_entrenamiento_declaradas"),
            "imagenes_evaluadas": report.get("imagenes_evaluadas"),
            "tipo_prenda_pct": (report.get("tipo_prenda") or {}).get("accuracy_pct"),
            "color_jaccard_pct": (report.get("color") or {}).get("coincidencia_parcial_jaccard_pct"),
            "estilo_jaccard_pct": (report.get("estilo") or {}).get("coincidencia_parcial_jaccard_pct"),
            "promedio_macro_pct": macro.get("porcentaje"),
            "cumple_R11": macro.get("porcentaje", 0) >= R11_THRESHOLD_PCT,
        })
    return rows


@app.get("/health")
def health():
    return {
        "status": "ok" if model is not None and manifest is not None else "loading",
        "device": "cpu",
        "checkpoint": str(CHECKPOINT_PATH),
        "test_manifest": {
            "total_imagenes": len(manifest["imagenes"]) if manifest else 0,
            "ruta": str(MANIFEST_PATH),
        },
    }


@app.get("/test/design")
def get_design():
    ensure_ready()
    return design_summary()


@app.get("/test/design/markdown")
def get_design_markdown():
    ensure_ready()
    if not DESIGN_DOC_PATH.is_file():
        raise HTTPException(status_code=404, detail=f"No existe el documento de diseño: {DESIGN_DOC_PATH}")
    return Response(content=DESIGN_DOC_PATH.read_text(encoding="utf-8"), media_type="text/markdown")


@app.get("/test/manifest")
def get_manifest_summary():
    ensure_ready()
    return manifest_summary()


@app.get("/test/informe")
def get_informe(run_id: Optional[str] = Query(None, description="Reporte guardado a usar; por defecto el más reciente.")):
    ensure_ready()
    reports = saved_reports()
    if run_id:
        selected = next((r for r in reports if r.get("run_id") == run_id), None)
        if selected is None:
            raise HTTPException(status_code=404, detail=f"No existe el reporte {run_id}.")
    else:
        selected = reports[0] if reports else None
    return {
        "tipo": "evidencia_informe_anexo_g",
        "generado": datetime.now().astimezone().isoformat(timespec="seconds"),
        "metodologia": "Design Science Research Methodology (DSRM)",
        "correspondencia_dsrm": dsr_correspondence(),
        "requisito_R11": {
            "id": "R11",
            "descripcion": "Reconocimiento de propiedades de prendas con promedio macro ≥ 70 %.",
            "criterio": f"promedio macro ≥ {R11_THRESHOLD_PCT:.0f} %",
            "umbral_pct": R11_THRESHOLD_PCT,
        },
        "indicadores": {
            "exactitud_tipo_pct": "Porcentaje de imágenes cuyo tipo predicho coincide con la etiqueta real.",
            "jaccard_color_pct": "Jaccard promedio por imagen para color.",
            "jaccard_estilo_pct": "Jaccard promedio por imagen para estilo.",
            "promedio_macro_pct": "Media simple de tipo, color y estilo (cada propiedad pesa 1/3).",
        },
        "condiciones_de_control": control_conditions(),
        "definiciones_operacionales": operational_definitions(),
        "conjunto_de_prueba": manifest_summary(),
        "checkpoint": checkpoint_info(),
        "resultado_referencia_documentado": REFERENCE_RESULT,
        "ultimo_resultado": selected,
        "matriz_comparativa": comparative_matrix(reports),
        "trazabilidad": {
            "software_version": f"test-api {API_VERSION}",
            "device": "cpu",
            "checkpoint_sha256": checkpoint_sha256(),
            "manifest_sha256": manifest_sha256(),
            "resultados_ubicacion": str(RESULTS_DIR),
            "nota": "Los reportes por ejecución quedan en tests/resultados/reporte_*.json.",
        },
    }


@app.get("/test/images")
def list_test_images(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=500)):
    ensure_ready()
    entries = manifest["imagenes"]
    start = (page - 1) * page_size
    stop = start + page_size
    return {
        "pagina": page,
        "page_size": page_size,
        "total": len(entries),
        "imagenes": entries[start:stop],
    }


@app.post("/test/run")
def run_test(
    max_images: Optional[int] = Query(None, ge=1, description="Limite opcional para una prueba de humo."),
    device: str = Query("cpu", pattern="^(cpu|cuda)$"),
):
    ensure_ready()
    if device == "cuda" and not torch.cuda.is_available():
        raise HTTPException(status_code=400, detail="CUDA fue solicitado, pero no hay GPU disponible.")
    with RUN_LOCK:
        report = run_evaluation(device, max_images)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = RESULTS_DIR / f"reporte_{run_id}.json"
    if output.exists():
        run_id = f"{run_id}-{int(time.time() * 1000) % 1000}"
        output = RESULTS_DIR / f"reporte_{run_id}.json"
    report["run_id"] = run_id
    report["resultado_guardado"] = str(output)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


@app.get("/test/results")
def list_results():
    if not RESULTS_DIR.is_dir():
        return {"resultados": []}
    files = sorted(RESULTS_DIR.glob("reporte_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    summaries = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        summaries.append({
            "run_id": path.stem.removeprefix("reporte_"),
            "archivo": path.name,
            "generado": data.get("generado"),
            "imagenes_evaluadas": data.get("imagenes_evaluadas"),
            "promedio_macro_propiedades": data.get("promedio_macro_propiedades", {}).get("porcentaje"),
        })
    return {"resultados": summaries}


@app.get("/test/results/{run_id}")
def get_result(run_id: str):
    path = RESULTS_DIR / f"reporte_{run_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"No existe el reporte {run_id}.")
    return JSONResponse(content=json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("test_api:app", host="0.0.0.0", port=8082, workers=1)
