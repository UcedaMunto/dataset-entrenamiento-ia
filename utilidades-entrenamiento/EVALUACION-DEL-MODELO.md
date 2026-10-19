# Evaluación por propiedad

El script [`evaluate_properties.py`](./evaluate_properties.py) evalúa un checkpoint sin entrenarlo. Usa solo prendas aprobadas y aptas del split elegido. La métrica se calcula por imagen; `test` se reserva para el resultado final.

## Ejecutar

Desde `utilidades-entrenamiento/`:

```bash
docker compose run --rm --no-deps --entrypoint python train \
  /app/evaluate_properties.py \
  --checkpoint /app/modelos-compartidos/mobilenetv3-small-best.pt \
  --split test --device cpu \
  --output /app/modelo-ia/evaluaciones/evaluacion_propiedades_test.json
```

El proceso no actualiza pesos. `--split val` sirve para pruebas; no se debe escoger el modelo con métricas de `test`. El JSON incluye fecha, época del checkpoint, dispositivo y SHA-256 de SQLite.

## Qué significa el porcentaje

- **Tipo:** porcentaje de imágenes cuyo tipo predicho coincide con la etiqueta real.
- **Color y estilo, coincidencia exacta:** porcentaje de imágenes anotadas donde el conjunto completo de etiquetas predichas coincide con el real.
- **Color y estilo, coincidencia parcial (Jaccard):** por imagen calcula etiquetas correctas dividido por la unión de etiquetas reales y predichas; luego promedia los resultados. Una coincidencia parcial recibe crédito proporcional y una etiqueta extra reduce el puntaje. Si ambos conjuntos están vacíos, cuenta como coincidencia total.
- **Promedio macro de propiedades:** media aritmética sin ponderar de exactitud de tipo, Jaccard parcial de color y Jaccard parcial de estilo. Cada propiedad pesa un tercio, independientemente de su número de etiquetas o soporte; es un resumen, no sustituye las métricas individuales.
- **Precisión / recall / F1 micro:** miden aciertos, falsos positivos y propiedades omitidas; complementan la coincidencia exacta, que exige acertar todas las etiquetas de esa propiedad.
- Las etiquetas con soporte cero no tienen evaluación interpretable. Las métricas son por imagen, no por prenda agregada si hay varias fotografías de una misma prenda.

## Resultado del 19-10-2026

Checkpoint `20261018-020637`, mejor época 15; CPU; umbral multi-etiqueta `0,5`. Se evaluaron 1.424 imágenes test; color y estilo tenían etiquetas en 1.418.

| Propiedad | Aciertos exactos | Exacta | Parcial (Jaccard) | F1 micro |
|---|---:|---:|---:|---:|
| Tipo de prenda | 1.352 / 1.424 | **94,94 %** | — | — |
| Color | 764 / 1.418 | 53,88 % | **68,42 %** | 72,80 % |
| Estilo | 674 / 1.418 | 47,53 % | **69,21 %** | 76,49 % |

**Promedio macro de efectividad:** $(94,94 + 68,42 + 69,21) / 3 = \mathbf{77,52\%}$.

El promedio macro da el mismo peso a las tres propiedades, no a cada etiqueta ni a cada imagen; úsalo como cifra global y presenta también la tabla para mostrar las diferencias. El tipo se reconoce mejor que los conjuntos completos de color y estilo. Jaccard muestra el crédito parcial: en promedio, color alcanza 68,42 % y estilo 69,21 % de coincidencia por imagen. El F1 micro evalúa etiquetas agregadas, mientras Jaccard da el mismo peso a cada imagen. Las etiquetas de poco soporte requieren más ejemplos antes de sacar conclusiones.

El informe detallado quedó en `modelo-ia/evaluaciones/evaluacion_propiedades_test_20261019.json`. Esta medición usa el dataset posterior a la purga de duplicados; el SHA-256 exacto de la base está en ese JSON.