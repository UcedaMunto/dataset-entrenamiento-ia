# Teoría y conceptos del método de evaluación (DSRM)

Documento de referencia conceptual sobre **cómo se mide** el desempeño del modelo de reconocimiento de prendas (MobileNetV3-Small). No incluye comandos, endpoints ni valores de ejecución: presenta únicamente la teoría y los conceptos del método de evaluación empleado, alineado con **Design Science Research Methodology (DSRM)** y con el protocolo documentado en el Anexo G.

---

## 1. La evaluación dentro del diseño: DSRM

### 1.1. Qué es la evaluación en Design Science

La evaluación es la actividad de Design Science que responde a una pregunta verificable: **¿el artefacto cumple los requisitos para los que fue diseñado?** No es un paso posterior al trabajo, sino una actividad integrada en el ciclo del método:

1. **Identificación del problema** — definir el hueco que el artefacto debe cubrir.
2. **Objetivos de la solución** — convertir ese problema en metas medibles.
3. **Diseño y desarrollo** — construir el artefacto (aquí, el clasificador de atributos).
4. **Demostración** — mostrar que el artefacto funciona en un caso controlado.
5. **Evaluación** — medir en qué grado cumple los objetivos, con rigor y evidencia.
6. **Comunicación** — publicar el problema, el artefacto y su utilidad verificada.

La evaluación exige que **el criterio de éxito sea observable y medible**. Por eso el objetivo general («reconocer el tipo, color y estilo de una prenda») se traduce en un requisito operativo: un valor numérico que se puede calcular, repetir y auditar.

### 1.2. Los tres ciclos de rigor

Hevner y colaboradores estructuran la investigación en tres ciclos que la evaluación conecta:

- **Ciclo de relevancia:** conecta el problema real del entorno (describir prendas a partir de fotografías) con la investigación. Define *qué* es útil medir.
- **Ciclo de rigor:** conecta el artefacto con la base de conocimiento (teoría de clasificación, métricas, validación experimental). Define *cómo* medirlo correctamente.
- **Ciclo de diseño:** alterna construcción y evaluación del artefacto. Cada evaluación alimenta una nueva versión.

En el método descrito en este proyecto, el ciclo de diseño queda documentado por la **comparación de estados del entrenamiento** (checkpoints), mientras el ciclo de rigor queda garantizado por **condiciones de control** y **fórmulas explícitas** (secciones 5 y 7).

### 1.3. Evaluación del artefacto frente a evaluación del proceso

Hay que distinguir dos objetos de evaluación distintos:

| Objeto | Pregunta que responde |
|---|---|
| **Artefacto (modelo)** | ¿Con qué precisión reconoce tipo, color y estilo en imágenes no vistas? |
| **Proceso (entrenamiento)** | ¿Mejoró o empeoró el artefacto entre dos estados? ¿Fue eficiente el entrenamiento? |

Ambos se apoyan en las **mismas métricas**, pero el segundo es **comparativo**: se evalúan dos o más versiones del mismo modelo sobre el mismo conjunto, y se interpreta la diferencia entre sus métricas. El primero es **absoluto**: se contrasta una única versión contra un umbral de aceptación.

---

## 2. El problema de evaluación como clasificación supervisada

### 2.1. Etiqueta de referencia y predicción

Toda evaluación supervisada compara dos objetos por cada muestra:

- **Etiqueta de referencia (verdad de terreno, *ground truth*):** el valor anotado que se asume correcto. En este proyecto las etiquetas proceden de modelos previos (IA de etiquetado) y de una revisión manual limitada; esta procedencia es una **limitación de validez**, no un error del método.
- **Predicción:** el valor que produce el modelo a evaluar.

La medición del desempeño es, por tanto, una **función de concordancia** entre predicciones y referencias. Cambia la métrica, no el principio.

### 2.2. Dos naturalezas de tarea

El modelo resuelve tres tareas de naturaleza distinta, lo que obliga a usar métricas distintas:

