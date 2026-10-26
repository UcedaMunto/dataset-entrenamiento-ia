# Diseño de prueba (DSR) — API de descripción de prendas

Prueba basada en la Tabla 6 del informe y en [`EVALUACION-ENTRENAMIENTO.md`](../EVALUACION-ENTRENAMIENTO.md). Metodología: **Design Science Research (DSR)**.

## 1. Problema y motivación
Medir si la API de descripción de prendas (MobileNetV3-Small, inferencia en CPU) reconoce **tipo, color y estilo** en fotografías que no usó para entrenar, y poder reproducir esa prueba en el **equipo de producción**, no solo en el nodo de entrenamiento.

## 2. Objetivos de la solución
- Reproducir la evaluación reportada: tipo **94,94 %**, color Jaccard **68,42 %**, estilo Jaccard **69,21 %**, macro **77,52 %**.
- Ejecutar la prueba mediante una API, sobre un conjunto portable versionado en Git.

## 3. Diseño y desarrollo (artefacto)
- **API de pruebas** (`test-api`, puerto 8082): servicio [`test_api.py`](../utilidades-entrenamiento/test_api.py).
- **Conjunto portable de test**: [`tests/imagenes-test/`](../tests/imagenes-test/) con 1.424 imágenes y `manifest.json` (etiquetas de referencia y SHA-256 de cada imagen).

## 4. Diseño de la prueba
- **Muestra:** 1.424 imágenes (una por prenda, split `test` fijo). 1.418 tienen color y estilo anotados; 6 no tienen color/estilo.
- **Instrumento:** `POST /test/run` en CPU. No entrena ni modifica pesos; guarda el SHA-256 del manifest como trazabilidad.
- **Predicción:** tipo = clase de mayor probabilidad; color y estilo = etiquetas con probabilidad ≥ 0,5.

## 5. Evaluación (métricas)
- **Tipo:** exactitud = tipos correctos / total.
- **Color y estilo:** coincidencia parcial (Jaccard) = media por imagen de |P∩R| / |P∪R| (1 si ambos vacíos).
- **Promedio macro:** media simple de tipo, color y estilo; cada propiedad pesa 1/3.
- **Criterio de aceptación (R11):** promedio macro **≥ 70 %**.

## 6. Demostración
```bash
docker compose up -d --build test-api
curl -X POST "http://127.0.0.1:8082/test/run?max_images=10"   # prueba de humo
curl -X POST "http://127.0.0.1:8082/test/run"                  # prueba completa
```
Resultado esperado (completo): tipo 94,94 %, color Jaccard 68,42 %, estilo Jaccard 69,21 %, macro 77,52 % (± tolerancia de implementación).

## 7. Comunicación
La prueba se considera satisfactoria si el macro es **≥ 70 %** y las métricas reproducen las del informe. El JSON de resultados se guarda en [`tests/resultados/`](../tests/resultados/) y este diseño queda como evidencia. Aplican las limitaciones conocidas: etiquetas de color/estilo generadas por IA, desbalance de clases y casi duplicados entre splits.
