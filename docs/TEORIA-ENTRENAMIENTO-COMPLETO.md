# Teoría del entrenamiento de MobileNetV3-Small para reconocimiento de prendas

**Documento de referencia (≈10 páginas).** Resume la teoría que sustenta el entrenamiento implementado en [`utilidades-entrenamiento/train.py`](../utilidades-entrenamiento/train.py) y las configuraciones [`default.yaml`](../utilidades-entrenamiento/configs/default.yaml) y [`desde-cero.yaml`](../utilidades-entrenamiento/configs/desde-cero.yaml). Los valores numéricos citados corresponden a la implementación real del repositorio, no a ejemplos genéricos.

---

## 1. Contexto y objetivo del modelo

El sistema clasifica una fotografía de una prenda de vestir en tres propiedades simultáneas:

| Tarea | Tipo de problema | Salida |
|---|---|---|
| Tipo de prenda | Clasificación **multiclase** (una sola clase) | 1 de 9 clases (`abrigo`, `blusa`, `camisa`, `chaqueta`, `falda`, `pantalon`, `short`, `sueter`, `vestido`) |
| Color | Clasificación **multietiqueta** | Subconjunto de 14 colores |
| Estilo | Clasificación **multietiqueta** | Subconjunto de 12 estilos |

Una prenda tiene exactamente un tipo, pero puede presentar varios colores y varios estilos a la vez. Por eso el tipo se modela como una decisión excluyente y el color/estilo como decisiones independientes por etiqueta. El umbral de decisión multietiqueta es **0,5** (`multilabel_threshold`): una etiqueta se considera presente si su probabilidad predicha es ≥ 0,5.

El criterio de aceptación del artefacto es el requisito **R11: promedio macro de las tres propiedades ≥ 70 %** (exactitud de tipo, Jaccard de color y Jaccard de estilo, con igual ponderación).

---

## 2. Fundamentos de visión por computador y redes convolucionales

### 2.1. La imagen como tensor

Una imagen RGB se representa como un tensor de forma `(3, H, W)`: tres canales (rojo, verde, azul) y una cuadrícula de píxeles de alto `H` y ancho `W`. Antes de entrar al modelo, cada imagen se redimensiona a **224×224** (la resolución nativa de los pesos ImageNet de MobileNetV3) y se normaliza con la media y desviación estándar de ImageNet:

$$\hat{x} = \frac{x - \mu}{\sigma},\qquad \mu=(0.485, 0.456, 0.406),\quad \sigma=(0.229, 0.224, 0.225)$$

La normalización pone cada canal en una escala comparable y es **obligatoria** para que los pesos preentrenados operen en el rango para el que fueron calibrados.

### 2.2. Convolución

Una capa convolucional desliza un **filtro** (kernel) de `k×k` sobre la imagen y calcula, en cada posición, el producto punto entre el filtro y el parche local. Los filtros aprenden detectores de patrones locales: bordes, texturas, formas. Conceptos asociados:

- **Padding:** relleno de ceros en los bordes para conservar la resolución espacial.
- **Stride:** paso con el que se desplaza el filtro; un stride > 1 reduce la resolución.
- **Canales de salida:** cada filtro produce un **mapa de características** (feature map); `C_out` filtros producen `C_out` mapas.

### 2.3. Jerarquía de características

Las CNN aprenden una jerarquía: las primeras capas detectan bordes y texturas; las capas medias combinan esos patrones en partes (cuellos, mangas, cierres); las capas finales forman conceptos de alto nivel (la forma de una prenda). Esta jerarquía es la razón por la que un backbone entrenado en un dominio visual general (ImageNet) es reutilizable en un dominio específico (prendas).

### 2.4. Pooling

El **pooling** reduce la resolución espacial tomando el máximo (max-pooling) o el promedio (average-pooling) de una ventana. Aporta invarianza a pequeños desplazamientos y reduce el costo computacional. MobileNetV3 usa, antes de la clasificación, un **global average pooling** que colapsa cada mapa de características a un único valor, produciendo un vector compacto de características.

---

## 3. MobileNetV3-Small

MobileNetV3-Small es una red convolucional **ligera** (≈2,5 millones de parámetros) diseñada por Google para dispositivos con recursos limitados. Es la arquitectura declarada del modelo (`architecture: mobilenet_v3_small`).

