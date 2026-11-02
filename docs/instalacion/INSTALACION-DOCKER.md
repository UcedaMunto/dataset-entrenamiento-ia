# Instalación del sistema completo (Docker)

Versión: 1.1 · 02 de noviembre de 2026

Guía operativa del **Reconocimiento de prendas V2**, complemento de IA del artefacto principal documentado en el informe del proyecto (nube privada, Kubernetes y VTON Studio). Alineada con la metodología **DSRM** (Peffers et al., 2007).

[Índice completo](../INDICE.md) · [Instalación nativa sin Docker de la API](INSTALACION-NATIVA.md) · [Referencia de endpoints](../operacion/API.md)

## 1. Contexto DSRM y rol de esta guía

El proyecto sigue **Design Science Research Methodology (DSRM)**. El artefacto principal es la nube privada con Kubernetes y el servicio FASHN VTON; **Reconocimiento de prendas V2** es un **complemento útil** que operativiza la inferencia (MobileNetV3-Small) y el entrenamiento del caso de estudio.

Esta guía no documenta el artefacto principal: describe cómo **instanciar y demostrar** el complemento en un equipo Ubuntu con Docker. La correspondencia con las seis actividades DSRM es:

| Actividad DSRM | Dónde se materializa en esta guía |
|---|---|
| 1. Identificación del problema | §2 Objetivo y alcance (qué resuelve el sistema) |
| 2. Objetivos de la solución | §2 Objetivo y alcance (servicios e interfaces) |
| 3. Diseño y desarrollo | §6 Levantar las interfaces y §9 Entrenamiento (Compose, recetas, checkpoints) |
| 4. Demostración | §6–8 Levantar y probar los servicios (HTTP 200 e inferencia) |
| 5. Evaluación | §8 API de pruebas DSR y §10 Informe HTML (métricas y Anexo G) |
| 6. Comunicación | Documentos referenciados: [API.md](../operacion/API.md), [DSR-PRUEBA-API.md](../operacion/DSR-PRUEBA-API.md), informe y Anexo G |

## 2. Objetivo y alcance

Esta guía instala el sistema completo **Reconocimiento de prendas V2** en un equipo con Ubuntu 24.04 y Docker. El sistema incluye:

| Interfaz | Dirección local | Función |
|---|---|---|
| Panel de dataset | http://127.0.0.1:8787/ | Importar, anotar (NVIDIA NIM / DeepSeek), revisar y depurar duplicados |
| Panel de entrenamiento | http://127.0.0.1:8090/ | Iniciar/detener entrenamientos, continuar checkpoints y ver métricas |
| API de inferencia (CPU) | http://127.0.0.1:8081/docs | Describe una prenda a partir de una fotografía |
| API de pruebas (DSR) | http://127.0.0.1:8082/docs | Ejecuta la prueba sobre el conjunto portable `tests/imagenes-test/` |

Todos los servicios se levantan con el **Compose unificado de la raíz** ([docker-compose.yaml](../../docker-compose.yaml)). No es necesario Docker para la API de inferencia: existe una [instalación nativa](INSTALACION-NATIVA.md) alternativa.

## 3. Requisitos

- Ubuntu 24.04, arquitectura x86-64.
- Docker Engine 29+ y Docker Compose v2 (`docker compose`).
- Conexión a Internet para descargar imágenes base y dependencias durante la primera compilación.
- Para el panel de dataset: claves de los proveedores de IA (NVIDIA NIM y/o DeepSeek). Son opcionales si solo se importan imágenes sin anotar.
- Para GPU (opcional): driver NVIDIA y NVIDIA Container Toolkit.

Verificación:

```bash
docker --version
docker compose version
```

Resultado esperado: Docker 29.x y Compose v2.40+.

## 4. Obtener el código

```bash
git clone <url-del-repositorio> modelo-reconocimiento-prendas
cd modelo-reconocimiento-prendas
```

El repositorio ya incluye el checkpoint compartido (`utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt`) y el conjunto portable de test (`tests/imagenes-test/`). El dataset (`dataset/`) se entrega aparte o se reconstruye con el panel.

## 5. Configurar el panel de dataset (una sola vez)

Crear el archivo de entorno desde la plantilla y restringir sus permisos:

```bash
[ -f utilidades-entrenamiento/modelo-general-destilacion/.env ] || \
  cp utilidades-entrenamiento/modelo-general-destilacion/.env.example \
     utilidades-entrenamiento/modelo-general-destilacion/.env
chmod 600 utilidades-entrenamiento/modelo-general-destilacion/.env
```

Variables principales (los valores son secretos y **no deben versionarse**):

| Variable | Uso |
|---|---|
| `ANNOTATION_PROVIDER` | `nim`, `deepseek` u `openai` (proveedor de anotación) |
| `NVIDIA_NIM_API_KEY`, `NVIDIA_NIM_MODEL` | Acceso a NVIDIA NIM |
| `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` | Acceso a la API de DeepSeek |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Acceso a OpenAI (opcional) |
| `TRAINING_UID`, `TRAINING_GID` | UID/GID del usuario para los montajes (por defecto 1000) |

## 6. Levantar las interfaces — Diseño y desarrollo → Demostración

