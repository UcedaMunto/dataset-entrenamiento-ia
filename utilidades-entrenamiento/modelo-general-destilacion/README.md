# Curación y anotación de datasets de moda

Este proyecto inspecciona fuentes locales, conserva su clase de origen, normaliza las categorías al dataset del proyecto y, opcionalmente, pide a **un proveedor visual por ejecución** una descripción y sugerencias de color/estilo. Es una etapa de preparación de datos; no es el entrenamiento de MobileNet ni, por sí sola, destilación de conocimiento.

## Estado de los datos y fuentes

`datos-crudos/` contiene los repositorios `clothing-dataset-small-master/` y `clothing-dataset-master/`, además de AIG en `AIG-Dataset/`. AIG tiene 13 carpetas de clase, con 10.000 archivos `.jpg` en cada una. Se inspeccionaron los archivos y no se encontró README, LICENSE ni manifiesto adicional en esa carpeta. Fashion-MNIST no está presente. No se descargan repositorios ni datasets automáticamente.

El usuario confirma que las imágenes agregadas tienen permiso de uso comercial libre. Las páginas/README locales de ambos repositorios de clothing también indican uso libre/comercial y sus copias incluyen LICENSE CC0. La ingesta conserva fuente y etiqueta original por imagen para mantener trazabilidad.

Ejecuta la auditoría para comprobar el contenido actual:

```bash
docker compose -f compose.yml build
docker compose -f compose.yml run --rm curator audit
```

