# Dudas y decisiones antes de procesar datos

Las decisiones ya confirmadas por el usuario se aplican en `sources.json` y en el pipeline. Estas preguntas restantes no bloquean la auditoría local; sí deben resolverse antes de importar lotes amplios o usar proveedores.

## Datos y taxonomía

1. **Licencia de AIG:** no se encontró README, LICENSE ni manifiesto dentro de `AIG-Dataset/`. Se habilitó con base en tu confirmación de uso comercial libre. La procedencia y etiqueta original se conservan en SQLite.
2. **Hoodies:** AIG contiene 10.000 imágenes en `Hoodies`; se excluyen conforme a la regla de omitir clases que no existen en el catálogo actual.
3. **Fashion-MNIST:** no está en los directorios inspeccionados y seguirá fuera del dataset fotográfico de prendas; su baja resolución y escala de grises no sirve para sugerir atributos visuales de estas fotografías. ¿Se conserva únicamente como benchmark independiente?

## Proveedores, privacidad y límites

1. **NVIDIA NIM en nube:** queda seleccionado como opción sin costo según la disponibilidad/créditos de la cuenta. El modelo VLM alojado y sus límites pueden cambiar; confirma que el modelo elegido en `.env` aparece habilitado para visión en tu cuenta NIM.
2. **DeepSeek:** es de pago y se configura su clave en el mismo `.env`. ¿Cuál es el presupuesto o límite de gasto por lote que debemos usar? El CLI ya requiere un `--limit` explícito, pero no conoce el saldo de la cuenta.
3. **TOON:** se manda el contexto estructurado de la tarea en TOON dentro del texto del mensaje. Los proveedores compatibles exigen que el sobre HTTP/chat y la respuesta parseable sigan siendo JSON; no hay transporte TOON nativo configurado.
4. **Revisión humana:** todas las imágenes aceptadas por una IA se importan como `pendiente` y no son elegibles para entrenar hasta la aprobación humana. ¿Qué criterios usarás para aprobar o rechazar descripciones, colores y estilos? La IA puede descartar una imagen, pero no sustituye esta revisión.
5. **Tamaño y formatos:** se omiten archivos mayores de 200.000 bytes antes de calcular hash o llamar al proveedor; no se redimensionan ni recomprimen. En llamadas remotas solo se admiten JPEG, PNG, GIF y WebP. ¿Quieres ajustar el umbral o admitir otro formato?

## Categorías físicas

La carpeta y guía `dataset/superior/abrigos/` ya existen, están incluidas por `crear_estructura.sh` y el pipeline la crea al importar la categoría `abrigo`. No se agregó una clase nueva para abrigos. `Outwear` se mantiene excluida porque puede corresponder a abrigo o chaqueta y requiere una equivalencia explícita; se distingue de `sueter`, que tiene su carpeta y guía propias.
