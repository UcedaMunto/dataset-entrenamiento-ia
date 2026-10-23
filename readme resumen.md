# Resumen del proyecto de reconocimiento de prendas

**Versión 2 · Revisión: 23 de octubre de 2026 · Lectura aproximada: cuatro páginas.**
Documento dividido en cuatro bloques con saltos sugeridos para impresión; la paginación final depende del visor. [Índice documental](docs/INDICE.md) · [Validación](docs/VALIDACION.md).

## Página 1 — Propósito, arquitectura y operación

El proyecto implementa un sistema de visión artificial para reconocer el tipo, los colores y los estilos de una prenda a partir de fotografías. Su flujo comprende la preparación del dataset, la anotación asistida, la aprobación de muestras, el entrenamiento supervisado, la evaluación y la inferencia. Funciona con Docker Compose y utiliza SQLite para metadatos; no necesita un servidor de base de datos ni Kubernetes para operar localmente.

Las dos interfaces tienen responsabilidades complementarias:

| Dirección | Responsabilidad | Servicio |
|---|---|---|
| `http://127.0.0.1:8787/` | Construir y curar el dataset; ver galería y resolver duplicados | `dashboard` |
| `http://127.0.0.1:8090/` | Gestionar entrenamiento, consultar métricas y probar checkpoints | `monitor` |
| `http://127.0.0.1:8081/docs` | Consultar y probar el contrato de inferencia CPU independiente | `inference-api` |

El panel de dataset está en `utilidades-entrenamiento/modelo-general-destilacion/`. El de entrenamiento está en `utilidades-entrenamiento/`. Se comunican mediante el dataset montado en Docker: el curador escribe imágenes y SQLite, y el entrenador los lee en solo lectura. Los pesos y resultados se guardan por separado en `modelo-ia/`; el modelo recomendado se conserva en `modelos-compartidos/`.

Para iniciar el monitor CPU desde la raíz:

```bash
docker compose -f utilidades-entrenamiento/docker-compose.yaml build train
docker compose -f utilidades-entrenamiento/docker-compose.yaml --profile monitor up -d monitor
```

Para iniciar curación, desde su carpeta, preparar `.env` a partir de `.env.example` si aún no existe, configurar los proveedores y ejecutar `docker compose -f compose.yml up -d --build dashboard`. Las claves se mantienen locales. El dashboard usa red del host y escucha en localhost; el monitor publica el puerto 8090 también en localhost. En una máquina remota se accede con un túnel SSH.

Los servicios `train` y `train-gpu` permiten entrenar por terminal. Los perfiles `monitor` y `monitor-gpu` habilitan el panel con CPU o acceso a una GPU local. Se utiliza una GPU por equipo: las memorias de laptops distintas no se suman. CPU es una alternativa funcional, cuyo tiempo de entrenamiento depende del hardware y del dataset. La API CPU independiente se levanta con `compose.cpu-api.yaml` y requiere indicar la ruta absoluta al checkpoint mediante `MODEL_CHECKPOINT`.

El resultado buscado es un clasificador reproducible y pequeño, con artefactos identificables y métricas explícitas. La integración con una plataforma OpenStack/Kubernetes es una etapa posterior; no forma parte del despliegue Compose actual.

<div style="page-break-after: always;"></div>

## Página 2 — Dataset, anotación y control de calidad

Las fotografías se organizan en `dataset/` por zona corporal, tipo y código de prenda. Ejemplo: `superior/camisas/CAMISA-1/frente.jpg`. Las rutas registradas son relativas al dataset, lo que permite trasladarlo entre equipos. Una prenda puede tener varias vistas, y todas deben conservar el mismo split para evitar contaminación entre entrenamiento y prueba.

El catálogo contempla nueve tipos: abrigo, blusa, camisa, chaqueta, falda, pantalón, short, suéter y vestido. Camisas y camisetas se unifican como `camisa`, conservando la etiqueta de origen para trazabilidad. Las temporadas se guardan como metadatos, pero no se predicen en las tres salidas actuales del modelo.

`dataset/metadata.sqlite` es la fuente de verdad de las relaciones. El esquema base tiene siete tablas: prendas, imágenes, catálogo de propiedades, valores de propiedades, descripciones generadas, análisis cacheados y configuración del pipeline. El módulo de duplicados añade tres tablas auxiliares; SQLite puede incluir además `sqlite_sequence`. Las imágenes y las bases locales no se distribuyen mediante Git.

Las fuentes se definen en `sources.json` y se leen desde `datos-crudos/`, montado en solo lectura. El curador verifica mapeo de clases, formato, tamaño y SHA-256. No incorpora clases fuera del mapeo; omite imágenes de más de 200.000 bytes. El hash evita importar otra vez el mismo archivo. Los análisis válidos se cachean considerando imagen, categoría, proveedor/modelo y prompt.

NVIDIA NIM y DeepSeek proponen descripciones y atributos. NIM divide el análisis en colores, estilos, temporadas y validación/descripción; los mecanismos de respaldo pueden generar más solicitudes por imagen. Los errores y respuestas inválidas se distinguen de los descartes válidos. Las claves, los modelos y los endpoints se configuran localmente; su disponibilidad remota no se comprobó en esta revisión.

El panel permite lotes de hasta **15.000 imágenes nuevas por proveedor**, con procesos y detención separados. Los colores usan vocabulario controlado; estilos y temporadas pueden ampliar el catálogo. La importación crea prendas pendientes y no aptas para entrenar. La aprobación debe confirmar etiquetas y procedencia. Existe `approve-generated`, que aprueba masivamente prendas pendientes con descripción: su ejecución no acredita revisión humana individual.

Para casi duplicados se usa dHash y distancia de Hamming, con umbral predeterminado 2. La interfaz permite conservar una imagen y rechazar las demás sin borrar archivos, descartar agrupaciones erróneas y deshacer resoluciones compatibles. `purge-duplicates` sí puede borrar archivos de rechazados; conserva filas para bloquear reimportaciones. Antes de una limpieza destructiva se necesita un respaldo recuperable.

La lectura del 23 de octubre encontró **14.456 prendas aprobadas y aptas**, distribuidas en 11.616 train, 1.416 val y 1.424 test; además, 12.134 pendientes y 17.007 rechazadas. Las 14.456 imágenes aprobadas existen. Los conteos son una instantánea y deben actualizarse si cambia el dataset.

<div style="page-break-after: always;"></div>

## Página 3 — Modelo, entrenamiento y artefactos

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

## Página 4 — Evaluación, inferencia y situación real

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

SQLite pasó `quick_check`, pero `foreign_key_check` encontró **15.066 referencias huérfanas** de miembros a grupos de duplicados. Hay **9.939 rutas de imagen sin archivo**, todas de prendas rechazadas, compatibles con el flujo de purga documentado; no se verificó individualmente su causa histórica. No faltan archivos del subconjunto aprobado. Estas observaciones deben resolverse o justificarse antes de declarar íntegra toda la base; no equivalen a que fallen las dos interfaces.

La documentación queda organizada mediante un README de entrada, un índice completo, guías operativas, referencia de endpoints, evaluación y registro de validación. Los planes anteriores se conservan como antecedentes. Los próximos pasos son sanear las relaciones de duplicados con respaldo, establecer una referencia humana independiente, controlar similitudes entre splits y medir el rendimiento en el entorno final. [Consultar evidencia y verificaciones](docs/VALIDACION.md).
