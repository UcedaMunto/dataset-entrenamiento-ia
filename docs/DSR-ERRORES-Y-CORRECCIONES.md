# Registro DSR: errores del entrenamiento y correcciones aplicadas

Documento de trazabilidad del **ciclo de diseño** de Design Science Research Methodology (DSRM) aplicado al clasificador MobileNetV3-Small. Registra los errores cometidos, su diagnóstico, las correcciones implementadas y la verificación del cambio. Complementa la teoría del método de evaluación en [`TEORIA-METODO-EVALUACION.md`](TEORIA-METODO-EVALUACION.md).

---

## 1. Contexto: el artefacto y su requisito de aceptación

- **Artefacto evaluado:** clasificador MobileNetV3-Small que predice **tipo** (multiclase), **color** y **estilo** (multietiqueta) a partir de una fotografía de prenda.
- **Requisito verificable (R11):** promedio macro ≥ **70 %**, calculado como media aritmética no ponderada de la exactitud de tipo y el Jaccard por imagen de color y estilo, sobre el conjunto de prueba fijo (1.424 imágenes portables).
- **Referencia documentada:** checkpoint compartido (`mobilenetv3-small-best.pt`, época 15 del entrenamiento del 26-10) con **macro 77,52 %** (tipo 94,94 %, color Jaccard 68,42 %, estilo Jaccard 69,21 %).

Las actividades DSRM que estructuran este registro son: identificación del problema → diagnóstico (diseño) → intervención (desarrollo) → verificación (evaluación) → lecciones (comunicación).

---

## 2. Identificación del problema

Tras los primeros entrenamientos, se observaron dos síntomas que debían explicarse:

1. Un entrenamiento **interrumpido durante el warmup** producía un modelo con colapso del recall de color.
2. Un entrenamiento **desde cero** configurado manualmente no alcanzaba R11 (macro **61,78 %**), muy por debajo del nivel esperado.

La pregunta de investigación del ciclo: **¿qué configuración de hiperparámetros permite entrenar desde cero alcanzando el nivel de referencia sin degradar el modelo?**

---

## 3. Errores anteriores (evidencia y diagnóstico)

### 3.1. Error E1 — Entrenamiento detenido durante el calentamiento (26-10)

| Elemento | Detalle |
|---|---|
| Ejecución | `20261026-020700` |
| Configuración | lr 0,001 · finetune_lr 1e-4 · warmup 3 · epochs 30 · pretrained sí |
| Observado | Se registraron **solo 3 épocas**; val_loss final 0,795 |
| Mecanismo | Con warmup = 3, el *backbone* preentrenado permanece congelado durante las 3 primeras épocas y solo se descongela después. Al detenerse en la época 3, el modelo **nunca liberó el backbone**; las cabezas aprendieron con features fijas y sin ajuste fino. |
| Consecuencia | Colapso del recall de color (la tarea multietiqueta más dependiente del backbone) y pérdida de capacidad de generalización. |

**Diagnóstico DSR (ciclo de diseño):** el fallo no fue de la arquitectura sino de la **condición de ejecución**: se evaluó/comparó un estado incompleto del entrenamiento (fase de warmup) como si fuera un resultado final. La lección: **no interpretar una ejecución truncada como un entrenamiento terminado**.

### 3.2. Error E2 — Tasas de aprendizaje de continuación usadas para entrenar desde cero (28-10)

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

## 4. Correcciones realizadas (intervención)

### 4.1. Corrección de la configuración desde cero

Se corrigió [`desde-cero.yaml`](../utilidades-entrenamiento/configs/desde-cero.yaml) para reproducir la receta que históricamente alcanzó el nivel de referencia:

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

### 4.2. Correcciones operativas en el panel de entrenamiento

- Se añadió el **selector de configuración** en el monitor y el endpoint `/api/configs`, para que el usuario elija la receta correcta sin editar archivos a mano.
- Se corrigió el **enrutamiento de `/api/start?config=…`**: antes se comparaba la ruta exacta y una petición con parámetros devolvía **404 «No encontrado»**; ahora se compara solo la parte de ruta.
- Efecto en DSR: se eliminó una **fuente de error humano** (elegir la configuración equivocada) y una **fuente de error de interfaz** (lanzar el entrenamiento fallaba sin indicar la causa).

---

## 5. Verificación del cambio (evaluación)

