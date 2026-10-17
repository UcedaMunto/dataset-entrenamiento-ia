# Curación y anotación de datasets de moda

Este proyecto inspecciona fuentes locales, conserva su clase de origen, normaliza las categorías al dataset del proyecto y, opcionalmente, pide a uno o más proveedores visuales una descripción y sugerencias de color, estilo y temporada. Los colores están limitados al catálogo; los estilos y temporadas nuevos se incorporan automáticamente a SQLite cuando los responde una API. Es una etapa de preparación de datos; no es el entrenamiento de MobileNet ni, por sí sola, destilación de conocimiento.

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
- Durante el procesamiento, las categorías `camisa` y `camiseta` se normalizan a la clase canónica `camisa`; la etiqueta original de la fuente se conserva para trazabilidad.
- [`dashboard.py`](./dashboard.py) y [`dashboard.html`](./dashboard.html): panel local para monitorear prendas por tipo y últimas importaciones, iniciar y detener lotes desde el navegador con estado y registro en vivo, y cambiar prompt, vocabularios y proveedor/claves.

Una imagen fuente produce inicialmente una carpeta/prenda en `dataset/`. Se conserva la partición si el path tiene `train`, `validation`/`val` o `test`; si no, se asigna determinísticamente por hash. El registro queda `pendiente` y `apta_para_entrenamiento=0`. Para llamadas remotas, la IA valida si la imagen corresponde a la clase fuente y puede descartarla antes de copiarla. Las imágenes aceptadas se importan con anotación pendiente; color/estilo sugeridos se guardan en `descripcion_prenda.atributos_sugeridos`, no como etiquetas supervisadas confirmadas. Una persona debe revisar y aprobarlas antes de entrenar.

Cada respuesta válida se guarda en `analisis_imagen`, tanto si acepta como si descarta la muestra. Al repetir la ejecución con la misma imagen, clase canónica, proveedor, modelo y versión del prompt, se reutiliza esa decisión y se evita otra llamada. Un análisis aceptado también queda protegido contra duplicación por SHA-256 en `prenda_imagen`. Si cambia proveedor/modelo o se incrementa la versión del prompt, la huella cambia intencionalmente.

## Proveedores de visión y secretos

El comando de ingesta selecciona **un proveedor** por ejecución; desde el dashboard es posible lanzar NVIDIA NIM y DeepSeek en paralelo. El mismo archivo `.env` aloja las claves de los tres proveedores. Copia `.env.example` a `.env` y completa solo las credenciales que vas a utilizar:

| Proveedor | Valores orientativos |
|---|---|
| OpenAI API con visión | `ANNOTATION_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL` y `OPENAI_BASE_URL` |
| NVIDIA NIM en nube | `ANNOTATION_PROVIDER=nim`, `NVIDIA_NIM_API_KEY`, `NVIDIA_NIM_MODEL` y `NVIDIA_NIM_BASE_URL`; el modelo visual recomendado es `nvidia/nemotron-3.5-super-vl-120b-a12b`, un modelo multimodal de NVIDIA disponible en NIM. Se usa el endpoint hospedado por defecto; acceso y cuota dependen de la cuenta. |
| DeepSeek | `ANNOTATION_PROVIDER=deepseek`, `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` y `DEEPSEEK_BASE_URL`; selecciona un modelo/end-point que admita imágenes. Considerarlo servicio de pago. |

