# Validación de documentación e implementación

**Fecha: 23 de octubre de 2026 (UTC).** [Índice](INDICE.md) · [Resumen](<../readme resumen.md>)

## Alcance y criterio

Se revisaron los archivos versionados de documentación, Compose/Dockerfiles, configuración, scripts de entrenamiento, evaluación, predicción, API y curación, handlers HTTP y pruebas existentes. Se contrastaron las guías con el código, el dataset local y artefactos de evaluación. Esta revisión no certifica calidad visual de todas las imágenes, licencias, disponibilidad de proveedores remotos ni rendimiento en producción.

No se modificaron SQLite, imágenes, pesos ni servicios. No se iniciaron entrenamientos, importaciones, llamadas de anotación remota ni purgas. Las suites usan fixtures y directorios temporales. Las primeras pruebas locales de curación fallaron por rutas de importación y por falta de `/app/schema.sql`; la ejecución final se hizo en el contenedor previsto y pasó.

## Actualización: API de una imagen e instalación nativa

Después de la revisión general se actualizó `inference_api.py` a la aplicación 2.0.0: `/v1/predict` recibe únicamente `garment_image` y devuelve descripción y propiedades en el objeto raíz. Se retiraron los campos de combinación de imágenes. La ruta predeterminada al checkpoint se resuelve junto al módulo, lo que permite instalar la estructura mínima sin variables de contenedor.

La instalación directa se verificó en un entorno virtual temporal de Python 3.12 con PyTorch 2.5.1+cpu, torchvision 0.20.1+cpu y las dependencias fijadas del proyecto. `pip check` no encontró incompatibilidades. Las **19 pruebas actuales de entrenamiento/inferencia pasaron**, incluidas cinco pruebas HTTP con un servidor temporal. Una prueba adicional cargó el checkpoint compartido real desde una copia mínima, sin dataset en la carpeta del servicio: `/health` respondió correctamente, OpenAPI exigió solo `garment_image` y el envío de una fotografía real produjo HTTP 200 con descripción y propiedades. Los procesos temporales se detuvieron al terminar.

El [manual DOCX APA 7](Instalacion_nativa_API_prendas_APA7.docx) y su [fuente de instalación](INSTALACION-NATIVA.md) describen el procedimiento. Se comprobó el formato del Word mediante renderizado a PDF. No se sustituyeron servicios existentes: requieren reiniciarse con código actualizado. La evidencia de Docker que sigue corresponde a la revisión anterior al cambio de contrato.

## Evidencia comprobada

| Comprobación | Resultado |
|---|---|
| Docker | Compose disponible; contenedores monitor, dashboard y API CPU en ejecución |
| Configuración Compose | Los tres archivos pasan `docker compose ... config --quiet`, incluidos perfiles de entrenamiento |
| HTTP monitor | `/`, `/api/status`, `/api/models`: 200 |
| HTTP dataset | `/`, `/api/overview`, `/api/gallery?page=1`, `/api/duplicates`: 200 |
| HTTP API CPU | `/health`: 200; informa `status=ok`, `device=cpu` |
| Suite entrenamiento/inferencia | **14 pruebas, OK** en la revisión inicial; **19 actuales, OK** en entorno nativo |
| Suite curación/duplicados | **61 pruebas, OK**, dentro del contenedor dashboard |
| SQLite, estructura física | `PRAGMA quick_check`: `ok` |
| SQLite, relaciones | `PRAGMA foreign_key_check`: **15.066 incidencias**, todas en `grupo_duplicado_miembro` hacia `grupo_duplicado` |
| Imágenes aprobadas | 14.456 registradas; ninguna ausente |
| Imágenes totales | 43.593 registradas; 9.939 sin archivo, todas de prendas rechazadas |
| Checkpoint compartido | SHA-256 coincide con el publicado en su README |
| Métricas publicadas | Coinciden con el JSON local `modelo-ia/evaluaciones/evaluacion_propiedades_test.json`, generado el 23-10-2026 |

La comprobación de páginas se realizó por HTTP y lectura del HTML y código, sin una sesión de interacción visual de navegador. Los POST de producción no se ejecutaron: sus contratos se contrastaron con los handlers y los tests. Que las suites pasen no implica ausencia de defectos ni prueba de carga.

## Estado del dataset consultado

| Estado | train | val | test | Total |
|---|---:|---:|---:|---:|
| Aprobado y apto | 11.616 | 1.416 | 1.424 | 14.456 |
| Pendiente y no apto | 9.718 | 1.221 | 1.191 | 12.134 |
| Rechazado y no apto | 13.609 | 1.682 | 1.716 | 17.007 |
| Total | 34.943 | 4.319 | 4.331 | 43.593 |

