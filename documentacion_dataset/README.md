# Documentación del dataset

Esta carpeta documenta la estructura de imágenes y el registro de metadatos en SQLite para el módulo de reconocimiento de prendas.

## Fuente de verdad

- Las imágenes permanecen en carpetas organizadas por zona y tipo de prenda dentro de `dataset/`.
- Los datos de cada prenda, las rutas a sus imágenes y las etiquetas se guardan en `dataset/metadata.sqlite`.
- No se usa un JSON por prenda ni un CSV como fuente de verdad. El archivo `descripcion.json` puede usarse solo como formato de intercambio si se desarrolla una importación/exportación explícita.
- [`schema.sql`](./schema.sql) define las cuatro tablas y las propiedades iniciales. [`crear_estructura.sh`](./crear_estructura.sh) prepara los directorios y crea la base a partir de ese esquema.

Para una visión del objetivo global y del flujo de entrenamiento, consulta el [README vigente del proyecto](../README.md). El [índice del dataset](../dataset/README.md) enlaza las guías de clasificación por zona y tipo.

## Estructura de carpetas

Desde la raíz del proyecto, ejecutar:

```bash
bash documentacion_dataset/crear_estructura.sh
```

Para ejecutarlo desde otro directorio, indica la ruta del script. Este resuelve la raíz del proyecto a partir de su propia ubicación. Requiere Python 3 con su módulo estándar `sqlite3`. Es idempotente: crea carpetas faltantes, conserva archivos/directorios existentes y crea o completa las tablas y el catálogo sin borrar datos. No ejecuta migraciones sobre una base ya existente; si se modifica el esquema, se debe definir y aplicar una migración explícita.

```text
dataset/
├── metadata.sqlite
├── superior/
│   ├── abrigos/
│   ├── blusas/
│   ├── camisas/
│   ├── chaquetas/
│   └── sueteres/
├── inferior/
│   ├── faldas/
│   │   ├── FALDA-1/
│   │   └── FALDA-2/
│   ├── pantalones/
│   └── shorts/
└── inferior_superior/
    └── vestido/
```

Cada carpeta identificada (`FALDA-1`, `CAMISA-1`, etc.) representa una prenda física. Guarda dentro sus imágenes, por ejemplo:

```text
dataset/inferior/faldas/FALDA-1/
├── frente.jpg
├── espalda.jpg
└── detalle.jpg
```

`metadata.sqlite` se crea en `dataset/` al ejecutar el script. La base, las imágenes locales, los pesos y los resultados de experimentos están excluidos de Git por [`.gitignore`](../.gitignore); conserva en Git las guías README y el esquema.

La categoría `camisa` reúne camisas y camisetas bajo una sola etiqueta y carpeta (`superior/camisas/`). El catálogo inicial tiene nueve tipos: abrigo, blusa, camisa, chaqueta, falda, pantalón, short, suéter y vestido.

## Modelo de datos SQLite

Relaciones:

```text
prenda 1 ─── N prenda_imagen
prenda 1 ─── N valor_propiedad_prenda N ─── 1 catalogo_propiedad
```

- **`prenda`**: una fila por prenda física. Conserva código, carpeta/categoría, split de entrenamiento y estado de revisión.
- **`prenda_imagen`**: una fila por foto. Relaciona una prenda con una o varias rutas relativas a `dataset/`.
- **`catalogo_propiedad`**: define las propiedades permitidas, por ejemplo `tipo_prenda`, `color`, `estilo`, `largo` o `patron`; puede documentar opciones admitidas en `valores_permitidos`.
- **`valor_propiedad_prenda`**: relaciona cada prenda con el valor de una propiedad. Las propiedades con varios valores usan varias filas; por ejemplo, una prenda con dos colores tiene dos valores asociados a la propiedad `color`.

El esquema completo e inicialización del catálogo están en [`schema.sql`](./schema.sql). SQLite debe abrirse con claves foráneas activadas (`PRAGMA foreign_keys = ON`) en cada conexión. Las rutas de imágenes son relativas al directorio `dataset/`, nunca rutas absolutas de una laptop.

