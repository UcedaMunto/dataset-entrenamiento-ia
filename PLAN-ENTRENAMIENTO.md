# Plan de entrenamiento (MobileNetV3-Small, V2)

> **Plan histórico.** Las mediciones y problemas descritos corresponden a la planificación inicial; no representan el estado actual. Consulta el [README vigente](README.md) y la [validación del 23-10-2026](docs/VALIDACION.md).

Documento de planificación. No ejecuta nada. Basado en `README.md`, `RESUMEN-METODO-ENTRENAMIENTO.md`, `utilidades-entrenamiento/README.md`, `documentacion_dataset/README.md` y el estado real de este equipo (`osanode-node4`).

## 1. Hardware detectado

| Recurso | Valor |
|---|---|
| CPU | Intel Core i7-8750H, 6 núcleos / 12 hilos |
| RAM | 15 GiB (≈11 GiB disponibles), swap 4 GiB |
| GPU | NVIDIA GeForce RTX 2060 Mobile (TU106M, 6 GB VRAM, Turing, CC 7.5) + Intel UHD 630 (integrada, no sirve para CUDA) |
| Disco | 98 GB totales, 77 GB libres |
| Docker | 29.1.3 + Compose 2.40.3 (paquetes `docker.io`, `docker-compose-v2`) |
| Driver NVIDIA | **No instalado** (no existe `nvidia-smi` ni `/proc/driver/nvidia`) |
| NVIDIA Container Toolkit | **No instalado** |
| Python en host | Sin `torch` (correcto: todo irá en contenedor) |

Consecuencia: hoy solo funciona el perfil CPU. La RTX 2060 (6 GB) es suficiente para MobileNetV3-Small a 224 px con batch 32-64, muy por encima de los 2-4 GB que asume el README; hay que instalar driver y toolkit para aprovecharla.

## 2. Estado de los datos (`dataset/metadata.sqlite`)

- 24 177 prendas, 24 177 imágenes (1 imagen por prenda).
- Aprobadas: train 11 496, val 1 398, test 1 407 (**14 301 utilizables**). Pendientes: 1 118. Rechazadas: 8 758.
- Carpetas: faldas, pantalones, shorts, vestido, abrigos, blusas, camisas, chaquetas, sueteres (8 276 imágenes en blusas, desbalance notable).
- Existe respaldo `metadata.respaldo-20261017-1628.sqlite`.

Consecuencia: el dataset es suficiente para entrenar tipo de prenda; color y estilo dependen de cuántas aprobadas tengan etiqueta (verificar, ver fase 0).

## 3. Arreglo del error de Docker (permisos del socket)

Causa: el usuario `ubuntu` está en el grupo `docker` en `/etc/group`, pero la sesión actual se abrió antes y no lo tiene (`id` no lista `docker`). Verificado: `sg docker -c "docker ps"` funciona.

Solución (una de las dos, no requiere sudo):

```bash
newgrp docker          # abre una shell con el grupo; sirve en esa terminal
# o cerrar sesión y volver a entrar / reiniciar la sesión de VS Code
```

Después, `docker compose up` / `docker compose run --rm train status` funcionan sin `sudo`. No usar `chmod 666 /var/run/docker.sock` ni `sudo docker` como solución permanente.

Nota: `docker compose up` sin servicio arranca `train` con el comando por defecto (entrena). Para solo construir/consultar usar `docker compose build` y `docker compose run --rm train status`.

## 4. Problemas detectados en la infraestructura actual (a corregir al implementar)

1. `docker-compose.yaml`: `build.network: none` y `Dockerfile` con `pip install --no-index` fallarán, porque la imagen base `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` no incluye `Pillow` ni `PyYAML` y no hay red en el build. Cambiar a build con red (o vendorizar wheels en `wheels/` y usar `--find-links`).
2. La imagen base no está descargada localmente (~3-4 GB); el primer `build` la bajará.
3. Los pesos preentrenados de MobileNetV3-Small se descargan en tiempo de ejecución a `modelo-ia/cache`. Para portabilidad/offline, pre-descargarlos y guardarlos en el volumen (o hornearlos en la imagen).
4. `num_workers: 0` y `batch_size: 2` en `configs/default.yaml` están pensados para 2 GB de VRAM; con 6 GB y 12 hilos son un cuello de botella.
5. Dataset montado `:ro` con rutas relativas: correcto y portable; mantenerlo.
6. Sin `shm_size`: con `num_workers > 0` PyTorch necesita `shm_size` (p. ej. `2g`) o `ipc: host`.
7. Hay un directorio `modelo-general-destilacion/docker-compose.yaml/` (carpeta con ese nombre) junto a `compose.yml`; revisar para evitar confusión.
8. El dashboard de curación está en ejecución y consume RAM/CPU; considerar detenerlo durante el entrenamiento.

## 5. Plan por fases

### Fase 0 – Preparación del equipo
1. Activar el grupo `docker` en la sesión (sección 3).
2. Instalar driver NVIDIA propietario recomendado (`ubuntu-drivers devices` → `sudo ubuntu-drivers install`) y reiniciar. Debe ser compatible con CUDA 12.4 (driver ≥ 550).
3. Instalar `nvidia-container-toolkit`, ejecutar `sudo nvidia-ctk runtime configure --runtime=docker` y reiniciar Docker.
4. Validar: `docker run --rm --gpus all pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime nvidia-smi`.
5. Liberar recursos: detener el contenedor `modelo-general-destilacion-dashboard` si no se usa.