Se abrió SQLite con URI `mode=ro`. Se verificaron existencia de rutas e integridad relacional, sin decodificar cada imagen ni recalcular todos los hashes. Los archivos faltantes de rechazados son compatibles con `purge-duplicates`, que conserva filas de bloqueo; no se reconstruyó la causa de cada eliminación. Los huérfanos de grupos requieren investigación y reparación independiente con respaldo: `quick_check=ok` no implica integridad de claves foráneas.

El esquema base tiene siete tablas funcionales. `duplicates.py` añade `imagen_huella`, `grupo_duplicado` y `grupo_duplicado_miembro`; la base local también tiene la tabla interna `sqlite_sequence`.

## Modelo y resultados

Archivo compartido: `utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt`.

SHA-256: `79407f5537418bc258857fa54723d8e39b152505ad3a6f6a6ea4f97e1dfcb35c`.

El JSON de evaluación existente registra 1.424 imágenes test, época 15, CPU y umbral 0,5. Sus componentes son tipo 94,94 %, Jaccard de color 68,42 %, Jaccard de estilo 69,21 % y macro 77,52 %. Se verificaron los artefactos; no se repitió la evaluación completa. El checkpoint carece del estado de optimizador/scheduler para una reanudación exacta.

Las limitaciones sobre etiquetas de IA, desbalance, casi duplicados y dominio visual están en [evaluación](../EVALUACION-ENTRENAMIENTO.md). El análisis previo de casi duplicados y su cifra de sensibilidad se conservan como evidencia reportada; no se recalcularon aquí. La diferencia de métricas entre modelos no dispone de prueba de significancia estadística.

## Correcciones y orden documental

- README principal sustituido por una entrada al sistema implementado, con las dos interfaces y sus instrucciones.
- Resumen nuevo de cuatro bloques imprimibles y navegación global mediante un índice de todos los Markdown del repositorio.
- Separación explícita de guías operativas, teoría, evaluaciones y antecedentes; se conservaron rutas para mantener referencias.
- Estados antiguos de cero muestras entrenables y ausencia de modelo identificados como históricos; cifras actuales contrastadas con SQLite.
- Diferenciación entre siete tablas base y extensiones de duplicados; entre metadatos de temporada y salidas reales del modelo.
- Corrección de la afirmación de instalación de dependencias sin red: el Dockerfile usa pip al construir.
- Límite de lote del panel documentado como 15.000 por proveedor, distinto del objetivo de 5.000.
- Tiempo de espera tras timeout NIM en el plan de pruebas corregido a 5–15 segundos, según constantes actuales.
- Aprobación masiva diferenciada de revisión humana individual; descripción de sugerencias persistidas alineada con el código.
- Referencia centralizada de endpoints, incluidas protecciones de POST y diferencias de formato de predicción.

## Repetir las verificaciones

Desde la raíz, validar navegación local y cobertura del índice:

```bash
python3 docs/validar_documentacion.py
docker compose -f utilidades-entrenamiento/docker-compose.yaml --profile gpu --profile monitor --profile monitor-gpu config --quiet
docker compose config --quiet
docker compose --profile tools config --quiet
```

Con los contenedores actuales en marcha (los nombres pueden variar según el proyecto Compose):

```bash
docker exec modelo-reconocimiento-prendas-monitor-1 python -m unittest discover -s /app/tests -v
docker exec modelo-reconocimiento-prendas-dashboard-1 python -m unittest discover -s /app/tests -v
curl --fail-with-body http://127.0.0.1:8090/api/models
curl --fail-with-body http://127.0.0.1:8787/api/jobs
curl --fail-with-body http://127.0.0.1:8081/health
sha256sum utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt
```

Para imágenes o relaciones, abrir `dataset/metadata.sqlite` en solo lectura y ejecutar `PRAGMA quick_check`, `PRAGMA foreign_key_check` y agrupaciones por estado/split. Los valores son instantáneas: repetir estas consultas después de nuevas importaciones o limpiezas. No usar el script de inicialización para auditar una base sin escribir: ese script crea tablas y puede aplicar migraciones aditivas.

La comprobación final de navegación cubrió todos los documentos Markdown y sus enlaces locales, sin destinos ni anclas rotos y con todos los documentos incluidos en el índice.

## Pendientes técnicos identificados

1. Investigar y sanear los miembros de grupos huérfanos, con respaldo y comprobación de que se conserva la trazabilidad de duplicados.
2. Verificar permisos de uso y la calidad de etiquetas mediante revisión independiente; `train.py` no audita documentos de licencia.
3. Evitar casi duplicados entre splits antes de la próxima evaluación y mantener un test independiente de nuevas decisiones de ajuste.
4. Medir GPU real, tiempos, memoria y concurrencia en el entorno final. El servicio CPU reutiliza una imagen PyTorch con CUDA, aunque la inferencia se ejecuta en CPU.
5. Validar proveedores remotos en una prueba acotada autorizada si se retoma la anotación; los nombres configurados no acreditan disponibilidad del proveedor.
