#!/usr/bin/env python3
import argparse
import json
import random
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import torch
import torch.nn as nn
import yaml
from PIL import Image, UnidentifiedImageError
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms


PROPERTY_CODES = ("tipo_prenda", "color", "estilo")


class MultiTaskMobileNet(nn.Module):
    def __init__(
        self,
        type_count: int,
        color_count: int,
        style_count: int,
        pretrained: bool = False,
    ) -> None:
        super().__init__()
        weights = models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
        self.backbone = models.mobilenet_v3_small(weights=weights)
        feature_count = self.backbone.classifier[0].in_features
        self.backbone.classifier = nn.Identity()
        self.type_head = nn.Linear(feature_count, type_count)
        self.color_head = nn.Linear(feature_count, color_count)
        self.style_head = nn.Linear(feature_count, style_count)

    def forward(self, images: torch.Tensor) -> dict[str, torch.Tensor]:
        features = self.backbone(images)
        return {
            "type": self.type_head(features),
            "color": self.color_head(features),
            "style": self.style_head(features),
        }


class GarmentImages(Dataset):
    def __init__(self, samples: list[dict], transform: transforms.Compose) -> None:
        self.samples = samples
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple:
        sample = self.samples[index]
        try:
            with Image.open(sample["path"]) as image:
                image_tensor = self.transform(image.convert("RGB"))
        except (OSError, UnidentifiedImageError) as error:
            raise RuntimeError(f"No se pudo leer la imagen {sample['path']}: {error}") from error

        return (
            image_tensor,
            sample["type_index"],
            torch.tensor(sample["color_target"], dtype=torch.float32),
            torch.tensor(sample["style_target"], dtype=torch.float32),
            sample["has_color_labels"],
            sample["has_style_labels"],
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Entrena MobileNetV3-Small desde metadata.sqlite.")
    parser.add_argument("--config", default="/app/configs/default.yaml")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), help="Sobrescribe el dispositivo.")
    parser.add_argument("--epochs", type=int, help="Sobrescribe la cantidad de épocas.")
    return parser.parse_args()


