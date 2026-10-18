# Checkpoint compartido

## Modelo recomendado

- Archivo: `mobilenetv3-small-best.pt`
- Arquitectura: MobileNetV3-Small
- Ejecución fuente: `20261018-020637` (checkpoint idéntico al de `20261018-175546`)
- Mejor época: 15 de 20 épocas registradas
- Pérdida de validación: `0.5127596084`
- Entrada: 224 × 224 px
- SHA-256: `79407f5537418bc258857fa54723d8e39b152505ad3a6f6a6ea4f97e1dfcb35c`

Se seleccionó por la menor pérdida de validación entre las ejecuciones comparadas. La ejecución `20261018-192232` obtuvo `0.5353452153`, por lo que no reemplaza al checkpoint compartido. Esta comparación presupone que se mantuvieron el mismo split y dataset; el checkpoint es para inferencia, no una copia del estado del optimizador para reanudar entrenamiento.

El archivo contiene los pesos, las clases, la resolución y el umbral de inferencia. No incluye imágenes, base SQLite, caché de pesos preentrenados ni historial de entrenamiento. El `.gitignore` permite versionar únicamente este checkpoint recomendado; los demás `.pt` locales siguen excluidos.

Desde la raíz del repositorio, los compañeros pueden obtenerlo con `git pull`. Para usarlo en la API CPU, sigue la guía de [despliegue en VM](../README.md#api-de-inferencia-en-una-vm-con-cpu).