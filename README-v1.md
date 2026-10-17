> **VERSIÓN 1 — DESCARTADA.** Este plan se conserva únicamente como respaldo histórico. Se descartó para dar paso a la versión 2; seguir las instrucciones de [`README.md`](./README.md).
>
> Para la documentación vigente del dataset, consulta el [índice](./dataset/README.md), la [guía de metadatos](./documentacion_dataset/README.md) y el [esquema SQLite](./documentacion_dataset/schema.sql).

# Reconocimiento de prendas

Módulo pequeño de visión por computadora para complementar el proyecto de OpenStack y Kubernetes. El objetivo es entrenar un modelo que, a partir de **una o varias fotos de la misma prenda**, devuelva:

- Tipo: camisa, pantalón, vestido, falda, etc.
- Color o colores básicos: negro, blanco, rojo, azul, rosa, etc.
- Estilo: casual, elegante, fiesta, verano, deportivo, etc.

La primera versión se ejecutará con **Docker Compose** en una laptop. No necesita Kubernetes, base de datos, API, interfaz web ni un modelo generativo grande para entrenar. La integración con el proyecto principal se deja para después.

## Decisión técnica para el MVP

Usar un modelo de clasificación de imágenes pequeño con pesos preentrenados y ajustar sus últimas capas con nuestras imágenes:

1. **MobileNetV3-Small**: primera opción por tamaño y costo de ejecución.
2. **SqueezeNet 1.1**: alternativa pequeña si MobileNet no cabe o resulta lento en una GPU concreta.
3. **EfficientNet-B0 o ResNet18**: alternativas para comparar si hay memoria suficiente.

El modelo tendrá salidas separadas:

- **Tipo de prenda:** una categoría principal.
- **Color:** uno o varios colores.
- **Estilo:** cero o varios estilos.

Las etiquetas de estilo dependen de criterios humanos. Se deben definir ejemplos para cada una y etiquetar consistentemente. No mezclar conceptos: si «fiesta rosa» significa una prenda rosa para fiesta, guardar `rosa` como color y `fiesta` como estilo, no como una sola categoría.

### Una o varias fotos

Cada foto debe mostrar la misma prenda. El modelo predice cada foto por separado y combina las probabilidades para generar un único resultado para esa prenda. Se recomienda empezar promediando las probabilidades de las fotos.

Este MVP **no identifica ni separa varias prendas dentro de una sola foto**. Para eso haría falta añadir detección de objetos o recortar las prendas antes de enviarlas al clasificador.

## Hardware y límites

- Las cuatro GPU están en laptops distintas: **no se combinan ni se suman sus VRAM**.
- Con **2 GB de VRAM**, empezar con MobileNetV3-Small, imágenes de 128–160 píxeles, batch 1 y el extractor de características congelado; entrenar primero solo la capa final. Si cabe, probar después a descongelar el último bloque.
- Con **4 GB**, probar imágenes de 160–224 píxeles y batch pequeño (1–4), midiendo uso real de memoria.
- GPUs GTX y RTX pueden tener capacidades diferentes. Docker necesita que el driver NVIDIA de cada laptop sea compatible con la versión de CUDA/PyTorch de la imagen.
- Si una GPU o driver no es compatible, ejecutar entrenamiento por CPU como alternativa funcional, aunque será más lento.
- Los 100–200 GB libres en SSD son suficientes para empezar con un dataset acotado y guardar varios experimentos. No descargar datasets grandes hasta confirmar las licencias y el espacio requerido.

Estos valores son **puntos de partida**, no garantías de memoria o velocidad. Verificar cada equipo con una prueba corta antes del entrenamiento completo.

## Estructura mínima del dataset

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

## Flujo de trabajo

1. Definir la lista inicial de tipos, colores y estilos.
2. Reunir imágenes que podamos usar y agrupar las vistas por prenda.
3. Etiquetar `labels.csv` siguiendo las reglas anteriores.
4. Separar train/val/test por `garment_id`.
5. Ejecutar un entrenamiento pequeño en una laptop y comprobar que cabe en su GPU.
6. Repetir en las demás laptops, cambiando una configuración por experimento y guardando los resultados por separado.
7. Comparar resultados sobre el mismo conjunto de test; escoger el modelo con menos errores relevantes, no solo el que entrenó más rápido.
8. Guardar el modelo entrenado y preparar posteriormente su integración con el proyecto OpenStack/Kubernetes.

## Uso de las cuatro laptops

Ejecutar **un experimento independiente por laptop**. Todas usan la misma versión del código y una copia idéntica de `data/`:

- Laptop 1: MobileNetV3-Small con configuración base.
- Laptop 2: mismo modelo con otra resolución o tasa de aprendizaje.
- Laptop 3: comparar SqueezeNet 1.1.
- Laptop 4: validar, probar otro ajuste o ejecutar el mejor modelo.

Registrar para cada ejecución el modelo, configuración, GPU, VRAM máxima, duración, métricas y versión del dataset. Copiar el resultado de cada equipo a una carpeta distinta; no sobrescribir modelos ni mezclar pesos automáticamente.

No se recomienda entrenamiento distribuido entre las laptops: añade configuración de red y sincronización, y no resuelve la limitación de VRAM de una tarjeta individual.

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

## Alternativas sencillas

| Opción | Uso | Decisión |
|---|---|---|
| MobileNetV3-Small preentrenado | Clasificar tipo, colores y estilos en una prenda | **Recomendada para comenzar** |
| SqueezeNet 1.1 preentrenado | Probar una arquitectura aún más pequeña | Alternativa para GPU con poca memoria |
| EfficientNet-B0 o ResNet18 | Comparar si MobileNet cabe y se desea otra referencia | Opcional |
| YOLO u otro detector | Encontrar varias prendas y recortarlas en una misma foto | No incluir en el MVP; requiere cajas anotadas y más recursos |
| CLIP | Probar etiquetas con texto sin ajuste supervisado completo | Comparación opcional; comprobar requisitos y licencias |
| Modelo grande de lenguaje/visión | Generar descripciones libres | No recomendado para este alcance y VRAM |

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

## Estado

Este README define el alcance reducido y la estructura propuesta. Aún deben crearse el dataset, el script de entrenamiento y los archivos Docker indicados en la sección Docker Compose. El primer paso es responder las preguntas abiertas e inventariar las GPU.
