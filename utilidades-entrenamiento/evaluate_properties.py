#!/usr/bin/env python3
"""Evaluate a trained garment classifier on a fixed dataset split."""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from train import GarmentImages, MultiTaskMobileNet, build_transform, load_samples


def percentage(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 2) if denominator else 0.0


def f1_score(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def macro_property_average(type_accuracy: float, color_jaccard: float,
                           style_jaccard: float) -> dict:
    components = {
        "tipo_prenda_pct": type_accuracy,
        "color_jaccard_pct": color_jaccard,
        "estilo_jaccard_pct": style_jaccard,
    }
    return {
        "metodo": "media_aritmetica_no_ponderada_de_las_tres_propiedades",
        "componentes_pct": components,
        "porcentaje": round(sum(components.values()) / len(components), 2),
    }


def summarize_multilabel(predicted, expected, labels: list[str]) -> dict:
    exact = int((predicted == expected).all(dim=1).sum().item())
    intersection = (predicted & expected).sum(dim=1)
    union = (predicted | expected).sum(dim=1)
    per_image_jaccard = torch.where(
        union > 0,
        intersection.float() / union.clamp(min=1),
        torch.ones_like(union, dtype=torch.float32),
    )
    counts = []
    for index, label in enumerate(labels):
        pred = predicted[:, index]
        real = expected[:, index]
        tp = int((pred & real).sum().item())
        fp = int((pred & ~real).sum().item())
        fn = int((~pred & real).sum().item())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        counts.append({
            "valor": label,
            "soporte": tp + fn,
            "precision_pct": percentage(tp, tp + fp),
            "recall_pct": percentage(tp, tp + fn),
            "f1_pct": round(100 * f1_score(precision, recall), 2),
        })

    total_tp = sum(int((predicted[:, i] & expected[:, i]).sum().item()) for i in range(len(labels)))
    total_fp = sum(int((predicted[:, i] & ~expected[:, i]).sum().item()) for i in range(len(labels)))
    total_fn = sum(int((~predicted[:, i] & expected[:, i]).sum().item()) for i in range(len(labels)))
    micro_precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0.0
    return {
        "coincidencia_exacta": {
            "correctas": exact,
            "total": len(expected),
            "porcentaje": percentage(exact, len(expected)),
        },
        "coincidencia_parcial_jaccard_pct": round(100 * float(per_image_jaccard.mean().item()), 2)
        if len(expected) else 0.0,
        "micro_precision_pct": percentage(total_tp, total_tp + total_fp),
        "micro_recall_pct": percentage(total_tp, total_tp + total_fn),
        "micro_f1_pct": round(100 * f1_score(micro_precision, micro_recall), 2),
        "por_etiqueta": counts,
    }


def summarize_types(confusion: torch.Tensor, labels: list[str]) -> dict:
    total = int(confusion.sum().item())
    correct = int(confusion.diag().sum().item())
    per_label = []
    for index, label in enumerate(labels):
        tp = int(confusion[index, index].item())
        support = int(confusion[index].sum().item())
        predicted = int(confusion[:, index].sum().item())
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else 0.0
        per_label.append({
            "valor": label,
            "soporte": support,
            "precision_pct": percentage(tp, predicted),
            "recall_pct": percentage(tp, support),
            "f1_pct": round(100 * f1_score(precision, recall), 2),
        })
    return {
        "correctas": correct,
        "total": total,
        "accuracy_pct": percentage(correct, total),
        "por_tipo": per_label,
        "matriz_confusion": confusion.tolist(),
    }


def evaluate(checkpoint_path: Path, database: Path, dataset_root: Path,
             split: str, device_name: str, batch_size: int, num_workers: int) -> dict:
    device = torch.device(device_name)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    classes = checkpoint["classes"]
    model = MultiTaskMobileNet(
        type_count=len(classes["tipo_prenda"]),
        color_count=len(classes["color"]),
        style_count=len(classes["estilo"]),
        pretrained=False,
    )
    model.load_state_dict(checkpoint["state_dict"])
    model.to(device).eval()

    samples_by_split, catalog = load_samples(database, dataset_root)
    samples = samples_by_split[split]
    if not samples:
        raise ValueError(f"El split {split} no tiene muestras elegibles.")
    type_map = [classes["tipo_prenda"].index(label) if label in classes["tipo_prenda"] else -1
                for label in catalog["tipo_prenda"]]
    color_columns = [catalog["color"].index(label) for label in classes["color"]]
    style_columns = [catalog["estilo"].index(label) for label in classes["estilo"]]
    loader = DataLoader(
        GarmentImages(samples, build_transform(checkpoint["image_size"])),
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
    )

    type_confusion = torch.zeros((len(classes["tipo_prenda"]),) * 2, dtype=torch.int64)
    color_predictions, color_targets = [], []
    style_predictions, style_targets = [], []
    threshold = float(checkpoint["multilabel_threshold"])

    with torch.inference_mode():
        for batch in loader:
            images, types, colors, styles, has_colors, has_styles = batch
            outputs = model(images.to(device))
            predicted_types = outputs["type"].argmax(dim=1).cpu()
            for actual, predicted in zip(types.tolist(), predicted_types.tolist()):
                actual_class = type_map[actual]
                if actual_class >= 0:
                    type_confusion[actual_class, predicted] += 1
            if has_colors.any():
                mask = has_colors.bool()
                color_predictions.append(outputs["color"].sigmoid()[mask.to(device)].cpu() >= threshold)
                color_targets.append(colors[mask][:, color_columns] >= 0.5)
            if has_styles.any():
                mask = has_styles.bool()
                style_predictions.append(outputs["style"].sigmoid()[mask.to(device)].cpu() >= threshold)
                style_targets.append(styles[mask][:, style_columns] >= 0.5)

    def concatenate(parts, width):
        return torch.cat(parts) if parts else torch.zeros((0, width), dtype=torch.bool)

    color_pred = concatenate(color_predictions, len(classes["color"]))
    color_real = concatenate(color_targets, len(classes["color"]))
    style_pred = concatenate(style_predictions, len(classes["estilo"]))
    style_real = concatenate(style_targets, len(classes["estilo"]))
    type_summary = summarize_types(type_confusion, classes["tipo_prenda"])
    color_summary = summarize_multilabel(color_pred, color_real, classes["color"])
    style_summary = summarize_multilabel(style_pred, style_real, classes["estilo"])
    return {
        "generado": datetime.now().astimezone().isoformat(timespec="seconds"),
        "checkpoint": str(checkpoint_path),
        "epoca_checkpoint": checkpoint.get("epoch"),
        "split": split,
        "device": str(device),
        "imagenes_evaluadas": len(samples),
        "umbral_multietiqueta": threshold,
        "sha256_metadata_sqlite": hashlib.sha256(database.read_bytes()).hexdigest(),
        "promedio_macro_propiedades": macro_property_average(
            type_summary["accuracy_pct"],
            color_summary["coincidencia_parcial_jaccard_pct"],
            style_summary["coincidencia_parcial_jaccard_pct"],
        ),
        "tipo_prenda": type_summary,
        "color": color_summary,
        "estilo": style_summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mide el rendimiento por propiedad en train, val o test sin entrenar."
    )
    parser.add_argument("--checkpoint", required=True, type=Path, help="Ruta a best.pt.")
    parser.add_argument("--database", type=Path, default=Path("/app/dataset/metadata.sqlite"))
    parser.add_argument("--dataset-root", type=Path, default=Path("/app/dataset"))
    parser.add_argument("--split", choices=("test", "val", "train"), default="test")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--output", type=Path, help="Ruta opcional para guardar el informe JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.checkpoint.is_file():
        raise FileNotFoundError(f"No existe el checkpoint: {args.checkpoint}")
    if args.batch_size < 1 or args.num_workers < 0:
        raise ValueError("batch-size debe ser positivo y num-workers no puede ser negativo.")
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA fue solicitado, pero PyTorch no detecta una GPU disponible.")
    result = evaluate(
        args.checkpoint, args.database, args.dataset_root, args.split,
        device, args.batch_size, args.num_workers,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Informe guardado en: {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError, KeyError) as error:
        raise SystemExit(f"Error de evaluación: {error}") from error