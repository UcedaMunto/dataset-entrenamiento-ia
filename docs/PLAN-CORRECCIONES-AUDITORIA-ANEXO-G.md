# Plan de correcciones — Auditoría Anexo G (01-11-2026)

Plan de trabajo para atender las 20 observaciones de la auditoría `Auditoria_Actualizada_Anexo_G_01-11-2026.xlsx` (Anexo G / MobileNetV3-Small). Objetivo: corregir lo corregible, generar los datos necesarios y, si se aprueba, reentrenar con los parámetros documentados para cerrar las observaciones que lo exigen.

**Estado de la auditoría:** 20 observaciones → 14 pendientes, 4 parciales, 2 por verificar. P1 (alta) = 11.

---

## 1. Clasificación de las observaciones

| ID | Prioridad | Tipo de corrección | Fase | ¿Requiere reentrenar? |
|---|---|---|---|---|
| AUD-026 | P1 | Datos (procedencia por fuente) | F2 | No |
| AUD-053 | P1 | Datos (hashes) | F2 | No |
| AUD-054 | P1 | Datos (separación de splits) | F2 | No |
| AUD-055 | P1 | Declaración (validez de etiquetas) | F3 | No |
| AUD-056 | P1 | Datos (matriz de ejecución) | F2 | No |
| AUD-007 | P1 | Editorial (síntesis 5.4) | F1 | No |
| G-002 | P1 | Editorial (fecha) | F1 | No |
| G-003 | P1 | Editorial (definición "desde cero") | F1 | No |
| G-006 | P1 | Datos (trazabilidad técnica) | F2 | No |
| G-007 | P1 | Declaración + opcional holdout | F3/F4 | **Sí (opción B)** |
| AUD-020 | P2 | Editorial (índice con folios) | F1 | No |
| AUD-068 | P2 | Datos (incertidumbre) + redacción | F2/F4 | **Sí (opción B)** |
| AUD-028 | P2 | Editorial (tipografía) | F1 | No |
| AUD-030 | P2 | Datos (línea de tiempo) | F2 | No |
| G-001 | P1 | Editorial (numeración) | F1 | No |
| G-004 | P2 | Editorial (licencias) | F1 | No |
| G-005 | P2 | Editorial (estilos de figuras) | F1 | No |
| G-008 | P2 | Datos (errores por clase) | F2 | No |
| G-009 | P2 | Editorial (organización) | F1 | No |
| G-010 | P2 | Datos (vínculo figura↔CSV) | F2 | No |

---

## 2. Fase 1 — Correcciones editoriales (manuales en Word, sin datos)

1. **AUD-020** — Generar índice con folios reales y navegación a encabezados; validar portada contra la guía UES.
2. **G-001** — Renumerar tablas consecutivamente: fuentes → G3, tratamientos → G4, resultados → G5 (o mover fuentes tras G4); actualizar todas las remisiones.
3. **G-002** — Cambiar fecha de portada de «25 de octubre» a «29 de octubre de 2026» o posterior; añadir control de versión y distinguir fecha del proyecto vs. fecha del informe de ensayos.
4. **G-003** — Sustituir «desde cero» por «ejecución independiente iniciada desde pesos preentrenados (ImageNet), sin reanudar un checkpoint previo»; reservar «desde cero» para pesos aleatorios. Los tres runs usan `pretrained=true`, `finetune=true`.
5. **G-004** — Renombrar la columna «Uso comercial y condiciones» por «Licencia y condiciones de uso aplicables al entrenamiento».
6. **G-005** — Unificar estilos `GCaptionNum`/`GCaptionTitle` y separar rótulos de imágenes en párrafos estables; regenerar lista de figuras.
7. **AUD-007** — Dejar en §5.4 solo la síntesis (metodología mínima + una tabla comparativa de 3 filas) y trasladar al Anexo G las 11 tablas por ejecución y las figuras de respaldo; renumerar tablas del cuerpo.
8. **AUD-028** — Corregir «MovileNetV3» → «MobileNetV3-Small» en §7; homogeneizar «run id», «fine-tuning» y denominaciones de §5.4.
9. **G-009** — Mover dHash, fuentes y filtros a un subapartado «Construcción y depuración del dataset» dentro de §4; dejar §2.1 solo con el objetivo de evaluación.
10. **AUD-068 (parte redaccional)** — Describir referencia (77,52 %) y corregida (77,53 %) como **equivalentes** a la precisión reportada; eliminar cualquier afirmación de superioridad.

---

## 3. Fase 2 — Generación de datos desde el repositorio (sin reentrenar)

Datos ya disponibles o generables con consultas a `dataset/metadata.sqlite`, `registro_entrenamiento.sqlite` y los JSON de evaluación. Se entregarán como CSV/JSON en `docs/datos-auditoria/`.

