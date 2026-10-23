# Reconocimiento de prendas — V2

Sistema Docker para construir un dataset de prendas, entrenar MobileNetV3-Small y ejecutar inferencia de **tipo, colores y estilos**. Revisión documental: **23 de octubre de 2026**.

- [Resumen del proyecto: unas cuatro páginas](<readme resumen.md>).
- [Índice completo de documentación](docs/INDICE.md).
- [Validación técnica, evidencia y hallazgos](docs/VALIDACION.md).
- [Referencia de endpoints](docs/API.md).
- [Instalación sin Docker](docs/INSTALACION-NATIVA.md) · [Manual DOCX APA 7](docs/Instalacion_nativa_API_prendas_APA7.docx).

## Las dos interfaces

| Interfaz | Dirección local | Función | Implementación |
|---|---|---|---|
| Dataset | http://127.0.0.1:8787/ | Importación, anotación asistida, galería y duplicados | `modelo-general-destilacion/dashboard.py` |
| Entrenamiento | http://127.0.0.1:8090/ | Iniciar/detener, continuar checkpoints, métricas, evaluación e inferencia CPU | `monitor.py` |
| API CPU independiente | http://127.0.0.1:8081/docs | Inferencia de una imagen; contrato OpenAPI | `inference_api.py` |

Las rutas del código de esta tabla son relativas a `utilidades-entrenamiento/`. El servicio `train` es de línea de comandos; el panel es el servicio `monitor`. Las interfaces comparten archivos y SQLite a través de montajes Docker, sin necesitar llamarse entre sí.

## Arranque

Desde la raíz del proyecto, construir la imagen y levantar el monitor CPU:

```bash
docker compose -f utilidades-entrenamiento/docker-compose.yaml build train
docker compose -f utilidades-entrenamiento/docker-compose.yaml --profile monitor up -d monitor
```

Para el panel de dataset, preparar una sola vez su archivo local de configuración si aún no existe y levantarlo:

```bash
cd utilidades-entrenamiento/modelo-general-destilacion
[ -f .env ] || cp .env.example .env
chmod 600 .env
docker compose -f compose.yml up -d --build dashboard
```

Las claves se configuran localmente; no deben versionarse. El panel de dataset usa red del host y escucha en `127.0.0.1:8787`; el monitor publica `127.0.0.1:8090`. En un servidor remoto se accede mediante túnel SSH. Para GPU usa los perfiles indicados en la [guía de entrenamiento](utilidades-entrenamiento/README.md); la reserva GPU requiere driver NVIDIA y Container Toolkit operativos.

## Flujo y estado comprobado

`Fuentes locales → curación/anotación → revisión y aprobación → SQLite + imágenes → entrenamiento → evaluación → checkpoint → inferencia`.

Hay **14.456 prendas aprobadas y aptas**: 11.616 train, 1.416 val y 1.424 test. La importación por sí sola deja muestras pendientes; `approve-generated` permite una aprobación masiva, por lo que el estado aprobado no demuestra una revisión humana individual.

El checkpoint compartido alcanza **94,94 % en tipo**, **68,42 % Jaccard de color**, **69,21 % Jaccard de estilo** y **77,52 % de promedio macro de propiedades**, según los artefactos de evaluación existentes contrastados durante esta revisión. El macro no equivale a exactitud global. Las etiquetas de color/estilo proceden de IA y se han reportado casi duplicados entre splits: consulta las [limitaciones de la evaluación](EVALUACION-ENTRENAMIENTO.md).

La base tiene registros huérfanos en la gestión de duplicados y archivos ausentes asociados a rechazados; el subconjunto aprobado tiene sus imágenes presentes. Detalle y alcance en [validación](docs/VALIDACION.md).

## Documentación por tarea

| Necesidad | Documento |
|---|---|
| Entender todo el proyecto rápidamente | [readme resumen.md](<readme resumen.md>) |
| Preparar imágenes, metadatos y etiquetas | [Guía del dataset](documentacion_dataset/README.md) |
| Operar curación y proveedores | [Guía de curación](utilidades-entrenamiento/modelo-general-destilacion/README.md) |
| Entrenar, continuar o desplegar inferencia | [Guía de entrenamiento](utilidades-entrenamiento/README.md) |
| Iniciar entrenamiento por terminal | [Inicio rápido](utilidades-entrenamiento/INICIO-RAPIDO.md) |
| Interpretar métricas | [Evaluación](EVALUACION-ENTRENAMIENTO.md) |
| Localizar cualquier documento | [Índice](docs/INDICE.md) |

El alcance es clasificar una misma prenda por imagen o conjunto de vistas. No hay detección de múltiples prendas, segmentación ni salida de temporada. La integración con OpenStack/Kubernetes permanece fuera de esta implementación. Los planes y V1 se conservan como antecedentes y se identifican en el índice.
