# Documentación completa — Reconocimiento de prendas V2

**Documento unificado generado automáticamente.** Reúne, en un solo archivo y en orden lógico, el contenido completo de todos los Markdown del repositorio `UcedaMunto/dataset-entrenamiento-ia`. Sirve como contexto y guía de implementación para otra IA.

Los archivos originales se conservan en el repositorio; este documento es una copia consolidada. Los enlaces apuntan a las rutas reales del repositorio.


## 1. Visión general


### Reconocimiento de prendas — V2

*Fuente: [`README.md`](README.md)*


**Documento único de referencia** del repositorio `UcedaMunto/dataset-entrenamiento-ia`. Unifica el acceso a toda la documentación, las interfaces, el flujo de trabajo y las evidencias del proyecto. Revisión: **2 de noviembre de 2026**.

Sistema Docker para construir un dataset de prendas, entrenar **MobileNetV3-Small** y ejecutar inferencia de **tipo, colores y estilos**. Complemento de IA del artefacto principal (nube privada + Kubernetes + VTON Studio), alineado con **DSRM** (Peffers et al., 2007).

##### 1. Interfaces

| Interfaz | Dirección local | Función | Implementación |
|---|---|---|---|
| Panel de dataset | http://127.0.0.1:8787/ | Importación, anotación asistida (NVIDIA NIM / DeepSeek), galería y duplicados | `modelo-general-destilacion/dashboard.py` |
| Panel de entrenamiento | http://127.0.0.1:8090/ | Iniciar/detener, continuar checkpoints, métricas, evaluación e inferencia CPU | `monitor.py` |
| API CPU independiente | http://127.0.0.1:8081/docs | Inferencia de una imagen; contrato OpenAPI | `inference_api.py` |
| API de pruebas (DSR) | http://127.0.0.1:8082/docs | Ejecuta la prueba de la API sobre `tests/imagenes-test/` | `test_api.py` |

Las rutas de código de esta tabla son relativas a `utilidades-entrenamiento/`. Los cuatro servicios se levantan con el **Compose unificado** de la raíz ([docker-compose.yaml](docker-compose.yaml)).

##### 2. Arranque

```bash
# Configurar el panel de dataset (una sola vez, si no existe)
[ -f utilidades-entrenamiento/modelo-general-destilacion/.env ] || cp utilidades-entrenamiento/modelo-general-destilacion/.env.example utilidades-entrenamiento/modelo-general-destilacion/.env
chmod 600 utilidades-entrenamiento/modelo-general-destilacion/.env

# Levantar las cuatro interfaces
docker compose up -d --build

# Verificación
docker compose ps
curl -s -o /dev/null -w "dataset: %{http_code}\n" http://127.0.0.1:8787/
curl -s -o /dev/null -w "monitor: %{http_code}\n" http://127.0.0.1:8090/
curl -s -o /dev/null -w "inferencia: %{http_code}\n" http://127.0.0.1:8081/docs
curl -s -o /dev/null -w "pruebas: %{http_code}\n" http://127.0.0.1:8082/docs

# Entrenamiento por terminal (alternativa al panel)
docker compose -f utilidades-entrenamiento/docker-compose.yaml build train
docker compose -f utilidades-entrenamiento/docker-compose.yaml run --rm train

# Detener
docker compose down
```

Instrucciones completas en [Instalación Docker](docs/instalacion/INSTALACION-DOCKER.md) · [Instalación nativa sin Docker](docs/instalacion/INSTALACION-NATIVA.md).

##### 3. Flujo y estado comprobado

`Fuentes locales → curación/anotación → revisión y aprobación → SQLite + imágenes → entrenamiento → evaluación → checkpoint → inferencia`.

- **14.456 prendas aprobadas y aptas**: 11.616 train · 1.416 val · 1.424 test.
- Checkpoint compartido (`mobilenetv3-small-best.pt`): **tipo 94,94 %** · **color Jaccard 68,42 %** · **estilo Jaccard 69,21 %** · **promedio macro 77,52 %**.
- El macro no equivale a exactitud global. Las etiquetas de color/estilo proceden de IA y se reportaron casi duplicados entre splits: ver [limitaciones de la evaluación](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md).

##### 4. Mapa completo de la documentación

###### 4.1 Entrada y resumen

| Documento | Propósito |
|---|---|
| [README (este documento)](README.md) | Documento único de referencia del repositorio. |
| [Resumen del proyecto](docs/resumen/RESUMEN-PROYECTO.md) | Resumen ejecutivo de unas cuatro páginas, apto para impresión. |
| [Índice de documentación](docs/INDICE.md) | Mapa detallado por carpetas temáticas. |

###### 4.2 Instalación

| Documento | Propósito |
|---|---|
| [Instalación del sistema completo (Docker)](docs/instalacion/INSTALACION-DOCKER.md) | Interfaces, API, pruebas, entrenamiento y respaldos con el Compose unificado. |
| [Instalación nativa del modelo y su API](docs/instalacion/INSTALACION-NATIVA.md) | Instalación directa con Python y verificación sin contenedores. |
| [Manual Word APA 7](docs/instalacion/Instalacion_nativa_API_prendas_APA7.docx) | Versión editable DOCX de la instalación nativa. |
| [Generador del manual DOCX](docs/instalacion/generar_manual_docx.py) | Script que sincroniza el Word con `INSTALACION-NATIVA.md`. |

###### 4.3 Operación: API y pruebas

| Documento | Propósito |
|---|---|
| [Referencia de endpoints locales](docs/operacion/API.md) | Contratos HTTP de paneles, API CPU y API de pruebas. |
| [Diseño de prueba DSR — API de descripción](docs/operacion/DSR-PRUEBA-API.md) | Prueba de una página basada en Design Science Research. |
| [README-TEST — Ejecutar la prueba](docs/operacion/README-TEST.md) | Guía rápida para correr la prueba con la API. |
| [README-PRUEBA — Cómo se hizo la prueba](docs/operacion/README-PRUEBA.md) | Detalle de ejecución y resultados. |

###### 4.4 Evaluación y evidencias

| Documento | Propósito |
|---|---|
| [Evaluación del clasificador](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md) | Resultados registrados y limitaciones. |
| [Validación de documentación e implementación](docs/evaluacion/VALIDACION.md) | Comprobaciones del 23-10-2026 y pendientes. |
| [Evidencias de integridad (SHA-256)](docs/evaluacion/EVIDENCIAS-INTEGRIDAD-SHA256.md) | Hashes completos para reproducibilidad. |
| [Registro DSR: errores y correcciones](docs/evaluacion/DSR-ERRORES-Y-CORRECCIONES.md) | Errores E1/E2, diagnóstico y verificación. |
| [Registro de entrenamiento 20261029-022656](docs/evaluacion/ENTRENAMIENTO-20261029-022656.md) | Configuración, validación y evaluación del entrenamiento corregido. |
| [Plan de correcciones — Auditoría Anexo G](docs/evaluacion/PLAN-CORRECCIONES-AUDITORIA-ANEXO-G.md) | Plan para atender las 20 observaciones. |
| [Resumen de los últimos 3 entrenamientos (DOCX)](docs/evaluacion/Resumen_Ultimos_3_Entrenamientos.docx) | Comparativo Word de los tres entrenamientos. |
| [Datos para gráficos del entrenamiento](docs/datos-graficos/README.md) | CSV/JSON de métricas por época y resultados de test. |

###### 4.5 Teoría y método

| Documento | Propósito |
|---|---|
| [Teoría del entrenamiento — resumen completo](docs/teoria/TEORIA-ENTRENAMIENTO-COMPLETO.md) | Fundamentos, MobileNetV3, transferencia, pérdidas, optimización y métricas. |
| [Terminología y teoría del entrenamiento](docs/teoria/TEORIA-ENTRENAMIENTO.md) | Referencia conceptual y glosario rápido. |
| [Teoría y conceptos del método de evaluación (DSRM)](docs/teoria/TEORIA-METODO-EVALUACION.md) | Métricas, Jaccard, macro, control y validez. |

###### 4.6 Antecedentes

Documentos históricos conservados como contexto; sus cifras **no** representan el estado vigente.

| Documento | Propósito |
|---|---|
| [Correcciones del informe (obs. 4, 5 y 6)](docs/antecedentes/CORRECCIONES-INFORME.md) | Análisis y propuestas fechados al 22-10-2026. |
| [Plan de entrenamiento (V2)](docs/antecedentes/PLAN-ENTRENAMIENTO.md) | Plan histórico inicial. |
| [Reconocimiento de prendas — V1](docs/antecedentes/README-v1.md) | Versión histórica descartada. |
| [Resumen del método de entrenamiento](docs/antecedentes/RESUMEN-METODO-ENTRENAMIENTO.md) | Método con contexto histórico. |

###### 4.7 Dataset y taxonomía

| Documento | Propósito |
|---|---|
| [Dataset de prendas](dataset/README.md) | Guía de clasificación y estructura general. |
| [Documentación del dataset](documentacion_dataset/README.md) | Esquema SQLite, procedencia y metadatos. |
| [Prendas de la parte inferior](dataset/inferior/README.md) · [Falda](dataset/inferior/faldas/README.md) · [Pantalón](dataset/inferior/pantalones/README.md) · [Short](dataset/inferior/shorts/README.md) | Clases de la parte inferior. |
| [Prendas de cuerpo completo](dataset/inferior_superior/README.md) · [Vestido](dataset/inferior_superior/vestido/README.md) | Clases de cuerpo completo. |
| [Prendas de la parte superior](dataset/superior/README.md) · [Abrigo](dataset/superior/abrigos/README.md) · [Blusa](dataset/superior/blusas/README.md) · [Camisa](dataset/superior/camisas/README.md) · [Chaqueta](dataset/superior/chaquetas/README.md) · [Suéter](dataset/superior/sueteres/README.md) | Clases de la parte superior. |
| [Conjunto portable de prueba](tests/imagenes-test/README.md) | 1.424 imágenes del split test con manifest. |

###### 4.8 Utilidades de entrenamiento y curación

| Documento | Propósito |
|---|---|
| [Utilidades de entrenamiento](utilidades-entrenamiento/README.md) | Entrenar, continuar checkpoints y desplegar inferencia. |
| [Inicio rápido](utilidades-entrenamiento/INICIO-RAPIDO.md) | Comandos mínimos para entrenar por terminal. |
| [Checkpoint compartido](utilidades-entrenamiento/modelos-compartidos/README.md) | Ubicación y uso de `mobilenetv3-small-best.pt`. |
| [Curación y anotación de datasets de moda](utilidades-entrenamiento/modelo-general-destilacion/README.md) | Panel de dataset, proveedores y flujo de curación. |
| [Plan de pruebas del pipeline de curación](utilidades-entrenamiento/modelo-general-destilacion/PLAN-PRUEBAS.md) | Pruebas del pipeline de curación. |
| [Dudas y decisiones antes de procesar datos](utilidades-entrenamiento/modelo-general-destilacion/dudas.md) | Preguntas abiertas y decisiones previas. |
| [Extensión Chrome: descargar imagen](utilidades-entrenamiento/scraping-plugin-chrome/folder-destino/README.md) | Utilidad auxiliar de captura de imágenes. |

##### 5. Archivos técnicos clave

- [Compose unificado](docker-compose.yaml) y [Compose de entrenamiento por terminal](utilidades-entrenamiento/docker-compose.yaml).
- [Esquema SQLite](documentacion_dataset/schema.sql) y [creación de estructura](documentacion_dataset/crear_estructura.sh).
- [Configuración por defecto](utilidades-entrenamiento/configs/default.yaml) y [desde cero](utilidades-entrenamiento/configs/desde-cero.yaml) del entrenamiento.
- [Fuentes de datos](utilidades-entrenamiento/modelo-general-destilacion/sources.json).
- [Validador documental](docs/validar_documentacion.py): `python3 docs/validar_documentacion.py` (comprueba enlaces, anclas y cobertura del índice).

##### 6. Alcance y notas

El alcance es clasificar una misma prenda por imagen o conjunto de vistas. No hay detección de múltiples prendas, segmentación ni salida de temporada. La integración con OpenStack/Kubernetes queda fuera de esta implementación. Los planes y V1 se conservan como antecedentes.

---


## 2. Resumen ejecutivo


### Resumen del proyecto de reconocimiento de prendas

*Fuente: [`docs/resumen/RESUMEN-PROYECTO.md`](docs/resumen/RESUMEN-PROYECTO.md)*


**Versión 2 · Revisión: 23 de octubre de 2026 · Lectura aproximada: cuatro páginas.**
Documento dividido en cuatro bloques con saltos sugeridos para impresión; la paginación final depende del visor. [Índice documental](docs/INDICE.md) · [Validación](docs/evaluacion/VALIDACION.md).

##### Página 1 — Propósito, arquitectura y operación

El proyecto implementa un sistema de visión artificial para reconocer el tipo, los colores y los estilos de una prenda a partir de fotografías. Su flujo comprende la preparación del dataset, la anotación asistida, la aprobación de muestras, el entrenamiento supervisado, la evaluación y la inferencia. Funciona con Docker Compose y utiliza SQLite para metadatos; no necesita un servidor de base de datos ni Kubernetes para operar localmente.

Las interfaces tienen responsabilidades complementarias:

| Dirección | Responsabilidad | Servicio |
|---|---|---|
| `http://127.0.0.1:8787/` | Construir y curar el dataset; ver galería y resolver duplicados | `dashboard` |
| `http://127.0.0.1:8090/` | Gestionar entrenamiento, consultar métricas y probar checkpoints | `monitor` |
| `http://127.0.0.1:8081/docs` | Consultar y probar el contrato de inferencia CPU independiente | `inference-api` |
| `http://127.0.0.1:8082/docs` | Ejecutar la prueba DSR de la API sobre el test portable | `test-api` |

El panel de dataset está en `utilidades-entrenamiento/modelo-general-destilacion/`. El de entrenamiento está en `utilidades-entrenamiento/`. Se comunican mediante el dataset montado en Docker: el curador escribe imágenes y SQLite, y el entrenador los lee en solo lectura. Los pesos y resultados se guardan por separado en `modelo-ia/`; el modelo recomendado se conserva en `modelos-compartidos/`.

Para iniciar las interfaces (panel de dataset, panel de entrenamiento, API CPU y API de pruebas) desde la raíz, preparar una sola vez el `.env` de curación y levantar el Compose unificado:

```bash
[ -f utilidades-entrenamiento/modelo-general-destilacion/.env ] || cp utilidades-entrenamiento/modelo-general-destilacion/.env.example utilidades-entrenamiento/modelo-general-destilacion/.env
chmod 600 utilidades-entrenamiento/modelo-general-destilacion/.env
docker compose up -d --build
```

Esto deja el panel de dataset en `http://127.0.0.1:8787/`, el panel de entrenamiento en `http://127.0.0.1:8090/`, la API CPU en `http://127.0.0.1:8081/docs` y la API de pruebas en `http://127.0.0.1:8082/docs`. Las claves se mantienen locales; el panel de dataset usa red del host y escucha solo en localhost, y las API y el monitor publican sus puertos también en localhost. En una máquina remota se accede con un túnel SSH. El checkpoint de la API se puede cambiar con `MODEL_CHECKPOINT` (ruta absoluta).

El entrenamiento por terminal se mantiene en el Compose de entrenamiento:

```bash
docker compose -f utilidades-entrenamiento/docker-compose.yaml build train
docker compose -f utilidades-entrenamiento/docker-compose.yaml run --rm train
```

Los servicios `train` y `train-gpu` permiten entrenar por terminal. El panel de entrenamiento se sirve con el servicio `monitor` del Compose unificado. Se utiliza una GPU por equipo: las memorias de laptops distintas no se suman. CPU es una alternativa funcional, cuyo tiempo de entrenamiento depende del hardware y del dataset.

El resultado buscado es un clasificador reproducible y pequeño, con artefactos identificables y métricas explícitas. La integración con una plataforma OpenStack/Kubernetes es una etapa posterior; no forma parte del despliegue Compose actual.

<div style="page-break-after: always;"></div>

##### Página 2 — Dataset, anotación y control de calidad

Las fotografías se organizan en `dataset/` por zona corporal, tipo y código de prenda. Ejemplo: `superior/camisas/CAMISA-1/frente.jpg`. Las rutas registradas son relativas al dataset, lo que permite trasladarlo entre equipos. Una prenda puede tener varias vistas, y todas deben conservar el mismo split para evitar contaminación entre entrenamiento y prueba.

El catálogo contempla nueve tipos: abrigo, blusa, camisa, chaqueta, falda, pantalón, short, suéter y vestido. Camisas y camisetas se unifican como `camisa`, conservando la etiqueta de origen para trazabilidad. Las temporadas se guardan como metadatos, pero no se predicen en las tres salidas actuales del modelo.

`dataset/metadata.sqlite` es la fuente de verdad de las relaciones. El esquema base tiene siete tablas: prendas, imágenes, catálogo de propiedades, valores de propiedades, descripciones generadas, análisis cacheados y configuración del pipeline. El módulo de duplicados añade tres tablas auxiliares; SQLite puede incluir además `sqlite_sequence`. Las imágenes y las bases locales no se distribuyen mediante Git.

Las fuentes se definen en `sources.json` y se leen desde `datos-crudos/`, montado en solo lectura. El curador verifica mapeo de clases, formato, tamaño y SHA-256. No incorpora clases fuera del mapeo; omite imágenes de más de 200.000 bytes. El hash evita importar otra vez el mismo archivo. Los análisis válidos se cachean considerando imagen, categoría, proveedor/modelo y prompt.

NVIDIA NIM y DeepSeek proponen descripciones y atributos. NIM divide el análisis en colores, estilos, temporadas y validación/descripción; los mecanismos de respaldo pueden generar más solicitudes por imagen. Los errores y respuestas inválidas se distinguen de los descartes válidos. Las claves, los modelos y los endpoints se configuran localmente; su disponibilidad remota no se comprobó en esta revisión.

El panel permite lotes de hasta **15.000 imágenes nuevas por proveedor**, con procesos y detención separados. Los colores usan vocabulario controlado; estilos y temporadas pueden ampliar el catálogo. La importación crea prendas pendientes y no aptas para entrenar. La aprobación debe confirmar etiquetas y procedencia. Existe `approve-generated`, que aprueba masivamente prendas pendientes con descripción: su ejecución no acredita revisión humana individual.

Para casi duplicados se usa dHash y distancia de Hamming, con umbral predeterminado 2. La interfaz permite conservar una imagen y rechazar las demás sin borrar archivos, descartar agrupaciones erróneas y deshacer resoluciones compatibles. `purge-duplicates` sí puede borrar archivos de rechazados; conserva filas para bloquear reimportaciones. Antes de una limpieza destructiva se necesita un respaldo recuperable.

La lectura del 23 de octubre encontró **14.456 prendas aprobadas y aptas**, distribuidas en 11.616 train, 1.416 val y 1.424 test; además, 12.134 pendientes y 17.007 rechazadas. Las 14.456 imágenes aprobadas existen. Los conteos son una instantánea y deben actualizarse si cambia el dataset.

<div style="page-break-after: always;"></div>

##### Página 3 — Modelo, entrenamiento y artefactos

La arquitectura es **MobileNetV3-Small** preentrenada con una base visual compartida y tres cabezas lineales. Tipo de prenda es clasificación de una categoría; color y estilo son multietiqueta. Se usa entropía cruzada para tipo y pérdidas binarias para las otras propiedades. Cuando una muestra carece de anotaciones de color o estilo, se omite esa parte de la pérdida: ausencia de anotación no significa que todas las etiquetas sean negativas.

El método es aprendizaje por transferencia supervisado con anotación asistida por IA. Aunque una carpeta se llama `modelo-general-destilacion`, no se implementa destilación clásica de logits de un maestro a un estudiante. Las descripciones guardadas tampoco convierten MobileNet en un modelo generativo.

La configuración vigente está en `configs/default.yaml`:

| Parámetro | Valor |
|---|---|
| Resolución y batch | 224 × 224; 64 imágenes |
| Duración máxima | 30 épocas; parada temprana con paciencia 5 |
| Inicio | Pesos preentrenados; 3 épocas de cabezas |
| Segunda fase | Ajuste fino de toda la base |
| Tasas de aprendizaje | 0,001 inicial; 0,0001 para ajuste fino |
| Otras opciones | AdamW, scheduler coseno, augmentación, ponderación por clase, suavizado de etiquetas |
| Reproducibilidad e inferencia | Semilla 42; umbral multietiqueta 0,5 |

Estos valores reflejan el archivo actual; no garantizan que el batch quepa en cualquier GPU. La precisión mixta se utiliza cuando CUDA y la configuración lo permiten. El primer uso de pesos preentrenados requiere descarga; la imagen Docker también instala dependencias mediante pip durante su construcción.

El cargador selecciona prendas aprobadas y aptas con split válido, fotografías reales y rutas existentes dentro del dataset. Valida etiquetas frente al catálogo. No comprueba documentalmente el permiso de uso de cada fotografía: esa revisión corresponde al proceso de preparación. El split reside en la prenda, aunque el aprendizaje y las métricas se calculan por imagen.

Por terminal se ejecuta `docker compose run --rm train` desde `utilidades-entrenamiento/`; con GPU se usa `docker compose --profile gpu run --rm train-gpu`. El monitor permite iniciar, detener y continuar desde el mejor checkpoint de una ejecución. Conviene usar un único mecanismo de control: un entrenamiento iniciado por terminal no es un proceso hijo gestionado por el monitor.

Cada ejecución crea `modelo-ia/runs/<id>/` con `best.pt`, configuración, progreso y métricas; el registro SQLite de entrenamiento identifica las imágenes utilizadas. Se selecciona el mejor checkpoint por pérdida de validación. El script también evalúa test al finalizar; las evaluaciones repetidas existentes deben distinguirse del objetivo metodológico de reservar test para el cierre.

Continuar desde un checkpoint crea una ejecución nueva. Las estrategias son ajuste fino completo o solo cabezas, con tasas reducidas y hasta diez épocas. Se exige coincidencia de arquitectura, clases y resolución. Se reutilizan pesos, pero se reinician optimizador, scheduler y épocas: no es una reanudación exacta de todo el estado anterior.

El modelo compartido es `modelos-compartidos/mobilenetv3-small-best.pt`, con entrada 224 × 224 y mejor época 15 de su ejecución fuente. Su SHA-256 verificado es `79407f5537418bc258857fa54723d8e39b152505ad3a6f6a6ea4f97e1dfcb35c`. Debe preservarse junto con su identificación y evaluación para reproducir resultados.

<div style="page-break-after: always;"></div>

##### Página 4 — Evaluación, inferencia y situación real

Los artefactos existentes evalúan el checkpoint compartido sobre 1.424 imágenes test; 1.418 tienen color y estilo anotados. El archivo local de evaluación generado el 23 de octubre confirma las cifras publicadas:

| Propiedad | Resultado |
|---|---:|
| Tipo: exactitud | 94,94 % |
| Color: coincidencia exacta / Jaccard | 53,88 % / 68,42 % |
| Estilo: coincidencia exacta / Jaccard | 47,53 % / 69,21 % |
| Promedio de tipo y los dos Jaccard | 77,52 % |

Jaccard mide coincidencia parcial entre conjuntos de etiquetas. El promedio de propiedades da el mismo peso a las tres salidas y supera el criterio documentado de 70 %, pero no significa que todas las propiedades tengan 77,52 % de exactitud. La diferencia de 0,12 puntos con otro entrenamiento no demuestra superioridad estadística. No se repitió el entrenamiento ni la evaluación completa durante esta revisión; se contrastaron los informes guardados y el hash del checkpoint.

La principal limitación es que color y estilo fueron anotados por IA: la evaluación mide concordancia con esas anotaciones, sin demostrar una referencia humana independiente. También hay desbalance de clases. El informe previo identifica 77 imágenes test con casi duplicados en train y reporta una reducción del macro a 76,96 % al excluirlas; ese análisis de similitud no se recalculó aquí. La generalización a personas vistiendo la prenda tampoco está demostrada por fotografías de catálogo.

La predicción por terminal permite una o varias vistas de la misma prenda, promediando probabilidades. El monitor prueba una imagen en CPU. La API independiente recibe una imagen multipart en `garment_image` y devuelve tipo, colores, estilos y una descripción formada a partir de esas etiquetas. No localiza ni separa varias prendas dentro de una fotografía. El contrato de la aplicación 2.0.0 sustituye al anterior de dos imágenes.

La API publica `GET /health` y `POST /v1/predict`, además de documentación FastAPI. Admite JPEG, PNG y WebP, hasta 10 MiB y 25 megapíxeles por imagen. Carga el checkpoint en CPU y no monta el dataset. El Compose CPU reutiliza una imagen base PyTorch con bibliotecas CUDA; ejecutar en CPU no implica que la imagen sea una distribución mínima sin CUDA.

En la revisión respondieron con HTTP 200 las dos páginas principales, la lista de modelos, el resumen de curación, la galería y los grupos duplicados; `/health` informó CPU disponible. Las comprobaciones HTTP fueron de consulta. Las operaciones de escritura se contrastaron con el código y las pruebas, sin lanzar lotes remotos ni modificar el dataset.

SQLite pasó `quick_check`, pero `foreign_key_check` encontró **15.066 referencias huérfanas** de miembros a grupos de duplicados. Hay **9.939 rutas de imagen sin archivo**, todas de prendas rechazadas, compatibles con el flujo de purga documentado; no se verificó individualmente su causa histórica. No faltan archivos del subconjunto aprobado. Estas observaciones deben resolverse o justificarse antes de declarar íntegra toda la base; no equivalen a que fallen las interfaces.

La documentación queda organizada mediante un README de entrada, un índice completo, guías operativas, referencia de endpoints, evaluación y registro de validación. Los planes anteriores se conservan como antecedentes. Los próximos pasos son sanear las relaciones de duplicados con respaldo, establecer una referencia humana independiente, controlar similitudes entre splits y medir el rendimiento en el entorno final. [Consultar evidencia y verificaciones](docs/evaluacion/VALIDACION.md).

---


## 3. Instalación


### Instalación del sistema completo (Docker)

*Fuente: [`docs/instalacion/INSTALACION-DOCKER.md`](docs/instalacion/INSTALACION-DOCKER.md)*


Versión: 1.1 · 02 de noviembre de 2026

Guía operativa del **Reconocimiento de prendas V2**, complemento de IA del artefacto principal documentado en el informe del proyecto (nube privada, Kubernetes y VTON Studio). Alineada con la metodología **DSRM** (Peffers et al., 2007).

[Índice completo](docs/INDICE.md) · [Instalación nativa sin Docker de la API](docs/instalacion/INSTALACION-NATIVA.md) · [Referencia de endpoints](docs/operacion/API.md)

##### 1. Contexto DSRM y rol de esta guía

El proyecto sigue **Design Science Research Methodology (DSRM)**. El artefacto principal es la nube privada con Kubernetes y el servicio FASHN VTON; **Reconocimiento de prendas V2** es un **complemento útil** que operativiza la inferencia (MobileNetV3-Small) y el entrenamiento del caso de estudio.

Esta guía no documenta el artefacto principal: describe cómo **instanciar y demostrar** el complemento en un equipo Ubuntu con Docker. La correspondencia con las seis actividades DSRM es:

| Actividad DSRM | Dónde se materializa en esta guía |
|---|---|
| 1. Identificación del problema | §2 Objetivo y alcance (qué resuelve el sistema) |
| 2. Objetivos de la solución | §2 Objetivo y alcance (servicios e interfaces) |
| 3. Diseño y desarrollo | §6 Levantar las interfaces y §9 Entrenamiento (Compose, recetas, checkpoints) |
| 4. Demostración | §6–8 Levantar y probar los servicios (HTTP 200 e inferencia) |
| 5. Evaluación | §8 API de pruebas DSR y §10 Informe HTML (métricas y Anexo G) |
| 6. Comunicación | Documentos referenciados: [API.md](docs/operacion/API.md), [DSR-PRUEBA-API.md](docs/operacion/DSR-PRUEBA-API.md), informe y Anexo G |

##### 2. Objetivo y alcance

Esta guía instala el sistema completo **Reconocimiento de prendas V2** en un equipo con Ubuntu 24.04 y Docker. El sistema incluye:

| Interfaz | Dirección local | Función |
|---|---|---|
| Panel de dataset | http://127.0.0.1:8787/ | Importar, anotar (NVIDIA NIM / DeepSeek), revisar y depurar duplicados |
| Panel de entrenamiento | http://127.0.0.1:8090/ | Iniciar/detener entrenamientos, continuar checkpoints y ver métricas |
| API de inferencia (CPU) | http://127.0.0.1:8081/docs | Describe una prenda a partir de una fotografía |
| API de pruebas (DSR) | http://127.0.0.1:8082/docs | Ejecuta la prueba sobre el conjunto portable `tests/imagenes-test/` |

Todos los servicios se levantan con el **Compose unificado de la raíz** ([docker-compose.yaml](docker-compose.yaml)). No es necesario Docker para la API de inferencia: existe una [instalación nativa](docs/instalacion/INSTALACION-NATIVA.md) alternativa.

##### 3. Requisitos

- Ubuntu 24.04, arquitectura x86-64.
- Docker Engine 29+ y Docker Compose v2 (`docker compose`).
- Conexión a Internet para descargar imágenes base y dependencias durante la primera compilación.
- Para el panel de dataset: claves de los proveedores de IA (NVIDIA NIM y/o DeepSeek). Son opcionales si solo se importan imágenes sin anotar.
- Para GPU (opcional): driver NVIDIA y NVIDIA Container Toolkit.

Verificación:

```bash
docker --version
docker compose version
```

Resultado esperado: Docker 29.x y Compose v2.40+.

##### 4. Obtener el código

```bash
git clone <url-del-repositorio> modelo-reconocimiento-prendas
cd modelo-reconocimiento-prendas
```

El repositorio ya incluye el checkpoint compartido (`utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt`) y el conjunto portable de test (`tests/imagenes-test/`). El dataset (`dataset/`) se entrega aparte o se reconstruye con el panel.

##### 5. Configurar el panel de dataset (una sola vez)

Crear el archivo de entorno desde la plantilla y restringir sus permisos:

```bash
[ -f utilidades-entrenamiento/modelo-general-destilacion/.env ] || \
  cp utilidades-entrenamiento/modelo-general-destilacion/.env.example \
     utilidades-entrenamiento/modelo-general-destilacion/.env
chmod 600 utilidades-entrenamiento/modelo-general-destilacion/.env
```

Variables principales (los valores son secretos y **no deben versionarse**):

| Variable | Uso |
|---|---|
| `ANNOTATION_PROVIDER` | `nim`, `deepseek` u `openai` (proveedor de anotación) |
| `NVIDIA_NIM_API_KEY`, `NVIDIA_NIM_MODEL` | Acceso a NVIDIA NIM |
| `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` | Acceso a la API de DeepSeek |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Acceso a OpenAI (opcional) |
| `TRAINING_UID`, `TRAINING_GID` | UID/GID del usuario para los montajes (por defecto 1000) |

##### 6. Levantar las interfaces — Diseño y desarrollo → Demostración

Desde la raíz del proyecto:

```bash
docker compose up -d --build
```

Esto construye y arranca los cuatro servicios. Para levantar solo dos de ellos (p. ej. las dos interfaces principales):

```bash
docker compose up -d --build dashboard monitor
```

Comprobar el estado:

```bash
docker compose ps
curl -s -o /dev/null -w "dataset:  %{http_code}\n" http://127.0.0.1:8787/
curl -s -o /dev/null -w "monitor:  %{http_code}\n" http://127.0.0.1:8090/
curl -s -o /dev/null -w "inferencia: %{http_code}\n" http://127.0.0.1:8081/docs
curl -s -o /dev/null -w "pruebas:  %{http_code}\n" http://127.0.0.1:8082/docs
```

Resultado esperado: HTTP 200 en las cuatro direcciones. El panel de dataset usa la red del host, por lo que su puerto 8787 no aparece en `docker ps`, pero responde en `127.0.0.1:8787`.

##### 7. Probar la API de inferencia — Demostración

```bash
curl -X POST http://127.0.0.1:8081/describir \
  -H "Content-Type: application/json" \
  -d '{"ruta_imagen": "ruta/a/una/foto.jpg"}'
```

Consulta el contrato completo en [API.md](docs/operacion/API.md) y en `http://127.0.0.1:8081/docs`.

Cambiar el checkpoint cargado por la API (antes de levantar):

```bash
MODEL_CHECKPOINT=/ruta/absoluta/al/checkpoint.pt docker compose up -d inference-api
```

##### 8. Probar la API de pruebas (DSR) — Evaluación

```bash
# Prueba de humo (10 imágenes)
curl -X POST "http://127.0.0.1:8082/test/run?max_images=10"

# Prueba completa (1.424 imágenes)
curl -X POST "http://127.0.0.1:8082/test/run"

# Evidencia para el informe y el Anexo G
curl "http://127.0.0.1:8082/test/informe"
```

Detalle en [DSR-PRUEBA-API.md](docs/operacion/DSR-PRUEBA-API.md) y [README-TEST.md](docs/operacion/README-TEST.md).

##### 9. Entrenamiento — Diseño y desarrollo / Demostración

###### 9.1 Desde el panel (recomendado)

Abrir http://127.0.0.1:8090/ y usar el selector de configuración. Las recetas disponibles están en `utilidades-entrenamiento/configs/`:

- `default.yaml` / `desde-cero.yaml`: entrenamiento independiente desde pesos preentrenados (lr 0,001 / finetune_lr 0,0001, warmup 3, 30 épocas).
- Recetas de continuación: tasas 1e-4 / 1e-5 y sin warmup, para reanudar un checkpoint.

###### 9.2 Desde terminal (Compose de entrenamiento)

```bash
docker compose -f utilidades-entrenamiento/docker-compose.yaml build train
docker compose -f utilidades-entrenamiento/docker-compose.yaml run --rm train
```

###### 9.3 Con GPU (opcional)

```bash
docker compose -f utilidades-entrenamiento/docker-compose.yaml --profile gpu run --rm train-gpu
```

Requiere driver NVIDIA y NVIDIA Container Toolkit. Detalle en la guía de entrenamiento (`utilidades-entrenamiento/README.md`).

##### 10. Generar el informe HTML de evaluación — Evaluación

```bash
python3 utilidades-entrenamiento/generar_informe_entrenamiento.py --output-dir docs/datos-graficos
```

O dentro del contenedor (deja el log de cálculos en `informe_entrenamiento.log`):

```bash
docker run --rm --user 1000:1000 \
  -v "$PWD/utilidades-entrenamiento/modelo-ia:/app/modelo-ia" \
  -v "$PWD/utilidades-entrenamiento/modelos-compartidos:/app/modelos-compartidos:ro" \
  -v "$PWD/dataset:/app/dataset:ro" \
  -v "$PWD/docs/datos-graficos:/app/salida" \
  -v "$PWD/utilidades-entrenamiento/generar_informe_entrenamiento.py:/app/generar_informe_entrenamiento.py:ro" \
  --entrypoint python modelo-general-destilacion-curator:latest \
  /app/generar_informe_entrenamiento.py \
    --modelo-ia /app/modelo-ia \
    --modelos-compartidos /app/modelos-compartidos \
    --dataset-sqlite /app/dataset/metadata.sqlite \
    --output-dir /app/salida
```

##### 11. Respaldo y restauración — Evidencias y trazabilidad

Respaldo de los entrenamientos, evaluaciones y base de datos (se guarda en `respaldos/`, ignorado por Git):

```bash
tar -czf "respaldos/entrenamiento-$(date +%Y%m%d-%H%M%S).tar.gz" \
  utilidades-entrenamiento/modelo-ia \
  utilidades-entrenamiento/modelos-compartidos \
  dataset/metadata.sqlite
```

Restaurar:

```bash
tar -xzf respaldos/entrenamiento-<marca>.tar.gz
```

##### 12. Detener el sistema

```bash
docker compose down            # detiene y retira contenedores; conserva datos
docker compose down --volumes  # además elimina volúmenes (pérdida de datos)
```

##### 13. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| El panel de dataset no anota | `.env` sin claves o proveedor inválido | Revisar `ANNOTATION_PROVIDER` y las claves en `.env` |
| `No encontrado` al iniciar entrenamiento | Petición sin cabecera `X-Requested-With: monitor` o config inexistente | Usar el panel; elegir una config de `configs/` |
| Puertos ocupados | Otro proceso usa 8081/8082/8090 | Cambiar los `ports` en `docker-compose.yaml` |
| Fallo de permisos en montajes | UID/GID distinto de 1000 | Definir `TRAINING_UID`/`TRAINING_GID` en `.env` |
| La API devuelve error de checkpoint | `MODEL_CHECKPOINT` apunta a un archivo inexistente | Verificar ruta y SHA-256 en [EVIDENCIAS-INTEGRIDAD-SHA256.md](docs/evaluacion/EVIDENCIAS-INTEGRIDAD-SHA256.md) |

---


### Instalación nativa del modelo entrenado y su API de reconocimiento de prendas

*Fuente: [`docs/instalacion/INSTALACION-NATIVA.md`](docs/instalacion/INSTALACION-NATIVA.md)*


Versión de la API: 2.0.0 · Edición revisada 1.1 · 23 de octubre de 2026

[Documento Word con formato APA 7](docs/instalacion/Instalacion_nativa_API_prendas_APA7.docx) · [Índice](docs/INDICE.md)

##### Objetivo y alcance

Este manual permite instalar MobileNetV3-Small con sus pesos ya entrenados y publicar una API local que recibe una fotografía y devuelve una descripción de la prenda. Está dirigido a la persona que instala el servicio y a quien lo integra con otra aplicación. El procedimiento utiliza Ubuntu 24.04, Python 3.12, arquitectura x86-64 y CPU.

La secuencia de instalación es: comprobar el equipo, copiar el código y el checkpoint, instalar dependencias en un entorno virtual, iniciar la API, probar una fotografía y, después, habilitar el servicio permanente. Al finalizar se debe obtener HTTP 200 con el campo `descripcion_mas_probable`, sin ejecutar entrenamiento, copiar el dataset, utilizar GPU ni configurar proveedores de IA.

El checkpoint contiene los pesos ajustados, el catálogo de clases, la resolución de entrada y el umbral multietiqueta. La arquitectura se construye desde `train.py` sin ejecutar su entrenamiento. Se carga el checkpoint en CPU con `pretrained=False`: una vez instaladas las dependencias y copiados los archivos, la inferencia no descarga pesos adicionales ni consulta servicios externos.

El servicio clasifica la fotografía completa. Produce tipo, colores y estilos; la descripción es una plantilla formada con esas etiquetas. No detecta varias prendas ni determina material, marca o talla. Para una entrada útil, mostrar una sola prenda, completa y bien iluminada, con poco fondo distractor. Estas recomendaciones de captura no garantizan una predicción correcta.

El catálogo de tipos comprende abrigo, blusa, camisa, chaqueta, falda, pantalón, short, suéter y vestido. Camisa y camiseta comparten la clase `camisa`. La temporada almacenada en el dataset no es una salida de esta API.

##### Entorno y archivos necesarios

Se necesita una terminal Bash, una cuenta con permiso para instalar paquetes del sistema, acceso de lectura a los archivos entregados y conexión a Internet durante la instalación. El puerto 8081 debe estar libre; puede sustituirse por otro puerto en todos los comandos. No se ha establecido un mínimo medido de RAM ni de núcleos: el tamaño del archivo de pesos no representa el consumo total del proceso.

Se fijan PyTorch 2.5.1 y torchvision 0.20.1 para mantener la compatibilidad con el proyecto; la documentación oficial publica esa combinación para CPU (PyTorch, s. f.). Una instalación en Windows, macOS o ARM requiere adaptar y verificar el procedimiento; no queda validada por esta guía.

Preparar una carpeta con estos archivos, conservando sus nombres:

```text
prendas-api/
  inference_api.py
  train.py
  requirements.txt
  modelos-compartidos/
    mobilenetv3-small-best.pt
```

Los archivos están en `utilidades-entrenamiento/` dentro del repositorio entregado. `train.py` es necesario porque la API importa la clase `MultiTaskMobileNet`. No copiar solo el archivo `.pt`: el programa necesita también la definición de arquitectura y las bibliotecas.

El hash SHA-256 esperado del checkpoint compartido es:

```text
79407f5537418bc258857fa54723d8e39b152505ad3a6f6a6ea4f97e1dfcb35c
```

Este valor identifica los pesos documentados. El checkpoint debe provenir de la entrega del proyecto; su hash permite comprobar que corresponde al archivo esperado. Si el resultado difiere, detener la instalación y confirmar la versión del modelo antes de continuar.

##### Preparación del sistema

Abrir una terminal Bash en Ubuntu. Los siguientes comandos instalan Python, el módulo de entornos virtuales y curl; requieren permisos administrativos en el equipo de destino:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl
python3 --version
uname -m
```

Resultado esperado: Python 3.12.x y arquitectura `x86_64`. Ejecutar los pasos de copia y de instalación de Python como usuario normal; usar `sudo` solo en los comandos administrativos que lo indican. Si se utiliza otra plataforma, revisar primero la compatibilidad de las distribuciones de PyTorch; no asumir que estos binarios CPU sirven para cualquier arquitectura.

Copiar los cuatro archivos desde la entrega del proyecto. En el ejemplo, sustituir `/ruta/al/repositorio` por la ruta real que contiene `utilidades-entrenamiento`:

```bash
mkdir -p "$HOME/prendas-api/modelos-compartidos"
cd /ruta/al/repositorio/utilidades-entrenamiento
cp inference_api.py train.py requirements.txt "$HOME/prendas-api/"
cp modelos-compartidos/mobilenetv3-small-best.pt \
  "$HOME/prendas-api/modelos-compartidos/"
cd "$HOME/prendas-api"
sha256sum modelos-compartidos/mobilenetv3-small-best.pt
```

Resultado esperado: los cuatro archivos están presentes y el hash coincide exactamente con el documentado. Comprobar también que la cuenta de ejecución puede leer el checkpoint. No ejecutar `train.py` ni inicializar SQLite.

##### Instalación de dependencias

Crear el entorno virtual en la ubicación definitiva de instalación. Un entorno virtual contiene rutas del equipo donde se creó: si se traslada el servicio, recrearlo en el destino en vez de copiar `.venv` (Python Software Foundation, s. f.). Activarlo antes de instalar paquetes:

```bash
cd "$HOME/prendas-api"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.5.1 torchvision==0.20.1 \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pip check
```

El índice CPU instala PyTorch sin requerir un controlador NVIDIA. `requirements.txt` fija Pillow 10.2.0, PyYAML 6.0.2, FastAPI 0.115.12, python-multipart 0.0.20 y Uvicorn 0.34.2. PyYAML se necesita para importar el módulo de arquitectura. FastAPI utiliza python-multipart para procesar archivos enviados mediante formularios (FastAPI, s. f.).

Resultado esperado de `pip check`: `No broken requirements found.` Las versiones impresas deben ser `2.5.1+cpu` y `0.20.1+cpu`. Si hay errores de resolución, no continuar con el arranque hasta corregir el entorno. Los comandos fijan bibliotecas principales, pero no bloquean todas las dependencias transitivas; guardar el inventario de versiones instalado:

```bash
python -m pip freeze > dependencias-instaladas.txt
python -c 'import torch, torchvision; print(torch.__version__); print(torchvision.__version__)'
```

##### Configuración y arranque de la API

Desde la carpeta de instalación y con el entorno activado, configurar la ubicación absoluta del checkpoint y los hilos de CPU:

```bash
cd "$HOME/prendas-api"
source .venv/bin/activate
export MODEL_CHECKPOINT="$PWD/modelos-compartidos/mobilenetv3-small-best.pt"
export API_CPU_THREADS=4
python -m uvicorn inference_api:app \
  --host 127.0.0.1 --port 8081 --workers 1
```

Uvicorn permite fijar dirección, puerto y número de procesos mediante opciones de ejecución (Uvicorn, s. f.). Se utiliza un proceso para cargar una sola instancia del modelo. `API_CPU_THREADS` controla los hilos de PyTorch; no fija el número total de clientes. La implementación limita a dos las inferencias que pueden entrar simultáneamente en su sección de ejecución.

`API_CPU_THREADS` debe ser un entero positivo; el valor 4 es el predeterminado, no una medición de capacidad del equipo. La variable `MODEL_CHECKPOINT` se lee al importar el módulo; si cambia, reiniciar el proceso. Si se omite, la API busca el archivo compartido en `modelos-compartidos/` junto a `inference_api.py`. Este comportamiento permite usar la estructura mínima anterior sin rutas dependientes de otro entorno.

Resultado esperado: Uvicorn informa que completó el arranque y está escuchando en `http://127.0.0.1:8081`. Si falla la carga del checkpoint, el arranque no se completa y el servicio puede no aceptar conexiones. Mantener esta terminal abierta durante la primera prueba. No utilizar `--reload` para el servicio permanente. Si el puerto 8081 está ocupado, elegir otro, por ejemplo 8082, y sustituirlo en todas las pruebas y clientes. Detener una ejecución manual con Ctrl+C.

##### Verificación y envío de una imagen

En otra terminal, comprobar disponibilidad:

```bash
curl --fail-with-body http://127.0.0.1:8081/health
```

La respuesta esperada tras cargar el modelo es:

```json
{"status":"ok","device":"cpu"}
```

Abrir `http://127.0.0.1:8081/docs`, seleccionar `POST /v1/predict`, pulsar “Try it out”, adjuntar la fotografía en `garment_image` y ejecutar. La interfaz se genera a partir del contrato de la API.

Para hacer la misma solicitud desde una terminal, sustituir la ruta por una fotografía real:

```bash
curl --fail-with-body http://127.0.0.1:8081/v1/predict \
  -F 'garment_image=@/ruta/a/prenda.jpg'
```

El campo requerido es exactamente `garment_image`; el nombre del archivo puede variar. El cuerpo es `multipart/form-data`, no JSON ni una cadena base64. La opción `-F` de curl construye el formulario: no establecer manualmente su encabezado `Content-Type`, porque debe incluir el separador multipart. No se necesita `person_image`.

La API admite JPEG, PNG y WebP, hasta 10 MiB (10.485.760 bytes) y 25.000.000 de píxeles por imagen. El tamaño en píxeles se calcula como ancho por alto; no basta con cambiar la extensión de un archivo para convertirlo a un formato admitido. El servidor decodifica la imagen, la convierte a RGB y la redimensiona a 224 × 224 según el checkpoint compartido.

Ejemplo abreviado e ilustrativo de respuesta; los valores concretos dependen de la fotografía:

```json
{
  "descripcion_mas_probable": "Tipo probable: camisa; colores probables: azul; estilos probables: casual.",
  "tipo_prenda": {"valor": "camisa", "probabilidad": 0.95},
  "colores": [
    {"valor": "azul", "probabilidad": 0.90, "supera_umbral": true}
  ],
  "estilos": [
    {"valor": "casual", "probabilidad": 0.85, "supera_umbral": true}
  ],
  "umbral_multietiqueta": 0.5,
  "device": "cpu",
  "latencia_ms": {
    "preprocesamiento_imagen": 3.0,
    "inferencia_imagen": 20.0,
    "total_servidor": 23.0
  }
}
```

`descripcion_mas_probable` contiene el texto listo para mostrar. `tipo_prenda` incluye la categoría de mayor puntuación y su probabilidad; la API siempre selecciona un tipo y no aplica un umbral de rechazo a esa categoría. Una puntuación baja no se transforma automáticamente en «desconocido».

`colores` y `estilos` incluyen hasta cinco candidatos por propiedad, con `valor`, `probabilidad` y `supera_umbral`. La descripción utiliza solo candidatos que alcanzan el umbral del checkpoint, actualmente 0,5. Si ninguno lo alcanza, lo indica en el texto. Una probabilidad es una puntuación del modelo, no una garantía de acierto ni evidencia de calibración.

`latencia_ms.preprocesamiento_imagen` mide la transformación de la imagen ya decodificada. `inferencia_imagen` incluye la espera para entrar al semáforo y la ejecución del modelo. `total_servidor` es la suma de ambas mediciones: excluye transferencia HTTP, decodificación y parte de la construcción de la respuesta. Para medir la experiencia del cliente se debe cronometrar la solicitud completa.

##### Integración desde otra aplicación

El cliente debe leer `descripcion_mas_probable` para mostrar el texto y utilizar las propiedades estructuradas si necesita filtros o indicadores de confianza. Ejemplo con Python; instalar requests en el entorno del cliente si no está disponible:

```bash
python -m pip install requests==2.32.3
```

```python
import requests

url = "http://127.0.0.1:8081/v1/predict"
with open("prenda.jpg", "rb") as image:
    response = requests.post(
        url,
        files={"garment_image": ("prenda.jpg", image, "image/jpeg")},
        timeout=60,
    )
response.raise_for_status()
print(response.json()["descripcion_mas_probable"])
```

Los errores HTTP deben tratarse antes de acceder al JSON de éxito; `raise_for_status()` cumple esa función en el ejemplo. El tiempo de espera de 60 segundos es un valor del cliente, no una promesa de latencia del modelo.

La aplicación 2.0.0 conserva `/v1/predict`, pero cambia el contrato anterior: ahora solo requiere la imagen de la prenda y devuelve las propiedades directamente en el objeto raíz. Los clientes anteriores deben dejar de depender de `prediccion_combinada`, `predicciones_por_imagen` y `metodo_combinacion`. La ruta y la versión del esquema de respuesta no deben confundirse.

##### Ejecución permanente en Ubuntu

Después de completar la prueba manual, detener ese proceso con Ctrl+C para liberar el puerto y registrar un servicio systemd. Esta etapa es opcional para una prueba puntual; permite supervisar el proceso y arrancarlo al iniciar el equipo (systemd, s. f.-a). El ejemplo supone que la carpeta definitiva es `/home/ubuntu/prendas-api`, el usuario es `ubuntu` y el grupo es `ubuntu`. Sustituir esas rutas y nombres si el equipo utiliza otros; no ejecutar el servicio con una ruta de ejemplo inexistente.

Crear la unidad con un editor administrativo:

```bash
sudo nano /etc/systemd/system/prendas-api.service
```

Contenido de la unidad:

```ini
[Unit]
Description=API CPU de reconocimiento de prendas
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/prendas-api
Environment=API_CPU_THREADS=4
ExecStart=/home/ubuntu/prendas-api/.venv/bin/python -m uvicorn \
  inference_api:app --host 127.0.0.1 --port 8081 --workers 1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

La unidad utiliza la ruta predeterminada del checkpoint junto a `inference_api.py`. Para otro modelo, añadir una directiva `Environment=MODEL_CHECKPOINT=/ruta/absoluta/modelo.pt`. Las variables exportadas en una terminal no configuran por sí solas la unidad del sistema. La barra inversa al final de `ExecStart` continúa el comando en la línea siguiente (systemd, s. f.-b).

Comprobar la sintaxis antes de activar y revisar el servicio:

```bash
sudo systemd-analyze verify /etc/systemd/system/prendas-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now prendas-api
sudo systemctl status prendas-api --no-pager
sudo journalctl -u prendas-api -n 50 --no-pager
curl --fail-with-body http://127.0.0.1:8081/health
```

Resultado esperado: `systemctl status` muestra `active (running)` y la consulta de salud responde HTTP 200. La cuenta del servicio debe poder leer código, checkpoint y entorno virtual. La unidad utiliza el ejecutable de `.venv` y no requiere activación interactiva.

Para detenerlo, ejecutar `sudo systemctl stop prendas-api`. Después de cambiar código o un checkpoint compatible, ejecutar `sudo systemctl restart prendas-api` y repetir las pruebas de salud e imagen. Si cambia el archivo `.service`, ejecutar antes `sudo systemctl daemon-reload`.

##### Acceso desde otro equipo

El servicio de este manual escucha en localhost. Para usarlo desde otro equipo mediante SSH:

```bash
ssh -L 8081:127.0.0.1:8081 usuario@servidor
```

Con el túnel abierto, usar `http://127.0.0.1:8081` en el equipo cliente. Si se requiere acceso público, definir un despliegue adicional con proxy, TLS, autenticación y límites de solicitudes. La API actual no incluye autenticación y no habilita orígenes CORS de navegador; una página de otro origen necesita una configuración específica o un proxy del mismo origen.

##### Diagnóstico de fallos

La primera comprobación es distinguir un fallo de conexión de una respuesta HTTP con error. Si curl no conecta, revisar que el proceso siga activo y que cliente, puerto y túnel coincidan. Si existe respuesta HTTP, conservar su campo `detail` y consultar los registros del servicio.

Tabla 1

*Diagnóstico de incidencias de instalación y consumo*

| Síntoma | Causa que debe comprobarse | Acción |
|---|---|---|
| No conecta o puerto ocupado | Proceso detenido, puerto equivocado u otro servicio escuchando | Revisar Uvicorn o systemctl; consultar `ss -ltnp`; usar un puerto libre en servidor y cliente. |
| Error al importar | Entorno incorrecto o archivos/dependencias incompletos | Activar `.venv`, ejecutar desde la carpeta de instalación y revisar `python -m pip check`. |
| Fallo al cargar pesos | Ruta, permisos o checkpoint incompatible | Comprobar `MODEL_CHECKPOINT`, lectura del archivo, hash y catálogo; revisar el error de arranque. |
| HTTP 422 | Campo ausente, archivo vacío o contenido ilegible | Enviar el archivo real mediante `-F` y el nombre `garment_image`. |
| HTTP 413 o 415 | Exceso de bytes/píxeles o formato no admitido | Preparar una imagen dentro de los límites; convertir el archivo si el formato no corresponde. |
| HTTP 503 | Modelo no disponible dentro de la aplicación | Revisar la carga del checkpoint y los registros; no interpretar este código como fallo de clasificación. |
| Funciona con curl, pero no en navegador | Origen CORS diferente | Usar un proxy del mismo origen o definir los orígenes permitidos de forma explícita. |

Si un cliente anterior recibe HTTP 422 y el detalle exige `person_image`, sigue conectado a una instancia con el contrato antiguo. Reiniciar el servicio con el código actualizado y revisar su `/openapi.json`; el cuerpo requerido debe contener solo `garment_image`.

##### Actualización y recuperación

Antes de actualizar, conservar una copia del código, checkpoint e inventario `dependencias-instaladas.txt` que funcionaban. No actualizar únicamente los pesos si cambia la arquitectura o el catálogo. Una vez sustituida una entrega compatible, reiniciar el proceso y repetir las pruebas de aceptación. Si falla, restaurar el conjunto anterior y reiniciar. Si cambian dependencias, preparar un entorno virtual nuevo con el inventario compatible en lugar de mezclar instalaciones sin registro.

##### Criterios de aceptación

La instalación queda aceptada cuando se cumplen todos estos puntos: el hash coincide con la entrega; `pip check` no reporta incompatibilidades; el proceso completa el arranque; `/health` responde `status=ok` y `device=cpu`; y una petición con una sola fotografía devuelve HTTP 200 con una descripción no vacía, tipo, colores y estilos. Para una instalación permanente, comprobar además `active (running)` y repetir la petición después de un reinicio del servicio.

Estas comprobaciones acreditan funcionamiento técnico, no exactitud para todas las prendas ni capacidad bajo una carga no medida. El estado de salud no sustituye la prueba de inferencia. Una respuesta semánticamente incorrecta puede seguir siendo HTTP 200 y debe evaluarse con imágenes y etiquetas de referencia.

##### Verificación de esta entrega

La instalación se comprobó en un entorno virtual temporal con Python 3.12, PyTorch 2.5.1+cpu y torchvision 0.20.1+cpu. Se copiaron únicamente los archivos de la estructura mínima y el checkpoint compartido. La API inició sin dataset en su carpeta de ejecución, `/health` informó CPU disponible y una solicitud multipart con una fotografía real devolvió HTTP 200, descripción y propiedades. El esquema OpenAPI exigió únicamente `garment_image`.

En la validación de la entrega anterior pasaron 19 pruebas automatizadas de entrenamiento e inferencia, incluidas solicitudes HTTP de una imagen y validación de errores. Esta comprobación valida el arranque y el contrato; no constituye una nueva evaluación de precisión ni una prueba de carga. Esta revisión del manual mantiene el código de la API y sus pesos; no vuelve a entrenar el modelo ni vuelve a medir su precisión. Los servicios previamente iniciados deben reiniciarse con el código actualizado para adoptar el nuevo contrato.

La presentación utiliza tamaño carta, márgenes de 2,54 cm, doble interlineado, numeración superior derecha y referencias con sangría francesa. El texto usa Times New Roman de 12 puntos y el código Courier New de 10 puntos, siguiendo las pautas aplicables de APA 7 (American Psychological Association, 2022, 2024, 2026). La portada se adapta al carácter técnico del documento.

##### Referencias

American Psychological Association. (2022, julio). *Line spacing*. APA Style. https://apastyle.apa.org/style-grammar-guidelines/paper-format/line-spacing

American Psychological Association. (2024, noviembre). *Paper format*. APA Style. https://apastyle.apa.org/style-grammar-guidelines/paper-format

American Psychological Association. (2026, febrero). *Font*. APA Style. https://apastyle.apa.org/style-grammar-guidelines/paper-format/font

FastAPI. (s. f.). *Request files*. https://fastapi.tiangolo.com/tutorial/request-files/

Python Software Foundation. (s. f.). *venv—Creation of virtual environments*. Python 3.12 documentation. https://docs.python.org/3.12/library/venv.html

PyTorch. (s. f.). *Previous PyTorch versions*. https://pytorch.org/get-started/previous-versions/

systemd. (s. f.-a). *systemd.service—Service unit configuration*. https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html

systemd. (s. f.-b). *systemd.syntax—General syntax of systemd configuration files*. https://www.freedesktop.org/software/systemd/man/latest/systemd.syntax.html

Uvicorn. (s. f.). *Settings*. https://uvicorn.dev/settings/

---


## 4. Operación: API y pruebas


### Referencia de endpoints locales

*Fuente: [`docs/operacion/API.md`](docs/operacion/API.md)*


[Índice](docs/INDICE.md) · [Validación](docs/evaluacion/VALIDACION.md) · [Resumen](<docs/resumen/RESUMEN-PROYECTO.md>)

Referencia contrastada con los handlers del código el **23-10-2026**. Las respuestas JSON son las de la implementación actual; no existe un contrato OpenAPI para los paneles. La API CPU y la API de pruebas publican `/openapi.json` y `/docs`. La validación HTTP realizada fue de consulta; los POST se revisaron mediante código y pruebas automatizadas.

##### Monitor de entrenamiento — puerto 8090

Implementación: [`monitor.py`](utilidades-entrenamiento/monitor.py). Los POST requieren `X-Requested-With: monitor`. Ese encabezado es una protección contra solicitudes de otros sitios, no autenticación de usuarios.

| Método | Ruta | Uso / parámetros |
|---|---|---|
| GET | `/` | Panel HTML |
| GET | `/api/status` | Proceso controlado por el monitor, PID, retorno y log |
| GET | `/api/runs` | Identificadores de ejecuciones |
| GET | `/api/run/{run_id}` | Configuración, métricas, progreso, test y conteos de imágenes |
| GET | `/api/models` | Ejecuciones con checkpoint disponible |
| GET | `/api/configs` | Configuraciones YAML disponibles en `/app/configs/` |
| GET | `/api/eval?run={run_id}&split={split}` | Estado y resultado guardado de evaluación |
| POST | `/api/start?config={nombre}` | Iniciar entrenamiento con la configuración elegida (`default.yaml` por defecto) |
| POST | `/api/continue?run={run_id}&strategy={strategy}&config={nombre}` | Crear fase desde `best.pt`; `fine_tune` o `heads_only` |
| POST | `/api/stop` | Detener el proceso de entrenamiento gestionado |
| POST | `/api/predict?run={run_id}` | Bytes de una imagen en el cuerpo, máximo 10 MB según mensaje del monitor |
| POST | `/api/eval?run={run_id}&split={split}` | Iniciar evaluación; split `train`, `val` o `test` |

Los IDs de ejecución se validan y deben referir a los artefactos locales. El parámetro `config` acepta nombres de `*.yaml` dentro de `/app/configs/` (por ejemplo `desde-cero.yaml`); los valores fuera de ese patrón se rechazan. La predicción del monitor recibe bytes, no el multipart de una imagen de la API independiente. Un entrenamiento iniciado fuera del monitor no queda bajo su control de procesos.

Ejemplo de consulta sin iniciar trabajos:

```bash
curl --fail-with-body http://127.0.0.1:8090/api/models
```

##### Curación del dataset — puerto 8787

Implementación: [`dashboard.py`](utilidades-entrenamiento/modelo-general-destilacion/dashboard.py). Acepta Host `localhost` o `127.0.0.1`. Los POST requieren `Origin` HTTP coincidente con Host y `Content-Type: application/json`; el cuerpo debe ser un objeto JSON de 1 byte a 1 MB.

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

`provider` de ingesta admite `none`, `nim` o `deepseek`; el límite por lote del panel es 1–15.000. Los proveedores remotos requieren clave y ambas confirmaciones. La detención espera a que termine la solicitud activa. El flujo de selección de ambos proveedores se describe en la [guía de curación](utilidades-entrenamiento/modelo-general-destilacion/README.md).

No existe `/api/status` en este panel: consultar `/api/overview` o `/api/jobs`.

```bash
curl --fail-with-body http://127.0.0.1:8787/api/jobs
```

##### API independiente CPU — puerto 8081 del host

Implementación: [`inference_api.py`](utilidades-entrenamiento/inference_api.py). Dentro del contenedor escucha en 8080. No utiliza el dataset para inferir.

| Método | Ruta | Contrato |
|---|---|---|
| GET | `/health` | `{"status":"ok","device":"cpu"}` |
| GET | `/docs`, `/redoc`, `/openapi.json` | Documentación y esquema FastAPI |
| POST | `/v1/predict` | Multipart con un único archivo requerido: `garment_image` |

JPEG, PNG o WebP; máximo 10 MiB y 25 megapíxeles por archivo. Devuelve `descripcion_mas_probable`, `tipo_prenda`, `colores`, `estilos`, `umbral_multietiqueta`, `device` y `latencia_ms`. La descripción se genera con una plantilla de etiquetas. La aplicación 2.0.0 sustituye el contrato anterior de dos imágenes; ya no devuelve campos de combinación. Los errores incluyen 422 para archivos ausentes/ilegibles, 413 para tamaños excesivos y 415 para formatos no admitidos.

Arranque y ejemplo de petición: [guía de despliegue CPU](utilidades-entrenamiento/README.md#api-de-inferencia-en-una-vm-con-cpu).

Instalación directa con Python: [guía nativa](docs/instalacion/INSTALACION-NATIVA.md) y [manual DOCX APA 7](docs/instalacion/Instalacion_nativa_API_prendas_APA7.docx). En instalación nativa se recomienda enlazar `127.0.0.1:8081` con Uvicorn.

##### API de pruebas (DSR) — puerto 8082 del host

Implementación: [`test_api.py`](utilidades-entrenamiento/test_api.py). Ejecuta la prueba de la API de descripción de prendas sobre el conjunto portable [`tests/imagenes-test/`](tests/imagenes-test), sin usar el dataset completo. Diseño: [DSR-PRUEBA-API.md](docs/operacion/DSR-PRUEBA-API.md).

| Método | Ruta | Contrato |
|---|---|---|
| GET | `/health` | Estado, checkpoint y total de imágenes del manifest |
| GET | `/docs`, `/openapi.json` | Documentación y esquema FastAPI |
| GET | `/test/design` | Resumen JSON del diseño DSR |
| GET | `/test/design/markdown` | Documento de diseño DSR en Markdown |
| GET | `/test/manifest` | Resumen del manifest: clases, conteos por tipo, sin color/estilo |
| GET | `/test/informe?run_id=` | Evidencia completa para el informe y el Anexo G (DSRM, R11, control, fórmulas, matriz comparativa) |
| GET | `/test/images?page=1&page_size=50` | Lista paginada de imágenes y etiquetas de referencia |
| POST | `/test/run?max_images=10&device=cpu` | Ejecuta la prueba (completa o limitada) y guarda el reporte |
| GET | `/test/results` | Reportes guardados con su promedio macro |
| GET | `/test/results/{run_id}` | Reporte completo guardado |

`max_images` opcional permite una prueba de humo; `device` admite `cpu` (por defecto) o `cuda`. Los reportes se guardan en `tests/resultados/reporte_*.json` (carpeta ignorada por Git). Ejemplo:

```bash
curl -X POST "http://127.0.0.1:8082/test/run?max_images=10"
curl "http://127.0.0.1:8082/test/results"
```

---


### Diseño de prueba (DSR) — API de descripción de prendas

*Fuente: [`docs/operacion/DSR-PRUEBA-API.md`](docs/operacion/DSR-PRUEBA-API.md)*


Prueba basada en la Tabla 6 del informe y en [`EVALUACION-ENTRENAMIENTO.md`](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md). Metodología: **Design Science Research (DSR)**.

##### 1. Problema y motivación
Medir si la API de descripción de prendas (MobileNetV3-Small, inferencia en CPU) reconoce **tipo, color y estilo** en fotografías que no usó para entrenar, y poder reproducir esa prueba en el **equipo de producción**, no solo en el nodo de entrenamiento.

##### 2. Objetivos de la solución
- Reproducir la evaluación reportada: tipo **94,94 %**, color Jaccard **68,42 %**, estilo Jaccard **69,21 %**, macro **77,52 %**.
- Ejecutar la prueba mediante una API, sobre un conjunto portable versionado en Git.

##### 3. Diseño y desarrollo (artefacto)
- **API de pruebas** (`test-api`, puerto 8082): servicio [`test_api.py`](utilidades-entrenamiento/test_api.py).
- **Conjunto portable de test**: [`tests/imagenes-test/`](tests/imagenes-test) con 1.424 imágenes y `manifest.json` (etiquetas de referencia y SHA-256 de cada imagen).

##### 4. Diseño de la prueba
- **Muestra:** 1.424 imágenes (una por prenda, split `test` fijo). 1.418 tienen color y estilo anotados; 6 no tienen color/estilo.
- **Instrumento:** `POST /test/run` en CPU. No entrena ni modifica pesos; guarda el SHA-256 del manifest como trazabilidad.
- **Predicción:** tipo = clase de mayor probabilidad; color y estilo = etiquetas con probabilidad ≥ 0,5.

##### 5. Evaluación (métricas)
- **Tipo:** exactitud = tipos correctos / total.
- **Color y estilo:** coincidencia parcial (Jaccard) = media por imagen de |P∩R| / |P∪R| (1 si ambos vacíos).
- **Promedio macro:** media simple de tipo, color y estilo; cada propiedad pesa 1/3.
- **Criterio de aceptación (R11):** promedio macro **≥ 70 %**.

##### 6. Demostración
```bash
docker compose up -d --build test-api
curl -X POST "http://127.0.0.1:8082/test/run?max_images=10"   # prueba de humo
curl -X POST "http://127.0.0.1:8082/test/run"                  # prueba completa
```
Resultado esperado (completo): tipo 94,94 %, color Jaccard 68,42 %, estilo Jaccard 69,21 %, macro 77,52 % (± tolerancia de implementación).

##### 7. Comunicación
La prueba se considera satisfactoria si el macro es **≥ 70 %** y las métricas reproducen las del informe. El JSON de resultados se guarda en [`tests/resultados/`](tests/resultados) y este diseño queda como evidencia. Aplican las limitaciones conocidas: etiquetas de color/estilo generadas por IA, desbalance de clases y casi duplicados entre splits.

---


### README-TEST — Ejecutar la prueba de la API de descripción de prendas

*Fuente: [`docs/operacion/README-TEST.md`](docs/operacion/README-TEST.md)*


Guía rápida de la prueba diseñada en [`DSR-PRUEBA-API.md`](docs/operacion/DSR-PRUEBA-API.md). La prueba mide si la API de descripción de prendas (MobileNetV3-Small, CPU) reconoce **tipo, color y estilo** en imágenes que no usó para entrenar, y está pensada para ejecutarse en el **equipo de producción**, sin el dataset completo.

##### Qué se necesita

- Docker con Compose.
- El checkpoint compartido (ya versionado en Git): `utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt`.
- El conjunto portable de test (ya versionado en Git): [`tests/imagenes-test/`](tests/imagenes-test) con 1.424 imágenes y `manifest.json`.

##### Arranque

```bash
docker compose up -d --build test-api
```

La API de pruebas queda en **http://127.0.0.1:8082/docs**.

##### Ejecutar la prueba

```bash
# Prueba de humo (10 imágenes)
curl -X POST "http://127.0.0.1:8082/test/run?max_images=10"

# Prueba completa (1.424 imágenes)
curl -X POST "http://127.0.0.1:8082/test/run"
```

Los reportes quedan en `tests/resultados/reporte_*.json` y se listan con:

```bash
curl "http://127.0.0.1:8082/test/results"
```

Para obtener en un solo JSON toda la evidencia que requiere el informe y el Anexo G (correspondencia DSRM, R11, condiciones de control, fórmulas, conjunto de prueba, trazabilidad y matriz comparativa):

```bash
curl "http://127.0.0.1:8082/test/informe"
```

##### Endpoints principales

| Método | Ruta | Uso |
|---|---|---|
| GET | `/health` | Estado, checkpoint y total del manifest |
| GET | `/test/design` | Resumen JSON del diseño DSR |
| GET | `/test/design/markdown` | Diseño DSR en Markdown |
| GET | `/test/manifest` | Clases y conteos del conjunto de test |
| GET | `/test/informe` | Evidencia completa para el informe y el Anexo G (DSRM, R11, fórmulas, matriz comparativa) |
| GET | `/test/images` | Lista paginada de imágenes y etiquetas |
| POST | `/test/run` | Ejecuta la prueba; `max_images` y `device` opcionales |
| GET | `/test/results` | Reportes guardados |
| GET | `/test/results/{run_id}` | Reporte completo |

##### Resultado esperado (prueba completa)

| Propiedad | Métrica | Valor |
|---|---|---|
| Tipo de prenda | Exactitud | 94,94 % (1.352 / 1.424) |
| Color | Jaccard parcial | 68,42 % |
| Estilo | Jaccard parcial | 69,21 % |
| **Promedio macro** | Media de las tres | **77,52 %** |

**Criterio de aceptación (R11):** promedio macro ≥ 70 %. La prueba queda satisfecha con el checkpoint compartido (77,52 %).

El detalle de cómo se construyó y ejecutó la prueba está en [`README-PRUEBA.md`](docs/operacion/README-PRUEBA.md).

---


### README-PRUEBA — Cómo se hizo la prueba de la API de descripción de prendas

*Fuente: [`docs/operacion/README-PRUEBA.md`](docs/operacion/README-PRUEBA.md)*


Documento de detalle (máximo dos páginas) de la prueba reportada en la Tabla 6 del informe y reproducida con la API de pruebas. La metodología sigue Design Science Research; el diseño de una página está en [`DSR-PRUEBA-API.md`](docs/operacion/DSR-PRUEBA-API.md).

##### 1. Objetivo y problema

Medir qué porcentaje de las propiedades de una prenda (**tipo, color y estilo**) reconoce el clasificador MobileNetV3-Small en fotografías que **no** usó para entrenar, y que esa medición pueda reproducirse en el equipo de producción y no solo en el nodo de entrenamiento.

##### 2. Conjunto de datos y muestra

El modelo se construyó con un dataset de 17.000 imágenes, etiquetadas con ayuda de **NVIDIA NIM** (6,6 %) y **DeepSeek** (93,4 %). Tras la curación y aprobación quedaron **14.456 prendas aprobadas y aptas**, repartidas en una partición fija:

| Split | Prendas |
|---|---:|
| train | 11.616 |
| val | 1.416 |
| test | 1.424 |

La prueba usa el **split test completo: 1.424 imágenes** (una por prenda, en su mayoría fotografías de catálogos públicos). De ellas, **1.418** tienen color y estilo anotados; 6 no tienen color/estilo. El test no se usó para elegir checkpoint ni umbral (0,5 fijo). Para el equipo de producción, esas 1.424 imágenes y sus etiquetas de referencia se exportaron a [`tests/imagenes-test/`](tests/imagenes-test) con un `manifest.json` que guarda el SHA-256 de cada imagen.

##### 3. Instrumento y predicción

- **Nodo de entrenamiento:** [`utilidades-entrenamiento/evaluate_properties.py`](utilidades-entrenamiento/evaluate_properties.py), que lee `dataset/metadata.sqlite` y el checkpoint, infiere en CPU y no modifica pesos.
- **Equipo de producción:** [`utilidades-entrenamiento/test_api.py`](utilidades-entrenamiento/test_api.py), que ejecuta la misma prueba sobre `tests/imagenes-test/` mediante `POST /test/run`.
- **Predicción:** tipo = clase de mayor probabilidad (softmax/argmax); color y estilo = etiquetas con probabilidad (sigmoide) ≥ **0,5**.

##### 4. Cálculos

Con `T` imágenes, `P_i` el conjunto predicho y `R_i` el conjunto real:

- **Tipo:** exactitud = tipos correctos / `T`.
- **Color y estilo — exacta:** `#{i : P_i = R_i} / T`.
- **Color y estilo — parcial (Jaccard):** `(1/T) · Σ |P_i ∩ R_i| / |P_i ∪ R_i|` (1 si ambos vacíos). Ejemplo: real {azul}, predicho {azul, blanco} → 0,5.
- **Promedio macro:** media simple de tipo, Jaccard de color y Jaccard de estilo; cada propiedad pesa 1/3.
- **Criterio de aceptación (R11):** promedio macro ≥ **70 %**.

##### 5. Ejecución

```bash
# Nodo de entrenamiento (dataset completo)
docker compose -f utilidades-entrenamiento/docker-compose.yaml run --rm --no-deps \
  --entrypoint python train /app/evaluate_properties.py \
  --checkpoint /app/modelos-compartidos/mobilenetv3-small-best.pt \
  --split test --device cpu \
  --output /app/modelo-ia/evaluaciones/evaluacion_propiedades_test.json

# Equipo de producción (conjunto portable)
docker compose up -d --build test-api
curl -X POST "http://127.0.0.1:8082/test/run"
```

Ambas rutas guardan un JSON con el SHA-256 de la fuente de verdad (SQLite en el nodo, `manifest.json` en producción) para trazabilidad.

##### 6. Resultados (test, CPU)

| Propiedad | Métrica | Checkpoint compartido (época 15) |
|---|---|---|
| Tipo | Exactitud | **94,94 %** (1.352 / 1.424) |
| Color | Exacta | 53,88 % (764 / 1.418) |
| Color | Jaccard parcial | **68,42 %** |
| Estilo | Exacta | 47,53 % (674 / 1.418) |
| Estilo | Jaccard parcial | **69,21 %** |
| **Promedio macro** | Media de las tres | **77,52 %** |

La API de pruebas reproduce estos valores de forma idéntica sobre `tests/imagenes-test/` (verificado el 26-10-2026).

##### 7. Conclusión y limitaciones

El promedio macro de **77,52 %** supera el criterio R11 (≥ 70 %), por lo que la prueba se considera satisfactoria. Limitaciones a tener presentes:

1. **Etiquetas de IA:** color y estilo los generaron NVIDIA NIM y DeepSeek; la prueba mide concordancia con esas anotaciones, no con una referencia humana.
2. **Desbalance:** blusa 43,8 % y falda 2,4 % de la muestra de test; falda (28) y suéter (42) tienen pocos ejemplos.
3. **Casi duplicados:** 77 imágenes de test (5,4 %) tienen una casi idéntica en train; al excluirlas el macro baja a 76,96 %.
4. **Exacta frente a parcial:** con coincidencia exacta, color y estilo quedan por debajo de 70 %; solo el macro con Jaccard supera el criterio.
5. **Dominio:** fotos de catálogo, no de una persona vistiendo la prenda.

---


## 5. Dataset y taxonomía


### Documentación del dataset

*Fuente: [`documentacion_dataset/README.md`](documentacion_dataset/README.md)*


Esta carpeta documenta la estructura de imágenes y el registro de metadatos en SQLite para el módulo de reconocimiento de prendas.

##### Fuente de verdad

- Las imágenes permanecen en carpetas organizadas por zona y tipo de prenda dentro de `dataset/`.
- Los datos de cada prenda, las rutas a sus imágenes y las etiquetas se guardan en `dataset/metadata.sqlite`.
- No se usa un JSON por prenda ni un CSV como fuente de verdad. El archivo `descripcion.json` puede usarse solo como formato de intercambio si se desarrolla una importación/exportación explícita.
- [`schema.sql`](documentacion_dataset/schema.sql) define las siete tablas y las propiedades iniciales. [`crear_estructura.sh`](documentacion_dataset/crear_estructura.sh) prepara los directorios y crea la base a partir de ese esquema.

Para una visión del objetivo global y del flujo de entrenamiento, consulta el [README vigente del proyecto](README.md). El [índice del dataset](dataset/README.md) enlaza las guías de clasificación por zona y tipo.

##### Estructura de carpetas

Desde la raíz del proyecto, ejecutar:

```bash
bash documentacion_dataset/crear_estructura.sh
```

Para ejecutarlo desde otro directorio, indica la ruta del script. Este resuelve la raíz del proyecto a partir de su propia ubicación. Requiere Python 3 con su módulo estándar `sqlite3`. Es idempotente: crea carpetas faltantes, conserva archivos/directorios existentes y crea o completa las tablas y el catálogo sin borrar datos. Aplica la migración aditiva de `prenda_imagen.etiqueta_fuente` si falta; cualquier otro cambio futuro de esquema requiere una migración explícita.

```text
dataset/
├── metadata.sqlite
├── superior/
│   ├── abrigos/
│   ├── blusas/
│   ├── camisas/
│   ├── chaquetas/
│   └── sueteres/
├── inferior/
│   ├── faldas/
│   │   ├── FALDA-1/
│   │   └── FALDA-2/
│   ├── pantalones/
│   └── shorts/
└── inferior_superior/
    └── vestido/
```

Cada carpeta identificada (`FALDA-1`, `CAMISA-1`, etc.) representa una prenda física. Guarda dentro sus imágenes, por ejemplo:

```text
dataset/inferior/faldas/FALDA-1/
├── frente.jpg
├── espalda.jpg
└── detalle.jpg
```

`metadata.sqlite` se crea en `dataset/` al ejecutar el script. La base, las imágenes locales, los pesos y los resultados de experimentos están excluidos de Git por [`.gitignore`](.gitignore); conserva en Git las guías README y el esquema.

La categoría `camisa` reúne camisas y camisetas bajo una sola etiqueta y carpeta (`superior/camisas/`). El catálogo inicial tiene nueve tipos: abrigo, blusa, camisa, chaqueta, falda, pantalón, short, suéter y vestido.

En el pipeline de fuentes externas, `camisa` y `camiseta` se normalizan a la misma categoría canónica `camisa` antes de calcular el análisis y guardar/importar la imagen. No se crea una clase o carpeta `camisetas`; la etiqueta original del dataset externo permanece en `prenda_imagen.etiqueta_fuente` para conservar su procedencia. La guía operativa de las fuentes, el límite de lote y los fallbacks de proveedores está en [`modelo-general-destilacion/README.md`](utilidades-entrenamiento/modelo-general-destilacion/README.md).

##### Modelo de datos SQLite

Relaciones:

```text
prenda 1 ─── N prenda_imagen
prenda 1 ─── N valor_propiedad_prenda N ─── 1 catalogo_propiedad
```

- **`prenda`**: una fila por prenda física. Conserva código, carpeta/categoría, split de entrenamiento y estado de revisión.
- **`prenda_imagen`**: una fila por foto. Relaciona una prenda con una o varias rutas relativas a `dataset/`.
  - `fuente` y `etiqueta_fuente` registran el dataset de origen y su etiqueta original cuando la imagen procede de una fuente externa.
- **`catalogo_propiedad`**: define las propiedades permitidas, por ejemplo `tipo_prenda`, `color`, `estilo`, `largo` o `patron`; puede documentar opciones admitidas en `valores_permitidos`.
- **`valor_propiedad_prenda`**: relaciona cada prenda con el valor de una propiedad. Las propiedades con varios valores usan varias filas; por ejemplo, una prenda con dos colores tiene dos valores asociados a la propiedad `color`.
- **`descripcion_prenda`**: almacena descripciones y sugerencias de atributos generadas por servicios de IA, junto con proveedor, modelo y estado de revisión. Las sugerencias empiezan pendientes y no sustituyen etiquetas aprobadas.
- **`analisis_imagen`**: registra decisiones válidas de análisis visual por huella de imagen, clase, proveedor/modelo y versión de prompt. Guarda aceptaciones y descartes para evitar pagar y repetir la misma inferencia; errores HTTP/red y respuestas inválidas no se cachean. Una imagen puede tener análisis de más de un proveedor o modelo por una evaluación cruzada o un fallback; la fila identifica cuál produjo cada resultado.
- **`pipeline_config`**: almacena el prompt editable del pipeline; claves API no se almacenan en SQLite.

El esquema completo e inicialización del catálogo están en [`schema.sql`](documentacion_dataset/schema.sql). SQLite debe abrirse con claves foráneas activadas (`PRAGMA foreign_keys = ON`) en cada conexión. Las rutas de imágenes son relativas al directorio `dataset/`, nunca rutas absolutas de una laptop. El pipeline de datasets externos documenta el uso de `descripcion_prenda` en [`modelo-general-destilacion/`](utilidades-entrenamiento/modelo-general-destilacion/README.md).

###### Ejemplo conceptual

Prenda `FALDA-1`:

| Tabla | Filas relacionadas |
|---|---|
| `prenda` | `FALDA-1`, categoría `inferior/faldas`, split `train` |
| `prenda_imagen` | `inferior/faldas/FALDA-1/frente.jpg`, `.../espalda.jpg` |
| `valor_propiedad_prenda` | `tipo_prenda = falda`, `color = azul`, `estilo = elegante`, `largo = midi` |
| `catalogo_propiedad` | Define que `tipo_prenda`, `color`, `estilo` y `largo` son propiedades válidas |

Cada etiqueta se debe elegir del vocabulario acordado. `valores_permitidos` es un JSON con las opciones iniciales propuestas; el equipo debe revisarlas antes de usarlas. Tipo de prenda es una propiedad de valor único; color y estilo permiten varios valores. Si una propiedad está marcada como de valor único, la aplicación de anotación debe impedir agregar más de un valor a la misma prenda.

###### Ejemplo de registro SQL

Con la base inicializada con `schema.sql`, se puede registrar una prenda con dos fotos, un tipo, dos colores y un estilo así:

```sql
PRAGMA foreign_keys = ON;
BEGIN;

INSERT INTO prenda
    (codigo, ruta_categoria, split, estado_revision, apta_para_entrenamiento)
VALUES
    ('FALDA-1', 'inferior/faldas', 'train', 'aprobado', 1);

INSERT INTO prenda_imagen
    (id_prenda, ruta_relativa, vista, es_fotografia_real, fuente, permiso_uso)
SELECT id_prenda, 'inferior/faldas/FALDA-1/frente.jpg',
       'frente', 1, 'propia', 'documentado'
FROM prenda WHERE codigo = 'FALDA-1';

INSERT INTO prenda_imagen
    (id_prenda, ruta_relativa, vista, es_fotografia_real, fuente, permiso_uso)
SELECT id_prenda, 'inferior/faldas/FALDA-1/espalda.jpg',
       'espalda', 1, 'propia', 'documentado'
FROM prenda WHERE codigo = 'FALDA-1';

INSERT INTO valor_propiedad_prenda (id_prenda, id_propiedad, valor)
SELECT p.id_prenda, cp.id_propiedad, etiquetas.valor
FROM prenda AS p
JOIN catalogo_propiedad AS cp
JOIN (SELECT 'tipo_prenda' AS propiedad, 'falda' AS valor
      UNION ALL SELECT 'color', 'azul'
      UNION ALL SELECT 'color', 'negro'
      UNION ALL SELECT 'estilo', 'elegante') AS etiquetas
  ON cp.codigo = etiquetas.propiedad
WHERE p.codigo = 'FALDA-1';

COMMIT;
```

##### Cómo registrar una prenda

1. Escoge la zona y el tipo adecuados: `superior/`, `inferior/` o `inferior_superior/`.
2. Crea una carpeta de prenda con código único, por ejemplo `dataset/inferior/faldas/FALDA-3/`.
3. Copia en esa carpeta una o varias fotos autorizadas de la misma prenda. Usa nombres descriptivos, sin espacios y con extensión real (`frente.jpg`, `espalda.jpg`).
4. Inserta una fila en `prenda` con el código, la ruta de categoría, el split y estado de revisión.
5. Inserta una fila en `prenda_imagen` por cada imagen, con su ruta relativa, vista, fuente/permiso y si es una fotografía real.
6. Registra cada etiqueta como una fila en `valor_propiedad_prenda`, ligada al registro correspondiente de `catalogo_propiedad`.
7. Aprueba la muestra solo cuando la categoría, las etiquetas, las imágenes y los permisos estén revisados.
8. Mantén todas las fotos de una prenda en el mismo split (`train`, `val` o `test`). La división se guarda en `prenda`, no por foto.

No inventar etiquetas cuando algo no sea visible. Un valor ausente representa “no anotado/no determinable”; los valores negativos deben anotarse solo cuando la guía de la propiedad los defina.

##### Preparar los datos para MobileNetV3-Small

Cuando el dataset esté suficientemente completo y revisado, el proceso de entrenamiento deberá:

1. Abrir `dataset/metadata.sqlite` con claves foráneas activadas.
2. Seleccionar prendas aprobadas y aptas para entrenamiento, con split definido.
3. Consultar sus valores en `valor_propiedad_prenda` y el nombre/tipo en `catalogo_propiedad`.
4. Consultar las rutas de sus fotos en `prenda_imagen`, comprobar que existan bajo `dataset/` y excluir ilustraciones/demo.
5. Cargar imágenes, redimensionarlas al tamaño configurado y construir el lote de MobileNetV3-Small.
6. Entrenar tipo de prenda como clasificación de una etiqueta y colores/estilos como clasificación multi-etiqueta.
7. Mantener todas las fotos de la misma prenda en el split indicado en `prenda`.
8. Guardar pesos, configuración y métricas en `utilidades-entrenamiento/modelo-ia/`, fuera del dataset.

Los ejemplos de documentación no sustituyen fotografías reales autorizadas ni son suficientes para entrenar. Los scripts Docker de entrenamiento ya están implementados; el estado comprobado se mantiene en [validación](docs/evaluacion/VALIDACION.md).

##### Factibilidad y alcance del MVP

Estado comprobado el **23-10-2026**: hay **14.456 prendas aprobadas y aptas** (11.616 train, 1.416 val y 1.424 test), checkpoints entrenados y evaluación registrada. Los registros iniciales del 17 de octubre, cuando ninguna muestra estaba habilitada, son un antecedente superado.

- El esquema base tiene siete tablas y el módulo de duplicados añade tres auxiliares. SQLite también puede crear `sqlite_sequence` internamente.
- Las nueve clases están contempladas por el modelo. Sujetadores, ropa interior y ropa de baño, mencionados como orientación de zona en algunas guías, quedan fuera del catálogo actual.
- La importación deja prendas pendientes; existe aprobación masiva mediante `approve-generated`. Una fila aprobada no acredita revisión humana individual ni permiso documentalmente verificado. El entrenador filtra estado, aptitud, split, fotografía real y etiquetas, pero no audita documentación de licencia.
- La configuración actual usa 224 px, batch 64 y ajuste fino; no es una garantía de compatibilidad con equipos de poca VRAM. Consultar `configs/default.yaml` y probar recursos antes de entrenar.
- La revisión encontró referencias huérfanas en grupos de duplicados y archivos ausentes solo en prendas rechazadas. Todas las imágenes aprobadas están presentes; la integridad física de SQLite y la integridad de sus relaciones son comprobaciones distintas.

El detalle de consultas, pruebas y límites está en [validación](docs/evaluacion/VALIDACION.md). Los resultados y sus limitaciones están en [evaluación](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md). Para operar, seguir la [guía de entrenamiento](utilidades-entrenamiento/README.md) o la [guía de curación](utilidades-entrenamiento/modelo-general-destilacion/README.md). Antes de entrenar con nuevas incorporaciones, revisar etiquetas, procedencia y separación de duplicados entre splits.

##### Archivos de esta carpeta

- [`crear_estructura.sh`](documentacion_dataset/crear_estructura.sh): crea carpetas y base SQLite sin borrar ni sobrescribir contenido existente.
- [`schema.sql`](documentacion_dataset/schema.sql): crea las siete tablas e inserta las propiedades iniciales.

---


### Dataset de prendas

*Fuente: [`dataset/README.md`](dataset/README.md)*


Las imágenes se organizan por zona del cuerpo y tipo de prenda. Las etiquetas, propiedades, estado de revisión y rutas de imagen se registran en SQLite; no se usa un JSON o CSV por prenda como fuente de verdad.

**Estado comprobado al 23-10-2026:** 14.456 prendas aprobadas y aptas; véase [validación](docs/evaluacion/VALIDACION.md).

**Antecedente histórico:** en una lectura de SQLite del 17 de octubre de 2026, todas las prendas existentes estaban pendientes de revisión y ninguna estaba habilitada para entrenamiento; la importación puede continuar, así que consulta SQLite para los conteos actuales. La respuesta de una API o la importación de una imagen no equivale a una etiqueta aprobada. Consulta el estado y los criterios de habilitación en la [guía general del dataset](documentacion_dataset/README.md#factibilidad-y-alcance-del-mvp), y el proceso de sugerencias en el [pipeline de curación](utilidades-entrenamiento/modelo-general-destilacion/README.md).

Consulta la [documentación del dataset](documentacion_dataset/README.md) para:

- Crear las carpetas y `metadata.sqlite` con [`crear_estructura.sh`](documentacion_dataset/crear_estructura.sh).
- Consultar las siete tablas y las etiquetas iniciales en [`schema.sql`](documentacion_dataset/schema.sql).
- Registrar prendas, imágenes, propiedades y descripciones revisables en SQLite.
- Preparar los datos para entrenar MobileNetV3-Small.

Guías de clasificación por zona: [superior](dataset/superior/README.md), [inferior](dataset/inferior/README.md) e [inferior_superior](dataset/inferior_superior/README.md). Cada tipo también tiene una guía dentro de su propia carpeta.

La taxonomía actual de carpetas y del catálogo es el alcance inicial, no el inventario completo de prendas posible. `camiseta` no es una carpeta/clase separada: se normaliza a `camisa`, conservando la etiqueta original de la fuente en SQLite. Consulta la sección de [factibilidad y alcance](documentacion_dataset/README.md#factibilidad-y-alcance-del-mvp) antes de añadir nuevas categorías.

---


### Prendas de la parte inferior

*Fuente: [`dataset/inferior/README.md`](dataset/inferior/README.md)*


Guarda aquí las categorías que cubren principalmente cintura y piernas: pantalones, shorts, faldas, ropa interior inferior y partes inferiores de ropa de baño.

Usa la subcarpeta específica y sigue su guía. Un vestido de una pieza va en `inferior_superior/`. Color y estilo se registran como atributos, no como categorías de prenda.

Guías por tipo: [faldas](dataset/inferior/faldas/README.md), [pantalones](dataset/inferior/pantalones/README.md) y [shorts](dataset/inferior/shorts/README.md). Para registrar prendas y etiquetas, consulta la [guía general](documentacion_dataset/README.md); vuelve al [índice del dataset](dataset/README.md) para las demás zonas.

---


### Falda

*Fuente: [`dataset/inferior/faldas/README.md`](dataset/inferior/faldas/README.md)*


##### Criterio de inclusión

Prenda inferior que cubre la cintura o cadera y cae alrededor de las piernas sin formar dos perneras independientes.

##### No confundir con

- **Vestido:** integra una parte superior y una falda en una misma prenda.
- **Pantalón o short:** tienen dos perneras separadas.

El largo de la falda puede registrarse como atributo, pero no cambia la categoría principal. No inferir ocasión o estilo solo por el largo o el color.

##### Registrar faldas

Crea una carpeta por cada falda física, por ejemplo `FALDA-1/`, y guarda dentro una o más fotografías autorizadas. Registra la prenda, sus rutas de imagen y sus propiedades en SQLite según la [guía de llenado](documentacion_dataset/README.md). No se usa `descripcion.json` como fuente de verdad.

Para la ubicación y el catálogo de categorías, consulta la [guía de prendas inferiores](dataset/inferior/README.md); para el flujo de preparación, consulta también el [índice del dataset](dataset/README.md).

---


### Pantalón

*Fuente: [`dataset/inferior/pantalones/README.md`](dataset/inferior/pantalones/README.md)*


##### Criterio de inclusión

Prenda inferior que cubre ambas piernas por separado desde la cintura o cadera. Puede ser largo, corto hasta el tobillo o de distintos cortes.

##### No confundir con

- **Short:** prenda inferior que termina claramente por encima de la rodilla.
- **Falda:** cubre la parte inferior sin separar las piernas en dos perneras.

Si la foto no muestra suficiente longitud para decidir entre pantalón y short, marcar para revisión. El corte y el estilo son atributos distintos al tipo.

Para la ubicación y el catálogo de categorías, consulta la [guía de prendas inferiores](dataset/inferior/README.md); para registrar imágenes y etiquetas, la [guía general del dataset](documentacion_dataset/README.md). Índice: [dataset](dataset/README.md).

---


### Short

*Fuente: [`dataset/inferior/shorts/README.md`](dataset/inferior/shorts/README.md)*


##### Criterio de inclusión

Prenda inferior con dos perneras que terminan claramente por encima de la rodilla.

##### No confundir con

- **Pantalón:** las perneras llegan más abajo; si el largo está oculto, no asumir.
- **Falda:** no tiene dos perneras separadas.
- **Ropa deportiva:** es un contexto o estilo de uso, no un tipo de prenda; un short deportivo sigue siendo `short`.

Registrar largo, color y estilo por separado si forman parte de las etiquetas del proyecto.

Para la ubicación y el catálogo de categorías, consulta la [guía de prendas inferiores](dataset/inferior/README.md); para registrar imágenes y etiquetas, la [guía general del dataset](documentacion_dataset/README.md). Índice: [dataset](dataset/README.md).

---


### Prendas de cuerpo completo

*Fuente: [`dataset/inferior_superior/README.md`](dataset/inferior_superior/README.md)*


Guarda aquí los vestidos: prendas de una sola pieza que integran la parte superior y una parte inferior tipo falda.

Usa la subcarpeta específica y sigue su guía. No clasifiques aquí un conjunto de dos piezas solo porque se vista junto: cada pieza debe anotarse por separado. Color y estilo son atributos independientes del tipo.

Guía: [vestidos](dataset/inferior_superior/vestido/README.md). Para registrar prendas y etiquetas, consulta la [guía general](documentacion_dataset/README.md); vuelve al [índice del dataset](dataset/README.md) para las demás zonas.

---


### Vestido

*Fuente: [`dataset/inferior_superior/vestido/README.md`](dataset/inferior_superior/vestido/README.md)*


##### Criterio de inclusión

Prenda de una pieza que integra una parte superior y una parte inferior tipo falda. Puede variar en mangas, escote, largo y ajuste.

##### No confundir con

- **Falda:** es únicamente una prenda inferior.
- **Conjunto de dos piezas:** la parte superior y la inferior son prendas separadas.

Una etiqueta como `fiesta` es estilo/uso y no sustituye el tipo `vestido`. Registrar los colores visibles aparte.

Para la ubicación y el catálogo de categorías, consulta la [guía de prendas de cuerpo completo](dataset/inferior_superior/README.md); para registrar imágenes y etiquetas, la [guía general del dataset](documentacion_dataset/README.md). Índice: [dataset](dataset/README.md).

---


### Prendas de la parte superior

*Fuente: [`dataset/superior/README.md`](dataset/superior/README.md)*


Guarda aquí las categorías de prendas que cubren principalmente el torso: camisas, blusas, chaquetas, abrigos y suéteres. En este proyecto, camisas y camisetas se agrupan bajo la única clase canónica `camisa` y se guardan en `camisas/`; no hay una carpeta/clase aparte para camisetas. La ingesta normaliza ambas etiquetas y conserva el nombre original de la fuente en SQLite.

Usa la subcarpeta específica de cada tipo y sigue su guía de etiquetado. No mezcles en una misma clase el tipo de prenda y sus atributos: por ejemplo, `camisa` es el tipo; `roja` puede ser su color y `deportiva` su estilo.

Una prenda que integre torso y parte inferior en una sola pieza corresponde a `inferior_superior/`, no a este grupo.

Las carpetas `abrigos/` y `sueteres/` son categorías distintas y ambas se crean con la estructura inicial del dataset. En la importación automática, una etiqueta fuente ambigua como `Outwear` no se asigna a abrigo ni a chaqueta sin revisión; las etiquetas sin equivalencia aprobada se omiten.

Guías por tipo: [abrigos](dataset/superior/abrigos/README.md), [blusas](dataset/superior/blusas/README.md), [camisas](dataset/superior/camisas/README.md), [chaquetas](dataset/superior/chaquetas/README.md) y [suéteres](dataset/superior/sueteres/README.md). Para registrar prendas y etiquetas, consulta la [guía general](documentacion_dataset/README.md); vuelve al [índice del dataset](dataset/README.md) para las demás zonas.

---


### Abrigo

*Fuente: [`dataset/superior/abrigos/README.md`](dataset/superior/abrigos/README.md)*


##### Criterio de inclusión

Prenda exterior diseñada para cubrir otras prendas y proporcionar una capa amplia; suele ser más larga o pesada que una chaqueta.

##### No confundir con

- **Chaqueta:** generalmente más corta o ligera.
- **Suéter:** prenda de punto que normalmente se viste como capa intermedia y no tiene la estructura típica de un abrigo.

El peso, material y propósito térmico no siempre pueden confirmarse solo por una foto. Etiquetar únicamente lo visible y registrar incertidumbre cuando corresponda.

La etiqueta fuente `Outwear` no se asigna automáticamente a `abrigo`: también puede describir chaquetas. Se omite durante la importación hasta que exista una equivalencia revisada.

Para la ubicación y el catálogo de categorías, consulta la [guía de prendas superiores](dataset/superior/README.md); para registrar imágenes y etiquetas, la [guía general del dataset](documentacion_dataset/README.md). Índice: [dataset](dataset/README.md).

---


### Blusa

*Fuente: [`dataset/superior/blusas/README.md`](dataset/superior/blusas/README.md)*


##### Criterio de inclusión

Prenda superior de diseño tipo blusa, normalmente de tela ligera o con detalles como pliegues, lazos, frunces o mangas decorativas. Puede tener cuello y abertura frontal.

##### No confundir con

- **Camisa:** es la clase unificada para prendas estructuradas con abertura frontal y para prendas cerradas de construcción sencilla. Usa `blusa` cuando el diseño visible corresponda a una blusa.

La etiqueta describe el tipo visible, no la formalidad, el género de quien la usa ni el material exacto. Registrar color y estilo como etiquetas independientes.

Para la ubicación y el catálogo de categorías, consulta la [guía de prendas superiores](dataset/superior/README.md); para registrar imágenes y etiquetas, la [guía general del dataset](documentacion_dataset/README.md). Índice: [dataset](dataset/README.md).

---


### Camisa (clase unificada)

*Fuente: [`dataset/superior/camisas/README.md`](dataset/superior/camisas/README.md)*


##### Criterio de inclusión

Clase única para prendas superiores con abertura frontal y cuello, así como prendas superiores cerradas sin abertura frontal completa. Incluye las variantes que comúnmente se denominan camisetas; todas se registran como `camisa` en `dataset/superior/camisas/`. Durante la ingesta, la etiqueta de fuente `camiseta` se normaliza a `camisa`; el nombre original se conserva en `prenda_imagen.etiqueta_fuente` para trazabilidad.

##### No confundir con

- **Blusa:** prenda superior cuyo diseño y construcción se etiquetan como blusa, aunque también tenga botones.
- **Chaqueta:** prenda exterior pensada para llevar sobre otra prenda.

No se separa esta clase por tipo de cuello, abertura o construcción. Si no se distingue con seguridad entre camisa y otra categoría, marcar para revisión. Etiquetar color y estilo por separado.

Para la ubicación y el catálogo de categorías, consulta la [guía de prendas superiores](dataset/superior/README.md); para registrar imágenes y etiquetas, la [guía general del dataset](documentacion_dataset/README.md). Índice: [dataset](dataset/README.md).

---


### Chaqueta

*Fuente: [`dataset/superior/chaquetas/README.md`](dataset/superior/chaquetas/README.md)*


##### Criterio de inclusión

Prenda exterior que cubre el torso y suele abrirse por delante. Puede tener mangas y distintos cierres; normalmente es más corta y ligera que un abrigo, aunque puede variar.

##### No confundir con

- **Abrigo:** suele ser más largo, grueso o destinado a cubrir otras capas.
- **Camisa o blusa:** prendas superiores que normalmente se llevan como capa interior o principal, no como prenda exterior.
- **Sudadera:** si se desea distinguirla, definir una clase separada antes de anotar.

Si la diferencia entre chaqueta y abrigo no es visible, marcar para revisión en lugar de adivinar.

Para la ubicación y el catálogo de categorías, consulta la [guía de prendas superiores](dataset/superior/README.md); para registrar imágenes y etiquetas, la [guía general del dataset](documentacion_dataset/README.md). Índice: [dataset](dataset/README.md).

---


### Suéter

*Fuente: [`dataset/superior/sueteres/README.md`](dataset/superior/sueteres/README.md)*


##### Criterio de inclusión

Prenda superior de punto, normalmente de manga larga, que puede tener cuello redondo, cuello alto o abertura parcial.

##### No confundir con

- **Sudadera:** suele ser de tejido tipo felpa y puede tener capucha o bolsillo frontal.
- **Abrigo o chaqueta:** prendas exteriores con una construcción y abertura distintas.
- **Camisa de manga larga:** la clase unificada `camisa` incluye prendas cerradas de punto fino; si no se distingue con seguridad de un suéter, marcar para revisión.

No inferir composición de fibras por la imagen. Color, patrón y estilo se anotan aparte.

La etiqueta fuente `Longsleeve` no se convierte automáticamente en `sueter`: puede referirse a una camisa de manga larga. Se excluye hasta acordar una equivalencia revisada.

Para la ubicación y el catálogo de categorías, consulta la [guía de prendas superiores](dataset/superior/README.md); para registrar imágenes y etiquetas, la [guía general del dataset](documentacion_dataset/README.md). Índice: [dataset](dataset/README.md).

---


### Conjunto portable de prueba — API de descripción de prendas

*Fuente: [`tests/imagenes-test/README.md`](tests/imagenes-test/README.md)*


Carpeta con seguimiento de Git para ejecutar la prueba de la API de descripción de prendas en el **equipo de producción**, sin necesidad del dataset completo ni del nodo de entrenamiento.

##### Contenido

- `manifest.json`: catálogo de clases, umbral multietiqueta, y una entrada por imagen con:
  - `archivo`: ruta relativa a esta carpeta.
  - `codigo`: identificador de la prenda.
  - `tipo_prenda`, `colores`, `estilos`: etiquetas de referencia.
  - `sha256`: integridad de la imagen copiada.
- `inferior/`, `inferior_superior/`, `superior/`: 1.424 imágenes `.jpg` (una por prenda del split `test`), organizadas como en `dataset/`.

##### Origen

Generado desde `dataset/metadata.sqlite` con el criterio:

```
split = 'test' AND estado_revision = 'aprobado'
AND apta_para_entrenamiento = 1 AND es_fotografia_real = 1
```

Checkpoint de referencia: [`utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt`](utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt).

##### Uso

La prueba la ejecuta la API de pruebas (`test-api`, puerto 8082):

```bash
docker compose up -d --build test-api
curl -X POST "http://127.0.0.1:8082/test/run"          # prueba completa
curl "http://127.0.0.1:8082/test/results"              # reportes guardados
```

Diseño de la prueba: [`DSR-PRUEBA-API.md`](docs/operacion/DSR-PRUEBA-API.md).

---


## 6. Entrenamiento y utilidades


### Utilidades de entrenamiento

*Fuente: [`utilidades-entrenamiento/README.md`](utilidades-entrenamiento/README.md)*


[Índice documental](docs/INDICE.md) · [Validación vigente](docs/evaluacion/VALIDACION.md).

Este directorio contiene el entorno Docker Compose y los scripts para el MVP MobileNetV3-Small. El dataset y sus tablas SQLite permanecen en `../dataset/`; los checkpoints y la caché de pesos preentrenados se escriben en `modelo-ia/`. Los repositorios auxiliares descargados, si fueran necesarios, se pueden colocar en `repositorios/`; no se versionan automáticamente.

##### Equipo de referencia actual

Medición del host de entrenamiento, **18 de octubre de 2026**:

| Recurso | Especificación observada |
|---|---|
| CPU | Intel Core i7-8750H, 6 núcleos / 12 hilos, 2,20 GHz base y hasta 4,10 GHz reportados |
| GPU física | NVIDIA GeForce RTX 2060 Mobile (TU106M), identificada por PCI (`10de:1f11`); VRAM no medida |
| RAM | 15 GiB visibles por Linux (aprox. 16 GB instalados) |
| Swap | 4 GiB configurados; el uso cambia con la carga del host |
| Sistema | Ubuntu 24.04.4 LTS, x86_64 |
| Disco del proyecto | Volumen de 98 GB; 67 GB libres durante la medición |
| Entorno del modelo | PyTorch 2.5.1+cu124 en Docker; `torch.cuda.is_available()` devuelve `False`, así que esta configuración entrena con CPU pese a que el host sí tiene una RTX 2060 Mobile |
| Límite del contenedor | Sin límites explícitos de memoria, cantidad de CPU ni cpuset en Docker; compite por los recursos disponibles del host |
| Dataset válido | 12.379 imágenes train, 1.511 val y 1.529 test en la consulta del 18 de octubre de 2026 |

La GPU física está confirmada por PCI, pero no está disponible para entrenamiento: faltan `/dev/nvidia*` y `/proc/driver/nvidia`, `nvidia-smi` no está instalado y PyTorch dentro del contenedor no detecta CUDA. Hay que instalar/cargar un driver NVIDIA compatible y configurar NVIDIA Container Toolkit antes de afirmar que el entrenamiento usa la RTX. La VRAM todavía no se ha medido. El espacio libre y el uso de RAM/swap son instantáneas y deben volver a medirse antes de trabajos largos.

##### Interfaz de entrenamiento

El servicio `train` ejecuta entrenamiento por terminal y no publica puertos; por eso no aparece una URL en `docker ps`. El panel de seguimiento (`monitor`) forma parte del [Compose unificado](docker-compose.yaml); desde la raíz del proyecto:

```bash
docker compose up -d --build
```

Abre `http://127.0.0.1:8090`. El panel permite iniciar o detener el entrenamiento, revisar progreso/métricas y probar los modelos guardados. Para detener solo el panel: `docker compose stop monitor`. Si Docker corre en otra máquina, usa un túnel SSH para el puerto 8090; el panel se enlaza solo a localhost.

El dashboard de curación de datos se sirve en `http://127.0.0.1:8787` y la API CPU en `http://127.0.0.1:8081/docs`, también desde el Compose unificado; sus instrucciones están en [`modelo-general-destilacion/README.md`](utilidades-entrenamiento/modelo-general-destilacion/README.md) y en esta guía.

###### Prueba CPU de un modelo ya entrenado

En el monitor pulsa **Probar modelo en CPU**, selecciona una ejecución con `best.pt` y carga una imagen. La interfaz muestra la predicción y latencias de carga del checkpoint, preparación de imagen, inferencia y petición total. El cargador ubica el modelo en CPU y la inferencia no actualiza ni guarda pesos. Esta es una prueba funcional/latencia de **inferencia del modelo ya entrenado**; no inicia entrenamiento ni mide cuánto tardaría una época.

En el servidor revisado hay 12 CPU lógicas y 15 GiB de RAM; el dataset tenía 12.379 imágenes train, 1.511 val y 1.529 test. Una inferencia CPU exitosa permite evaluar el uso del modelo sin GPU en ese host, pero no basta para afirmar que entrenar sobre todo ese dataset en CPU sea práctico. Para eso se necesitaría un benchmark de entrenamiento separado y autorizado, que no forma parte de esta prueba.

##### Requisitos

- Docker Engine y Docker Compose v2.
- Acceso a Internet para descargar la imagen base de PyTorch y, desde el contenedor, los pesos preentrenados de MobileNetV3-Small.
- Para GPU NVIDIA: driver del host compatible con CUDA 12.4 y NVIDIA Container Toolkit. Si no hay GPU compatible, usar el servicio CPU.
- El usuario de Compose por defecto es UID/GID `1000`; para que los artefactos pertenezcan al usuario local, configura `TRAINING_UID` y `TRAINING_GID` en el entorno antes de invocar Compose si tu laptop usa otros identificadores.

##### Construir y consultar el entorno

Desde esta carpeta:

```bash
docker compose build
docker compose run --rm train status
```

`status` indica versión de PyTorch y si el contenedor detecta CUDA. El servicio predeterminado `train` no solicita GPU y es adecuado para CPU.

La imagen de entrenamiento instala sus dependencias con pip durante la construcción y requiere acceso al repositorio de paquetes; los pesos preentrenados sí se descargan al iniciar el primer entrenamiento. Si Docker avisa que el reenvío IPv4 está deshabilitado, el estado puede funcionar pero la descarga de pesos fallará hasta corregir la conectividad del daemon.

##### Entrenar

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

Los hiperparámetros predeterminados están en [`configs/default.yaml`](utilidades-entrenamiento/configs/default.yaml): MobileNetV3-Small a 224 × 224, batch 64, hasta 30 épocas, calentamiento inicial de cabezas y ajuste fino, con parada temprana. Los pesos preentrenados se guardan bajo `modelo-ia/cache/`; cada ejecución crea un directorio nuevo en `modelo-ia/runs/` con `best.pt`, `config.json` y `metrics.json`.

##### Estrategia recomendada para continuar

En el historial actual, la ejecución que registró 20 épocas guardó su mejor checkpoint en la época 15 (pérdida de validación 0,513). La ejecución posterior quedó en 7 épocas y su mejor pérdida registrada es 0,577. Por eso la recomendación es seleccionar la ejecución de 20 épocas y continuar desde su `best.pt` (época 15), no desde la ejecución parcial ni desde su última época. Esta comparación solo es válida si ambas ejecuciones usaron el mismo split de validación; verifica los artefactos y el registro de imágenes si el dataset cambió.

En el monitor, selecciona la ejecución en **Ejecución**, elige **Ajuste fino completo (recomendado)** y pulsa **Continuar desde mejor checkpoint**. Esta estrategia inicia una nueva fase de hasta 10 épocas: conserva los pesos del checkpoint, ajusta toda la red, usa tasa de aprendizaje `0.0001` para las cabezas y `0.00001` para MobileNet, y mantiene la parada temprana con paciencia 5. La ejecución nueva guarda su origen y estrategia en `config.json`; valida su checkpoint con el conjunto de validación. El conjunto `test` no se usa para escoger el checkpoint y debe reservarse para la evaluación final.

**Solo entrenar las cabezas** es la alternativa conservadora si el ajuste fino completo hace que la pérdida de validación empeore o el dataset sea muy pequeño: mantiene congelada la base MobileNet y adapta las salidas de tipo, color y estilo. Se puede detener la fase desde el monitor si la validación se deteriora; cada época y checkpoint quedan en una ejecución separada.

Continuar es un *warm start*, no una reanudación exacta: cada fase nueva usa optimizador, scheduler y contador de épocas nuevos porque los checkpoints actuales no guardan esos estados. La interfaz usa el mejor checkpoint de la ejecución seleccionada y solo lo acepta si coinciden arquitectura, catálogo de clases y resolución. Si cambia el catálogo, corrige/configura la compatibilidad antes de continuar; no fuerces el `state_dict`.

La pérdida de colores y estilos solo se calcula para prendas que tengan esas anotaciones; una etiqueta ausente en SQLite se trata como no anotada, no como negativa. Las métricas de tipo se calculan sobre imágenes de validación; precision/recall/F1 multi-etiqueta se calculan sobre los ejemplos con anotaciones correspondientes. Revisar especialmente el tamaño del dataset y las métricas antes de usar el checkpoint.

##### Predecir

El resultado combina las probabilidades de varias vistas de **la misma prenda**. No detecta ni separa múltiples prendas de una imagen.

```bash
docker compose run --rm train predict \
  --checkpoint /app/modelo-ia/runs/<ejecucion>/best.pt \
  /app/dataset/superior/camisas/CAMISA-1/frente.jpg \
  /app/dataset/superior/camisas/CAMISA-1/espalda.jpg
```

El umbral por defecto proviene del checkpoint; se puede ajustar con `--threshold 0.5`.

La metodología, comando de terminal, resultados actuales y limitaciones están en el [informe de evaluación](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md).

##### API de inferencia en una VM con CPU

`inference_api.py` es un servicio independiente del monitor y del curador. Sirve **solo inferencia** de un `best.pt` existente: obliga a usar CPU, carga un único checkpoint de solo lectura al iniciar y no monta `dataset/`, SQLite de entrenamiento ni cachés. No requiere GPU, NVIDIA Container Toolkit ni conexión a proveedores de anotación. El contenedor parte de la imagen PyTorch actual, que puede incluir bibliotecas CUDA, pero no reserva ni usa GPU.

###### Requisitos y selección del modelo

- VM Linux con Docker Engine y Docker Compose v2.
- El checkpoint compartido [`modelos-compartidos/mobilenetv3-small-best.pt`](utilidades-entrenamiento/modelos-compartidos/README.md), compatible con `MobileNetV3-Small` y con el catálogo de clases almacenado en el propio archivo.
- Memoria y CPU suficientes para mantener el proceso y ejecutar inferencias. En el host de desarrollo medimos 12 CPU lógicas y 15 GiB RAM; esto no es un mínimo universal ni mide tiempo de entrenamiento.

Desde la raíz del proyecto, selecciona un checkpoint que exista en esa VM y levanta la API con el Compose unificado (junto al panel de dataset):

```bash
export MODEL_CHECKPOINT="$PWD/utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt"
export API_CPU_THREADS=4
docker compose up -d --build
```

Para levantar solo esta API sin el panel de dataset:

```bash
docker compose up -d --build inference-api
```

`MODEL_CHECKPOINT` debe ser una ruta absoluta al archivo del host; si se omite se usa el checkpoint compartido `utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt`. Compose lo monta como `/models/best.pt` de solo lectura. La única carpeta de datos que recibe el contenedor es el checkpoint. `API_CPU_THREADS` limita los hilos de PyTorch (predeterminado: 4). Esta API ya no usa un Compose propio: forma parte del [Compose unificado](docker-compose.yaml) junto con el dashboard de curación.

Comprobación de salud:

```bash
curl http://127.0.0.1:8081/health
```

Respuesta esperada: `{"status":"ok","device":"cpu"}`. La especificación interactiva OpenAPI está en `http://127.0.0.1:8081/docs`.

###### Contrato de una imagen

`POST /v1/predict` recibe `multipart/form-data` con un único campo de archivo requerido: `garment_image`, la foto de la prenda. No requiere foto de persona.

Admite JPEG, PNG y WebP; máximo 10 MiB y 25 megapíxeles por imagen. Ejemplo:

```bash
curl --fail-with-body -X POST http://127.0.0.1:8081/v1/predict \
  -F 'garment_image=@/ruta/a/prenda.jpg'
```

Devuelve `descripcion_mas_probable`, `tipo_prenda`, `colores`, `estilos`, `umbral_multietiqueta`, `device` y `latencia_ms`. Tipo utiliza softmax; color y estilo utilizan sigmoid. Se devuelven los cinco candidatos principales por propiedad multietiqueta con su indicador `supera_umbral`. La descripción es una plantilla de etiquetas, sin generar material, talla ni atributos abiertos.

**Cambio de contrato (versión de aplicación 2.0.0):** se mantiene `/v1/predict`, pero se eliminan la segunda imagen y los campos de combinación. Los clientes deben enviar solo `garment_image` y leer las predicciones directamente en el objeto raíz. Reiniciar el proceso con el código actualizado para aplicar el cambio.

Para instalar el modelo y esta API directamente con Python, seguir la [guía nativa](docs/instalacion/INSTALACION-NATIVA.md) o el [manual Word en APA 7](docs/instalacion/Instalacion_nativa_API_prendas_APA7.docx). No se necesita dataset ni acceso a proveedores de anotación.

###### Red y seguridad

El servicio se publica solo en `127.0.0.1:8081` del host y no tiene autenticación. Para acceder desde una computadora remota, crea un túnel SSH:

```bash
ssh -L 8081:127.0.0.1:8081 usuario@servidor
```

Luego usa `http://127.0.0.1:8081` en esa computadora. No publiques el puerto directamente en Internet; para acceso compartido, colócalo detrás de un proxy con TLS, autenticación y límites de solicitudes.

Detener el servicio:

```bash
docker compose stop inference-api
```

(o `docker compose down` para detener también el panel de dataset).

Para cambiar checkpoint, detén el servicio, actualiza `MODEL_CHECKPOINT` y vuelve a levantarlo. La prueba CPU de entrenamiento no forma parte de esta API; inferencia rápida no demuestra que entrenar todo el dataset en CPU sea viable.

##### Layout

- [`docker-compose.yaml`](utilidades-entrenamiento/docker-compose.yaml): servicios CPU y GPU local.
- [`Dockerfile`](utilidades-entrenamiento/Dockerfile): imagen basada en PyTorch con runtime CUDA 12.4.
- [`entrypoint.sh`](utilidades-entrenamiento/entrypoint.sh): despacha `train`, `predict` y `status`.
- [`train.py`](utilidades-entrenamiento/train.py): lectura de SQLite, entrenamiento multisalida y métricas de validación.
- [`predict.py`](utilidades-entrenamiento/predict.py): predicción de una o varias vistas de una prenda.
- [`modelo-ia/`](utilidades-entrenamiento/modelo-ia): checkpoints y caché local, excluidos de Git.
- [`repositorios/`](utilidades-entrenamiento/repositorios): espacio para clones auxiliares, excluidos de Git.
- [`scraping-plugin-chrome/folder-destino/`](utilidades-entrenamiento/scraping-plugin-chrome/folder-destino/README.md): extensión Chrome para descargar manualmente imágenes de producto con un clic.
- [`modelo-general-destilacion/`](utilidades-entrenamiento/modelo-general-destilacion/README.md): pipeline separado para auditar/importar datasets públicos, guardar resultados de análisis para evitar llamadas repetidas y generar descripciones revisables; ver también el [`plan de pruebas`](utilidades-entrenamiento/modelo-general-destilacion/PLAN-PRUEBAS.md) y [`dudas.md`](utilidades-entrenamiento/modelo-general-destilacion/dudas.md).
- El panel local de seguimiento se levanta con `docker compose up -d --build dashboard` desde `modelo-general-destilacion`; monitorea conteos, actividad, prompt y opciones del proveedor en `http://127.0.0.1:8787`. También inicia/detiene lotes y muestra registros por proveedor; desde esos registros se pueden borrar líneas de error o congelar temporalmente la vista sin pausar el proceso.

##### Pipeline de curación y anotación

Este flujo es independiente del entrenamiento de MobileNetV3-Small. Su función es auditar fuentes, seleccionar imágenes mapeadas, detectar duplicados, solicitar anotaciones visuales opcionales y guardar sugerencias revisables en el dataset compartido. No aprueba etiquetas ni inicia entrenamiento automáticamente.

La guía completa, las rutas fuente, límites de envío, claves, política de fallback y ejemplos de uso están en [`modelo-general-destilacion/README.md`](utilidades-entrenamiento/modelo-general-destilacion/README.md). El pipeline unifica `camisa` y `camiseta` en la clase canónica `camisa`, manteniendo la etiqueta de origen en SQLite. En lotes remotos se pueden seleccionar hasta 5.000 imágenes nuevas por proveedor; se omiten hashes importados y análisis vigentes para el proveedor/modelo/configuración antes de aplicar el límite. La selección recomendada busca en todas las fuentes elegibles.

Si está habilitado en `.env`, un fallo de NVIDIA NIM activa el siguiente modelo de la cadena `NVIDIA_NIM_FALLBACK_MODELS`; un fallo de DeepSeek activa NVIDIA NIM como respaldo. Estos intentos pueden enviar la imagen a otro modelo/proveedor y aumentar uso o costo, por lo que el dashboard solicita consentimiento remoto. Las claves se guardan fuera del repositorio y no deben incluirse en argumentos, documentos públicos ni commits.

El dataset ya contiene imágenes importadas, pero falta revisar y aprobar suficientes muestras autorizadas para entrenamiento. En el snapshot documentado en la [guía de factibilidad](documentacion_dataset/README.md#factibilidad-y-alcance-del-mvp), ninguna prenda estaba aprobada y apta; en ese estado el entrenador termina con un mensaje explícito y no fabrica un modelo de éxito.

---


### Iniciar el entrenamiento

*Fuente: [`utilidades-entrenamiento/INICIO-RAPIDO.md`](utilidades-entrenamiento/INICIO-RAPIDO.md)*


[Índice documental](docs/INDICE.md) · [Panel del dataset](utilidades-entrenamiento/modelo-general-destilacion/README.md) · [Resumen del proyecto](<docs/resumen/RESUMEN-PROYECTO.md>).

Esta guía inicia entrenamiento por terminal. Para gestionarlo desde el panel, levanta el Compose unificado de la raíz (incluye `monitor`) y pulsa iniciar allí. El monitor solo puede detener los entrenamientos que él mismo lanza; evita iniciar otro por terminal al mismo tiempo.

Todo corre en contenedores; solo se necesita Docker (y driver NVIDIA + NVIDIA Container Toolkit para GPU).

```bash
cd utilidades-entrenamiento
newgrp docker                                   # si Docker da "permission denied"
docker compose build
docker compose --profile gpu run --rm train-gpu status   # debe mostrar la GPU
docker compose --profile gpu run --rm train-gpu          # entrena (usa configs/default.yaml)
```

Sin GPU: `docker compose run --rm train` (mucho más lento).

##### Ver el avance

En otra terminal, desde la raíz del proyecto:

```bash
docker compose up -d --build
```

Abrir http://127.0.0.1:8090 (progreso, pérdida por época, métricas e imágenes registradas).

Para continuar desde un checkpoint, selecciona la ejecución y estrategia en el panel. Se recomienda **Ajuste fino completo** desde el mejor checkpoint según validación; crea una fase nueva de hasta 10 épocas y reinicia optimizador/scheduler. Consulta la [estrategia y sus consideraciones](utilidades-entrenamiento/README.md#estrategia-recomendada-para-continuar).

##### Resultados

- Pesos: `modelo-ia/runs/<fecha-hora>/best.pt`; métricas en `metrics.json` y `test_metrics.json`.
- Registro de imágenes usadas por ejecución: `modelo-ia/registro_entrenamiento.sqlite`.
- Ajustes (épocas, batch, resolución): `configs/default.yaml`.

---


### Checkpoint compartido

*Fuente: [`utilidades-entrenamiento/modelos-compartidos/README.md`](utilidades-entrenamiento/modelos-compartidos/README.md)*


##### Modelo recomendado

- Archivo: `mobilenetv3-small-best.pt`
- Arquitectura: MobileNetV3-Small
- Ejecución fuente: `20261018-020637` (checkpoint idéntico al de `20261018-175546`)
- Mejor época: 15 de 20 épocas registradas
- Pérdida de validación: `0.5127596084`
- Entrada: 224 × 224 px
- SHA-256: `79407f5537418bc258857fa54723d8e39b152505ad3a6f6a6ea4f97e1dfcb35c`

Se seleccionó por la menor pérdida de validación entre las ejecuciones comparadas. La ejecución `20261018-192232` obtuvo `0.5353452153`, por lo que no reemplaza al checkpoint compartido. Esta comparación presupone que se mantuvieron el mismo split y dataset; el checkpoint es para inferencia, no una copia del estado del optimizador para reanudar entrenamiento.

El archivo contiene los pesos, las clases, la resolución y el umbral de inferencia. No incluye imágenes, base SQLite, caché de pesos preentrenados ni historial de entrenamiento. El `.gitignore` permite versionar únicamente este checkpoint recomendado; los demás `.pt` locales siguen excluidos.

Desde la raíz del repositorio, los compañeros pueden obtenerlo con `git pull`. Para usarlo en la API CPU, sigue la guía de [despliegue en VM](utilidades-entrenamiento/README.md#api-de-inferencia-en-una-vm-con-cpu).

---


### Curación y anotación de datasets de moda

*Fuente: [`utilidades-entrenamiento/modelo-general-destilacion/README.md`](utilidades-entrenamiento/modelo-general-destilacion/README.md)*


Este proyecto inspecciona fuentes locales, conserva su clase de origen, normaliza las categorías al dataset del proyecto y, opcionalmente, pide a uno o más proveedores visuales una descripción y sugerencias de color, estilo y temporada. Los colores están limitados al catálogo; los estilos y temporadas nuevos se incorporan automáticamente a SQLite cuando los responde una API. Es una etapa de preparación de datos; no es el entrenamiento de MobileNet ni, por sí sola, destilación de conocimiento.

[Índice documental](docs/INDICE.md) · [Estado verificado](docs/evaluacion/VALIDACION.md).

El máximo actual del panel es **15.000 imágenes nuevas por proveedor**; 5.000 es un objetivo de referencia, no el límite técnico.

##### Estado de los datos y fuentes

`datos-crudos/` contiene los repositorios `clothing-dataset-small-master/` y `clothing-dataset-master/`, además de AIG en `AIG-Dataset/`. AIG tiene 13 carpetas de clase, con 10.000 archivos `.jpg` en cada una. Se inspeccionaron los archivos y no se encontró README, LICENSE ni manifiesto adicional en esa carpeta. Fashion-MNIST no está presente. No se descargan repositorios ni datasets automáticamente.

El usuario confirma que las imágenes agregadas tienen permiso de uso comercial libre. Las páginas/README locales de ambos repositorios de clothing también indican uso libre/comercial y sus copias incluyen LICENSE CC0. La ingesta conserva fuente y etiqueta original por imagen para mantener trazabilidad.

Ejecuta la auditoría para comprobar el contenido actual (desde la raíz del proyecto):

```bash
docker compose build dashboard
docker compose --profile tools run --rm curator audit
```

| Fuente | Carpetas esperadas bajo `datos-crudos/` | Uso y mapeo inicial |
|---|---|---|
| [clothing-dataset-small](https://github.com/alexeygrigorev/clothing-dataset-small) | `clothing-dataset-small-master/{train,validation,test}/<clase>/` | Descargado/descomprimido: la última auditoría contó 3.781 archivos. Se mapean `dress`, `pants`, `shirt`, `shorts`, `skirt` y `t-shirt`; `hat`, `shoes`, `longsleeve` y `outwear` se omiten. Las cantidades pueden cambiar si se actualizan los archivos; `audit` es la referencia para el estado actual. |
| [clothing-dataset](https://github.com/alexeygrigorev/clothing-dataset) | `clothing-dataset-master/images.csv` y `images/<id>.jpg` | Descargado/descomprimido: CSV de 5.403 filas. Se mapean `Blouse`, `Blazer`, `Dress`, `Pants`, `Polo`, `Shirt`, `Shorts`, `Skirt`, `T-Shirt` y `Undershirt`. `Polo`/`Undershirt` se guardan como `camisa`; `Blazer` como `chaqueta`. El resto se omite. |
| [Apparel Images Gallery (Mendeley)](https://data.mendeley.com/datasets/pxkbgkydrp/1) | `AIG-Dataset/<clase>/*.jpg` | Descargado: 130.000 imágenes (13 carpetas de 10.000). Se aceptan las 12 carpetas que tienen correspondencia en la taxonomía y se omite `Hoodies` (10.000), que no es una clase canónica. Los archivos locales no incluyen README ni licencia; se usa la confirmación del usuario de que las imágenes tienen permiso comercial libre. |
| [Fashion-MNIST](https://github.com/zalandoresearch/fashion-mnist) | `fashion-mnist/` | No está presente. Cuando se añada, será benchmark independiente de 28×28 en escala de grises, no fotos a color para anotación. |

En la última auditoría local, el subset tenía 3.781 imágenes: 2.513 con clase mapeada; las otras 1.268 etiquetas se omiten. El dataset completo tenía 5.403 filas: 3.271 mapeadas y 2.132 omitidas. AIG contiene 120.000 imágenes en carpetas mapeadas y 10.000 en `Hoodies`, que se excluyen por no pertenecer al catálogo. Aunque los archivos terminan en `.jpg`, una inspección del contenido encontró 124.042 JPEG, 5.956 WebP y 2 PNG; el pipeline determina el MIME por el contenido real y conserva intactos los bytes. Ninguna de las 130.000 imágenes AIG supera 200.000 bytes (máximo observado: 92.069 bytes). Estos son conteos de inventario, no el número de imágenes que todavía necesitan análisis. Los totales se pueden volver a generar con `audit`.

La configuración/mapeos editables están en [`sources.json`](utilidades-entrenamiento/modelo-general-destilacion/sources.json). El pipeline solo procesa etiquetas incluidas explícitamente en el mapeo: carpetas o filas fuera de la taxonomía no se copian ni se envían a una API. Las imágenes de más de **200.000 bytes (0,2 MB decimal)** también se excluyen; no se reducen, convierten ni recomprimen antes del envío. Los ZIP originales locales se conservan y `datos-crudos/` está excluido de Git.

##### Arquitectura mínima

- [Compose unificado](docker-compose.yaml): servicios `dashboard` (panel) y `curator` (perfil `tools`); montan `datos-crudos/` en solo lectura y el dataset SQLite/carpeta del proyecto en escritura.
- [`Dockerfile`](utilidades-entrenamiento/modelo-general-destilacion/Dockerfile): Python 3.12 con Pillow y Requests.
- [`app.py`](utilidades-entrenamiento/modelo-general-destilacion/app.py): auditoría, mapeo de clases, importación, hash para evitar duplicados, cache por configuración y anotación visual opcional con fallback de proveedor/modelo.
- [`sources.json`](utilidades-entrenamiento/modelo-general-destilacion/sources.json): directorios, licencia declarada, clases que se admiten y mapeos al catálogo actual.
- [`.env.example`](utilidades-entrenamiento/modelo-general-destilacion/.env.example): plantilla de un único `.env` con las tres claves y configuraciones de proveedor; el `.env` real está excluido de Git.
- El esquema compartido contiene `descripcion_prenda` y `analisis_imagen`: anotaciones revisables y cache de decisiones por hash/clase/proveedor/modelo/versión de prompt.
- `prenda_imagen.etiqueta_fuente` conserva la etiqueta original (por ejemplo `Polo`) junto a la categoría canónica (por ejemplo `camisa`).
- Durante el procesamiento, las categorías `camisa` y `camiseta` se normalizan a la clase canónica `camisa`; la etiqueta original de la fuente se conserva para trazabilidad.
- [`dashboard.py`](utilidades-entrenamiento/modelo-general-destilacion/dashboard.py) y [`dashboard.html`](utilidades-entrenamiento/modelo-general-destilacion/dashboard.html): panel local para monitorear prendas por tipo y últimas importaciones, iniciar y detener lotes desde el navegador con estado y registro en vivo, y cambiar prompt, vocabularios y proveedor/claves.

Una imagen fuente produce inicialmente una carpeta/prenda en `dataset/`. Se conserva la partición si el path tiene `train`, `validation`/`val` o `test`; si no, se asigna determinísticamente por hash. El registro queda `pendiente` y `apta_para_entrenamiento=0`. Para llamadas remotas, la IA valida si la imagen corresponde a la clase fuente y puede descartarla antes de copiarla. Las imágenes aceptadas se importan con anotación pendiente; color/estilo sugeridos se guardan en `descripcion_prenda.atributos_sugeridos` y `valor_propiedad_prenda`, pero la prenda sigue pendiente y no es apta para entrenamiento. Una persona debe revisar y aprobarlas antes de entrenar.

Cada respuesta válida se guarda en `analisis_imagen`, tanto si acepta como si descarta la muestra. Al repetir la ejecución con la misma imagen, clase canónica, proveedor, modelo y versión del prompt, se reutiliza esa decisión y se evita otra llamada. Un análisis aceptado también queda protegido contra duplicación por SHA-256 en `prenda_imagen`. Si cambia proveedor/modelo o se incrementa la versión del prompt, la huella cambia intencionalmente.

##### Proveedores de visión y secretos

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

No pongas claves en el Compose, argumentos de shell, SQLite ni commits. No se envían etiquetas sin mapeo, imágenes >200.000 bytes ni formatos incompatibles. Antes de aplicar `--limit`, la ingesta quita hashes que ya están en el dataset y repeticiones dentro del plan; por eso las siguientes ejecuciones avanzan a imágenes nuevas en vez de volver a seleccionar las primeras ya importadas. El registro informa cuántas duplicadas se omitieron antes de la IA. Para usar APIs remotas se requieren explícitamente `--allow-remote`, `--limit` y `--execute`. Los errores HTTP/red del proveedor detienen el lote; respuestas de IA con estructura inválida se omiten y el lote continúa.

##### Uso seguro y reproducible

La suite automatizada local y las etapas de validación están descritas en [`PLAN-PRUEBAS.md`](utilidades-entrenamiento/modelo-general-destilacion/PLAN-PRUEBAS.md). Ejecuta primero sus pruebas sin red ni credenciales.

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
   docker compose --profile tools run --rm curator audit
   ```

3. Ensaya el mapeo de una fuente:

   ```bash
   docker compose --profile tools run --rm curator ingest \
     --source clothing-small --provider none
   ```

4. Importa sin enviar imágenes a terceros:

   ```bash
   docker compose --profile tools run --rm curator ingest \
     --source clothing-small --provider none --execute
   ```

5. Solo para una muestra pequeña que hayas autorizado, configura `.env` y limita explícitamente una prueba remota:

   ```bash
   docker compose --profile tools run --rm curator ingest \
     --source mendeley-aig --provider nim --allow-remote --limit 10 --execute
   ```

NIM se usará en nube sujeto a la cuota gratuita disponible; DeepSeek es de pago. Cada llamada remota puede consumir cuota o generar costo. `--allow-remote`, `--limit` y `--execute` son requisitos explícitos tanto en CLI como al iniciar un lote desde el dashboard. Las rutas fuente se montan read-only. Los archivos importados se guardan en la estructura canónica; los originales no se modifican. Ejecuta `audit` después de importar para verificar conteos.

Si una solicitud remota expira, puede haberse realizado una llamada facturable aunque no llegue respuesta. Para cada modelo NIM el curador espera aleatoriamente 5–15 segundos y reintenta una vez la misma imagen; si se agotan los modelos, omite esa imagen y continúa. Ante el fallo de DeepSeek puede probarse NIM y su cadena configurada; ante el fallo de un modelo NIM se prueban los siguientes modelos configurados. Estos mecanismos pueden volver a enviar la misma imagen y generar consumo adicional. **Detener envío** no interrumpe una petición que el proveedor ya esté procesando; el proceso espera a que concluya y luego cancela. Revisa el uso en el proveedor antes de volver a ejecutar un lote.

##### ¿Es destilación?

En sentido estricto, **todavía no**. Este flujo importa datos con etiquetas originales y genera *pseudo-etiquetas* y descripciones textuales con un modelo maestro (VLM). Esto se suele llamar curación/anotación asistida por IA o pseudo-labeling. La destilación clásica requiere después entrenar un modelo estudiante con objetivos producidos por el maestro —idealmente distribuciones/logits o supervisión docente definida— y evaluar su transferencia. `descripcion_prenda` guarda texto y sugerencias, no logits; por eso no los presentamos como conocimiento destilado ni los aprobamos automáticamente.

##### Decisiones pendientes

Las preguntas restantes se mantienen en [`dudas.md`](utilidades-entrenamiento/modelo-general-destilacion/dudas.md): confirmar el tope de gasto de DeepSeek y los criterios de aprobación humana. AIG ya fue localizado, su estructura fue inspeccionada y se habilitó con las clases canónicas compatibles; `Hoodies` se excluye.

##### Reparto del lote entre categorías

Al aplicar el límite de imágenes nuevas, el curador no sigue el orden alfabético de las carpetas: prioriza las categorías con menos análisis aceptados hasta igualarlas (por ejemplo suéter, falda, short y pantalón antes que blusa o vestido). Así un lote de 5.000 no se consume solo con las primeras carpetas de AIG.

##### Propiedades guardadas en SQLite

Al importar una imagen, los colores, estilos y temporadas propuestos por la IA se guardan en `valor_propiedad_prenda` (sin `unknown`; `summer` y `spring` se normalizan a `verano` y `primavera`), además del JSON de `descripcion_prenda.atributos_sugeridos`. La prenda sigue `pendiente` y sin `apta_para_entrenamiento`, así que `train.py` no la usa hasta que se apruebe. Para rellenar prendas importadas antes de este cambio, o tras un lote que corrió con código viejo:

```bash
docker compose --profile tools run --rm --no-deps --entrypoint python curator /app/app.py sync-properties
```

##### Galería de prendas

`http://127.0.0.1:8787/galeria` (enlace "Galería de prendas" en el monitor) es una vista aparte que muestra
cada imagen con sus propiedades generadas (color, estilo, temporada), descripción, proveedor/modelo, split y estado.
Se navega de 15 en 15 (primera/anterior/números/siguiente/última, ir a página y flechas del teclado) y se puede
filtrar por categoría y proveedor. Los datos salen de `valor_propiedad_prenda` y, como respaldo, de
`descripcion_prenda.atributos_sugeridos`. API: `/api/gallery?page=&category=&provider=`.

##### Filtro antes del envío a la IA: últimas diez prendas

Antes de un análisis remoto nuevo, se compara la candidata con las **últimas 10 prendas reservadas para envío inicial por el proveedor del lote**. Si presenta alta similitud, se omite sin consultar la IA y se continúa buscando otra candidata. Las omitidas no consumen el límite de envíos; el lote puede revisar más candidatas para completar el máximo solicitado.

El filtro combina dHash de 64 bits (distancia máxima 2), proporción de imagen (diferencia máxima del 3 %) y una miniatura RGB de 32 × 32. Para omitir exige diferencia media máxima de 8 por canal y diferencia máxima local de 32 en escala 0–255. Es un criterio conservador para copias, recompresiones y variaciones pequeñas; no es una evaluación semántica ni garantiza detectar todos los recortes o cambios de fondo. El color evita depender únicamente de la silueta en escala de grises.

El historial se guarda en `pipeline_config` bajo `recent_sent_images_v1:<proveedor>` y conserva solo diez miniaturas/huellas por proveedor entre lotes y reinicios. Se reserva inmediatamente antes de invocar la anotación, incluso si ese intento termina en descarte, timeout o respuesta inválida. Las etapas, reintentos y fallbacks de esa prenda no añaden entradas. La reserva es atómica y libera SQLite antes de esperar al proveedor. NIM y DeepSeek mantienen historiales separados para conservar la posibilidad de evaluación cruzada. El historial empieza al utilizar esta versión; no reconstruye envíos antiguos.

La comparación se aplica a nuevas solicitudes remotas, no a `--provider none` ni a resultados ya cacheados. No borra archivos, no cambia aprobaciones y no guarda las omitidas como descartes de IA. Una candidata omitida puede volver a evaluarse cuando la referencia deje de estar entre las diez últimas; no es una lista permanente de exclusión.

En el registro del dashboard aparece `Omitida por alta similitud...` con su referencia; al terminar se informa `similares omitidas antes de IA` y `envíos iniciales`. El cambio requiere recrear el dashboard con la imagen actualizada; un lote ya en curso conserva el código con el que arrancó.

##### Limpieza de imágenes duplicadas

El dataset de origen (sobre todo `mendeley-aig`) trae la misma foto repetida con pequeñas variaciones, por lo que el
SHA-256 no las detecta. Flujo:

1. `docker compose --profile tools run --rm --no-deps --entrypoint python curator /app/app.py find-duplicates [--threshold 2]`
   calcula un dHash de 64 bits por imagen (tabla `imagen_huella`) y agrupa las que están a distancia de Hamming
   <= umbral (tablas `grupo_duplicado` y `grupo_duplicado_miembro`). Es repetible; solo recalcula los grupos pendientes.
   Con umbral 6 el encadenamiento fusiona miles de imágenes distintas, por eso el valor por defecto es 2.
2. `http://127.0.0.1:8787/duplicados` (botón "Duplicados" del monitor) muestra cada grupo. La imagen de mayor resolución
   viene marcada para conservarse; haz clic en otra para cambiarla. "Dejar solo la verde y eliminar el resto" marca las demás
   como `rechazado` con `apta_para_entrenamiento=0` (no borra archivos), "No son duplicadas" descarta el grupo y
   "Deshacer" lo revierte. "Resolver toda la página" aplica la recomendada a los 10 grupos visibles.
3. La galería oculta las prendas rechazadas y `train.py` solo usa aprobadas, así que el grupo deja una sola imagen.

Respaldo previo a la limpieza: `respaldos/dataset-*/` (ignorado por git).

###### Borrado masivo de grupos grandes

`app.py purge-duplicates --min-size 4` resuelve los grupos pendientes con al menos 4 imágenes: conserva la de mayor
resolución, rechaza el resto y **borra sus archivos**. Las filas de `prenda_imagen` se conservan (prendas `rechazado`) para que
su SHA-256 siga bloqueando futuras importaciones y análisis, de modo que no se vuelven a revisar. Estos grupos no se pueden
deshacer desde la interfaz; restaura desde `respaldos/`. Los originales de `datos-crudos/` no se modifican.

##### Aprobación de lo generado

`app.py approve-generated` pasa a `aprobado` con `apta_para_entrenamiento=1` toda prenda `pendiente` que ya tenga descripción
generada (y aprueba esas descripciones). No toca las `rechazado`. Es repetible: ejecútalo de nuevo cuando terminen los lotes.
Úsalo tras revisar una muestra manual de las descripciones.

---


### Plan de pruebas del pipeline de curación

*Fuente: [`utilidades-entrenamiento/modelo-general-destilacion/PLAN-PRUEBAS.md`](utilidades-entrenamiento/modelo-general-destilacion/PLAN-PRUEBAS.md)*


El objetivo es verificar desde la inspección de fuentes hasta la importación, el cache de análisis, la revisión pendiente y el comportamiento de las APIs. Las pruebas automatizadas no hacen llamadas externas ni utilizan el dataset productivo.

##### 1. Pruebas automáticas locales

Construir la imagen y ejecutar la suite dentro del contenedor:

```bash
docker compose build curator
docker compose run --rm --no-deps --entrypoint python curator -m unittest discover -s tests -v
```

Cobertura:

- La huella del análisis es determinista y separa proveedor, modelo, clase e imagen.
- `camisa` y `camiseta` se normalizan al mismo tipo canónico `camisa` durante el escaneo/importación.
- Si un modelo NVIDIA NIM falla, se prueba automáticamente el siguiente modelo de `NVIDIA_NIM_FALLBACK_MODELS`; los siguientes elementos del lote continúan con el modelo que funcionó.
- Si DeepSeek falla por HTTP/red, timeout o respuesta inválida, se intenta el análisis con NVIDIA NIM y el resultado queda atribuido al proveedor/modelo que respondió.
- Un análisis aceptado guardado se reutiliza; no se vuelve a invocar al modelo.
- Un descarte guardado también se reutiliza; no se vuelve a enviar ni importar.
- Una anotación nueva queda registrada y la siguiente ejecución omite la imagen ya importada.
- Carpetas sin clase canónica y archivos por encima de 200.000 bytes no entran en el plan.
- La imagen se envía sin modificar sus bytes y el MIME coincide con su formato real.
- El prompt guardado y los vocabularios de propiedad quedan disponibles para el siguiente proceso de curación.
- Ambos proveedores pueden proponer estilos y temporadas nuevos; los valores se fusionan sin duplicados en el catálogo incluso si la imagen se descarta. Los colores no admiten valores fuera de su catálogo.
- El dashboard agrupa por proveedor/modelo las respuestas válidas guardadas, con conteos apta/descartada y fecha más reciente. Los resultados inválidos se mantienen visibles en el registro del lote, pero no se cuentan como respuestas válidas.

Resultado esperado: todos los tests pasan; ningún test conoce ni carga API keys.

###### Filtro de similitud previo a la IA

La suite `tests/test_recent_similarity.py` verifica que una copia recompresa/redimensionada se omite antes de llamar al proveedor; que una candidata distinta posterior completa el límite; que se conservan diferencias de color, forma y proporción; y que solo las últimas diez reservas permanecen en la ventana. Comprueba además persistencia entre lotes, separación por proveedor, reserva concurrente atómica, recuperación de caché sin un envío nuevo, continuidad ante imágenes ilegibles y ausencia de cambios en la importación sin IA. Las pruebas usan imágenes y SQLite temporales, con proveedores simulados. La suite completa actualizada pasó **72 pruebas** el 23-10-2026 dentro de la imagen Docker construida, con `--network none`, sin credenciales ni montaje del dataset real.

##### 2. Auditoría de fuentes (solo lectura)

```bash
docker compose run --rm curator audit
```

Comprobar en AIG: 130.000 archivos, 120.000 mapeados, 10.000 omitidos en `Hoodies` y cero archivos mayores de 200 KB. Las demás fuentes deben mostrar sus conteos actuales. Esta fase no crea filas ni hace peticiones remotas.

##### 3. Ensayo de selección (dry-run)

```bash
docker compose run --rm curator ingest --source mendeley-aig --provider none --limit 5
docker compose run --rm curator ingest --source clothing-full --provider none --limit 5
```

El comando informa cuántas imágenes están en el plan y termina en “Ensayo solamente”. No copia imágenes, no escribe SQLite y no contacta servicios.

##### 4. Importación local acotada, sin API

Probar primero en una copia temporal del dataset/SQLite, no en la carpeta productiva. Importar una imagen con `--provider none --execute --limit 1`; verificar `prenda`, `prenda_imagen`, `etiqueta_fuente`, `valor_propiedad_prenda`, hash SHA-256, ruta y split. Debe quedar `pendiente` y `apta_para_entrenamiento=0`. Repetir el mismo comando: el hash debe evitar duplicar la muestra.

##### 5. Prueba remota manual, opcional y con costo/cuota

Solo ejecutar tras confirmar endpoint y disponibilidad de un modelo visual en la cuenta. NIM y DeepSeek se prueban por separado, una imagen cada vez, con una fuente/montaje de prueba aislado:

```bash
docker compose run --rm curator ingest \
  --source mendeley-aig --provider nim --allow-remote --limit 1 --execute
```

Antes de ejecutar, verificar que el `.env` local contiene la clave del proveedor seleccionado. No imprimirla, ponerla en la línea de comandos ni guardarla en SQLite. Después verificar que `analisis_imagen` contiene una fila con SHA-256, clase, proveedor/modelo, versión del prompt y decisión; una aceptación debe además crear prenda e imagen pendientes, y un rechazo solo el registro de análisis.

Repetir exactamente el comando. El resultado esperado es “análisis reutilizados: 1” (si fue descartado) o “duplicadas omitidas: 1” (si fue aceptado); en ninguno de los casos debe emitirse una segunda llamada al proveedor. Para comprobarlo, contrastar los contadores de uso del proveedor, no registrar ni exponer la clave.

El curador aplica una separación mínima de 3 segundos entre inicios de peticiones NVIDIA NIM. La [documentación oficial](https://docs.api.nvidia.com/nim/reference/llm-apis) confirma el endpoint de chat, pero no publica un RPS universal aplicable a todas las cuentas; un timeout de lectura no prueba por sí solo una respuesta 429 ni un límite de tasa.

##### 6. Fallos y recuperación

- Con key/endpoint inválidos, la ejecución debe exponer el error; no marcar una respuesta fallida como procesada.
- Si la llamada API funciona pero falla la escritura de una imagen aceptada, el resultado del análisis permanece cacheado para reintentar la importación sin volver a pagar la inferencia.
- Simular HTTP 500 o respuesta inválida en el modelo NIM principal; verificar el intento del modelo siguiente y que se registra el proveedor/modelo de respaldo.
- Simular fallo DeepSeek con clave NIM configurada; verificar el fallback a NIM y que la fila de análisis y la descripción atribuyen el resultado a NIM.
- Una respuesta inválida no genera análisis cacheado; la imagen se omite y el proceso prueba las siguientes del lote.
- DeepSeek solicita `response_format=json_object`, 1.024 tokens iniciales y un reintento con 2.048 cuando el contenido está vacío o truncado; además envía `thinking: {type: disabled}` y el prompt incluye JSON y un ejemplo.
- NIM envía cuatro solicitudes por imagen, en orden: colores, estilos, temporadas y validación/descripción. Cada etapa solicita JSON de hasta 256 tokens y reintenta una vez con 512 ante JSON inválido; comprobar que se combinan las cuatro respuestas, los inicios se separan al menos 3 segundos y una detención impide enviar las etapas siguientes.
- El modelo NIM recomendado `nvidia/nemotron-3.5-super-vl-120b-a12b` envía `reasoning_effort=none`; verificar que no se agrega este parámetro a otros modelos. Antes de usarlo en un lote grande, probar una muestra pequeña y comprobar que está habilitado para la API key.
- La salida NIM distingue JSON malformado de JSON sintácticamente válido con una estructura incorrecta, e incluye etapa, `finish_reason` y longitud en el log sin imprimir todo el contenido de la respuesta.
- Con DeepSeek configurado, un descarte NIM debe iniciar una evaluación DeepSeek usando su propio fingerprint/cache. Si DeepSeek acepta, importar con proveedor/modelo DeepSeek; si también descarta, conservar ambos análisis y no importar. Sin clave DeepSeek, mantener el descarte NIM y mostrarlo explícitamente. Si ambos proveedores se seleccionan en paralelo, comprobar que no se dispara una llamada fallback redundante desde el proceso NIM.
- NIM debe realizar cuatro etapas: colores, estilos, temporadas y validación/descripción. Debe pedir un máximo de 8 palabras en descripción y motivo de descarte, y máximo 2 valores por propiedad. Verificar que colores fuera del catálogo se ignoran, estilos/temporadas nuevos se conservan, y el resultado combinado respeta esos límites. DeepSeek debe conservar estilos/temporadas nuevos, restringir colores al catálogo y mantener descripción de hasta 12 palabras y hasta 3 valores por lista.
- Tras responder una anotación, comprobar que estilo/temporada nuevos se guardan en `catalogo_propiedad`; en imágenes incorporadas, las sugerencias quedan también en `atributos_sugeridos`. El catálogo de color no cambia. El siguiente análisis debe recibir el catálogo actualizado en su prompt.
- Mocks de ambos proveedores: una primera respuesta vacía/truncada seguida de JSON válido debe devolver anotación válida y demostrar el aumento de tokens; dos respuestas incompletas deben omitir la imagen sin guardarla y continuar el lote.
- Dos inicios consecutivos de solicitudes NIM se separan como mínimo 3 segundos. Ante timeout, el proceso espera un intervalo aleatorio entre 5 y 15 segundos y reintenta la misma imagen exactamente una vez; si el segundo intento también expira, la omite y pasa a la siguiente muestra. Verificar orden de imágenes, espera y que solo se persista una decisión válida.
- Con hashes ya importados al inicio del inventario, un límite de lote pequeño debe saltarlos antes de contar candidatos; el mismo tamaño de lote debe avanzar hasta llenar el cupo con imágenes nuevas. El resumen debe reportar las duplicadas omitidas antes de IA.
- `motivo_descarte: null` se normaliza a cadena vacía solo para imágenes aceptadas; otros tipos inválidos se omiten sin frenar el lote.
- La prueba de rollback/importación se hace solo en dataset temporal; nunca simular fallos destructivos contra `dataset/metadata.sqlite`.

##### 7. Panel de monitoreo

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
- La tarjeta **Procesar imágenes ahora** ofrece solo fuentes importables, inicia hasta dos lotes en paralelo (uno por proveedor remoto), cada uno con límite de 1–15.000 imágenes, y presenta estado/salida por separado.
- Con NIM y DeepSeek seleccionados, validar que se crean dos procesos independientes con el mismo límite y que cada uno llama solo a su proveedor.
- Enviar ambos proveedores sobre imágenes comunes y verificar que una imagen se incorpora una sola vez aunque los dos procesos terminen su análisis; la escritura SQLite debe serializarse y el segundo importador debe registrar el duplicado.
- **Detener envío** solicita la cancelación solo al proceso proveedor elegido; el estado pasa a “detención solicitada” y luego “detenido”. Una solicitud ya activa puede finalizar/importarse, pero no se inicia otra. Si se detiene durante el backoff de timeout, no se reintenta ni se avanza a otra imagen. La otra ejecución en paralelo debe continuar.
- Sin IA exige confirmación de escritura; NIM/DeepSeek además requieren clave configurada y autorización explícita de envío remoto. OpenAI permanece fuera de la selección hasta habilitarlo por separado.
- Un segundo lote del mismo proveedor se rechaza mientras ese proveedor siga activo; se permite lanzar el otro proveedor en paralelo. Errores y claves deben estar ausentes de cualquier registro mostrado.

##### Criterios de aceptación

1. La suite automatizada pasa sin red y sin credenciales.
2. Dry-run y auditoría no alteran el dataset ni SQLite.
3. La importación repetida no duplica la imagen.
4. Una decisión de IA válida no se vuelve a consultar para la misma huella de imagen/clase/proveedor/modelo/versión de prompt.
5. No se importan imágenes de clases fuera del mapeo ni mayores de 200.000 bytes.
6. Las muestras aprobadas por la IA continúan pendientes de revisión humana y no habilitadas para entrenamiento.
7. El dashboard solo responde en localhost, las claves se ocultan y los cambios de prompt/vocabulario afectan los procesos futuros.
8. Cada proveedor acepta un límite de hasta 15.000 prendas; al seleccionar NIM y DeepSeek se inician trabajos paralelos independientes.
9. La importación concurrente de un mismo hash crea una sola prenda y una sola imagen registrada en SQLite.

---


### Dudas y decisiones antes de procesar datos

*Fuente: [`utilidades-entrenamiento/modelo-general-destilacion/dudas.md`](utilidades-entrenamiento/modelo-general-destilacion/dudas.md)*


Las decisiones ya confirmadas por el usuario se aplican en `sources.json` y en el pipeline. Estas preguntas restantes no bloquean la auditoría local; sí deben resolverse antes de importar lotes amplios o usar proveedores.

##### Datos y taxonomía

1. **Licencia de AIG:** no se encontró README, LICENSE ni manifiesto dentro de `AIG-Dataset/`. Se habilitó con base en tu confirmación de uso comercial libre. La procedencia y etiqueta original se conservan en SQLite.
2. **Hoodies:** AIG contiene 10.000 imágenes en `Hoodies`; se excluyen conforme a la regla de omitir clases que no existen en el catálogo actual.
3. **Fashion-MNIST:** no está en los directorios inspeccionados y seguirá fuera del dataset fotográfico de prendas; su baja resolución y escala de grises no sirve para sugerir atributos visuales de estas fotografías. ¿Se conserva únicamente como benchmark independiente?

##### Proveedores, privacidad y límites

1. **NVIDIA NIM en nube:** queda seleccionado como opción sin costo según la disponibilidad/créditos de la cuenta. El modelo VLM alojado y sus límites pueden cambiar; confirma que el modelo elegido en `.env` aparece habilitado para visión en tu cuenta NIM.
2. **DeepSeek:** es de pago y se configura su clave en el mismo `.env`. ¿Cuál es el presupuesto o límite de gasto por lote que debemos usar? El CLI ya requiere un `--limit` explícito, pero no conoce el saldo de la cuenta.
3. **TOON:** se manda el contexto estructurado de la tarea en TOON dentro del texto del mensaje. Los proveedores compatibles exigen que el sobre HTTP/chat y la respuesta parseable sigan siendo JSON; no hay transporte TOON nativo configurado.
4. **Revisión humana:** todas las imágenes aceptadas por una IA se importan como `pendiente` y no son elegibles para entrenar hasta la aprobación humana. ¿Qué criterios usarás para aprobar o rechazar descripciones, colores y estilos? La IA puede descartar una imagen, pero no sustituye esta revisión.
5. **Tamaño y formatos:** se omiten archivos mayores de 200.000 bytes antes de calcular hash o llamar al proveedor; no se redimensionan ni recomprimen. En llamadas remotas solo se admiten JPEG, PNG, GIF y WebP. ¿Quieres ajustar el umbral o admitir otro formato?

##### Categorías físicas

La carpeta y guía `dataset/superior/abrigos/` ya existen, están incluidas por `crear_estructura.sh` y el pipeline la crea al importar la categoría `abrigo`. No se agregó una clase nueva para abrigos. `Outwear` se mantiene excluida porque puede corresponder a abrigo o chaqueta y requiere una equivalencia explícita; se distingue de `sueter`, que tiene su carpeta y guía propias.

---


### Extensión Chrome: descargar imagen de producto

*Fuente: [`utilidades-entrenamiento/scraping-plugin-chrome/folder-destino/README.md`](utilidades-entrenamiento/scraping-plugin-chrome/folder-destino/README.md)*


Extensión Manifest V3 que descarga una imagen con un clic en el icono de Chrome. Busca imágenes de la pestaña activa, prioriza imágenes grandes y señales de producto/galería, y usa Open Graph como alternativa. El nombre de archivo se basa en el título de la página.

##### Instalar en Chrome

1. Abre `chrome://extensions`.
2. Activa **Modo de desarrollador**.
3. Selecciona **Cargar extensión sin empaquetar**.
4. Elige esta carpeta `folder-destino/`.
5. Abre una ficha de producto y pulsa el icono de la extensión. El indicador del icono muestra `OK` si inició la descarga o `ERR` si no encontró una imagen.

##### Carpeta de descarga

Chrome no permite a una extensión escribir directamente en una ruta absoluta del proyecto. Por defecto solicita una ruta relativa:

```text
folder-destino/
```

Normalmente los archivos quedan en `~/Downloads/folder-destino/`. Para guardarlos en esta carpeta del proyecto, cambia una sola vez la ubicación base de descargas de Chrome a:

```text
/home/uceda/Documents/consolidacion del proyecto/modelo-reconocimiento-prendas/utilidades-entrenamiento/scraping-plugin-chrome
```

Con esa ubicación, Chrome guarda las imágenes en `scraping-plugin-chrome/folder-destino/`, junto a la extensión. Los archivos de imagen descargados están excluidos de Git por el `.gitignore` de esta carpeta. La ubicación base es global para las descargas normales de Chrome; si no deseas cambiarla, conserva la predeterminada y usa `~/Downloads/folder-destino/`. La ubicación base se configura en `chrome://settings/downloads`.

##### Alcance y permisos

- No descarga la página completa ni todas las imágenes: selecciona una candidata al hacer clic.
- La heurística puede escoger una imagen incorrecta en tiendas con galerías complejas, anuncios o fichas sin metadatos; revisa la imagen resultante.
- No intenta saltar inicios de sesión, muros de pago, controles anti-bot ni restricciones de acceso. Solo descarga una imagen accesible desde la pestaña abierta.
- Usa `activeTab` y `scripting` para leer las imágenes al pulsar el icono, y `downloads` para guardar el archivo. No solicita acceso permanente a todos los sitios.

---


## 7. Evaluación y evidencias


### Evaluación del clasificador (MobileNetV3-Small)

*Fuente: [`docs/evaluacion/EVALUACION-ENTRENAMIENTO.md`](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md)*


La revisión del 23-10-2026 contrastó estas cifras con los JSON locales existentes y el hash del checkpoint; no ejecutó una nueva evaluación completa. Véase [validación](docs/evaluacion/VALIDACION.md). La columna de entrenamiento del 22 de octubre es una comparación fechada, no necesariamente la última ejecución disponible.

##### Diseño de la prueba

- **Objetivo:** medir qué porcentaje de las propiedades de una prenda (tipo, color y estilo) reconoce el modelo en fotografías que no usó para entrenar.
- **Muestra:** el conjunto de prueba completo, 1.424 imágenes (una por prenda); 1.418 tienen color y estilo anotados. La partición es fija (carpeta de origen o hash SHA-256) y el test no se usó para elegir checkpoint ni umbral (0,5 fijo). Dataset vigente (22-10-2026): 14.456 imágenes aprobadas, 11.616 train, 1.416 val y 1.424 test.
- **Instrumento:** `utilidades-entrenamiento/evaluate_properties.py`. Solo inferencia en CPU; no entrena ni modifica pesos. Guarda un JSON con el SHA-256 de la base de datos.
- **Predicción:** tipo = clase de mayor probabilidad; color y estilo = etiquetas con probabilidad ≥ 0,5.

##### Cálculos

Con $T$ imágenes, $P_i$ el conjunto predicho y $R_i$ el real:

- **Tipo:** exactitud $=$ tipos correctos $/\,T$.
- **Color/estilo, exacta:** $\#\{i: P_i=R_i\}\,/\,T$.
- **Color/estilo, parcial (Jaccard):** $\frac{1}{T}\sum_i \frac{|P_i\cap R_i|}{|P_i\cup R_i|}$ (1 si ambos vacíos). Ejemplo: real {azul}, predicho {azul, blanco} da 0,5.
- **Promedio macro:** media simple de tipo, Jaccard de color y Jaccard de estilo (cada una pesa un tercio).
- **Criterio de aceptación (R11):** macro $\ge 70\,\%$.

##### Reproducir

Desde `utilidades-entrenamiento/`:

```bash
docker compose run --rm --no-deps --entrypoint python train \
  /app/evaluate_properties.py \
  --checkpoint /app/modelos-compartidos/mobilenetv3-small-best.pt \
  --split test --device cpu \
  --output /app/modelo-ia/evaluaciones/evaluacion_propiedades_test.json
```

##### Resultados (test, 1.424 imágenes, CPU, 22-10-2026)

| Propiedad | Checkpoint compartido (época 15) | Último entrenamiento `20261022-015119` (época 21) |
|---|---:|---:|
| Tipo, exactitud | 1.352 / 1.424 = **94,94 %** | 1.340 / 1.424 = **94,10 %** |
| Color, exacta | 764 / 1.418 = 53,88 % | 774 / 1.418 = 54,58 % |
| Color, Jaccard | **68,42 %** | **69,34 %** |
| Estilo, exacta | 674 / 1.418 = 47,53 % | 676 / 1.418 = 47,67 % |
| Estilo, Jaccard | **69,21 %** | **69,48 %** |
| **Promedio macro** | **77,52 %** | **77,64 %** |

El modelo reportado en el informe es el checkpoint compartido; la diferencia con ese entrenamiento es de 0,12 puntos porcentuales; no se ha realizado una prueba estadística para establecer su significancia. Clases más débiles (checkpoint compartido): suéter (recall 66,7 %), color naranja (18,9 %) y estilo entretiempo (15,0 %). Detalle por clase en `utilidades-entrenamiento/modelo-ia/evaluaciones/`.

##### Limitaciones críticas

1. **Etiquetas no independientes:** color y estilo los generaron NVIDIA NIM (6,6 %) y DeepSeek (93,4 %); la prueba mide concordancia con anotaciones de IA, no con una referencia humana. El tipo viene de la clase de la fuente pública.
2. **Desbalance:** blusa 43,8 % y falda 2,4 %; falda (28) y suéter (42) tienen pocos ejemplos de prueba.
3. **Casi duplicados:** 77 imágenes de test (5,4 %) tienen una casi idéntica en train; al excluirlas el macro baja a 76,96 %.
4. **Exacta frente a parcial:** con coincidencia exacta, color y estilo quedan por debajo de 70 %; solo el macro con Jaccard supera el criterio.
5. **Dominio:** fotos de catálogos públicos, no de una persona vistiendo la prenda; esa condición no se midió.

Análisis ampliado y correcciones al informe: [CORRECCIONES-INFORME.md](docs/antecedentes/CORRECCIONES-INFORME.md).

---


### Validación de documentación e implementación

*Fuente: [`docs/evaluacion/VALIDACION.md`](docs/evaluacion/VALIDACION.md)*


**Fecha: 23 de octubre de 2026 (UTC).** [Índice](docs/INDICE.md) · [Resumen](<docs/resumen/RESUMEN-PROYECTO.md>)

##### Alcance y criterio

Se revisaron los archivos versionados de documentación, Compose/Dockerfiles, configuración, scripts de entrenamiento, evaluación, predicción, API y curación, handlers HTTP y pruebas existentes. Se contrastaron las guías con el código, el dataset local y artefactos de evaluación. Esta revisión no certifica calidad visual de todas las imágenes, licencias, disponibilidad de proveedores remotos ni rendimiento en producción.

No se modificaron SQLite, imágenes, pesos ni servicios. No se iniciaron entrenamientos, importaciones, llamadas de anotación remota ni purgas. Las suites usan fixtures y directorios temporales. Las primeras pruebas locales de curación fallaron por rutas de importación y por falta de `/app/schema.sql`; la ejecución final se hizo en el contenedor previsto y pasó.

##### Actualización: API de una imagen e instalación nativa

Después de la revisión general se actualizó `inference_api.py` a la aplicación 2.0.0: `/v1/predict` recibe únicamente `garment_image` y devuelve descripción y propiedades en el objeto raíz. Se retiraron los campos de combinación de imágenes. La ruta predeterminada al checkpoint se resuelve junto al módulo, lo que permite instalar la estructura mínima sin variables de contenedor.

La instalación directa se verificó en un entorno virtual temporal de Python 3.12 con PyTorch 2.5.1+cpu, torchvision 0.20.1+cpu y las dependencias fijadas del proyecto. `pip check` no encontró incompatibilidades. Las **19 pruebas actuales de entrenamiento/inferencia pasaron**, incluidas cinco pruebas HTTP con un servidor temporal. Una prueba adicional cargó el checkpoint compartido real desde una copia mínima, sin dataset en la carpeta del servicio: `/health` respondió correctamente, OpenAPI exigió solo `garment_image` y el envío de una fotografía real produjo HTTP 200 con descripción y propiedades. Los procesos temporales se detuvieron al terminar.

El [manual DOCX APA 7](docs/instalacion/Instalacion_nativa_API_prendas_APA7.docx) y su [fuente de instalación](docs/instalacion/INSTALACION-NATIVA.md) describen el procedimiento. Se comprobó el formato del Word mediante renderizado a PDF. No se sustituyeron servicios existentes: requieren reiniciarse con código actualizado. La evidencia de Docker que sigue corresponde a la revisión anterior al cambio de contrato.

##### Evidencia comprobada

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

##### Estado del dataset consultado

| Estado | train | val | test | Total |
|---|---:|---:|---:|---:|
| Aprobado y apto | 11.616 | 1.416 | 1.424 | 14.456 |
| Pendiente y no apto | 9.718 | 1.221 | 1.191 | 12.134 |
| Rechazado y no apto | 13.609 | 1.682 | 1.716 | 17.007 |
| Total | 34.943 | 4.319 | 4.331 | 43.593 |

Se abrió SQLite con URI `mode=ro`. Se verificaron existencia de rutas e integridad relacional, sin decodificar cada imagen ni recalcular todos los hashes. Los archivos faltantes de rechazados son compatibles con `purge-duplicates`, que conserva filas de bloqueo; no se reconstruyó la causa de cada eliminación. Los huérfanos de grupos requieren investigación y reparación independiente con respaldo: `quick_check=ok` no implica integridad de claves foráneas.

El esquema base tiene siete tablas funcionales. `duplicates.py` añade `imagen_huella`, `grupo_duplicado` y `grupo_duplicado_miembro`; la base local también tiene la tabla interna `sqlite_sequence`.

##### Modelo y resultados

Archivo compartido: `utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt`.

SHA-256: `79407f5537418bc258857fa54723d8e39b152505ad3a6f6a6ea4f97e1dfcb35c`.

El JSON de evaluación existente registra 1.424 imágenes test, época 15, CPU y umbral 0,5. Sus componentes son tipo 94,94 %, Jaccard de color 68,42 %, Jaccard de estilo 69,21 % y macro 77,52 %. Se verificaron los artefactos; no se repitió la evaluación completa. El checkpoint carece del estado de optimizador/scheduler para una reanudación exacta.

Las limitaciones sobre etiquetas de IA, desbalance, casi duplicados y dominio visual están en [evaluación](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md). El análisis previo de casi duplicados y su cifra de sensibilidad se conservan como evidencia reportada; no se recalcularon aquí. La diferencia de métricas entre modelos no dispone de prueba de significancia estadística.

##### Correcciones y orden documental

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

##### Repetir las verificaciones

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

##### Pendientes técnicos identificados

1. Investigar y sanear los miembros de grupos huérfanos, con respaldo y comprobación de que se conserva la trazabilidad de duplicados.
2. Verificar permisos de uso y la calidad de etiquetas mediante revisión independiente; `train.py` no audita documentos de licencia.
3. Evitar casi duplicados entre splits antes de la próxima evaluación y mantener un test independiente de nuevas decisiones de ajuste.
4. Medir GPU real, tiempos, memoria y concurrencia en el entorno final. El servicio CPU reutiliza una imagen PyTorch con CUDA, aunque la inferencia se ejecuta en CPU.
5. Validar proveedores remotos en una prueba acotada autorizada si se retoma la anotación; los nombres configurados no acreditan disponibilidad del proveedor.

---


### Evidencias de integridad (SHA-256) para reproducibilidad

*Fuente: [`docs/evaluacion/EVIDENCIAS-INTEGRIDAD-SHA256.md`](docs/evaluacion/EVIDENCIAS-INTEGRIDAD-SHA256.md)*


Documento de referencia con los **SHA-256 completos** necesarios para comprobar la integridad criptográfica del proyecto y de futuras ejecuciones. Complementa los resúmenes que usan hashes truncados (suficientes para distinguir visualmente ejecuciones, pero no para verificar integridad).

##### 1. Por qué son necesarios los hashes completos

| Uso | Truncado (8 dígitos) | Completo (64 dígitos) |
|---|---|---|
| Distinguir visualmente ejecuciones | Sí | Sí |
| Comprobar que un archivo no cambió | No | **Sí** |
| Reproducir la evaluación exactamente | No | **Sí** |
| Verificar qué checkpoint cargó la API | No | **Sí** |

Para replicar el proyecto o auditar una ejecución futura se debe poder recalcular el hash del archivo y compararlo con el valor registrado. Por eso se conservan aquí los valores completos.

##### 2. Checkpoints (pesos del modelo)

| Checkpoint | Rol | Época | SHA-256 completo |
|---|---|---|---|
| `utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt` | Referencia compartida (26-10) | 15 | `79407f5537418bc258857fa54723d8e39b152505ad3a6f6a6ea4f97e1dfcb35c` |
| `utilidades-entrenamiento/modelo-ia/runs/20261028-042931/best.pt` | Intento fallido desde cero (28-10) | 15 | `77fbd17bfebd1c9cb64d08fd9a31e691aa0beac2a7c2e615d42aeb0f3413dea8` |
| `utilidades-entrenamiento/modelo-ia/runs/20261029-022656/best.pt` | Desde cero corregido (29-10) | 23 | `8aacd8b45aa5f7c99461b48c4fcf4d9e998b6efd9134758234675477ed96d923` |

##### 3. Conjunto de prueba portable

| Elemento | Valor |
|---|---|
| Archivo | `tests/imagenes-test/manifest.json` |
| SHA-256 del manifest completo | `4e1b28e2b506d5d1c38331e516f0931178f931e8822e865867396d7e1c05cdc0` |
| Versión del manifest | 1 |
| Generado | 2026-10-26T03:23:27+00:00 |
| Imágenes referenciadas | 1.424 (cada una con su propio SHA-256) |
| Verificación contra disco | 1.424 / 1.424 sin discrepancias |

El hash del manifest completo fija la **definición del conjunto de prueba** (lista de imágenes, etiquetas de referencia, clases y umbral). Los hashes por imagen fijan el contenido de cada fotografía.

##### 4. Base de datos del dataset

| Elemento | Valor |
|---|---|
| Archivo | `dataset/metadata.sqlite` |
| SHA-256 (estado al entrenamiento 29-10) | `246713975fd632899f7b34cf7fbdb585c2f2a45e616322e8ad61c847b5cef75f` |

Este hash coincide con el campo `sha256_metadata` del registro de entrenamiento (`registro_entrenamiento.sqlite`), lo que acredita que la base actual es la que se usó en la ejecución `20261029-022656`.

##### 5. Cómo obtenerlos automáticamente

La API de pruebas los calcula y expone en tiempo de ejecución, sin intervención manual:

```bash
# /health devuelve checkpoint.sha256 y manifest.sha256
curl -s http://127.0.0.1:8082/health

# /test/informe incluye checkpoint_sha256 y manifest_sha256
curl -s http://127.0.0.1:8082/test/informe | python3 -m json.tool
```

Y en línea de comandos:

```bash
sha256sum utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt
sha256sum tests/imagenes-test/manifest.json
sha256sum dataset/metadata.sqlite
```

##### 6. Verificación de una ejecución futura

1. Registrar el **SHA-256 completo** del checkpoint que se cargó y del `manifest.json` usado.
2. Tras la ejecución, recalcular `sha256sum` de ambos archivos y comparar con lo registrado.
3. Si coinciden, la ejecución usó exactamente los mismos pesos y el mismo conjunto de prueba; si no, se declara la discrepancia y la ejecución no es comparable.

---


### Registro DSR: errores del entrenamiento y correcciones aplicadas

*Fuente: [`docs/evaluacion/DSR-ERRORES-Y-CORRECCIONES.md`](docs/evaluacion/DSR-ERRORES-Y-CORRECCIONES.md)*


Documento de trazabilidad del **ciclo de diseño** de Design Science Research Methodology (DSRM) aplicado al clasificador MobileNetV3-Small. Registra los errores cometidos, su diagnóstico, las correcciones implementadas y la verificación del cambio. Complementa la teoría del método de evaluación en [`TEORIA-METODO-EVALUACION.md`](docs/teoria/TEORIA-METODO-EVALUACION.md).

---

##### 1. Contexto: el artefacto y su requisito de aceptación

- **Artefacto evaluado:** clasificador MobileNetV3-Small que predice **tipo** (multiclase), **color** y **estilo** (multietiqueta) a partir de una fotografía de prenda.
- **Requisito verificable (R11):** promedio macro ≥ **70 %**, calculado como media aritmética no ponderada de la exactitud de tipo y el Jaccard por imagen de color y estilo, sobre el conjunto de prueba fijo (1.424 imágenes portables).
- **Referencia documentada:** checkpoint compartido (`mobilenetv3-small-best.pt`, época 15 del entrenamiento del 26-10) con **macro 77,52 %** (tipo 94,94 %, color Jaccard 68,42 %, estilo Jaccard 69,21 %).

Las actividades DSRM que estructuran este registro son: identificación del problema → diagnóstico (diseño) → intervención (desarrollo) → verificación (evaluación) → lecciones (comunicación).

---

##### 2. Identificación del problema

Tras los primeros entrenamientos, se observaron dos síntomas que debían explicarse:

1. Un entrenamiento **interrumpido durante el warmup** producía un modelo con colapso del recall de color.
2. Un entrenamiento **desde cero** configurado manualmente no alcanzaba R11 (macro **61,78 %**), muy por debajo del nivel esperado.

La pregunta de investigación del ciclo: **¿qué configuración de hiperparámetros permite entrenar desde cero alcanzando el nivel de referencia sin degradar el modelo?**

---

##### 3. Errores anteriores (evidencia y diagnóstico)

###### 3.1. Error E1 — Entrenamiento detenido durante el calentamiento (26-10)

| Elemento | Detalle |
|---|---|
| Ejecución | `20261026-020700` |
| Configuración | lr 0,001 · finetune_lr 1e-4 · warmup 3 · epochs 30 · pretrained sí |
| Observado | Se registraron **solo 3 épocas**; val_loss final 0,795 |
| Mecanismo | Con warmup = 3, el *backbone* preentrenado permanece congelado durante las 3 primeras épocas y solo se descongela después. Al detenerse en la época 3, el modelo **nunca liberó el backbone**; las cabezas aprendieron con features fijas y sin ajuste fino. |
| Consecuencia | Colapso del recall de color (la tarea multietiqueta más dependiente del backbone) y pérdida de capacidad de generalización. |

**Diagnóstico DSR (ciclo de diseño):** el fallo no fue de la arquitectura sino de la **condición de ejecución**: se evaluó/comparó un estado incompleto del entrenamiento (fase de warmup) como si fuera un resultado final. La lección: **no interpretar una ejecución truncada como un entrenamiento terminado**.

###### 3.2. Error E2 — Tasas de aprendizaje de continuación usadas para entrenar desde cero (28-10)

| Elemento | Detalle |
|---|---|
| Ejecución | `20261028-042931` |
| Configuración usada | lr **1e-4** · finetune_lr **1e-5** · warmup **0** · epochs **15** · pretrained sí |
| Naturaleza del error | Se reutilizó una receta pensada para **ajuste fino/continuación** (tasas pequeñas, sin warmup) como si fuera válida para **entrenamiento desde cero**. |
| Mecanismo | Las cabezas se inicializan aleatoriamente; con lr 1e-4/1e-5 avanzan demasiado lento para converger en 15 épocas. El color (14 etiquetas, desbalanceadas) es la tarea que primero manifiesta el subajuste. |
| Resultado medido | **Macro 61,78 %** (tipo 89,37 %, color Jaccard **33,2 %**, estilo Jaccard 62,78 %). R11 **no cumplido**; color en colapso (recall de test 29,3 %). |

**Diagnóstico DSR (ciclo de rigor):** el error fue de **definición operacional**: se confundieron dos perfiles de entrenamiento con objetivos distintos.

| Perfil | Objetivo | Tasas | Warmup |
|---|---|---|---|
| Continuación / ajuste fino | Reanudar un modelo ya entrenado sin romper lo aprendido | lr 1e-4 · finetune_lr 1e-5 | 0 |
| **Desde cero** | Aprender cabezas nuevas y ajustar el backbone con rapidez | **lr 0,001 · finetune_lr 1e-4** | **3** |

---

##### 4. Correcciones realizadas (intervención)

###### 4.1. Corrección de la configuración desde cero

Se corrigió [`desde-cero.yaml`](utilidades-entrenamiento/configs/desde-cero.yaml) para reproducir la receta que históricamente alcanzó el nivel de referencia:

```yaml
learning_rate: 0.001
finetune_lr: 0.0001
warmup_epochs: 3
epochs: 30
pretrained: true
finetune: true
early_stopping_patience: 5
```

Cambio esencial respecto del error E2: **subir las tasas a 0,001/1e-4 y restaurar 3 épocas de warmup**, de modo que las cabezas (aleatorias) converjan rápido y el backbone se descongele de forma controlada.

###### 4.2. Correcciones operativas en el panel de entrenamiento

- Se añadió el **selector de configuración** en el monitor y el endpoint `/api/configs`, para que el usuario elija la receta correcta sin editar archivos a mano.
- Se corrigió el **enrutamiento de `/api/start?config=…`**: antes se comparaba la ruta exacta y una petición con parámetros devolvía **404 «No encontrado»**; ahora se compara solo la parte de ruta.
- Efecto en DSR: se eliminó una **fuente de error humano** (elegir la configuración equivocada) y una **fuente de error de interfaz** (lanzar el entrenamiento fallaba sin indicar la causa).

---

##### 5. Verificación del cambio (evaluación)

###### 5.1. Verificación de la configuración ejecutada

La nueva ejecución `20261029-022656` cargó exactamente la receta corregida: lr 0,001 · finetune_lr 1e-4 · warmup 3 · epochs 30 · pretrained sí · early stopping 5. ✔

###### 5.2. Comportamiento del entrenamiento

| Observación | Valor |
|---|---|
| Épocas ejecutadas | 28 de 30 (parada temprana) |
| Mejor época (best.pt) | 23 |
| val_loss época 1 → 28 | 1,025 → 0,535 |
| Exactitud de tipo en validación (ép. 28) | 93,56 % |
| F1 color / estilo en validación (ép. 28) | 0,738 / 0,779 |

La curva muestra aprendizaje sostenido y sin divergencia; la parada temprana actuó correctamente tras el warmup.

###### 5.3. Resultado sobre el conjunto de prueba portable (1.424 imágenes)

| Métrica | Referencia (26-10) | Fallido E2 (28-10) | **Nuevo (29-10)** |
|---|---:|---:|---:|
| Tipo (exactitud) | 94,94 % | 89,37 % | 94,03 % |
| Color (Jaccard) | 68,42 % | 33,20 % | **69,28 %** |
| Estilo (Jaccard) | 69,21 % | 62,78 % | **69,29 %** |
| **Promedio macro** | **77,52 %** | **61,78 %** | **77,53 %** |
| R11 (macro ≥ 70 %) | Cumple | No cumple | **Cumple** |

Verificación con la misma fuente (conjunto portable de 1.424 imágenes, mismo preprocesamiento y umbral 0,5) y también sobre el split `test` del nodo de entrenamiento (1.421 imágenes): macro **77,55 %** (tipo 94,02 %, color 69,33 %, estilo 69,30 %).

###### 5.4. Conclusión de la verificación

1. **El entrenamiento se hizo correctamente:** configuración verificada, 28 épocas completas, parada temprana válida, sin colapso de color.
2. **Mejoró respecto del entrenamiento fallido:** macro **77,53 %** frente a 61,78 % (+15,75 pp), recuperando por completo el recall de color (69,28 % frente a 33,20 %).
3. **Frente a la referencia:** macro prácticamente idéntico (77,53 % vs 77,52 %). Se observa un intercambio: color (+0,86 pp) y estilo (+0,08 pp) mejoran, mientras tipo baja (−0,91 pp). Es decir, **la receta corregida reproduce el nivel de referencia, pero no lo supera**.
4. **R11 cumplido:** sí, con margen de +7,53 pp sobre el umbral de 70 %.

---

##### 6. Lecciones aprendidas y prevención de recurrencia

| Lección DSR | Consecuencia operativa |
|---|---|
| La configuración de **continuación** no sirve para **desde cero**; son perfiles distintos. | Mantener `default.yaml`/`desde-cero.yaml` (desde cero) separados del perfil de continuación, con nombres explícitos. |
| Un entrenamiento **truncado en warmup** no es un resultado final. | No evaluar ni comparar ejecuciones con menos épocas que el warmup; registrar el motivo de finalización. |
| Los parámetros de la petición deben manejarse en la **ruta**, no en la cadena completa. | `/api/start?config=…` ya compara solo la parte de ruta. |
| La comparación justa exige **misma muestra y mismas condiciones**. | Verificar el checkpoint cargado (SHA-256) y el conjunto de imágenes en cada ejecución. |

**Limitaciones que persisten:** el split de entrenamiento cambió levemente entre la referencia (11.616) y la nueva ejecución (11.592) por la depuración de duplicados, por lo que la comparación debe declarar ese factor; las etiquetas de color/estilo proceden de IA (NVIDIA NIM y DeepSeek), de modo que se mide concordancia con esas anotaciones, no con una verdad de terreno humana.

---

##### 7. Referencias

- Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). Design Science in Information Systems Research. *MIS Quarterly*, 28(1), 75–105.
- Peffers, K., Tuunanen, T., Rothenberger, M. A., & Chatterjee, S. (2007). A Design Science Research Methodology for Information Systems Research. *Journal of Management Information Systems*, 24(3), 45–77.
- Guía de contenido del informe DSRM y Anexo G (documento de trabajo del proyecto).
- [`TEORIA-METODO-EVALUACION.md`](docs/teoria/TEORIA-METODO-EVALUACION.md) — teoría del método de evaluación.

---


### Registro de entrenamiento — 20261029-022656

*Fuente: [`docs/evaluacion/ENTRENAMIENTO-20261029-022656.md`](docs/evaluacion/ENTRENAMIENTO-20261029-022656.md)*


Documento de trazabilidad del entrenamiento **desde cero** corregido del clasificador MobileNetV3-Small. Complementa [`DSR-ERRORES-Y-CORRECCIONES.md`](docs/evaluacion/DSR-ERRORES-Y-CORRECCIONES.md) (diagnóstico de errores anteriores) y [`TEORIA-METODO-EVALUACION.md`](docs/teoria/TEORIA-METODO-EVALUACION.md) (método de evaluación).

---

##### 1. Identificación

| Campo | Valor |
|---|---|
| Ejecución (run id) | `20261029-022656` |
| Fecha de inicio / fin | 2026-10-29 02:26 / 03:57 UTC |
| Checkpoint final | `modelo-ia/runs/20261029-022656/best.pt` |
| SHA-256 del checkpoint | `8aacd8b45aa5f7c99461b48c4fcf4d9e998b6efd9134758234675477ed96d923` |
| Época del checkpoint | 23 |
| Umbral multietiqueta | 0,5 |
| SHA-256 de `metadata.sqlite` | `246713975fd632899f7b34cf7fbdb585c2f2a45e616322e8ad61c847b5cef75f` |

##### 2. Configuración ejecutada

| Parámetro | Valor | Parámetro | Valor |
|---|---|---|---|
| Arquitectura | MobileNetV3-Small | image_size | 224 |
| batch_size | 64 | epochs | 30 |
| learning_rate | **0,001** | finetune_lr | **0,0001** |
| warmup_epochs | **3** | pretrained | sí |
| weight_decay | 0,0001 | label_smoothing | 0,05 |
| augment | sí | class_weighted | sí |
| amp | sí | early_stopping_patience | 5 |
| multilabel_threshold | 0,5 | seed | 42 |

Esta es la receta corregida de [`desde-cero.yaml`](utilidades-entrenamiento/configs/desde-cero.yaml): tasas altas (0,001/1e-4) para cabezas recién inicializadas + 3 épocas de warmup antes de descongelar el backbone.

##### 3. Objetivo

Verificar que, con la configuración corregida, un entrenamiento **desde cero** alcanza el requisito **R11** (promedio macro ≥ 70 %) y reproduce el nivel del checkpoint de referencia (macro 77,52 %), sin el colapso de color del intento fallido del 28-10 (macro 61,78 %).

##### 4. Ejecución y evolución de la validación

El entrenamiento completó **28 de 30 épocas** y la parada temprana actuó correctamente: el mejor `val_loss` se obtuvo en la **época 23** (0,5329) y no se superó en las 5 épocas siguientes, por lo que terminó en la época 28.

| Época | val_loss | Exactitud tipo | F1 color | F1 estilo |
|---|---:|---:|---:|---:|
| 1 (inicio warmup) | 1,025 | 0,845 | 0,332 | 0,718 |
| 3 (fin warmup) | 0,856 | 0,876 | 0,496 | 0,734 |
| 6 | 0,589 | 0,920 | 0,687 | 0,762 |
| 12 | 0,545 | 0,931 | 0,731 | 0,770 |
| **23 (mejor)** | **0,533** | 0,935 | 0,738 | 0,777 |
| 28 (final) | 0,535 | 0,936 | 0,738 | 0,779 |

**Lectura de la curva:** descenso rápido de `val_loss` hasta la época ~11 y luego una **meseta** (0,533–0,545) desde la época 14. La exactitud de tipo y el F1 de color/estilo se estabilizan en 0,93–0,94 / 0,73–0,74 / 0,77–0,78. No hay divergencia ni sobreajuste visible, pero tampoco mejora marginal relevante tras la época 23.

##### 5. Evaluación sobre el conjunto de prueba

###### 5.1. Conjunto portable (1.424 imágenes, el mismo de la referencia)

| Métrica | Valor |
|---|---:|
| Tipo (exactitud) | **94,03 %** (1.339 / 1.424) |
| Color (Jaccard) | **69,28 %** |
| Estilo (Jaccard) | **69,29 %** |
| **Promedio macro** | **77,53 %** |

###### 5.2. Split `test` del nodo de entrenamiento (1.421 imágenes)

| Métrica | Valor |
|---|---:|
| Tipo (exactitud) | 94,02 % (1.336 / 1.421) |
| Color (Jaccard) | 69,33 % |
| Estilo (Jaccard) | 69,30 % |
| **Promedio macro** | **77,55 %** |

Ambas mediciones coinciden dentro de ±0,02 pp y confirman **R11 cumplido** (+7,5 pp sobre el umbral de 70 %).

##### 6. Comparación con ejecuciones previas

| Métrica | Fallido E2 (28-10) | Referencia (26-10) | **Este entrenamiento** |
|---|---:|---:|---:|
| Tipo | 89,37 % | 94,94 % | 94,03 % |
| Color Jaccard | 33,20 % | 68,42 % | **69,28 %** |
| Estilo Jaccard | 62,78 % | 69,21 % | **69,29 %** |
| **Macro** | **61,78 %** | **77,52 %** | **77,53 %** |
| R11 | No | Sí | **Sí** |

Frente al intento fallido, la mejora es **+15,75 pp** de macro (recuperación total del color). Frente a la referencia, el resultado es **estadísticamente idéntico** (77,53 vs 77,52), con color y estilo ligeramente superiores y tipo ligeramente inferior (−0,91 pp).

##### 7. Veredicto

1. **Ejecución correcta:** configuración verificada, warmup respetado, parada temprana válida, sin colapso de color.
2. **Objetivo cumplido:** R11 satisfecho y nivel de referencia reproducido desde cero.
3. **Resultado:** válido como modelo final; no supera al checkpoint de referencia, sino que lo iguala.

##### 8. Decisión sobre continuar el entrenamiento

**No se recomienda continuar con la misma receta.** La validación ya está en meseta desde la época 14 y la parada temprana confirmó que el mejor punto (época 23) no se superó en 5 épocas posteriores; más épocas solo aumentarían el riesgo de sobreajuste al split de validación sin ganancia esperada.

Opciones si se desea intentar superar el 77,53 %:

1. **Aceptar este modelo como final** (recomendado): ya iguala la referencia y cumple R11.
2. **Ajuste fino corto desde `best.pt`** con el perfil de continuación (lr 1e-4/1e-5, warmup 0, 5–10 épocas, patience 3) y re-evaluar en test. Ganancia esperada **≤ 1 pp**, con riesgo de sobreajuste; solo tiene sentido como experimento controlado, no como rutina.
3. **No repetir desde cero con más épocas**: la receta ya convergió; aumentar `epochs` no aporta.

Si se elige la opción 2, debe registrarse como una ejecución nueva y evaluarse sobre el mismo conjunto portable de 1.424 imágenes para poder compararla con este registro.

---

##### 9. Trazabilidad

- Configuración: `utilidades-entrenamiento/modelo-ia/runs/20261029-022656/config.json`.
- Métricas por época: `utilidades-entrenamiento/modelo-ia/runs/20261029-022656/metrics.json`.
- Evaluación en test (nodo): `utilidades-entrenamiento/modelo-ia/evaluaciones/evaluacion_propiedades_test_20261029-022656.json`.
- Checkpoint: `utilidades-entrenamiento/modelo-ia/runs/20261029-022656/best.pt` (SHA-256 en la sección 1).

---


### Plan de correcciones — Auditoría Anexo G (01-11-2026)

*Fuente: [`docs/evaluacion/PLAN-CORRECCIONES-AUDITORIA-ANEXO-G.md`](docs/evaluacion/PLAN-CORRECCIONES-AUDITORIA-ANEXO-G.md)*


Plan de trabajo para atender las 20 observaciones de la auditoría `Auditoria_Actualizada_Anexo_G_01-11-2026.xlsx` (Anexo G / MobileNetV3-Small). Objetivo: corregir lo corregible, generar los datos necesarios y, si se aprueba, reentrenar con los parámetros documentados para cerrar las observaciones que lo exigen.

**Estado de la auditoría:** 20 observaciones → 14 pendientes, 4 parciales, 2 por verificar. P1 (alta) = 11.

---

##### 1. Clasificación de las observaciones

| ID | Prioridad | Tipo de corrección | Fase | ¿Requiere reentrenar? |
|---|---|---|---|---|
| AUD-026 | P1 | Datos (procedencia por fuente) | F2 | No |
| AUD-053 | P1 | Datos (hashes) | F2 | No |
| AUD-054 | P1 | Datos (separación de splits) | F2 | No |
| AUD-055 | P1 | Declaración (validez de etiquetas) | F3 | No |
| AUD-056 | P1 | Datos (matriz de ejecución) | F2 | No |
| AUD-007 | P1 | Editorial (síntesis 5.4) | F1 | No |
| G-002 | P1 | Editorial (fecha) | F1 | No |
| G-003 | P1 | Editorial (definición "desde cero") | F1 | No |
| G-006 | P1 | Datos (trazabilidad técnica) | F2 | No |
| G-007 | P1 | Declaración + opcional holdout | F3/F4 | **Sí (opción B)** |
| AUD-020 | P2 | Editorial (índice con folios) | F1 | No |
| AUD-068 | P2 | Datos (incertidumbre) + redacción | F2/F4 | **Sí (opción B)** |
| AUD-028 | P2 | Editorial (tipografía) | F1 | No |
| AUD-030 | P2 | Datos (línea de tiempo) | F2 | No |
| G-001 | P1 | Editorial (numeración) | F1 | No |
| G-004 | P2 | Editorial (licencias) | F1 | No |
| G-005 | P2 | Editorial (estilos de figuras) | F1 | No |
| G-008 | P2 | Datos (errores por clase) | F2 | No |
| G-009 | P2 | Editorial (organización) | F1 | No |
| G-010 | P2 | Datos (vínculo figura↔CSV) | F2 | No |

---

##### 2. Fase 1 — Correcciones editoriales (manuales en Word, sin datos)

1. **AUD-020** — Generar índice con folios reales y navegación a encabezados; validar portada contra la guía UES.
2. **G-001** — Renumerar tablas consecutivamente: fuentes → G3, tratamientos → G4, resultados → G5 (o mover fuentes tras G4); actualizar todas las remisiones.
3. **G-002** — Cambiar fecha de portada de «25 de octubre» a «29 de octubre de 2026» o posterior; añadir control de versión y distinguir fecha del proyecto vs. fecha del informe de ensayos.
4. **G-003** — Sustituir «desde cero» por «ejecución independiente iniciada desde pesos preentrenados (ImageNet), sin reanudar un checkpoint previo»; reservar «desde cero» para pesos aleatorios. Los tres runs usan `pretrained=true`, `finetune=true`.
5. **G-004** — Renombrar la columna «Uso comercial y condiciones» por «Licencia y condiciones de uso aplicables al entrenamiento».
6. **G-005** — Unificar estilos `GCaptionNum`/`GCaptionTitle` y separar rótulos de imágenes en párrafos estables; regenerar lista de figuras.
7. **AUD-007** — Dejar en §5.4 solo la síntesis (metodología mínima + una tabla comparativa de 3 filas) y trasladar al Anexo G las 11 tablas por ejecución y las figuras de respaldo; renumerar tablas del cuerpo.
8. **AUD-028** — Corregir «MovileNetV3» → «MobileNetV3-Small» en §7; homogeneizar «run id», «fine-tuning» y denominaciones de §5.4.
9. **G-009** — Mover dHash, fuentes y filtros a un subapartado «Construcción y depuración del dataset» dentro de §4; dejar §2.1 solo con el objetivo de evaluación.
10. **AUD-068 (parte redaccional)** — Describir referencia (77,52 %) y corregida (77,53 %) como **equivalentes** a la precisión reportada; eliminar cualquier afirmación de superioridad.

---

##### 3. Fase 2 — Generación de datos desde el repositorio (sin reentrenar)

Datos ya disponibles o generables con consultas a `dataset/metadata.sqlite`, `registro_entrenamiento.sqlite` y los JSON de evaluación. Se entregarán como CSV/JSON en `docs/datos-auditoria/`.

###### AUD-026 — Procedencia por fuente (desglose inicial → final)
Fuente de datos: `prenda.codigo` (prefijos `mendeley-*`, `clothing-small-*`, `clothing-*`).

| Fuente | Versión / fecha | Total ingresado | Aprobado | Rechazado | Otro estado |
|---|---:|---:|---:|---:|---:|
| AIG-Dataset (Mendeley) | DOI 10.17632/pxkbgkydrp.1, v1 (2025-04-17) | 53.055 | 11.227 | 23.443 | 18.385 |
| Clothing Dataset Small | GitHub (snapshot; sin versión) | 2.513 | 2.510 | 1 | 2 |
| Clothing Dataset | GitHub (snapshot; sin versión) | 778 | 690 | 0 | 88 |
| **Total** | — | **56.346** | **14.427** | **23.444** | **18.475** |

Cierre: balance trazable `56.346 → 14.427` por fuente y filtros (aprobado + apto + split).

###### AUD-053 — Integridad de hashes
Ya documentado en `docs/EVIDENCIAS-INTEGRIDAD-SHA256.md`. Entregar además la salida real de la API:
- `GET http://127.0.0.1:8082/health` (campos `checkpoint.sha256`, `manifest.sha256`).
- `GET http://127.0.0.1:8082/test/informe` (campos `checkpoint_sha256`, `manifest_sha256`).

| Checkpoint | SHA-256 completo |
|---|---|
| `modelos-compartidos/mobilenetv3-small-best.pt` (época 15) | `79407f5537418bc258857fa54723d8e39b152505ad3a6f6a6ea4f97e1dfcb35c` |
| `runs/20261028-042931/best.pt` (época 15) | `77fbd17bfebd1c9cb64d08fd9a31e691aa0beac2a7c2e615d42aeb0f3413dea8` |
| `runs/20261029-022656/best.pt` (época 23) | `8aacd8b45aa5f7c99461b48c4fcf4d9e998b6efd9134758234675477ed96d923` |
| `tests/imagenes-test/manifest.json` | `4e1b28e2b506d5d1c38331e516f0931178f931e8822e865867396d7e1c05cdc0` |

###### AUD-054 — Separación de splits
- Partición por prenda: **0 prendas con más de un split** (verificado: `split` es columna única por prenda). Conteos: train 11.592, val 1.414, test 1.421.
- Casi duplicados entre particiones (dHash, Hamming ≤ 2): 2.467 grupos tocan train∩test; 780 test∩val; 2.282 train∩val. Incluir la **tabla de sensibilidad** ya calculada en `CORRECCIONES-INFORME.md` §4.3 (77 imágenes de test con casi duplicado en train; macro 77,52 → 76,96 al excluirlas).
- Nota de rigor: el dHash≤2 es conservador (76 de 77 pares fueron marcados por revisor como "no duplicadas"); reportarlo como cota, no como fuga confirmada.

###### AUD-056 / G-006 — Matriz de ejecución y trazabilidad técnica
Fuente: `registro_entrenamiento.sqlite` (tablas `ejecucion`, `imagen_entrenamiento`) + evaluaciones.

| Run id | Fecha (UTC) | Config | sha256 metadata | Checkpoint | Época | Test (portable) | Macro |
|---|---|---|---|---|---|---|---|
| 20261026-021300 | 2026-10-26 02:13 | lr 0,001/1e-4, warmup 3 | `58013102…` (dataset 11.616) | compartido | 15 | 94,94/68,42/69,21 | 77,52 |
| 20261028-042931 | 2026-10-28 04:29 | lr 1e-4/1e-5, warmup 0 | `24671397…` (dataset 11.592) | best.pt | 15 | 89,40/33,17/62,79 | 61,79 |
| 20261029-022656 | 2026-10-29 02:26 | lr 0,001/1e-4, warmup 3 | `24671397…` (dataset 11.592) | best.pt | 23 | 94,03/69,28/69,29 | 77,53 |

Declarar explícitamente que la referencia usó una versión anterior de `metadata.sqlite` (sha `58013102…`) con split train de 11.616.

###### G-008 — Errores por clase
Extraer de `modelo-ia/evaluaciones/*.json` los bloques `por_etiqueta` (precisión, recall, F1 y soporte por clase de color y estilo) y presentar como tablas resumen + principales confusiones.

###### G-010 — Vínculo figura ↔ datos
Mapear cada figura a su CSV/script:
| Figura | Datos | Archivo |
|---|---|---|
| G1–G3 (curvas) | validación por época | `docs/datos-graficos/validacion_por_epoca.csv` |
| G4 (comparación) | resultados test | `docs/datos-graficos/resultados_test.csv` |
| Script de gráficas | HTML autónomo | `figuras_entrenamiento_APA7.html` |

###### AUD-030 — Línea de tiempo
`20261026-021300` (referencia) → hallazgo: detención prematura en warmup (`20261026-020700`, 3 épocas) y colapso de color → `20261028-042931` (configuración de continuación usada desde cero, macro 61,79) → decisión: restaurar receta `default.yaml` → `20261029-022656` (macro 77,53). Vincular cada paso a logs y commits.

---

##### 4. Fase 3 — Declaraciones metodológicas (sin reentrenar)

###### AUD-055 — Revisión manual de 50 imágenes
No existe registro cuantificado de las 50 imágenes (muestreo, errores por propiedad). Cierre recomendado: **declararlo como control limitado** y cuantificarlo solo si las 50 imágenes son identificables; en caso contrario, no atribuir al macro una exactitud humana. Complementar con el acuerdo entre proveedores ya medido (349 imágenes: color 64,2 % exacta / 75,7 % Jaccard; estilo 55,9 % / 73,8 %) como indicador del ruido de etiquetas.

###### G-007 — Uso del conjunto test
Declaración verificable: la configuración corregida **no se buscó sobre test**; se restauró la receta ya documentada `default.yaml`/`desde-cero.yaml` (la misma que produjo la referencia). El checkpoint de cada run se eligió por **validación**; el test se usó una vez por checkpoint para la tabla comparativa. Declarar la limitación residual y, si se exige un holdout intacto, pasar a Fase 4.

---

##### 5. Fase 4 — Reentrenamiento con parámetros documentados (si se aprueba)

**Objetivo:** cerrar AUD-068 (incertidumbre) y G-007 (holdout limpio) con evidencia nueva.

###### Configuración fija (documentada y reproducible)
`utilidades-entrenamiento/configs/default.yaml` (equivale a `desde-cero.yaml`):
```
image_size: 224 · batch_size: 64 · epochs: 30
learning_rate: 0.001 · finetune_lr: 0.0001 · warmup_epochs: 3
pretrained: true · finetune: true · weight_decay: 0.0001
label_smoothing: 0.05 · class_weighted: true · augment: true · amp: true
early_stopping_patience: 5 · seed: 42
```

###### Protocolo
1. **Congelar la receta antes de ejecutar** (no se toca el test para elegir config).
2. Ejecutar **N = 3 semillas** (seed 42, 123, 2026) del mismo config; seleccionar checkpoint por **validación**.
3. Evaluar cada checkpoint **una sola vez** sobre el test portable (1.424 imágenes, API en CPU, umbral 0,5).
4. Reportar macro medio ± desviación y **intervalo de confianza bootstrap** por imagen (diferencias pareadas referencia vs. corregida).

###### Costo y cronograma (CPU)
- Cada corrida ~30 épocas ≈ 1,5–2 h en CPU; 3 semillas ≈ **5–6 h**.
- Alternativa GPU (`docker compose --profile gpu`): si hay GPU disponible, reduce el tiempo significativamente.

###### Criterio de cierre
- AUD-068: tabla con media/desvío/IC bootstrap y redacción «equivalente / no superior».
- G-007: bitácora de decisiones que demuestre que el test no guió la selección de configuración.

---

##### 6. Orden de ejecución sugerido

1. **F1 + F2 en paralelo** (no dependen de reentrenar): generar `docs/datos-auditoria/` con los CSV/JSON y aplicar correcciones editoriales.
2. **F3**: redactar las declaraciones de AUD-055 y G-007.
3. **Decisión F4**: si el tribunal exige repeticiones/holdout, ejecutar las 3 semillas y regenerar AUD-068.
4. **Cierre**: volver a validar documentación (`python3 docs/validar_documentacion.py`), actualizar INDICE y commit.

---

##### 7. Entregables esperados

| Observación | Entregable |
|---|---|
| AUD-026 | Tabla fuente→cantidades + balance 56.346 → 14.427 |
| AUD-053 | `docs/EVIDENCIAS-INTEGRIDAD-SHA256.md` + salida real de `/health` y `/test/informe` |
| AUD-054 | Reporte de cruce de splits + sensibilidad dHash |
| AUD-056 / G-006 | Matriz run→checkpoint→SHA→fecha→archivo |
| AUD-068 | IC bootstrap + redacción equivalente (requiere F4) |
| G-008 | Tablas de errores por clase (color/estilo) |
| G-010 | Mapa figura→CSV→script |
| AUD-030 | Línea de tiempo run→hallazgo→decisión→run |
| Resto editorial | Documento Word corregido (Anexo G v4 + §5.4 sintetizado) |

---


### Datos para gráficos del entrenamiento

*Fuente: [`docs/datos-graficos/README.md`](docs/datos-graficos/README.md)*


CSV y JSON generados desde los `metrics.json` y las evaluaciones de los tres entrenamientos documentados (referencia `20261026-021300`, fallido `20261028-042931` y corregido `20261029-022656`).

##### Archivos

| Archivo | Contenido |
|---|---|
| `validacion_por_epoca.csv` | Métricas de validación por época (63 filas = 20 + 15 + 28). |
| `resultados_test.csv` | Resultados del test portable de 1.424 imágenes por ejecución. |
| `datos_graficos.json` | Ambas fuentes en un único JSON. |
| `figuras_entrenamiento_APA7.html` | Informe HTML original con figuras y tablas. |
| `figuras_entrenamiento_APA7_corregido.html` | Informe HTML corregido según la auditoría del Anexo G (trazabilidad, procedencia, errores por clase, equivalencia y limitaciones). |

##### Columnas de `validacion_por_epoca.csv`

`run_id`, `rol`, `epoch`, `train_loss`, `val_loss`, `tipo_accuracy`, `color_precision`, `color_recall`, `color_f1`, `estilo_precision`, `estilo_recall`, `estilo_f1`.

Los porcentajes están en escala **0–1** (multiplicar por 100 para %).

##### Gráficos sugeridos

1. **Curvas de aprendizaje:** `val_loss` y `train_loss` frente a `epoch`, una línea por `run_id`.
2. **Evolución de tipo:** `tipo_accuracy` frente a `epoch`.
3. **Evolución de color:** `color_f1` (o `color_recall`) frente a `epoch`; evidencia el colapso del run fallido.
4. **Evolución de estilo:** `estilo_f1` frente a `epoch`.
5. **Barras comparativas:** `resultados_test.csv` — tipo, color Jaccard, estilo Jaccard y macro por ejecución, con la línea de referencia R11 en 70 %.

##### Regenerar el informe HTML

El HTML corregido se genera con el script [`generar_informe_entrenamiento.py`](utilidades-entrenamiento/generar_informe_entrenamiento.py), que lee los datos crudos (`metrics.json`, `evaluaciones/*.json`, `registro_entrenamiento.sqlite`, `metadata.sqlite`) y deja un log con cada cálculo en `informe_entrenamiento.log`.

En el host:

```bash
python3 utilidades-entrenamiento/generar_informe_entrenamiento.py --output-dir docs/datos-graficos
```

En el contenedor Docker (misma salida, log en `informe_entrenamiento.log`):

```bash
docker run --rm --user 1000:1000 \
  -v "$PWD/utilidades-entrenamiento/modelo-ia:/app/modelo-ia" \
  -v "$PWD/utilidades-entrenamiento/modelos-compartidos:/app/modelos-compartidos:ro" \
  -v "$PWD/dataset:/app/dataset:ro" \
  -v "$PWD/docs/datos-graficos:/app/salida" \
  -v "$PWD/utilidades-entrenamiento/generar_informe_entrenamiento.py:/app/generar_informe_entrenamiento.py:ro" \
  --entrypoint python modelo-general-destilacion-curator:latest \
  /app/generar_informe_entrenamiento.py \
    --modelo-ia /app/modelo-ia \
    --modelos-compartidos /app/modelos-compartidos \
    --dataset-sqlite /app/dataset/metadata.sqlite \
    --output-dir /app/salida
```

---


## 8. Teoría y método


### Teoría del entrenamiento de MobileNetV3-Small para reconocimiento de prendas

*Fuente: [`docs/teoria/TEORIA-ENTRENAMIENTO-COMPLETO.md`](docs/teoria/TEORIA-ENTRENAMIENTO-COMPLETO.md)*


**Documento de referencia (≈10 páginas).** Resume la teoría que sustenta el entrenamiento implementado en [`utilidades-entrenamiento/train.py`](utilidades-entrenamiento/train.py) y las configuraciones [`default.yaml`](utilidades-entrenamiento/configs/default.yaml) y [`desde-cero.yaml`](utilidades-entrenamiento/configs/desde-cero.yaml). Los valores numéricos citados corresponden a la implementación real del repositorio, no a ejemplos genéricos.

---

##### 1. Contexto y objetivo del modelo

El sistema clasifica una fotografía de una prenda de vestir en tres propiedades simultáneas:

| Tarea | Tipo de problema | Salida |
|---|---|---|
| Tipo de prenda | Clasificación **multiclase** (una sola clase) | 1 de 9 clases (`abrigo`, `blusa`, `camisa`, `chaqueta`, `falda`, `pantalon`, `short`, `sueter`, `vestido`) |
| Color | Clasificación **multietiqueta** | Subconjunto de 14 colores |
| Estilo | Clasificación **multietiqueta** | Subconjunto de 12 estilos |

Una prenda tiene exactamente un tipo, pero puede presentar varios colores y varios estilos a la vez. Por eso el tipo se modela como una decisión excluyente y el color/estilo como decisiones independientes por etiqueta. El umbral de decisión multietiqueta es **0,5** (`multilabel_threshold`): una etiqueta se considera presente si su probabilidad predicha es ≥ 0,5.

El criterio de aceptación del artefacto es el requisito **R11: promedio macro de las tres propiedades ≥ 70 %** (exactitud de tipo, Jaccard de color y Jaccard de estilo, con igual ponderación).

---

##### 2. Fundamentos de visión por computador y redes convolucionales

###### 2.1. La imagen como tensor

Una imagen RGB se representa como un tensor de forma `(3, H, W)`: tres canales (rojo, verde, azul) y una cuadrícula de píxeles de alto `H` y ancho `W`. Antes de entrar al modelo, cada imagen se redimensiona a **224×224** (la resolución nativa de los pesos ImageNet de MobileNetV3) y se normaliza con la media y desviación estándar de ImageNet:

$$\hat{x} = \frac{x - \mu}{\sigma},\qquad \mu=(0.485, 0.456, 0.406),\quad \sigma=(0.229, 0.224, 0.225)$$

La normalización pone cada canal en una escala comparable y es **obligatoria** para que los pesos preentrenados operen en el rango para el que fueron calibrados.

###### 2.2. Convolución

Una capa convolucional desliza un **filtro** (kernel) de `k×k` sobre la imagen y calcula, en cada posición, el producto punto entre el filtro y el parche local. Los filtros aprenden detectores de patrones locales: bordes, texturas, formas. Conceptos asociados:

- **Padding:** relleno de ceros en los bordes para conservar la resolución espacial.
- **Stride:** paso con el que se desplaza el filtro; un stride > 1 reduce la resolución.
- **Canales de salida:** cada filtro produce un **mapa de características** (feature map); `C_out` filtros producen `C_out` mapas.

###### 2.3. Jerarquía de características

Las CNN aprenden una jerarquía: las primeras capas detectan bordes y texturas; las capas medias combinan esos patrones en partes (cuellos, mangas, cierres); las capas finales forman conceptos de alto nivel (la forma de una prenda). Esta jerarquía es la razón por la que un backbone entrenado en un dominio visual general (ImageNet) es reutilizable en un dominio específico (prendas).

###### 2.4. Pooling

El **pooling** reduce la resolución espacial tomando el máximo (max-pooling) o el promedio (average-pooling) de una ventana. Aporta invarianza a pequeños desplazamientos y reduce el costo computacional. MobileNetV3 usa, antes de la clasificación, un **global average pooling** que colapsa cada mapa de características a un único valor, produciendo un vector compacto de características.

---

##### 3. MobileNetV3-Small

MobileNetV3-Small es una red convolucional **ligera** (≈2,5 millones de parámetros) diseñada por Google para dispositivos con recursos limitados. Es la arquitectura declarada del modelo (`architecture: mobilenet_v3_small`).

###### 3.1. Convolución separable en profundidad (depthwise separable convolution)

Es el bloque fundamental que reduce el costo. Una convolución estándar `k×k` sobre `C_in` canales y con `C_out` filtros cuesta aproximadamente:

$$H\cdot W\cdot C_{in}\cdot C_{out}\cdot k^2$$

La convolución separable la divide en dos pasos:

1. **Depthwise:** un filtro `k×k` **por canal de entrada** (no mezcla canales): costo `H·W·C_in·k²`.
2. **Pointwise:** una convolución `1×1` que combina canales: costo `H·W·C_in·C_out`.

La relación de costo frente a la convolución estándar es aproximadamente:

$$\frac{1}{C_{out}} + \frac{1}{k^2}$$

Con `k=3` y `C_out` grande, la convolución separable cuesta entre 8 y 9 veces menos, manteniendo una capacidad expresiva razonable.

###### 3.2. Bloque residual invertido con cuello de botella lineal

MobileNetV2/V3 organizan las capas en **bloques residuales invertidos**:

- **Expansión:** un pointwise `1×1` expande los canales (factor de expansión típico 3–6).
- **Depthwise `3×3`** procesa espacialmente los canales expandidos.
- **Proyección `1×1`** comprime de nuevo los canales (cuello de botella).
- **Conexión residual (skip):** suma la entrada a la salida cuando las formas coinciden, facilitando el flujo de gradientes en redes profundas.

El **cuello de botella lineal** evita aplicar una no linealidad (ReLU) en el espacio comprimido, donde destruiría información útil.

###### 3.3. Squeeze-and-Excitation (SE)

Los bloques de MobileNetV3 incluyen un módulo **Squeeze-and-Excitation**: un global pooling "comprime" (squeeze) cada canal a un escalar y una pequeña red "excita" (excite) calcula pesos por canal que recalibran la importancia de cada feature map. Es una atención por canal barata que mejora la calidad sin añadir apenas costo.

###### 3.4. Activación h-swish

MobileNetV3 sustituye ReLU por **hard-swish** en capas intermedias/tardías:

$$\text{h-swish}(x) = x\cdot\frac{\text{ReLU6}(x+3)}{6}$$

Aproxima swish con operaciones baratas y es más estable en cuantización y en hardware móvil.

###### 3.5. Por qué es adecuada

- **Bajo costo:** permite entrenar e inferir en CPU o en una GPU modesta.
- **Transferencia directa:** existe un checkpoint preentrenado en ImageNet de calidad.
- **Multitarea:** su backbone produce un vector de características que alimenta tres cabezas lineales pequeñas.

---

##### 4. Aprendizaje por transferencia y ajuste fino

###### 4.1. Transferencia de aprendizaje

Entrenar una CNN desde pesos aleatorios exige millones de imágenes. En su lugar se parte de pesos **preentrenados en ImageNet** (≈1,2 millones de imágenes, 1000 clases), que ya codifican detectores generales de bordes, texturas y formas. El entrenamiento solo **adapta** esas representaciones al dominio de prendas.

###### 4.2. Congelar y descongelar el backbone

- **Backbone congelado (freeze):** sus parámetros no reciben gradiente y no se actualizan. Solo se entrenan las cabezas.
- **Backbone descongelado (fine-tuning):** todos los parámetros se actualizan, el backbone con una tasa menor para no destruir las características preentrenadas.

La implementación controla esto en [`train.py`](utilidades-entrenamiento/train.py) mediante `set_backbone_trainable()`:

- Si `finetune=true` y `warmup_epochs=0`, el backbone queda **descongelado desde la época 1**.
- Si `finetune=true` y `warmup_epochs>0`, el backbone inicia **congelado** y se descongela en la época `warmup_epochs + 1`.

###### 4.3. Calentamiento de cabezas (warmup)

En la fase de calentamiento, las cabezas (inicializadas aleatoriamente) se entrenan solas durante `warmup_epochs` épocas, mientras el backbone permanece congelado. Esto evita que los gradientes grandes y ruidosos de las cabezas recién inicializadas degraden las características preentrenadas.

###### 4.4. Tasas de aprendizaje diferenciales

El optimizador usa **dos tasas de aprendizaje**:

| Grupo de parámetros | Parámetro | Valor recomendado |
|---|---|---|
| Cabezas (`type_head`, `color_head`, `style_head`) | `learning_rate` | **0,001** desde cero; **0,0001** en continuación |
| Backbone | `finetune_lr` | **0,0001** desde cero; **0,00001** en continuación |

> **Lección verificada en el proyecto:** entrenar desde cero con la tasa de continuación (1e-4/1e-5) deja las cabezas sub-entrenadas y produce un recall de color colapsado (macro ≈ 61,8 %). Las cabezas aleatorias necesitan la tasa mayor (0,001). La tasa baja solo es apropiada para **afinar un modelo ya convergido**.

---

##### 5. Formulación multitarea y multietiqueta

El modelo es una red **multitarea**: un único backbone compartido alimenta tres cabezas lineales.

###### 5.1. Cabeza de tipo (multiclase)

Produce un logit por clase (`9`). Se aplica **softmax**, que convierte los logits en una distribución de probabilidad que suma 1:

$$P(y=c \mid x) = \frac{e^{z_c}}{\sum_{j} e^{z_j}}$$

La clase predicha es la de mayor probabilidad (`argmax`).

###### 5.2. Cabezas de color y estilo (multietiqueta)

Producen un logit por etiqueta (`14` colores, `12` estilos). Se aplica **sigmoide** a cada logit de forma independiente:

$$P(\text{etiqueta}_i = 1 \mid x) = \sigma(z_i) = \frac{1}{1+e^{-z_i}}$$

Cada etiqueta se decide por separado: una prenda puede tener varios colores y varios estilos. La etiqueta se considera presente si `σ(z_i) ≥ 0,5`.

###### 5.3. Tratamiento de etiquetas no anotadas

En la evaluación, una prenda sin etiquetas de color (o estilo) **no entra** en el cálculo de color (o estilo): la métrica solo se calcula sobre prendas con esa propiedad anotada. En el entrenamiento, la pérdida de color/estilo se enmascara análogamente para no penalizar como "ausente" lo que simplemente no fue anotado.

---

##### 6. Funciones de pérdida

###### 6.1. Entropía cruzada (tipo)

Para la clasificación multiclase se minimiza la **entropía cruzada** entre la distribución real (one-hot) y la predicha:

$$\mathcal{L}_{tipo} = -\sum_c y_c \log P(c \mid x)$$

###### 6.2. Entropía cruzada binaria (color y estilo)

Para cada etiqueta multietiqueta se usa **entropía cruzada binaria con logits** (BCEWithLogits):

$$\mathcal{L}_{color} = -\sum_i \left[ y_i \log \sigma(z_i) + (1-y_i)\log(1-\sigma(z_i)) \right]$$

La pérdida total es la suma de las tres tareas, aplicando las máscaras de anotación en color y estilo.

###### 6.3. Label smoothing

Con `label_smoothing = 0.05`, la etiqueta objetivo del tipo deja de ser one-hot puro (`1`/`0`) y se suaviza:

$$y^{LS}_c = (1-\alpha)\, y_c + \frac{\alpha}{C},\qquad \alpha=0.05$$

Evita que el modelo persiga una confianza del 100 % y mejora la calibración y la generalización.

###### 6.4. Ponderación por clase

Con `class_weighted = true`, la pérdida de cada clase se multiplica por un peso inversamente proporcional a su frecuencia (con raíz cuadrada para suavizar):

$$w_c \propto \frac{1}{\sqrt{f_c}}$$

Esto compensa el desbalance (por ejemplo, muchas más blusas que faldas o suéteres) y evita que el modelo ignore las clases raras. Como efecto secundario, el modelo puede volverse más conservador en las clases raras, lo que se observa en el recall.

---

##### 7. Optimización

###### 7.1. Descenso de gradiente estocástico y lotes

El entrenamiento avanza por **épocas** (una pasada completa por train) y **lotes** (`batch_size = 64`). Cada lote produce un gradiente estimado y una actualización de pesos. Un lote mayor da gradientes más estables pero consume más memoria.

###### 7.2. AdamW

Se usa **AdamW**: Adam con **weight decay desacoplado**. Adam mantiene medias móviles del gradiente (primer momento) y de su cuadrado (segundo momento) para adaptar el paso de cada parámetro:

$$m_t = \beta_1 m_{t-1} + (1-\beta_1) g_t,\qquad v_t = \beta_2 v_{t-1} + (1-\beta_2) g_t^2$$

$$\theta_t = \theta_{t-1} - \eta \cdot \frac{\hat{m}_t}{\sqrt{\hat{v}_t}+\epsilon} - \eta\,\lambda\,\theta_{t-1}$$

El término `η·λ·θ` es el **weight decay** (`weight_decay = 0.0001`): una penalización L2 desacoplada que reduce el sobreajuste.

###### 7.3. Planificador coseno

`CosineAnnealingLR` reduce la tasa de aprendizaje desde su valor inicial hasta casi cero siguiendo una curva coseno a lo largo de `epochs`:

$$\eta_t = \eta_{min} + \frac{\eta_{max}-\eta_{min}}{2}\left(1 + \cos\left(\frac{t}{T_{max}}\pi\right)\right)$$

Permite dar pasos grandes al inicio y pasos finos al final para converger con suavidad.

---

##### 8. Regularización y generalización

###### 8.1. Aumento de datos

Con `augment = true`, cada época aplica variaciones aleatorias: **recorte aleatorio redimensionado** (RandomResizedCrop), **volteo horizontal** y **jitter de brillo/contraste**. El tono no se altera deliberadamente para no falsear la etiqueta de color. El aumento expande efectivamente el dataset y reduce el sobreajuste.

###### 8.2. Otras regularizaciones

- **Weight decay** (sección 7.2).
- **Label smoothing** (sección 6.3).
- **Parada temprana:** si el `val_loss` no mejora durante `early_stopping_patience = 5` épocas consecutivas (contadas **después del warmup**), el entrenamiento se detiene.

###### 8.3. Checkpoint por validación

En cada época se guarda `best.pt` **solo si** el `val_loss` mejora. El modelo final es el de menor pérdida de validación, no necesariamente el de la última época. La selección del checkpoint **no** consulta el test.

###### 8.4. Separación de particiones y fuga de datos

Los datos se dividen en **train / val / test**. La partición se hace **por prenda** (todas las fotos de una prenda van al mismo split) para evitar **data leakage**: si una prenda apareciera en train y en test, el modelo la habría "visto" y el resultado se inflaría. Solo se usan prendas `aprobadas` y `aptas_para_entrenamiento = 1`. El test se evalúa **una única vez** con el modelo final.

---

##### 9. Eficiencia: precisión mixta y ejecución

###### 9.1. Precisión mixta (AMP)

Con `amp = true`, las operaciones seguras se ejecutan en **16 bits** (half) y las críticas en 32 bits. Un **GradScaler** escala la pérdida para evitar que gradientes pequeños se redondeen a cero en half. En GPU con Tensor Cores reduce memoria y acelera; en CPU el escaler se desactiva (`enabled=use_cuda and amp`).

###### 9.2. Carga de datos

`num_workers = 8` son procesos que leen y transforman imágenes en paralelo, evitando que el cómputo espere a la entrada/salida. `shm_size` amplía la memoria compartida del contenedor para estos procesos.

###### 9.3. CPU frente a GPU

El proyecto entrena tanto en CPU como en GPU. La GPU (CUDA) acelera enormemente las convoluciones; en CPU el entrenamiento es viable pero lento (≈3 min/época en el hardware de referencia). El dispositivo se elige con `--device auto|cpu|cuda`.

---

##### 10. Métricas de evaluación

Con TP (verdaderos positivos), FP (falsos positivos) y FN (falsos negativos):

$$\text{Precisión} = \frac{TP}{TP+FP},\qquad \text{Recall} = \frac{TP}{TP+FN},\qquad F_1 = \frac{2\cdot P\cdot R}{P+R}$$

###### 10.1. Exactitud de tipo

Porcentaje de imágenes cuyo tipo predicho coincide con la etiqueta real:

$$\text{Accuracy} = \frac{\text{tipos correctos}}{T}$$

Se complementa con **F1 macro** por clase y la **matriz de confusión**.

###### 10.2. Jaccard (IoU) por imagen para color y estilo

Para una imagen, con `P_i` el conjunto de etiquetas predichas y `R_i` el conjunto real:

$$J_i = \frac{|P_i \cap R_i|}{|P_i \cup R_i|}$$

Se define `J_i = 1` si ambos conjuntos están vacíos. El **Jaccard promedio** es `(1/T)·Σ J_i`. También se reporta la **coincidencia exacta** (fracción de imágenes con `P_i = R_i`).

###### 10.3. Promedio macro

Media aritmética sin ponderar de las tres propiedades (cada una pesa 1/3):

$$\text{Macro} = \frac{\text{Acc}_{tipo} + \text{Jaccard}_{color} + \text{Jaccard}_{estilo}}{3}$$

###### 10.4. Umbral y curvas de precisión-recall

El umbral 0,5 fijo es **conservador** en color/estilo: subirlo aumenta la precisión y baja el recall; bajarlo hace lo contrario. La calibración correcta se hace sobre **validación** (curvas precisión-recall por etiqueta), nunca sobre test. Un recall muy bajo con precisión alta indica que el modelo omite etiquetas presentes — exactamente la firma observada en las ejecuciones degradadas.

---

##### 11. Diagnóstico de entrenamiento y análisis de degradación

###### 11.1. Interpretar curvas de pérdida

| Patrón | Interpretación |
|---|---|
| `train_loss` baja y `val_loss` baja | Convergencia sana |
| `train_loss` baja y `val_loss` sube de forma sostenida | Sobreajuste |
| Ambas se mantienen altas | Subajuste o configuración inadecuada |
| `val_loss` oscila | Ruido de etiquetas, lote pequeño o LR alta |

En este proyecto, `train_loss` y `val_loss` **no son directamente comparables**: el entrenamiento aplica aumento de datos y label smoothing, mientras que la validación no.

###### 11.2. Hipótesis sobre la degradación observada

El [análisis de degradación](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md) y las ejecuciones registradas permiten ordenar hipótesis:

- **H1. Ausencia de ajuste fino tras el warmup:** la ejecución del 26/10 configuró `warmup_epochs=3` y se detuvo en la época 3; el backbone nunca se descongeló. Es la hipótesis principal.
- **H2. Tasa de aprendizaje demasiado alta:** el 26/10 usó 0,001/0,0001 (correcta para desde cero, pero el experimento cambió varias variables a la vez, así que su efecto no quedó aislado).
- **H3. Umbral 0,5 conservador:** produce recall bajo en color; se comprueba calibrando en validación.
- **H4. Desbalance y ruido de etiquetas:** factor limitante documentado.
- **H5. Sobreajuste por exceso de épocas:** **no demostrado**; las ejecuciones de más épocas no fueron peores.

###### 11.3. Plan experimental controlado

Para separar los efectos se proponen (análisis DSR):

| Prueba | LR cabezas | LR backbone | Backbone congelado | Épocas máx |
|---|---:|---:|---|---:|
| A — Ajuste fino desde el inicio | 0,001 | 0,0001 | No | 30 |
| B — Calentamiento controlado | 0,001 | 0,0001 | Primeras 3 | 30 |
| C — Fine-tune con LR de backbone menor | 0,001 | 0,00005 | No | 30 |

Manteniendo constantes dataset, particiones, batch, transformaciones, pesos iniciales, semilla, pérdida y procedimiento de evaluación.

---

##### 12. Configuración concreta del proyecto

###### 12.1. Hiperparámetros principales

| Parámetro | `default.yaml` / `desde-cero.yaml` (desde cero) | Estrategia de continuación `fine_tune` |
|---|---|---|
| `image_size` | 224 | 224 |
| `batch_size` | 64 | 64 |
| `epochs` | 30 | 10 |
| `learning_rate` (cabezas) | **0,001** | 0,0001 |
| `finetune_lr` (backbone) | **0,0001** | 0,00001 |
| `warmup_epochs` | 3 | 0 |
| `finetune` | true | true |
| `pretrained` | true (ImageNet) | false (carga checkpoint) |
| `seed` | 42 | 42 |
| `multilabel_threshold` | 0,5 | 0,5 |
| `weight_decay` | 0,0001 | 0,0001 |
| `label_smoothing` | 0,05 | 0,05 |
| `class_weighted` | true | true |
| `augment` | true | true |
| `amp` | true | true |
| `early_stopping_patience` | 5 | 5 |

###### 12.2. Trazabilidad

Cada ejecución crea `modelo-ia/runs/<fecha-hora>/` con `config.json`, `metrics.json` (métricas por época), `progress.json`, `test_metrics.json` y `best.pt`. El ledger `registro_entrenamiento.sqlite` guarda el **SHA-256** de cada imagen usada por ejecución, permitiendo auditar qué datos vio cada modelo y detectar imágenes nuevas.

###### 12.3. Reproducibilidad

- **Semilla fija** (`seed = 42`) para los sorteos de aumento y partición.
- **Mismo preprocesamiento** (resize 224 + normalización ImageNet) en train, val y test.
- **Selección por validación** del checkpoint; el test se evalúa una sola vez al final.

---

##### 13. Referencias

- Howard, A., et al. (2019). *Searching for MobileNetV3*. ICCV.
- Sandler, M., et al. (2018). *MobileNetV2: Inverted Residuals and Linear Bottlenecks*. CVPR.
- Hu, J., Shen, L., & Sun, G. (2018). *Squeeze-and-Excitation Networks*. CVPR.
- He, K., Zhang, X., Ren, S., & Sun, J. (2016). *Deep Residual Learning for Image Recognition*. CVPR.
- Kingma, D. P., & Ba, J. (2015). *Adam: A Method for Stochastic Optimization*. ICLR.
- Loshchilov, I., & Hutter, F. (2019). *Decoupled Weight Decay Regularization* (AdamW). ICLR.
- Loshchilov, I., & Hutter, F. (2017). *SGDR: Stochastic Gradient Descent with Warm Restarts* (cosine schedule). ICLR.
- Szegedy, C., et al. (2016). *Rethinking the Inception Architecture for Computer Vision* (label smoothing). CVPR.
- Shorten, C., & Khoshgoftaar, T. M. (2019). *A survey on Image Data Augmentation for Deep Learning*.

---

*Documento derivado de la implementación real del repositorio; no sustituye los artefactos de cada ejecución. Consulta [`TEORIA-ENTRENAMIENTO.md`](docs/teoria/TEORIA-ENTRENAMIENTO.md) para el glosario rápido y [`EVALUACION-ENTRENAMIENTO.md`](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md) para resultados.*

---


### Terminología y teoría del entrenamiento

*Fuente: [`docs/teoria/TEORIA-ENTRENAMIENTO.md`](docs/teoria/TEORIA-ENTRENAMIENTO.md)*


> **Referencia conceptual.** Para configuración, estado y resultados vigentes consulta el [resumen del proyecto](<docs/resumen/RESUMEN-PROYECTO.md>); los ejemplos teóricos no sustituyen los artefactos de cada ejecución.

Explica los conceptos detrás del entrenamiento que hace este proyecto (`utilidades-entrenamiento/train.py`, configuración en `configs/default.yaml`).

##### 1. Qué se está entrenando

Un **clasificador de imágenes multitarea**: dada la foto de una prenda, predice a la vez:

| Tarea | Tipo de problema | Salida |
|---|---|---|
| Tipo de prenda (blusa, falda, short…) | Clasificación de **una sola clase** | una clase entre 9 |
| Color | Clasificación **multi-etiqueta** | varios colores posibles |
| Estilo | Clasificación **multi-etiqueta** | varios estilos posibles |

Una prenda tiene un único tipo, pero puede tener varios colores y estilos; por eso se tratan distinto.

##### 2. Modelo y arquitectura

- **Red neuronal:** función con millones de parámetros (pesos) que transforma una imagen en números. Aprender es ajustar esos pesos.
- **MobileNetV3-Small:** red convolucional ligera (~2,5 M de parámetros) diseñada para móviles y equipos modestos. Es la única arquitectura del MVP.
- **Backbone (base / extractor de características):** parte convolucional que convierte la imagen en un vector de características (colores, texturas, formas).
- **Cabezas (heads):** tres capas lineales pequeñas (`type_head`, `color_head`, `style_head`) que leen ese vector y producen las predicciones. Comparten el backbone: es lo que hace al modelo "multitarea".
- **Logit:** salida cruda de una cabeza, antes de convertirla en probabilidad.
- **Softmax:** convierte los logits del tipo en probabilidades que suman 1 (solo gana una clase).
- **Sigmoide:** convierte cada logit de color/estilo en una probabilidad independiente entre 0 y 1.
- **Umbral (`multilabel_threshold`, 0.5):** una etiqueta de color/estilo se considera presente si su probabilidad supera el umbral.

##### 3. Aprendizaje por transferencia (transfer learning)

Entrenar desde cero requiere millones de imágenes. En su lugar se parte de pesos **preentrenados en ImageNet** (1,2 M de imágenes), que ya saben detectar bordes, texturas y formas. Solo se adaptan a las prendas.

Se hace en dos fases (`warmup_epochs` y `finetune`):

1. **Calentamiento (warmup):** el backbone está **congelado** (sus pesos no cambian) y solo se entrenan las cabezas, que empiezan con valores aleatorios. Evita que gradientes grandes y ruidosos destruyan lo ya aprendido.
2. **Ajuste fino (fine-tuning):** se **descongela** todo el backbone y se sigue con una tasa de aprendizaje mucho menor (`finetune_lr`) para especializarlo en ropa.

##### 4. Ciclo de entrenamiento

- **Época (epoch):** una pasada completa por todas las imágenes de entrenamiento.
- **Lote (batch) y `batch_size`:** grupo de imágenes procesadas juntas (64). Un lote mayor estabiliza el gradiente pero consume más VRAM.
- **Paso / iteración:** procesar un lote y actualizar los pesos una vez. Pasos por época = imágenes / batch_size.
- **Pérdida (loss):** número que mide cuánto se equivoca el modelo; entrenar es minimizarlo.
  - Tipo: **entropía cruzada** (cross-entropy).
  - Color y estilo: **entropía cruzada binaria** (BCE con logits), una por etiqueta.
  - La pérdida total es la suma de las tres. Para color/estilo solo cuentan las prendas que tienen esas etiquetas anotadas (una etiqueta ausente se trata como "no anotada", no como negativa).
- **Retropropagación (backpropagation):** calcula cuánto contribuyó cada peso al error (gradiente).
- **Gradiente:** dirección en que hay que mover cada peso para reducir la pérdida.
- **Optimizador (AdamW):** regla que usa los gradientes para actualizar los pesos; adapta el paso de cada parámetro. Aplica además **weight decay** (decaimiento de pesos, `weight_decay`), una penalización leve a pesos grandes que reduce el sobreajuste.
- **Tasa de aprendizaje (learning rate, `learning_rate`):** tamaño del paso de actualización. Muy alta: inestable; muy baja: lenta. Cabezas: 1e-3; backbone en ajuste fino: 1e-4.
- **Planificador coseno (CosineAnnealingLR):** reduce la tasa de aprendizaje siguiendo una curva coseno hasta casi 0 al final, para converger con pasos finos.

##### 5. Conjuntos de datos (splits)

| Split | Uso |
|---|---|
| **train** | Ajustar los pesos. |
| **val** (validación) | Medir tras cada época, elegir el mejor checkpoint, ajustar umbrales y decidir cuándo parar. No se entrena con él. |
| **test** | Evaluación final, **una sola vez** con el mejor modelo. Da la estimación honesta de rendimiento real. |

La partición se hace **por prenda** (todas las fotos de una prenda van al mismo split) para evitar **fuga de datos (data leakage)**: si una misma prenda estuviera en train y test, el resultado se inflaría.

Solo se usan prendas con `estado_revision = 'aprobado'` y `apta_para_entrenamiento = 1`.

##### 6. Generalización: sobreajuste y regularización

- **Sobreajuste (overfitting):** el modelo memoriza el entrenamiento y falla con imágenes nuevas. Síntoma: la pérdida de train baja pero la de val sube.
- **Subajuste (underfitting):** el modelo no aprende ni siquiera el entrenamiento.
- **Regularización:** técnicas que combaten el sobreajuste:
  - **Aumento de datos (`augment`):** variaciones aleatorias en cada época (recorte aleatorio redimensionado, volteo horizontal, ligero cambio de brillo/contraste). No se altera el tono para no falsear el color.
  - **Label smoothing (0.05):** evita que el modelo se vuelva excesivamente seguro; suaviza las etiquetas objetivo del tipo.
  - **Weight decay** (ver sección 4).
  - **Parada temprana (`early_stopping_patience`, 5):** se detiene si la pérdida de validación no mejora durante 5 épocas seguidas.
- **Checkpoint (`best.pt`):** archivo con los pesos del mejor momento según la pérdida de validación; no necesariamente el de la última época.

##### 7. Desbalance de clases

Hay muchas más blusas (≈6 300) que faldas (≈400) o suéteres (≈400). Sin corrección el modelo tiende a favorecer las clases mayoritarias. Se usa **ponderación por clase** (`class_weighted`): la pérdida de cada clase se multiplica por un peso inversamente proporcional a su frecuencia (con raíz cuadrada para suavizarlo). Por eso conviene mirar el rendimiento **por clase**, no solo el global.

##### 8. Eficiencia: GPU y precisión mixta

- **GPU / CUDA:** la GPU NVIDIA procesa en paralelo miles de operaciones; CUDA es su plataforma de cómputo. Sin GPU el entrenamiento corre en CPU, mucho más lento.
- **VRAM:** memoria de la GPU (6 GB en la RTX 2060). Limita el tamaño de lote y de imagen.
- **Precisión mixta (AMP, `amp`):** usa números de 16 bits donde es seguro y 32 donde hace falta. Reduce memoria y acelera en GPU con Tensor Cores (Turing las tiene). El **GradScaler** escala la pérdida para evitar que gradientes pequeños se redondeen a cero.
- **`num_workers`:** procesos que leen y transforman imágenes en paralelo para que la GPU no espere.
- **`shm_size`:** memoria compartida del contenedor; necesaria para que esos procesos intercambien lotes.
- **Resolución (`image_size`, 224):** tamaño al que se redimensiona cada imagen. 224 px es la resolución nativa con la que se preentrenaron los pesos; más pequeña ahorra cómputo pero pierde detalle.
- **Normalización:** las imágenes se restan/dividen por la media y desviación de ImageNet, que es lo que espera el backbone preentrenado.

##### 9. Métricas de evaluación

- **Accuracy (exactitud) del tipo:** porcentaje de prendas con el tipo correcto.
- Para color y estilo (multi-etiqueta), con TP = verdaderos positivos, FP = falsos positivos y FN = falsos negativos:

$$\text{Precisión}=\frac{TP}{TP+FP}\qquad \text{Recall}=\frac{TP}{TP+FN}\qquad F_1=\frac{2\cdot P\cdot R}{P+R}$$

  - **Precisión:** de lo que el modelo dijo que había, cuánto era cierto.
  - **Recall (exhaustividad):** de lo que realmente había, cuánto detectó.
  - **F1:** media armónica de ambas; penaliza que una sea baja.
- **Matriz de confusión:** tabla clase real vs. predicha; muestra qué clases se confunden (por ejemplo, falda con short).
- Subir el umbral aumenta la precisión y baja el recall; bajarlo hace lo contrario. Se ajusta en `val`, nunca en `test`.

##### 10. Trazabilidad y reproducibilidad

- **Semilla (`seed`):** fija los números aleatorios para poder repetir un experimento.
- **Ejecución (run):** cada entrenamiento crea `modelo-ia/runs/<fecha-hora>/` con `config.json`, `metrics.json`, `test_metrics.json`, `progress.json` y `best.pt`.
- **Registro de imágenes:** `modelo-ia/registro_entrenamiento.sqlite` guarda qué imágenes (con su **hash SHA-256**) se usaron en cada ejecución. El hash identifica el contenido del archivo, de modo que se puede saber qué imágenes son nuevas al crecer el dataset.
- **Contenedor (Docker):** empaqueta código, dependencias y entorno para que el entrenamiento sea idéntico y portable entre equipos. El dataset se monta en solo lectura.

##### 11. Limitaciones conocidas

- El modelo clasifica **una prenda por foto**; no detecta ni separa varias prendas en una imagen (eso requeriría detección de objetos).
- Las etiquetas proceden de anotación asistida por IA y revisión humana; los errores de etiqueta limitan el techo de calidad.
- Las fuentes públicas pueden tener fondos y poses distintos al uso real: el rendimiento en producción puede ser menor que en `test`.
- El estilo es subjetivo; su F1 suele ser inferior al del tipo o el color.

##### 12. Glosario rápido

| Término | Significado |
|---|---|
| Backbone | Base convolucional que extrae características |
| Head | Capa final que produce una predicción concreta |
| Freeze / congelar | Impedir que unos pesos se actualicen |
| Fine-tuning | Reajustar pesos preentrenados con tasa baja |
| Epoch | Una pasada completa por el entrenamiento |
| Batch | Grupo de imágenes por paso |
| Loss | Medida del error a minimizar |
| Checkpoint | Pesos guardados en un momento dado |
| Overfitting | Memorizar en vez de generalizar |
| Data leakage | Información de test filtrada al entrenamiento |
| AMP | Precisión mixta 16/32 bits |
| F1 | Equilibrio entre precisión y recall |

---


### Teoría y conceptos del método de evaluación (DSRM)

*Fuente: [`docs/teoria/TEORIA-METODO-EVALUACION.md`](docs/teoria/TEORIA-METODO-EVALUACION.md)*


Documento de referencia conceptual sobre **cómo se mide** el desempeño del modelo de reconocimiento de prendas (MobileNetV3-Small). No incluye comandos, endpoints ni valores de ejecución: presenta únicamente la teoría y los conceptos del método de evaluación empleado, alineado con **Design Science Research Methodology (DSRM)** y con el protocolo documentado en el Anexo G.

---

##### 1. La evaluación dentro del diseño: DSRM

###### 1.1. Qué es la evaluación en Design Science

La evaluación es la actividad de Design Science que responde a una pregunta verificable: **¿el artefacto cumple los requisitos para los que fue diseñado?** No es un paso posterior al trabajo, sino una actividad integrada en el ciclo del método:

1. **Identificación del problema** — definir el hueco que el artefacto debe cubrir.
2. **Objetivos de la solución** — convertir ese problema en metas medibles.
3. **Diseño y desarrollo** — construir el artefacto (aquí, el clasificador de atributos).
4. **Demostración** — mostrar que el artefacto funciona en un caso controlado.
5. **Evaluación** — medir en qué grado cumple los objetivos, con rigor y evidencia.
6. **Comunicación** — publicar el problema, el artefacto y su utilidad verificada.

La evaluación exige que **el criterio de éxito sea observable y medible**. Por eso el objetivo general («reconocer el tipo, color y estilo de una prenda») se traduce en un requisito operativo: un valor numérico que se puede calcular, repetir y auditar.

###### 1.2. Los tres ciclos de rigor

Hevner y colaboradores estructuran la investigación en tres ciclos que la evaluación conecta:

- **Ciclo de relevancia:** conecta el problema real del entorno (describir prendas a partir de fotografías) con la investigación. Define *qué* es útil medir.
- **Ciclo de rigor:** conecta el artefacto con la base de conocimiento (teoría de clasificación, métricas, validación experimental). Define *cómo* medirlo correctamente.
- **Ciclo de diseño:** alterna construcción y evaluación del artefacto. Cada evaluación alimenta una nueva versión.

En el método descrito en este proyecto, el ciclo de diseño queda documentado por la **comparación de estados del entrenamiento** (checkpoints), mientras el ciclo de rigor queda garantizado por **condiciones de control** y **fórmulas explícitas** (secciones 5 y 7).

###### 1.3. Evaluación del artefacto frente a evaluación del proceso

Hay que distinguir dos objetos de evaluación distintos:

| Objeto | Pregunta que responde |
|---|---|
| **Artefacto (modelo)** | ¿Con qué precisión reconoce tipo, color y estilo en imágenes no vistas? |
| **Proceso (entrenamiento)** | ¿Mejoró o empeoró el artefacto entre dos estados? ¿Fue eficiente el entrenamiento? |

Ambos se apoyan en las **mismas métricas**, pero el segundo es **comparativo**: se evalúan dos o más versiones del mismo modelo sobre el mismo conjunto, y se interpreta la diferencia entre sus métricas. El primero es **absoluto**: se contrasta una única versión contra un umbral de aceptación.

---

##### 2. El problema de evaluación como clasificación supervisada

###### 2.1. Etiqueta de referencia y predicción

Toda evaluación supervisada compara dos objetos por cada muestra:

- **Etiqueta de referencia (verdad de terreno, *ground truth*):** el valor anotado que se asume correcto. En este proyecto las etiquetas proceden de modelos previos (IA de etiquetado) y de una revisión manual limitada; esta procedencia es una **limitación de validez**, no un error del método.
- **Predicción:** el valor que produce el modelo a evaluar.

La medición del desempeño es, por tanto, una **función de concordancia** entre predicciones y referencias. Cambia la métrica, no el principio.

###### 2.2. Dos naturalezas de tarea

El modelo resuelve tres tareas de naturaleza distinta, lo que obliga a usar métricas distintas:

- **Tipo de prenda — clasificación multiclase:** cada imagen pertenece a **exactamente una** clase dentro de un vocabulario cerrado (blusa, pantalón, falda, …). La salida es una distribución de probabilidad normalizada (softmax) y la decisión es la clase de mayor probabilidad.
- **Color y estilo — clasificación multietiqueta:** una prenda puede llevar **varias** etiquetas a la vez (por ejemplo, color {azul, blanco}). La salida son probabilidades independientes por etiqueta (sigmoide) y la decisión es el conjunto de etiquetas cuya probabilidad supera un umbral.

Confundir ambas naturalezas produce métricas sin sentido (por ejemplo, exigir una única clase ganadora en color, que es multietiqueta).

---

##### 3. Matriz de confusión y métricas elementales

###### 3.1. Verdaderos y falsos

Para una decisión binaria (la etiqueta está presente o no) se definen cuatro conteos:

| | Predicción positiva | Predicción negativa |
|---|---|---|
| **Real positiva** | Verdadero positivo (VP) | Falso negativo (FN) |
| **Real negativa** | Falso positivo (FP) | Verdadero negativo (VN) |

Todos los indicadores de esta sección se derivan de estos cuatro valores; la matriz de confusión multiclase y los conteos multietiqueta son generalizaciones directas.

###### 3.2. Exactitud (accuracy)

Proporción de decisiones correctas:

$$
\text{Exactitud} = \frac{VP + VN}{VP + VN + FP + FN}
$$

En clasificación **multiclase** se simplifica a la diagonal de la matriz de confusión: la proporción de muestras cuya clase predicha coincide con la clase real. Es la métrica natural para el tipo de prenda.

**Limitación:** es engañosa con clases muy desbalanceadas. Por eso se complementa con precisión y recall por clase (apartado 3.3) y nunca se usa sola para las tareas multietiqueta.

###### 3.3. Precisión, recall (sensibilidad) y F1

- **Precisión:** de todo lo que el modelo marcó como positivo, cuánto era realmente positivo.

$$
\text{Precisión} = \frac{VP}{VP + FP}
$$

- **Recall (sensibilidad o exhaustividad):** de todo lo realmente positivo, cuánto marcó el modelo.

$$
\text{Recall} = \frac{VP}{VP + FN}
$$

- **F1:** media armónica de precisión y recall; penaliza los desequilibrios extremos entre ambas.

$$
F_1 = 2 \cdot \frac{\text{Precisión} \cdot \text{Recall}}{\text{Precisión} + \text{Recall}} = \frac{2 \cdot VP}{2 \cdot VP + FP + FN}
$$

###### 3.4. Micro y macro promedio

Al agregar métricas de muchas etiquetas (o clases) hay dos estrategias:

- **Micro promedio:** se suman primero todos los VP, FP y FN y se calcula la métrica **global** sobre esos totales. Pondera implícitamente por la frecuencia de cada etiqueta: las clases más frecuentes dominan el resultado.
- **Macro promedio:** se calcula la métrica **por etiqueta** y luego se promedian esos valores, dando a cada etiqueta el mismo peso, sin importar su frecuencia. Refleja mejor el comportamiento en clases raras.

La elección entre micro y macro es una **decisión de interpretación**: micro describe el rendimiento global sobre el volumen de datos; macro describe el rendimiento promedio sobre el vocabulario.

###### 3.5. Matriz de confusión multiclase

Para una tarea de $K$ clases, la matriz $C \in \mathbb{Z}^{K \times K}$ acumula en $C_{ij}$ cuántas muestras de la clase real $i$ fueron predichas como clase $j$. La diagonal $C_{ii}$ contiene los aciertos. La exactitud multiclase es la suma de la diagonal dividida por el total, y cada fila permite derivar precisión y recall de esa clase.

---

##### 4. Métricas para clasificación multietiqueta

###### 4.1. La predicción como conjunto

En color y estilo, la predicción y la referencia son **conjuntos de etiquetas**: $P_i$ (predicho) y $R_i$ (real) para la imagen $i$. Toda la evaluación multietiqueta se reduce a comparar conjuntos.

###### 4.2. Coincidencia exacta (subset accuracy)

Proporción de imágenes donde ambos conjuntos son idénticos:

$$
\text{Exacta} = \frac{\#\{i : P_i = R_i\}}{T}
$$

Es la métrica más estricta: un solo error de etiqueta invalida la imagen. Es útil como diagnóstico, pero **infravalora** el acierto parcial: acertar 3 de 4 colores cuenta igual que acertar 0.

###### 4.3. Jaccard (intersección sobre unión)

El índice de Jaccard mide el **solapamiento** entre conjuntos:

$$
J(P_i, R_i) = \frac{|P_i \cap R_i|}{|P_i \cup R_i|}
$$

Toma valor 1 cuando los conjuntos coinciden, 0 cuando son disjuntos y un valor intermedio para aciertos parciales. El promedio por imagen es:

$$
\text{Jaccard} = \frac{1}{T} \sum_{i=1}^{T} J(P_i, R_i)
$$

**Convención del conjunto vacío:** si predicción y referencia son ambas vacías, la concordancia es total y se asigna $J = 1$; si solo una es vacía, $J = 0$. Esta convención evita divisiones indefinidas y debe quedar explícita en el protocolo, porque afecta al resultado en clases raras.

**Por qué Jaccard:** en tareas multietiqueta el acierto es gradual. Jaccard es la métrica estándar de similitud de conjuntos y reconoce el mérito parcial, al contrario que la coincidencia exacta. Es el indicador seleccionado para color y estilo en el criterio de aceptación.

---

##### 5. El indicador compuesto: promedio macro de propiedades

###### 5.1. Agregación de las tres tareas

El modelo produce tres indicadores parciales: exactitud de tipo, Jaccard de color y Jaccard de estilo. Para una única cifra resumen se usa la **media aritmética no ponderada**:

$$
\text{Macro} = \frac{\text{Exactitud}_{\text{tipo}} + \text{Jaccard}_{\text{color}} + \text{Jaccard}_{\text{estilo}}}{3}
$$

###### 5.2. Igual ponderación

Cada propiedad pesa exactamente $1/3$, independientemente de su dificultad o del número de clases que tenga. Esta decisión responde a una **definición operacional** del éxito: el sistema se considera útil si, **en promedio**, las tres capacidades funcionan por igual. La alternativa —ponderar por número de etiquetas— favorecería artificialmente a color y estilo (que tienen muchas más etiquetas que las clases de tipo).

###### 5.3. Interpretación y cuidado

- El macro es un **resumen**, no sustituye a las métricas por propiedad ni por etiqueta.
- Un macro alto puede ocultar el colapso de una propiedad concreta; por eso el informe siempre desagrega las tres componentes y, en el anexo, los valores por etiqueta.
- El criterio de aceptación se aplica **al macro**, no a cada propiedad individualmente: es posible cumplir el requisito con una propiedad por debajo del umbral si las otras lo compensan.

---

##### 6. Diseño experimental de la evaluación

###### 6.1. Unidad de análisis y muestra

- **Unidad de análisis:** cada imagen evaluada. En el diseño comparativo, la unidad secundaria es cada **versión de pesos (checkpoint)** sometida al mismo protocolo.
- **Muestra:** un conjunto fijo de imágenes **nunca usadas para entrenar ni para validar**. La muestra se mantiene constante entre evaluaciones para que las diferencias sean atribuibles al modelo y no a los datos.

###### 6.2. Particiones y holdout

El reparto en tres conjuntos es la base del rigor:

- **Entrenamiento:** ajusta los pesos.
- **Validación:** selecciona hiperparámetros y decide el checkpoint sin tocar el test.
- **Prueba (test):** se usa **una sola vez**, al final, para declarar el desempeño.

Usar el test repetidamente para elegir el mejor modelo lo convierte en un segundo conjunto de validación y **invalida** la estimación del error (el modelo acaba «memorizando» la selección). Esta es una regla fundamental del método.

###### 6.3. Fuga de información (data leakage)

La fuga ocurre cuando información del conjunto de prueba se filtra al entrenamiento o a la selección del modelo:

- Imágenes **duplicadas o casi duplicadas** entre particiones.
- Selección de hiperparámetros o del umbral usando el test.
- Normalización o vocabulario calculados sobre el test.

La prevención es una **condición de control** explícita: verificar el no solapamiento de imágenes entre particiones (por hash o similitud perceptual) y fijar el umbral a priori.

###### 6.4. Comparar checkpoints frente a repetir la misma prueba

Son dos diseños distintos que no deben confundirse:

- **Comparación de checkpoints:** varía una sola variable (la versión de pesos) manteniendo todo lo demás constante. Responde a *«¿mejoró el entrenamiento?»*.
- **Repetición de la misma prueba:** ejecuta el mismo checkpoint varias veces en las mismas condiciones. Responde a *«¿es reproducible?»* y mide variabilidad instrumental (debería ser mínima en inferencia determinista).

El protocolo documenta qué variable cambia en cada caso; en la comparación solo debe cambiar el checkpoint y, si aplica, el tamaño del conjunto de entrenamiento declarado como factor.

---

##### 7. Control, validez y reproducibilidad

###### 7.1. Variables constantes y variables que cambian

La validez de una comparación exige separar:

- **Constantes:** imágenes, etiquetas de referencia, preprocesamiento, vocabulario de clases, umbral de decisión, código de evaluación, hardware y versión de las bibliotecas.
- **Variables de interés:** el checkpoint evaluado (y, si cambia, el volumen de entrenamiento).

Solo así las diferencias observadas en las métricas se atribuyen a la variable de interés.

###### 7.2. Definición operacional

Cada métrica debe definirse de forma **operacional**: una fórmula exacta, sin ambigüedad, que cualquier tercero pueda aplicar y obtener el mismo número. Incluye:

- La fórmula matemática.
- La convención de casos especiales (por ejemplo, conjuntos vacíos en Jaccard).
- El umbral de decisión y su origen.
- La fuente de las etiquetas de referencia.

###### 7.3. Trazabilidad

La trazabilidad garantiza que un resultado puede ligarse a sus insumos exactos:

- Identificador y **hash criptográfico (SHA-256)** del checkpoint y del manifiesto de imágenes.
- Registro de la versión de código y de los reportes de cada ejecución.
- Archivo de resultados por ejecución con fecha, incidencias y total de imágenes procesadas.

###### 7.4. Tipos de validez

- **Validez interna:** ¿las diferencias observadas se deben al factor manipulado y no a variables ocultas? La protegen las condiciones de control y la separación de particiones.
- **Validez de constructo:** ¿la métrica mide lo que se quiere medir? La exactitud mide acierto de tipo; el Jaccard mide solapamiento de conjuntos; el macro mide desempeño global ponderado por propiedad.
- **Validez externa:** ¿hasta dónde se generaliza el resultado? Limitada al dominio de las imágenes (fotografías de catálogo) y a la procedencia de las etiquetas.

###### 7.5. Limitación de validez de las etiquetas automáticas

Cuando la referencia no es una verdad de terreno validada por humanos, sino la salida de **otras IA**, la métrica mide **concordancia con esas anotaciones**, no exactitud frente a la realidad. Esta salvedad debe declararse: no descalifica el método, pero delimita qué se puede concluir.

---

##### 8. Criterio de aceptación (requisito R11)

###### 8.1. Formulación verificable

Un requisito es evaluable solo si fija **qué magnitud**, **qué umbral** y **en qué condiciones**:

> El modelo debe alcanzar un **promedio macro ≥ 70 %** en el reconocimiento de tipo, color y estilo, medido sobre el conjunto de prueba fijo con las fórmulas y condiciones de control definidas.

###### 8.2. Regla de decisión

- **Macro ≥ 70 %** → requisito **cumplido**.
- **Macro < 70 %** → requisito **no cumplido**; procede diagnóstico por propiedad y por etiqueta.

###### 8.3. Interpretación correcta

El requisito se refiere al **agregado**. No implica que cada propiedad individual supere el 70 %, ni convierte el macro en una medida de «fiabilidad» del sistema: es un indicador de **concordancia con las etiquetas de referencia** bajo un protocolo declarado.

---

##### 9. Diagnóstico cuando el requisito no se cumple

La evaluación no termina en la cifra; la cifra orienta el diagnóstico:

1. **Desagregar el macro** en exactitud de tipo, Jaccard de color y Jaccard de estilo para localizar la propiedad que falla.
2. **Bajar a nivel de etiqueta** (precisión, recall, F1 por clase) para detectar colapso en clases concretas o en clases raras.
3. **Contrastar coincidencia exacta con Jaccard:** si la exacta es muy baja y el Jaccard alto, el modelo acierta parcialmente (sobrerreporte o subreporte de etiquetas); si ambos son bajos, el modelo no distingue la propiedad.
4. **Revisar desbalance y solapamiento** entre particiones: clases con pocos ejemplos y casi duplicados sesgan las métricas.
5. **Comparar checkpoints** para distinguir un problema de configuración de un límite del modelo.

---

##### 10. Referencias

- Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). Design Science in Information Systems Research. *MIS Quarterly*, 28(1), 75–105.
- Peffers, K., Tuunanen, T., Rothenberger, M. A., & Chatterjee, S. (2007). A Design Science Research Methodology for Information Systems Research. *Journal of Management Information Systems*, 24(3), 45–77.
- Sokolova, M., & Lapalme, G. (2009). A systematic analysis of performance measures for classification tasks. *Information Processing & Management*, 45(4), 427–437.
- Tsoumakas, G., & Katakis, I. (2007). Multi-Label Classification: An Overview. *International Journal of Data Warehousing and Mining*, 3(3), 1–13.
- Wu, X.-Z., & Zhou, Z.-H. (2017). A unified view of multi-label performance measures. *Proceedings of the 34th International Conference on Machine Learning* (ICML).
- Bishop, C. M. (2006). *Pattern Recognition and Machine Learning*. Springer.
- Howard, A., et al. (2019). Searching for MobileNetV3. *Proceedings of the IEEE/CVF International Conference on Computer Vision* (ICCV).

---


## 9. Antecedentes


### Correcciones del informe (observaciones 4, 5 y 6)

*Fuente: [`docs/antecedentes/CORRECCIONES-INFORME.md`](docs/antecedentes/CORRECCIONES-INFORME.md)*


> **Informe analítico fechado al 22-10-2026.** Conserva propuestas y mediciones históricas; la comprobación posterior está en [validación](docs/evaluacion/VALIDACION.md).

Todas las cifras de este documento se midieron el 22-10-2026 con consultas de solo lectura sobre `dataset/metadata.sqlite`, el registro `registro_entrenamiento.sqlite` y el checkpoint compartido (`mobilenetv3-small-best.pt`, época 15, ejecución `20261018-020637`). La evaluación se repite con [EVALUACION-ENTRENAMIENTO.md](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md). Lo que no se pudo medir desde este repositorio está marcado como **pendiente**.

##### Datos vigentes (22-10-2026, después de la depuración de duplicados)

| Dato | Valor |
|---|---:|
| Prendas aprobadas y aptas para entrenamiento (cada una con 1 imagen) | **14.456** |
| Entrenamiento (train) | 11.616 (80,4 %) |
| Validación (val) | 1.416 (9,8 %) |
| Prueba (test) | 1.424 (9,9 %) |
| Test con color y estilo anotados | 1.418 |
| Prendas pendientes de revisión (no se usan) | 7.412 |
| Prendas rechazadas (duplicados y descartes; no se usan) | 17.007 |
| Checkpoint evaluado | `mobilenetv3-small-best.pt`, época 15, SHA-256 `79407f55…dcb35c` |
| Dispositivo y umbral | CPU; umbral multi-etiqueta 0,5 |

| Propiedad | Aciertos | Exacta | Parcial (Jaccard) | F1 micro |
|---|---:|---:|---:|---:|
| Tipo de prenda | 1.352 / 1.424 | **94,94 %** | — | — |
| Color | 764 / 1.418 | 53,88 % | **68,42 %** | 72,80 % |
| Estilo | 674 / 1.418 | 47,53 % | **69,21 %** | 76,49 % |
| **Promedio macro** | | | **77,52 %** | |

La evaluación se repitió el 22-10-2026 después de borrar 4.039 duplicados y dio resultados idénticos (incluidas las tablas por clase) porque el test no cambió. El informe detallado está en `modelo-ia/evaluaciones/evaluacion_propiedades_test_20261022.json`.

##### 0. Cifras del informe que no coinciden con los datos

| Dónde | El informe dice | Dato verificado | Acción |
|---|---|---|---|
| 5.3 | 17,000 imágenes de entrenamiento | 14.456 imágenes elegibles: 11.616 train, 1.416 val, 1.424 test. Al entrenar el checkpoint había 15.419 (12.379 / 1.511 / 1.529), antes de depurar duplicados | Reportar ambas cifras y aclarar qué conjunto se usó |
| 5.3 | 1,400 fotografías de prueba | 1.424 (1.418 con color y estilo anotados) | Corregir |
| 5.3, Tabla 6 | 77.50 % de promedio macro | (94,94 + 68,42 + 69,21) / 3 = **77,52 %** | Corregir y usar dos decimales en toda la tabla |
| 5.1, R11 | Criterio del 70 %, "Cumplido" | Con coincidencia exacta, color 53,88 % y estilo 47,53 % están **por debajo** de 70 %. Solo el macro con Jaccard (77,52 %) lo supera | Definir en la Tabla 2 qué métrica es el criterio y presentar ambas (ver 4.4) |
| 1.3, 1.5, 5.4 | "MovileNetV3", "MovilNetV3"; frase suelta "y MobileNetV3-Small." | — | Corregir ortografía y redacción |

##### Observación 4: validación del clasificador (9/10)

###### 4.1 Dataset y procedimiento de partición

**Fuentes (14.456 imágenes elegibles).** Las tres fuentes públicas declaradas con uso comercial: Apparel Images Gallery (11.255, 77,9 %), clothing-dataset-small (2.511) y clothing-dataset (690).

**Partición.** Se asigna al importar, por imagen, con una regla determinista:

1. Si la ruta de origen contiene una carpeta `train`, `val`/`validation` o `test`, se hereda (clothing-small).
2. Si no, se usa el SHA-256: los primeros 8 caracteres hexadecimales del hash, interpretados como número, módulo 100; menos de 80 es train, menos de 90 es val y el resto es test. Esto cubre AIG y clothing-dataset.

La proporción resultante es 80,4 % / 9,8 % / 9,9 %. Cada prenda tiene una sola imagen, por lo que la partición por prenda y por imagen es la misma. Solo se usan prendas con `estado_revision = aprobado` y `apta_para_entrenamiento = 1`. El test no se usó para elegir checkpoints ni umbrales (el umbral 0,5 es fijo). Según el registro de entrenamiento, las 1.424 imágenes de test, las 11.616 de train y las 1.416 de val actuales estaban en esas mismas particiones cuando se entrenó el checkpoint; ninguna cambió de conjunto. Desde entonces se descartaron 963 imágenes del conjunto original (763 de train, 95 de val y 105 de test) al depurar duplicados.

**Distribución por clase de tipo de prenda:**

| Tipo | Train | Val | Test | Total | % del total |
|---|---:|---:|---:|---:|---:|
| blusa | 5.044 | 630 | 663 | 6.337 | 43,8 |
| camisa | 1.300 | 144 | 106 | 1.550 | 10,7 |
| vestido | 1.220 | 147 | 166 | 1.533 | 10,6 |
| pantalón | 1.176 | 144 | 131 | 1.451 | 10,0 |
| abrigo | 893 | 108 | 103 | 1.104 | 7,6 |
| chaqueta | 879 | 104 | 114 | 1.097 | 7,6 |
| short | 538 | 64 | 71 | 673 | 4,7 |
| suéter | 294 | 35 | 42 | 371 | 2,6 |
| falda | 272 | 40 | 28 | 340 | 2,4 |

Hay un desbalance marcado: blusa pesa 43,8 % y falda 2,4 %. El entrenamiento compensó con pérdida ponderada por clase (raíz cuadrada de la frecuencia inversa). Falda (28) y suéter (42) tienen pocos ejemplos de prueba, por lo que sus métricas son inestables.

###### 4.2 Calidad e independencia de las etiquetas

| Propiedad | Origen de la etiqueta | Independiente de NIM y DeepSeek |
|---|---|---|
| Tipo de prenda | Clase de la fuente pública, convertida con `sources.json`. La IA solo valida que la imagen corresponda a esa clase y descarta las que no | Sí, con un sesgo de selección: solo quedan imágenes que la IA aceptó |
| Color y estilo | Generados por NVIDIA NIM o DeepSeek | **No**: no existe una referencia humana independiente |

Procedencia de las 14.456 descripciones aprobadas:

| Proveedor | Train | Val | Test | Total |
|---|---:|---:|---:|---:|
| DeepSeek (`deepseek-flash`) | 10.865 | 1.390 | 1.240 | 13.495 (93,4 %) |
| NVIDIA NIM (varios modelos) | 751 | 26 | 184 | 961 (6,6 %) |

La proporción de NIM no es uniforme: 12,9 % del test frente a 6,5 % de train y 1,8 % de val. Debe declararse porque el test tiene una mezcla de anotadores distinta de la de entrenamiento.

**Revisión humana.** Las 14.456 descripciones figuran como `aprobado`, pero el procedimiento documentado del curador aprueba en bloque (`approve-generated`) tras revisar una muestra. El informe menciona una muestra aleatoria de 50 imágenes **sin reportar su tasa de error**. Pendiente: cuantificarla (aciertos por propiedad sobre esas 50 imágenes).

**Acuerdo entre los dos proveedores (indicador de ruido de etiquetas).** En 349 imágenes aceptadas por ambos:

| Propiedad | Coincidencia exacta | Jaccard medio |
|---|---:|---:|
| Color | 224 / 349 = 64,2 % | 75,7 % |
| Estilo | 195 / 349 = 55,9 % | 73,8 % |

Esta muestra no es representativa: incluye solo imágenes aceptadas por ambos, y los desacuerdos sobre aptitud quedan fuera. Aun así, indica que las etiquetas de color y estilo tienen un ruido propio de 25 % aproximadamente en Jaccard. El 68,4 % y el 69,2 % del modelo deben leerse como **concordancia con anotaciones generadas por IA**, no como exactitud frente a la verdad.

###### 4.3 Posible fuga entre particiones y análisis de sensibilidad

El SHA-256 no detecta fotos casi idénticas. Con la huella perceptual dHash (distancia de Hamming) se encontró que parte del test tiene un casi duplicado en train:

| Distancia dHash | Test con casi duplicado en train | Val con casi duplicado en train |
|---|---:|---:|
| 0 (idénticas) | 41 / 1.424 (2,9 %) | 36 / 1.416 |
| ≤ 2 | 77 / 1.424 (5,4 %) | 79 / 1.416 |
| ≤ 4 | 172 / 1.424 (12,1 %) | 174 / 1.416 |

Se reevaluó el mismo checkpoint excluyendo esas imágenes del test:

| Test evaluado | n | Tipo | Color exacta / Jaccard | Estilo exacta / Jaccard | **Macro** |
|---|---:|---:|---:|---:|---:|
| Completo | 1.424 | 94,94 | 53,88 / 68,42 | 47,53 / 69,21 | **77,52** |
| Sin casi duplicados (≤ 2) | 1.347 | 94,65 | 52,80 / 67,76 | 46,46 / 68,46 | **76,96** |
| Sin casi duplicados (≤ 4) | 1.252 | 94,33 | 52,25 / 67,32 | 45,35 / 67,92 | **76,52** |

El efecto es pequeño (como máximo 1 punto del macro). Es una cota conservadora: de los 77 pares con distancia ≤ 2, 76 pertenecen a grupos que un revisor marcó en la interfaz como "No son duplicadas" (el revisor consideró que las fotos eran distintas), y solo 1 no pertenece a un grupo revisado. El dHash de 64 bits es una huella gruesa, de modo que parte de esos 77 no son repeticiones reales. Tras la depuración del 22-10-2026 quedan 20 grupos pendientes de revisión manual (encadenamientos de imágenes dispares, no purgados a propósito) y 404 descartados como no duplicados.

###### 4.4 Evaluación por clase (test, 1.424 imágenes)

Resumen por propiedad. Se reportan los dos criterios para que la elección de métrica sea transparente. La coincidencia exacta es la más estricta; Jaccard da crédito parcial.

| Propiedad | n | Exacta | Parcial (Jaccard) | F1 micro |
|---|---:|---:|---:|---:|
| Tipo | 1.424 | 94,94 % | — | — |
| Color | 1.418 | 53,88 % | 68,42 % | 72,80 % |
| Estilo | 1.418 | 47,53 % | 69,21 % | 76,49 % |

**Tipo de prenda:**

| Tipo | Soporte | Precisión % | Recall % | F1 % |
|---|---:|---:|---:|---:|
| abrigo | 103 | 93,00 | 90,29 | 91,63 |
| blusa | 663 | 96,42 | 97,59 | 97,00 |
| camisa | 106 | 92,79 | 97,17 | 94,93 |
| chaqueta | 114 | 94,74 | 94,74 | 94,74 |
| falda | 28 | 89,66 | 92,86 | 91,23 |
| pantalón | 131 | 98,46 | 97,71 | 98,08 |
| short | 71 | 95,65 | 92,96 | 94,29 |
| suéter | 42 | 93,33 | 66,67 | 77,78 |
| vestido | 166 | 90,00 | 92,17 | 91,07 |

El suéter es la clase más débil (recall 66,7 %): 8 de 42 se predicen como blusa. Vestido y blusa se confunden entre sí (10 vestidos predichos como blusa).

**Color (soporte > 0):**

| Etiqueta | Soporte | Precisión % | Recall % | F1 % |
|---|---:|---:|---:|---:|
| amarillo | 96 | 88,89 | 66,67 | 76,19 |
| azul | 290 | 86,38 | 76,55 | 81,17 |
| beige | 102 | 72,58 | 44,12 | 54,88 |
| blanco | 351 | 72,15 | 77,49 | 74,73 |
| café | 52 | 75,00 | 34,62 | 47,37 |
| gris | 195 | 85,59 | 51,79 | 64,54 |
| morado | 67 | 79,17 | 56,72 | 66,09 |
| multicolor | 66 | 68,42 | 39,39 | 50,00 |
| naranja | 37 | 70,00 | 18,92 | 29,79 |
| negro | 428 | 80,53 | 78,27 | 79,38 |
| rojo | 173 | 87,10 | 78,03 | 82,32 |
| rosa | 143 | 72,12 | 52,45 | 60,73 |
| verde | 169 | 89,17 | 63,31 | 74,05 |

**Estilo (soporte > 0):**

| Etiqueta | Soporte | Precisión % | Recall % | F1 % |
|---|---:|---:|---:|---:|
| casual | 1.103 | 88,66 | 91,48 | 90,05 |
| elegante | 583 | 70,41 | 84,91 | 76,98 |
| deportivo | 157 | 91,67 | 63,06 | 74,72 |
| verano | 156 | 73,61 | 33,97 | 46,49 |
| fiesta | 103 | 70,83 | 33,01 | 45,03 |
| bohemio | 86 | 65,12 | 32,56 | 43,41 |
| formal | 161 | 54,74 | 32,30 | 40,62 |
| invierno | 41 | 71,43 | 24,39 | 36,36 |
| infantil | 13 | 75,00 | 23,08 | 35,29 |
| entretiempo | 40 | 60,00 | 15,00 | 24,00 |

En color y estilo la precisión supera con claridad al recall: el modelo es conservador con las etiquetas poco frecuentes. Colores como naranja (recall 18,9 %) y estilos como entretiempo (15,0 %) casi no se detectan.

###### 4.5 Texto propuesto para la sección 5.3

> El clasificador se entrenó con imágenes de tres fuentes públicas de uso comercial (Apparel Images Gallery, clothing-dataset y clothing-dataset-small). Tras la depuración de duplicados quedaron 14.456 imágenes aprobadas: 11.616 para entrenamiento, 1.416 para validación y 1.424 para prueba (80,4 %, 9,8 % y 9,9 %). La partición se asignó al importar cada imagen: se heredó la carpeta de origen cuando existía y, en los demás casos, se derivó de forma determinista del hash SHA-256 de la imagen. Cada prenda tiene una sola fotografía, por lo que no hay fuga por prendas repetidas. El conjunto está desbalanceado (blusa 43,8 %; falda 2,4 %); el entrenamiento aplicó pérdida ponderada por clase.
>
> La etiqueta de tipo proviene de la clase de la fuente pública; NVIDIA NIM y DeepSeek solo validaron que la imagen correspondiera a esa clase. Las etiquetas de color y estilo fueron generadas por NVIDIA NIM (6,6 %) y DeepSeek (93,4 %), por lo que no son independientes de dichos servicios y la evaluación mide la concordancia del modelo con anotaciones asistidas por IA, no con una referencia humana. En 349 imágenes anotadas por ambos proveedores, su coincidencia fue de 75,7 % (color) y 73,8 % (estilo) en Jaccard, lo que indica el ruido de las etiquetas. [Agregar aquí la tasa de error de la revisión manual de 50 imágenes.]
>
> El 5,4 % de las imágenes de prueba tiene un casi duplicado en entrenamiento (dHash ≤ 2). Al excluirlas, el promedio macro baja de 77,52 % a 76,96 %. En la prueba completa (1.424 imágenes) se obtuvo una exactitud de tipo de 94,94 %; para color y estilo, coincidencia exacta de 53,88 % y 47,53 %, y coincidencia parcial (Jaccard) de 68,42 % y 69,21 %. El promedio macro de las tres propiedades es 77,52 %. La Tabla 6 y las Tablas 6a a 6c presentan los resultados por clase.

###### 4.6 Diseño de la prueba de validación

**Objetivo.** Medir qué porcentaje de las propiedades de una prenda (tipo, color y estilo) reconoce correctamente el clasificador en fotografías que no usó para entrenar.

**Población y muestra.** Prendas aprobadas, aptas y con archivo presente. El conjunto de prueba contiene 1.424 imágenes (una por prenda), asignadas antes de entrenar y sin uso en la elección del modelo; en 1.418 hay color y estilo anotados y solo esas cuentan para esas dos propiedades. No se muestrea: se evalúa el test completo.

**Instrumento.** `utilidades-entrenamiento/evaluate_properties.py`: carga el checkpoint en modo inferencia (CPU), calcula las predicciones y guarda un JSON con fecha, época, SHA-256 de la base de datos y métricas por clase. No actualiza pesos.

**Regla de predicción.** Tipo: la clase de mayor probabilidad (*softmax*). Color y estilo: se incluyen las etiquetas cuya probabilidad (*sigmoide*) es ≥ 0,5.

**Cálculos.** Con $T$ = imágenes evaluadas, $P_i$ = conjunto predicho y $R_i$ = conjunto real de la imagen $i$:

- Tipo: $\text{Exactitud} = \dfrac{\text{tipos correctos}}{T} = \dfrac{1.352}{1.424} = 94{,}94\,\%$
- Coincidencia exacta (color o estilo): $\dfrac{\#\{i : P_i = R_i\}}{T}$; color $764/1.418 = 53{,}88\,\%$; estilo $674/1.418 = 47{,}53\,\%$.
- Coincidencia parcial (Jaccard): $J = \dfrac{1}{T}\sum_i \dfrac{|P_i \cap R_i|}{|P_i \cup R_i|}$, con $J_i = 1$ si ambos conjuntos están vacíos. Color $68{,}42\,\%$; estilo $69{,}21\,\%$.
- Promedio macro: $\dfrac{94{,}94 + 68{,}42 + 69{,}21}{3} = 77{,}52\,\%$ (cada propiedad pesa un tercio).
- Precisión, *recall* y F1 por etiqueta: $P=\dfrac{TP}{TP+FP}$, $R=\dfrac{TP}{TP+FN}$, $F_1=\dfrac{2PR}{P+R}$; el F1 micro suma TP, FP y FN de todas las etiquetas.

**Ejemplo de Jaccard.** Si la etiqueta real de color es {azul} y el modelo predice {azul, blanco}, la intersección es 1 y la unión es 2, así que $J_i = 0{,}5$ (la exacta daría 0). Si predice {azul} da 1; si predice {rojo}, 0.

**Criterio de aceptación propuesto (R11).** El promedio macro (Jaccard) debe ser ≥ 70 %. Resultado: 77,52 %, cumple. Como criterio complementario y más estricto, ninguna propiedad debe quedar por debajo de 70 % con coincidencia exacta; no cumple en color (53,88 %) ni estilo (47,53 %). Fijar y justificar en la Tabla 2 cuál de los dos es el criterio oficial.

**Reproducibilidad.** Misma semilla de partición (derivada del hash de cada imagen), umbral fijo 0,5, checkpoint identificado por SHA-256 y base de datos identificada por SHA-256 en cada informe.

**Comando.**

```bash
cd utilidades-entrenamiento
docker compose run --rm --no-deps --entrypoint python train \
  /app/evaluate_properties.py \
  --checkpoint /app/modelos-compartidos/mobilenetv3-small-best.pt \
  --split test --device cpu \
  --output /app/modelo-ia/evaluaciones/evaluacion_propiedades_test.json
```

**Amenazas a la validez (a declarar).**

1. Las etiquetas de color y estilo vienen de IA, no de una referencia humana independiente (4.2).
2. Desbalance de clases y pocos ejemplos de test en falda (28) y suéter (42).
3. Posible solapamiento por fotos casi idénticas entre train y test, con impacto acotado (4.3).
4. Distinta mezcla de anotadores en test (12,9 % NIM) que en train (6,5 %).
5. Las imágenes proceden de catálogos públicos; el rendimiento con fotos reales de una persona vistiendo la prenda no se midió.
6. El test pertenece a la misma distribución que el entrenamiento (mismas tres fuentes).

##### Observación 5: alcance de MobileNetV3-Small (9/10)

###### Hechos verificables

| Aspecto | Dónde se hizo | Evidencia |
|---|---|---|
| Entrenamiento | Equipo independiente de la nube: Docker con PyTorch 2.5.1 sobre CPU (Intel i7-8750H, 15 GiB RAM, Ubuntu 24.04). La RTX 2060 de ese equipo no estaba disponible (CUDA no detectada) | Registro de ejecuciones en `modelo-ia/runs/` y salida de `train status` |
| Evaluación | El mismo equipo, en CPU, con `evaluate_properties.py` | JSON en `modelo-ia/evaluaciones/` |
| Curación del dataset | Mismo equipo (dashboard `127.0.0.1:8787`), con llamadas remotas a NVIDIA NIM y DeepSeek | Tabla `analisis_imagen` |
| Ejecución en OpenStack/Kubernetes | **Sin evidencia en el repositorio**: no hay despliegue del clasificador en `k8s-vton`, ni en una VM de OpenStack, ni métricas de Prometheus asociadas | — |

El equipo medido se identifica como `osanode-node4`, pero su hardware no coincide con el de `osa-node4` en la Tabla 9 (Ryzen 5 3550H, 16 GB). **Pendiente:** confirmar si es uno de los cinco nodos de la nube. Si no lo es, el informe debe decir expresamente que el entrenamiento se hizo fuera de la infraestructura evaluada.

###### Texto propuesto (reemplaza o ajusta 1.3, 1.5, 2.2 y 5.4)

**1.3, última frase del primer párrafo.** El caso de estudio es la prueba virtual de prendas de vestir mediante el modelo FASHN VTON v1.5, desplegado sobre la nube privada; como componente complementario se desarrolló y evaluó, fuera de la nube, un clasificador MobileNetV3-Small de propiedades de prendas.

**1.5, alcance (inciso i).** (i) El entrenamiento y la evaluación de un clasificador basado en MobileNetV3-Small para reconocer el tipo, el color y el estilo de prendas de vestir, realizados en un equipo independiente de la nube privada.

**1.5, fuera del alcance.** Quedan fuera del alcance la adaptación (*fine-tuning*) del modelo VTON, la evaluación de su calidad visual, la medición del beneficio empresarial de la prueba virtual, la alta disponibilidad y el escalamiento a gran número de servidores, la documentación del entrenamiento de VTON y la ejecución del entrenamiento o de la inferencia de MobileNetV3-Small sobre la infraestructura OpenStack/Kubernetes.

**2.2, objetivo específico 4.** Integrar el modelo FASHN VTON v1.5 como caso de estudio sobre la nube privada, desplegándolo como un prototipo funcional compuesto por un servicio de inferencia expuesto mediante API, una interfaz web con cola de solicitudes y el registro de los metadatos de cada ejecución sobre la GPU dedicada; y desarrollar y evaluar, de forma independiente, un clasificador visual de prendas (MobileNetV3-Small), documentando su preparación de datos, entrenamiento y evaluación.

**5.4, Tabla 7, fila OE4.** Evidencia: `vton-api` y VTON Studio operativos sobre `k8s-vton`; clasificador MobileNetV3-Small entrenado y evaluado fuera de la nube (sección 5.3).

**5.1, Tabla 3, R11.** Requisito: obtener un resultado de al menos 70 % en el reconocimiento de propiedades de las prendas. Evidencia: evaluación sobre 1.424 imágenes de prueba, promedio macro 77,52 % (tipo 94,94 %, color 68,42 %, estilo 69,21 %, estos dos con Jaccard). Con coincidencia exacta, color (53,88 %) y estilo (47,53 %) no alcanzan 70 %. Estado: **Parcial**, o "Cumplido" si la Tabla 2 define de antemano el macro con Jaccard como criterio.

**Si el equipo prefiere integrarlo a la nube.** El repositorio incluye una API de inferencia en CPU (`utilidades-entrenamiento/compose.cpu-api.yaml`, endpoint `POST /v1/predict`). Para afirmar que corre en OpenStack habría que desplegarla en una VM o pod de la nube, repetir la evaluación allí y registrar latencia y consumo de CPU/RAM con Prometheus. Solo entonces se puede conservar la redacción original del objetivo 4.

##### Observación 6: concurrencia (9/10)

###### Situación actual

El informe declara R8 como "Cumplido" porque existe una cola y se observaron 3 solicitudes en cola con 126 s en total. Eso solo demuestra procesamiento serializado. Dividir 126 s entre 3 da unos 42 s por solicitud (coherente con los 40–50 s del flujo web), pero es un promedio **inferido**, no hay tiempos individuales, rendimiento (*throughput*) ni tasa de error. Esta prueba se ejecuta en la nube del equipo, por lo que **los resultados deben medirse allí**; la tabla siguiente queda sin valores a propósito.

###### Protocolo propuesto

- **Variable:** usuarios simultáneos N = 1, 2 y 3.
- **Carga fija:** mismas imágenes de persona y prenda, 30 pasos, semilla 42, categoría `tops`.
- **Calentamiento:** una ejecución previa descartada, para excluir la carga del modelo en frío.
- **Repeticiones:** 5 por cada N, fijadas antes de medir.
- **Doble nivel:** (a) directo a `vton-api`, que mide el servicio sin la cola web; (b) a través de VTON Studio, que mide el flujo completo y el tiempo de espera en cola.
- **Registrar por solicitud:** hora de envío, hora de respuesta, código HTTP y tiempo de espera en cola (panel `/admin`).
- **Registrar por prueba:** duración total, solicitudes completadas, VRAM pico y utilización de GPU (DCGM), reinicios de pods.

###### Criterios de aceptación (definirlos antes de medir)

| Criterio | Umbral propuesto |
|---|---|
| Tasa de éxito | 100 % de respuestas HTTP 200; ningún 5xx ni tiempo de espera agotado |
| Atención serializada | La última de N solicitudes termina en ≤ 1,25 × N × T1 (T1 = latencia con N = 1) |
| Rendimiento | ≥ 0,8 × el rendimiento con N = 1 |
| VRAM | Pico ≤ 90 % de 12.288 MiB (11.059 MiB) |
| Estabilidad | Cero reinicios de pods durante la prueba |

###### Plantilla de resultados (completar con mediciones)

| N | Rep. | Latencia por solicitud (s) | Espera en cola (s) | Duración total (s) | Rendimiento (sol/min) | Errores | VRAM pico (MiB) |
|---|---:|---|---|---:|---:|---:|---:|
| 1 | 5 | por medir | por medir | por medir | por medir | por medir | por medir |
| 2 | 5 | por medir | por medir | por medir | por medir | por medir | por medir |
| 3 | 5 | por medir | por medir | por medir | por medir | por medir | por medir |

Hipótesis de referencia si la atención es estrictamente serial y T1 ≈ 42 s: tiempos de finalización de 42 s (N = 1), 42 y 84 s (N = 2) y 42, 84 y 126 s (N = 3). Es una expectativa derivada, no un resultado.

###### Script de medición (ejecutar desde un equipo con acceso al servicio)

Los nombres de los campos de `POST /v1/tryon` no están en este repositorio; cópialos de `/docs` antes de ejecutar.

```python
import os, time, statistics
from concurrent.futures import ThreadPoolExecutor
import requests

URL = os.environ["VTON_URL"]            # p. ej. http://localhost:8080/v1/tryon
KEY = os.environ["VTON_API_KEY"]
PERSONA, PRENDA = "persona.jpg", "prenda.jpg"

def una_solicitud(_):
    inicio = time.perf_counter()
    with open(PERSONA, "rb") as p, open(PRENDA, "rb") as g:
        r = requests.post(URL, headers={"X-API-Key": KEY}, timeout=600,
                          files={"person_image": p, "garment_image": g},   # ajustar a /docs
                          data={"category": "tops", "num_timesteps": 30})  # ajustar a /docs
    return r.status_code, time.perf_counter() - inicio

una_solicitud(0)  # calentamiento descartado
for n in (1, 2, 3):
    for rep in range(5):
        inicio = time.perf_counter()
        with ThreadPoolExecutor(n) as pool:
            res = list(pool.map(una_solicitud, range(n)))
        total = time.perf_counter() - inicio
        tiempos = sorted(t for _, t in res)
        errores = sum(1 for c, _ in res if c != 200)
        print(n, rep, [round(t, 1) for t in tiempos], round(total, 1),
              round(n / total * 60, 2), errores)
```

###### Texto propuesto para R8 mientras no existan las mediciones

R8, soportar solicitudes concurrentes. Evidencia: una solicitud a la vez por diseño; la cola absorbe la espera (3 solicitudes en cola completadas en 126 s, equivalente a unos 42 s por solicitud). Estado: **Parcial**; falta caracterizar latencia individual, rendimiento y tasa de error con 1, 2 y 3 usuarios (protocolo en este documento). Al completar la prueba, cambiar a "Cumplido" si se satisfacen los criterios de aceptación.

##### Pendientes que solo el equipo puede resolver

1. Cuantificar el resultado de la revisión manual de 50 imágenes (por propiedad).
2. Confirmar si el equipo de entrenamiento pertenece a la nube y decidir entre mantener el clasificador fuera de ella o desplegarlo en OpenStack.
3. Medir la concurrencia con el protocolo anterior y completar la Tabla 5.
4. Decidir y fijar en la Tabla 2 la métrica del criterio R11 (exacta o Jaccard) y justificar la elección.
5. Opcional: revisar a mano los 273 grupos de duplicados pendientes y repetir el entrenamiento y la evaluación con el dataset depurado.

##### Cómo reproducir las cifras

- Evaluación por propiedad: comando en [EVALUACION-ENTRENAMIENTO.md](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md), con `--checkpoint /app/modelos-compartidos/mobilenetv3-small-best.pt`.
- Distribución por clase, procedencia de etiquetas, acuerdo NIM/DeepSeek y casi duplicados: consultas de solo lectura sobre `prenda`, `prenda_imagen`, `valor_propiedad_prenda`, `descripcion_prenda`, `analisis_imagen` e `imagen_huella`. No hay un script versionado para estos cálculos.
- La base de datos cambia cuando se importan, rechazan o depuran imágenes; cada JSON de evaluación guarda el SHA-256 de la base usada.

---


### Plan de entrenamiento (MobileNetV3-Small, V2)

*Fuente: [`docs/antecedentes/PLAN-ENTRENAMIENTO.md`](docs/antecedentes/PLAN-ENTRENAMIENTO.md)*


> **Plan histórico.** Las mediciones y problemas descritos corresponden a la planificación inicial; no representan el estado actual. Consulta el [README vigente](README.md) y la [validación del 23-10-2026](docs/evaluacion/VALIDACION.md).

Documento de planificación. No ejecuta nada. Basado en `README.md`, `RESUMEN-METODO-ENTRENAMIENTO.md`, `utilidades-entrenamiento/README.md`, `documentacion_dataset/README.md` y el estado real de este equipo (`osanode-node4`).

##### 1. Hardware detectado

| Recurso | Valor |
|---|---|
| CPU | Intel Core i7-8750H, 6 núcleos / 12 hilos |
| RAM | 15 GiB (≈11 GiB disponibles), swap 4 GiB |
| GPU | NVIDIA GeForce RTX 2060 Mobile (TU106M, 6 GB VRAM, Turing, CC 7.5) + Intel UHD 630 (integrada, no sirve para CUDA) |
| Disco | 98 GB totales, 77 GB libres |
| Docker | 29.1.3 + Compose 2.40.3 (paquetes `docker.io`, `docker-compose-v2`) |
| Driver NVIDIA | **No instalado** (no existe `nvidia-smi` ni `/proc/driver/nvidia`) |
| NVIDIA Container Toolkit | **No instalado** |
| Python en host | Sin `torch` (correcto: todo irá en contenedor) |

Consecuencia: hoy solo funciona el perfil CPU. La RTX 2060 (6 GB) es suficiente para MobileNetV3-Small a 224 px con batch 32-64, muy por encima de los 2-4 GB que asume el README; hay que instalar driver y toolkit para aprovecharla.

##### 2. Estado de los datos (`dataset/metadata.sqlite`)

- 24 177 prendas, 24 177 imágenes (1 imagen por prenda).
- Aprobadas: train 11 496, val 1 398, test 1 407 (**14 301 utilizables**). Pendientes: 1 118. Rechazadas: 8 758.
- Carpetas: faldas, pantalones, shorts, vestido, abrigos, blusas, camisas, chaquetas, sueteres (8 276 imágenes en blusas, desbalance notable).
- Existe respaldo `metadata.respaldo-20261017-1628.sqlite`.

Consecuencia: el dataset es suficiente para entrenar tipo de prenda; color y estilo dependen de cuántas aprobadas tengan etiqueta (verificar, ver fase 0).

##### 3. Arreglo del error de Docker (permisos del socket)

Causa: el usuario `ubuntu` está en el grupo `docker` en `/etc/group`, pero la sesión actual se abrió antes y no lo tiene (`id` no lista `docker`). Verificado: `sg docker -c "docker ps"` funciona.

Solución (una de las dos, no requiere sudo):

```bash
newgrp docker          # abre una shell con el grupo; sirve en esa terminal
# o cerrar sesión y volver a entrar / reiniciar la sesión de VS Code
```

Después, `docker compose up` / `docker compose run --rm train status` funcionan sin `sudo`. No usar `chmod 666 /var/run/docker.sock` ni `sudo docker` como solución permanente.

Nota: `docker compose up` sin servicio arranca `train` con el comando por defecto (entrena). Para solo construir/consultar usar `docker compose build` y `docker compose run --rm train status`.

##### 4. Problemas detectados en la infraestructura actual (a corregir al implementar)

1. `docker-compose.yaml`: `build.network: none` y `Dockerfile` con `pip install --no-index` fallarán, porque la imagen base `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` no incluye `Pillow` ni `PyYAML` y no hay red en el build. Cambiar a build con red (o vendorizar wheels en `wheels/` y usar `--find-links`).
2. La imagen base no está descargada localmente (~3-4 GB); el primer `build` la bajará.
3. Los pesos preentrenados de MobileNetV3-Small se descargan en tiempo de ejecución a `modelo-ia/cache`. Para portabilidad/offline, pre-descargarlos y guardarlos en el volumen (o hornearlos en la imagen).
4. `num_workers: 0` y `batch_size: 2` en `configs/default.yaml` están pensados para 2 GB de VRAM; con 6 GB y 12 hilos son un cuello de botella.
5. Dataset montado `:ro` con rutas relativas: correcto y portable; mantenerlo.
6. Sin `shm_size`: con `num_workers > 0` PyTorch necesita `shm_size` (p. ej. `2g`) o `ipc: host`.
7. Hay un directorio `modelo-general-destilacion/docker-compose.yaml/` (carpeta con ese nombre) junto a `compose.yml`; revisar para evitar confusión.
8. El dashboard de curación está en ejecución y consume RAM/CPU; considerar detenerlo durante el entrenamiento.

##### 5. Plan por fases

###### Fase 0 – Preparación del equipo
1. Activar el grupo `docker` en la sesión (sección 3).
2. Instalar driver NVIDIA propietario recomendado (`ubuntu-drivers devices` → `sudo ubuntu-drivers install`) y reiniciar. Debe ser compatible con CUDA 12.4 (driver ≥ 550).
3. Instalar `nvidia-container-toolkit`, ejecutar `sudo nvidia-ctk runtime configure --runtime=docker` y reiniciar Docker.
4. Validar: `docker run --rm --gpus all pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime nvidia-smi`.
5. Liberar recursos: detener el contenedor `modelo-general-destilacion-dashboard` si no se usa.

###### Fase 1 – Auditoría de datos (sin entrenar)
1. Contar por clase de `tipo_prenda` en train/val/test solo con `estado_revision='aprobado'`.
2. Contar cuántas aprobadas tienen etiquetas de `color` y `estilo`; decidir si se entrenan esas cabezas o solo tipo en la primera corrida.
3. Verificar que todas las rutas de `prenda_imagen` existan y abran con Pillow.
4. Revisar duplicados entre splits (fuga de datos) con el pipeline de duplicados existente.
5. Decidir manejo de desbalance (blusas 8 276 vs. ~1 300-1 500 del resto): `pos_weight`/pesos por clase o muestreo balanceado.
6. Confirmar licencias/permisos de las fuentes antes de cualquier publicación del modelo.

###### Fase 2 – Contenerización portable
Objetivo: todo el entrenamiento se mueve a otro equipo copiando carpeta + `docker compose up`.
1. Un solo `Dockerfile` con dependencias fijadas (`torch/torchvision` de la imagen base, `Pillow`, `PyYAML`, más `scikit-learn`/`numpy` si se agregan métricas).
2. Perfiles Compose: `train` (CPU) y `train-gpu` (GPU); variables en `.env` (`TRAINING_UID`, `TRAINING_GID`, `CUDA_VISIBLE_DEVICES`, imagen, tamaño, batch).
3. Volúmenes: `../dataset` solo lectura; `./modelo-ia` para runs/caché; nada fuera de la carpeta del proyecto, sin rutas absolutas del host.
4. Empaquetado de migración: `docker save` de la imagen o build reproducible desde Dockerfile; copiar `dataset/` y `metadata.sqlite` (con hash SHA-256 para verificar integridad).
5. Script `status` ampliado: versión de PyTorch, GPU, VRAM, hash de la base y conteos por split.
6. Healthcheck de entorno antes de entrenar (GPU visible, SQLite legible, imágenes accesibles).

###### Fase 3 – Prueba de humo
1. `status` en CPU y en GPU.
2. 1 época con un subconjunto (p. ej. 500 imágenes) para validar el pipeline, la pérdida y la escritura de checkpoints.
3. Medir tiempo por iteración, uso de VRAM (`nvidia-smi`) y RAM.

###### Fase 4 – Entrenamiento por etapas (GPU RTX 2060, 6 GB)

| Experimento | Configuración inicial | Objetivo |
|---|---|---|
| E1 línea base | base congelada, 160 px, batch 64, lr 1e-3, 10-15 épocas, `num_workers` 6-8, AMP (mixed precision) | validar cabezas, obtener base de comparación |
| E2 resolución | base congelada, 224 px, batch 32-64 | medir ganancia por resolución |
| E3 ajuste fino | descongelar último bloque, lr 1e-4 (cabezas 1e-3), 224 px | mejora esperada en tipo/color |
| E4 mejor config + semillas | repetir mejor config con 3 semillas | estimar varianza |

Reglas comunes: semilla fija, aumento de datos ligero solo en train (flip horizontal, recorte aleatorio, variación de brillo; evitar cambios de tono que alteren el color), `ReduceLROnPlateau` o coseno, early stopping por métrica de val, guardado de `best.pt` y `last.pt`, registro de configuración, hash de dataset, GPU, VRAM máxima y duración en cada run (`modelo-ia/runs/<fecha>-<exp>/`).

Estimación de memoria: MobileNetV3-Small a 224 px con batch 64 y AMP cabe holgadamente en 6 GB; escalar batch hasta ≈70 % de VRAM. Validar empíricamente.

###### Fase 5 – Evaluación
1. Selección de hiperparámetros y umbrales de color/estilo solo en `val`.
2. Medir **una sola vez** en `test` con el mejor modelo.
3. Métricas: accuracy y matriz de confusión por tipo; precision/recall/F1 por clase para color y estilo; errores más frecuentes (faldas/shorts, camisas/blusas).
4. Prueba de inferencia multi-vista (`predict.py`) y de tiempo en CPU.
5. Guardar informe en `modelo-ia/runs/<run>/metrics.json` y resumen en Markdown.

###### Fase 6 – Cierre y migración
1. Congelar versión: copia de SQLite, listado de hashes, `configs/` usado, imagen Docker etiquetada (`modelo-reconocimiento-entrenamiento:v2-<fecha>`).
2. Exportar el mejor checkpoint (opcional ONNX/TorchScript) para integración con OpenStack/Kubernetes.
3. Verificar en un equipo limpio: `git clone`/copia + instalar Docker (+ NVIDIA toolkit si hay GPU) + `docker compose --profile gpu run --rm train-gpu status`.

##### 6. Riesgos

- Calidad de etiquetas generadas por IA (mayor riesgo): muestrear aprobadas y medir error.
- Sesgo de fuentes y fondos distintos al uso real.
- Desbalance de clases (blusas dominan).
- Driver/toolkit incompatibles: fallback CPU (más lento; 12 hilos pero sin aceleración).
- Etiquetas de color/estilo ausentes tratadas como "no anotadas" (ya implementado): puede dejar cabezas con pocas muestras.
- Espacio en disco: 77 GB libres bastan; cada run ocupa pocos MB.

##### 7. Criterios de aceptación

- `docker compose --profile gpu run --rm train-gpu status` muestra RTX 2060 y CUDA disponible.
- Entrenamiento reproducible (misma semilla y dataset ⇒ métricas equivalentes).
- Métricas por tipo, color y estilo registradas sobre `test` no usado en entrenamiento.
- Todo el stack se levanta en otro equipo solo con Docker, el dataset y este directorio.

##### 8. Decisiones pendientes

1. ¿Entrenar primero solo `tipo_prenda` o las tres cabezas?
2. ¿Aprobar más de las 1 118 pendientes antes de congelar el dataset?
3. ¿Se acepta instalar driver NVIDIA y toolkit (requieren `sudo` y reinicio)?
4. ¿Resolución objetivo final (160 vs 224 px)?

---


### Reconocimiento de prendas

*Fuente: [`docs/antecedentes/README-v1.md`](docs/antecedentes/README-v1.md)*

> **VERSIÓN 1 — DESCARTADA.** Este plan se conserva únicamente como respaldo histórico. Se descartó para dar paso a la versión 2; seguir las instrucciones de [`README.md`](README.md).
>
> Para la documentación vigente del dataset, consulta el [índice](dataset/README.md), la [guía de metadatos](documentacion_dataset/README.md) y el [esquema SQLite](documentacion_dataset/schema.sql).


Módulo pequeño de visión por computadora para complementar el proyecto de OpenStack y Kubernetes. El objetivo es entrenar un modelo que, a partir de **una o varias fotos de la misma prenda**, devuelva:

- Tipo: camisa, pantalón, vestido, falda, etc.
- Color o colores básicos: negro, blanco, rojo, azul, rosa, etc.
- Estilo: casual, elegante, fiesta, verano, deportivo, etc.

La primera versión se ejecutará con **Docker Compose** en una laptop. No necesita Kubernetes, base de datos, API, interfaz web ni un modelo generativo grande para entrenar. La integración con el proyecto principal se deja para después.

##### Decisión técnica para el MVP

Usar un modelo de clasificación de imágenes pequeño con pesos preentrenados y ajustar sus últimas capas con nuestras imágenes:

1. **MobileNetV3-Small**: primera opción por tamaño y costo de ejecución.
2. **SqueezeNet 1.1**: alternativa pequeña si MobileNet no cabe o resulta lento en una GPU concreta.
3. **EfficientNet-B0 o ResNet18**: alternativas para comparar si hay memoria suficiente.

El modelo tendrá salidas separadas:

- **Tipo de prenda:** una categoría principal.
- **Color:** uno o varios colores.
- **Estilo:** cero o varios estilos.

Las etiquetas de estilo dependen de criterios humanos. Se deben definir ejemplos para cada una y etiquetar consistentemente. No mezclar conceptos: si «fiesta rosa» significa una prenda rosa para fiesta, guardar `rosa` como color y `fiesta` como estilo, no como una sola categoría.

###### Una o varias fotos

Cada foto debe mostrar la misma prenda. El modelo predice cada foto por separado y combina las probabilidades para generar un único resultado para esa prenda. Se recomienda empezar promediando las probabilidades de las fotos.

Este MVP **no identifica ni separa varias prendas dentro de una sola foto**. Para eso haría falta añadir detección de objetos o recortar las prendas antes de enviarlas al clasificador.

##### Hardware y límites

- Las cuatro GPU están en laptops distintas: **no se combinan ni se suman sus VRAM**.
- Con **2 GB de VRAM**, empezar con MobileNetV3-Small, imágenes de 128–160 píxeles, batch 1 y el extractor de características congelado; entrenar primero solo la capa final. Si cabe, probar después a descongelar el último bloque.
- Con **4 GB**, probar imágenes de 160–224 píxeles y batch pequeño (1–4), midiendo uso real de memoria.
- GPUs GTX y RTX pueden tener capacidades diferentes. Docker necesita que el driver NVIDIA de cada laptop sea compatible con la versión de CUDA/PyTorch de la imagen.
- Si una GPU o driver no es compatible, ejecutar entrenamiento por CPU como alternativa funcional, aunque será más lento.
- Los 100–200 GB libres en SSD son suficientes para empezar con un dataset acotado y guardar varios experimentos. No descargar datasets grandes hasta confirmar las licencias y el espacio requerido.

Estos valores son **puntos de partida**, no garantías de memoria o velocidad. Verificar cada equipo con una prueba corta antes del entrenamiento completo.

##### Estructura mínima del dataset

```text
data/
├── images/
│   ├── garment-0001/
│   │   ├── front.jpg
│   │   └── back.jpg
│   └── garment-0002/
│       └── front.jpg
├── labels.csv
└── README.md
```

Una carpeta representa una prenda física; puede contener una o varias vistas de esa misma prenda. `labels.csv` tiene una fila por foto:

```csv
garment_id,image_path,split,garment_type,colors,styles
garment-0001,images/garment-0001/front.jpg,train,vestido,negro|rosa,elegante|fiesta
garment-0001,images/garment-0001/back.jpg,train,vestido,negro|rosa,elegante|fiesta
garment-0002,images/garment-0002/front.jpg,val,camisa,azul,casual|verano
```

Reglas:

- `garment_id` identifica la prenda, no la foto.
- `image_path` es relativo a `data/`.
- `split` es `train`, `val` o `test`.
- `garment_type` usa una categoría aprobada y escrita siempre igual.
- `colors` y `styles` son listas separadas por `|`. Usar `unknown` si no se puede determinar; no dejar que cada persona invente etiquetas.
- Mantener una lista breve y documentada de categorías, colores y estilos. Empezar con pocas clases y ampliarlas cuando haya ejemplos suficientes.
- Las vistas de una prenda deben quedarse juntas en el mismo split. **No poner una foto de la misma prenda en train y otra en test.**
- Para evaluar, separar `test` antes de probar configuraciones y no usarlo para entrenar.
- Guardar de dónde vienen las imágenes y confirmar permiso de uso. Evitar fotografías borrosas, duplicadas o donde la prenda no sea visible.
- Etiquetar el estilo según una guía acordada. No deducir ocasión o estilo como verdad objetiva solo por el color.

No hay un número universal de imágenes que garantice buenos resultados. Primero crear un piloto con varias categorías y ejemplos diversos, medir errores y luego recoger más imágenes para las clases con pocos ejemplos.

##### Flujo de trabajo

1. Definir la lista inicial de tipos, colores y estilos.
2. Reunir imágenes que podamos usar y agrupar las vistas por prenda.
3. Etiquetar `labels.csv` siguiendo las reglas anteriores.
4. Separar train/val/test por `garment_id`.
5. Ejecutar un entrenamiento pequeño en una laptop y comprobar que cabe en su GPU.
6. Repetir en las demás laptops, cambiando una configuración por experimento y guardando los resultados por separado.
7. Comparar resultados sobre el mismo conjunto de test; escoger el modelo con menos errores relevantes, no solo el que entrenó más rápido.
8. Guardar el modelo entrenado y preparar posteriormente su integración con el proyecto OpenStack/Kubernetes.

##### Uso de las cuatro laptops

Ejecutar **un experimento independiente por laptop**. Todas usan la misma versión del código y una copia idéntica de `data/`:

- Laptop 1: MobileNetV3-Small con configuración base.
- Laptop 2: mismo modelo con otra resolución o tasa de aprendizaje.
- Laptop 3: comparar SqueezeNet 1.1.
- Laptop 4: validar, probar otro ajuste o ejecutar el mejor modelo.

Registrar para cada ejecución el modelo, configuración, GPU, VRAM máxima, duración, métricas y versión del dataset. Copiar el resultado de cada equipo a una carpeta distinta; no sobrescribir modelos ni mezclar pesos automáticamente.

No se recomienda entrenamiento distribuido entre las laptops: añade configuración de red y sincronización, y no resuelve la limitación de VRAM de una tarjeta individual.

##### Docker Compose

La estructura mínima que se implementará para ejecutar el entrenamiento:

```text
.
├── Dockerfile
├── compose.yaml
├── train.py
├── predict.py
├── requirements.txt
├── configs/
│   └── default.yaml
├── data/
└── models/
```

El contenedor montará `data/` y `models/` desde la laptop: las imágenes y los modelos no se guardan dentro de la imagen Docker. Compose debe permitir seleccionar entrenamiento por GPU o CPU, y la configuración debe dejar cambiar modelo, tamaño de imagen y batch sin modificar el código.

Ejemplo de reserva de **una GPU local** en `compose.yaml`:

```yaml
services:
  train:
    build: .
    command: ["python", "train.py", "--config", "configs/default.yaml"]
    volumes:
      - ./data:/app/data:ro
      - ./models:/app/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Comandos previstos una vez creados `Dockerfile`, `compose.yaml` y `train.py`:

```bash
# Comprobar que Docker ve la GPU en esta laptop
docker compose run --rm train nvidia-smi

# Entrenar
docker compose run --rm train
```

Para usar GPU dentro del contenedor, instalar Docker Engine/Compose y NVIDIA Container Toolkit compatibles con el driver del equipo. Si `nvidia-smi` no funciona dentro del contenedor, corregir primero el acceso de Docker a la GPU o ejecutar el perfil CPU. La configuración anterior es la **meta de implementación**, no un compose ejecutable hasta que existan los archivos indicados.

##### Alternativas sencillas

| Opción | Uso | Decisión |
|---|---|---|
| MobileNetV3-Small preentrenado | Clasificar tipo, colores y estilos en una prenda | **Recomendada para comenzar** |
| SqueezeNet 1.1 preentrenado | Probar una arquitectura aún más pequeña | Alternativa para GPU con poca memoria |
| EfficientNet-B0 o ResNet18 | Comparar si MobileNet cabe y se desea otra referencia | Opcional |
| YOLO u otro detector | Encontrar varias prendas y recortarlas en una misma foto | No incluir en el MVP; requiere cajas anotadas y más recursos |
| CLIP | Probar etiquetas con texto sin ajuste supervisado completo | Comparación opcional; comprobar requisitos y licencias |
| Modelo grande de lenguaje/visión | Generar descripciones libres | No recomendado para este alcance y VRAM |

##### Criterio de éxito del MVP

- Docker Compose puede iniciar el entrenamiento en cada laptop de forma independiente.
- El proceso puede usar GPU cuando driver y tarjeta sean compatibles, y dispone de alternativa CPU.
- El modelo recibe una o varias fotos de la misma prenda y devuelve tipo, colores y estilos con sus puntuaciones.
- Se mide accuracy por tipo y precision/recall/F1 para colores y estilos.
- Se registran los errores por clase y se conserva un test que no se utilizó para entrenar.

##### Preguntas abiertas

1. ¿Cuáles son los modelos exactos de GPU de las cuatro laptops? Ejecutar `nvidia-smi` en cada una y compartir `Name` y `Memory-Total`.
2. ¿Qué tipos de prenda entran en la primera versión? Propongo empezar con camisa, pantalón, vestido, falda y chaqueta.
3. ¿Qué colores básicos y qué estilos quieren incluir? ¿«Fiesta rosa» significa color rosa más estilo fiesta?
4. ¿Las fotos muestran la prenda aislada, extendida, puesta en una persona o una combinación?
5. ¿Cuántas imágenes tienen y son propias o cuentan con permiso para entrenar?

##### Estado

Este README define el alcance reducido y la estructura propuesta. Aún deben crearse el dataset, el script de entrenamiento y los archivos Docker indicados en la sección Docker Compose. El primer paso es responder las preguntas abiertas e inventariar las GPU.

---


### Resumen del método de entrenamiento

*Fuente: [`docs/antecedentes/RESUMEN-METODO-ENTRENAMIENTO.md`](docs/antecedentes/RESUMEN-METODO-ENTRENAMIENTO.md)*


> **Referencia metodológica con contexto histórico.** Ya existe un modelo entrenado y evaluado. Las cifras iniciales, recomendaciones y descripciones futuras del cuerpo no son un parte de estado vigente. Consulta el [resumen actualizado](<docs/resumen/RESUMEN-PROYECTO.md>) y la [evaluación](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md).

##### 1. Objetivo y estado actual

El proyecto entrena un clasificador visual que, a partir de una o varias fotografías de **una misma prenda**, predice tres grupos de propiedades: **tipo de prenda**, **color** y **estilo**. El alcance son nueve categorías: abrigo, blusa, camisa, chaqueta, falda, pantalón, short, suéter y vestido (camisas y camisetas se unifican en `camisa`). La temporada se anota en el dataset como metadato, pero **no es una salida del modelo** del MVP.

El modelo de producción del MVP es **MobileNetV3-Small**. Las IA generativas (NVIDIA NIM y DeepSeek) solo participan en la **curación del dataset**; no se despliegan ni son un profesor de destilación. El método implementado es **aprendizaje por transferencia supervisado** con etiquetas asistidas por IA; el estado aprobado no acredita revisión humana individual. La destilación queda como experimento posterior.

Estado: el dataset supera las 5.900 prendas importadas, pero las muestras creadas por el curador quedan `pendiente` y con `apta_para_entrenamiento = 0` hasta que una persona las apruebe. Ese era el estado inicial; actualmente existe un checkpoint compartido con evaluación registrada.

##### 2. Flujo completo, del dataset al modelo

| Etapa | Qué ocurre | Responsable |
|---|---|---|
| 1. Importación | Se leen las fuentes locales, se mapea cada clase original a una clase canónica y se omiten las clases fuera del catálogo | Curador |
| 2. Anotación asistida | NIM y/o DeepSeek proponen aptitud, descripción, colores, estilos y temporadas | IA (solo propuesta) |
| 3. Revisión humana | Se aprueba o descarta cada prenda y se corrigen propiedades | Persona |
| 4. Particiones | Cada prenda recibe `train`, `val` o `test` | Script |
| 5. Entrenamiento | Transfer learning sobre `train`, comparación en `val` | `train.py` |
| 6. Evaluación final | Métricas en `test`, revisión de errores y decisión de aceptar el checkpoint | Persona |
| 7. Predicción | Inferencia con una o varias vistas de la prenda | `predict.py` |

##### 3. Preparación y anotación de los datos

**Fuentes.** clothing-dataset-small, clothing-dataset y Apparel Images Gallery (AIG). Se conservan el origen y la etiqueta original; las carpetas fuera del catálogo (por ejemplo `Hoodies`) se omiten. Fashion-MNIST se reserva como benchmark aparte.

**Control de calidad al importar.** Se valida formato y tamaño (las imágenes de más de 200.000 bytes no se envían ni se reducen) y se calcula el SHA-256. La deduplicación por hash evita repetir imágenes y análisis, incluso con dos proveedores en paralelo. Los originales se montan en solo lectura y las muestras válidas se copian a `dataset/` con sus metadatos en SQLite.

**Anotación con IA.** Cada proveedor corre en su propio lote, con control de detención independiente y hasta **15.000 imágenes nuevas** por lote (no analizadas aún).

- **NVIDIA NIM:** modelo principal `nvidia/nemotron-3.5-super-vl-120b-a12b`. Si falla, cambia automáticamente a `meta/llama-3.2-11b-vision-instruct` después a `meta/llama-3.2-90b-vision-instruct` y finalmente a `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`. Un HTTP 500 o 429 se reintenta una vez; un modelo solo se excluye tras 4 fallos seguidos, o de inmediato con HTTP 401, 403 o 404.
- **DeepSeek:** `deepseek-flash`. Si falla, la imagen se reintenta con NIM.
- **Llamadas por etapas.** Para reducir JSON inválido, NIM resuelve cada imagen en cuatro llamadas cortas (colores, estilos, temporadas y validación) que luego se unen. El parser extrae el primer objeto JSON de la respuesta aunque venga con texto alrededor.
- **Vocabulario controlado.** Los colores son una lista cerrada. Los estilos y las temporadas pueden ampliarse con valores nuevos devueltos por las IA, que entran al catálogo.

**Las respuestas de IA son propuestas, no etiquetas.** Se guardan con proveedor, modelo y estado de revisión. Una persona debe confirmar la categoría, comprobar que la prenda sea visible y aprobar colores y estilos antes de habilitar la muestra. Las respuestas inválidas no se guardan como análisis.

##### 4. Particiones y prevención de fuga de datos

La partición se asigna **por prenda**, no por fotografía: todas las vistas de una prenda quedan en el mismo conjunto. Esto evita que el modelo vea en `train` la misma prenda que luego se evalúa.

- `train` ajusta los pesos.
- `val` compara configuraciones, elige el mejor checkpoint y ajusta umbrales.
- `test` se usa **una sola vez** al final y nunca para elegir checkpoints o hiperparámetros.

Proporción recomendada: 70 % / 15 % / 15 %, estratificada por tipo de prenda. Mínimos sugeridos antes del primer entrenamiento serio: unas 100 prendas aprobadas por categoría y al menos 10 por categoría en `val` y en `test`. Las clases con muy pocas muestras deben esperar a tener más datos antes de interpretarse sus métricas.

##### 5. Arquitectura del modelo

Se usa **MobileNetV3-Small preentrenada en ImageNet**: ligera, adecuada para CPU y portátil. Una base compartida extrae las características visuales y tres cabezas de clasificación las usan:

1. **Tipo de prenda:** una clase entre nueve (softmax). Pérdida: entropía cruzada.
2. **Color:** multi-etiqueta (sigmoide), porque una prenda puede tener varios colores. Pérdida: entropía cruzada binaria.
3. **Estilo:** multi-etiqueta (sigmoide), con cero o varios estilos. Pérdida: entropía cruzada binaria.

La pérdida total es la suma de las tres. Las prendas sin colores o estilos anotados **no aportan** a esa cabeza: la ausencia de anotación no se trata como etiqueta negativa.

##### 6. Cómo se entrenará

**Fase A, transfer learning con base congelada (implementada).** Se congela el extractor preentrenado y solo se ajustan las tres cabezas. Es rápido, funciona con datasets pequeños y reduce el riesgo de sobreajuste.

**Fase B, ajuste fino (experimento opcional).** Si la fase A se estanca, se activa `unfreeze_last_block: true` para descongelar solo el último bloque, con una tasa de aprendizaje menor (por ejemplo 1e-4) y un checkpoint y métricas separados. Solo se conserva si mejora en `val`.

Configuración inicial, en `utilidades-entrenamiento/configs/default.yaml`:

| Parámetro | Valor |
|---|---|
| Tamaño de imagen | 160 × 160 |
| Batch | 2 (se puede subir si hay memoria) |
| Épocas | 15 |
| Tasa de aprendizaje | 0,001 |
| Semilla | 42 |
| Umbral multi-etiqueta | 0,5 |
| Preprocesado | redimensionado y normalización de ImageNet |

Son valores de partida para ajustar con experimentos, no garantías de rendimiento. En cada época se calcula la pérdida de validación y se guarda `best.pt` cuando mejora; `config`, métricas y checkpoints quedan en `utilidades-entrenamiento/modelo-ia/runs/<ejecución>/`.

**Mejoras planificadas, aún no implementadas.** Conviene añadirlas por separado y medir cada una en `val`:

- Aumento de datos en `train`: volteo horizontal, rotaciones pequeñas, recortes y variación leve de brillo. No se usan cambios de tono que alteren el color real de la prenda.
- Pesos por clase o muestreo balanceado, si el reparto entre tipos queda desigual.
- Resolución de 224 × 224 y batch mayor, cuando haya GPU.
- Umbrales por color y estilo, ajustados en `val` en lugar del 0,5 fijo.

##### 7. Evaluación y criterios de aceptación

- **Tipo:** exactitud global, precisión, recall y F1 por clase, y matriz de confusión. Se revisan las confusiones esperables, como blusa–camisa o chaqueta–abrigo.
- **Color y estilo:** precisión, recall y F1 por etiqueta, y su promedio macro. La exactitud global engaña en problemas multi-etiqueta.
- **Revisión cualitativa:** se miran manualmente los errores de mayor confianza para detectar etiquetas mal revisadas.
- **Prueba final:** se ejecuta `test` solo con el checkpoint ya elegido. Si se retoca el modelo después de verlo, hay que renovar la partición `test`.

Un checkpoint se acepta si ninguna categoría queda con un rendimiento muy inferior al resto y el resultado en `test` es coherente con `val`. Los umbrales numéricos deben fijarse antes de entrenar, según el uso previsto del MVP.

##### 8. Predicción

`predict.py` carga el checkpoint y devuelve el tipo y los colores y estilos cuya probabilidad supera el umbral. Con varias fotos de una misma prenda se predice cada vista y se **promedian las probabilidades**. El modelo no detecta ni separa varias prendas dentro de una imagen, así que cada foto debe mostrar una sola prenda.

##### 9. Herramientas y ejecución

- **Python 3.12, PyTorch y torchvision** para dataset, entrenamiento, evaluación y predicción.
- **SQLite** (`dataset/metadata.sqlite`) guarda prendas, imágenes, particiones, etiquetas aprobadas, catálogos y la trazabilidad de la curación.
- **Docker Compose** da ejecución reproducible. Existe un perfil de CPU y otro de GPU NVIDIA con CUDA; una GPU AMD requeriría validar una pila ROCm.
- Las claves de API viven en `.env` y no forman parte del dataset ni del modelo.

```bash
cd utilidades-entrenamiento
docker compose build
docker compose run --rm train status
docker compose run --rm train train --epochs 1 --device cpu   # prueba rápida
docker compose run --rm train                                   # entrenamiento normal
docker compose run --rm train predict --checkpoint /app/modelo-ia/runs/<ejecucion>/best.pt <imagen>
```

##### 10. Riesgos y siguientes pasos

1. **Calidad de etiquetas:** es el mayor riesgo. Las propuestas de IA pueden equivocarse, por eso la revisión humana es obligatoria y conviene muestrear las aprobaciones para medir el error.
2. **Sesgo de las fuentes:** las imágenes públicas pueden tener fondos y poses distintos de los de uso real. Hay que añadir fotos propias y verificar licencias y permisos antes de usar o publicar el modelo.
3. **Desbalance:** revisar el conteo por tipo, color y estilo antes de entrenar.
4. **Orden de trabajo:** terminar el lote de anotación, revisar y aprobar, fijar particiones, entrenar la fase A, evaluar y solo entonces decidir sobre aumento de datos, ajuste fino o destilación.

Más detalle en el [README del proyecto](README.md), la [guía de entrenamiento](utilidades-entrenamiento/README.md), la [guía de metadatos](documentacion_dataset/README.md) y el [pipeline de curación](utilidades-entrenamiento/modelo-general-destilacion/README.md).

---


## 10. Inventario de archivos


### Índice de documentación

*Fuente: [`docs/INDICE.md`](docs/INDICE.md)*


**Revisión: 2 de noviembre de 2026.** Inventario completo de los Markdown del repositorio, reorganizado por carpetas temáticas dentro de `docs/`. Este índice es el punto de entrada: todos los documentos están enlazados aquí y las rutas son las definitivas.

Lectura sugerida: [README de entrada](README.md) → [resumen del proyecto](docs/resumen/RESUMEN-PROYECTO.md) → [validación](docs/evaluacion/VALIDACION.md) → [instalación Docker](docs/instalacion/INSTALACION-DOCKER.md) → [referencia de endpoints](docs/operacion/API.md).

##### Organización de la documentación

```
docs/
├── INDICE.md                  ← este índice
├── validar_documentacion.py   ← comprobador de enlaces y cobertura
├── instalacion/               ← Docker, nativa, manual DOCX y generador
├── operacion/                 ← API, endpoints y prueba DSR de la API
├── evaluacion/                ← métricas, evidencias, validación y planes de auditoría
├── teoria/                    ← teoría del entrenamiento y del método de evaluación
├── antecedentes/              ← planes y versiones históricas (contexto, no estado)
├── resumen/                   ← resumen ejecutivo del proyecto
└── datos-graficos/            ← CSV/JSON y figuras de los entrenamientos
```

Fuera de `docs/` se conservan los README temáticos de cada módulo (dataset, utilidades de entrenamiento, tests) porque documentan el código que acompañan.

##### Entrada y resumen

| Documento | Propósito |
|---|---|
| [Reconocimiento de prendas — V2](README.md) | Portada del repositorio: interfaces, arranque, flujo y estado comprobado. |
| [Resumen del proyecto](docs/resumen/RESUMEN-PROYECTO.md) | Resumen ejecutivo de unas cuatro páginas, apto para impresión. |
| [Índice de documentación](docs/INDICE.md) | Este documento: mapa completo de la documentación. |

##### Instalación

| Documento | Propósito |
|---|---|
| [Instalación del sistema completo (Docker)](docs/instalacion/INSTALACION-DOCKER.md) | Levantar interfaces, API, pruebas, entrenamiento y respaldos con el Compose unificado. |
| [Instalación nativa del modelo y su API](docs/instalacion/INSTALACION-NATIVA.md) | Instalación directa con Python, contrato de una imagen y verificación sin contenedores. |
| [Manual Word APA 7](docs/instalacion/Instalacion_nativa_API_prendas_APA7.docx) | Versión editable DOCX de la instalación nativa, generada desde la fuente anterior. |
| [Generador del manual DOCX](docs/instalacion/generar_manual_docx.py) | Script que sincroniza el Word con `INSTALACION-NATIVA.md` (requiere `python-docx`). |

##### Operación: API y pruebas

| Documento | Propósito |
|---|---|
| [Referencia de endpoints locales](docs/operacion/API.md) | Contratos HTTP de los paneles, la API CPU y la API de pruebas. |
| [Diseño de prueba DSR — API de descripción de prendas](docs/operacion/DSR-PRUEBA-API.md) | Prueba de una página basada en Design Science Research. |
| [README-TEST — Ejecutar la prueba](docs/operacion/README-TEST.md) | Guía rápida para correr la prueba con la API. |
| [README-PRUEBA — Cómo se hizo la prueba](docs/operacion/README-PRUEBA.md) | Detalle de la ejecución y los resultados de la prueba. |

##### Evaluación y evidencias

| Documento | Propósito |
|---|---|
| [Evaluación del clasificador (MobileNetV3-Small)](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md) | Resultados registrados y limitaciones. |
| [Validación de documentación e implementación](docs/evaluacion/VALIDACION.md) | Comprobaciones del 23-10-2026 y pendientes. |
| [Evidencias de integridad (SHA-256)](docs/evaluacion/EVIDENCIAS-INTEGRIDAD-SHA256.md) | Hashes completos de checkpoints, manifest y dataset para reproducibilidad. |
| [Registro DSR: errores y correcciones](docs/evaluacion/DSR-ERRORES-Y-CORRECCIONES.md) | Errores E1/E2, diagnóstico DSR, correcciones y verificación. |
| [Registro de entrenamiento 20261029-022656](docs/evaluacion/ENTRENAMIENTO-20261029-022656.md) | Configuración, evolución de validación, evaluación en test y decisión de continuidad. |
| [Plan de correcciones — Auditoría Anexo G](docs/evaluacion/PLAN-CORRECCIONES-AUDITORIA-ANEXO-G.md) | Plan para atender las 20 observaciones y generar los datos necesarios. |
| [Resumen de los últimos 3 entrenamientos (DOCX)](docs/evaluacion/Resumen_Ultimos_3_Entrenamientos.docx) | Documento Word con el resumen comparativo de los tres entrenamientos. |
| [Datos para gráficos del entrenamiento](docs/datos-graficos/README.md) | CSV/JSON con métricas por época y resultados de test de los tres entrenamientos. |

##### Teoría y método

| Documento | Propósito |
|---|---|
| [Teoría del entrenamiento — resumen completo (≈10 páginas)](docs/teoria/TEORIA-ENTRENAMIENTO-COMPLETO.md) | Fundamentos, MobileNetV3, transferencia, pérdidas, optimización y métricas. |
| [Terminología y teoría del entrenamiento](docs/teoria/TEORIA-ENTRENAMIENTO.md) | Referencia conceptual y glosario rápido. |
| [Teoría y conceptos del método de evaluación (DSRM)](docs/teoria/TEORIA-METODO-EVALUACION.md) | Matriz de confusión, exactitud, precisión/recall/F1, Jaccard, macro, control y validez. |

##### Antecedentes

Documentos históricos conservados como contexto. Sus cifras **no** representan el estado vigente.

| Documento | Propósito |
|---|---|
| [Correcciones del informe (observaciones 4, 5 y 6)](docs/antecedentes/CORRECCIONES-INFORME.md) | Análisis y propuestas del informe, fechados al 22-10-2026. |
| [Plan de entrenamiento (MobileNetV3-Small, V2)](docs/antecedentes/PLAN-ENTRENAMIENTO.md) | Plan histórico inicial. |
| [Reconocimiento de prendas — V1](docs/antecedentes/README-v1.md) | Versión histórica descartada. |
| [Resumen del método de entrenamiento](docs/antecedentes/RESUMEN-METODO-ENTRENAMIENTO.md) | Método con contexto histórico; estado vigente en el resumen nuevo. |

##### Dataset y taxonomía

| Documento | Propósito |
|---|---|
| [Dataset de prendas](dataset/README.md) | Guía de clasificación y estructura general. |
| [Documentación del dataset](documentacion_dataset/README.md) | Esquema SQLite, procedencia y gestión de metadatos. |
| [Prendas de la parte inferior](dataset/inferior/README.md) | Categorías de la parte inferior. |
| [Falda](dataset/inferior/faldas/README.md) · [Pantalón](dataset/inferior/pantalones/README.md) · [Short](dataset/inferior/shorts/README.md) | Clases de la parte inferior. |
| [Prendas de cuerpo completo](dataset/inferior_superior/README.md) · [Vestido](dataset/inferior_superior/vestido/README.md) | Clases de cuerpo completo. |
| [Prendas de la parte superior](dataset/superior/README.md) | Categorías de la parte superior. |
| [Abrigo](dataset/superior/abrigos/README.md) · [Blusa](dataset/superior/blusas/README.md) · [Camisa](dataset/superior/camisas/README.md) · [Chaqueta](dataset/superior/chaquetas/README.md) · [Suéter](dataset/superior/sueteres/README.md) | Clases de la parte superior. |
| [Conjunto portable de prueba](tests/imagenes-test/README.md) | 1.424 imágenes del split test con manifest para la API de pruebas. |

##### Utilidades de entrenamiento y curación

| Documento | Propósito |
|---|---|
| [Utilidades de entrenamiento](utilidades-entrenamiento/README.md) | Guía del módulo: entrenar, continuar checkpoints y desplegar inferencia. |
| [Inicio rápido](utilidades-entrenamiento/INICIO-RAPIDO.md) | Comandos mínimos para arrancar el entrenamiento por terminal. |
| [Checkpoint compartido](utilidades-entrenamiento/modelos-compartidos/README.md) | Ubicación y uso del checkpoint `mobilenetv3-small-best.pt`. |
| [Curación y anotación de datasets de moda](utilidades-entrenamiento/modelo-general-destilacion/README.md) | Panel de dataset, proveedores de anotación y flujo de curación. |
| [Plan de pruebas del pipeline de curación](utilidades-entrenamiento/modelo-general-destilacion/PLAN-PRUEBAS.md) | Pruebas del pipeline de curación. |
| [Dudas y decisiones antes de procesar datos](utilidades-entrenamiento/modelo-general-destilacion/dudas.md) | Preguntas abiertas y decisiones previas al procesamiento. |
| [Extensión Chrome: descargar imagen de producto](utilidades-entrenamiento/scraping-plugin-chrome/folder-destino/README.md) | Utilidad auxiliar de captura de imágenes. |

##### Archivos técnicos relacionados

- [Esquema SQLite](documentacion_dataset/schema.sql) y [creación de estructura](documentacion_dataset/crear_estructura.sh).
- [Compose unificado (dataset + entrenamiento + API CPU + API de pruebas)](docker-compose.yaml) y [Compose de entrenamiento por terminal](utilidades-entrenamiento/docker-compose.yaml).
- [Configuración de entrenamiento por defecto](utilidades-entrenamiento/configs/default.yaml) y [desde cero](utilidades-entrenamiento/configs/desde-cero.yaml).
- [Fuentes de datos](utilidades-entrenamiento/modelo-general-destilacion/sources.json).
- [Validador documental](docs/validar_documentacion.py): ejecutar `python3 docs/validar_documentacion.py` desde la raíz. Comprueba enlaces locales, anclas y cobertura del índice, sin red ni escrituras.

##### Mantenimiento

Al añadir un Markdown, enlazarlo en la tabla de su categoría y especificar si es guía vigente, resultado fechado, referencia conceptual o antecedente. Actualizar cifras con fecha y origen; no presentar planificación como medición ni aprobación masiva como auditoría humana. Actualizar la referencia de API cuando cambien los handlers.

---