### Ejemplo conceptual

Prenda `FALDA-1`:

| Tabla | Filas relacionadas |
|---|---|
| `prenda` | `FALDA-1`, categoría `inferior/faldas`, split `train` |
| `prenda_imagen` | `inferior/faldas/FALDA-1/frente.jpg`, `.../espalda.jpg` |
| `valor_propiedad_prenda` | `tipo_prenda = falda`, `color = azul`, `estilo = elegante`, `largo = midi` |
| `catalogo_propiedad` | Define que `tipo_prenda`, `color`, `estilo` y `largo` son propiedades válidas |

Cada etiqueta se debe elegir del vocabulario acordado. `valores_permitidos` es un JSON con las opciones iniciales propuestas; el equipo debe revisarlas antes de usarlas. Tipo de prenda es una propiedad de valor único; color y estilo permiten varios valores. Si una propiedad está marcada como de valor único, la aplicación de anotación debe impedir agregar más de un valor a la misma prenda.

### Ejemplo de registro SQL

Con la base inicializada con `schema.sql`, se puede registrar una prenda con dos fotos, un tipo, dos colores y un estilo así:

```sql
PRAGMA foreign_keys = ON;
BEGIN;

INSERT INTO prenda
    (codigo, ruta_categoria, split, estado_revision, apta_para_entrenamiento)
VALUES
    ('FALDA-1', 'inferior/faldas', 'train', 'aprobado', 1);

INSERT INTO prenda_imagen
    (id_prenda, ruta_relativa, vista, es_fotografia_real, fuente, permiso_uso)
SELECT id_prenda, 'inferior/faldas/FALDA-1/frente.jpg',
       'frente', 1, 'propia', 'documentado'
FROM prenda WHERE codigo = 'FALDA-1';

INSERT INTO prenda_imagen
    (id_prenda, ruta_relativa, vista, es_fotografia_real, fuente, permiso_uso)
SELECT id_prenda, 'inferior/faldas/FALDA-1/espalda.jpg',
       'espalda', 1, 'propia', 'documentado'
FROM prenda WHERE codigo = 'FALDA-1';

INSERT INTO valor_propiedad_prenda (id_prenda, id_propiedad, valor)
SELECT p.id_prenda, cp.id_propiedad, etiquetas.valor
FROM prenda AS p
JOIN catalogo_propiedad AS cp
JOIN (SELECT 'tipo_prenda' AS propiedad, 'falda' AS valor
      UNION ALL SELECT 'color', 'azul'
      UNION ALL SELECT 'color', 'negro'
      UNION ALL SELECT 'estilo', 'elegante') AS etiquetas
  ON cp.codigo = etiquetas.propiedad
WHERE p.codigo = 'FALDA-1';

COMMIT;
```

## Cómo registrar una prenda

1. Escoge la zona y el tipo adecuados: `superior/`, `inferior/` o `inferior_superior/`.
2. Crea una carpeta de prenda con código único, por ejemplo `dataset/inferior/faldas/FALDA-3/`.
3. Copia en esa carpeta una o varias fotos autorizadas de la misma prenda. Usa nombres descriptivos, sin espacios y con extensión real (`frente.jpg`, `espalda.jpg`).
4. Inserta una fila en `prenda` con el código, la ruta de categoría, el split y estado de revisión.
5. Inserta una fila en `prenda_imagen` por cada imagen, con su ruta relativa, vista, fuente/permiso y si es una fotografía real.
6. Registra cada etiqueta como una fila en `valor_propiedad_prenda`, ligada al registro correspondiente de `catalogo_propiedad`.
7. Aprueba la muestra solo cuando la categoría, las etiquetas, las imágenes y los permisos estén revisados.
8. Mantén todas las fotos de una prenda en el mismo split (`train`, `val` o `test`). La división se guarda en `prenda`, no por foto.

