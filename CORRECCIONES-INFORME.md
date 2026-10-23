# Correcciones del informe (observaciones 4, 5 y 6)

Todas las cifras de este documento se midieron el 22-10-2026 con consultas de solo lectura sobre `dataset/metadata.sqlite`, el registro `registro_entrenamiento.sqlite` y el checkpoint compartido (`mobilenetv3-small-best.pt`, época 15, ejecución `20261018-020637`). La evaluación se repite con [EVALUACION-ENTRENAMIENTO.md](./EVALUACION-ENTRENAMIENTO.md). Lo que no se pudo medir desde este repositorio está marcado como **pendiente**.

## Datos vigentes (22-10-2026, después de la depuración de duplicados)

| Dato | Valor |
|---|---:|
| Prendas aprobadas y aptas para entrenamiento (cada una con 1 imagen) | **14.456** |
| Entrenamiento (train) | 11.616 (80,4 %) |
| Validación (val) | 1.416 (9,8 %) |
| Prueba (test) | 1.424 (9,9 %) |
| Test con color y estilo anotados | 1.418 |
| Prendas pendientes de revisión (no se usan) | 7.412 |
| Prendas rechazadas (duplicados y descartes; no se usan) | 17.007 |
| Checkpoint evaluado | `mobilenetv3-small-best.pt`, época 15, SHA-256 `79407f55…dcb35c` |
| Dispositivo y umbral | CPU; umbral multi-etiqueta 0,5 |

| Propiedad | Aciertos | Exacta | Parcial (Jaccard) | F1 micro |
|---|---:|---:|---:|---:|
| Tipo de prenda | 1.352 / 1.424 | **94,94 %** | — | — |
| Color | 764 / 1.418 | 53,88 % | **68,42 %** | 72,80 % |
| Estilo | 674 / 1.418 | 47,53 % | **69,21 %** | 76,49 % |
| **Promedio macro** | | | **77,52 %** | |

La evaluación se repitió el 22-10-2026 después de borrar 4.039 duplicados y dio resultados idénticos (incluidas las tablas por clase) porque el test no cambió. El informe detallado está en `modelo-ia/evaluaciones/evaluacion_propiedades_test_20261022.json`.

## 0. Cifras del informe que no coinciden con los datos

| Dónde | El informe dice | Dato verificado | Acción |
|---|---|---|---|
| 5.3 | 17,000 imágenes de entrenamiento | 14.456 imágenes elegibles: 11.616 train, 1.416 val, 1.424 test. Al entrenar el checkpoint había 15.419 (12.379 / 1.511 / 1.529), antes de depurar duplicados | Reportar ambas cifras y aclarar qué conjunto se usó |
| 5.3 | 1,400 fotografías de prueba | 1.424 (1.418 con color y estilo anotados) | Corregir |
| 5.3, Tabla 6 | 77.50 % de promedio macro | (94,94 + 68,42 + 69,21) / 3 = **77,52 %** | Corregir y usar dos decimales en toda la tabla |
| 5.1, R11 | Criterio del 70 %, "Cumplido" | Con coincidencia exacta, color 53,88 % y estilo 47,53 % están **por debajo** de 70 %. Solo el macro con Jaccard (77,52 %) lo supera | Definir en la Tabla 2 qué métrica es el criterio y presentar ambas (ver 4.4) |
| 1.3, 1.5, 5.4 | "MovileNetV3", "MovilNetV3"; frase suelta "y MobileNetV3-Small." | — | Corregir ortografía y redacción |

## Observación 4: validación del clasificador (9/10)

### 4.1 Dataset y procedimiento de partición

**Fuentes (14.456 imágenes elegibles).** Las tres fuentes públicas declaradas con uso comercial: Apparel Images Gallery (11.255, 77,9 %), clothing-dataset-small (2.511) y clothing-dataset (690).

**Partición.** Se asigna al importar, por imagen, con una regla determinista:

1. Si la ruta de origen contiene una carpeta `train`, `val`/`validation` o `test`, se hereda (clothing-small).
2. Si no, se usa el SHA-256: los primeros 8 caracteres hexadecimales del hash, interpretados como número, módulo 100; menos de 80 es train, menos de 90 es val y el resto es test. Esto cubre AIG y clothing-dataset.

