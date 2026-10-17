# Plan de pruebas del pipeline de curación

El objetivo es verificar desde la inspección de fuentes hasta la importación, el cache de análisis, la revisión pendiente y el comportamiento de las APIs. Las pruebas automatizadas no hacen llamadas externas ni utilizan el dataset productivo.

## 1. Pruebas automáticas locales

Construir la imagen y ejecutar la suite dentro del contenedor:

```bash
docker compose build curator
docker compose run --rm --no-deps --entrypoint python curator -m unittest discover -s tests -v
```

Cobertura:

- La huella del análisis es determinista y separa proveedor, modelo, clase e imagen.
- Un análisis aceptado guardado se reutiliza; no se vuelve a invocar al modelo.
- Un descarte guardado también se reutiliza; no se vuelve a enviar ni importar.
- Una anotación nueva queda registrada y la siguiente ejecución omite la imagen ya importada.
- Carpetas sin clase canónica y archivos por encima de 200.000 bytes no entran en el plan.
- La imagen se envía sin modificar sus bytes y el MIME coincide con su formato real.
- El prompt guardado y los vocabularios de propiedad quedan disponibles para el siguiente proceso de curación.
- Ambos proveedores pueden proponer estilos y temporadas nuevos; los valores se fusionan sin duplicados en el catálogo incluso si la imagen se descarta. Los colores no admiten valores fuera de su catálogo.
- El dashboard agrupa por proveedor/modelo las respuestas válidas guardadas, con conteos apta/descartada y fecha más reciente. Los resultados inválidos se mantienen visibles en el registro del lote, pero no se cuentan como respuestas válidas.

Resultado esperado: todos los tests pasan; ningún test conoce ni carga API keys.

## 2. Auditoría de fuentes (solo lectura)

```bash
docker compose run --rm curator audit
```

Comprobar en AIG: 130.000 archivos, 120.000 mapeados, 10.000 omitidos en `Hoodies` y cero archivos mayores de 200 KB. Las demás fuentes deben mostrar sus conteos actuales. Esta fase no crea filas ni hace peticiones remotas.

## 3. Ensayo de selección (dry-run)

```bash
docker compose run --rm curator ingest --source mendeley-aig --provider none --limit 5
docker compose run --rm curator ingest --source clothing-full --provider none --limit 5
```

El comando informa cuántas imágenes están en el plan y termina en “Ensayo solamente”. No copia imágenes, no escribe SQLite y no contacta servicios.

## 4. Importación local acotada, sin API

Probar primero en una copia temporal del dataset/SQLite, no en la carpeta productiva. Importar una imagen con `--provider none --execute --limit 1`; verificar `prenda`, `prenda_imagen`, `etiqueta_fuente`, `valor_propiedad_prenda`, hash SHA-256, ruta y split. Debe quedar `pendiente` y `apta_para_entrenamiento=0`. Repetir el mismo comando: el hash debe evitar duplicar la muestra.

## 5. Prueba remota manual, opcional y con costo/cuota

Solo ejecutar tras confirmar endpoint y disponibilidad de un modelo visual en la cuenta. NIM y DeepSeek se prueban por separado, una imagen cada vez, con una fuente/montaje de prueba aislado:

```bash
docker compose run --rm curator ingest \
  --source mendeley-aig --provider nim --allow-remote --limit 1 --execute
```

Antes de ejecutar, verificar que el `.env` local contiene la clave del proveedor seleccionado. No imprimirla, ponerla en la línea de comandos ni guardarla en SQLite. Después verificar que `analisis_imagen` contiene una fila con SHA-256, clase, proveedor/modelo, versión del prompt y decisión; una aceptación debe además crear prenda e imagen pendientes, y un rechazo solo el registro de análisis.

Repetir exactamente el comando. El resultado esperado es “análisis reutilizados: 1” (si fue descartado) o “duplicadas omitidas: 1” (si fue aceptado); en ninguno de los casos debe emitirse una segunda llamada al proveedor. Para comprobarlo, contrastar los contadores de uso del proveedor, no registrar ni exponer la clave.

