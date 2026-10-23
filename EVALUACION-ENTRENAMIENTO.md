# Evaluación del clasificador (MobileNetV3-Small)

La revisión del 23-10-2026 contrastó estas cifras con los JSON locales existentes y el hash del checkpoint; no ejecutó una nueva evaluación completa. Véase [validación](docs/VALIDACION.md). La columna de entrenamiento del 22 de octubre es una comparación fechada, no necesariamente la última ejecución disponible.

## Diseño de la prueba

- **Objetivo:** medir qué porcentaje de las propiedades de una prenda (tipo, color y estilo) reconoce el modelo en fotografías que no usó para entrenar.
- **Muestra:** el conjunto de prueba completo, 1.424 imágenes (una por prenda); 1.418 tienen color y estilo anotados. La partición es fija (carpeta de origen o hash SHA-256) y el test no se usó para elegir checkpoint ni umbral (0,5 fijo). Dataset vigente (22-10-2026): 14.456 imágenes aprobadas, 11.616 train, 1.416 val y 1.424 test.
- **Instrumento:** `utilidades-entrenamiento/evaluate_properties.py`. Solo inferencia en CPU; no entrena ni modifica pesos. Guarda un JSON con el SHA-256 de la base de datos.
- **Predicción:** tipo = clase de mayor probabilidad; color y estilo = etiquetas con probabilidad ≥ 0,5.

## Cálculos

Con $T$ imágenes, $P_i$ el conjunto predicho y $R_i$ el real:

- **Tipo:** exactitud $=$ tipos correctos $/\,T$.
- **Color/estilo, exacta:** $\#\{i: P_i=R_i\}\,/\,T$.
- **Color/estilo, parcial (Jaccard):** $\frac{1}{T}\sum_i \frac{|P_i\cap R_i|}{|P_i\cup R_i|}$ (1 si ambos vacíos). Ejemplo: real {azul}, predicho {azul, blanco} da 0,5.
- **Promedio macro:** media simple de tipo, Jaccard de color y Jaccard de estilo (cada una pesa un tercio).
- **Criterio de aceptación (R11):** macro $\ge 70\,\%$.

## Reproducir

Desde `utilidades-entrenamiento/`:

```bash
docker compose run --rm --no-deps --entrypoint python train \
  /app/evaluate_properties.py \
  --checkpoint /app/modelos-compartidos/mobilenetv3-small-best.pt \
  --split test --device cpu \
  --output /app/modelo-ia/evaluaciones/evaluacion_propiedades_test.json
```

## Resultados (test, 1.424 imágenes, CPU, 22-10-2026)

| Propiedad | Checkpoint compartido (época 15) | Último entrenamiento `20261022-015119` (época 21) |
|---|---:|---:|
| Tipo, exactitud | 1.352 / 1.424 = **94,94 %** | 1.340 / 1.424 = **94,10 %** |
| Color, exacta | 764 / 1.418 = 53,88 % | 774 / 1.418 = 54,58 % |
| Color, Jaccard | **68,42 %** | **69,34 %** |
| Estilo, exacta | 674 / 1.418 = 47,53 % | 676 / 1.418 = 47,67 % |
| Estilo, Jaccard | **69,21 %** | **69,48 %** |
| **Promedio macro** | **77,52 %** | **77,64 %** |

El modelo reportado en el informe es el checkpoint compartido; la diferencia con ese entrenamiento es de 0,12 puntos porcentuales; no se ha realizado una prueba estadística para establecer su significancia. Clases más débiles (checkpoint compartido): suéter (recall 66,7 %), color naranja (18,9 %) y estilo entretiempo (15,0 %). Detalle por clase en `utilidades-entrenamiento/modelo-ia/evaluaciones/`.

## Limitaciones críticas

1. **Etiquetas no independientes:** color y estilo los generaron NVIDIA NIM (6,6 %) y DeepSeek (93,4 %); la prueba mide concordancia con anotaciones de IA, no con una referencia humana. El tipo viene de la clase de la fuente pública.
2. **Desbalance:** blusa 43,8 % y falda 2,4 %; falda (28) y suéter (42) tienen pocos ejemplos de prueba.
3. **Casi duplicados:** 77 imágenes de test (5,4 %) tienen una casi idéntica en train; al excluirlas el macro baja a 76,96 %.
4. **Exacta frente a parcial:** con coincidencia exacta, color y estilo quedan por debajo de 70 %; solo el macro con Jaccard supera el criterio.
5. **Dominio:** fotos de catálogos públicos, no de una persona vistiendo la prenda; esa condición no se midió.

Análisis ampliado y correcciones al informe: [CORRECCIONES-INFORME.md](./CORRECCIONES-INFORME.md).
