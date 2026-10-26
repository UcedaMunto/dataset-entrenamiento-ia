# Referencia de endpoints locales

[Índice](INDICE.md) · [Validación](VALIDACION.md) · [Resumen](<../readme resumen.md>)

Referencia contrastada con los handlers del código el **23-10-2026**. Las respuestas JSON son las de la implementación actual; no existe un contrato OpenAPI para los paneles. La API CPU y la API de pruebas publican `/openapi.json` y `/docs`. La validación HTTP realizada fue de consulta; los POST se revisaron mediante código y pruebas automatizadas.

## Monitor de entrenamiento — puerto 8090

Implementación: [`monitor.py`](../utilidades-entrenamiento/monitor.py). Los POST requieren `X-Requested-With: monitor`. Ese encabezado es una protección contra solicitudes de otros sitios, no autenticación de usuarios.

| Método | Ruta | Uso / parámetros |
|---|---|---|
| GET | `/` | Panel HTML |
| GET | `/api/status` | Proceso controlado por el monitor, PID, retorno y log |
| GET | `/api/runs` | Identificadores de ejecuciones |
| GET | `/api/run/{run_id}` | Configuración, métricas, progreso, test y conteos de imágenes |
| GET | `/api/models` | Ejecuciones con checkpoint disponible |
| GET | `/api/eval?run={run_id}&split={split}` | Estado y resultado guardado de evaluación |
| POST | `/api/start` | Iniciar entrenamiento con configuración del contenedor |
| POST | `/api/continue?run={run_id}&strategy={strategy}` | Crear fase desde `best.pt`; `fine_tune` o `heads_only` |
| POST | `/api/stop` | Detener el proceso de entrenamiento gestionado |
| POST | `/api/predict?run={run_id}` | Bytes de una imagen en el cuerpo, máximo 10 MB según mensaje del monitor |
| POST | `/api/eval?run={run_id}&split={split}` | Iniciar evaluación; split `train`, `val` o `test` |

Los IDs de ejecución se validan y deben referir a los artefactos locales. La predicción del monitor recibe bytes, no el multipart de una imagen de la API independiente. Un entrenamiento iniciado fuera del monitor no queda bajo su control de procesos.

Ejemplo de consulta sin iniciar trabajos:

```bash
curl --fail-with-body http://127.0.0.1:8090/api/models
```

## Curación del dataset — puerto 8787

Implementación: [`dashboard.py`](../utilidades-entrenamiento/modelo-general-destilacion/dashboard.py). Acepta Host `localhost` o `127.0.0.1`. Los POST requieren `Origin` HTTP coincidente con Host y `Content-Type: application/json`; el cuerpo debe ser un objeto JSON de 1 byte a 1 MB.

| Método | Ruta | Uso / parámetros |
|---|---|---|
| GET | `/` | Panel principal |
| GET | `/galeria`, `/duplicados` | Vistas auxiliares; admiten barra final |
| GET | `/api/overview` | Totales, fuentes, configuración y propiedades; no devuelve claves |
| GET | `/api/gallery?page=1&category=&provider=` | Galería, 15 prendas por página |
| GET | `/api/duplicates?page=1&estado=pendiente` | Grupos; estados `pendiente`, `resuelto`, `descartado` |
| GET | `/api/jobs` | Estado de trabajos por proveedor |
| GET | `/api/job` | Compatibilidad: estado del trabajo NIM |
| GET | `/api/rejections/{provider}` | Descartes recientes de `nim` o `deepseek` |
| GET | `/api/image/{id_prenda}` | Primera imagen de una prenda; el número es ID de prenda |
| GET | `/api/rejected-image/{sha256}` | Imagen original de un descarte, si se puede resolver |
| POST | `/api/prompt` | Guardar `instructions` |
| POST | `/api/properties` | Guardar listas `color`, `estilo`, `temporada` |
| POST | `/api/credentials` | Actualizar configuración local de proveedores, sin lectura de secretos |
| POST | `/api/ingest` | Lote: `source`, `provider`, `limit`, `confirm_write`, `confirm_remote` |
| POST | `/api/stop` | Solicitar detención cooperativa de `provider` |
| POST | `/api/jobs/clear-errors` | Limpiar errores mostrados del `provider` seleccionado |
| POST | `/api/duplicates/resolve` | Objeto con `groups`: lista de objetos `group_id` y `keep` (ID de prenda a conservar) |
| POST | `/api/duplicates/dismiss` | Descartar agrupación: `group_id` |
| POST | `/api/duplicates/undo` | Deshacer resolución compatible: `group_id` |

