# Índice de documentación

**Revisión: 2 de noviembre de 2026.** Inventario completo de los Markdown del repositorio, reorganizado por carpetas temáticas dentro de `docs/`. Este índice es el punto de entrada: todos los documentos están enlazados aquí y las rutas son las definitivas.

Lectura sugerida: [README de entrada](../README.md) → [resumen del proyecto](resumen/RESUMEN-PROYECTO.md) → [validación](evaluacion/VALIDACION.md) → [instalación Docker](instalacion/INSTALACION-DOCKER.md) → [referencia de endpoints](operacion/API.md).

## Organización de la documentación

```
docs/
├── INDICE.md                  ← este índice
├── validar_documentacion.py   ← comprobador de enlaces y cobertura
├── instalacion/               ← Docker, nativa, manual DOCX y generador
├── operacion/                 ← API, endpoints y prueba DSR de la API
├── evaluacion/                ← métricas, evidencias, validación y planes de auditoría
├── teoria/                    ← teoría del entrenamiento y del método de evaluación
├── antecedentes/              ← planes y versiones históricas (contexto, no estado)
├── resumen/                   ← resumen ejecutivo del proyecto
└── datos-graficos/            ← CSV/JSON y figuras de los entrenamientos
```

Fuera de `docs/` se conservan los README temáticos de cada módulo (dataset, utilidades de entrenamiento, tests) porque documentan el código que acompañan.

## Entrada y resumen

| Documento | Propósito |
|---|---|
| [Reconocimiento de prendas — V2](../README.md) | Portada del repositorio: interfaces, arranque, flujo y estado comprobado. |
| [Documentación completa unificada](../README-COMPLETO.md) | Todo el contenido de los Markdown del repositorio en un solo archivo ordenado, para dar contexto a otra IA. |
| [Resumen del proyecto](resumen/RESUMEN-PROYECTO.md) | Resumen ejecutivo de unas cuatro páginas, apto para impresión. |
| [Índice de documentación](INDICE.md) | Este documento: mapa completo de la documentación. |

## Instalación

| Documento | Propósito |
|---|---|
| [Instalación del sistema completo (Docker)](instalacion/INSTALACION-DOCKER.md) | Levantar interfaces, API, pruebas, entrenamiento y respaldos con el Compose unificado. |
| [Instalación nativa del modelo y su API](instalacion/INSTALACION-NATIVA.md) | Instalación directa con Python, contrato de una imagen y verificación sin contenedores. |
| [Manual Word APA 7](instalacion/Instalacion_nativa_API_prendas_APA7.docx) | Versión editable DOCX de la instalación nativa, generada desde la fuente anterior. |
| [Generador del manual DOCX](instalacion/generar_manual_docx.py) | Script que sincroniza el Word con `INSTALACION-NATIVA.md` (requiere `python-docx`). |

## Operación: API y pruebas

| Documento | Propósito |
|---|---|
| [Referencia de endpoints locales](operacion/API.md) | Contratos HTTP de los paneles, la API CPU y la API de pruebas. |
| [Guía de interfaces — botones y funciones](operacion/GUIA-INTERFACES.md) | Capturas de pantalla y lista de botones del panel de entrenamiento y del panel de dataset. |
| [Diseño de prueba DSR — API de descripción de prendas](operacion/DSR-PRUEBA-API.md) | Prueba de una página basada en Design Science Research. |
| [README-TEST — Ejecutar la prueba](operacion/README-TEST.md) | Guía rápida para correr la prueba con la API. |
| [README-PRUEBA — Cómo se hizo la prueba](operacion/README-PRUEBA.md) | Detalle de la ejecución y los resultados de la prueba. |

## Evaluación y evidencias

| Documento | Propósito |
|---|---|
| [Evaluación del clasificador (MobileNetV3-Small)](evaluacion/EVALUACION-ENTRENAMIENTO.md) | Resultados registrados y limitaciones. |
| [Validación de documentación e implementación](evaluacion/VALIDACION.md) | Comprobaciones del 23-10-2026 y pendientes. |
| [Evidencias de integridad (SHA-256)](evaluacion/EVIDENCIAS-INTEGRIDAD-SHA256.md) | Hashes completos de checkpoints, manifest y dataset para reproducibilidad. |
| [Registro DSR: errores y correcciones](evaluacion/DSR-ERRORES-Y-CORRECCIONES.md) | Errores E1/E2, diagnóstico DSR, correcciones y verificación. |
| [Registro de entrenamiento 20261029-022656](evaluacion/ENTRENAMIENTO-20261029-022656.md) | Configuración, evolución de validación, evaluación en test y decisión de continuidad. |
| [Plan de correcciones — Auditoría Anexo G](evaluacion/PLAN-CORRECCIONES-AUDITORIA-ANEXO-G.md) | Plan para atender las 20 observaciones y generar los datos necesarios. |
| [Resumen de los últimos 3 entrenamientos (DOCX)](evaluacion/Resumen_Ultimos_3_Entrenamientos.docx) | Documento Word con el resumen comparativo de los tres entrenamientos. |
| [Datos para gráficos del entrenamiento](datos-graficos/README.md) | CSV/JSON con métricas por época y resultados de test de los tres entrenamientos. |

## Teoría y método

