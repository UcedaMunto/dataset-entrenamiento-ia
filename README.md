# Reconocimiento de prendas — V2

**Documento único de referencia** del repositorio `UcedaMunto/dataset-entrenamiento-ia`. Unifica el acceso a toda la documentación, las interfaces, el flujo de trabajo y las evidencias del proyecto. Revisión: **2 de noviembre de 2026**.

Sistema Docker para construir un dataset de prendas, entrenar **MobileNetV3-Small** y ejecutar inferencia de **tipo, colores y estilos**. Complemento de IA del artefacto principal (nube privada + Kubernetes + VTON Studio), alineado con **DSRM** (Peffers et al., 2007).

## 1. Interfaces

| Interfaz | Dirección local | Función | Implementación |
|---|---|---|---|
| Panel de dataset | http://127.0.0.1:8787/ | Importación, anotación asistida (NVIDIA NIM / DeepSeek), galería y duplicados | `modelo-general-destilacion/dashboard.py` |
| Panel de entrenamiento | http://127.0.0.1:8090/ | Iniciar/detener, continuar checkpoints, métricas, evaluación e inferencia CPU | `monitor.py` |
| API CPU independiente | http://127.0.0.1:8081/docs | Inferencia de una imagen; contrato OpenAPI | `inference_api.py` |
| API de pruebas (DSR) | http://127.0.0.1:8082/docs | Ejecuta la prueba de la API sobre `tests/imagenes-test/` | `test_api.py` |

Las rutas de código de esta tabla son relativas a `utilidades-entrenamiento/`. Los cuatro servicios se levantan con el **Compose unificado** de la raíz ([docker-compose.yaml](docker-compose.yaml)).

## 2. Arranque

```bash
# Configurar el panel de dataset (una sola vez, si no existe)
[ -f utilidades-entrenamiento/modelo-general-destilacion/.env ] || cp utilidades-entrenamiento/modelo-general-destilacion/.env.example utilidades-entrenamiento/modelo-general-destilacion/.env
chmod 600 utilidades-entrenamiento/modelo-general-destilacion/.env

# Levantar las cuatro interfaces
docker compose up -d --build

# Verificación
docker compose ps
curl -s -o /dev/null -w "dataset: %{http_code}\n" http://127.0.0.1:8787/
curl -s -o /dev/null -w "monitor: %{http_code}\n" http://127.0.0.1:8090/
curl -s -o /dev/null -w "inferencia: %{http_code}\n" http://127.0.0.1:8081/docs
curl -s -o /dev/null -w "pruebas: %{http_code}\n" http://127.0.0.1:8082/docs

# Entrenamiento por terminal (alternativa al panel)
docker compose -f utilidades-entrenamiento/docker-compose.yaml build train
docker compose -f utilidades-entrenamiento/docker-compose.yaml run --rm train

# Detener
docker compose down
```

Instrucciones completas en [Instalación Docker](docs/instalacion/INSTALACION-DOCKER.md) · [Instalación nativa sin Docker](docs/instalacion/INSTALACION-NATIVA.md).

## 3. Flujo y estado comprobado

`Fuentes locales → curación/anotación → revisión y aprobación → SQLite + imágenes → entrenamiento → evaluación → checkpoint → inferencia`.

- **14.456 prendas aprobadas y aptas**: 11.616 train · 1.416 val · 1.424 test.
- Checkpoint compartido (`mobilenetv3-small-best.pt`): **tipo 94,94 %** · **color Jaccard 68,42 %** · **estilo Jaccard 69,21 %** · **promedio macro 77,52 %**.
- El macro no equivale a exactitud global. Las etiquetas de color/estilo proceden de IA y se reportaron casi duplicados entre splits: ver [limitaciones de la evaluación](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md).

## 4. Mapa completo de la documentación

### 4.1 Entrada y resumen

| Documento | Propósito |
|---|---|
| [README (este documento)](README.md) | Documento único de referencia del repositorio. |
| [Resumen del proyecto](docs/resumen/RESUMEN-PROYECTO.md) | Resumen ejecutivo de unas cuatro páginas, apto para impresión. |
| [Índice de documentación](docs/INDICE.md) | Mapa detallado por carpetas temáticas. |

