# Terminología y teoría del entrenamiento

Explica los conceptos detrás del entrenamiento que hace este proyecto (`utilidades-entrenamiento/train.py`, configuración en `configs/default.yaml`).

## 1. Qué se está entrenando

Un **clasificador de imágenes multitarea**: dada la foto de una prenda, predice a la vez:

| Tarea | Tipo de problema | Salida |
|---|---|---|
| Tipo de prenda (blusa, falda, short…) | Clasificación de **una sola clase** | una clase entre 9 |
| Color | Clasificación **multi-etiqueta** | varios colores posibles |
| Estilo | Clasificación **multi-etiqueta** | varios estilos posibles |

Una prenda tiene un único tipo, pero puede tener varios colores y estilos; por eso se tratan distinto.

## 2. Modelo y arquitectura

- **Red neuronal:** función con millones de parámetros (pesos) que transforma una imagen en números. Aprender es ajustar esos pesos.
- **MobileNetV3-Small:** red convolucional ligera (~2,5 M de parámetros) diseñada para móviles y equipos modestos. Es la única arquitectura del MVP.
- **Backbone (base / extractor de características):** parte convolucional que convierte la imagen en un vector de características (colores, texturas, formas).
- **Cabezas (heads):** tres capas lineales pequeñas (`type_head`, `color_head`, `style_head`) que leen ese vector y producen las predicciones. Comparten el backbone: es lo que hace al modelo "multitarea".
- **Logit:** salida cruda de una cabeza, antes de convertirla en probabilidad.
- **Softmax:** convierte los logits del tipo en probabilidades que suman 1 (solo gana una clase).
- **Sigmoide:** convierte cada logit de color/estilo en una probabilidad independiente entre 0 y 1.
- **Umbral (`multilabel_threshold`, 0.5):** una etiqueta de color/estilo se considera presente si su probabilidad supera el umbral.

## 3. Aprendizaje por transferencia (transfer learning)

Entrenar desde cero requiere millones de imágenes. En su lugar se parte de pesos **preentrenados en ImageNet** (1,2 M de imágenes), que ya saben detectar bordes, texturas y formas. Solo se adaptan a las prendas.

Se hace en dos fases (`warmup_epochs` y `finetune`):

1. **Calentamiento (warmup):** el backbone está **congelado** (sus pesos no cambian) y solo se entrenan las cabezas, que empiezan con valores aleatorios. Evita que gradientes grandes y ruidosos destruyan lo ya aprendido.
2. **Ajuste fino (fine-tuning):** se **descongela** todo el backbone y se sigue con una tasa de aprendizaje mucho menor (`finetune_lr`) para especializarlo en ropa.

## 4. Ciclo de entrenamiento

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

## 5. Conjuntos de datos (splits)

| Split | Uso |
|---|---|
| **train** | Ajustar los pesos. |
| **val** (validación) | Medir tras cada época, elegir el mejor checkpoint, ajustar umbrales y decidir cuándo parar. No se entrena con él. |
| **test** | Evaluación final, **una sola vez** con el mejor modelo. Da la estimación honesta de rendimiento real. |

La partición se hace **por prenda** (todas las fotos de una prenda van al mismo split) para evitar **fuga de datos (data leakage)**: si una misma prenda estuviera en train y test, el resultado se inflaría.

Solo se usan prendas con `estado_revision = 'aprobado'` y `apta_para_entrenamiento = 1`.

## 6. Generalización: sobreajuste y regularización

- **Sobreajuste (overfitting):** el modelo memoriza el entrenamiento y falla con imágenes nuevas. Síntoma: la pérdida de train baja pero la de val sube.
- **Subajuste (underfitting):** el modelo no aprende ni siquiera el entrenamiento.
- **Regularización:** técnicas que combaten el sobreajuste:
  - **Aumento de datos (`augment`):** variaciones aleatorias en cada época (recorte aleatorio redimensionado, volteo horizontal, ligero cambio de brillo/contraste). No se altera el tono para no falsear el color.
  - **Label smoothing (0.05):** evita que el modelo se vuelva excesivamente seguro; suaviza las etiquetas objetivo del tipo.
  - **Weight decay** (ver sección 4).
  - **Parada temprana (`early_stopping_patience`, 5):** se detiene si la pérdida de validación no mejora durante 5 épocas seguidas.
