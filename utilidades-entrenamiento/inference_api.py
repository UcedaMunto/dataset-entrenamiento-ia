#!/usr/bin/env python3
import io
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from torchvision import transforms

from train import MultiTaskMobileNet


MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
CHECKPOINT_PATH = Path(os.environ.get("MODEL_CHECKPOINT", "/models/best.pt"))
INFERENCE_LOCK = threading.Semaphore(2)
model = None
checkpoint = None
transform = None


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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global model, checkpoint, transform
    thread_count = max(1, int(os.environ.get("API_CPU_THREADS", "4")))
    torch.set_num_threads(thread_count)
    model, checkpoint, transform = load_checkpoint(CHECKPOINT_PATH)
    yield


app = FastAPI(
    title="API de reconocimiento de prendas",
    version="1.0.0",
    description="Inferencia CPU con un checkpoint MobileNetV3-Small ya entrenado.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def reject_oversized_requests(request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > (2 * MAX_IMAGE_BYTES + 1_000_000):
        return JSONResponse(status_code=413, content={"detail": "La solicitud supera el tamaño permitido."})
    return await call_next(request)


def decode_image(upload: UploadFile) -> Image.Image:
    raw = upload.file.read(MAX_IMAGE_BYTES + 1)
    if not raw:
        raise HTTPException(status_code=422, detail=f"La imagen {upload.filename or ''} está vacía.")
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Cada imagen debe pesar como máximo 10 MiB.")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in ALLOWED_FORMATS:
                raise HTTPException(status_code=415, detail="Formato admitido: JPEG, PNG o WebP.")
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise HTTPException(status_code=413, detail="Cada imagen debe tener como máximo 25 megapíxeles.")
            image.load()
            return image.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise HTTPException(status_code=422, detail="No se pudo decodificar una de las imágenes.") from error


def ranked_labels(probabilities: torch.Tensor, labels: list[str], threshold: float, limit: int = 5) -> list[dict]:
    indices = probabilities.argsort(descending=True)[:limit].tolist()
    return [
        {
            "valor": labels[index],
            "probabilidad": round(float(probabilities[index].item()), 6),
            "supera_umbral": bool(probabilities[index].item() >= threshold),
        }
        for index in indices
    ]


def describe_predictions(type_probs: torch.Tensor, color_probs: torch.Tensor,
                         style_probs: torch.Tensor, classes: dict, threshold: float) -> dict:
    type_index = int(type_probs.argmax().item())
    colors = ranked_labels(color_probs, classes["color"], threshold)
    styles = ranked_labels(style_probs, classes["estilo"], threshold)
    selected_colors = [item["valor"] for item in colors if item["supera_umbral"]]
    selected_styles = [item["valor"] for item in styles if item["supera_umbral"]]
    description = f"Tipo probable: {classes['tipo_prenda'][type_index]}"
    description += "; colores probables: " + (", ".join(selected_colors) if selected_colors else "sin color sobre el umbral")
    description += "; estilos probables: " + (", ".join(selected_styles) if selected_styles else "sin estilo sobre el umbral")
    return {
        "descripcion_mas_probable": description + ".",
        "tipo_prenda": {
            "valor": classes["tipo_prenda"][type_index],
            "probabilidad": round(float(type_probs[type_index].item()), 6),
        },
        "colores": colors,
        "estilos": styles,
    }


def combine_image_predictions(outputs: dict, saved_checkpoint: dict) -> dict:
    classes = saved_checkpoint["classes"]
    threshold = float(saved_checkpoint["multilabel_threshold"])
    type_probs = outputs["type"].softmax(dim=1)
    color_probs = outputs["color"].sigmoid()
    style_probs = outputs["style"].sigmoid()
    per_image = {
        "prenda": describe_predictions(type_probs[0], color_probs[0], style_probs[0], classes, threshold),
        "persona": describe_predictions(type_probs[1], color_probs[1], style_probs[1], classes, threshold),
    }
    combined = describe_predictions(
        type_probs.mean(dim=0), color_probs.mean(dim=0), style_probs.mean(dim=0), classes, threshold
    )
    return {
        "descripcion_mas_probable": combined["descripcion_mas_probable"],
        "prediccion_combinada": combined,
        "predicciones_por_imagen": per_image,
        "metodo_combinacion": "media_aritmetica_de_probabilidades",
        "umbral_multietiqueta": threshold,
    }


@app.get("/health")
def health():
    return {"status": "ok" if model is not None else "loading", "device": "cpu"}


@app.post("/v1/predict")
def predict_pair(garment_image: UploadFile = File(...), person_image: UploadFile = File(...)):
    if model is None or checkpoint is None or transform is None:
        raise HTTPException(status_code=503, detail="El modelo todavía no está disponible.")
    garment = decode_image(garment_image)
    person = decode_image(person_image)
    preprocessing_started = time.perf_counter()
    tensors = torch.stack([transform(garment), transform(person)])
    preprocessing_ms = (time.perf_counter() - preprocessing_started) * 1000
    inference_started = time.perf_counter()
    with INFERENCE_LOCK, torch.inference_mode():
        outputs = model(tensors)
    inference_ms = (time.perf_counter() - inference_started) * 1000
    result = combine_image_predictions(outputs, checkpoint)
    result.update({
        "device": "cpu",
        "latencia_ms": {
            "preprocesamiento_dos_imagenes": round(preprocessing_ms, 2),
            "inferencia_dos_imagenes": round(inference_ms, 2),
            "total_servidor": round(preprocessing_ms + inference_ms, 2),
        },
    })
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inference_api:app", host="0.0.0.0", port=8080, workers=1)