def load_config(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as stream:
            config = yaml.safe_load(stream)
    except OSError as error:
        raise RuntimeError(f"No se pudo leer la configuración {path}: {error}") from error
    if not isinstance(config, dict):
        raise ValueError(f"La configuración {path} debe ser un mapa YAML.")

    required = (
        "dataset_root", "database", "model_dir", "image_size", "batch_size",
        "epochs", "learning_rate", "num_workers", "pretrained",
        "unfreeze_last_block", "seed", "multilabel_threshold",
    )
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Faltan opciones en {path}: {', '.join(missing)}")
    for key in ("image_size", "batch_size", "epochs"):
        if not isinstance(config[key], int) or config[key] < 1:
            raise ValueError(f"{key} debe ser un entero positivo.")
    if config["num_workers"] < 0:
        raise ValueError("num_workers no puede ser negativo.")
    if not 0 < config["multilabel_threshold"] < 1:
        raise ValueError("multilabel_threshold debe estar entre 0 y 1.")
    return config


def read_catalog(connection: sqlite3.Connection, code: str) -> list[str]:
    row = connection.execute(
        "SELECT valores_permitidos FROM catalogo_propiedad WHERE codigo = ? AND activo = 1",
        (code,),
    ).fetchone()
    if row is None or row[0] is None:
        raise ValueError(f"El catálogo activo no define valores permitidos para {code}.")
    try:
        values = json.loads(row[0])
    except json.JSONDecodeError as error:
        raise ValueError(f"valores_permitidos para {code} no es JSON válido.") from error
    if not isinstance(values, list) or not values or any(not isinstance(value, str) for value in values):
        raise ValueError(f"valores_permitidos para {code} debe ser una lista no vacía de textos.")
    return values


def load_samples(database: Path, dataset_root: Path) -> tuple[dict, dict]:
    if not database.is_file():
        raise FileNotFoundError(f"No existe la base de datos del dataset: {database}")
    dataset_root = dataset_root.resolve()

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        garments = connection.execute(
            """
            SELECT id_prenda, codigo, split
            FROM prenda
            WHERE estado_revision = 'aprobado'
              AND apta_para_entrenamiento = 1
              AND split IN ('train', 'val', 'test')
            ORDER BY id_prenda
            """
        ).fetchall()
        if not garments:
            raise ValueError(
                "No hay prendas aprobadas y aptas para entrenamiento con split train/val/test."
            )
        eligible_garment_ids = {garment["id_prenda"] for garment in garments}

        labels_by_garment = defaultdict(lambda: defaultdict(list))
        rows = connection.execute(
            """
            SELECT v.id_prenda, c.codigo, v.valor
            FROM valor_propiedad_prenda AS v
            JOIN catalogo_propiedad AS c ON c.id_propiedad = v.id_propiedad
            WHERE c.activo = 1 AND c.codigo IN (?, ?, ?)
            """,
            PROPERTY_CODES,
        )
        for row in rows:
            labels_by_garment[row["id_prenda"]][row["codigo"]].append(row["valor"])

        images_by_garment = defaultdict(list)
        rows = connection.execute(
            """
            SELECT id_prenda, ruta_relativa
            FROM prenda_imagen
            WHERE es_fotografia_real = 1
            ORDER BY id_imagen
            """
        )
        for row in rows:
            if row["id_prenda"] not in eligible_garment_ids:
                continue
            relative_path = Path(row["ruta_relativa"])
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise ValueError(f"Ruta de imagen no permitida: {row['ruta_relativa']}")
            image_path = (dataset_root / relative_path).resolve()
            if not image_path.is_relative_to(dataset_root):
                raise ValueError(f"Ruta de imagen fuera de dataset/: {row['ruta_relativa']}")
            if not image_path.is_file():
                raise FileNotFoundError(f"No existe la imagen registrada: {image_path}")
            images_by_garment[row["id_prenda"]].append(image_path)

        color_classes = read_catalog(connection, "color")
        style_classes = read_catalog(connection, "estilo")

    type_classes = sorted({
        labels_by_garment[garment["id_prenda"]]["tipo_prenda"][0]
        for garment in garments
        if garment["split"] == "train"
        if len(labels_by_garment[garment["id_prenda"]]["tipo_prenda"]) == 1
    })
    if not type_classes:
        raise ValueError("No hay prendas train con exactamente una etiqueta tipo_prenda.")
    type_index = {value: index for index, value in enumerate(type_classes)}
    color_index = {value: index for index, value in enumerate(color_classes)}
    style_index = {value: index for index, value in enumerate(style_classes)}
    samples_by_split = {"train": [], "val": [], "test": []}

    for garment in garments:
        garment_id = garment["id_prenda"]
        labels = labels_by_garment[garment_id]
        garment_types = labels["tipo_prenda"]
        if len(garment_types) != 1:
            raise ValueError(
                f"La prenda {garment['codigo']} debe tener exactamente un tipo_prenda; "
                f"tiene {len(garment_types)}."
            )
        garment_type = garment_types[0]
        if garment_type not in type_index:
            raise ValueError(f"Tipo no válido para {garment['codigo']}: {garment_type}")

        colors = set(labels["color"])
        styles = set(labels["estilo"])
        unknown_colors = colors - color_index.keys()
        unknown_styles = styles - style_index.keys()
        if unknown_colors or unknown_styles:
            raise ValueError(
                f"Etiquetas fuera del catálogo en {garment['codigo']}: "
                f"colores={sorted(unknown_colors)}, estilos={sorted(unknown_styles)}"
            )
        image_paths = images_by_garment[garment_id]
        if not image_paths:
            raise ValueError(f"La prenda {garment['codigo']} no tiene fotografías reales registradas.")

        color_target = [float(value in colors) for value in color_classes]
        style_target = [float(value in styles) for value in style_classes]
        for image_path in image_paths:
            samples_by_split[garment["split"]].append({
                "path": image_path,
                "type_index": type_index[garment_type],
                "color_target": color_target,
                "style_target": style_target,
                "has_color_labels": bool(colors),
                "has_style_labels": bool(styles),
            })

    if not samples_by_split["train"]:
        raise ValueError("No hay fotografías de prendas aprobadas en split=train.")
    if not samples_by_split["val"]:
        raise ValueError("No hay fotografías de prendas aprobadas en split=val.")
    return samples_by_split, {
        "tipo_prenda": type_classes,
        "color": color_classes,
        "estilo": style_classes,
    }


def build_transform(image_size: int) -> transforms.Compose:
    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=(0.485, 0.456, 0.406),
            std=(0.229, 0.224, 0.225),
        ),
    ])