### 5.1. Verificación de la configuración ejecutada

La nueva ejecución `20261029-022656` cargó exactamente la receta corregida: lr 0,001 · finetune_lr 1e-4 · warmup 3 · epochs 30 · pretrained sí · early stopping 5. ✔

### 5.2. Comportamiento del entrenamiento

| Observación | Valor |
|---|---|
| Épocas ejecutadas | 28 de 30 (parada temprana) |
| Mejor época (best.pt) | 23 |
| val_loss época 1 → 28 | 1,025 → 0,535 |
| Exactitud de tipo en validación (ép. 28) | 93,56 % |
| F1 color / estilo en validación (ép. 28) | 0,738 / 0,779 |

La curva muestra aprendizaje sostenido y sin divergencia; la parada temprana actuó correctamente tras el warmup.

### 5.3. Resultado sobre el conjunto de prueba portable (1.424 imágenes)

| Métrica | Referencia (26-10) | Fallido E2 (28-10) | **Nuevo (29-10)** |
|---|---:|---:|---:|
| Tipo (exactitud) | 94,94 % | 89,37 % | 94,03 % |
| Color (Jaccard) | 68,42 % | 33,20 % | **69,28 %** |
| Estilo (Jaccard) | 69,21 % | 62,78 % | **69,29 %** |
| **Promedio macro** | **77,52 %** | **61,78 %** | **77,53 %** |
| R11 (macro ≥ 70 %) | Cumple | No cumple | **Cumple** |

Verificación con la misma fuente (conjunto portable de 1.424 imágenes, mismo preprocesamiento y umbral 0,5) y también sobre el split `test` del nodo de entrenamiento (1.421 imágenes): macro **77,55 %** (tipo 94,02 %, color 69,33 %, estilo 69,30 %).

### 5.4. Conclusión de la verificación

1. **El entrenamiento se hizo correctamente:** configuración verificada, 28 épocas completas, parada temprana válida, sin colapso de color.
2. **Mejoró respecto del entrenamiento fallido:** macro **77,53 %** frente a 61,78 % (+15,75 pp), recuperando por completo el recall de color (69,28 % frente a 33,20 %).
3. **Frente a la referencia:** macro prácticamente idéntico (77,53 % vs 77,52 %). Se observa un intercambio: color (+0,86 pp) y estilo (+0,08 pp) mejoran, mientras tipo baja (−0,91 pp). Es decir, **la receta corregida reproduce el nivel de referencia, pero no lo supera**.
4. **R11 cumplido:** sí, con margen de +7,53 pp sobre el umbral de 70 %.

---

## 6. Lecciones aprendidas y prevención de recurrencia

| Lección DSR | Consecuencia operativa |
|---|---|
| La configuración de **continuación** no sirve para **desde cero**; son perfiles distintos. | Mantener `default.yaml`/`desde-cero.yaml` (desde cero) separados del perfil de continuación, con nombres explícitos. |
| Un entrenamiento **truncado en warmup** no es un resultado final. | No evaluar ni comparar ejecuciones con menos épocas que el warmup; registrar el motivo de finalización. |
| Los parámetros de la petición deben manejarse en la **ruta**, no en la cadena completa. | `/api/start?config=…` ya compara solo la parte de ruta. |
| La comparación justa exige **misma muestra y mismas condiciones**. | Verificar el checkpoint cargado (SHA-256) y el conjunto de imágenes en cada ejecución. |

**Limitaciones que persisten:** el split de entrenamiento cambió levemente entre la referencia (11.616) y la nueva ejecución (11.592) por la depuración de duplicados, por lo que la comparación debe declarar ese factor; las etiquetas de color/estilo proceden de IA (NVIDIA NIM y DeepSeek), de modo que se mide concordancia con esas anotaciones, no con una verdad de terreno humana.

---

## 7. Referencias

- Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). Design Science in Information Systems Research. *MIS Quarterly*, 28(1), 75–105.
- Peffers, K., Tuunanen, T., Rothenberger, M. A., & Chatterjee, S. (2007). A Design Science Research Methodology for Information Systems Research. *Journal of Management Information Systems*, 24(3), 45–77.
- Guía de contenido del informe DSRM y Anexo G (documento de trabajo del proyecto).
- [`TEORIA-METODO-EVALUACION.md`](TEORIA-METODO-EVALUACION.md) — teoría del método de evaluación.