`provider` de ingesta admite `none`, `nim` o `deepseek`; el límite por lote del panel es 1–15.000. Los proveedores remotos requieren clave y ambas confirmaciones. La detención espera a que termine la solicitud activa. El flujo de selección de ambos proveedores se describe en la [guía de curación](../utilidades-entrenamiento/modelo-general-destilacion/README.md).

No existe `/api/status` en este panel: consultar `/api/overview` o `/api/jobs`.

```bash
curl --fail-with-body http://127.0.0.1:8787/api/jobs
```

## API independiente CPU — puerto 8081 del host

Implementación: [`inference_api.py`](../utilidades-entrenamiento/inference_api.py). Dentro del contenedor escucha en 8080. No utiliza el dataset para inferir.

| Método | Ruta | Contrato |
|---|---|---|
| GET | `/health` | `{"status":"ok","device":"cpu"}` |
| GET | `/docs`, `/redoc`, `/openapi.json` | Documentación y esquema FastAPI |
| POST | `/v1/predict` | Multipart con un único archivo requerido: `garment_image` |

JPEG, PNG o WebP; máximo 10 MiB y 25 megapíxeles por archivo. Devuelve `descripcion_mas_probable`, `tipo_prenda`, `colores`, `estilos`, `umbral_multietiqueta`, `device` y `latencia_ms`. La descripción se genera con una plantilla de etiquetas. La aplicación 2.0.0 sustituye el contrato anterior de dos imágenes; ya no devuelve campos de combinación. Los errores incluyen 422 para archivos ausentes/ilegibles, 413 para tamaños excesivos y 415 para formatos no admitidos.

Arranque y ejemplo de petición: [guía de despliegue CPU](../utilidades-entrenamiento/README.md#api-de-inferencia-en-una-vm-con-cpu).

Instalación directa con Python: [guía nativa](INSTALACION-NATIVA.md) y [manual DOCX APA 7](Instalacion_nativa_API_prendas_APA7.docx). En instalación nativa se recomienda enlazar `127.0.0.1:8081` con Uvicorn.

## API de pruebas (DSR) — puerto 8082 del host

Implementación: [`test_api.py`](../utilidades-entrenamiento/test_api.py). Ejecuta la prueba de la API de descripción de prendas sobre el conjunto portable [`tests/imagenes-test/`](../tests/imagenes-test/), sin usar el dataset completo. Diseño: [DSR-PRUEBA-API.md](DSR-PRUEBA-API.md).

| Método | Ruta | Contrato |
|---|---|---|
| GET | `/health` | Estado, checkpoint y total de imágenes del manifest |
| GET | `/docs`, `/openapi.json` | Documentación y esquema FastAPI |
| GET | `/test/design` | Resumen JSON del diseño DSR |
| GET | `/test/design/markdown` | Documento de diseño DSR en Markdown |
| GET | `/test/manifest` | Resumen del manifest: clases, conteos por tipo, sin color/estilo |
| GET | `/test/images?page=1&page_size=50` | Lista paginada de imágenes y etiquetas de referencia |
| POST | `/test/run?max_images=10&device=cpu` | Ejecuta la prueba (completa o limitada) y guarda el reporte |
| GET | `/test/results` | Reportes guardados con su promedio macro |
| GET | `/test/results/{run_id}` | Reporte completo guardado |

`max_images` opcional permite una prueba de humo; `device` admite `cpu` (por defecto) o `cuda`. Los reportes se guardan en `tests/resultados/reporte_*.json` (carpeta ignorada por Git). Ejemplo:

```bash
curl -X POST "http://127.0.0.1:8082/test/run?max_images=10"
curl "http://127.0.0.1:8082/test/results"
```