### 3.1. Convolución separable en profundidad (depthwise separable convolution)

Es el bloque fundamental que reduce el costo. Una convolución estándar `k×k` sobre `C_in` canales y con `C_out` filtros cuesta aproximadamente:

$$H\cdot W\cdot C_{in}\cdot C_{out}\cdot k^2$$

La convolución separable la divide en dos pasos:

1. **Depthwise:** un filtro `k×k` **por canal de entrada** (no mezcla canales): costo `H·W·C_in·k²`.
2. **Pointwise:** una convolución `1×1` que combina canales: costo `H·W·C_in·C_out`.

La relación de costo frente a la convolución estándar es aproximadamente:

$$\frac{1}{C_{out}} + \frac{1}{k^2}$$

Con `k=3` y `C_out` grande, la convolución separable cuesta entre 8 y 9 veces menos, manteniendo una capacidad expresiva razonable.

### 3.2. Bloque residual invertido con cuello de botella lineal

MobileNetV2/V3 organizan las capas en **bloques residuales invertidos**:

- **Expansión:** un pointwise `1×1` expande los canales (factor de expansión típico 3–6).
- **Depthwise `3×3`** procesa espacialmente los canales expandidos.
- **Proyección `1×1`** comprime de nuevo los canales (cuello de botella).
- **Conexión residual (skip):** suma la entrada a la salida cuando las formas coinciden, facilitando el flujo de gradientes en redes profundas.

El **cuello de botella lineal** evita aplicar una no linealidad (ReLU) en el espacio comprimido, donde destruiría información útil.

### 3.3. Squeeze-and-Excitation (SE)

Los bloques de MobileNetV3 incluyen un módulo **Squeeze-and-Excitation**: un global pooling "comprime" (squeeze) cada canal a un escalar y una pequeña red "excita" (excite) calcula pesos por canal que recalibran la importancia de cada feature map. Es una atención por canal barata que mejora la calidad sin añadir apenas costo.

### 3.4. Activación h-swish

MobileNetV3 sustituye ReLU por **hard-swish** en capas intermedias/tardías:

$$\text{h-swish}(x) = x\cdot\frac{\text{ReLU6}(x+3)}{6}$$

Aproxima swish con operaciones baratas y es más estable en cuantización y en hardware móvil.

### 3.5. Por qué es adecuada

- **Bajo costo:** permite entrenar e inferir en CPU o en una GPU modesta.
- **Transferencia directa:** existe un checkpoint preentrenado en ImageNet de calidad.
- **Multitarea:** su backbone produce un vector de características que alimenta tres cabezas lineales pequeñas.

---

## 4. Aprendizaje por transferencia y ajuste fino

### 4.1. Transferencia de aprendizaje

Entrenar una CNN desde pesos aleatorios exige millones de imágenes. En su lugar se parte de pesos **preentrenados en ImageNet** (≈1,2 millones de imágenes, 1000 clases), que ya codifican detectores generales de bordes, texturas y formas. El entrenamiento solo **adapta** esas representaciones al dominio de prendas.

### 4.2. Congelar y descongelar el backbone

- **Backbone congelado (freeze):** sus parámetros no reciben gradiente y no se actualizan. Solo se entrenan las cabezas.
- **Backbone descongelado (fine-tuning):** todos los parámetros se actualizan, el backbone con una tasa menor para no destruir las características preentrenadas.

La implementación controla esto en [`train.py`](../utilidades-entrenamiento/train.py) mediante `set_backbone_trainable()`:

- Si `finetune=true` y `warmup_epochs=0`, el backbone queda **descongelado desde la época 1**.
- Si `finetune=true` y `warmup_epochs>0`, el backbone inicia **congelado** y se descongela en la época `warmup_epochs + 1`.

### 4.3. Calentamiento de cabezas (warmup)

En la fase de calentamiento, las cabezas (inicializadas aleatoriamente) se entrenan solas durante `warmup_epochs` épocas, mientras el backbone permanece congelado. Esto evita que los gradientes grandes y ruidosos de las cabezas recién inicializadas degraden las características preentrenadas.

### 4.4. Tasas de aprendizaje diferenciales

El optimizador usa **dos tasas de aprendizaje**:

