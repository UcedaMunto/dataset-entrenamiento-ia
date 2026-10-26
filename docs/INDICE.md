# Índice de documentación

**Revisión: 23 de octubre de 2026.** Inventario completo de Markdown del repositorio. Se conservan las rutas originales para mantener referencias.

Lectura sugerida: [entrada](../README.md) → [resumen de cuatro páginas](<../readme resumen.md>) → [validación](VALIDACION.md) → guía operativa del módulo.

Las cifras de validación son instantáneas comprobadas; los planes y V1 contienen antecedentes. Una propuesta no acredita ejecución. Para configuración real consultar código y artefactos de cada experimento.

## Entrada y evidencia

| Documento | Propósito / estado |
|---|---|
| [Reconocimiento de prendas — V2](<../README.md>) | Guía del módulo; atender a fechas de mediciones y decisiones pendientes. |
| [Instalación nativa del modelo entrenado y su API](INSTALACION-NATIVA.md) | Instalación directa con Python; contrato de una imagen; verificación nativa. |
| [Manual Word APA 7](Instalacion_nativa_API_prendas_APA7.docx) | Documento editable de instalación, configuración y operación sin contenedores. |
| [Referencia de endpoints locales](<API.md>) | Contratos HTTP de las dos interfaces y la API CPU. |
| [Índice de documentación](<INDICE.md>) | Guía del módulo; atender a fechas de mediciones y decisiones pendientes. |
| [Validación de documentación e implementación](<VALIDACION.md>) | Comprobaciones del 23-10-2026 y pendientes. |
| [Resumen del proyecto de reconocimiento de prendas](<../readme resumen.md>) | Resumen en cuatro bloques para impresión. |

## Operación

| Documento | Propósito / estado |
|---|---|
| [Evaluación del clasificador (MobileNetV3-Small)](<../EVALUACION-ENTRENAMIENTO.md>) | Resultados registrados y limitaciones. |
| [Iniciar el entrenamiento](<../utilidades-entrenamiento/INICIO-RAPIDO.md>) | Guía del módulo; atender a fechas de mediciones y decisiones pendientes. |
| [Utilidades de entrenamiento](<../utilidades-entrenamiento/README.md>) | Guía del módulo; atender a fechas de mediciones y decisiones pendientes. |
| [Plan de pruebas del pipeline de curación](<../utilidades-entrenamiento/modelo-general-destilacion/PLAN-PRUEBAS.md>) | Guía del módulo; atender a fechas de mediciones y decisiones pendientes. |
| [Curación y anotación de datasets de moda](<../utilidades-entrenamiento/modelo-general-destilacion/README.md>) | Guía del módulo; atender a fechas de mediciones y decisiones pendientes. |
| [Checkpoint compartido](<../utilidades-entrenamiento/modelos-compartidos/README.md>) | Guía del módulo; atender a fechas de mediciones y decisiones pendientes. |

## Dataset y taxonomía

| Documento | Propósito / estado |
|---|---|
| [Dataset de prendas](<../dataset/README.md>) | Guía de clasificación y estructura. |
| [Prendas de la parte inferior](<../dataset/inferior/README.md>) | Guía de clasificación y estructura. |
| [Falda](<../dataset/inferior/faldas/README.md>) | Guía de clasificación y estructura. |
| [Pantalón](<../dataset/inferior/pantalones/README.md>) | Guía de clasificación y estructura. |
| [Short](<../dataset/inferior/shorts/README.md>) | Guía de clasificación y estructura. |
| [Prendas de cuerpo completo](<../dataset/inferior_superior/README.md>) | Guía de clasificación y estructura. |
| [Vestido](<../dataset/inferior_superior/vestido/README.md>) | Guía de clasificación y estructura. |
| [Prendas de la parte superior](<../dataset/superior/README.md>) | Guía de clasificación y estructura. |
| [Abrigo](<../dataset/superior/abrigos/README.md>) | Guía de clasificación y estructura. |
| [Blusa](<../dataset/superior/blusas/README.md>) | Guía de clasificación y estructura. |
| [Camisa (clase unificada)](<../dataset/superior/camisas/README.md>) | Guía de clasificación y estructura. |
| [Chaqueta](<../dataset/superior/chaquetas/README.md>) | Guía de clasificación y estructura. |
| [Suéter](<../dataset/superior/sueteres/README.md>) | Guía de clasificación y estructura. |
| [Documentación del dataset](<../documentacion_dataset/README.md>) | Guía de clasificación y estructura. |

## Teoría y antecedentes

| Documento | Propósito / estado |
|---|---|
| [Correcciones del informe (observaciones 4, 5 y 6)](<../CORRECCIONES-INFORME.md>) | Análisis y propuestas del informe, fechados al 22-10-2026. |
| [Plan de entrenamiento (MobileNetV3-Small, V2)](<../PLAN-ENTRENAMIENTO.md>) | Plan histórico: no usar sus cifras como estado actual. |
| [Reconocimiento de prendas](<../README-v1.md>) | Versión histórica descartada. |
| [Resumen del método de entrenamiento](<../RESUMEN-METODO-ENTRENAMIENTO.md>) | Método con contexto histórico; estado vigente en el resumen nuevo. |
| [Terminología y teoría del entrenamiento](<../TEORIA-ENTRENAMIENTO.md>) | Referencia conceptual. |
| [Dudas y decisiones antes de procesar datos](<../utilidades-entrenamiento/modelo-general-destilacion/dudas.md>) | Guía del módulo; atender a fechas de mediciones y decisiones pendientes. |

## Utilidades auxiliares

| Documento | Propósito / estado |
|---|---|
| [Extensión Chrome: descargar imagen de producto](<../utilidades-entrenamiento/scraping-plugin-chrome/folder-destino/README.md>) | Guía del módulo; atender a fechas de mediciones y decisiones pendientes. |

## Archivos técnicos relacionados

- [Esquema base](../documentacion_dataset/schema.sql) y [creación de estructura](../documentacion_dataset/crear_estructura.sh).
- [Compose unificado (dataset + entrenamiento + API CPU)](../docker-compose.yaml) y [Compose entrenamiento por terminal](../utilidades-entrenamiento/docker-compose.yaml).
- [Configuración de entrenamiento](../utilidades-entrenamiento/configs/default.yaml) y [fuentes](../utilidades-entrenamiento/modelo-general-destilacion/sources.json).
- [Validador documental](validar_documentacion.py): ejecutar `python3 docs/validar_documentacion.py` desde la raíz. Comprueba enlaces locales, anclas y cobertura del índice, sin red ni escrituras.

## Mantenimiento

El [generador del manual DOCX](generar_manual_docx.py) mantiene sincronizado el Word con [su fuente de instalación](INSTALACION-NATIVA.md). Requiere `python-docx` en un entorno de edición y se ejecuta con `python docs/generar_manual_docx.py`; no es una dependencia de la API.


Al añadir un Markdown, enlazarlo aquí y especificar si es guía vigente, resultado fechado, referencia conceptual o antecedente. Actualizar cifras con fecha y origen. No presentar planificación como medición ni aprobación masiva como auditoría humana. Actualizar la referencia de API cuando cambien los handlers.
