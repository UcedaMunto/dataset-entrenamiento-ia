# Reconocimiento de prendas — Versión 2

> **Versión vigente:** 2. La versión anterior se conserva como respaldo descartado en [`README-v1.md`](./README-v1.md).

Módulo pequeño de visión por computadora para complementar el proyecto de OpenStack y Kubernetes. El objetivo es entrenar un modelo que, a partir de **una o varias fotos de la misma prenda**, devuelva:

- Tipo: camisa, pantalón, vestido, falda, etc.
- Color o colores básicos: negro, blanco, rojo, azul, rosa, etc.
- Estilo: casual, elegante, fiesta, verano, deportivo, etc.

El MVP se ejecutará con **Docker Compose** en una laptop. No necesita Kubernetes, un servidor de base de datos, API, interfaz web ni un modelo generativo grande para entrenar. Usa SQLite local únicamente para los metadatos del dataset. La integración con el proyecto principal se deja para después.

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

La clase `camisa` agrupa las prendas superiores con abertura frontal y las camisetas; ambas se guardan en `superior/camisas/` y usan la misma etiqueta. Los tipos de prenda del catálogo inicial son abrigo, blusa, camisa, chaqueta, falda, pantalón, short, suéter y vestido.

El esquema usa cuatro tablas:

- `prenda`: código, ruta de categoría, split y estado de revisión; una fila por prenda.
- `prenda_imagen`: relación de una prenda con una o más rutas relativas a `dataset/`.
- `catalogo_propiedad`: tipos de propiedad permitidos, como `tipo_prenda`, `color`, `estilo` y atributos.
- `valor_propiedad_prenda`: cada valor asociado a la prenda y a su propiedad. Color y estilo pueden ocupar varias filas por prenda.

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
├── dataset/
└── models/
```

El contenedor montará `dataset/` y `models/` desde la laptop: las imágenes y los modelos no se guardan dentro de la imagen Docker. El script de entrenamiento leerá `dataset/metadata.sqlite`, cargará las rutas de `prenda_imagen` y formará lotes usando las etiquetas de `valor_propiedad_prenda` agrupadas por split. La configuración permitirá elegir GPU o CPU y cambiar resolución y batch, manteniendo MobileNetV3-Small como arquitectura de esta versión.

Ejemplo de reserva de **una GPU local** en `compose.yaml`:

```yaml
services:
  train:
    build: .
    command: ["python", "train.py", "--config", "configs/default.yaml"]
    volumes:
      - ./dataset:/app/dataset:ro
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
5. ¿Cuántas imágenes tienen y son propias o cuentan con permiso para entrenar?

## Factibilidad y estado de la versión 2

La preparación local de carpetas y metadatos es factible y queda cubierta por el script y el esquema enlazados arriba. La guía de [factibilidad, alcance y pendientes del dataset](./documentacion_dataset/README.md#factibilidad-y-alcance-del-mvp) detalla qué está listo y qué bloquea un entrenamiento completo. En particular, aún se necesitan imágenes autorizadas y anotadas, decisiones de taxonomía y los scripts de entrenamiento y Docker. Antes de entrenar, validar relaciones, rutas de imagen, etiquetas, permisos y splits.