| Grupo de parámetros | Parámetro | Valor recomendado |
|---|---|---|
| Cabezas (`type_head`, `color_head`, `style_head`) | `learning_rate` | **0,001** desde cero; **0,0001** en continuación |
| Backbone | `finetune_lr` | **0,0001** desde cero; **0,00001** en continuación |

> **Lección verificada en el proyecto:** entrenar desde cero con la tasa de continuación (1e-4/1e-5) deja las cabezas sub-entrenadas y produce un recall de color colapsado (macro ≈ 61,8 %). Las cabezas aleatorias necesitan la tasa mayor (0,001). La tasa baja solo es apropiada para **afinar un modelo ya convergido**.

---

## 5. Formulación multitarea y multietiqueta

El modelo es una red **multitarea**: un único backbone compartido alimenta tres cabezas lineales.

### 5.1. Cabeza de tipo (multiclase)

Produce un logit por clase (`9`). Se aplica **softmax**, que convierte los logits en una distribución de probabilidad que suma 1:

$$P(y=c \mid x) = \frac{e^{z_c}}{\sum_{j} e^{z_j}}$$

La clase predicha es la de mayor probabilidad (`argmax`).

### 5.2. Cabezas de color y estilo (multietiqueta)

Producen un logit por etiqueta (`14` colores, `12` estilos). Se aplica **sigmoide** a cada logit de forma independiente:

$$P(\text{etiqueta}_i = 1 \mid x) = \sigma(z_i) = \frac{1}{1+e^{-z_i}}$$

Cada etiqueta se decide por separado: una prenda puede tener varios colores y varios estilos. La etiqueta se considera presente si `σ(z_i) ≥ 0,5`.

### 5.3. Tratamiento de etiquetas no anotadas

En la evaluación, una prenda sin etiquetas de color (o estilo) **no entra** en el cálculo de color (o estilo): la métrica solo se calcula sobre prendas con esa propiedad anotada. En el entrenamiento, la pérdida de color/estilo se enmascara análogamente para no penalizar como "ausente" lo que simplemente no fue anotado.

---

## 6. Funciones de pérdida

### 6.1. Entropía cruzada (tipo)

Para la clasificación multiclase se minimiza la **entropía cruzada** entre la distribución real (one-hot) y la predicha:

$$\mathcal{L}_{tipo} = -\sum_c y_c \log P(c \mid x)$$

### 6.2. Entropía cruzada binaria (color y estilo)

Para cada etiqueta multietiqueta se usa **entropía cruzada binaria con logits** (BCEWithLogits):

$$\mathcal{L}_{color} = -\sum_i \left[ y_i \log \sigma(z_i) + (1-y_i)\log(1-\sigma(z_i)) \right]$$

La pérdida total es la suma de las tres tareas, aplicando las máscaras de anotación en color y estilo.

### 6.3. Label smoothing

Con `label_smoothing = 0.05`, la etiqueta objetivo del tipo deja de ser one-hot puro (`1`/`0`) y se suaviza:

$$y^{LS}_c = (1-\alpha)\, y_c + \frac{\alpha}{C},\qquad \alpha=0.05$$

Evita que el modelo persiga una confianza del 100 % y mejora la calibración y la generalización.

### 6.4. Ponderación por clase

Con `class_weighted = true`, la pérdida de cada clase se multiplica por un peso inversamente proporcional a su frecuencia (con raíz cuadrada para suavizar):

$$w_c \propto \frac{1}{\sqrt{f_c}}$$

Esto compensa el desbalance (por ejemplo, muchas más blusas que faldas o suéteres) y evita que el modelo ignore las clases raras. Como efecto secundario, el modelo puede volverse más conservador en las clases raras, lo que se observa en el recall.

---

## 7. Optimización

### 7.1. Descenso de gradiente estocástico y lotes

El entrenamiento avanza por **épocas** (una pasada completa por train) y **lotes** (`batch_size = 64`). Cada lote produce un gradiente estimado y una actualización de pesos. Un lote mayor da gradientes más estables pero consume más memoria.

### 7.2. AdamW

Se usa **AdamW**: Adam con **weight decay desacoplado**. Adam mantiene medias móviles del gradiente (primer momento) y de su cuadrado (segundo momento) para adaptar el paso de cada parámetro:

$$m_t = \beta_1 m_{t-1} + (1-\beta_1) g_t,\qquad v_t = \beta_2 v_{t-1} + (1-\beta_2) g_t^2$$

