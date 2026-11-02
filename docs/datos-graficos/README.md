# Datos para gráficos del entrenamiento

CSV y JSON generados desde los `metrics.json` y las evaluaciones de los tres entrenamientos documentados (referencia `20261026-021300`, fallido `20261028-042931` y corregido `20261029-022656`).

## Archivos

| Archivo | Contenido |
|---|---|
| `validacion_por_epoca.csv` | Métricas de validación por época (63 filas = 20 + 15 + 28). |
| `resultados_test.csv` | Resultados del test portable de 1.424 imágenes por ejecución. |
| `datos_graficos.json` | Ambas fuentes en un único JSON. |
| `figuras_entrenamiento_APA7.html` | Informe HTML original con figuras y tablas. |
| `figuras_entrenamiento_APA7_corregido.html` | Informe HTML corregido según la auditoría del Anexo G (trazabilidad, procedencia, errores por clase, equivalencia y limitaciones). |

## Columnas de `validacion_por_epoca.csv`

`run_id`, `rol`, `epoch`, `train_loss`, `val_loss`, `tipo_accuracy`, `color_precision`, `color_recall`, `color_f1`, `estilo_precision`, `estilo_recall`, `estilo_f1`.

Los porcentajes están en escala **0–1** (multiplicar por 100 para %).

## Gráficos sugeridos

1. **Curvas de aprendizaje:** `val_loss` y `train_loss` frente a `epoch`, una línea por `run_id`.
2. **Evolución de tipo:** `tipo_accuracy` frente a `epoch`.
3. **Evolución de color:** `color_f1` (o `color_recall`) frente a `epoch`; evidencia el colapso del run fallido.
4. **Evolución de estilo:** `estilo_f1` frente a `epoch`.
5. **Barras comparativas:** `resultados_test.csv` — tipo, color Jaccard, estilo Jaccard y macro por ejecución, con la línea de referencia R11 en 70 %.

## Regenerar el informe HTML

El HTML corregido se genera con el script [`generar_informe_entrenamiento.py`](../../utilidades-entrenamiento/generar_informe_entrenamiento.py), que lee los datos crudos (`metrics.json`, `evaluaciones/*.json`, `registro_entrenamiento.sqlite`, `metadata.sqlite`) y deja un log con cada cálculo en `informe_entrenamiento.log`.

En el host:

```bash
python3 utilidades-entrenamiento/generar_informe_entrenamiento.py --output-dir docs/datos-graficos
```

En el contenedor Docker (misma salida, log en `informe_entrenamiento.log`):

```bash
docker run --rm --user 1000:1000 \
  -v "$PWD/utilidades-entrenamiento/modelo-ia:/app/modelo-ia" \
  -v "$PWD/utilidades-entrenamiento/modelos-compartidos:/app/modelos-compartidos:ro" \
  -v "$PWD/dataset:/app/dataset:ro" \
  -v "$PWD/docs/datos-graficos:/app/salida" \
  -v "$PWD/utilidades-entrenamiento/generar_informe_entrenamiento.py:/app/generar_informe_entrenamiento.py:ro" \
  --entrypoint python modelo-general-destilacion-curator:latest \
  /app/generar_informe_entrenamiento.py \
    --modelo-ia /app/modelo-ia \
    --modelos-compartidos /app/modelos-compartidos \
    --dataset-sqlite /app/dataset/metadata.sqlite \
    --output-dir /app/salida
```
