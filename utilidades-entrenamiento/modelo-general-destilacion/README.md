# Curación y anotación de datasets de moda

Este proyecto inspecciona fuentes locales, conserva su clase de origen, normaliza las categorías al dataset del proyecto y, opcionalmente, pide a uno o más proveedores visuales una descripción y sugerencias de color, estilo y temporada. Los colores están limitados al catálogo; los estilos y temporadas nuevos se incorporan automáticamente a SQLite cuando los responde una API. Es una etapa de preparación de datos; no es el entrenamiento de MobileNet ni, por sí sola, destilación de conocimiento.

[Índice documental](../../docs/INDICE.md) · [Estado verificado](../../docs/VALIDACION.md).

El máximo actual del panel es **15.000 imágenes nuevas por proveedor**; 5.000 es un objetivo de referencia, no el límite técnico.

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
| [clothing-dataset-small](https://github.com/alexeygrigorev/clothing-dataset-small) | `clothing-dataset-small-master/{train,validation,test}/<clase>/` | Descargado/descomprimido: la última auditoría contó 3.781 archivos. Se mapean `dress`, `pants`, `shirt`, `shorts`, `skirt` y `t-shirt`; `hat`, `shoes`, `longsleeve` y `outwear` se omiten. Las cantidades pueden cambiar si se actualizan los archivos; `audit` es la referencia para el estado actual. |
| [clothing-dataset](https://github.com/alexeygrigorev/clothing-dataset) | `clothing-dataset-master/images.csv` y `images/<id>.jpg` | Descargado/descomprimido: CSV de 5.403 filas. Se mapean `Blouse`, `Blazer`, `Dress`, `Pants`, `Polo`, `Shirt`, `Shorts`, `Skirt`, `T-Shirt` y `Undershirt`. `Polo`/`Undershirt` se guardan como `camisa`; `Blazer` como `chaqueta`. El resto se omite. |
| [Apparel Images Gallery (Mendeley)](https://data.mendeley.com/datasets/pxkbgkydrp/1) | `AIG-Dataset/<clase>/*.jpg` | Descargado: 130.000 imágenes (13 carpetas de 10.000). Se aceptan las 12 carpetas que tienen correspondencia en la taxonomía y se omite `Hoodies` (10.000), que no es una clase canónica. Los archivos locales no incluyen README ni licencia; se usa la confirmación del usuario de que las imágenes tienen permiso comercial libre. |
| [Fashion-MNIST](https://github.com/zalandoresearch/fashion-mnist) | `fashion-mnist/` | No está presente. Cuando se añada, será benchmark independiente de 28×28 en escala de grises, no fotos a color para anotación. |

En la última auditoría local, el subset tenía 3.781 imágenes: 2.513 con clase mapeada; las otras 1.268 etiquetas se omiten. El dataset completo tenía 5.403 filas: 3.271 mapeadas y 2.132 omitidas. AIG contiene 120.000 imágenes en carpetas mapeadas y 10.000 en `Hoodies`, que se excluyen por no pertenecer al catálogo. Aunque los archivos terminan en `.jpg`, una inspección del contenido encontró 124.042 JPEG, 5.956 WebP y 2 PNG; el pipeline determina el MIME por el contenido real y conserva intactos los bytes. Ninguna de las 130.000 imágenes AIG supera 200.000 bytes (máximo observado: 92.069 bytes). Estos son conteos de inventario, no el número de imágenes que todavía necesitan análisis. Los totales se pueden volver a generar con `audit`.

La configuración/mapeos editables están en [`sources.json`](./sources.json). El pipeline solo procesa etiquetas incluidas explícitamente en el mapeo: carpetas o filas fuera de la taxonomía no se copian ni se envían a una API. Las imágenes de más de **200.000 bytes (0,2 MB decimal)** también se excluyen; no se reducen, convierten ni recomprimen antes del envío. Los ZIP originales locales se conservan y `datos-crudos/` está excluido de Git.

## Arquitectura mínima

- [`compose.yml`](./compose.yml): servicio efímero `curator`; monta `datos-crudos/` en solo lectura y el dataset SQLite/carpeta del proyecto en escritura.
- [`Dockerfile`](./Dockerfile): Python 3.12 con Pillow y Requests.
- [`app.py`](./app.py): auditoría, mapeo de clases, importación, hash para evitar duplicados, cache por configuración y anotación visual opcional con fallback de proveedor/modelo.
- [`sources.json`](./sources.json): directorios, licencia declarada, clases que se admiten y mapeos al catálogo actual.
- [`.env.example`](./.env.example): plantilla de un único `.env` con las tres claves y configuraciones de proveedor; el `.env` real está excluido de Git.
- El esquema compartido contiene `descripcion_prenda` y `analisis_imagen`: anotaciones revisables y cache de decisiones por hash/clase/proveedor/modelo/versión de prompt.
- `prenda_imagen.etiqueta_fuente` conserva la etiqueta original (por ejemplo `Polo`) junto a la categoría canónica (por ejemplo `camisa`).
- Durante el procesamiento, las categorías `camisa` y `camiseta` se normalizan a la clase canónica `camisa`; la etiqueta original de la fuente se conserva para trazabilidad.
- [`dashboard.py`](./dashboard.py) y [`dashboard.html`](./dashboard.html): panel local para monitorear prendas por tipo y últimas importaciones, iniciar y detener lotes desde el navegador con estado y registro en vivo, y cambiar prompt, vocabularios y proveedor/claves.

Una imagen fuente produce inicialmente una carpeta/prenda en `dataset/`. Se conserva la partición si el path tiene `train`, `validation`/`val` o `test`; si no, se asigna determinísticamente por hash. El registro queda `pendiente` y `apta_para_entrenamiento=0`. Para llamadas remotas, la IA valida si la imagen corresponde a la clase fuente y puede descartarla antes de copiarla. Las imágenes aceptadas se importan con anotación pendiente; color/estilo sugeridos se guardan en `descripcion_prenda.atributos_sugeridos` y `valor_propiedad_prenda`, pero la prenda sigue pendiente y no es apta para entrenamiento. Una persona debe revisar y aprobarlas antes de entrenar.

Cada respuesta válida se guarda en `analisis_imagen`, tanto si acepta como si descarta la muestra. Al repetir la ejecución con la misma imagen, clase canónica, proveedor, modelo y versión del prompt, se reutiliza esa decisión y se evita otra llamada. Un análisis aceptado también queda protegido contra duplicación por SHA-256 en `prenda_imagen`. Si cambia proveedor/modelo o se incrementa la versión del prompt, la huella cambia intencionalmente.

## Proveedores de visión y secretos

El comando de ingesta selecciona **un proveedor principal** por ejecución; desde el dashboard es posible lanzar NVIDIA NIM y DeepSeek en paralelo como lotes independientes. La política de respaldo también puede llamar al otro proveedor: NIM consulta DeepSeek si descarta una imagen cuando está habilitado, y DeepSeek consulta NIM si falla. El mismo archivo `.env` aloja las claves de los tres proveedores. Copia `.env.example` a `.env` y completa solo las credenciales que vas a utilizar:

| Proveedor | Valores orientativos |
|---|---|
| OpenAI API con visión | `ANNOTATION_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL` y `OPENAI_BASE_URL` |
| NVIDIA NIM en nube | `ANNOTATION_PROVIDER=nim`, `NVIDIA_NIM_API_KEY`, `NVIDIA_NIM_MODEL`, `NVIDIA_NIM_FALLBACK_MODELS` y `NVIDIA_NIM_BASE_URL`; el modelo visual principal predeterminado es `nvidia/nemotron-3.5-super-vl-120b-a12b`, un modelo multimodal de NVIDIA disponible en NIM. Se usa el endpoint hospedado por defecto; acceso y cuota dependen de la cuenta. |
| DeepSeek | `ANNOTATION_PROVIDER=deepseek`, `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` y `DEEPSEEK_BASE_URL`; selecciona un modelo/end-point que admita imágenes. Considerarlo servicio de pago. |

El contexto estructurado del prompt se expresa en **TOON** para reducir verbosidad. El sobre de Chat Completions sigue siendo JSON —es el formato de transporte que exigen las API compatibles— y se solicita JSON como salida para validar y almacenar respuestas. DeepSeek usa `response_format=json_object`, empieza con 1.024 tokens y, ante contenido vacío o truncado (`finish_reason=length`), se reintenta una vez con 2.048 tokens. DeepSeek también inicia con el modo de razonamiento desactivado (`thinking.type=disabled`), porque el modo de razonamiento puede consumir el límite de salida antes de producir el JSON. Su documentación advierte que JSON Output puede devolver contenido vacío y recomienda incluir JSON y un ejemplo; el prompt contiene ambos. Fuentes: [JSON Output de DeepSeek](https://api-docs.deepseek.com/guides/json_mode) y [Thinking Mode de DeepSeek](https://api-docs.deepseek.com/guides/thinking_mode). La [documentación de NIM](https://docs.api.nvidia.com/nim/reference/llm-apis) define `POST /v1/chat/completions`, pero no anuncia un límite universal de peticiones por segundo para todas las cuentas.

NIM segmenta cada imagen en cuatro solicitudes visuales con `response_format=json_object`: **colores**, **estilos**, **temporadas** y **validación de clase/descripción**; el curador combina los resultados en una anotación. Cada etapa empieza con 256 tokens y reintenta una vez con 512 si el JSON está malformado o no tiene la estructura esperada. El modo de razonamiento se desactiva en `nvidia/nemotron-3.5-super-vl-120b-a12b` (`reasoning_effort=none`) para priorizar respuestas cortas con el formato solicitado. El modelo visual anterior, `meta/llama-3.2-11b-vision-instruct`, sigue seleccionable en `NVIDIA_NIM_MODEL`, pero la base local muestra que produjo reintentos de formato en el lote más reciente. La [tarjeta oficial de Nemotron 3.5 Super VL](https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b.md) indica soporte de texto e imágenes y la [referencia NIM](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3_5-super-vl-120b-a12b-infer) muestra `reasoning_effort: none` en una solicitud visual. Este cambio de modelo es una configuración recomendada, no una garantía de disponibilidad o calidad; verifica primero que la cuenta tenga acceso.

Si un modelo NIM falla por HTTP/red, timeout o respuesta inválida, el mismo análisis se intenta automáticamente con el siguiente modelo de `NVIDIA_NIM_FALLBACK_MODELS`. El modelo principal predeterminado es `nvidia/nemotron-3.5-super-vl-120b-a12b`; la cadena de respaldo predeterminada es `meta/llama-3.2-11b-vision-instruct`, `meta/llama-3.2-90b-vision-instruct` y `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, verificados con una llamada real. El catálogo `/models` lista modelos que la cuenta no puede invocar (por ejemplo Gemma 3, Phi-3 Vision, VILA, NeVA, Kosmos-2 y Kimi devuelven HTTP 404 "Function … Not found for account"), así que hay que sondear antes de añadir modelos. Llama 11B a veces responde en prosa en vez de JSON; el parser extrae el primer objeto JSON y, si no hay, registra un fragmento de la salida. El acceso de catálogo no garantiza disponibilidad permanente, cuota ni calidad; errores detectados en un lote hacen que el modelo quede fuera de servicio para el resto de esa ejecución. Si una alternativa funciona, se guarda el modelo efectivo y se prioriza para las imágenes restantes. Se puede ajustar la lista separada por comas en `.env`. Si todos los modelos NIM se agotan, el lote termina con un error explícito en vez de repetir los mismos modelos en cada imagen.

Solo se conservan colores exactos del catálogo; se permiten hasta dos valores observables por lista de estilo y temporada, incluidos valores nuevos. Los estilos y temporadas nuevos se agregan al catálogo SQLite cuando una API los responde, incluso si la imagen queda descartada. Se descartan valores de color desconocidos, pero no se rechaza toda la imagen por proponer un estilo o temporada nuevos. Una etapa que continúe inválida después del reintento se reporta y no guarda el análisis; el pipeline prueba entonces el siguiente modelo NIM disponible. Se mantiene una separación mínima de **3 segundos entre inicios de solicitudes NIM**; cuatro etapas equivalen a un máximo teórico cercano a **5 imágenes por minuto**, sin contar latencia ni reintentos. Ante un timeout, cada modelo NIM espera un tiempo aleatorio de **30 a 120 segundos** y reintenta una vez la misma imagen antes de avanzar al siguiente modelo. Una respuesta tardía podría haber sido procesada/cobrada, así que cada reintento puede duplicar consumo. Las claves de análisis de NIM usan una versión separada para evitar reutilizar resultados previos a la segmentación sin invalidar el cache de DeepSeek.

Las imágenes se envían en su formato y bytes originales como data URL; el MIME se detecta por el contenido y no se redimensionan, recodifican ni recomprimen. Solo se aceptan contenidos JPEG, PNG, GIF y WebP para anotación remota. `motivo_descarte: null` se normaliza a texto vacío solo para imágenes aceptadas. Una respuesta inválida prueba los modelos/proveedores de respaldo disponibles; si un análisis agota todos los modelos NIM, no se guarda para esa imagen y los modelos fallidos se excluyen del resto del lote. Si no queda ningún modelo NIM, el proceso se detiene y muestra un error claro en vez de seguir facturando reintentos inútiles. DeepSeek se intenta una vez por imagen antes de activar NIM; cada modelo NIM conserva su propio reintento ante timeout.

Para reducir respuestas largas de NIM, solo ese proveedor recibe instrucciones más estrictas: descripciones y motivos de descarte de hasta **8 palabras**, y un máximo de **2 colores, 2 estilos y 2 temporadas**. DeepSeek conserva sus límites previos de 12 palabras y hasta 3 valores por lista. Si DeepSeek falla por HTTP/red, timeout o respuesta inválida, el mismo análisis se intenta automáticamente con NVIDIA NIM cuando la clave está configurada; los resultados se guardan bajo el proveedor/modelo que efectivamente respondió. Si NIM no está configurado, el error se informa y la imagen no se presenta como procesada. En sentido inverso, una respuesta válida de descarte de NIM (no un error) puede iniciar una evaluación adicional de DeepSeek cuando esté configurado; si DeepSeek la acepta, se importa y la descripción queda atribuida a ese proveedor. Se conservan ambos análisis válidos en SQLite para auditar la diferencia. Si DeepSeek también descarta, la imagen se mantiene descartada. Al seleccionar NIM y DeepSeek en paralelo desde el dashboard, se desactiva únicamente el fallback automático NIM→DeepSeek para evitar duplicar esa evaluación; el lote DeepSeek independiente sigue teniendo su respaldo a NIM ante fallo. Los fallbacks usan imágenes en otro modelo/proveedor y pueden sumar llamadas/costos fuera del cupo inicial. La confirmación remota del dashboard advierte este envío cruzado. En “Prendas incorporadas y descartadas”, el dashboard separa las incorporadas y las descartadas por proveedor. Para análisis antiguos que no registraban la ruta original, busca la imagen fuente por su hash SHA-256. El panel “Resultados válidos por modelo” cuenta los análisis guardados en SQLite, separados en aceptados y descartados; una respuesta inválida que no se guarda no se suma a esos totales. Los registros de lote se muestran por proveedor, se pueden congelar visualmente sin pausar inferencias y permiten borrar las líneas clasificadas como errores sin borrar análisis de SQLite.

No pongas claves en `compose.yml`, argumentos de shell, SQLite ni commits. No se envían etiquetas sin mapeo, imágenes >200.000 bytes ni formatos incompatibles. Antes de aplicar `--limit`, la ingesta quita hashes que ya están en el dataset y repeticiones dentro del plan; por eso las siguientes ejecuciones avanzan a imágenes nuevas en vez de volver a seleccionar las primeras ya importadas. El registro informa cuántas duplicadas se omitieron antes de la IA. Para usar APIs remotas se requieren explícitamente `--allow-remote`, `--limit` y `--execute`. Los errores HTTP/red del proveedor detienen el lote; respuestas de IA con estructura inválida se omiten y el lote continúa.

## Uso seguro y reproducible

La suite automatizada local y las etapas de validación están descritas en [`PLAN-PRUEBAS.md`](./PLAN-PRUEBAS.md). Ejecuta primero sus pruebas sin red ni credenciales.

Levanta la interfaz en localhost:

```bash
docker compose up -d dashboard
```

Abre `http://127.0.0.1:8787`. El servicio usa la red del host porque el reenvío IPv4 de Docker está deshabilitado en este equipo; el servidor se enlaza estrictamente a `127.0.0.1` y no se publica en la red local. En **Procesar imágenes ahora**, elige **Todas las fuentes elegibles (recomendado)** o limita el procesamiento a una fuente, uno o ambos proveedores y un máximo de **1–15.000 imágenes nuevas por proveedor principal**. El máximo se aplica después de quitar hashes ya importados, duplicados dentro del plan y análisis vigentes para el proveedor/modelo/configuración actuales. Análisis aceptados cacheados pero aún no importados se recuperan sin consumir el límite. La lista principal de candidatos de cada proveedor se limita por separado; una llamada de respaldo a otro modelo/proveedor puede exceder ese conteo. NIM y DeepSeek pueden ejecutarse en paralelo como procesos independientes; cada uno muestra estado, registro y botón de detención. Las fuentes seleccionadas pueden solaparse y la misma imagen puede ser enviada a ambos. Para importar localmente debes confirmar la escritura en el dataset y SQLite. Para cualquier llamada remota —incluyendo fallbacks— debes autorizar expresamente el envío y configurar las claves correspondientes. **Detener envío** pide cancelar el proveedor seleccionado; permite terminar la petición actual, pero evita nuevas solicitudes una vez que el proceso atiende la señal. No se ejecuta ningún lote automáticamente al abrir la página.

Las claves se capturan como campos tipo password, nunca se devuelven al navegador y se escriben en `.env` con permisos privados. El prompt y las listas de color/estilo/temporada se guardan en SQLite. Cambiar prompt, modelo, categoría o vocabulario produce una huella de análisis distinta para que el cache no reutilice un resultado obsoleto. El estimado a 5.000 requiere historial suficiente; antes el panel lo indica sin inventar un tiempo.

Si un lote termina con `El destino ya existe y no está registrado`, el importador ahora compara el SHA-256 del archivo existente con el original. Si coinciden, reutiliza el archivo y completa su registro en SQLite sin volver a copiarlo; si difieren, se detiene y conserva ambos contenidos. Reintenta desde el dashboard: cuando el análisis aceptado sigue en cache para el mismo proveedor, modelo y prompt, se importa sin otra llamada remota. No se relanza un lote automáticamente tras un error.

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

Si una solicitud remota expira, puede haberse realizado una llamada facturable aunque no llegue respuesta. Para cada modelo NIM el curador espera aleatoriamente 5–15 segundos y reintenta una vez la misma imagen; si se agotan los modelos, omite esa imagen y continúa. Ante el fallo de DeepSeek puede probarse NIM y su cadena configurada; ante el fallo de un modelo NIM se prueban los siguientes modelos configurados. Estos mecanismos pueden volver a enviar la misma imagen y generar consumo adicional. **Detener envío** no interrumpe una petición que el proveedor ya esté procesando; el proceso espera a que concluya y luego cancela. Revisa el uso en el proveedor antes de volver a ejecutar un lote.

## ¿Es destilación?

En sentido estricto, **todavía no**. Este flujo importa datos con etiquetas originales y genera *pseudo-etiquetas* y descripciones textuales con un modelo maestro (VLM). Esto se suele llamar curación/anotación asistida por IA o pseudo-labeling. La destilación clásica requiere después entrenar un modelo estudiante con objetivos producidos por el maestro —idealmente distribuciones/logits o supervisión docente definida— y evaluar su transferencia. `descripcion_prenda` guarda texto y sugerencias, no logits; por eso no los presentamos como conocimiento destilado ni los aprobamos automáticamente.

## Decisiones pendientes

Las preguntas restantes se mantienen en [`dudas.md`](./dudas.md): confirmar el tope de gasto de DeepSeek y los criterios de aprobación humana. AIG ya fue localizado, su estructura fue inspeccionada y se habilitó con las clases canónicas compatibles; `Hoodies` se excluye.

## Reparto del lote entre categorías

Al aplicar el límite de imágenes nuevas, el curador no sigue el orden alfabético de las carpetas: prioriza las categorías con menos análisis aceptados hasta igualarlas (por ejemplo suéter, falda, short y pantalón antes que blusa o vestido). Así un lote de 5.000 no se consume solo con las primeras carpetas de AIG.

## Propiedades guardadas en SQLite

Al importar una imagen, los colores, estilos y temporadas propuestos por la IA se guardan en `valor_propiedad_prenda` (sin `unknown`; `summer` y `spring` se normalizan a `verano` y `primavera`), además del JSON de `descripcion_prenda.atributos_sugeridos`. La prenda sigue `pendiente` y sin `apta_para_entrenamiento`, así que `train.py` no la usa hasta que se apruebe. Para rellenar prendas importadas antes de este cambio, o tras un lote que corrió con código viejo:

```bash
docker compose run --rm --no-deps --entrypoint python curator /app/app.py sync-properties
```

## Galería de prendas

`http://127.0.0.1:8787/galeria` (enlace "Galería de prendas" en el monitor) es una vista aparte que muestra
cada imagen con sus propiedades generadas (color, estilo, temporada), descripción, proveedor/modelo, split y estado.
Se navega de 15 en 15 (primera/anterior/números/siguiente/última, ir a página y flechas del teclado) y se puede
filtrar por categoría y proveedor. Los datos salen de `valor_propiedad_prenda` y, como respaldo, de
`descripcion_prenda.atributos_sugeridos`. API: `/api/gallery?page=&category=&provider=`.

## Limpieza de imágenes duplicadas

El dataset de origen (sobre todo `mendeley-aig`) trae la misma foto repetida con pequeñas variaciones, por lo que el
SHA-256 no las detecta. Flujo:

1. `docker compose -f compose.yml run --rm --no-deps --entrypoint python curator /app/app.py find-duplicates [--threshold 2]`
   calcula un dHash de 64 bits por imagen (tabla `imagen_huella`) y agrupa las que están a distancia de Hamming
   <= umbral (tablas `grupo_duplicado` y `grupo_duplicado_miembro`). Es repetible; solo recalcula los grupos pendientes.
   Con umbral 6 el encadenamiento fusiona miles de imágenes distintas, por eso el valor por defecto es 2.
2. `http://127.0.0.1:8787/duplicados` (botón "Duplicados" del monitor) muestra cada grupo. La imagen de mayor resolución
   viene marcada para conservarse; haz clic en otra para cambiarla. "Dejar solo la verde y eliminar el resto" marca las demás
   como `rechazado` con `apta_para_entrenamiento=0` (no borra archivos), "No son duplicadas" descarta el grupo y
   "Deshacer" lo revierte. "Resolver toda la página" aplica la recomendada a los 10 grupos visibles.
3. La galería oculta las prendas rechazadas y `train.py` solo usa aprobadas, así que el grupo deja una sola imagen.

Respaldo previo a la limpieza: `respaldos/dataset-*/` (ignorado por git).

### Borrado masivo de grupos grandes

`app.py purge-duplicates --min-size 4` resuelve los grupos pendientes con al menos 4 imágenes: conserva la de mayor
resolución, rechaza el resto y **borra sus archivos**. Las filas de `prenda_imagen` se conservan (prendas `rechazado`) para que
su SHA-256 siga bloqueando futuras importaciones y análisis, de modo que no se vuelven a revisar. Estos grupos no se pueden
deshacer desde la interfaz; restaura desde `respaldos/`. Los originales de `datos-crudos/` no se modifican.

## Aprobación de lo generado

`app.py approve-generated` pasa a `aprobado` con `apta_para_entrenamiento=1` toda prenda `pendiente` que ya tenga descripción
generada (y aprueba esas descripciones). No toca las `rechazado`. Es repetible: ejecútalo de nuevo cuando terminen los lotes.
Úsalo tras revisar una muestra manual de las descripciones.
