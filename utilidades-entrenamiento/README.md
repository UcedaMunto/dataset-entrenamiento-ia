# Utilidades de entrenamiento

Este directorio contiene el entorno Docker Compose y los scripts para el MVP MobileNetV3-Small. El dataset y sus tablas SQLite permanecen en `../dataset/`; los checkpoints y la caché de pesos preentrenados se escriben en `modelo-ia/`. Los repositorios auxiliares descargados, si fueran necesarios, se pueden colocar en `repositorios/`; no se versionan automáticamente.

## Requisitos

- Docker Engine y Docker Compose v2.
- Acceso a Internet para descargar la imagen base de PyTorch y, desde el contenedor, los pesos preentrenados de MobileNetV3-Small.
- Para GPU NVIDIA: driver del host compatible con CUDA 12.4 y NVIDIA Container Toolkit. Si no hay GPU compatible, usar el servicio CPU.
- El usuario de Compose por defecto es UID/GID `1000`; para que los artefactos pertenezcan al usuario local, configura `TRAINING_UID` y `TRAINING_GID` en el entorno antes de invocar Compose si tu laptop usa otros identificadores.

## Construir y consultar el entorno

Desde esta carpeta:

```bash
docker compose build
docker compose run --rm train status
```

`status` indica versión de PyTorch y si el contenedor detecta CUDA. El servicio predeterminado `train` no solicita GPU y es adecuado para CPU.

La imagen de entrenamiento instala sus dependencias sin red; los pesos preentrenados sí se descargan al iniciar el primer entrenamiento. Si Docker avisa que el reenvío IPv4 está deshabilitado, el estado puede funcionar pero la descarga de pesos fallará hasta corregir la conectividad del daemon.

## Entrenar

El entrenamiento requiere imágenes y registros válidos en `../dataset/metadata.sqlite`: prendas aprobadas y aptas, con split `train` o `val`, una etiqueta `tipo_prenda`, fotografías reales registradas y las etiquetas dentro del catálogo. Las vistas de cada prenda conservan juntas su partición. No se utiliza el split `test` para seleccionar el checkpoint.

```bash
docker compose run --rm train
```

Para usar una GPU NVIDIA local:

```bash
docker compose --profile gpu run --rm train-gpu status
docker compose --profile gpu run --rm train-gpu
```

Sobrescribir opciones sin editar la configuración:

```bash
docker compose run --rm train train --epochs 1 --device cpu
```

Los hiperparámetros predeterminados están en [`configs/default.yaml`](./configs/default.yaml). Se empieza con el extractor congelado, 160 × 160 píxeles y batch 2. Los pesos preentrenados se guardan bajo `modelo-ia/cache/`; cada ejecución crea un directorio nuevo en `modelo-ia/runs/` con `best.pt`, `config.json` y `metrics.json`.

La pérdida de colores y estilos solo se calcula para prendas que tengan esas anotaciones; una etiqueta ausente en SQLite se trata como no anotada, no como negativa. Las métricas de tipo se calculan sobre imágenes de validación; precision/recall/F1 multi-etiqueta se calculan sobre los ejemplos con anotaciones correspondientes. Revisar especialmente el tamaño del dataset y las métricas antes de usar el checkpoint.

## Predecir

El resultado combina las probabilidades de varias vistas de **la misma prenda**. No detecta ni separa múltiples prendas de una imagen.

```bash
docker compose run --rm train predict \
  --checkpoint /app/modelo-ia/runs/<ejecucion>/best.pt \
  /app/dataset/superior/camisas/CAMISA-1/frente.jpg \
  /app/dataset/superior/camisas/CAMISA-1/espalda.jpg
```

El umbral por defecto proviene del checkpoint; se puede ajustar con `--threshold 0.5`.

## Layout

- [`docker-compose.yaml`](./docker-compose.yaml): servicios CPU y GPU local.
- [`Dockerfile`](./Dockerfile): imagen basada en PyTorch con runtime CUDA 12.4.
- [`entrypoint.sh`](./entrypoint.sh): despacha `train`, `predict` y `status`.
- [`train.py`](./train.py): lectura de SQLite, entrenamiento multisalida y métricas de validación.
- [`predict.py`](./predict.py): predicción de una o varias vistas de una prenda.
- [`modelo-ia/`](./modelo-ia/): checkpoints y caché local, excluidos de Git.
- [`repositorios/`](./repositorios/): espacio para clones auxiliares, excluidos de Git.
- [`scraping-plugin-chrome/folder-destino/`](./scraping-plugin-chrome/folder-destino/README.md): extensión Chrome para descargar manualmente imágenes de producto con un clic.
- [`modelo-general-destilacion/`](./modelo-general-destilacion/README.md): pipeline separado para auditar/importar datasets públicos, guardar resultados de análisis para evitar llamadas repetidas y generar descripciones revisables; ver también el [`plan de pruebas`](./modelo-general-destilacion/PLAN-PRUEBAS.md) y [`dudas.md`](./modelo-general-destilacion/dudas.md).
- El panel local de seguimiento se levanta con `docker compose up -d --build dashboard` desde `modelo-general-destilacion`; monitorea conteos, actividad, prompt y opciones del proveedor en `http://127.0.0.1:8787`. También inicia/detiene lotes y muestra registros por proveedor; desde esos registros se pueden borrar líneas de error o congelar temporalmente la vista sin pausar el proceso.

## Pipeline de curación y anotación

Este flujo es independiente del entrenamiento de MobileNetV3-Small. Su función es auditar fuentes, seleccionar imágenes mapeadas, detectar duplicados, solicitar anotaciones visuales opcionales y guardar sugerencias revisables en el dataset compartido. No aprueba etiquetas ni inicia entrenamiento automáticamente.

La guía completa, las rutas fuente, límites de envío, claves, política de fallback y ejemplos de uso están en [`modelo-general-destilacion/README.md`](./modelo-general-destilacion/README.md). El pipeline unifica `camisa` y `camiseta` en la clase canónica `camisa`, manteniendo la etiqueta de origen en SQLite. En lotes remotos se pueden seleccionar hasta 5.000 imágenes nuevas por proveedor; se omiten hashes importados y análisis vigentes para el proveedor/modelo/configuración antes de aplicar el límite. La selección recomendada busca en todas las fuentes elegibles.

Si está habilitado en `.env`, un fallo de NVIDIA NIM activa el siguiente modelo de la cadena `NVIDIA_NIM_FALLBACK_MODELS`; un fallo de DeepSeek activa NVIDIA NIM como respaldo. Estos intentos pueden enviar la imagen a otro modelo/proveedor y aumentar uso o costo, por lo que el dashboard solicita consentimiento remoto. Las claves se guardan fuera del repositorio y no deben incluirse en argumentos, documentos públicos ni commits.

El dataset ya contiene imágenes importadas, pero falta revisar y aprobar suficientes muestras autorizadas para entrenamiento. En el snapshot documentado en la [guía de factibilidad](../documentacion_dataset/README.md#factibilidad-y-alcance-del-mvp), ninguna prenda estaba aprobada y apta; en ese estado el entrenador termina con un mensaje explícito y no fabrica un modelo de éxito.
