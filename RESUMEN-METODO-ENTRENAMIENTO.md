# Resumen del método de entrenamiento

> **Referencia metodológica con contexto histórico.** Ya existe un modelo entrenado y evaluado. Las cifras iniciales, recomendaciones y descripciones futuras del cuerpo no son un parte de estado vigente. Consulta el [resumen actualizado](<readme resumen.md>) y la [evaluación](EVALUACION-ENTRENAMIENTO.md).

## 1. Objetivo y estado actual

El proyecto entrena un clasificador visual que, a partir de una o varias fotografías de **una misma prenda**, predice tres grupos de propiedades: **tipo de prenda**, **color** y **estilo**. El alcance son nueve categorías: abrigo, blusa, camisa, chaqueta, falda, pantalón, short, suéter y vestido (camisas y camisetas se unifican en `camisa`). La temporada se anota en el dataset como metadato, pero **no es una salida del modelo** del MVP.

El modelo de producción del MVP es **MobileNetV3-Small**. Las IA generativas (NVIDIA NIM y DeepSeek) solo participan en la **curación del dataset**; no se despliegan ni son un profesor de destilación. El método implementado es **aprendizaje por transferencia supervisado** con etiquetas asistidas por IA; el estado aprobado no acredita revisión humana individual. La destilación queda como experimento posterior.

Estado: el dataset supera las 5.900 prendas importadas, pero las muestras creadas por el curador quedan `pendiente` y con `apta_para_entrenamiento = 0` hasta que una persona las apruebe. Ese era el estado inicial; actualmente existe un checkpoint compartido con evaluación registrada.

## 2. Flujo completo, del dataset al modelo

| Etapa | Qué ocurre | Responsable |
|---|---|---|
| 1. Importación | Se leen las fuentes locales, se mapea cada clase original a una clase canónica y se omiten las clases fuera del catálogo | Curador |
| 2. Anotación asistida | NIM y/o DeepSeek proponen aptitud, descripción, colores, estilos y temporadas | IA (solo propuesta) |
| 3. Revisión humana | Se aprueba o descarta cada prenda y se corrigen propiedades | Persona |
| 4. Particiones | Cada prenda recibe `train`, `val` o `test` | Script |
| 5. Entrenamiento | Transfer learning sobre `train`, comparación en `val` | `train.py` |
| 6. Evaluación final | Métricas en `test`, revisión de errores y decisión de aceptar el checkpoint | Persona |
| 7. Predicción | Inferencia con una o varias vistas de la prenda | `predict.py` |

## 3. Preparación y anotación de los datos

**Fuentes.** clothing-dataset-small, clothing-dataset y Apparel Images Gallery (AIG). Se conservan el origen y la etiqueta original; las carpetas fuera del catálogo (por ejemplo `Hoodies`) se omiten. Fashion-MNIST se reserva como benchmark aparte.

**Control de calidad al importar.** Se valida formato y tamaño (las imágenes de más de 200.000 bytes no se envían ni se reducen) y se calcula el SHA-256. La deduplicación por hash evita repetir imágenes y análisis, incluso con dos proveedores en paralelo. Los originales se montan en solo lectura y las muestras válidas se copian a `dataset/` con sus metadatos en SQLite.

**Anotación con IA.** Cada proveedor corre en su propio lote, con control de detención independiente y hasta **15.000 imágenes nuevas** por lote (no analizadas aún).

- **NVIDIA NIM:** modelo principal `nvidia/nemotron-3.5-super-vl-120b-a12b`. Si falla, cambia automáticamente a `meta/llama-3.2-11b-vision-instruct` después a `meta/llama-3.2-90b-vision-instruct` y finalmente a `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`. Un HTTP 500 o 429 se reintenta una vez; un modelo solo se excluye tras 4 fallos seguidos, o de inmediato con HTTP 401, 403 o 404.
- **DeepSeek:** `deepseek-flash`. Si falla, la imagen se reintenta con NIM.
- **Llamadas por etapas.** Para reducir JSON inválido, NIM resuelve cada imagen en cuatro llamadas cortas (colores, estilos, temporadas y validación) que luego se unen. El parser extrae el primer objeto JSON de la respuesta aunque venga con texto alrededor.
- **Vocabulario controlado.** Los colores son una lista cerrada. Los estilos y las temporadas pueden ampliarse con valores nuevos devueltos por las IA, que entran al catálogo.

