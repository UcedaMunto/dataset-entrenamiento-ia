# Evaluación del entrenamiento

## Método

El evaluador independiente `utilidades-entrenamiento/evaluate_properties.py` carga un checkpoint existente en modo inferencia; no entrena ni modifica los pesos. Usa únicamente prendas aprobadas, aptas y con archivos presentes en el split elegido. Para el resultado final se usa `test`, que no debe emplearse para ajustar el modelo.

- **Tipo:** exactitud = tipos correctos / imágenes evaluadas.
- **Color y estilo:** coincidencia exacta requiere que el conjunto completo de etiquetas coincida. Jaccard parcial calcula, por imagen, intersección / unión entre etiquetas predichas y reales; después promedia los valores. Dos conjuntos vacíos cuentan como coincidencia total.
- **Promedio global:** media aritmética no ponderada de exactitud de tipo, Jaccard parcial de color y Jaccard parcial de estilo. Cada propiedad pesa un tercio; se informa junto con cada métrica para no ocultar diferencias.
- El script también calcula precisión, recall y F1 micro y por etiqueta. Etiquetas sin ejemplos anotados tienen soporte cero y no son interpretables.

## Reproducir el test

Desde `utilidades-entrenamiento/`, sobre la última ejecución:

```bash
docker compose run --rm --no-deps --entrypoint python train \
  /app/evaluate_properties.py \
  --checkpoint /app/modelo-ia/runs/20261019-003147/best.pt \
  --split test --device cpu \
  --output /app/modelo-ia/evaluaciones/evaluacion_propiedades_20261019-003147.json
```

## Resultado del último checkpoint

Ejecución `20261019-003147`, mejor checkpoint de la época 8. Evaluación CPU sobre 1.424 imágenes test; tipo tiene 1.424 etiquetas y color/estilo 1.418 muestras anotadas. Umbral multi-etiqueta: 0,5.

| Propiedad | Exacta | Coincidencia parcial | F1 micro |
|---|---:|---:|---:|
| Tipo | 1.341 / 1.424 = **94,17 %** | — | — |
| Color | 755 / 1.418 = **53,24 %** | Jaccard **67,10 %** | 71,68 % |
| Estilo | 659 / 1.418 = **46,47 %** | Jaccard **68,63 %** | 75,91 % |

**Promedio global:** $(94,17 + 67,10 + 68,63) / 3 = \mathbf{76,63\%}$.

El informe JSON completo conserva métricas por etiqueta y el hash de SQLite. Este test corresponde al dataset después de la purga de duplicados; al cambiar el dataset, debe generarse un nuevo resultado.

## Estado actual en 20 líneas

1. No hay entrenamiento activo; la última ejecución terminó correctamente.
2. Última ejecución: `20261019-003147`.
3. Arquitectura: MobileNetV3-Small multitarea.
4. Resolución: 224 × 224 píxeles; batch: 64.
5. Se continuó desde `20261018-192232`, checkpoint de época 10.
6. La continuación reinició optimizador y scheduler; no fue reanudación exacta.
7. Estrategia: ajuste fino completo en CPU, con hasta 10 épocas.
8. Se completaron las 10 épocas; no se activó parada temprana.
9. Mejor checkpoint de la ejecución: época 8.
10. Mejor pérdida de validación: 0,5635.
11. Pérdida de validación en época 10: 0,5648.
12. Dataset elegible actual: train 11.622, val 1.417 y test 1.424 imágenes.
13. Test de tipo: 1.341 aciertos de 1.424, exactitud 94,17 %.
14. Test de color: 1.418 muestras anotadas; coincidencia exacta 53,24 %.
15. Jaccard parcial de color: 67,10 %; F1 micro: 71,68 %.
16. Test de estilo: 1.418 muestras anotadas; coincidencia exacta 46,47 %.
17. Jaccard parcial de estilo: 68,63 %; F1 micro: 75,91 %.
18. Promedio macro de tipo, color-Jaccard y estilo-Jaccard: **76,63 %**.
19. Umbral de color/estilo: 0,5; el modelo no genera descripciones libres.
20. Informe detallado: `utilidades-entrenamiento/modelo-ia/evaluaciones/evaluacion_propiedades_20261019-003147.json`.