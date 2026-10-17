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

## 6. Fallos y recuperación

- Con key/endpoint inválidos, la ejecución debe exponer el error; no marcar una respuesta fallida como procesada.
- Si la llamada API funciona pero falla la escritura de una imagen aceptada, el resultado del análisis permanece cacheado para reintentar la importación sin volver a pagar la inferencia.
- Una respuesta inválida no genera análisis cacheado.
- La prueba de rollback/importación se hace solo en dataset temporal; nunca simular fallos destructivos contra `dataset/metadata.sqlite`.

## 7. Panel de monitoreo

Levantar el servicio localmente y abrir `http://127.0.0.1:8787`:

```bash
docker compose up -d dashboard
```

Comprobar:

- Los totales y conteos por clase coinciden con consultas de SQLite.
- La sección de actividad muestra las últimas cinco prendas, propiedades, descripciones y proveedor/modelo; no hay imágenes si aún no se han importado.
- La estimación queda como “sin datos” con menos de dos marcas de tiempo medibles y pasa a duración cuando existe una tasa válida.
- Guardar un prompt cambia la vista previa y el valor persistido en `pipeline_config`; el prompt nuevo cambia la huella del análisis.
- Cambiar vocabularios modifica `catalogo_propiedad`, y el prompt siguiente contiene esos valores.
- El modal de credenciales indica presencia de claves sin revelar sus valores. Reemplazar una key debe conservar campos vacíos, actualizar `.env` con modo 600 y no incluir el secreto en respuestas o logs.
- Solicitudes POST con host/origen ajeno son rechazadas; las claves no existen en SQLite.
- El servicio está publicado en `127.0.0.1`, no en `0.0.0.0` del host.
- La tarjeta **Procesar imágenes ahora** ofrece solo fuentes importables, inicia lotes de 1–1.000 imágenes y muestra estado/salida mientras refresca los conteos.
- Sin IA exige confirmación de escritura; NIM/DeepSeek además requieren clave configurada y autorización explícita de envío remoto. OpenAI permanece fuera de la selección hasta habilitarlo por separado.
- Un segundo lote se rechaza mientras el anterior siga activo; errores y claves deben estar ausentes de cualquier registro mostrado.

## Criterios de aceptación

1. La suite automatizada pasa sin red y sin credenciales.
2. Dry-run y auditoría no alteran el dataset ni SQLite.
3. La importación repetida no duplica la imagen.
4. Una decisión de IA válida no se vuelve a consultar para la misma huella de imagen/clase/proveedor/modelo/versión de prompt.
5. No se importan imágenes de clases fuera del mapeo ni mayores de 200.000 bytes.
6. Las muestras aprobadas por la IA continúan pendientes de revisión humana y no habilitadas para entrenamiento.
7. El dashboard solo responde en localhost, las claves se ocultan y los cambios de prompt/vocabulario afectan los procesos futuros.