La proporción resultante es 80,4 % / 9,8 % / 9,9 %. Cada prenda tiene una sola imagen, por lo que la partición por prenda y por imagen es la misma. Solo se usan prendas con `estado_revision = aprobado` y `apta_para_entrenamiento = 1`. El test no se usó para elegir checkpoints ni umbrales (el umbral 0,5 es fijo). Según el registro de entrenamiento, las 1.424 imágenes de test, las 11.616 de train y las 1.416 de val actuales estaban en esas mismas particiones cuando se entrenó el checkpoint; ninguna cambió de conjunto. Desde entonces se descartaron 963 imágenes del conjunto original (763 de train, 95 de val y 105 de test) al depurar duplicados.

**Distribución por clase de tipo de prenda:**

| Tipo | Train | Val | Test | Total | % del total |
|---|---:|---:|---:|---:|---:|
| blusa | 5.044 | 630 | 663 | 6.337 | 43,8 |
| camisa | 1.300 | 144 | 106 | 1.550 | 10,7 |
| vestido | 1.220 | 147 | 166 | 1.533 | 10,6 |
| pantalón | 1.176 | 144 | 131 | 1.451 | 10,0 |
| abrigo | 893 | 108 | 103 | 1.104 | 7,6 |
| chaqueta | 879 | 104 | 114 | 1.097 | 7,6 |
| short | 538 | 64 | 71 | 673 | 4,7 |
| suéter | 294 | 35 | 42 | 371 | 2,6 |
| falda | 272 | 40 | 28 | 340 | 2,4 |

Hay un desbalance marcado: blusa pesa 43,8 % y falda 2,4 %. El entrenamiento compensó con pérdida ponderada por clase (raíz cuadrada de la frecuencia inversa). Falda (28) y suéter (42) tienen pocos ejemplos de prueba, por lo que sus métricas son inestables.

### 4.2 Calidad e independencia de las etiquetas

| Propiedad | Origen de la etiqueta | Independiente de NIM y DeepSeek |
|---|---|---|
| Tipo de prenda | Clase de la fuente pública, convertida con `sources.json`. La IA solo valida que la imagen corresponda a esa clase y descarta las que no | Sí, con un sesgo de selección: solo quedan imágenes que la IA aceptó |
| Color y estilo | Generados por NVIDIA NIM o DeepSeek | **No**: no existe una referencia humana independiente |

Procedencia de las 14.456 descripciones aprobadas:

| Proveedor | Train | Val | Test | Total |
|---|---:|---:|---:|---:|
| DeepSeek (`deepseek-flash`) | 10.865 | 1.390 | 1.240 | 13.495 (93,4 %) |
| NVIDIA NIM (varios modelos) | 751 | 26 | 184 | 961 (6,6 %) |

La proporción de NIM no es uniforme: 12,9 % del test frente a 6,5 % de train y 1,8 % de val. Debe declararse porque el test tiene una mezcla de anotadores distinta de la de entrenamiento.

**Revisión humana.** Las 14.456 descripciones figuran como `aprobado`, pero el procedimiento documentado del curador aprueba en bloque (`approve-generated`) tras revisar una muestra. El informe menciona una muestra aleatoria de 50 imágenes **sin reportar su tasa de error**. Pendiente: cuantificarla (aciertos por propiedad sobre esas 50 imágenes).

**Acuerdo entre los dos proveedores (indicador de ruido de etiquetas).** En 349 imágenes aceptadas por ambos:

| Propiedad | Coincidencia exacta | Jaccard medio |
|---|---:|---:|
| Color | 224 / 349 = 64,2 % | 75,7 % |
| Estilo | 195 / 349 = 55,9 % | 73,8 % |

Esta muestra no es representativa: incluye solo imágenes aceptadas por ambos, y los desacuerdos sobre aptitud quedan fuera. Aun así, indica que las etiquetas de color y estilo tienen un ruido propio de 25 % aproximadamente en Jaccard. El 68,4 % y el 69,2 % del modelo deben leerse como **concordancia con anotaciones generadas por IA**, no como exactitud frente a la verdad.

### 4.3 Posible fuga entre particiones y análisis de sensibilidad

El SHA-256 no detecta fotos casi idénticas. Con la huella perceptual dHash (distancia de Hamming) se encontró que parte del test tiene un casi duplicado en train:

| Distancia dHash | Test con casi duplicado en train | Val con casi duplicado en train |
|---|---:|---:|
| 0 (idénticas) | 41 / 1.424 (2,9 %) | 36 / 1.416 |
| ≤ 2 | 77 / 1.424 (5,4 %) | 79 / 1.416 |
| ≤ 4 | 172 / 1.424 (12,1 %) | 174 / 1.416 |