- **Tipo de prenda — clasificación multiclase:** cada imagen pertenece a **exactamente una** clase dentro de un vocabulario cerrado (blusa, pantalón, falda, …). La salida es una distribución de probabilidad normalizada (softmax) y la decisión es la clase de mayor probabilidad.
- **Color y estilo — clasificación multietiqueta:** una prenda puede llevar **varias** etiquetas a la vez (por ejemplo, color {azul, blanco}). La salida son probabilidades independientes por etiqueta (sigmoide) y la decisión es el conjunto de etiquetas cuya probabilidad supera un umbral.

Confundir ambas naturalezas produce métricas sin sentido (por ejemplo, exigir una única clase ganadora en color, que es multietiqueta).

---

## 3. Matriz de confusión y métricas elementales

### 3.1. Verdaderos y falsos

Para una decisión binaria (la etiqueta está presente o no) se definen cuatro conteos:

| | Predicción positiva | Predicción negativa |
|---|---|---|
| **Real positiva** | Verdadero positivo (VP) | Falso negativo (FN) |
| **Real negativa** | Falso positivo (FP) | Verdadero negativo (VN) |

Todos los indicadores de esta sección se derivan de estos cuatro valores; la matriz de confusión multiclase y los conteos multietiqueta son generalizaciones directas.

### 3.2. Exactitud (accuracy)

Proporción de decisiones correctas:

$$
\text{Exactitud} = \frac{VP + VN}{VP + VN + FP + FN}
$$

En clasificación **multiclase** se simplifica a la diagonal de la matriz de confusión: la proporción de muestras cuya clase predicha coincide con la clase real. Es la métrica natural para el tipo de prenda.

**Limitación:** es engañosa con clases muy desbalanceadas. Por eso se complementa con precisión y recall por clase (apartado 3.3) y nunca se usa sola para las tareas multietiqueta.

### 3.3. Precisión, recall (sensibilidad) y F1

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

### 3.4. Micro y macro promedio

Al agregar métricas de muchas etiquetas (o clases) hay dos estrategias:

- **Micro promedio:** se suman primero todos los VP, FP y FN y se calcula la métrica **global** sobre esos totales. Pondera implícitamente por la frecuencia de cada etiqueta: las clases más frecuentes dominan el resultado.
- **Macro promedio:** se calcula la métrica **por etiqueta** y luego se promedian esos valores, dando a cada etiqueta el mismo peso, sin importar su frecuencia. Refleja mejor el comportamiento en clases raras.

La elección entre micro y macro es una **decisión de interpretación**: micro describe el rendimiento global sobre el volumen de datos; macro describe el rendimiento promedio sobre el vocabulario.

### 3.5. Matriz de confusión multiclase

Para una tarea de $K$ clases, la matriz $C \in \mathbb{Z}^{K \times K}$ acumula en $C_{ij}$ cuántas muestras de la clase real $i$ fueron predichas como clase $j$. La diagonal $C_{ii}$ contiene los aciertos. La exactitud multiclase es la suma de la diagonal dividida por el total, y cada fila permite derivar precisión y recall de esa clase.

---

## 4. Métricas para clasificación multietiqueta

### 4.1. La predicción como conjunto

En color y estilo, la predicción y la referencia son **conjuntos de etiquetas**: $P_i$ (predicho) y $R_i$ (real) para la imagen $i$. Toda la evaluación multietiqueta se reduce a comparar conjuntos.

### 4.2. Coincidencia exacta (subset accuracy)

Proporción de imágenes donde ambos conjuntos son idénticos:

$$
\text{Exacta} = \frac{\#\{i : P_i = R_i\}}{T}
$$

Es la métrica más estricta: un solo error de etiqueta invalida la imagen. Es útil como diagnóstico, pero **infravalora** el acierto parcial: acertar 3 de 4 colores cuenta igual que acertar 0.

### 4.3. Jaccard (intersección sobre unión)

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

## 5. El indicador compuesto: promedio macro de propiedades

### 5.1. Agregación de las tres tareas

El modelo produce tres indicadores parciales: exactitud de tipo, Jaccard de color y Jaccard de estilo. Para una única cifra resumen se usa la **media aritmética no ponderada**:

$$
\text{Macro} = \frac{\text{Exactitud}_{\text{tipo}} + \text{Jaccard}_{\text{color}} + \text{Jaccard}_{\text{estilo}}}{3}
$$

### 5.2. Igual ponderación

Cada propiedad pesa exactamente $1/3$, independientemente de su dificultad o del número de clases que tenga. Esta decisión responde a una **definición operacional** del éxito: el sistema se considera útil si, **en promedio**, las tres capacidades funcionan por igual. La alternativa —ponderar por número de etiquetas— favorecería artificialmente a color y estilo (que tienen muchas más etiquetas que las clases de tipo).

### 5.3. Interpretación y cuidado

- El macro es un **resumen**, no sustituye a las métricas por propiedad ni por etiqueta.
- Un macro alto puede ocultar el colapso de una propiedad concreta; por eso el informe siempre desagrega las tres componentes y, en el anexo, los valores por etiqueta.
- El criterio de aceptación se aplica **al macro**, no a cada propiedad individualmente: es posible cumplir el requisito con una propiedad por debajo del umbral si las otras lo compensan.

---

## 6. Diseño experimental de la evaluación

### 6.1. Unidad de análisis y muestra

- **Unidad de análisis:** cada imagen evaluada. En el diseño comparativo, la unidad secundaria es cada **versión de pesos (checkpoint)** sometida al mismo protocolo.
- **Muestra:** un conjunto fijo de imágenes **nunca usadas para entrenar ni para validar**. La muestra se mantiene constante entre evaluaciones para que las diferencias sean atribuibles al modelo y no a los datos.

### 6.2. Particiones y holdout

El reparto en tres conjuntos es la base del rigor:

- **Entrenamiento:** ajusta los pesos.
- **Validación:** selecciona hiperparámetros y decide el checkpoint sin tocar el test.
- **Prueba (test):** se usa **una sola vez**, al final, para declarar el desempeño.

Usar el test repetidamente para elegir el mejor modelo lo convierte en un segundo conjunto de validación y **invalida** la estimación del error (el modelo acaba «memorizando» la selección). Esta es una regla fundamental del método.

### 6.3. Fuga de información (data leakage)

La fuga ocurre cuando información del conjunto de prueba se filtra al entrenamiento o a la selección del modelo:

- Imágenes **duplicadas o casi duplicadas** entre particiones.
- Selección de hiperparámetros o del umbral usando el test.
- Normalización o vocabulario calculados sobre el test.

La prevención es una **condición de control** explícita: verificar el no solapamiento de imágenes entre particiones (por hash o similitud perceptual) y fijar el umbral a priori.

### 6.4. Comparar checkpoints frente a repetir la misma prueba

Son dos diseños distintos que no deben confundirse:

- **Comparación de checkpoints:** varía una sola variable (la versión de pesos) manteniendo todo lo demás constante. Responde a *«¿mejoró el entrenamiento?»*.
- **Repetición de la misma prueba:** ejecuta el mismo checkpoint varias veces en las mismas condiciones. Responde a *«¿es reproducible?»* y mide variabilidad instrumental (debería ser mínima en inferencia determinista).

El protocolo documenta qué variable cambia en cada caso; en la comparación solo debe cambiar el checkpoint y, si aplica, el tamaño del conjunto de entrenamiento declarado como factor.

---

## 7. Control, validez y reproducibilidad

### 7.1. Variables constantes y variables que cambian

La validez de una comparación exige separar:

- **Constantes:** imágenes, etiquetas de referencia, preprocesamiento, vocabulario de clases, umbral de decisión, código de evaluación, hardware y versión de las bibliotecas.
- **Variables de interés:** el checkpoint evaluado (y, si cambia, el volumen de entrenamiento).

Solo así las diferencias observadas en las métricas se atribuyen a la variable de interés.

### 7.2. Definición operacional

Cada métrica debe definirse de forma **operacional**: una fórmula exacta, sin ambigüedad, que cualquier tercero pueda aplicar y obtener el mismo número. Incluye:

- La fórmula matemática.
- La convención de casos especiales (por ejemplo, conjuntos vacíos en Jaccard).
- El umbral de decisión y su origen.
- La fuente de las etiquetas de referencia.

### 7.3. Trazabilidad

La trazabilidad garantiza que un resultado puede ligarse a sus insumos exactos:

- Identificador y **hash criptográfico (SHA-256)** del checkpoint y del manifiesto de imágenes.
- Registro de la versión de código y de los reportes de cada ejecución.
- Archivo de resultados por ejecución con fecha, incidencias y total de imágenes procesadas.

### 7.4. Tipos de validez

- **Validez interna:** ¿las diferencias observadas se deben al factor manipulado y no a variables ocultas? La protegen las condiciones de control y la separación de particiones.
- **Validez de constructo:** ¿la métrica mide lo que se quiere medir? La exactitud mide acierto de tipo; el Jaccard mide solapamiento de conjuntos; el macro mide desempeño global ponderado por propiedad.
- **Validez externa:** ¿hasta dónde se generaliza el resultado? Limitada al dominio de las imágenes (fotografías de catálogo) y a la procedencia de las etiquetas.

### 7.5. Limitación de validez de las etiquetas automáticas

Cuando la referencia no es una verdad de terreno validada por humanos, sino la salida de **otras IA**, la métrica mide **concordancia con esas anotaciones**, no exactitud frente a la realidad. Esta salvedad debe declararse: no descalifica el método, pero delimita qué se puede concluir.

---

## 8. Criterio de aceptación (requisito R11)

### 8.1. Formulación verificable

Un requisito es evaluable solo si fija **qué magnitud**, **qué umbral** y **en qué condiciones**:

> El modelo debe alcanzar un **promedio macro ≥ 70 %** en el reconocimiento de tipo, color y estilo, medido sobre el conjunto de prueba fijo con las fórmulas y condiciones de control definidas.

### 8.2. Regla de decisión

- **Macro ≥ 70 %** → requisito **cumplido**.
- **Macro < 70 %** → requisito **no cumplido**; procede diagnóstico por propiedad y por etiqueta.

### 8.3. Interpretación correcta

El requisito se refiere al **agregado**. No implica que cada propiedad individual supere el 70 %, ni convierte el macro en una medida de «fiabilidad» del sistema: es un indicador de **concordancia con las etiquetas de referencia** bajo un protocolo declarado.

---

## 9. Diagnóstico cuando el requisito no se cumple

La evaluación no termina en la cifra; la cifra orienta el diagnóstico:

1. **Desagregar el macro** en exactitud de tipo, Jaccard de color y Jaccard de estilo para localizar la propiedad que falla.
2. **Bajar a nivel de etiqueta** (precisión, recall, F1 por clase) para detectar colapso en clases concretas o en clases raras.
3. **Contrastar coincidencia exacta con Jaccard:** si la exacta es muy baja y el Jaccard alto, el modelo acierta parcialmente (sobrerreporte o subreporte de etiquetas); si ambos son bajos, el modelo no distingue la propiedad.
4. **Revisar desbalance y solapamiento** entre particiones: clases con pocos ejemplos y casi duplicados sesgan las métricas.
5. **Comparar checkpoints** para distinguir un problema de configuración de un límite del modelo.

---

## 10. Referencias

- Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). Design Science in Information Systems Research. *MIS Quarterly*, 28(1), 75–105.
- Peffers, K., Tuunanen, T., Rothenberger, M. A., & Chatterjee, S. (2007). A Design Science Research Methodology for Information Systems Research. *Journal of Management Information Systems*, 24(3), 45–77.
- Sokolova, M., & Lapalme, G. (2009). A systematic analysis of performance measures for classification tasks. *Information Processing & Management*, 45(4), 427–437.
- Tsoumakas, G., & Katakis, I. (2007). Multi-Label Classification: An Overview. *International Journal of Data Warehousing and Mining*, 3(3), 1–13.
- Wu, X.-Z., & Zhou, Z.-H. (2017). A unified view of multi-label performance measures. *Proceedings of the 34th International Conference on Machine Learning* (ICML).
- Bishop, C. M. (2006). *Pattern Recognition and Machine Learning*. Springer.
- Howard, A., et al. (2019). Searching for MobileNetV3. *Proceedings of the IEEE/CVF International Conference on Computer Vision* (ICCV).