| Fuente | Carpetas esperadas bajo `datos-crudos/` | Uso y mapeo inicial |
|---|---|---|
| [clothing-dataset-small](https://github.com/alexeygrigorev/clothing-dataset-small) | `clothing-dataset-small-master/{train,validation,test}/<clase>/` | Descargado/descomprimido: el inventario tiene 3.783 archivos. Se mapean `dress`, `pants`, `shirt`, `shorts`, `skirt` y `t-shirt`; `hat`, `shoes`, `longsleeve` y `outwear` se omiten. |
| [clothing-dataset](https://github.com/alexeygrigorev/clothing-dataset) | `clothing-dataset-master/images.csv` y `images/<id>.jpg` | Descargado/descomprimido: CSV de 5.403 filas. Se mapean `Blouse`, `Blazer`, `Dress`, `Pants`, `Polo`, `Shirt`, `Shorts`, `Skirt`, `T-Shirt` y `Undershirt`. `Polo`/`Undershirt` se guardan como `camisa`; `Blazer` como `chaqueta`. El resto se omite. |
| [Apparel Images Gallery (Mendeley)](https://data.mendeley.com/datasets/pxkbgkydrp/1) | `AIG-Dataset/<clase>/*.jpg` | Descargado: 130.000 imágenes (13 carpetas de 10.000). Se aceptan las 12 carpetas que tienen correspondencia en la taxonomía y se omite `Hoodies` (10.000), que no es una clase canónica. Los archivos locales no incluyen README ni licencia; se usa la confirmación del usuario de que las imágenes tienen permiso comercial libre. |
| [Fashion-MNIST](https://github.com/zalandoresearch/fashion-mnist) | `fashion-mnist/` | No está presente. Cuando se añada, será benchmark independiente de 28×28 en escala de grises, no fotos a color para anotación. |

En la última auditoría local, el subset tenía 3.781 imágenes: 2.513 con clase mapeada; las otras 1.268 etiquetas se omiten. El dataset completo tenía 5.403 filas: 3.271 mapeadas y 2.132 omitidas. AIG contiene 120.000 imágenes en carpetas mapeadas y 10.000 en `Hoodies`, que se excluyen por no pertenecer al catálogo. Aunque los archivos terminan en `.jpg`, una inspección del contenido encontró 124.042 JPEG, 5.956 WebP y 2 PNG; el pipeline determina el MIME por el contenido real y conserva intactos los bytes. Ninguna de las 130.000 imágenes AIG supera 200.000 bytes (máximo observado: 92.069 bytes). Los totales se pueden volver a generar con `audit`.

La configuración/mapeos editables están en [`sources.json`](./sources.json). El pipeline solo procesa etiquetas incluidas explícitamente en el mapeo: carpetas o filas fuera de la taxonomía no se copian ni se envían a una API. Las imágenes de más de **200.000 bytes (0,2 MB decimal)** también se excluyen; no se reducen, convierten ni recomprimen antes del envío. Los ZIP originales locales se conservan y `datos-crudos/` está excluido de Git.

## Arquitectura mínima

- [`compose.yml`](./compose.yml): servicio efímero `curator`; monta `datos-crudos/` en solo lectura y el dataset SQLite/carpeta del proyecto en escritura.
- [`Dockerfile`](./Dockerfile): Python 3.12 con Pillow y Requests.
- [`app.py`](./app.py): auditoría, mapeo de clases, importación, hash para evitar duplicados y anotación visual opcional.
- [`sources.json`](./sources.json): directorios, licencia declarada, clases que se admiten y mapeos al catálogo actual.
- [`.env.example`](./.env.example): plantilla de un único `.env` con las tres claves y configuraciones de proveedor; el `.env` real está excluido de Git.
- El esquema compartido contiene `descripcion_prenda` y `analisis_imagen`: anotaciones revisables y cache de decisiones por hash/clase/proveedor/modelo/versión de prompt.
- `prenda_imagen.etiqueta_fuente` conserva la etiqueta original (por ejemplo `Polo`) junto a la categoría canónica (por ejemplo `camisa`).
- [`dashboard.py`](./dashboard.py) y [`dashboard.html`](./dashboard.html): panel local para monitorear prendas por tipo y últimas importaciones, iniciar y detener lotes desde el navegador con estado y registro en vivo, y cambiar prompt, vocabularios y proveedor/claves.

Una imagen fuente produce inicialmente una carpeta/prenda en `dataset/`. Se conserva la partición si el path tiene `train`, `validation`/`val` o `test`; si no, se asigna determinísticamente por hash. El registro queda `pendiente` y `apta_para_entrenamiento=0`. Para llamadas remotas, la IA valida si la imagen corresponde a la clase fuente y puede descartarla antes de copiarla. Las imágenes aceptadas se importan con anotación pendiente; color/estilo sugeridos se guardan en `descripcion_prenda.atributos_sugeridos`, no como etiquetas supervisadas confirmadas. Una persona debe revisar y aprobarlas antes de entrenar.

Cada respuesta válida se guarda en `analisis_imagen`, tanto si acepta como si descarta la muestra. Al repetir la ejecución con la misma imagen, clase canónica, proveedor, modelo y versión del prompt, se reutiliza esa decisión y se evita otra llamada. Un análisis aceptado también queda protegido contra duplicación por SHA-256 en `prenda_imagen`. Si cambia proveedor/modelo o se incrementa la versión del prompt, la huella cambia intencionalmente.

## Proveedores de visión y secretos

Se selecciona **uno** por ejecución; el mismo archivo `.env` aloja las claves de los tres proveedores. Copia `.env.example` a `.env` y completa solo las credenciales que vas a utilizar:

| Proveedor | Valores orientativos |
|---|---|
| OpenAI API con visión | `ANNOTATION_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL` y `OPENAI_BASE_URL` |
| NVIDIA NIM en nube | `ANNOTATION_PROVIDER=nim`, `NVIDIA_NIM_API_KEY`, `NVIDIA_NIM_MODEL` y `NVIDIA_NIM_BASE_URL`; el modelo vision predeterminado es `meta/llama-3.2-11b-vision-instruct` y debe estar disponible para la cuenta en el catálogo NIM. Se usa el endpoint hospedado por defecto. El acceso sin costo depende de la cuota/créditos y disponibilidad del modelo en la cuenta. |
| DeepSeek | `ANNOTATION_PROVIDER=deepseek`, `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` y `DEEPSEEK_BASE_URL`; selecciona un modelo/end-point que admita imágenes. Considerarlo servicio de pago. |

El contexto estructurado del prompt se expresa en **TOON** para reducir verbosidad. El sobre de Chat Completions sigue siendo JSON —es el formato de transporte que exigen las API compatibles— y se solicita JSON como salida para validar y almacenar respuestas. NVIDIA NIM y DeepSeek usan `response_format=json_object`; la respuesta inicial permite 1.024 tokens y, ante contenido vacío o truncado (`finish_reason=length`), se reintenta una sola vez con 2.048 tokens y una instrucción aún más concisa. DeepSeek inicia con el modo de razonamiento desactivado (`thinking.type=disabled`): ese modo viene activado por defecto con esfuerzo alto y puede consumir el límite de salida antes de producir el JSON. Su documentación también advierte que JSON Output puede devolver contenido vacío y recomienda incluir JSON y un ejemplo; el prompt ya incluye ambos. Fuentes: [JSON Output de DeepSeek](https://api-docs.deepseek.com/guides/json_mode) y [Thinking Mode de DeepSeek](https://api-docs.deepseek.com/guides/thinking_mode). La [documentación de NIM](https://docs.api.nvidia.com/nim/reference/llm-apis) define `POST /v1/chat/completions`, pero no anuncia un límite universal de peticiones por segundo para todos los modelos/cuentas. Por precaución, este curador separa **al menos 3 segundos entre inicios de solicitudes NIM** (máximo teórico 20 por minuto, normalmente menos por el tiempo de inferencia). Ante un timeout, espera un tiempo aleatorio de **30 a 120 segundos** y reintenta una vez la misma imagen; si vuelve a expirar, la omite y continúa con la siguiente. La respuesta tardía del proveedor podría haber sido procesada/cobrada, así que cualquier reintento puede duplicar ese consumo. Si el modelo devuelve `motivo_descarte: null` para una imagen apta, se normaliza como cadena vacía. Una respuesta que siga incompleta o sea inválida tras el reintento se informa, no se guarda y el lote continúa con la siguiente; los errores HTTP/red distintos de timeout siguen deteniendo el lote. Las imágenes se envían en su formato y bytes originales como data URL; el MIME se detecta por el contenido y no se redimensionan, recodifican ni recomprimen. Solo se aceptan contenidos JPEG, PNG, GIF y WebP para anotación remota.

Para reducir respuestas largas de NIM, solo ese proveedor recibe instrucciones más estrictas: descripciones de hasta **8 palabras**, un máximo de **2 colores** y **2 estilos**, y motivos de descarte de hasta **8 palabras**. Esos mismos límites se aplican al resultado antes de guardarlo, incluso si el modelo no sigue el prompt. DeepSeek conserva sus límites previos de 12 palabras y hasta 3 valores por lista. La vista previa del dashboard muestra el prompt acotado de NIM; estos cambios incrementan la versión del prompt para invalidar análisis cacheados con instrucciones anteriores.

No pongas claves en `compose.yml`, argumentos de shell, SQLite ni commits. No se envían etiquetas sin mapeo, imágenes >200.000 bytes ni formatos incompatibles. Antes de aplicar `--limit`, la ingesta quita hashes que ya están en el dataset y repeticiones dentro del plan; por eso las siguientes ejecuciones avanzan a imágenes nuevas en vez de volver a seleccionar las primeras ya importadas. El registro informa cuántas duplicadas se omitieron antes de la IA. Para usar APIs remotas se requieren explícitamente `--allow-remote`, `--limit` y `--execute`. Los errores HTTP/red del proveedor detienen el lote; respuestas de IA con estructura inválida se omiten y el lote continúa.

## Uso seguro y reproducible

La suite automatizada local y las etapas de validación están descritas en [`PLAN-PRUEBAS.md`](./PLAN-PRUEBAS.md). Ejecuta primero sus pruebas sin red ni credenciales.

Levanta la interfaz en localhost:

```bash
docker compose up -d dashboard
```

Abre `http://127.0.0.1:8787`. El servicio usa la red del host porque el reenvío IPv4 de Docker está deshabilitado en este equipo; el servidor se enlaza estrictamente a `127.0.0.1` y no se publica en la red local. En **Procesar imágenes ahora** selecciona una fuente, uno o ambos proveedores y un máximo de **1–5.000 imágenes por proveedor**. NIM y DeepSeek pueden ejecutarse en paralelo en procesos independientes; cada uno muestra progreso y botón de detención propios. Si ambos se seleccionan, cada proveedor examina hasta el mismo límite, por lo que se pueden realizar hasta 10.000 análisis combinados y enviar cada imagen a los dos servicios. El panel impide duplicar importaciones concurrentes de la misma imagen mediante una transacción SQLite de escritura. Para importar localmente debes confirmar la escritura en el dataset y SQLite. Para NIM o DeepSeek también debes autorizar expresamente el envío de imágenes; las claves deben estar configuradas. **Detener envío** afecta solo al proveedor elegido, no inicia más solicitudes para ese proceso y permite que termine/importa la imagen que ya está en análisis. Si la detención ocurre durante la espera de reintento tras un timeout, se cancela ese reintento. No se ejecuta ningún lote automáticamente al abrir la página.

Las claves se capturan como campos tipo password, nunca se devuelven al navegador y se escriben en `.env` con permisos privados. El prompt y las listas de color/estilo se guardan en SQLite. Cambiar prompt, modelo, categoría o vocabulario produce una huella de análisis distinta para que el cache no reutilice un resultado obsoleto. El estimado a 5.000 requiere historial suficiente; antes el panel lo indica sin inventar un tiempo.

1. Descarga manualmente los datasets autorizados en los directorios de la tabla.
2. Audita sin escribir ni contactar proveedores:

   ```bash
   docker compose -f compose.yml run --rm curator audit
   ```

3. Ensaya el mapeo de una fuente:

   ```bash
   docker compose -f compose.yml run --rm curator ingest \
     --source clothing-small --provider none
   ```

4. Importa sin enviar imágenes a terceros:

   ```bash
   docker compose -f compose.yml run --rm curator ingest \
     --source clothing-small --provider none --execute
   ```

5. Solo para una muestra pequeña que hayas autorizado, configura `.env` y limita explícitamente una prueba remota:

   ```bash
   docker compose -f compose.yml run --rm curator ingest \
     --source mendeley-aig --provider nim --allow-remote --limit 10 --execute
   ```

NIM se usará en nube sujeto a la cuota gratuita disponible; DeepSeek es de pago. Cada llamada remota puede consumir cuota o generar costo. `--allow-remote`, `--limit` y `--execute` son requisitos explícitos tanto en CLI como al iniciar un lote desde el dashboard. Las rutas fuente se montan read-only. Los archivos importados se guardan en la estructura canónica; los originales no se modifican. Ejecuta `audit` después de importar para verificar conteos.

Si una solicitud remota expira, puede haberse realizado una llamada facturable aunque no llegue respuesta. Para NIM el curador espera aleatoriamente 30–120 segundos y reintenta una vez la misma imagen; un segundo timeout omite esa imagen y continúa. El botón **Detener envío** previene nuevas llamadas, pero no interrumpe una petición que el proveedor ya está procesando. Revisa el uso en el proveedor antes de volver a ejecutar un lote.

## ¿Es destilación?

En sentido estricto, **todavía no**. Este flujo importa datos con etiquetas originales y genera *pseudo-etiquetas* y descripciones textuales con un modelo maestro (VLM). Esto se suele llamar curación/anotación asistida por IA o pseudo-labeling. La destilación clásica requiere después entrenar un modelo estudiante con objetivos producidos por el maestro —idealmente distribuciones/logits o supervisión docente definida— y evaluar su transferencia. `descripcion_prenda` guarda texto y sugerencias, no logits; por eso no los presentamos como conocimiento destilado ni los aprobamos automáticamente.

## Decisiones pendientes

Las preguntas restantes se mantienen en [`dudas.md`](./dudas.md): confirmar el tope de gasto de DeepSeek y los criterios de aprobación humana. AIG ya fue localizado, su estructura fue inspeccionada y se habilitó con las clases canónicas compatibles; `Hoodies` se excluye.
