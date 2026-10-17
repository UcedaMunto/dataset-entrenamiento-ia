# Camisa (clase unificada)

## Criterio de inclusión

Clase única para prendas superiores con abertura frontal y cuello, así como prendas superiores cerradas sin abertura frontal completa. Incluye las variantes que comúnmente se denominan camisetas; todas se registran como `camisa` en `dataset/superior/camisas/`. Durante la ingesta, la etiqueta de fuente `camiseta` se normaliza a `camisa`; el nombre original se conserva en `prenda_imagen.etiqueta_fuente` para trazabilidad.

## No confundir con

- **Blusa:** prenda superior cuyo diseño y construcción se etiquetan como blusa, aunque también tenga botones.
- **Chaqueta:** prenda exterior pensada para llevar sobre otra prenda.

No se separa esta clase por tipo de cuello, abertura o construcción. Si no se distingue con seguridad entre camisa y otra categoría, marcar para revisión. Etiquetar color y estilo por separado.

Para la ubicación y el catálogo de categorías, consulta la [guía de prendas superiores](../README.md); para registrar imágenes y etiquetas, la [guía general del dataset](../../../documentacion_dataset/README.md). Índice: [dataset](../../README.md).