### AUD-026 — Procedencia por fuente (desglose inicial → final)
Fuente de datos: `prenda.codigo` (prefijos `mendeley-*`, `clothing-small-*`, `clothing-*`).

| Fuente | Versión / fecha | Total ingresado | Aprobado | Rechazado | Otro estado |
|---|---:|---:|---:|---:|---:|
| AIG-Dataset (Mendeley) | DOI 10.17632/pxkbgkydrp.1, v1 (2025-04-17) | 53.055 | 11.227 | 23.443 | 18.385 |
| Clothing Dataset Small | GitHub (snapshot; sin versión) | 2.513 | 2.510 | 1 | 2 |
| Clothing Dataset | GitHub (snapshot; sin versión) | 778 | 690 | 0 | 88 |
| **Total** | — | **56.346** | **14.427** | **23.444** | **18.475** |

Cierre: balance trazable `56.346 → 14.427` por fuente y filtros (aprobado + apto + split).

### AUD-053 — Integridad de hashes
Ya documentado en `docs/EVIDENCIAS-INTEGRIDAD-SHA256.md`. Entregar además la salida real de la API:
- `GET http://127.0.0.1:8082/health` (campos `checkpoint.sha256`, `manifest.sha256`).
- `GET http://127.0.0.1:8082/test/informe` (campos `checkpoint_sha256`, `manifest_sha256`).

| Checkpoint | SHA-256 completo |
|---|---|
| `modelos-compartidos/mobilenetv3-small-best.pt` (época 15) | `79407f5537418bc258857fa54723d8e39b152505ad3a6f6a6ea4f97e1dfcb35c` |
| `runs/20261028-042931/best.pt` (época 15) | `77fbd17bfebd1c9cb64d08fd9a31e691aa0beac2a7c2e615d42aeb0f3413dea8` |
| `runs/20261029-022656/best.pt` (época 23) | `8aacd8b45aa5f7c99461b48c4fcf4d9e998b6efd9134758234675477ed96d923` |
| `tests/imagenes-test/manifest.json` | `4e1b28e2b506d5d1c38331e516f0931178f931e8822e865867396d7e1c05cdc0` |

### AUD-054 — Separación de splits
- Partición por prenda: **0 prendas con más de un split** (verificado: `split` es columna única por prenda). Conteos: train 11.592, val 1.414, test 1.421.
- Casi duplicados entre particiones (dHash, Hamming ≤ 2): 2.467 grupos tocan train∩test; 780 test∩val; 2.282 train∩val. Incluir la **tabla de sensibilidad** ya calculada en `CORRECCIONES-INFORME.md` §4.3 (77 imágenes de test con casi duplicado en train; macro 77,52 → 76,96 al excluirlas).
- Nota de rigor: el dHash≤2 es conservador (76 de 77 pares fueron marcados por revisor como "no duplicadas"); reportarlo como cota, no como fuga confirmada.

### AUD-056 / G-006 — Matriz de ejecución y trazabilidad técnica
Fuente: `registro_entrenamiento.sqlite` (tablas `ejecucion`, `imagen_entrenamiento`) + evaluaciones.

| Run id | Fecha (UTC) | Config | sha256 metadata | Checkpoint | Época | Test (portable) | Macro |
|---|---|---|---|---|---|---|---|
| 20261026-021300 | 2026-10-26 02:13 | lr 0,001/1e-4, warmup 3 | `58013102…` (dataset 11.616) | compartido | 15 | 94,94/68,42/69,21 | 77,52 |
| 20261028-042931 | 2026-10-28 04:29 | lr 1e-4/1e-5, warmup 0 | `24671397…` (dataset 11.592) | best.pt | 15 | 89,40/33,17/62,79 | 61,79 |
| 20261029-022656 | 2026-10-29 02:26 | lr 0,001/1e-4, warmup 3 | `24671397…` (dataset 11.592) | best.pt | 23 | 94,03/69,28/69,29 | 77,53 |

Declarar explícitamente que la referencia usó una versión anterior de `metadata.sqlite` (sha `58013102…`) con split train de 11.616.

### G-008 — Errores por clase
Extraer de `modelo-ia/evaluaciones/*.json` los bloques `por_etiqueta` (precisión, recall, F1 y soporte por clase de color y estilo) y presentar como tablas resumen + principales confusiones.

### G-010 — Vínculo figura ↔ datos
Mapear cada figura a su CSV/script:
| Figura | Datos | Archivo |
|---|---|---|
| G1–G3 (curvas) | validación por época | `docs/datos-graficos/validacion_por_epoca.csv` |
| G4 (comparación) | resultados test | `docs/datos-graficos/resultados_test.csv` |
| Script de gráficas | HTML autónomo | `figuras_entrenamiento_APA7.html` |