Desde la raíz del proyecto:

```bash
docker compose up -d --build
```

Esto construye y arranca los cuatro servicios. Para levantar solo dos de ellos (p. ej. las dos interfaces principales):

```bash
docker compose up -d --build dashboard monitor
```

Comprobar el estado:

```bash
docker compose ps
curl -s -o /dev/null -w "dataset:  %{http_code}\n" http://127.0.0.1:8787/
curl -s -o /dev/null -w "monitor:  %{http_code}\n" http://127.0.0.1:8090/
curl -s -o /dev/null -w "inferencia: %{http_code}\n" http://127.0.0.1:8081/docs
curl -s -o /dev/null -w "pruebas:  %{http_code}\n" http://127.0.0.1:8082/docs
```

Resultado esperado: HTTP 200 en las cuatro direcciones. El panel de dataset usa la red del host, por lo que su puerto 8787 no aparece en `docker ps`, pero responde en `127.0.0.1:8787`.

## 7. Probar la API de inferencia — Demostración

```bash
curl -X POST http://127.0.0.1:8081/describir \
  -H "Content-Type: application/json" \
  -d '{"ruta_imagen": "ruta/a/una/foto.jpg"}'
```

Consulta el contrato completo en [API.md](../operacion/API.md) y en `http://127.0.0.1:8081/docs`.

Cambiar el checkpoint cargado por la API (antes de levantar):

```bash
MODEL_CHECKPOINT=/ruta/absoluta/al/checkpoint.pt docker compose up -d inference-api
```

## 8. Probar la API de pruebas (DSR) — Evaluación

```bash
# Prueba de humo (10 imágenes)
curl -X POST "http://127.0.0.1:8082/test/run?max_images=10"

# Prueba completa (1.424 imágenes)
curl -X POST "http://127.0.0.1:8082/test/run"

# Evidencia para el informe y el Anexo G
curl "http://127.0.0.1:8082/test/informe"
```

Detalle en [DSR-PRUEBA-API.md](../operacion/DSR-PRUEBA-API.md) y [README-TEST.md](../operacion/README-TEST.md).

## 9. Entrenamiento — Diseño y desarrollo / Demostración

### 9.1 Desde el panel (recomendado)

Abrir http://127.0.0.1:8090/ y usar el selector de configuración. Las recetas disponibles están en `utilidades-entrenamiento/configs/`:

- `default.yaml` / `desde-cero.yaml`: entrenamiento independiente desde pesos preentrenados (lr 0,001 / finetune_lr 0,0001, warmup 3, 30 épocas).
- Recetas de continuación: tasas 1e-4 / 1e-5 y sin warmup, para reanudar un checkpoint.

### 9.2 Desde terminal (Compose de entrenamiento)

```bash
docker compose -f utilidades-entrenamiento/docker-compose.yaml build train
docker compose -f utilidades-entrenamiento/docker-compose.yaml run --rm train
```

### 9.3 Con GPU (opcional)

```bash
docker compose -f utilidades-entrenamiento/docker-compose.yaml --profile gpu run --rm train-gpu
```

Requiere driver NVIDIA y NVIDIA Container Toolkit. Detalle en la guía de entrenamiento (`utilidades-entrenamiento/README.md`).

## 10. Generar el informe HTML de evaluación — Evaluación

```bash
python3 utilidades-entrenamiento/generar_informe_entrenamiento.py --output-dir docs/datos-graficos
```

O dentro del contenedor (deja el log de cálculos en `informe_entrenamiento.log`):

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

## 11. Respaldo y restauración — Evidencias y trazabilidad

Respaldo de los entrenamientos, evaluaciones y base de datos (se guarda en `respaldos/`, ignorado por Git):

```bash
tar -czf "respaldos/entrenamiento-$(date +%Y%m%d-%H%M%S).tar.gz" \
  utilidades-entrenamiento/modelo-ia \
  utilidades-entrenamiento/modelos-compartidos \
  dataset/metadata.sqlite
```

Restaurar:

```bash
tar -xzf respaldos/entrenamiento-<marca>.tar.gz
```

## 12. Detener el sistema

```bash
docker compose down            # detiene y retira contenedores; conserva datos
docker compose down --volumes  # además elimina volúmenes (pérdida de datos)
```

## 13. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| El panel de dataset no anota | `.env` sin claves o proveedor inválido | Revisar `ANNOTATION_PROVIDER` y las claves en `.env` |
| `No encontrado` al iniciar entrenamiento | Petición sin cabecera `X-Requested-With: monitor` o config inexistente | Usar el panel; elegir una config de `configs/` |
| Puertos ocupados | Otro proceso usa 8081/8082/8090 | Cambiar los `ports` en `docker-compose.yaml` |
| Fallo de permisos en montajes | UID/GID distinto de 1000 | Definir `TRAINING_UID`/`TRAINING_GID` en `.env` |
| La API devuelve error de checkpoint | `MODEL_CHECKPOINT` apunta a un archivo inexistente | Verificar ruta y SHA-256 en [EVIDENCIAS-INTEGRIDAD-SHA256.md](../evaluacion/EVIDENCIAS-INTEGRIDAD-SHA256.md) |