**Las respuestas de IA son propuestas, no etiquetas.** Se guardan con proveedor, modelo y estado de revisión. Una persona debe confirmar la categoría, comprobar que la prenda sea visible y aprobar colores y estilos antes de habilitar la muestra. Las respuestas inválidas no se guardan como análisis.

## 4. Particiones y prevención de fuga de datos

La partición se asigna **por prenda**, no por fotografía: todas las vistas de una prenda quedan en el mismo conjunto. Esto evita que el modelo vea en `train` la misma prenda que luego se evalúa.

- `train` ajusta los pesos.
- `val` compara configuraciones, elige el mejor checkpoint y ajusta umbrales.
- `test` se usa **una sola vez** al final y nunca para elegir checkpoints o hiperparámetros.

Proporción recomendada: 70 % / 15 % / 15 %, estratificada por tipo de prenda. Mínimos sugeridos antes del primer entrenamiento serio: unas 100 prendas aprobadas por categoría y al menos 10 por categoría en `val` y en `test`. Las clases con muy pocas muestras deben esperar a tener más datos antes de interpretarse sus métricas.

## 5. Arquitectura del modelo

Se usa **MobileNetV3-Small preentrenada en ImageNet**: ligera, adecuada para CPU y portátil. Una base compartida extrae las características visuales y tres cabezas de clasificación las usan:

1. **Tipo de prenda:** una clase entre nueve (softmax). Pérdida: entropía cruzada.
2. **Color:** multi-etiqueta (sigmoide), porque una prenda puede tener varios colores. Pérdida: entropía cruzada binaria.
3. **Estilo:** multi-etiqueta (sigmoide), con cero o varios estilos. Pérdida: entropía cruzada binaria.

La pérdida total es la suma de las tres. Las prendas sin colores o estilos anotados **no aportan** a esa cabeza: la ausencia de anotación no se trata como etiqueta negativa.

## 6. Cómo se entrenará

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

## 7. Evaluación y criterios de aceptación

- **Tipo:** exactitud global, precisión, recall y F1 por clase, y matriz de confusión. Se revisan las confusiones esperables, como blusa–camisa o chaqueta–abrigo.
- **Color y estilo:** precisión, recall y F1 por etiqueta, y su promedio macro. La exactitud global engaña en problemas multi-etiqueta.
- **Revisión cualitativa:** se miran manualmente los errores de mayor confianza para detectar etiquetas mal revisadas.
- **Prueba final:** se ejecuta `test` solo con el checkpoint ya elegido. Si se retoca el modelo después de verlo, hay que renovar la partición `test`.

Un checkpoint se acepta si ninguna categoría queda con un rendimiento muy inferior al resto y el resultado en `test` es coherente con `val`. Los umbrales numéricos deben fijarse antes de entrenar, según el uso previsto del MVP.

## 8. Predicción

`predict.py` carga el checkpoint y devuelve el tipo y los colores y estilos cuya probabilidad supera el umbral. Con varias fotos de una misma prenda se predice cada vista y se **promedian las probabilidades**. El modelo no detecta ni separa varias prendas dentro de una imagen, así que cada foto debe mostrar una sola prenda.

## 9. Herramientas y ejecución

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

## 10. Riesgos y siguientes pasos

1. **Calidad de etiquetas:** es el mayor riesgo. Las propuestas de IA pueden equivocarse, por eso la revisión humana es obligatoria y conviene muestrear las aprobaciones para medir el error.
2. **Sesgo de las fuentes:** las imágenes públicas pueden tener fondos y poses distintos de los de uso real. Hay que añadir fotos propias y verificar licencias y permisos antes de usar o publicar el modelo.
3. **Desbalance:** revisar el conteo por tipo, color y estilo antes de entrenar.
4. **Orden de trabajo:** terminar el lote de anotación, revisar y aprobar, fijar particiones, entrenar la fase A, evaluar y solo entonces decidir sobre aumento de datos, ajuste fino o destilación.

Más detalle en el [README del proyecto](./README.md), la [guía de entrenamiento](./utilidades-entrenamiento/README.md), la [guía de metadatos](./documentacion_dataset/README.md) y el [pipeline de curación](./utilidades-entrenamiento/modelo-general-destilacion/README.md).