| Documento | Propósito |
|---|---|
| [Teoría del entrenamiento — resumen completo (≈10 páginas)](teoria/TEORIA-ENTRENAMIENTO-COMPLETO.md) | Fundamentos, MobileNetV3, transferencia, pérdidas, optimización y métricas. |
| [Terminología y teoría del entrenamiento](teoria/TEORIA-ENTRENAMIENTO.md) | Referencia conceptual y glosario rápido. |
| [Teoría y conceptos del método de evaluación (DSRM)](teoria/TEORIA-METODO-EVALUACION.md) | Matriz de confusión, exactitud, precisión/recall/F1, Jaccard, macro, control y validez. |

## Antecedentes

Documentos históricos conservados como contexto. Sus cifras **no** representan el estado vigente.

| Documento | Propósito |
|---|---|
| [Correcciones del informe (observaciones 4, 5 y 6)](antecedentes/CORRECCIONES-INFORME.md) | Análisis y propuestas del informe, fechados al 22-10-2026. |
| [Plan de entrenamiento (MobileNetV3-Small, V2)](antecedentes/PLAN-ENTRENAMIENTO.md) | Plan histórico inicial. |
| [Reconocimiento de prendas — V1](antecedentes/README-v1.md) | Versión histórica descartada. |
| [Resumen del método de entrenamiento](antecedentes/RESUMEN-METODO-ENTRENAMIENTO.md) | Método con contexto histórico; estado vigente en el resumen nuevo. |

## Dataset y taxonomía

| Documento | Propósito |
|---|---|
| [Dataset de prendas](../dataset/README.md) | Guía de clasificación y estructura general. |
| [Documentación del dataset](../documentacion_dataset/README.md) | Esquema SQLite, procedencia y gestión de metadatos. |
| [Prendas de la parte inferior](../dataset/inferior/README.md) | Categorías de la parte inferior. |
| [Falda](../dataset/inferior/faldas/README.md) · [Pantalón](../dataset/inferior/pantalones/README.md) · [Short](../dataset/inferior/shorts/README.md) | Clases de la parte inferior. |
| [Prendas de cuerpo completo](../dataset/inferior_superior/README.md) · [Vestido](../dataset/inferior_superior/vestido/README.md) | Clases de cuerpo completo. |
| [Prendas de la parte superior](../dataset/superior/README.md) | Categorías de la parte superior. |
| [Abrigo](../dataset/superior/abrigos/README.md) · [Blusa](../dataset/superior/blusas/README.md) · [Camisa](../dataset/superior/camisas/README.md) · [Chaqueta](../dataset/superior/chaquetas/README.md) · [Suéter](../dataset/superior/sueteres/README.md) | Clases de la parte superior. |
| [Conjunto portable de prueba](../tests/imagenes-test/README.md) | 1.424 imágenes del split test con manifest para la API de pruebas. |

## Utilidades de entrenamiento y curación

| Documento | Propósito |
|---|---|
| [Utilidades de entrenamiento](../utilidades-entrenamiento/README.md) | Guía del módulo: entrenar, continuar checkpoints y desplegar inferencia. |
| [Inicio rápido](../utilidades-entrenamiento/INICIO-RAPIDO.md) | Comandos mínimos para arrancar el entrenamiento por terminal. |
| [Checkpoint compartido](../utilidades-entrenamiento/modelos-compartidos/README.md) | Ubicación y uso del checkpoint `mobilenetv3-small-best.pt`. |
| [Curación y anotación de datasets de moda](../utilidades-entrenamiento/modelo-general-destilacion/README.md) | Panel de dataset, proveedores de anotación y flujo de curación. |
| [Plan de pruebas del pipeline de curación](../utilidades-entrenamiento/modelo-general-destilacion/PLAN-PRUEBAS.md) | Pruebas del pipeline de curación. |
| [Dudas y decisiones antes de procesar datos](../utilidades-entrenamiento/modelo-general-destilacion/dudas.md) | Preguntas abiertas y decisiones previas al procesamiento. |
| [Extensión Chrome: descargar imagen de producto](../utilidades-entrenamiento/scraping-plugin-chrome/folder-destino/README.md) | Utilidad auxiliar de captura de imágenes. |

## Archivos técnicos relacionados

- [Esquema SQLite](../documentacion_dataset/schema.sql) y [creación de estructura](../documentacion_dataset/crear_estructura.sh).
- [Compose unificado (dataset + entrenamiento + API CPU + API de pruebas)](../docker-compose.yaml) y [Compose de entrenamiento por terminal](../utilidades-entrenamiento/docker-compose.yaml).
- [Configuración de entrenamiento por defecto](../utilidades-entrenamiento/configs/default.yaml) y [desde cero](../utilidades-entrenamiento/configs/desde-cero.yaml).
- [Fuentes de datos](../utilidades-entrenamiento/modelo-general-destilacion/sources.json).
- [Validador documental](validar_documentacion.py): ejecutar `python3 docs/validar_documentacion.py` desde la raíz. Comprueba enlaces locales, anclas y cobertura del índice, sin red ni escrituras.

## Mantenimiento

Al añadir un Markdown, enlazarlo en la tabla de su categoría y especificar si es guía vigente, resultado fechado, referencia conceptual o antecedente. Actualizar cifras con fecha y origen; no presentar planificación como medición ni aprobación masiva como auditoría humana. Actualizar la referencia de API cuando cambien los handlers.
