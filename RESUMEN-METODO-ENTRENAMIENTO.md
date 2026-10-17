# Resumen del método de entrenamiento

## Objetivo y estado actual

El proyecto busca entrenar un clasificador visual que, a partir de una o varias fotografías de una misma prenda, prediga tres grupos de propiedades: **tipo de prenda**, **color** y **estilo**. El alcance actual contempla nueve categorías: abrigo, blusa, camisa, chaqueta, falda, pantalón, short, suéter y vestido. Camisas y camisetas se unifican en `camisa`.

El modelo de producción del MVP será **MobileNetV3-Small**. El pipeline de IA generativa/visión usado para preparar y describir imágenes es una etapa de curación de datos, no el modelo que se desplegará para clasificar prendas ni una destilación clásica. La destilación podrá evaluarse después, pero el método actualmente implementado es **aprendizaje por transferencia supervisado**, con etiquetas revisadas por personas.

La base del dataset ya está en marcha; sin embargo, las muestras importadas por el curador quedan pendientes de revisión humana y deshabilitadas para entrenamiento hasta que se aprueben. Por tanto, aún no se considera entrenado ni validado un modelo final.

## Estrategia de preparación y anotación

Las imágenes se inspeccionan desde tres fuentes locales: clothing-dataset-small, clothing-dataset y Apparel Images Gallery (AIG). Se conserva el origen y la etiqueta original, y se asigna una clase canónica mediante mapeos explícitos. Se omiten carpetas y clases que no pertenecen al catálogo; por ejemplo, `Hoodies` en AIG. Fashion-MNIST se mantiene como benchmark separado, no como fuente de fotos para la anotación visual.

Antes de copiar una imagen, el pipeline comprueba su formato, tamaño y huella SHA-256. Las imágenes de más de 200.000 bytes no se envían ni se reducen. Los originales se montan en solo lectura; las muestras válidas se copian a la jerarquía `dataset/` y sus rutas y metadatos quedan en SQLite. La deduplicación por hash evita repetir análisis o registrar dos veces una misma imagen, incluso si dos proveedores terminan simultáneamente.

Para sugerir si la imagen corresponde a su clase y generar una descripción breve se pueden ejecutar, en paralelo e independientemente:

- **NVIDIA NIM**, con el modelo visual configurado por defecto `meta/llama-3.2-11b-vision-instruct`.
- **DeepSeek**, con el modelo configurado `deepseek-flash`, cuando el endpoint y la cuenta admitan la entrada visual requerida.

Estos son modelos auxiliares de anotación, no el clasificador que se entrenará. Cada proveedor tiene su propio registro y control de detención. El límite del panel es de hasta 5.000 imágenes por proveedor; seleccionar ambos puede producir hasta 10.000 análisis combinados y repetir el costo/cuota por imagen. Se solicita salida JSON estructurada y se pide a la IA utilizar solo clases, colores y estilos del vocabulario. El prompt incluye el contexto estructurado en TOON; el formato de transporte y respuesta sigue siendo el JSON compatible con las APIs.

Las respuestas de IA son **propuestas**, no etiquetas confiables automáticamente. Una persona debe aprobar la categoría, comprobar que la prenda sea visible y confirmar las propiedades antes de habilitar la muestra para entrenamiento. Descripciones y sugerencias se guardan con proveedor, modelo y estado de revisión. Las decisiones válidas se almacenan por huella para reutilizarlas; respuestas inválidas o truncadas no se guardan como análisis. Si una respuesta viene vacía o truncada, se hace un reintento acotado con más tokens; si continúa fallando, se omite la imagen y el lote avanza.

## Método de entrenamiento y modelo

La arquitectura implementada en `train.py` usa una base **MobileNetV3-Small preentrenada en ImageNet** y tres cabezas de clasificación que comparten las características visuales:

1. **Tipo de prenda:** clasificación de una sola clase mediante una salida por categoría.
2. **Color:** clasificación multi-etiqueta, porque una prenda puede tener varios colores.
3. **Estilo:** clasificación multi-etiqueta; puede tener cero o varios estilos confirmados.

El entrenamiento inicial congela la base preentrenada y ajusta las cabezas. Es una forma de *transfer learning* que reduce el costo y el riesgo de sobreajuste cuando el dataset propio todavía es pequeño. Si la validación y la memoria disponible lo justifican, el siguiente experimento puede descongelar solo el último bloque, conservando checkpoint y métricas separados. La función de pérdida combina entropía cruzada para tipo con entropía cruzada binaria para colores y estilos; las propiedades sin anotación no se tratan como etiquetas negativas.

La configuración de partida es 160 × 160 píxeles, batch 2, 15 épocas, tasa de aprendizaje 0,001, pesos preentrenados, semilla 42 y umbral multi-etiqueta 0,5. Son valores iniciales que se deben ajustar mediante experimentos y validación, no garantías de desempeño. El pipeline de entrenamiento lee las etiquetas aprobadas de SQLite y excluye muestras pendientes o no aptas.

Cada prenda, no cada fotografía, tiene su partición (`train`, `val` o `test`); así todas las vistas de la misma prenda permanecen juntas y no hay fuga de datos entre particiones. `train` ajusta los pesos, `val` permite comparar configuraciones y elegir umbrales, y `test` se reserva para la evaluación final, sin utilizarlo para seleccionar checkpoints. Para varias fotos de una prenda, se predice cada vista y se promedian las probabilidades; el sistema no detecta ni separa varias prendas dentro de una sola fotografía.

## Herramientas y ejecución

- **Python 3.12**, **PyTorch** y **torchvision** implementan el dataset, el entrenamiento, la evaluación y la predicción.
- **SQLite** (`dataset/metadata.sqlite`) guarda prendas, imágenes, particiones, etiquetas aprobadas, catálogo y trazabilidad de la curación.
- **Docker Compose** ofrece ejecución reproducible del curador y del entrenamiento. El pipeline de curación utiliza Pillow y Requests para inspeccionar/preparar imágenes y llamar a APIs.
- **NVIDIA NIM y DeepSeek** proporcionan anotación visual asistida durante la preparación; las API keys permanecen en `.env` y no forman parte del dataset ni del modelo.
- Los checkpoints, la configuración y las métricas de cada entrenamiento se almacenan en `utilidades-entrenamiento/modelo-ia/runs/`, fuera de `dataset/`.
- El entrenamiento ofrece CPU y un perfil opcional de GPU NVIDIA con CUDA. El uso de una GPU AMD no se debe dar por habilitado por esta configuración: requeriría validar una pila compatible, por ejemplo ROCm, en el hardware concreto.

Comandos de referencia desde `utilidades-entrenamiento/`:

```bash
docker compose build
docker compose run --rm train status
docker compose run --rm train train --epochs 1 --device cpu
docker compose --profile gpu run --rm train-gpu status
docker compose --profile gpu run --rm train-gpu
```

El entrenamiento normal se debe ejecutar cuando haya suficientes imágenes con permiso verificado, etiquetas revisadas y ejemplos representativos en `train` y `val`. Antes de aceptar un checkpoint se deben comparar métricas por tipo y métricas multi-etiqueta de color/estilo, revisar errores por clase y confirmar el resultado en `test`. El plan detallado y el estado operativo permanecen en los [documentos del proyecto](./README.md), la [guía del entrenamiento](./utilidades-entrenamiento/README.md), la [guía de metadatos](./documentacion_dataset/README.md) y el [pipeline de curación](./utilidades-entrenamiento/modelo-general-destilacion/README.md).
