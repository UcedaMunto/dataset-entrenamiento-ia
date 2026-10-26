# README-PRUEBA — Cómo se hizo la prueba de la API de descripción de prendas

Documento de detalle (máximo dos páginas) de la prueba reportada en la Tabla 6 del informe y reproducida con la API de pruebas. La metodología sigue Design Science Research; el diseño de una página está en [`docs/DSR-PRUEBA-API.md`](docs/DSR-PRUEBA-API.md).

## 1. Objetivo y problema

Medir qué porcentaje de las propiedades de una prenda (**tipo, color y estilo**) reconoce el clasificador MobileNetV3-Small en fotografías que **no** usó para entrenar, y que esa medición pueda reproducirse en el equipo de producción y no solo en el nodo de entrenamiento.

## 2. Conjunto de datos y muestra

El modelo se construyó con un dataset de 17.000 imágenes, etiquetadas con ayuda de **NVIDIA NIM** (6,6 %) y **DeepSeek** (93,4 %). Tras la curación y aprobación quedaron **14.456 prendas aprobadas y aptas**, repartidas en una partición fija:

| Split | Prendas |
|---|---:|
| train | 11.616 |
| val | 1.416 |
| test | 1.424 |

La prueba usa el **split test completo: 1.424 imágenes** (una por prenda, en su mayoría fotografías de catálogos públicos). De ellas, **1.418** tienen color y estilo anotados; 6 no tienen color/estilo. El test no se usó para elegir checkpoint ni umbral (0,5 fijo). Para el equipo de producción, esas 1.424 imágenes y sus etiquetas de referencia se exportaron a [`tests/imagenes-test/`](tests/imagenes-test/) con un `manifest.json` que guarda el SHA-256 de cada imagen.

## 3. Instrumento y predicción

- **Nodo de entrenamiento:** [`utilidades-entrenamiento/evaluate_properties.py`](utilidades-entrenamiento/evaluate_properties.py), que lee `dataset/metadata.sqlite` y el checkpoint, infiere en CPU y no modifica pesos.
- **Equipo de producción:** [`utilidades-entrenamiento/test_api.py`](utilidades-entrenamiento/test_api.py), que ejecuta la misma prueba sobre `tests/imagenes-test/` mediante `POST /test/run`.
- **Predicción:** tipo = clase de mayor probabilidad (softmax/argmax); color y estilo = etiquetas con probabilidad (sigmoide) ≥ **0,5**.

## 4. Cálculos

Con `T` imágenes, `P_i` el conjunto predicho y `R_i` el conjunto real:

- **Tipo:** exactitud = tipos correctos / `T`.
- **Color y estilo — exacta:** `#{i : P_i = R_i} / T`.
- **Color y estilo — parcial (Jaccard):** `(1/T) · Σ |P_i ∩ R_i| / |P_i ∪ R_i|` (1 si ambos vacíos). Ejemplo: real {azul}, predicho {azul, blanco} → 0,5.
- **Promedio macro:** media simple de tipo, Jaccard de color y Jaccard de estilo; cada propiedad pesa 1/3.
- **Criterio de aceptación (R11):** promedio macro ≥ **70 %**.

## 5. Ejecución

```bash
# Nodo de entrenamiento (dataset completo)
docker compose -f utilidades-entrenamiento/docker-compose.yaml run --rm --no-deps \
  --entrypoint python train /app/evaluate_properties.py \
  --checkpoint /app/modelos-compartidos/mobilenetv3-small-best.pt \
  --split test --device cpu \
  --output /app/modelo-ia/evaluaciones/evaluacion_propiedades_test.json

# Equipo de producción (conjunto portable)
docker compose up -d --build test-api
curl -X POST "http://127.0.0.1:8082/test/run"
```

Ambas rutas guardan un JSON con el SHA-256 de la fuente de verdad (SQLite en el nodo, `manifest.json` en producción) para trazabilidad.

## 6. Resultados (test, CPU)

| Propiedad | Métrica | Checkpoint compartido (época 15) |
|---|---|---|
| Tipo | Exactitud | **94,94 %** (1.352 / 1.424) |
| Color | Exacta | 53,88 % (764 / 1.418) |
| Color | Jaccard parcial | **68,42 %** |
| Estilo | Exacta | 47,53 % (674 / 1.418) |
| Estilo | Jaccard parcial | **69,21 %** |
| **Promedio macro** | Media de las tres | **77,52 %** |

La API de pruebas reproduce estos valores de forma idéntica sobre `tests/imagenes-test/` (verificado el 26-10-2026).

## 7. Conclusión y limitaciones

El promedio macro de **77,52 %** supera el criterio R11 (≥ 70 %), por lo que la prueba se considera satisfactoria. Limitaciones a tener presentes:

1. **Etiquetas de IA:** color y estilo los generaron NVIDIA NIM y DeepSeek; la prueba mide concordancia con esas anotaciones, no con una referencia humana.
2. **Desbalance:** blusa 43,8 % y falda 2,4 % de la muestra de test; falda (28) y suéter (42) tienen pocos ejemplos.
3. **Casi duplicados:** 77 imágenes de test (5,4 %) tienen una casi idéntica en train; al excluirlas el macro baja a 76,96 %.
4. **Exacta frente a parcial:** con coincidencia exacta, color y estilo quedan por debajo de 70 %; solo el macro con Jaccard supera el criterio.
5. **Dominio:** fotos de catálogo, no de una persona vistiendo la prenda.
