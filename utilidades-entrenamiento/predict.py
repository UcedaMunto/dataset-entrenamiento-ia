#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

import torch
from PIL import Image, UnidentifiedImageError
from torchvision import transforms

from train import MultiTaskMobileNet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predice tipo, color y estilo de una prenda.")
    parser.add_argument("--checkpoint", required=True, help="Ruta al checkpoint best.pt.")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--threshold", type=float, help="Umbral para colores y estilos.")
    parser.add_argument("images", nargs="+", help="Una o varias vistas de la misma prenda.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Se solicitó CUDA, pero PyTorch no detecta una GPU disponible.")
    device_name = args.device
    if device_name == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_name)

    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    classes = checkpoint["classes"]
    model = MultiTaskMobileNet(
        type_count=len(classes["tipo_prenda"]),
        color_count=len(classes["color"]),
        style_count=len(classes["estilo"]),
        pretrained=False,
    )
    model.load_state_dict(checkpoint["state_dict"])
    model.to(device).eval()

    transform = transforms.Compose([
        transforms.Resize((checkpoint["image_size"], checkpoint["image_size"])),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=(0.485, 0.456, 0.406),
            std=(0.229, 0.224, 0.225),
        ),
    ])
    image_tensors = []
    for image_arg in args.images:
        image_path = Path(image_arg)
        if not image_path.is_file():
            raise FileNotFoundError(f"No existe la imagen: {image_path}")
        try:
            with Image.open(image_path) as image:
                image_tensors.append(transform(image.convert("RGB")))
        except (OSError, UnidentifiedImageError) as error:
            raise RuntimeError(f"No se pudo leer la imagen {image_path}: {error}") from error

    with torch.no_grad():
        outputs = model(torch.stack(image_tensors).to(device))
        type_probabilities = outputs["type"].softmax(dim=1).mean(dim=0)
        color_probabilities = outputs["color"].sigmoid().mean(dim=0)
        style_probabilities = outputs["style"].sigmoid().mean(dim=0)
    threshold = args.threshold
    if threshold is None:
        threshold = checkpoint["multilabel_threshold"]
    if not 0 < threshold < 1:
        raise ValueError("El umbral debe estar entre 0 y 1.")
    type_index = int(type_probabilities.argmax().item())
    result = {
        "tipo_prenda": {
            "valor": classes["tipo_prenda"][type_index],
            "probabilidad": float(type_probabilities[type_index].item()),
        },
        "colores": [
            {"valor": label, "probabilidad": float(color_probabilities[index].item())}
            for index, label in enumerate(classes["color"])
            if color_probabilities[index] >= threshold
        ],
        "estilos": [
            {"valor": label, "probabilidad": float(style_probabilities[index].item())}
            for index, label in enumerate(classes["estilo"])
            if style_probabilities[index] >= threshold
        ],
        "imagenes": [str(Path(image).resolve()) for image in args.images],
        "umbral_multietiqueta": threshold,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError, KeyError) as error:
        print(f"Error de predicción: {error}", file=sys.stderr)
        raise SystemExit(1) from error
