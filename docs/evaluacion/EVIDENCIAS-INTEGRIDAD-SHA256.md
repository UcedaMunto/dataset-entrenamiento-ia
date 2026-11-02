# Evidencias de integridad (SHA-256) para reproducibilidad

Documento de referencia con los **SHA-256 completos** necesarios para comprobar la integridad criptográfica del proyecto y de futuras ejecuciones. Complementa los resúmenes que usan hashes truncados (suficientes para distinguir visualmente ejecuciones, pero no para verificar integridad).

## 1. Por qué son necesarios los hashes completos

| Uso | Truncado (8 dígitos) | Completo (64 dígitos) |
|---|---|---|
| Distinguir visualmente ejecuciones | Sí | Sí |
| Comprobar que un archivo no cambió | No | **Sí** |
| Reproducir la evaluación exactamente | No | **Sí** |
| Verificar qué checkpoint cargó la API | No | **Sí** |

Para replicar el proyecto o auditar una ejecución futura se debe poder recalcular el hash del archivo y compararlo con el valor registrado. Por eso se conservan aquí los valores completos.

## 2. Checkpoints (pesos del modelo)

| Checkpoint | Rol | Época | SHA-256 completo |
|---|---|---|---|
| `utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt` | Referencia compartida (26-10) | 15 | `79407f5537418bc258857fa54723d8e39b152505ad3a6f6a6ea4f97e1dfcb35c` |
| `utilidades-entrenamiento/modelo-ia/runs/20261028-042931/best.pt` | Intento fallido desde cero (28-10) | 15 | `77fbd17bfebd1c9cb64d08fd9a31e691aa0beac2a7c2e615d42aeb0f3413dea8` |
| `utilidades-entrenamiento/modelo-ia/runs/20261029-022656/best.pt` | Desde cero corregido (29-10) | 23 | `8aacd8b45aa5f7c99461b48c4fcf4d9e998b6efd9134758234675477ed96d923` |

## 3. Conjunto de prueba portable

| Elemento | Valor |
|---|---|
| Archivo | `tests/imagenes-test/manifest.json` |
| SHA-256 del manifest completo | `4e1b28e2b506d5d1c38331e516f0931178f931e8822e865867396d7e1c05cdc0` |
| Versión del manifest | 1 |
| Generado | 2026-10-26T03:23:27+00:00 |
| Imágenes referenciadas | 1.424 (cada una con su propio SHA-256) |
| Verificación contra disco | 1.424 / 1.424 sin discrepancias |

El hash del manifest completo fija la **definición del conjunto de prueba** (lista de imágenes, etiquetas de referencia, clases y umbral). Los hashes por imagen fijan el contenido de cada fotografía.

## 4. Base de datos del dataset

| Elemento | Valor |
|---|---|
| Archivo | `dataset/metadata.sqlite` |
| SHA-256 (estado al entrenamiento 29-10) | `246713975fd632899f7b34cf7fbdb585c2f2a45e616322e8ad61c847b5cef75f` |

Este hash coincide con el campo `sha256_metadata` del registro de entrenamiento (`registro_entrenamiento.sqlite`), lo que acredita que la base actual es la que se usó en la ejecución `20261029-022656`.

## 5. Cómo obtenerlos automáticamente

La API de pruebas los calcula y expone en tiempo de ejecución, sin intervención manual:

```bash
# /health devuelve checkpoint.sha256 y manifest.sha256
curl -s http://127.0.0.1:8082/health

# /test/informe incluye checkpoint_sha256 y manifest_sha256
curl -s http://127.0.0.1:8082/test/informe | python3 -m json.tool
```

Y en línea de comandos:

```bash
sha256sum utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt
sha256sum tests/imagenes-test/manifest.json
sha256sum dataset/metadata.sqlite
```

## 6. Verificación de una ejecución futura

1. Registrar el **SHA-256 completo** del checkpoint que se cargó y del `manifest.json` usado.
2. Tras la ejecución, recalcular `sha256sum` de ambos archivos y comparar con lo registrado.
3. Si coinciden, la ejecución usó exactamente los mismos pesos y el mismo conjunto de prueba; si no, se declara la discrepancia y la ejecución no es comparable.
