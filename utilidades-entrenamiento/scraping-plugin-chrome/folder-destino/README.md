# Extensión Chrome: descargar imagen de producto

Extensión Manifest V3 que descarga una imagen con un clic en el icono de Chrome. Busca imágenes de la pestaña activa, prioriza imágenes grandes y señales de producto/galería, y usa Open Graph como alternativa. El nombre de archivo se basa en el título de la página.

## Instalar en Chrome

1. Abre `chrome://extensions`.
2. Activa **Modo de desarrollador**.
3. Selecciona **Cargar extensión sin empaquetar**.
4. Elige esta carpeta `folder-destino/`.
5. Abre una ficha de producto y pulsa el icono de la extensión. El indicador del icono muestra `OK` si inició la descarga o `ERR` si no encontró una imagen.

## Carpeta de descarga

Chrome no permite a una extensión escribir directamente en una ruta absoluta del proyecto. Por defecto solicita una ruta relativa:

```text
folder-destino/
```

Normalmente los archivos quedan en `~/Downloads/folder-destino/`. Para guardarlos en esta carpeta del proyecto, cambia una sola vez la ubicación base de descargas de Chrome a:

```text
/home/uceda/Documents/consolidacion del proyecto/modelo-reconocimiento-prendas/utilidades-entrenamiento/scraping-plugin-chrome
```

Con esa ubicación, Chrome guarda las imágenes en `scraping-plugin-chrome/folder-destino/`, junto a la extensión. Los archivos de imagen descargados están excluidos de Git por el `.gitignore` de esta carpeta. La ubicación base es global para las descargas normales de Chrome; si no deseas cambiarla, conserva la predeterminada y usa `~/Downloads/folder-destino/`. La ubicación base se configura en `chrome://settings/downloads`.

## Alcance y permisos

- No descarga la página completa ni todas las imágenes: selecciona una candidata al hacer clic.
- La heurística puede escoger una imagen incorrecta en tiendas con galerías complejas, anuncios o fichas sin metadatos; revisa la imagen resultante.
- No intenta saltar inicios de sesión, muros de pago, controles anti-bot ni restricciones de acceso. Solo descarga una imagen accesible desde la pestaña abierta.
- Usa `activeTab` y `scripting` para leer las imágenes al pulsar el icono, y `downloads` para guardar el archivo. No solicita acceso permanente a todos los sitios.