$$\theta_t = \theta_{t-1} - \eta \cdot \frac{\hat{m}_t}{\sqrt{\hat{v}_t}+\epsilon} - \eta\,\lambda\,\theta_{t-1}$$

El término `η·λ·θ` es el **weight decay** (`weight_decay = 0.0001`): una penalización L2 desacoplada que reduce el sobreajuste.

### 7.3. Planificador coseno

`CosineAnnealingLR` reduce la tasa de aprendizaje desde su valor inicial hasta casi cero siguiendo una curva coseno a lo largo de `epochs`:

$$\eta_t = \eta_{min} + \frac{\eta_{max}-\eta_{min}}{2}\left(1 + \cos\left(\frac{t}{T_{max}}\pi\right)\right)$$

Permite dar pasos grandes al inicio y pasos finos al final para converger con suavidad.

---

## 8. Regularización y generalización

### 8.1. Aumento de datos

Con `augment = true`, cada época aplica variaciones aleatorias: **recorte aleatorio redimensionado** (RandomResizedCrop), **volteo horizontal** y **jitter de brillo/contraste**. El tono no se altera deliberadamente para no falsear la etiqueta de color. El aumento expande efectivamente el dataset y reduce el sobreajuste.

### 8.2. Otras regularizaciones

- **Weight decay** (sección 7.2).
- **Label smoothing** (sección 6.3).
- **Parada temprana:** si el `val_loss` no mejora durante `early_stopping_patience = 5` épocas consecutivas (contadas **después del warmup**), el entrenamiento se detiene.

### 8.3. Checkpoint por validación

En cada época se guarda `best.pt` **solo si** el `val_loss` mejora. El modelo final es el de menor pérdida de validación, no necesariamente el de la última época. La selección del checkpoint **no** consulta el test.

### 8.4. Separación de particiones y fuga de datos

Los datos se dividen en **train / val / test**. La partición se hace **por prenda** (todas las fotos de una prenda van al mismo split) para evitar **data leakage**: si una prenda apareciera en train y en test, el modelo la habría "visto" y el resultado se inflaría. Solo se usan prendas `aprobadas` y `aptas_para_entrenamiento = 1`. El test se evalúa **una única vez** con el modelo final.

---

## 9. Eficiencia: precisión mixta y ejecución

### 9.1. Precisión mixta (AMP)

Con `amp = true`, las operaciones seguras se ejecutan en **16 bits** (half) y las críticas en 32 bits. Un **GradScaler** escala la pérdida para evitar que gradientes pequeños se redondeen a cero en half. En GPU con Tensor Cores reduce memoria y acelera; en CPU el escaler se desactiva (`enabled=use_cuda and amp`).

### 9.2. Carga de datos

`num_workers = 8` son procesos que leen y transforman imágenes en paralelo, evitando que el cómputo espere a la entrada/salida. `shm_size` amplía la memoria compartida del contenedor para estos procesos.

### 9.3. CPU frente a GPU

El proyecto entrena tanto en CPU como en GPU. La GPU (CUDA) acelera enormemente las convoluciones; en CPU el entrenamiento es viable pero lento (≈3 min/época en el hardware de referencia). El dispositivo se elige con `--device auto|cpu|cuda`.

---

## 10. Métricas de evaluación

Con TP (verdaderos positivos), FP (falsos positivos) y FN (falsos negativos):

$$\text{Precisión} = \frac{TP}{TP+FP},\qquad \text{Recall} = \frac{TP}{TP+FN},\qquad F_1 = \frac{2\cdot P\cdot R}{P+R}$$

### 10.1. Exactitud de tipo

Porcentaje de imágenes cuyo tipo predicho coincide con la etiqueta real:

$$\text{Accuracy} = \frac{\text{tipos correctos}}{T}$$

Se complementa con **F1 macro** por clase y la **matriz de confusión**.

### 10.2. Jaccard (IoU) por imagen para color y estilo

Para una imagen, con `P_i` el conjunto de etiquetas predichas y `R_i` el conjunto real:

$$J_i = \frac{|P_i \cap R_i|}{|P_i \cup R_i|}$$

Se define `J_i = 1` si ambos conjuntos están vacíos. El **Jaccard promedio** es `(1/T)·Σ J_i`. También se reporta la **coincidencia exacta** (fracción de imágenes con `P_i = R_i`).