def move_batch(batch: tuple, device: torch.device) -> tuple:
    images, types, colors, styles, has_colors, has_styles = batch
    return (
        images.to(device),
        types.to(device),
        colors.to(device),
        styles.to(device),
        has_colors.to(device),
        has_styles.to(device),
    )


def compute_loss(outputs: dict, batch: tuple) -> torch.Tensor:
    _, type_targets, color_targets, style_targets, has_colors, has_styles = batch
    loss = nn.functional.cross_entropy(outputs["type"], type_targets)
    if has_colors.any():
        loss = loss + nn.functional.binary_cross_entropy_with_logits(
            outputs["color"][has_colors], color_targets[has_colors]
        )
    if has_styles.any():
        loss = loss + nn.functional.binary_cross_entropy_with_logits(
            outputs["style"][has_styles], style_targets[has_styles]
        )
    return loss


def update_multilabel_metrics(
    prediction: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    counters: dict,
    key: str,
    threshold: float,
) -> None:
    if not mask.any():
        return
    predicted = prediction[mask] >= threshold
    expected = target[mask] >= 0.5
    counters[key]["tp"] += int((predicted & expected).sum().item())
    counters[key]["fp"] += int((predicted & ~expected).sum().item())
    counters[key]["fn"] += int((~predicted & expected).sum().item())


def metric_values(counts: dict) -> dict:
    values = {}
    for key, stats in counts.items():
        tp, fp, fn = stats["tp"], stats["fp"], stats["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        values[key] = {
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall)
            if precision + recall else 0.0,
        }
    return values


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    threshold: float,
) -> dict:
    model.eval()
    total_loss = 0.0
    total = 0
    correct_types = 0
    multilabel_counts = {
        "color": {"tp": 0, "fp": 0, "fn": 0},
        "style": {"tp": 0, "fp": 0, "fn": 0},
    }
    with torch.no_grad():
        for raw_batch in loader:
            batch = move_batch(raw_batch, device)
            images, type_targets, color_targets, style_targets, has_colors, has_styles = batch
            outputs = model(images)
            batch_size = images.shape[0]
            total_loss += float(compute_loss(outputs, batch).item()) * batch_size
            total += batch_size
            correct_types += int((outputs["type"].argmax(dim=1) == type_targets).sum().item())
            update_multilabel_metrics(
                outputs["color"].sigmoid(),
                color_targets,
                has_colors,
                multilabel_counts,
                "color",
                threshold,
            )
            update_multilabel_metrics(
                outputs["style"].sigmoid(),
                style_targets,
                has_styles,
                multilabel_counts,
                "style",
                threshold,
            )
    if total == 0:
        raise ValueError("No hay datos para evaluar en validation.")
    return {
        "loss": total_loss / total,
        "type_accuracy": correct_types / total,
        **metric_values(multilabel_counts),
    }