### Fase 1 – Auditoría de datos (sin entrenar)
1. Contar por clase de `tipo_prenda` en train/val/test solo con `estado_revision='aprobado'`.
2. Contar cuántas aprobadas tienen etiquetas de `color` y `estilo`; decidir si se entrenan esas cabezas o solo tipo en la primera corrida.
3. Verificar que todas las rutas de `prenda_imagen` existan y abran con Pillow.
4. Revisar duplicados entre splits (fuga de datos) con el pipeline de duplicados existente.
5. Decidir manejo de desbalance (blusas 8 276 vs. ~1 300-1 500 del resto): `pos_weight`/pesos por clase o muestreo balanceado.
6. Confirmar licencias/permisos de las fuentes antes de cualquier publicación del modelo.

### Fase 2 – Contenerización portable
Objetivo: todo el entrenamiento se mueve a otro equipo copiando carpeta + `docker compose up`.
1. Un solo `Dockerfile` con dependencias fijadas (`torch/torchvision` de la imagen base, `Pillow`, `PyYAML`, más `scikit-learn`/`numpy` si se agregan métricas).
2. Perfiles Compose: `train` (CPU) y `train-gpu` (GPU); variables en `.env` (`TRAINING_UID`, `TRAINING_GID`, `CUDA_VISIBLE_DEVICES`, imagen, tamaño, batch).
3. Volúmenes: `../dataset` solo lectura; `./modelo-ia` para runs/caché; nada fuera de la carpeta del proyecto, sin rutas absolutas del host.
4. Empaquetado de migración: `docker save` de la imagen o build reproducible desde Dockerfile; copiar `dataset/` y `metadata.sqlite` (con hash SHA-256 para verificar integridad).
5. Script `status` ampliado: versión de PyTorch, GPU, VRAM, hash de la base y conteos por split.
6. Healthcheck de entorno antes de entrenar (GPU visible, SQLite legible, imágenes accesibles).

### Fase 3 – Prueba de humo
1. `status` en CPU y en GPU.
2. 1 época con un subconjunto (p. ej. 500 imágenes) para validar el pipeline, la pérdida y la escritura de checkpoints.
3. Medir tiempo por iteración, uso de VRAM (`nvidia-smi`) y RAM.

### Fase 4 – Entrenamiento por etapas (GPU RTX 2060, 6 GB)

| Experimento | Configuración inicial | Objetivo |
|---|---|---|
| E1 línea base | base congelada, 160 px, batch 64, lr 1e-3, 10-15 épocas, `num_workers` 6-8, AMP (mixed precision) | validar cabezas, obtener base de comparación |
| E2 resolución | base congelada, 224 px, batch 32-64 | medir ganancia por resolución |
| E3 ajuste fino | descongelar último bloque, lr 1e-4 (cabezas 1e-3), 224 px | mejora esperada en tipo/color |
| E4 mejor config + semillas | repetir mejor config con 3 semillas | estimar varianza |

Reglas comunes: semilla fija, aumento de datos ligero solo en train (flip horizontal, recorte aleatorio, variación de brillo; evitar cambios de tono que alteren el color), `ReduceLROnPlateau` o coseno, early stopping por métrica de val, guardado de `best.pt` y `last.pt`, registro de configuración, hash de dataset, GPU, VRAM máxima y duración en cada run (`modelo-ia/runs/<fecha>-<exp>/`).

Estimación de memoria: MobileNetV3-Small a 224 px con batch 64 y AMP cabe holgadamente en 6 GB; escalar batch hasta ≈70 % de VRAM. Validar empíricamente.

### Fase 5 – Evaluación
1. Selección de hiperparámetros y umbrales de color/estilo solo en `val`.
2. Medir **una sola vez** en `test` con el mejor modelo.
3. Métricas: accuracy y matriz de confusión por tipo; precision/recall/F1 por clase para color y estilo; errores más frecuentes (faldas/shorts, camisas/blusas).
4. Prueba de inferencia multi-vista (`predict.py`) y de tiempo en CPU.
5. Guardar informe en `modelo-ia/runs/<run>/metrics.json` y resumen en Markdown.

### Fase 6 – Cierre y migración
1. Congelar versión: copia de SQLite, listado de hashes, `configs/` usado, imagen Docker etiquetada (`modelo-reconocimiento-entrenamiento:v2-<fecha>`).
2. Exportar el mejor checkpoint (opcional ONNX/TorchScript) para integración con OpenStack/Kubernetes.
3. Verificar en un equipo limpio: `git clone`/copia + instalar Docker (+ NVIDIA toolkit si hay GPU) + `docker compose --profile gpu run --rm train-gpu status`.

## 6. Riesgos

- Calidad de etiquetas generadas por IA (mayor riesgo): muestrear aprobadas y medir error.
- Sesgo de fuentes y fondos distintos al uso real.
- Desbalance de clases (blusas dominan).
- Driver/toolkit incompatibles: fallback CPU (más lento; 12 hilos pero sin aceleración).
- Etiquetas de color/estilo ausentes tratadas como "no anotadas" (ya implementado): puede dejar cabezas con pocas muestras.
- Espacio en disco: 77 GB libres bastan; cada run ocupa pocos MB.

## 7. Criterios de aceptación

- `docker compose --profile gpu run --rm train-gpu status` muestra RTX 2060 y CUDA disponible.
- Entrenamiento reproducible (misma semilla y dataset ⇒ métricas equivalentes).
- Métricas por tipo, color y estilo registradas sobre `test` no usado en entrenamiento.
- Todo el stack se levanta en otro equipo solo con Docker, el dataset y este directorio.

## 8. Decisiones pendientes

1. ¿Entrenar primero solo `tipo_prenda` o las tres cabezas?
2. ¿Aprobar más de las 1 118 pendientes antes de congelar el dataset?
3. ¿Se acepta instalar driver NVIDIA y toolkit (requieren `sudo` y reinicio)?
4. ¿Resolución objetivo final (160 vs 224 px)?
