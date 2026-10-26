# Conjunto portable de prueba — API de descripción de prendas

Carpeta con seguimiento de Git para ejecutar la prueba de la API de descripción de prendas en el **equipo de producción**, sin necesidad del dataset completo ni del nodo de entrenamiento.

## Contenido

- `manifest.json`: catálogo de clases, umbral multietiqueta, y una entrada por imagen con:
  - `archivo`: ruta relativa a esta carpeta.
  - `codigo`: identificador de la prenda.
  - `tipo_prenda`, `colores`, `estilos`: etiquetas de referencia.
  - `sha256`: integridad de la imagen copiada.
- `inferior/`, `inferior_superior/`, `superior/`: 1.424 imágenes `.jpg` (una por prenda del split `test`), organizadas como en `dataset/`.

## Origen

Generado desde `dataset/metadata.sqlite` con el criterio:

```
split = 'test' AND estado_revision = 'aprobado'
AND apta_para_entrenamiento = 1 AND es_fotografia_real = 1
```

Checkpoint de referencia: [`utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt`](../../utilidades-entrenamiento/modelos-compartidos/mobilenetv3-small-best.pt).

## Uso

La prueba la ejecuta la API de pruebas (`test-api`, puerto 8082):

```bash
docker compose up -d --build test-api
curl -X POST "http://127.0.0.1:8082/test/run"          # prueba completa
curl "http://127.0.0.1:8082/test/results"              # reportes guardados
```

Diseño de la prueba: [`docs/DSR-PRUEBA-API.md`](../../docs/DSR-PRUEBA-API.md).
