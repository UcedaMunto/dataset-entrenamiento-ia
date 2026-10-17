# Dataset de prendas

Las imágenes se organizan por zona del cuerpo y tipo de prenda. Las etiquetas, propiedades, estado de revisión y rutas de imagen se registran en SQLite; no se usa un JSON o CSV por prenda como fuente de verdad.

Consulta la [documentación del dataset](../documentacion_dataset/README.md) para:

- Crear las carpetas y `metadata.sqlite` con [`crear_estructura.sh`](../documentacion_dataset/crear_estructura.sh).
- Consultar las siete tablas y las etiquetas iniciales en [`schema.sql`](../documentacion_dataset/schema.sql).
- Registrar prendas, imágenes, propiedades y descripciones revisables en SQLite.
- Preparar los datos para entrenar MobileNetV3-Small.

Guías de clasificación por zona: [superior](./superior/README.md), [inferior](./inferior/README.md) e [inferior_superior](./inferior_superior/README.md). Cada tipo también tiene una guía dentro de su propia carpeta.

La taxonomía actual de carpetas y del catálogo es el alcance inicial, no el inventario completo de prendas posible. Consulta la sección de [factibilidad y alcance](../documentacion_dataset/README.md#factibilidad-y-alcance-del-mvp) antes de añadir nuevas categorías.