El curador aplica una separación mínima de 3 segundos entre inicios de peticiones NVIDIA NIM. La [documentación oficial](https://docs.api.nvidia.com/nim/reference/llm-apis) confirma el endpoint de chat, pero no publica un RPS universal aplicable a todas las cuentas; un timeout de lectura no prueba por sí solo una respuesta 429 ni un límite de tasa.

## 6. Fallos y recuperación

- Con key/endpoint inválidos, la ejecución debe exponer el error; no marcar una respuesta fallida como procesada.
- Si la llamada API funciona pero falla la escritura de una imagen aceptada, el resultado del análisis permanece cacheado para reintentar la importación sin volver a pagar la inferencia.
- Una respuesta inválida no genera análisis cacheado; la imagen se omite y el proceso prueba las siguientes del lote.
- DeepSeek solicita `response_format=json_object`, 1.024 tokens iniciales y un reintento con 2.048 cuando el contenido está vacío o truncado; además envía `thinking: {type: disabled}` y el prompt incluye JSON y un ejemplo.
- NIM envía cuatro solicitudes por imagen, en orden: colores, estilos, temporadas y validación/descripción. Cada etapa solicita JSON de hasta 256 tokens y reintenta una vez con 512 ante JSON inválido; comprobar que se combinan las cuatro respuestas, los inicios se separan al menos 3 segundos y una detención impide enviar las etapas siguientes.
- El modelo NIM recomendado `nvidia/nemotron-3.5-super-vl-120b-a12b` envía `reasoning_effort=none`; verificar que no se agrega este parámetro a otros modelos. Antes de usarlo en un lote grande, probar una muestra pequeña y comprobar que está habilitado para la API key.
- La salida NIM distingue JSON malformado de JSON sintácticamente válido con una estructura incorrecta, e incluye etapa, `finish_reason` y longitud en el log sin imprimir todo el contenido de la respuesta.
- Con DeepSeek configurado, un descarte NIM debe iniciar una evaluación DeepSeek usando su propio fingerprint/cache. Si DeepSeek acepta, importar con proveedor/modelo DeepSeek; si también descarta, conservar ambos análisis y no importar. Sin clave DeepSeek, mantener el descarte NIM y mostrarlo explícitamente. Si ambos proveedores se seleccionan en paralelo, comprobar que no se dispara una llamada fallback redundante desde el proceso NIM.
- NIM debe realizar cuatro etapas: colores, estilos, temporadas y validación/descripción. Debe pedir un máximo de 8 palabras en descripción y motivo de descarte, y máximo 2 valores por propiedad. Verificar que colores fuera del catálogo se ignoran, estilos/temporadas nuevos se conservan, y el resultado combinado respeta esos límites. DeepSeek debe conservar estilos/temporadas nuevos, restringir colores al catálogo y mantener descripción de hasta 12 palabras y hasta 3 valores por lista.
- Tras responder una anotación, comprobar que estilo/temporada nuevos se guardan en `catalogo_propiedad`; en imágenes incorporadas, las sugerencias quedan también en `atributos_sugeridos`. El catálogo de color no cambia. El siguiente análisis debe recibir el catálogo actualizado en su prompt.
- Mocks de ambos proveedores: una primera respuesta vacía/truncada seguida de JSON válido debe devolver anotación válida y demostrar el aumento de tokens; dos respuestas incompletas deben omitir la imagen sin guardarla y continuar el lote.
- Dos inicios consecutivos de solicitudes NIM se separan como mínimo 3 segundos. Ante timeout, el proceso espera un intervalo aleatorio entre 30 y 120 segundos y reintenta la misma imagen exactamente una vez; si el segundo intento también expira, la omite y pasa a la siguiente muestra. Verificar orden de imágenes, espera y que solo se persista una decisión válida.
- Con hashes ya importados al inicio del inventario, un límite de lote pequeño debe saltarlos antes de contar candidatos; el mismo tamaño de lote debe avanzar hasta llenar el cupo con imágenes nuevas. El resumen debe reportar las duplicadas omitidas antes de IA.
- `motivo_descarte: null` se normaliza a cadena vacía solo para imágenes aceptadas; otros tipos inválidos se omiten sin frenar el lote.
- La prueba de rollback/importación se hace solo en dataset temporal; nunca simular fallos destructivos contra `dataset/metadata.sqlite`.

## 7. Panel de monitoreo

Levantar el servicio localmente y abrir `http://127.0.0.1:8787`:

```bash
docker compose up -d dashboard
```

Comprobar:

- Los totales y conteos por clase coinciden con consultas de SQLite.
- “Resultados válidos por modelo” coincide con un `GROUP BY proveedor, modelo` de `analisis_imagen`; aceptadas y descartadas suman el total válido y no se exponen API keys.
- La sección de actividad muestra las últimas cinco prendas, propiedades, descripciones y proveedor/modelo; no hay imágenes si aún no se han importado.
- Las pestañas muestran incorporadas y descartadas de cada proveedor. Las imágenes descartadas se resuelven por su ruta guardada o, para análisis antiguos, por el hash SHA-256 en las fuentes crudas.
- La confirmación de envío remoto indica que NIM puede reenviar descartes a DeepSeek y que esto puede agregar costo/uso de imágenes.
- La estimación queda como “sin datos” con menos de dos marcas de tiempo medibles y pasa a duración cuando existe una tasa válida.
- Guardar un prompt cambia la vista previa y el valor persistido en `pipeline_config`; el prompt nuevo cambia la huella del análisis.
- Cambiar vocabularios modifica `catalogo_propiedad`, y el prompt siguiente contiene esos valores.
- El modal de propiedades expone y permite editar colores, estilos y temporadas. Los nuevos valores de estilo/temporada detectados aparecen allí aunque se haya descartado la imagen.
- El modal de credenciales indica presencia de claves sin revelar sus valores. Reemplazar una key debe conservar campos vacíos, actualizar `.env` con modo 600 y no incluir el secreto en respuestas o logs.
- Solicitudes POST con host/origen ajeno son rechazadas; las claves no existen en SQLite.
- El servicio está publicado en `127.0.0.1`, no en `0.0.0.0` del host.
- La tarjeta **Procesar imágenes ahora** ofrece solo fuentes importables, inicia hasta dos lotes en paralelo (uno por proveedor remoto), cada uno con límite de 1–5.000 imágenes, y presenta estado/salida por separado.
- Con NIM y DeepSeek seleccionados, validar que se crean dos procesos independientes con el mismo límite y que cada uno llama solo a su proveedor.
- Enviar ambos proveedores sobre imágenes comunes y verificar que una imagen se incorpora una sola vez aunque los dos procesos terminen su análisis; la escritura SQLite debe serializarse y el segundo importador debe registrar el duplicado.
- **Detener envío** solicita la cancelación solo al proceso proveedor elegido; el estado pasa a “detención solicitada” y luego “detenido”. Una solicitud ya activa puede finalizar/importarse, pero no se inicia otra. Si se detiene durante el backoff de timeout, no se reintenta ni se avanza a otra imagen. La otra ejecución en paralelo debe continuar.
- Sin IA exige confirmación de escritura; NIM/DeepSeek además requieren clave configurada y autorización explícita de envío remoto. OpenAI permanece fuera de la selección hasta habilitarlo por separado.
- Un segundo lote del mismo proveedor se rechaza mientras ese proveedor siga activo; se permite lanzar el otro proveedor en paralelo. Errores y claves deben estar ausentes de cualquier registro mostrado.

## Criterios de aceptación

1. La suite automatizada pasa sin red y sin credenciales.
2. Dry-run y auditoría no alteran el dataset ni SQLite.
3. La importación repetida no duplica la imagen.
4. Una decisión de IA válida no se vuelve a consultar para la misma huella de imagen/clase/proveedor/modelo/versión de prompt.
5. No se importan imágenes de clases fuera del mapeo ni mayores de 200.000 bytes.
6. Las muestras aprobadas por la IA continúan pendientes de revisión humana y no habilitadas para entrenamiento.
7. El dashboard solo responde en localhost, las claves se ocultan y los cambios de prompt/vocabulario afectan los procesos futuros.
8. Cada proveedor acepta un límite de hasta 5.000 prendas; al seleccionar NIM y DeepSeek se inician trabajos paralelos independientes.
9. La importación concurrente de un mismo hash crea una sola prenda y una sola imagen registrada en SQLite.