### 4.2 Instalación

| Documento | Propósito |
|---|---|
| [Instalación del sistema completo (Docker)](docs/instalacion/INSTALACION-DOCKER.md) | Interfaces, API, pruebas, entrenamiento y respaldos con el Compose unificado. |
| [Instalación nativa del modelo y su API](docs/instalacion/INSTALACION-NATIVA.md) | Instalación directa con Python y verificación sin contenedores. |
| [Manual Word APA 7](docs/instalacion/Instalacion_nativa_API_prendas_APA7.docx) | Versión editable DOCX de la instalación nativa. |
| [Generador del manual DOCX](docs/instalacion/generar_manual_docx.py) | Script que sincroniza el Word con `INSTALACION-NATIVA.md`. |

### 4.3 Operación: API y pruebas

| Documento | Propósito |
|---|---|
| [Referencia de endpoints locales](docs/operacion/API.md) | Contratos HTTP de paneles, API CPU y API de pruebas. |
| [Diseño de prueba DSR — API de descripción](docs/operacion/DSR-PRUEBA-API.md) | Prueba de una página basada en Design Science Research. |
| [README-TEST — Ejecutar la prueba](docs/operacion/README-TEST.md) | Guía rápida para correr la prueba con la API. |
| [README-PRUEBA — Cómo se hizo la prueba](docs/operacion/README-PRUEBA.md) | Detalle de ejecución y resultados. |

### 4.4 Evaluación y evidencias

| Documento | Propósito |
|---|---|
| [Evaluación del clasificador](docs/evaluacion/EVALUACION-ENTRENAMIENTO.md) | Resultados registrados y limitaciones. |
| [Validación de documentación e implementación](docs/evaluacion/VALIDACION.md) | Comprobaciones del 23-10-2026 y pendientes. |
| [Evidencias de integridad (SHA-256)](docs/evaluacion/EVIDENCIAS-INTEGRIDAD-SHA256.md) | Hashes completos para reproducibilidad. |
| [Registro DSR: errores y correcciones](docs/evaluacion/DSR-ERRORES-Y-CORRECCIONES.md) | Errores E1/E2, diagnóstico y verificación. |
| [Registro de entrenamiento 20261029-022656](docs/evaluacion/ENTRENAMIENTO-20261029-022656.md) | Configuración, validación y evaluación del entrenamiento corregido. |
| [Plan de correcciones — Auditoría Anexo G](docs/evaluacion/PLAN-CORRECCIONES-AUDITORIA-ANEXO-G.md) | Plan para atender las 20 observaciones. |
| [Resumen de los últimos 3 entrenamientos (DOCX)](docs/evaluacion/Resumen_Ultimos_3_Entrenamientos.docx) | Comparativo Word de los tres entrenamientos. |
| [Datos para gráficos del entrenamiento](docs/datos-graficos/README.md) | CSV/JSON de métricas por época y resultados de test. |

### 4.5 Teoría y método

| Documento | Propósito |
|---|---|
| [Teoría del entrenamiento — resumen completo](docs/teoria/TEORIA-ENTRENAMIENTO-COMPLETO.md) | Fundamentos, MobileNetV3, transferencia, pérdidas, optimización y métricas. |
| [Terminología y teoría del entrenamiento](docs/teoria/TEORIA-ENTRENAMIENTO.md) | Referencia conceptual y glosario rápido. |
| [Teoría y conceptos del método de evaluación (DSRM)](docs/teoria/TEORIA-METODO-EVALUACION.md) | Métricas, Jaccard, macro, control y validez. |

### 4.6 Antecedentes

Documentos históricos conservados como contexto; sus cifras **no** representan el estado vigente.

