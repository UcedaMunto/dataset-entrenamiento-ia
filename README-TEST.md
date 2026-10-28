# README-TEST — Ejecutar la prueba de la API de descripción de prendas

Guía rápida de la prueba diseñada en [`docs/DSR-PRUEBA-API.md`](docs/DSR-PRUEBA-API.md). La prueba mide si la API de descripción de prendas (MobileNetV3-Small, CPU) reconoce **tipo, color y estilo** en imágenes que no usó para entrenar, y está pensada para ejecutarse en el **equipo de producción**, sin el dataset completo.

## Qué se necesita

- Docker con Compose.
- El checkpoint compartido (ya versionado en Git): `utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt`.
- El conjunto portable de test (ya versionado en Git): [`tests/imagenes-test/`](tests/imagenes-test/) con 1.424 imágenes y `manifest.json`.

## Arranque

```bash
docker compose up -d --build test-api
```

La API de pruebas queda en **http://127.0.0.1:8082/docs**.

## Ejecutar la prueba

```bash
# Prueba de humo (10 imágenes)
curl -X POST "http://127.0.0.1:8082/test/run?max_images=10"

# Prueba completa (1.424 imágenes)
curl -X POST "http://127.0.0.1:8082/test/run"
```

Los reportes quedan en `tests/resultados/reporte_*.json` y se listan con:

```bash
curl "http://127.0.0.1:8082/test/results"
```

Para obtener en un solo JSON toda la evidencia que requiere el informe y el Anexo G (correspondencia DSRM, R11, condiciones de control, fórmulas, conjunto de prueba, trazabilidad y matriz comparativa):

```bash
curl "http://127.0.0.1:8082/test/informe"
```

## Endpoints principales

| Método | Ruta | Uso |
|---|---|---|
| GET | `/health` | Estado, checkpoint y total del manifest |
| GET | `/test/design` | Resumen JSON del diseño DSR |
| GET | `/test/design/markdown` | Diseño DSR en Markdown |
| GET | `/test/manifest` | Clases y conteos del conjunto de test |
| GET | `/test/informe` | Evidencia completa para el informe y el Anexo G (DSRM, R11, fórmulas, matriz comparativa) |
| GET | `/test/images` | Lista paginada de imágenes y etiquetas |
| POST | `/test/run` | Ejecuta la prueba; `max_images` y `device` opcionales |
| GET | `/test/results` | Reportes guardados |
| GET | `/test/results/{run_id}` | Reporte completo |

## Resultado esperado (prueba completa)

| Propiedad | Métrica | Valor |
|---|---|---|
| Tipo de prenda | Exactitud | 94,94 % (1.352 / 1.424) |
| Color | Jaccard parcial | 68,42 % |
| Estilo | Jaccard parcial | 69,21 % |
| **Promedio macro** | Media de las tres | **77,52 %** |

**Criterio de aceptación (R11):** promedio macro ≥ 70 %. La prueba queda satisfecha con el checkpoint compartido (77,52 %).

El detalle de cómo se construyó y ejecutó la prueba está en [`README-PRUEBA.md`](README-PRUEBA.md).
