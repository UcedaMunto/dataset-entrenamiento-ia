# Utilidades de entrenamiento

Este directorio contiene el entorno Docker Compose y los scripts para el MVP MobileNetV3-Small. El dataset y sus tablas SQLite permanecen en `../dataset/`; los checkpoints y la caché de pesos preentrenados se escriben en `modelo-ia/`. Los repositorios auxiliares descargados, si fueran necesarios, se pueden colocar en `repositorios/`; no se versionan automáticamente.

## Interfaz de entrenamiento

El servicio `train` entrena en segundo plano y no publica puertos; por eso no aparece una URL en `docker ps`. Para abrir el panel de seguimiento, ejecuta desde este directorio:

```bash
docker compose build
docker compose --profile monitor up -d monitor
```

Abre `http://127.0.0.1:8090`. El panel permite iniciar o detener el entrenamiento, revisar progreso/métricas y probar los modelos guardados. Para detener el panel: `docker compose --profile monitor down`. Si Docker corre en otra máquina, usa un túnel SSH para el puerto 8090; el panel se enlaza solo a localhost.

El dashboard de curación de datos es independiente y se sirve en `http://127.0.0.1:8787`; sus instrucciones están en [`modelo-general-destilacion/README.md`](./modelo-general-destilacion/README.md).

### Prueba CPU de un modelo ya entrenado

En el monitor pulsa **Probar modelo en CPU**, selecciona una ejecución con `best.pt` y carga una imagen. La interfaz muestra la predicción y latencias de carga del checkpoint, preparación de imagen, inferencia y petición total. El cargador ubica el modelo en CPU y la inferencia no actualiza ni guarda pesos. Esta es una prueba funcional/latencia de **inferencia del modelo ya entrenado**; no inicia entrenamiento ni mide cuánto tardaría una época.

En el servidor revisado hay 12 CPU lógicas y 15 GiB de RAM; el dataset tenía 12.379 imágenes train, 1.511 val y 1.529 test. Una inferencia CPU exitosa permite evaluar el uso del modelo sin GPU en ese host, pero no basta para afirmar que entrenar sobre todo ese dataset en CPU sea práctico. Para eso se necesitaría un benchmark de entrenamiento separado y autorizado, que no forma parte de esta prueba.

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

Los hiperparámetros predeterminados están en [`configs/default.yaml`](./configs/default.yaml): MobileNetV3-Small a 224 × 224, batch 64, hasta 30 épocas, calentamiento inicial de cabezas y ajuste fino, con parada temprana. Los pesos preentrenados se guardan bajo `modelo-ia/cache/`; cada ejecución crea un directorio nuevo en `modelo-ia/runs/` con `best.pt`, `config.json` y `metrics.json`.

## Estrategia recomendada para continuar

En el historial actual, la ejecución que registró 20 épocas guardó su mejor checkpoint en la época 15 (pérdida de validación 0,513). La ejecución posterior quedó en 7 épocas y su mejor pérdida registrada es 0,577. Por eso la recomendación es seleccionar la ejecución de 20 épocas y continuar desde su `best.pt` (época 15), no desde la ejecución parcial ni desde su última época. Esta comparación solo es válida si ambas ejecuciones usaron el mismo split de validación; verifica los artefactos y el registro de imágenes si el dataset cambió.

En el monitor, selecciona la ejecución en **Ejecución**, elige **Ajuste fino completo (recomendado)** y pulsa **Continuar desde mejor checkpoint**. Esta estrategia inicia una nueva fase de hasta 10 épocas: conserva los pesos del checkpoint, ajusta toda la red, usa tasa de aprendizaje `0.0001` para las cabezas y `0.00001` para MobileNet, y mantiene la parada temprana con paciencia 5. La ejecución nueva guarda su origen y estrategia en `config.json`; valida su checkpoint con el conjunto de validación. El conjunto `test` no se usa para escoger el checkpoint y debe reservarse para la evaluación final.

**Solo entrenar las cabezas** es la alternativa conservadora si el ajuste fino completo hace que la pérdida de validación empeore o el dataset sea muy pequeño: mantiene congelada la base MobileNet y adapta las salidas de tipo, color y estilo. Se puede detener la fase desde el monitor si la validación se deteriora; cada época y checkpoint quedan en una ejecución separada.

Continuar es un *warm start*, no una reanudación exacta: cada fase nueva usa optimizador, scheduler y contador de épocas nuevos porque los checkpoints actuales no guardan esos estados. La interfaz usa el mejor checkpoint de la ejecución seleccionada y solo lo acepta si coinciden arquitectura, catálogo de clases y resolución. Si cambia el catálogo, corrige/configura la compatibilidad antes de continuar; no fuerces el `state_dict`.

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