### AUD-030 — Línea de tiempo
`20261026-021300` (referencia) → hallazgo: detención prematura en warmup (`20261026-020700`, 3 épocas) y colapso de color → `20261028-042931` (configuración de continuación usada desde cero, macro 61,79) → decisión: restaurar receta `default.yaml` → `20261029-022656` (macro 77,53). Vincular cada paso a logs y commits.

---

## 4. Fase 3 — Declaraciones metodológicas (sin reentrenar)

### AUD-055 — Revisión manual de 50 imágenes
No existe registro cuantificado de las 50 imágenes (muestreo, errores por propiedad). Cierre recomendado: **declararlo como control limitado** y cuantificarlo solo si las 50 imágenes son identificables; en caso contrario, no atribuir al macro una exactitud humana. Complementar con el acuerdo entre proveedores ya medido (349 imágenes: color 64,2 % exacta / 75,7 % Jaccard; estilo 55,9 % / 73,8 %) como indicador del ruido de etiquetas.

### G-007 — Uso del conjunto test
Declaración verificable: la configuración corregida **no se buscó sobre test**; se restauró la receta ya documentada `default.yaml`/`desde-cero.yaml` (la misma que produjo la referencia). El checkpoint de cada run se eligió por **validación**; el test se usó una vez por checkpoint para la tabla comparativa. Declarar la limitación residual y, si se exige un holdout intacto, pasar a Fase 4.

---

## 5. Fase 4 — Reentrenamiento con parámetros documentados (si se aprueba)

**Objetivo:** cerrar AUD-068 (incertidumbre) y G-007 (holdout limpio) con evidencia nueva.

### Configuración fija (documentada y reproducible)
`utilidades-entrenamiento/configs/default.yaml` (equivale a `desde-cero.yaml`):
```
image_size: 224 · batch_size: 64 · epochs: 30
learning_rate: 0.001 · finetune_lr: 0.0001 · warmup_epochs: 3
pretrained: true · finetune: true · weight_decay: 0.0001
label_smoothing: 0.05 · class_weighted: true · augment: true · amp: true
early_stopping_patience: 5 · seed: 42
```

### Protocolo
1. **Congelar la receta antes de ejecutar** (no se toca el test para elegir config).
2. Ejecutar **N = 3 semillas** (seed 42, 123, 2026) del mismo config; seleccionar checkpoint por **validación**.
3. Evaluar cada checkpoint **una sola vez** sobre el test portable (1.424 imágenes, API en CPU, umbral 0,5).
4. Reportar macro medio ± desviación y **intervalo de confianza bootstrap** por imagen (diferencias pareadas referencia vs. corregida).

### Costo y cronograma (CPU)
- Cada corrida ~30 épocas ≈ 1,5–2 h en CPU; 3 semillas ≈ **5–6 h**.
- Alternativa GPU (`docker compose --profile gpu`): si hay GPU disponible, reduce el tiempo significativamente.

### Criterio de cierre
- AUD-068: tabla con media/desvío/IC bootstrap y redacción «equivalente / no superior».
- G-007: bitácora de decisiones que demuestre que el test no guió la selección de configuración.

---

## 6. Orden de ejecución sugerido

1. **F1 + F2 en paralelo** (no dependen de reentrenar): generar `docs/datos-auditoria/` con los CSV/JSON y aplicar correcciones editoriales.
2. **F3**: redactar las declaraciones de AUD-055 y G-007.
3. **Decisión F4**: si el tribunal exige repeticiones/holdout, ejecutar las 3 semillas y regenerar AUD-068.
4. **Cierre**: volver a validar documentación (`python3 docs/validar_documentacion.py`), actualizar INDICE y commit.

---

## 7. Entregables esperados

| Observación | Entregable |
|---|---|
| AUD-026 | Tabla fuente→cantidades + balance 56.346 → 14.427 |
| AUD-053 | `docs/EVIDENCIAS-INTEGRIDAD-SHA256.md` + salida real de `/health` y `/test/informe` |
| AUD-054 | Reporte de cruce de splits + sensibilidad dHash |
| AUD-056 / G-006 | Matriz run→checkpoint→SHA→fecha→archivo |
| AUD-068 | IC bootstrap + redacción equivalente (requiere F4) |
| G-008 | Tablas de errores por clase (color/estilo) |
| G-010 | Mapa figura→CSV→script |
| AUD-030 | Línea de tiempo run→hallazgo→decisión→run |
| Resto editorial | Documento Word corregido (Anexo G v4 + §5.4 sintetizado) |
