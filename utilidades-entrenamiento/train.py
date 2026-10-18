#!/usr/bin/env python3
import argparse
import hashlib
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
        "seed", "multilabel_threshold",
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
                "codigo": garment["codigo"],
                "ruta_relativa": image_path.relative_to(dataset_root).as_posix(),
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


def build_transform(image_size: int, augment: bool = False) -> transforms.Compose:
    if augment:
        steps = [
            transforms.RandomResizedCrop(image_size, scale=(0.7, 1.0), ratio=(0.85, 1.15)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
        ]
    else:
        steps = [transforms.Resize((image_size, image_size))]
    return transforms.Compose([
        *steps,
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


def compute_loss(
    outputs: dict,
    batch: tuple,
    type_weights: torch.Tensor | None = None,
    label_smoothing: float = 0.0,
) -> torch.Tensor:
    _, type_targets, color_targets, style_targets, has_colors, has_styles = batch
    loss = nn.functional.cross_entropy(
        outputs["type"], type_targets, weight=type_weights, label_smoothing=label_smoothing
    )
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


def set_backbone_trainable(model: MultiTaskMobileNet, trainable: bool) -> None:
    for parameter in model.backbone.parameters():
        parameter.requires_grad = trainable


def train_epoch(
    model: MultiTaskMobileNet,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    scaler: torch.amp.GradScaler,
    backbone_trainable: bool,
    type_weights: torch.Tensor | None,
    label_smoothing: float,
    progress_path: Path,
    epoch: int,
) -> float:
    model.train()
    if not backbone_trainable:
        model.backbone.features.eval()
    total_loss = 0.0
    total = 0
    for step, raw_batch in enumerate(loader, 1):
        batch = move_batch(raw_batch, device)
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, enabled=scaler.is_enabled()):
            outputs = model(batch[0])
            loss = compute_loss(outputs, batch, type_weights, label_smoothing)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        batch_size = batch[0].shape[0]
        total_loss += float(loss.item()) * batch_size
        total += batch_size
        if step % 20 == 0 or step == len(loader):
            progress_path.write_text(json.dumps({
                "epoch": epoch, "batch": step, "batches": len(loader),
                "loss": total_loss / total, "updated": datetime.now().isoformat(timespec="seconds"),
            }), encoding="utf-8")
    if total == 0:
        raise ValueError("No hay datos para entrenar.")
    return total_loss / total


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def register_run(
    ledger_path: Path, run_id: str, config: dict, samples_by_split: dict, database: Path
) -> None:
    """Registra en un SQLite aparte qué imágenes entran en cada ejecución."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(ledger_path) as ledger:
        ledger.executescript(
            """
            CREATE TABLE IF NOT EXISTS ejecucion (
                run_id TEXT PRIMARY KEY,
                fecha TEXT NOT NULL,
                config_json TEXT NOT NULL,
                sha256_metadata TEXT NOT NULL,
                mejor_checkpoint TEXT
            );
            CREATE TABLE IF NOT EXISTS imagen_entrenamiento (
                run_id TEXT NOT NULL REFERENCES ejecucion(run_id),
                split TEXT NOT NULL CHECK (split IN ('train', 'val', 'test')),
                codigo TEXT NOT NULL,
                ruta_relativa TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                PRIMARY KEY (run_id, ruta_relativa)
            );
            CREATE INDEX IF NOT EXISTS idx_imagen_sha ON imagen_entrenamiento(sha256);
            """
        )
        previous = {row[0] for row in ledger.execute("SELECT DISTINCT sha256 FROM imagen_entrenamiento")}
        ledger.execute(
            "INSERT INTO ejecucion (run_id, fecha, config_json, sha256_metadata) VALUES (?, ?, ?, ?)",
            (run_id, datetime.now().isoformat(timespec="seconds"),
             json.dumps(config, ensure_ascii=False, default=str), file_sha256(database)),
        )
        rows = [
            (run_id, split, sample["codigo"], sample["ruta_relativa"], file_sha256(sample["path"]))
            for split, samples in samples_by_split.items()
            for sample in samples
        ]
        ledger.executemany("INSERT INTO imagen_entrenamiento VALUES (?, ?, ?, ?, ?)", rows)
    new = sum(1 for row in rows if row[4] not in previous)
    print(f"Registro: {len(rows)} imágenes en {run_id}; nuevas respecto a ejecuciones previas: {new}", flush=True)


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
    use_cuda = device.type == "cuda"
    eval_transform = build_transform(config["image_size"])
    train_transform = build_transform(config["image_size"], config.get("augment", True))
    generator = torch.Generator().manual_seed(config["seed"])
    loader_options = {
        "batch_size": config["batch_size"],
        "num_workers": config["num_workers"],
        "pin_memory": use_cuda,
        "persistent_workers": config["num_workers"] > 0,
    }
    train_loader = DataLoader(
        GarmentImages(samples_by_split["train"], train_transform),
        shuffle=True, generator=generator, drop_last=True, **loader_options,
    )
    validation_loader = DataLoader(
        GarmentImages(samples_by_split["val"], eval_transform), shuffle=False, **loader_options
    )
    test_loader = DataLoader(
        GarmentImages(samples_by_split["test"], eval_transform), shuffle=False, **loader_options
    ) if samples_by_split["test"] else None

    type_weights = None
    if config.get("class_weighted", True):
        counts = torch.zeros(len(classes["tipo_prenda"]))
        for sample in samples_by_split["train"]:
            counts[sample["type_index"]] += 1
        type_weights = (counts.sum() / (len(counts) * counts.clamp(min=1))).sqrt().to(device)
    label_smoothing = float(config.get("label_smoothing", 0.05))

    model = MultiTaskMobileNet(
        type_count=len(classes["tipo_prenda"]),
        color_count=len(classes["color"]),
        style_count=len(classes["estilo"]),
        pretrained=config["pretrained"],
    )
    model.to(device)

    # Fase 1: solo cabezas; fase 2: ajuste fino de toda la base con lr menor.
    warmup_epochs = min(int(config.get("warmup_epochs", 0)), config["epochs"])
    finetune = bool(config.get("finetune", False))
    head_params = [
        p for m in (model.type_head, model.color_head, model.style_head) for p in m.parameters()
    ]
    set_backbone_trainable(model, finetune and warmup_epochs == 0)
    optimizer = torch.optim.AdamW(
        [
            {"params": head_params, "lr": config["learning_rate"]},
            {"params": model.backbone.parameters(), "lr": config.get("finetune_lr", 1e-4)},
        ],
        weight_decay=config.get("weight_decay", 1e-4),
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=config["epochs"])
    scaler = torch.amp.GradScaler(enabled=use_cuda and config.get("amp", True))

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(config["model_dir"]) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    history = []
    best_loss = float("inf")
    stale = 0
    patience = int(config.get("early_stopping_patience", 5))
    ledger_path = Path(config.get("ledger", "/app/modelo-ia/registro_entrenamiento.sqlite"))
    register_run(ledger_path, run_id, config, samples_by_split, database)
    print(
        f"Dispositivo: {device}; imágenes train={len(samples_by_split['train'])}, "
        f"val={len(samples_by_split['val'])}, test={len(samples_by_split['test'])}; "
        f"clases tipo={len(classes['tipo_prenda'])}",
        flush=True,
    )

    for epoch in range(1, config["epochs"] + 1):
        if finetune and epoch == warmup_epochs + 1:
            set_backbone_trainable(model, True)
        train_loss = train_epoch(
            model, train_loader, optimizer, device, scaler,
            finetune and epoch > warmup_epochs, type_weights, label_smoothing,
            run_dir / "progress.json", epoch,
        )
        scheduler.step()
        validation = evaluate(model, validation_loader, device, config["multilabel_threshold"])
        metrics = {"epoch": epoch, "train_loss": train_loss, "validation": validation}
        history.append(metrics)
        print(json.dumps(metrics, ensure_ascii=False), flush=True)
        if validation["loss"] < best_loss:
            best_loss = validation["loss"]
            stale = 0
            torch.save({
                "state_dict": model.state_dict(),
                "classes": classes,
                "image_size": config["image_size"],
                "architecture": "mobilenet_v3_small",
                "multilabel_threshold": config["multilabel_threshold"],
                "epoch": epoch,
                "validation": validation,
            }, run_dir / "best.pt")
        else:
            stale += 1
        (run_dir / "metrics.json").write_text(
            json.dumps(history, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if epoch > warmup_epochs and stale >= patience:
            print(f"Parada temprana en la época {epoch}.", flush=True)
            break

    if test_loader is not None:
        model.load_state_dict(torch.load(run_dir / "best.pt", map_location=device)["state_dict"])
        test_metrics = evaluate(model, test_loader, device, config["multilabel_threshold"])
        (run_dir / "test_metrics.json").write_text(
            json.dumps(test_metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps({"test": test_metrics}, ensure_ascii=False), flush=True)

    with sqlite3.connect(ledger_path) as ledger:
        ledger.execute(
            "UPDATE ejecucion SET mejor_checkpoint = ? WHERE run_id = ?",
            (str(run_dir / "best.pt"), run_id),
        )
    (run_dir / "progress.json").write_text(
        json.dumps({"finished": True, "updated": datetime.now().isoformat(timespec="seconds")}),
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
