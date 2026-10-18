# Reconocimiento de prendas — Versión 2

> **Versión vigente:** 2. La versión anterior se conserva como respaldo descartado en [`README-v1.md`](./README-v1.md).

## ¿Dónde se ve la interfaz?

Hay dos paneles web, para tareas distintas:

- **Entrenamiento e inferencia:** el monitor abre en `http://127.0.0.1:8090`; **Probar modelo en CPU** ejecuta inferencia de un checkpoint existente. Para servir inferencia desde una VM con CPU, hay una API separada en el puerto local `8081` que recibe foto de prenda y foto de persona usándola, y devuelve predicciones por foto más una descripción combinada. El servicio no monta el dataset ni inicia entrenamiento. Sigue los comandos y límites de despliegue en [`utilidades-entrenamiento/README.md`](./utilidades-entrenamiento/README.md#api-de-inferencia-en-una-vm-con-cpu). El servicio `train` por sí solo no publica un puerto ni tiene interfaz.
- **Checkpoint compartido:** el modelo recomendado está versionado en [`utilidades-entrenamiento/modelos-compartidos/`](./utilidades-entrenamiento/modelos-compartidos/README.md). Los compañeros lo descargan con `git pull`; no se suben los otros checkpoints ni la caché local.
- **Curación de datos:** desde `utilidades-entrenamiento/modelo-general-destilacion/`, ejecuta `docker compose up -d dashboard` y abre `http://127.0.0.1:8787`. Este panel gestiona importación y anotación de imágenes; no es el monitor de entrenamiento. Consulta su [guía](./utilidades-entrenamiento/modelo-general-destilacion/README.md).

Las direcciones `127.0.0.1` funcionan en la máquina donde corre Docker. Si Docker corre en un servidor remoto, crea un túnel SSH (por ejemplo, `ssh -L 8090:127.0.0.1:8090 usuario@servidor`) y luego abre `http://127.0.0.1:8090` en tu computadora.

Módulo pequeño de visión por computadora para complementar el proyecto de OpenStack y Kubernetes. El objetivo es entrenar un modelo que, a partir de **una o varias fotos de la misma prenda**, devuelva:

- Tipo: camisa, pantalón, vestido, falda, etc.
- Color o colores básicos: negro, blanco, rojo, azul, rosa, etc.
- Estilo: casual, elegante, fiesta, verano, deportivo, etc.

El entrenamiento del MVP se ejecutará con **Docker Compose** en una laptop. No necesita Kubernetes, un servidor de base de datos, una API ni una interfaz web para entrenar. Usa SQLite local únicamente para los metadatos del dataset. La integración con el proyecto principal se deja para después. La preparación de datos incluye un pipeline separado para auditar e importar fuentes y, si se autoriza, pedir anotaciones a proveedores de visión; esas anotaciones son sugerencias pendientes de revisión y no son el modelo que se entrena.

## Decisión técnica para el MVP

Usar **MobileNetV3-Small**, con pesos preentrenados, como arquitectura única del MVP. Ajustar el modelo con imágenes propias etiquetadas. No cambiar de arquitectura durante esta versión.

La red tendrá una base MobileNetV3-Small compartida y tres salidas:

- **Tipo de prenda:** clasificación de una categoría (por ejemplo, camisa o vestido).
- **Color:** clasificación multi-etiqueta (una o varias opciones).
- **Estilo:** clasificación multi-etiqueta (cero o varios estilos).

Para la primera prueba, cargar los pesos preentrenados, congelar la base y entrenar las tres capas de salida. Si la GPU tiene memoria suficiente, probar después descongelar solo el último bloque de MobileNetV3-Small. Mantener el mismo test para ambas pruebas y guardar cada resultado por separado.

Las etiquetas de estilo dependen de criterios humanos. Se deben definir ejemplos para cada una y etiquetar consistentemente. No mezclar conceptos: si «fiesta rosa» significa una prenda rosa para fiesta, guardar `rosa` como color y `fiesta` como estilo, no como una sola categoría.

### Una o varias fotos

Cada foto debe mostrar la misma prenda. MobileNetV3-Small predice cada foto por separado; para entregar un resultado por prenda, promediar las probabilidades de sus fotos. Los tipos se asignan con la puntuación más alta y color/estilo con umbrales que se fijarán usando el conjunto de validación.

Este MVP **no identifica ni separa varias prendas dentro de una sola foto**. Para eso haría falta añadir detección de objetos o recortar las prendas antes de enviarlas al clasificador.

## Hardware y límites

- Las cuatro GPU están en laptops distintas: **no se combinan ni se suman sus VRAM**.
- Con **2 GB de VRAM**, empezar con MobileNetV3-Small, imágenes de 128–160 píxeles, batch 1 y el extractor de características congelado; entrenar primero solo la capa final. Si cabe, probar después a descongelar el último bloque.
- Con **4 GB**, probar imágenes de 160–224 píxeles y batch pequeño (1–4), midiendo uso real de memoria.
- GPUs GTX y RTX pueden tener capacidades diferentes. Docker necesita que el driver NVIDIA de cada laptop sea compatible con la versión de CUDA/PyTorch de la imagen.
- Si una GPU o driver no es compatible, ejecutar entrenamiento por CPU como alternativa funcional, aunque será más lento.
- Los 100–200 GB libres en SSD son suficientes para empezar con un dataset acotado y guardar varios experimentos. No descargar datasets grandes hasta confirmar las licencias y el espacio requerido.

Estos valores son **puntos de partida**, no garantías de memoria o velocidad. Verificar cada equipo con una prueba corta antes del entrenamiento completo.

## Estructura del dataset y SQLite

Las imágenes se guardan en carpetas por zona, tipo y prenda física. Las etiquetas y relaciones se guardan en una sola base SQLite, `dataset/metadata.sqlite`; no se mantiene un JSON por prenda ni un CSV como fuente de verdad.

```text
dataset/
├── metadata.sqlite
├── superior/camisas/CAMISA-1/frente.jpg
├── superior/camisas/CAMISA-1/espalda.jpg
├── inferior/faldas/FALDA-1/frente.jpg
└── inferior_superior/vestido/VESTIDO-1/frente.jpg
```

La clase canónica `camisa` agrupa las prendas superiores con abertura frontal y las camisetas; ambas se guardan en `superior/camisas/` y usan la misma etiqueta. En la ingesta, `camisa` y `camiseta` se normalizan a esa clase, y se conserva la etiqueta original en SQLite para trazabilidad. Los tipos de prenda del catálogo inicial son abrigo, blusa, camisa, chaqueta, falda, pantalón, short, suéter y vestido.

El esquema usa siete tablas:

- `prenda`: código, ruta de categoría, split y estado de revisión; una fila por prenda.
- `prenda_imagen`: relación de una prenda con una o más rutas relativas a `dataset/`.
- `catalogo_propiedad`: tipos de propiedad permitidos, como `tipo_prenda`, `color`, `estilo` y atributos.
- `valor_propiedad_prenda`: cada valor asociado a la prenda y a su propiedad. Color y estilo pueden ocupar varias filas por prenda.
- `descripcion_prenda`: descripciones y sugerencias de IA con proveedor/modelo y revisión pendiente.
- `analisis_imagen`: resultado cacheado por huella para reutilizar aceptaciones y descartes del proveedor sin repetir inferencias.
- `pipeline_config`: prompt editable y configuración funcional del proceso.

Así se representa `prenda X → imágenes 1, 2, 3` y `prenda X → valor → tipo de propiedad`. La [guía del dataset](./documentacion_dataset/README.md) explica el modelo, las etiquetas y el registro de prendas; [`schema.sql`](./documentacion_dataset/schema.sql) define las tablas y el catálogo inicial. El script [`crear_estructura.sh`](./documentacion_dataset/crear_estructura.sh) crea tanto las carpetas como `dataset/metadata.sqlite`. El [índice del dataset](./dataset/README.md) enlaza las guías por zona y tipo. Consulta también el [respaldo histórico V1](./README-v1.md), que no representa el plan vigente.

Para inicializar la estructura y la base desde la raíz del proyecto (o invoca ese mismo script con su ruta desde otro directorio):

```bash
bash documentacion_dataset/crear_estructura.sh
```

El script requiere Python 3 con su módulo estándar `sqlite3`, no el ejecutable de línea de comandos `sqlite3`. Es idempotente: conserva archivos existentes y las tablas y propiedades ya presentes; no migra una base anterior si cambia el esquema.

Reglas esenciales:

1. Una carpeta individual por prenda, con todas las fotos autorizadas de esa misma prenda.
2. Guardar las rutas de imagen relativas a `dataset/`; no usar rutas absolutas de las laptops.
3. Registrar cada imagen en `prenda_imagen` y cada etiqueta en `valor_propiedad_prenda`, enlazadas por `id_prenda`.
4. Mantener `split` en `prenda`, de modo que todas sus vistas queden en train, val o test conjuntamente.
5. Solo usar registros aprobados, aptos para entrenamiento y con permiso verificado.
6. El proceso MobileNet leerá SQLite y comprobará las imágenes referenciadas antes de entrenar.

La clase canónica `camisa` reúne camisas y camisetas. Esa unificación se aplica a las etiquetas de fuentes externas durante el escaneo y la importación; el texto de la etiqueta de origen se conserva para trazabilidad, pero no se crea una clase `camiseta` independiente.

## Flujo de trabajo

1. Definir la lista inicial de tipos, colores y estilos en el catálogo.
2. Crear una carpeta por prenda y guardar sus fotos autorizadas.
3. Registrar la prenda, cada ruta de imagen y sus propiedades en SQLite.
4. Revisar que las rutas existan, las propiedades estén en el catálogo y la muestra esté aprobada.
5. Asignar `train`, `val` o `test` por prenda; todas sus imágenes comparten ese split.
6. Cuando haya muestras suficientes y revisadas, congelar una copia de SQLite y de las imágenes.
7. Entrenar MobileNetV3-Small leyendo imágenes y etiquetas desde SQLite; empezar con la base congelada y batch bajo.
8. Evaluar en `val`, ajustar umbrales de color/estilo y medir una sola vez en `test`.
9. Repetir experimentos independientes en las demás laptops y guardar cada artefacto por separado.
10. Guardar el modelo y posteriormente preparar su integración con el proyecto OpenStack/Kubernetes.

## Uso de las cuatro laptops

Ejecutar **un experimento independiente por laptop**. Todas usan la misma versión del código y una copia idéntica de `dataset/`:

- Laptop 1: MobileNetV3-Small con base congelada, resolución inicial 160 × 160.
- Laptop 2: MobileNetV3-Small con base congelada, batch o tasa de aprendizaje distinta.
- Laptop 3: MobileNetV3-Small con la resolución mayor que permita su VRAM.
- Laptop 4: repetir la mejor configuración o probar descongelar solo el último bloque.

Registrar para cada ejecución el modelo, configuración, GPU, VRAM máxima, duración, métricas y versión del dataset. Copiar el resultado de cada equipo a una carpeta distinta; no sobrescribir modelos ni mezclar pesos automáticamente.

No se recomienda entrenamiento distribuido entre las laptops: añade configuración de red y sincronización, y no resuelve la limitación de VRAM de una tarjeta individual. En V2 las cuatro ejecutan MobileNetV3-Small en trabajos independientes.

## Docker Compose

La infraestructura inicial de entrenamiento se encuentra en [`utilidades-entrenamiento/`](./utilidades-entrenamiento/). El subproyecto [`modelo-general-destilacion/`](./utilidades-entrenamiento/modelo-general-destilacion/README.md) audita y prepara fuentes públicas con procedencia, revisión y anotación visual opcional; consulta su [`dudas.md`](./utilidades-entrenamiento/modelo-general-destilacion/dudas.md) antes de habilitar ingestión masiva.

La anotación con NVIDIA NIM o DeepSeek es una etapa de **curación**, no entrenamiento: NIM divide el análisis en solicitudes breves; ante un fallo intenta modelos NIM alternativos configurados. Si DeepSeek falla y NVIDIA NIM está configurado, se intenta NIM como respaldo. Los resultados guardan proveedor/modelo efectivos y quedan pendientes de revisión humana. La interfaz permite seleccionar hasta 5.000 imágenes nuevas por proveedor, buscando en todas las fuentes elegibles u otra fuente elegida; hashes ya importados y análisis vigentes se filtran antes de aplicar ese límite. Cada proveedor alterno o fallback puede generar solicitudes adicionales fuera del límite inicial.

```text
utilidades-entrenamiento/
├── Dockerfile
├── docker-compose.yaml
├── entrypoint.sh
├── train.py
├── predict.py
├── requirements.txt
├── configs/default.yaml
├── modelo-ia/
└── repositorios/
```

El Compose de CPU y el servicio opcional de GPU montan `../dataset/` en solo lectura y guardan pesos/caché en `utilidades-entrenamiento/modelo-ia/`. Los clones auxiliares pueden colocarse en `utilidades-entrenamiento/repositorios/`. El entrenador lee `dataset/metadata.sqlite`, agrupa las vistas por prenda para respetar el split y mantiene MobileNetV3-Small como arquitectura del MVP.

El servicio GPU ya está definido en `utilidades-entrenamiento/docker-compose.yaml` y reserva **una GPU local**.

Comandos implementados (desde `utilidades-entrenamiento/`):

```bash
# Consultar si el contenedor detecta GPU o usa CPU
docker compose --profile gpu run --rm train-gpu status

# Entrenar en GPU
docker compose --profile gpu run --rm train-gpu

# Entrenar en CPU
docker compose run --rm train
```

Para usar GPU dentro del contenedor, instalar Docker Engine/Compose y NVIDIA Container Toolkit compatibles con el driver del equipo. Si el comando `status` no detecta CUDA, corregir primero el acceso de Docker a la GPU o ejecutar el servicio CPU. El [README de las utilidades](./utilidades-entrenamiento/README.md) documenta entrenamiento, predicción y configuración.

## Alternativas sencillas

| Opción | Uso | Decisión |
|---|---|---|
| MobileNetV3-Small preentrenado | Clasificar tipo, colores y estilos en una prenda | **Único modelo del MVP V2** |
| Detector de objetos | Encontrar varias prendas y recortarlas en una misma foto | Fuera de alcance; considerar solo en otra versión |
| Modelo imagen-texto o modelo grande de lenguaje/visión | Clasificación zero-shot o descripción libre | Fuera de alcance; no requerido para V2 |

No cambiar a otro modelo si una laptop no logra usar GPU: ejecutar la misma arquitectura en CPU o reducir resolución/batch. Anotar cualquier limitación y decidir cambios de alcance en una versión posterior.

## Criterio de éxito del MVP

- Docker Compose puede iniciar el entrenamiento en cada laptop de forma independiente.
- El proceso puede usar GPU cuando driver y tarjeta sean compatibles, y dispone de alternativa CPU.
- El modelo recibe una o varias fotos de la misma prenda y devuelve tipo, colores y estilos con sus puntuaciones.
- Se mide accuracy por tipo y precision/recall/F1 para colores y estilos.
- Se registran los errores por clase y se conserva un test que no se utilizó para entrenar.

## Preguntas abiertas

1. ¿Cuáles son los modelos exactos de GPU de las cuatro laptops? Ejecutar `nvidia-smi` en cada una y compartir `Name` y `Memory-Total`.
2. ¿Qué tipos de prenda entran en la primera versión? Propongo empezar con camisa, pantalón, vestido, falda y chaqueta.
3. ¿Qué colores básicos y qué estilos quieren incluir? ¿«Fiesta rosa» significa color rosa más estilo fiesta?
4. ¿Las fotos muestran la prenda aislada, extendida, puesta en una persona o una combinación?
5. ¿Cómo se verificará y registrará el permiso de uso de las imágenes propias y de nuevas fuentes?

## Factibilidad y estado de la versión 2

La preparación local de carpetas y metadatos y el esqueleto ejecutable de entrenamiento Docker están implementados. El dataset ya tiene imágenes importadas, pero el snapshot de SQLite descrito en la guía de [factibilidad, alcance y pendientes del dataset](./documentacion_dataset/README.md#factibilidad-y-alcance-del-mvp) tenía todas las prendas pendientes de revisión y ninguna habilitada para entrenamiento. Antes de entrenar, validar relaciones, rutas de imagen, etiquetas, permisos y splits, aprobar muestras suficientes para las clases elegidas y probar compatibilidad con las GPU concretas. El [README de utilidades](./utilidades-entrenamiento/README.md) incluye comandos reproducibles; la guía del [pipeline de curación](./utilidades-entrenamiento/modelo-general-destilacion/README.md) describe las fuentes y los análisis sugeridos por IA.
