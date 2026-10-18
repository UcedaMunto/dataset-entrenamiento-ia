# Iniciar el entrenamiento

Todo corre en contenedores; solo se necesita Docker (y driver NVIDIA + NVIDIA Container Toolkit para GPU).

```bash
cd utilidades-entrenamiento
newgrp docker                                   # si Docker da "permission denied"
docker compose build
docker compose --profile gpu run --rm train-gpu status   # debe mostrar la GPU
docker compose --profile gpu run --rm train-gpu          # entrena (usa configs/default.yaml)
```

Sin GPU: `docker compose run --rm train` (mucho más lento).

## Ver el avance

En otra terminal:

```bash
docker compose --profile monitor up -d monitor
```

Abrir http://127.0.0.1:8090 (progreso, pérdida por época, métricas e imágenes registradas).

Para continuar desde un checkpoint, selecciona la ejecución y estrategia en el panel. Se recomienda **Ajuste fino completo** desde el mejor checkpoint según validación; crea una fase nueva de hasta 10 épocas y reinicia optimizador/scheduler. Consulta la [estrategia y sus consideraciones](./README.md#estrategia-recomendada-para-continuar).

## Resultados

- Pesos: `modelo-ia/runs/<fecha-hora>/best.pt`; métricas en `metrics.json` y `test_metrics.json`.
- Registro de imágenes usadas por ejecución: `modelo-ia/registro_entrenamiento.sqlite`.
- Ajustes (épocas, batch, resolución): `configs/default.yaml`.