## API de inferencia en una VM con CPU

`inference_api.py` es un servicio independiente del monitor y del curador. Sirve **solo inferencia** de un `best.pt` existente: obliga a usar CPU, carga un único checkpoint de solo lectura al iniciar y no monta `dataset/`, SQLite de entrenamiento ni cachés. No requiere GPU, NVIDIA Container Toolkit ni conexión a proveedores de anotación. El contenedor parte de la imagen PyTorch actual, que puede incluir bibliotecas CUDA, pero no reserva ni usa GPU.

### Requisitos y selección del modelo

- VM Linux con Docker Engine y Docker Compose v2.
- Un checkpoint `best.pt` compatible con `MobileNetV3-Small` y las clases guardadas en él. Para el historial descrito en esta guía, el checkpoint recomendado es `modelo-ia/runs/20261018-020637/best.pt`, cuyo mejor estado fue la época 15.
- Memoria y CPU suficientes para mantener el proceso y ejecutar inferencias. En el host de desarrollo medimos 12 CPU lógicas y 15 GiB RAM; esto no es un mínimo universal ni mide tiempo de entrenamiento.

Desde `utilidades-entrenamiento/`, selecciona un checkpoint que exista en esa VM y levanta la API:

```bash
export MODEL_CHECKPOINT="$PWD/modelo-ia/runs/20261018-020637/best.pt"
export API_CPU_THREADS=4
docker compose -f compose.cpu-api.yaml up -d --build
```

`MODEL_CHECKPOINT` debe ser una ruta absoluta al archivo del host; Compose lo monta como `/models/best.pt` de solo lectura. La única carpeta de datos que recibe el contenedor es el checkpoint. `API_CPU_THREADS` limita los hilos de PyTorch (predeterminado: 4). No inicies esta API con el Compose de entrenamiento ni con el dashboard de curación: tiene su propio archivo y servicio.

Comprobación de salud:

```bash
curl http://127.0.0.1:8081/health
```

Respuesta esperada: `{"status":"ok","device":"cpu"}`. La especificación interactiva OpenAPI está en `http://127.0.0.1:8081/docs`.

### Contrato de dos imágenes

`POST /v1/predict` recibe `multipart/form-data` con exactamente estos dos campos de archivo requeridos:

- `garment_image`: foto de la prenda aislada o de producto.
- `person_image`: foto de una persona usando esa misma prenda.

Admite JPEG, PNG y WebP; cada archivo puede pesar hasta 10 MiB y tener como máximo 25 megapíxeles. Ejemplo desde el host:

```bash
curl --fail-with-body -X POST http://127.0.0.1:8081/v1/predict \
  -F 'garment_image=@/ruta/a/prenda.jpg' \
  -F 'person_image=@/ruta/a/persona-con-prenda.jpg'
```

La respuesta incluye `descripcion_mas_probable`, probabilidades combinadas, predicciones separadas bajo `predicciones_por_imagen.prenda` y `.persona`, el método de combinación y latencias. Para tipo se promedian las distribuciones softmax de ambas imágenes; para color y estilo se promedian las probabilidades sigmoid. Color/estilo devuelven los cinco candidatos principales y marcan `supera_umbral` usando el umbral almacenado en el checkpoint.

La descripción es una plantilla construida con las clases del modelo (tipo, colores y estilos); **no** la redacta un modelo de lenguaje ni incluye atributos abiertos como material, estampado o ajuste. La API tampoco verifica que ambas fotos muestren la misma prenda. El modelo fue entrenado para clasificar fotos de prendas y la imagen de una persona puede pertenecer a otro dominio visual; por eso se devuelven las dos predicciones individuales para detectar desacuerdos en lugar de ocultarlos en el promedio.

### Red y seguridad

El servicio se publica solo en `127.0.0.1:8081` del host y no tiene autenticación. Para acceder desde una computadora remota, crea un túnel SSH:

```bash
ssh -L 8081:127.0.0.1:8081 usuario@servidor
```

Luego usa `http://127.0.0.1:8081` en esa computadora. No publiques el puerto directamente en Internet; para acceso compartido, colócalo detrás de un proxy con TLS, autenticación y límites de solicitudes.

Detener el servicio:

```bash
docker compose -f compose.cpu-api.yaml down
```

Para cambiar checkpoint, detén el servicio, actualiza `MODEL_CHECKPOINT` y vuelve a levantarlo. La prueba CPU de entrenamiento no forma parte de esta API; inferencia rápida no demuestra que entrenar todo el dataset en CPU sea viable.

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