No inventar etiquetas cuando algo no sea visible. Un valor ausente representa “no anotado/no determinable”; los valores negativos deben anotarse solo cuando la guía de la propiedad los defina.

## Preparar los datos para MobileNetV3-Small

Cuando el dataset esté suficientemente completo y revisado, el proceso de entrenamiento deberá:

1. Abrir `dataset/metadata.sqlite` con claves foráneas activadas.
2. Seleccionar prendas aprobadas y aptas para entrenamiento, con split definido.
3. Consultar sus valores en `valor_propiedad_prenda` y el nombre/tipo en `catalogo_propiedad`.
4. Consultar las rutas de sus fotos en `prenda_imagen`, comprobar que existan bajo `dataset/` y excluir ilustraciones/demo.
5. Cargar imágenes, redimensionarlas al tamaño configurado y construir el lote de MobileNetV3-Small.
6. Entrenar tipo de prenda como clasificación de una etiqueta y colores/estilos como clasificación multi-etiqueta.
7. Mantener todas las fotos de la misma prenda en el split indicado en `prenda`.
8. Guardar pesos y métricas en `models/` y resultados del experimento fuera del dataset.

Los ejemplos de documentación no sustituyen fotografías reales autorizadas ni son suficientes para entrenar. Primero se llena y revisa la base; después se implementan los scripts Docker de entrenamiento.

## Factibilidad y alcance del MVP

El plan actual es **factible como MVP acotado**, pero la inicialización de datos no equivale a tener el entrenamiento listo:

- **Preparación local, lista:** el script crea la jerarquía de carpetas y `dataset/metadata.sqlite` usando únicamente Bash y Python 3 estándar. No depende de instalar `sqlite3` como programa.
- **Modelo de datos, listo para poblar:** las cuatro tablas cubren prendas, varias imágenes por prenda, catálogo de propiedades y valores múltiples. El split reside en la prenda, como requiere el entrenamiento.
- **Entrenamiento, pendiente:** en el repositorio aún no están implementados `train.py`, `predict.py`, `Dockerfile`, `compose.yaml` ni la configuración citada por el plan. Por tanto, los comandos Docker son una meta, no instrucciones ejecutables todavía.
- **Datos, pendientes:** la estructura no contiene fotografías de entrenamiento ni anotaciones completas. Las carpetas `FALDA-1` y `FALDA-2` son solo ejemplos vacíos; no cuentan como muestras.
- **Taxonomía inicial definida:** el catálogo y las carpetas cubren nueve tipos (`abrigo`, `blusa`, `camisa`, `chaqueta`, `falda`, `pantalon`, `short`, `sueter`, `vestido`). `camisa` es la etiqueta única tanto para camisas como para camisetas. Las guías de zona también mencionan sujetadores, ropa interior y ropa de baño, categorías que quedan fuera del catálogo y requieren una decisión explícita antes de incorporarse. El README principal propone empezar con cinco de los nueve tipos; confirmar ese subconjunto y reunir ejemplos suficientes por clase antes de entrenar.
- **Recursos, por validar:** MobileNetV3-Small con lote y resolución pequeños ofrece un punto de partida razonable para las GPU descritas, y CPU es una alternativa funcional más lenta. No se puede garantizar rendimiento ni memoria sin los modelos exactos de GPU, el driver y una prueba corta con datos reales.

Conclusión: se puede iniciar ahora la recolección y el registro con las categorías actuales, pero no es viable medir calidad ni entrenar el MVP hasta acordar las clases efectivas, reunir fotografías autorizadas y desarrollar el flujo Docker/entrenamiento. El [README del proyecto](../README.md#factibilidad-y-estado-de-la-versión-2) resume este estado a nivel del plan.

## Archivos de esta carpeta

- [`crear_estructura.sh`](./crear_estructura.sh): crea carpetas y base SQLite sin borrar ni sobrescribir contenido existente.
- [`schema.sql`](./schema.sql): crea las cuatro tablas e inserta las propiedades iniciales.