El contexto estructurado del prompt se expresa en **TOON** para reducir verbosidad. El sobre de Chat Completions sigue siendo JSON —es el formato de transporte que exigen las API compatibles— y se solicita JSON como salida para validar y almacenar respuestas. DeepSeek usa `response_format=json_object`, empieza con 1.024 tokens y, ante contenido vacío o truncado (`finish_reason=length`), se reintenta una vez con 2.048 tokens. DeepSeek también inicia con el modo de razonamiento desactivado (`thinking.type=disabled`), porque el modo de razonamiento puede consumir el límite de salida antes de producir el JSON. Su documentación advierte que JSON Output puede devolver contenido vacío y recomienda incluir JSON y un ejemplo; el prompt contiene ambos. Fuentes: [JSON Output de DeepSeek](https://api-docs.deepseek.com/guides/json_mode) y [Thinking Mode de DeepSeek](https://api-docs.deepseek.com/guides/thinking_mode). La [documentación de NIM](https://docs.api.nvidia.com/nim/reference/llm-apis) define `POST /v1/chat/completions`, pero no anuncia un límite universal de peticiones por segundo para todas las cuentas.

NIM segmenta cada imagen en cuatro solicitudes visuales con `response_format=json_object`: **colores**, **estilos**, **temporadas** y **validación de clase/descripción**; el curador combina los resultados en una anotación. Cada etapa empieza con 256 tokens y reintenta una vez con 512 si el JSON está malformado o no tiene la estructura esperada. El modo de razonamiento se desactiva en `nvidia/nemotron-3.5-super-vl-120b-a12b` (`reasoning_effort=none`) para priorizar respuestas cortas con el formato solicitado. El modelo visual anterior, `meta/llama-3.2-11b-vision-instruct`, sigue seleccionable en `NVIDIA_NIM_MODEL`, pero la base local muestra que produjo reintentos de formato en el lote más reciente. La [tarjeta oficial de Nemotron 3.5 Super VL](https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b.md) indica soporte de texto e imágenes y la [referencia NIM](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3_5-super-vl-120b-a12b-infer) muestra `reasoning_effort: none` en una solicitud visual. Este cambio de modelo es una configuración recomendada, no una garantía de disponibilidad o calidad; verifica primero que la cuenta tenga acceso.

Si un modelo NIM falla por HTTP/red, timeout o respuesta inválida, el mismo análisis se intenta automáticamente con el siguiente modelo de `NVIDIA_NIM_FALLBACK_MODELS`. Por defecto la cadena incluye `meta/llama-3.2-11b-vision-instruct` y `nvidia/nemotron-3.5-super-vl-120b-a12b`, omitiendo el modelo activo para evitar repetirlo; al encontrar un modelo que responda, se usa para el resto del lote. Las filas guardan el proveedor/modelo que realmente produjo el resultado. Se puede ajustar la lista separada por comas en `.env`.

Solo se conservan colores exactos del catálogo; se permiten hasta dos valores observables por lista de estilo y temporada, incluidos valores nuevos. Los estilos y temporadas nuevos se agregan al catálogo SQLite cuando una API los responde, incluso si la imagen queda descartada. Se descartan valores de color desconocidos, pero no se rechaza toda la imagen por proponer un estilo o temporada nuevos. Una etapa que continúe inválida después del reintento se reporta y no guarda el análisis; el pipeline prueba entonces el siguiente modelo NIM disponible. Se mantiene una separación mínima de **3 segundos entre inicios de solicitudes NIM**; cuatro etapas equivalen a un máximo teórico cercano a **5 imágenes por minuto**, sin contar latencia ni reintentos. Ante un timeout, cada modelo NIM espera un tiempo aleatorio de **30 a 120 segundos** y reintenta una vez la misma imagen antes de avanzar al siguiente modelo. Una respuesta tardía podría haber sido procesada/cobrada, así que cada reintento puede duplicar consumo. Las claves de análisis de NIM usan una versión separada para evitar reutilizar resultados previos a la segmentación sin invalidar el cache de DeepSeek.

Las imágenes se envían en su formato y bytes originales como data URL; el MIME se detecta por el contenido y no se redimensionan, recodifican ni recomprimen. Solo se aceptan contenidos JPEG, PNG, GIF y WebP para anotación remota. `motivo_descarte: null` se normaliza a texto vacío solo para imágenes aceptadas. Si DeepSeek o NIM entrega una respuesta inválida se prueban los fallbacks configurados; si persiste la respuesta inválida tras agotar modelos, esa imagen no se guarda y el lote continúa. Los errores de HTTP/red también prueban los fallbacks; si todos los proveedores/modelos disponibles fallan con error de servicio, el lote termina con error explícito.

Para reducir respuestas largas de NIM, solo ese proveedor recibe instrucciones más estrictas: descripciones y motivos de descarte de hasta **8 palabras**, y un máximo de **2 colores, 2 estilos y 2 temporadas**. DeepSeek conserva sus límites previos de 12 palabras y hasta 3 valores por lista. Si DeepSeek falla por HTTP/red, timeout o respuesta inválida, el mismo análisis se intenta automáticamente con NVIDIA NIM cuando la clave está configurada; se registran e importan los resultados bajo el proveedor/modelo que efectivamente respondió. Si no hay clave NIM, el error se informa y el lote no presenta la imagen como procesada. En sentido inverso, si DeepSeek tiene una clave configurada, cada imagen que NIM descarte se evalúa también con DeepSeek; si DeepSeek la acepta, se importa y la descripción queda atribuida a ese proveedor. Se conservan ambos análisis en SQLite para poder auditar la diferencia. Si no hay clave DeepSeek, se conserva el descarte NIM y se informa que no se hizo el segundo análisis. Al seleccionar NIM y DeepSeek en paralelo desde el dashboard, el fallback implícito de NIM se desactiva para no duplicar las llamadas: el lote explícito de DeepSeek procesa también la imagen, aunque un fallo de DeepSeek aún puede usar NIM como respaldo. La confirmación de envío del dashboard advierte que, con solo NIM seleccionado, los descartes pueden enviarse además a DeepSeek. En “Prendas incorporadas y descartadas”, el dashboard separa las incorporadas y las descartadas por proveedor. Para análisis antiguos que no registraban la ruta original, busca la imagen fuente por su hash SHA-256. El panel “Resultados válidos por modelo” cuenta los análisis guardados en SQLite, separados en aceptados y descartados; una respuesta JSON inválida que no se guarda no se suma a esos totales. Los reintentos/errores del lote activo aparecen en el registro de cada proveedor.

No pongas claves en `compose.yml`, argumentos de shell, SQLite ni commits. No se envían etiquetas sin mapeo, imágenes >200.000 bytes ni formatos incompatibles. Antes de aplicar `--limit`, la ingesta quita hashes que ya están en el dataset y repeticiones dentro del plan; por eso las siguientes ejecuciones avanzan a imágenes nuevas en vez de volver a seleccionar las primeras ya importadas. El registro informa cuántas duplicadas se omitieron antes de la IA. Para usar APIs remotas se requieren explícitamente `--allow-remote`, `--limit` y `--execute`. Los errores HTTP/red del proveedor detienen el lote; respuestas de IA con estructura inválida se omiten y el lote continúa.

## Uso seguro y reproducible

La suite automatizada local y las etapas de validación están descritas en [`PLAN-PRUEBAS.md`](./PLAN-PRUEBAS.md). Ejecuta primero sus pruebas sin red ni credenciales.

Levanta la interfaz en localhost:

```bash
docker compose up -d dashboard
```

Abre `http://127.0.0.1:8787`. El servicio usa la red del host porque el reenvío IPv4 de Docker está deshabilitado en este equipo; el servidor se enlaza estrictamente a `127.0.0.1` y no se publica en la red local. En **Procesar imágenes ahora**, elige **Todas las fuentes elegibles (recomendado)** o limita el procesamiento a una fuente, uno o ambos proveedores y un máximo de **1–5.000 imágenes nuevas por proveedor**. El máximo se aplica después de omitir las imágenes ya importadas, las duplicadas y las que ya tienen un análisis vigente para ese proveedor, modelo y configuración del prompt. Los análisis aceptados guardados pero todavía no importados se recuperan sin consumir el límite ni volver a llamar a la API. NIM y DeepSeek pueden ejecutarse en paralelo en procesos independientes; cada uno muestra progreso y botón de detención propios. Si ambos se seleccionan, cada proveedor busca hasta ese límite entre las imágenes que aún no ha analizado; la selección puede solaparse y cada imagen puede enviarse a ambos servicios. Para importar localmente debes confirmar la escritura en el dataset y SQLite. Para NIM o DeepSeek también debes autorizar expresamente el envío de imágenes; las claves deben estar configuradas. **Detener envío** afecta solo al proveedor elegido, no inicia más solicitudes para ese proceso y permite que termine/importa la imagen que ya está en análisis. Si la detención ocurre durante la espera de reintento tras un timeout, se cancela ese reintento. No se ejecuta ningún lote automáticamente al abrir la página.

Las claves se capturan como campos tipo password, nunca se devuelven al navegador y se escriben en `.env` con permisos privados. El prompt y las listas de color/estilo/temporada se guardan en SQLite. Cambiar prompt, modelo, categoría o vocabulario produce una huella de análisis distinta para que el cache no reutilice un resultado obsoleto. El estimado a 5.000 requiere historial suficiente; antes el panel lo indica sin inventar un tiempo.

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