- **Checkpoint (`best.pt`):** archivo con los pesos del mejor momento según la pérdida de validación; no necesariamente el de la última época.

## 7. Desbalance de clases

Hay muchas más blusas (≈6 300) que faldas (≈400) o suéteres (≈400). Sin corrección el modelo tiende a favorecer las clases mayoritarias. Se usa **ponderación por clase** (`class_weighted`): la pérdida de cada clase se multiplica por un peso inversamente proporcional a su frecuencia (con raíz cuadrada para suavizarlo). Por eso conviene mirar el rendimiento **por clase**, no solo el global.

## 8. Eficiencia: GPU y precisión mixta

- **GPU / CUDA:** la GPU NVIDIA procesa en paralelo miles de operaciones; CUDA es su plataforma de cómputo. Sin GPU el entrenamiento corre en CPU, mucho más lento.
- **VRAM:** memoria de la GPU (6 GB en la RTX 2060). Limita el tamaño de lote y de imagen.
- **Precisión mixta (AMP, `amp`):** usa números de 16 bits donde es seguro y 32 donde hace falta. Reduce memoria y acelera en GPU con Tensor Cores (Turing las tiene). El **GradScaler** escala la pérdida para evitar que gradientes pequeños se redondeen a cero.
- **`num_workers`:** procesos que leen y transforman imágenes en paralelo para que la GPU no espere.
- **`shm_size`:** memoria compartida del contenedor; necesaria para que esos procesos intercambien lotes.
- **Resolución (`image_size`, 224):** tamaño al que se redimensiona cada imagen. 224 px es la resolución nativa con la que se preentrenaron los pesos; más pequeña ahorra cómputo pero pierde detalle.
- **Normalización:** las imágenes se restan/dividen por la media y desviación de ImageNet, que es lo que espera el backbone preentrenado.

## 9. Métricas de evaluación

- **Accuracy (exactitud) del tipo:** porcentaje de prendas con el tipo correcto.
- Para color y estilo (multi-etiqueta), con TP = verdaderos positivos, FP = falsos positivos y FN = falsos negativos:

$$\text{Precisión}=\frac{TP}{TP+FP}\qquad \text{Recall}=\frac{TP}{TP+FN}\qquad F_1=\frac{2\cdot P\cdot R}{P+R}$$

  - **Precisión:** de lo que el modelo dijo que había, cuánto era cierto.
  - **Recall (exhaustividad):** de lo que realmente había, cuánto detectó.
  - **F1:** media armónica de ambas; penaliza que una sea baja.
- **Matriz de confusión:** tabla clase real vs. predicha; muestra qué clases se confunden (por ejemplo, falda con short).
- Subir el umbral aumenta la precisión y baja el recall; bajarlo hace lo contrario. Se ajusta en `val`, nunca en `test`.

## 10. Trazabilidad y reproducibilidad

- **Semilla (`seed`):** fija los números aleatorios para poder repetir un experimento.
- **Ejecución (run):** cada entrenamiento crea `modelo-ia/runs/<fecha-hora>/` con `config.json`, `metrics.json`, `test_metrics.json`, `progress.json` y `best.pt`.
- **Registro de imágenes:** `modelo-ia/registro_entrenamiento.sqlite` guarda qué imágenes (con su **hash SHA-256**) se usaron en cada ejecución. El hash identifica el contenido del archivo, de modo que se puede saber qué imágenes son nuevas al crecer el dataset.
- **Contenedor (Docker):** empaqueta código, dependencias y entorno para que el entrenamiento sea idéntico y portable entre equipos. El dataset se monta en solo lectura.

## 11. Limitaciones conocidas

- El modelo clasifica **una prenda por foto**; no detecta ni separa varias prendas en una imagen (eso requeriría detección de objetos).
- Las etiquetas proceden de anotación asistida por IA y revisión humana; los errores de etiqueta limitan el techo de calidad.
- Las fuentes públicas pueden tener fondos y poses distintos al uso real: el rendimiento en producción puede ser menor que en `test`.
- El estilo es subjetivo; su F1 suele ser inferior al del tipo o el color.

## 12. Glosario rápido

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