Se reevaluó el mismo checkpoint excluyendo esas imágenes del test:

| Test evaluado | n | Tipo | Color exacta / Jaccard | Estilo exacta / Jaccard | **Macro** |
|---|---:|---:|---:|---:|---:|
| Completo | 1.424 | 94,94 | 53,88 / 68,42 | 47,53 / 69,21 | **77,52** |
| Sin casi duplicados (≤ 2) | 1.347 | 94,65 | 52,80 / 67,76 | 46,46 / 68,46 | **76,96** |
| Sin casi duplicados (≤ 4) | 1.252 | 94,33 | 52,25 / 67,32 | 45,35 / 67,92 | **76,52** |

El efecto es pequeño (como máximo 1 punto del macro). Es una cota conservadora: de los 77 pares con distancia ≤ 2, 76 pertenecen a grupos que un revisor marcó en la interfaz como "No son duplicadas" (el revisor consideró que las fotos eran distintas), y solo 1 no pertenece a un grupo revisado. El dHash de 64 bits es una huella gruesa, de modo que parte de esos 77 no son repeticiones reales. Tras la depuración del 22-10-2026 quedan 20 grupos pendientes de revisión manual (encadenamientos de imágenes dispares, no purgados a propósito) y 404 descartados como no duplicados.

### 4.4 Evaluación por clase (test, 1.424 imágenes)

Resumen por propiedad. Se reportan los dos criterios para que la elección de métrica sea transparente. La coincidencia exacta es la más estricta; Jaccard da crédito parcial.

| Propiedad | n | Exacta | Parcial (Jaccard) | F1 micro |
|---|---:|---:|---:|---:|
| Tipo | 1.424 | 94,94 % | — | — |
| Color | 1.418 | 53,88 % | 68,42 % | 72,80 % |
| Estilo | 1.418 | 47,53 % | 69,21 % | 76,49 % |

**Tipo de prenda:**

| Tipo | Soporte | Precisión % | Recall % | F1 % |
|---|---:|---:|---:|---:|
| abrigo | 103 | 93,00 | 90,29 | 91,63 |
| blusa | 663 | 96,42 | 97,59 | 97,00 |
| camisa | 106 | 92,79 | 97,17 | 94,93 |
| chaqueta | 114 | 94,74 | 94,74 | 94,74 |
| falda | 28 | 89,66 | 92,86 | 91,23 |
| pantalón | 131 | 98,46 | 97,71 | 98,08 |
| short | 71 | 95,65 | 92,96 | 94,29 |
| suéter | 42 | 93,33 | 66,67 | 77,78 |
| vestido | 166 | 90,00 | 92,17 | 91,07 |

El suéter es la clase más débil (recall 66,7 %): 8 de 42 se predicen como blusa. Vestido y blusa se confunden entre sí (10 vestidos predichos como blusa).

**Color (soporte > 0):**

| Etiqueta | Soporte | Precisión % | Recall % | F1 % |
|---|---:|---:|---:|---:|
| amarillo | 96 | 88,89 | 66,67 | 76,19 |
| azul | 290 | 86,38 | 76,55 | 81,17 |
| beige | 102 | 72,58 | 44,12 | 54,88 |
| blanco | 351 | 72,15 | 77,49 | 74,73 |
| café | 52 | 75,00 | 34,62 | 47,37 |
| gris | 195 | 85,59 | 51,79 | 64,54 |
| morado | 67 | 79,17 | 56,72 | 66,09 |
| multicolor | 66 | 68,42 | 39,39 | 50,00 |
| naranja | 37 | 70,00 | 18,92 | 29,79 |
| negro | 428 | 80,53 | 78,27 | 79,38 |
| rojo | 173 | 87,10 | 78,03 | 82,32 |
| rosa | 143 | 72,12 | 52,45 | 60,73 |
| verde | 169 | 89,17 | 63,31 | 74,05 |

**Estilo (soporte > 0):**