def train_epoch(
    model: MultiTaskMobileNet,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    unfreeze_last_block: bool,
) -> float:
    model.train()
    if not unfreeze_last_block:
        model.backbone.features.eval()
    else:
        model.backbone.features.eval()
        model.backbone.features[-1].train()
    total_loss = 0.0
    total = 0
    for raw_batch in loader:
        batch = move_batch(raw_batch, device)
        optimizer.zero_grad(set_to_none=True)
        outputs = model(batch[0])
        loss = compute_loss(outputs, batch)
        loss.backward()
        optimizer.step()
        batch_size = batch[0].shape[0]
        total_loss += float(loss.item()) * batch_size
        total += batch_size
    if total == 0:
        raise ValueError("No hay datos para entrenar.")
    return total_loss / total


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    config = load_config(config_path)
    if args.epochs is not None:
        if args.epochs < 1:
            raise ValueError("--epochs debe ser positivo.")
        config["epochs"] = args.epochs

    random.seed(config["seed"])
    torch.manual_seed(config["seed"])
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config["seed"])

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Se solicitó CUDA, pero PyTorch no detecta una GPU disponible.")
    selected_device = args.device or "auto"
    if selected_device == "auto":
        selected_device = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(selected_device)

    dataset_root = Path(config["dataset_root"])
    database = Path(config["database"])
    samples_by_split, classes = load_samples(database, dataset_root)
    transform = build_transform(config["image_size"])
    generator = torch.Generator().manual_seed(config["seed"])
    train_loader = DataLoader(
        GarmentImages(samples_by_split["train"], transform),
        batch_size=config["batch_size"],
        shuffle=True,
        num_workers=config["num_workers"],
        generator=generator,
    )
    validation_loader = DataLoader(
        GarmentImages(samples_by_split["val"], transform),
        batch_size=config["batch_size"],
        shuffle=False,
        num_workers=config["num_workers"],
    )

    model = MultiTaskMobileNet(
        type_count=len(classes["tipo_prenda"]),
        color_count=len(classes["color"]),
        style_count=len(classes["estilo"]),
        pretrained=config["pretrained"],
    )
    for parameter in model.backbone.features.parameters():
        parameter.requires_grad = False
    if config["unfreeze_last_block"]:
        for parameter in model.backbone.features[-1].parameters():
            parameter.requires_grad = True
    model.to(device)
    optimizer = torch.optim.Adam(
        (parameter for parameter in model.parameters() if parameter.requires_grad),
        lr=config["learning_rate"],
    )

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(config["model_dir"]) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    history = []
    best_loss = float("inf")
    print(
        f"Dispositivo: {device}; imágenes train={len(samples_by_split['train'])}, "
        f"val={len(samples_by_split['val'])}; clases tipo={len(classes['tipo_prenda'])}",
        flush=True,
    )

    for epoch in range(1, config["epochs"] + 1):
        train_loss = train_epoch(
            model, train_loader, optimizer, device, config["unfreeze_last_block"]
        )
        validation = evaluate(
            model,
            validation_loader,
            device,
            config["multilabel_threshold"],
        )
        metrics = {"epoch": epoch, "train_loss": train_loss, "validation": validation}
        history.append(metrics)
        print(json.dumps(metrics, ensure_ascii=False), flush=True)
        if validation["loss"] < best_loss:
            best_loss = validation["loss"]
            torch.save({
                "state_dict": model.state_dict(),
                "classes": classes,
                "image_size": config["image_size"],
                "architecture": "mobilenet_v3_small",
                "multilabel_threshold": config["multilabel_threshold"],
                "epoch": epoch,
                "validation": validation,
            }, run_dir / "best.pt")
        (run_dir / "metrics.json").write_text(
            json.dumps(history, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(f"Mejor checkpoint: {run_dir / 'best.pt'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError, sqlite3.Error) as error:
        print(f"Error de entrenamiento: {error}", file=sys.stderr)
        raise SystemExit(1) from error