| Documento | Propósito |
|---|---|
| [Correcciones del informe (obs. 4, 5 y 6)](docs/antecedentes/CORRECCIONES-INFORME.md) | Análisis y propuestas fechados al 22-10-2026. |
| [Plan de entrenamiento (V2)](docs/antecedentes/PLAN-ENTRENAMIENTO.md) | Plan histórico inicial. |
| [Reconocimiento de prendas — V1](docs/antecedentes/README-v1.md) | Versión histórica descartada. |
| [Resumen del método de entrenamiento](docs/antecedentes/RESUMEN-METODO-ENTRENAMIENTO.md) | Método con contexto histórico. |

### 4.7 Dataset y taxonomía

| Documento | Propósito |
|---|---|
| [Dataset de prendas](dataset/README.md) | Guía de clasificación y estructura general. |
| [Documentación del dataset](documentacion_dataset/README.md) | Esquema SQLite, procedencia y metadatos. |
| [Prendas de la parte inferior](dataset/inferior/README.md) · [Falda](dataset/inferior/faldas/README.md) · [Pantalón](dataset/inferior/pantalones/README.md) · [Short](dataset/inferior/shorts/README.md) | Clases de la parte inferior. |
| [Prendas de cuerpo completo](dataset/inferior_superior/README.md) · [Vestido](dataset/inferior_superior/vestido/README.md) | Clases de cuerpo completo. |
| [Prendas de la parte superior](dataset/superior/README.md) · [Abrigo](dataset/superior/abrigos/README.md) · [Blusa](dataset/superior/blusas/README.md) · [Camisa](dataset/superior/camisas/README.md) · [Chaqueta](dataset/superior/chaquetas/README.md) · [Suéter](dataset/superior/sueteres/README.md) | Clases de la parte superior. |
| [Conjunto portable de prueba](tests/imagenes-test/README.md) | 1.424 imágenes del split test con manifest. |

### 4.8 Utilidades de entrenamiento y curación

| Documento | Propósito |
|---|---|
| [Utilidades de entrenamiento](utilidades-entrenamiento/README.md) | Entrenar, continuar checkpoints y desplegar inferencia. |
| [Inicio rápido](utilidades-entrenamiento/INICIO-RAPIDO.md) | Comandos mínimos para entrenar por terminal. |
| [Checkpoint compartido](utilidades-entrenamiento/modelos-compartidos/README.md) | Ubicación y uso de `mobilenetv3-small-best.pt`. |
| [Curación y anotación de datasets de moda](utilidades-entrenamiento/modelo-general-destilacion/README.md) | Panel de dataset, proveedores y flujo de curación. |
| [Plan de pruebas del pipeline de curación](utilidades-entrenamiento/modelo-general-destilacion/PLAN-PRUEBAS.md) | Pruebas del pipeline de curación. |
| [Dudas y decisiones antes de procesar datos](utilidades-entrenamiento/modelo-general-destilacion/dudas.md) | Preguntas abiertas y decisiones previas. |
| [Extensión Chrome: descargar imagen](utilidades-entrenamiento/scraping-plugin-chrome/folder-destino/README.md) | Utilidad auxiliar de captura de imágenes. |

## 5. Archivos técnicos clave

- [Compose unificado](docker-compose.yaml) y [Compose de entrenamiento por terminal](utilidades-entrenamiento/docker-compose.yaml).
- [Esquema SQLite](documentacion_dataset/schema.sql) y [creación de estructura](documentacion_dataset/crear_estructura.sh).
- [Configuración por defecto](utilidades-entrenamiento/configs/default.yaml) y [desde cero](utilidades-entrenamiento/configs/desde-cero.yaml) del entrenamiento.
- [Fuentes de datos](utilidades-entrenamiento/modelo-general-destilacion/sources.json).
- [Validador documental](docs/validar_documentacion.py): `python3 docs/validar_documentacion.py` (comprueba enlaces, anclas y cobertura del índice).

## 6. Alcance y notas

El alcance es clasificar una misma prenda por imagen o conjunto de vistas. No hay detección de múltiples prendas, segmentación ni salida de temporada. La integración con OpenStack/Kubernetes queda fuera de esta implementación. Los planes y V1 se conservan como antecedentes.