### 10.3. Promedio macro

Media aritmética sin ponderar de las tres propiedades (cada una pesa 1/3):

$$\text{Macro} = \frac{\text{Acc}_{tipo} + \text{Jaccard}_{color} + \text{Jaccard}_{estilo}}{3}$$

### 10.4. Umbral y curvas de precisión-recall

El umbral 0,5 fijo es **conservador** en color/estilo: subirlo aumenta la precisión y baja el recall; bajarlo hace lo contrario. La calibración correcta se hace sobre **validación** (curvas precisión-recall por etiqueta), nunca sobre test. Un recall muy bajo con precisión alta indica que el modelo omite etiquetas presentes — exactamente la firma observada en las ejecuciones degradadas.

---

## 11. Diagnóstico de entrenamiento y análisis de degradación

### 11.1. Interpretar curvas de pérdida

| Patrón | Interpretación |
|---|---|
| `train_loss` baja y `val_loss` baja | Convergencia sana |
| `train_loss` baja y `val_loss` sube de forma sostenida | Sobreajuste |
| Ambas se mantienen altas | Subajuste o configuración inadecuada |
| `val_loss` oscila | Ruido de etiquetas, lote pequeño o LR alta |

En este proyecto, `train_loss` y `val_loss` **no son directamente comparables**: el entrenamiento aplica aumento de datos y label smoothing, mientras que la validación no.

### 11.2. Hipótesis sobre la degradación observada

El [análisis de degradación](../EVALUACION-ENTRENAMIENTO.md) y las ejecuciones registradas permiten ordenar hipótesis:

- **H1. Ausencia de ajuste fino tras el warmup:** la ejecución del 26/10 configuró `warmup_epochs=3` y se detuvo en la época 3; el backbone nunca se descongeló. Es la hipótesis principal.
- **H2. Tasa de aprendizaje demasiado alta:** el 26/10 usó 0,001/0,0001 (correcta para desde cero, pero el experimento cambió varias variables a la vez, así que su efecto no quedó aislado).
- **H3. Umbral 0,5 conservador:** produce recall bajo en color; se comprueba calibrando en validación.
- **H4. Desbalance y ruido de etiquetas:** factor limitante documentado.
- **H5. Sobreajuste por exceso de épocas:** **no demostrado**; las ejecuciones de más épocas no fueron peores.

### 11.3. Plan experimental controlado

Para separar los efectos se proponen (análisis DSR):

| Prueba | LR cabezas | LR backbone | Backbone congelado | Épocas máx |
|---|---:|---:|---|---:|
| A — Ajuste fino desde el inicio | 0,001 | 0,0001 | No | 30 |
| B — Calentamiento controlado | 0,001 | 0,0001 | Primeras 3 | 30 |
| C — Fine-tune con LR de backbone menor | 0,001 | 0,00005 | No | 30 |

Manteniendo constantes dataset, particiones, batch, transformaciones, pesos iniciales, semilla, pérdida y procedimiento de evaluación.

---

## 12. Configuración concreta del proyecto

### 12.1. Hiperparámetros principales

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

### 12.2. Trazabilidad

Cada ejecución crea `modelo-ia/runs/<fecha-hora>/` con `config.json`, `metrics.json` (métricas por época), `progress.json`, `test_metrics.json` y `best.pt`. El ledger `registro_entrenamiento.sqlite` guarda el **SHA-256** de cada imagen usada por ejecución, permitiendo auditar qué datos vio cada modelo y detectar imágenes nuevas.

### 12.3. Reproducibilidad

- **Semilla fija** (`seed = 42`) para los sorteos de aumento y partición.
- **Mismo preprocesamiento** (resize 224 + normalización ImageNet) en train, val y test.
- **Selección por validación** del checkpoint; el test se evalúa una sola vez al final.

---

## 13. Referencias

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

*Documento derivado de la implementación real del repositorio; no sustituye los artefactos de cada ejecución. Consulta [`TEORIA-ENTRENAMIENTO.md`](../TEORIA-ENTRENAMIENTO.md) para el glosario rápido y [`EVALUACION-ENTRENAMIENTO.md`](../EVALUACION-ENTRENAMIENTO.md) para resultados.*