| Etiqueta | Soporte | Precisión % | Recall % | F1 % |
|---|---:|---:|---:|---:|
| casual | 1.103 | 88,66 | 91,48 | 90,05 |
| elegante | 583 | 70,41 | 84,91 | 76,98 |
| deportivo | 157 | 91,67 | 63,06 | 74,72 |
| verano | 156 | 73,61 | 33,97 | 46,49 |
| fiesta | 103 | 70,83 | 33,01 | 45,03 |
| bohemio | 86 | 65,12 | 32,56 | 43,41 |
| formal | 161 | 54,74 | 32,30 | 40,62 |
| invierno | 41 | 71,43 | 24,39 | 36,36 |
| infantil | 13 | 75,00 | 23,08 | 35,29 |
| entretiempo | 40 | 60,00 | 15,00 | 24,00 |

En color y estilo la precisión supera con claridad al recall: el modelo es conservador con las etiquetas poco frecuentes. Colores como naranja (recall 18,9 %) y estilos como entretiempo (15,0 %) casi no se detectan.

### 4.5 Texto propuesto para la sección 5.3

> El clasificador se entrenó con imágenes de tres fuentes públicas de uso comercial (Apparel Images Gallery, clothing-dataset y clothing-dataset-small). Tras la depuración de duplicados quedaron 14.456 imágenes aprobadas: 11.616 para entrenamiento, 1.416 para validación y 1.424 para prueba (80,4 %, 9,8 % y 9,9 %). La partición se asignó al importar cada imagen: se heredó la carpeta de origen cuando existía y, en los demás casos, se derivó de forma determinista del hash SHA-256 de la imagen. Cada prenda tiene una sola fotografía, por lo que no hay fuga por prendas repetidas. El conjunto está desbalanceado (blusa 43,8 %; falda 2,4 %); el entrenamiento aplicó pérdida ponderada por clase.
>
> La etiqueta de tipo proviene de la clase de la fuente pública; NVIDIA NIM y DeepSeek solo validaron que la imagen correspondiera a esa clase. Las etiquetas de color y estilo fueron generadas por NVIDIA NIM (6,6 %) y DeepSeek (93,4 %), por lo que no son independientes de dichos servicios y la evaluación mide la concordancia del modelo con anotaciones asistidas por IA, no con una referencia humana. En 349 imágenes anotadas por ambos proveedores, su coincidencia fue de 75,7 % (color) y 73,8 % (estilo) en Jaccard, lo que indica el ruido de las etiquetas. [Agregar aquí la tasa de error de la revisión manual de 50 imágenes.]
>
> El 5,4 % de las imágenes de prueba tiene un casi duplicado en entrenamiento (dHash ≤ 2). Al excluirlas, el promedio macro baja de 77,52 % a 76,96 %. En la prueba completa (1.424 imágenes) se obtuvo una exactitud de tipo de 94,94 %; para color y estilo, coincidencia exacta de 53,88 % y 47,53 %, y coincidencia parcial (Jaccard) de 68,42 % y 69,21 %. El promedio macro de las tres propiedades es 77,52 %. La Tabla 6 y las Tablas 6a a 6c presentan los resultados por clase.

### 4.6 Diseño de la prueba de validación

**Objetivo.** Medir qué porcentaje de las propiedades de una prenda (tipo, color y estilo) reconoce correctamente el clasificador en fotografías que no usó para entrenar.

**Población y muestra.** Prendas aprobadas, aptas y con archivo presente. El conjunto de prueba contiene 1.424 imágenes (una por prenda), asignadas antes de entrenar y sin uso en la elección del modelo; en 1.418 hay color y estilo anotados y solo esas cuentan para esas dos propiedades. No se muestrea: se evalúa el test completo.

**Instrumento.** `utilidades-entrenamiento/evaluate_properties.py`: carga el checkpoint en modo inferencia (CPU), calcula las predicciones y guarda un JSON con fecha, época, SHA-256 de la base de datos y métricas por clase. No actualiza pesos.

**Regla de predicción.** Tipo: la clase de mayor probabilidad (*softmax*). Color y estilo: se incluyen las etiquetas cuya probabilidad (*sigmoide*) es ≥ 0,5.

**Cálculos.** Con $T$ = imágenes evaluadas, $P_i$ = conjunto predicho y $R_i$ = conjunto real de la imagen $i$:

- Tipo: $\text{Exactitud} = \dfrac{\text{tipos correctos}}{T} = \dfrac{1.352}{1.424} = 94{,}94\,\%$
- Coincidencia exacta (color o estilo): $\dfrac{\#\{i : P_i = R_i\}}{T}$; color $764/1.418 = 53{,}88\,\%$; estilo $674/1.418 = 47{,}53\,\%$.
- Coincidencia parcial (Jaccard): $J = \dfrac{1}{T}\sum_i \dfrac{|P_i \cap R_i|}{|P_i \cup R_i|}$, con $J_i = 1$ si ambos conjuntos están vacíos. Color $68{,}42\,\%$; estilo $69{,}21\,\%$.
- Promedio macro: $\dfrac{94{,}94 + 68{,}42 + 69{,}21}{3} = 77{,}52\,\%$ (cada propiedad pesa un tercio).
- Precisión, *recall* y F1 por etiqueta: $P=\dfrac{TP}{TP+FP}$, $R=\dfrac{TP}{TP+FN}$, $F_1=\dfrac{2PR}{P+R}$; el F1 micro suma TP, FP y FN de todas las etiquetas.

**Ejemplo de Jaccard.** Si la etiqueta real de color es {azul} y el modelo predice {azul, blanco}, la intersección es 1 y la unión es 2, así que $J_i = 0{,}5$ (la exacta daría 0). Si predice {azul} da 1; si predice {rojo}, 0.

**Criterio de aceptación propuesto (R11).** El promedio macro (Jaccard) debe ser ≥ 70 %. Resultado: 77,52 %, cumple. Como criterio complementario y más estricto, ninguna propiedad debe quedar por debajo de 70 % con coincidencia exacta; no cumple en color (53,88 %) ni estilo (47,53 %). Fijar y justificar en la Tabla 2 cuál de los dos es el criterio oficial.

**Reproducibilidad.** Misma semilla de partición (derivada del hash de cada imagen), umbral fijo 0,5, checkpoint identificado por SHA-256 y base de datos identificada por SHA-256 en cada informe.

**Comando.**

```bash
cd utilidades-entrenamiento
docker compose run --rm --no-deps --entrypoint python train \
  /app/evaluate_properties.py \
  --checkpoint /app/modelos-compartidos/mobilenetv3-small-best.pt \
  --split test --device cpu \
  --output /app/modelo-ia/evaluaciones/evaluacion_propiedades_test.json
```

**Amenazas a la validez (a declarar).**

1. Las etiquetas de color y estilo vienen de IA, no de una referencia humana independiente (4.2).
2. Desbalance de clases y pocos ejemplos de test en falda (28) y suéter (42).
3. Posible solapamiento por fotos casi idénticas entre train y test, con impacto acotado (4.3).
4. Distinta mezcla de anotadores en test (12,9 % NIM) que en train (6,5 %).
5. Las imágenes proceden de catálogos públicos; el rendimiento con fotos reales de una persona vistiendo la prenda no se midió.
6. El test pertenece a la misma distribución que el entrenamiento (mismas tres fuentes).

## Observación 5: alcance de MobileNetV3-Small (9/10)

### Hechos verificables

| Aspecto | Dónde se hizo | Evidencia |
|---|---|---|
| Entrenamiento | Equipo independiente de la nube: Docker con PyTorch 2.5.1 sobre CPU (Intel i7-8750H, 15 GiB RAM, Ubuntu 24.04). La RTX 2060 de ese equipo no estaba disponible (CUDA no detectada) | Registro de ejecuciones en `modelo-ia/runs/` y salida de `train status` |
| Evaluación | El mismo equipo, en CPU, con `evaluate_properties.py` | JSON en `modelo-ia/evaluaciones/` |
| Curación del dataset | Mismo equipo (dashboard `127.0.0.1:8787`), con llamadas remotas a NVIDIA NIM y DeepSeek | Tabla `analisis_imagen` |
| Ejecución en OpenStack/Kubernetes | **Sin evidencia en el repositorio**: no hay despliegue del clasificador en `k8s-vton`, ni en una VM de OpenStack, ni métricas de Prometheus asociadas | — |

El equipo medido se identifica como `osanode-node4`, pero su hardware no coincide con el de `osa-node4` en la Tabla 9 (Ryzen 5 3550H, 16 GB). **Pendiente:** confirmar si es uno de los cinco nodos de la nube. Si no lo es, el informe debe decir expresamente que el entrenamiento se hizo fuera de la infraestructura evaluada.

### Texto propuesto (reemplaza o ajusta 1.3, 1.5, 2.2 y 5.4)

**1.3, última frase del primer párrafo.** El caso de estudio es la prueba virtual de prendas de vestir mediante el modelo FASHN VTON v1.5, desplegado sobre la nube privada; como componente complementario se desarrolló y evaluó, fuera de la nube, un clasificador MobileNetV3-Small de propiedades de prendas.

**1.5, alcance (inciso i).** (i) El entrenamiento y la evaluación de un clasificador basado en MobileNetV3-Small para reconocer el tipo, el color y el estilo de prendas de vestir, realizados en un equipo independiente de la nube privada.

**1.5, fuera del alcance.** Quedan fuera del alcance la adaptación (*fine-tuning*) del modelo VTON, la evaluación de su calidad visual, la medición del beneficio empresarial de la prueba virtual, la alta disponibilidad y el escalamiento a gran número de servidores, la documentación del entrenamiento de VTON y la ejecución del entrenamiento o de la inferencia de MobileNetV3-Small sobre la infraestructura OpenStack/Kubernetes.

**2.2, objetivo específico 4.** Integrar el modelo FASHN VTON v1.5 como caso de estudio sobre la nube privada, desplegándolo como un prototipo funcional compuesto por un servicio de inferencia expuesto mediante API, una interfaz web con cola de solicitudes y el registro de los metadatos de cada ejecución sobre la GPU dedicada; y desarrollar y evaluar, de forma independiente, un clasificador visual de prendas (MobileNetV3-Small), documentando su preparación de datos, entrenamiento y evaluación.

**5.4, Tabla 7, fila OE4.** Evidencia: `vton-api` y VTON Studio operativos sobre `k8s-vton`; clasificador MobileNetV3-Small entrenado y evaluado fuera de la nube (sección 5.3).

**5.1, Tabla 3, R11.** Requisito: obtener un resultado de al menos 70 % en el reconocimiento de propiedades de las prendas. Evidencia: evaluación sobre 1.424 imágenes de prueba, promedio macro 77,52 % (tipo 94,94 %, color 68,42 %, estilo 69,21 %, estos dos con Jaccard). Con coincidencia exacta, color (53,88 %) y estilo (47,53 %) no alcanzan 70 %. Estado: **Parcial**, o "Cumplido" si la Tabla 2 define de antemano el macro con Jaccard como criterio.

**Si el equipo prefiere integrarlo a la nube.** El repositorio incluye una API de inferencia en CPU (`utilidades-entrenamiento/compose.cpu-api.yaml`, endpoint `POST /v1/predict`). Para afirmar que corre en OpenStack habría que desplegarla en una VM o pod de la nube, repetir la evaluación allí y registrar latencia y consumo de CPU/RAM con Prometheus. Solo entonces se puede conservar la redacción original del objetivo 4.

## Observación 6: concurrencia (9/10)

### Situación actual

El informe declara R8 como "Cumplido" porque existe una cola y se observaron 3 solicitudes en cola con 126 s en total. Eso solo demuestra procesamiento serializado. Dividir 126 s entre 3 da unos 42 s por solicitud (coherente con los 40–50 s del flujo web), pero es un promedio **inferido**, no hay tiempos individuales, rendimiento (*throughput*) ni tasa de error. Esta prueba se ejecuta en la nube del equipo, por lo que **los resultados deben medirse allí**; la tabla siguiente queda sin valores a propósito.

### Protocolo propuesto

- **Variable:** usuarios simultáneos N = 1, 2 y 3.
- **Carga fija:** mismas imágenes de persona y prenda, 30 pasos, semilla 42, categoría `tops`.
- **Calentamiento:** una ejecución previa descartada, para excluir la carga del modelo en frío.
- **Repeticiones:** 5 por cada N, fijadas antes de medir.
- **Doble nivel:** (a) directo a `vton-api`, que mide el servicio sin la cola web; (b) a través de VTON Studio, que mide el flujo completo y el tiempo de espera en cola.
- **Registrar por solicitud:** hora de envío, hora de respuesta, código HTTP y tiempo de espera en cola (panel `/admin`).
- **Registrar por prueba:** duración total, solicitudes completadas, VRAM pico y utilización de GPU (DCGM), reinicios de pods.

### Criterios de aceptación (definirlos antes de medir)

| Criterio | Umbral propuesto |
|---|---|
| Tasa de éxito | 100 % de respuestas HTTP 200; ningún 5xx ni tiempo de espera agotado |
| Atención serializada | La última de N solicitudes termina en ≤ 1,25 × N × T1 (T1 = latencia con N = 1) |
| Rendimiento | ≥ 0,8 × el rendimiento con N = 1 |
| VRAM | Pico ≤ 90 % de 12.288 MiB (11.059 MiB) |
| Estabilidad | Cero reinicios de pods durante la prueba |

### Plantilla de resultados (completar con mediciones)

| N | Rep. | Latencia por solicitud (s) | Espera en cola (s) | Duración total (s) | Rendimiento (sol/min) | Errores | VRAM pico (MiB) |
|---|---:|---|---|---:|---:|---:|---:|
| 1 | 5 | por medir | por medir | por medir | por medir | por medir | por medir |
| 2 | 5 | por medir | por medir | por medir | por medir | por medir | por medir |
| 3 | 5 | por medir | por medir | por medir | por medir | por medir | por medir |

Hipótesis de referencia si la atención es estrictamente serial y T1 ≈ 42 s: tiempos de finalización de 42 s (N = 1), 42 y 84 s (N = 2) y 42, 84 y 126 s (N = 3). Es una expectativa derivada, no un resultado.

### Script de medición (ejecutar desde un equipo con acceso al servicio)

Los nombres de los campos de `POST /v1/tryon` no están en este repositorio; cópialos de `/docs` antes de ejecutar.

```python
import os, time, statistics
from concurrent.futures import ThreadPoolExecutor
import requests

URL = os.environ["VTON_URL"]            # p. ej. http://localhost:8080/v1/tryon
KEY = os.environ["VTON_API_KEY"]
PERSONA, PRENDA = "persona.jpg", "prenda.jpg"

def una_solicitud(_):
    inicio = time.perf_counter()
    with open(PERSONA, "rb") as p, open(PRENDA, "rb") as g:
        r = requests.post(URL, headers={"X-API-Key": KEY}, timeout=600,
                          files={"person_image": p, "garment_image": g},   # ajustar a /docs
                          data={"category": "tops", "num_timesteps": 30})  # ajustar a /docs
    return r.status_code, time.perf_counter() - inicio

una_solicitud(0)  # calentamiento descartado
for n in (1, 2, 3):
    for rep in range(5):
        inicio = time.perf_counter()
        with ThreadPoolExecutor(n) as pool:
            res = list(pool.map(una_solicitud, range(n)))
        total = time.perf_counter() - inicio
        tiempos = sorted(t for _, t in res)
        errores = sum(1 for c, _ in res if c != 200)
        print(n, rep, [round(t, 1) for t in tiempos], round(total, 1),
              round(n / total * 60, 2), errores)
```

### Texto propuesto para R8 mientras no existan las mediciones

R8, soportar solicitudes concurrentes. Evidencia: una solicitud a la vez por diseño; la cola absorbe la espera (3 solicitudes en cola completadas en 126 s, equivalente a unos 42 s por solicitud). Estado: **Parcial**; falta caracterizar latencia individual, rendimiento y tasa de error con 1, 2 y 3 usuarios (protocolo en este documento). Al completar la prueba, cambiar a "Cumplido" si se satisfacen los criterios de aceptación.

## Pendientes que solo el equipo puede resolver

1. Cuantificar el resultado de la revisión manual de 50 imágenes (por propiedad).
2. Confirmar si el equipo de entrenamiento pertenece a la nube y decidir entre mantener el clasificador fuera de ella o desplegarlo en OpenStack.
3. Medir la concurrencia con el protocolo anterior y completar la Tabla 5.
4. Decidir y fijar en la Tabla 2 la métrica del criterio R11 (exacta o Jaccard) y justificar la elección.
5. Opcional: revisar a mano los 273 grupos de duplicados pendientes y repetir el entrenamiento y la evaluación con el dataset depurado.

## Cómo reproducir las cifras

- Evaluación por propiedad: comando en [EVALUACION-ENTRENAMIENTO.md](./EVALUACION-ENTRENAMIENTO.md), con `--checkpoint /app/modelos-compartidos/mobilenetv3-small-best.pt`.
- Distribución por clase, procedencia de etiquetas, acuerdo NIM/DeepSeek y casi duplicados: consultas de solo lectura sobre `prenda`, `prenda_imagen`, `valor_propiedad_prenda`, `descripcion_prenda`, `analisis_imagen` e `imagen_huella`. No hay un script versionado para estos cálculos.
- La base de datos cambia cuando se importan, rechazan o depuran imágenes; cada JSON de evaluación guarda el SHA-256 de la base usada.
