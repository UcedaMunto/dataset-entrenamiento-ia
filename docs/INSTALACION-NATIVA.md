# Instalación nativa del modelo entrenado y su API de reconocimiento de prendas

Versión de la API: 2.0.0 · Edición revisada 1.1 · 23 de octubre de 2026

[Documento Word con formato APA 7](Instalacion_nativa_API_prendas_APA7.docx) · [Índice](INDICE.md)

## Objetivo y alcance

Este manual permite instalar MobileNetV3-Small con sus pesos ya entrenados y publicar una API local que recibe una fotografía y devuelve una descripción de la prenda. Está dirigido a la persona que instala el servicio y a quien lo integra con otra aplicación. El procedimiento utiliza Ubuntu 24.04, Python 3.12, arquitectura x86-64 y CPU.

La secuencia de instalación es: comprobar el equipo, copiar el código y el checkpoint, instalar dependencias en un entorno virtual, iniciar la API, probar una fotografía y, después, habilitar el servicio permanente. Al finalizar se debe obtener HTTP 200 con el campo `descripcion_mas_probable`, sin ejecutar entrenamiento, copiar el dataset, utilizar GPU ni configurar proveedores de IA.

El checkpoint contiene los pesos ajustados, el catálogo de clases, la resolución de entrada y el umbral multietiqueta. La arquitectura se construye desde `train.py` sin ejecutar su entrenamiento. Se carga el checkpoint en CPU con `pretrained=False`: una vez instaladas las dependencias y copiados los archivos, la inferencia no descarga pesos adicionales ni consulta servicios externos.

El servicio clasifica la fotografía completa. Produce tipo, colores y estilos; la descripción es una plantilla formada con esas etiquetas. No detecta varias prendas ni determina material, marca o talla. Para una entrada útil, mostrar una sola prenda, completa y bien iluminada, con poco fondo distractor. Estas recomendaciones de captura no garantizan una predicción correcta.

El catálogo de tipos comprende abrigo, blusa, camisa, chaqueta, falda, pantalón, short, suéter y vestido. Camisa y camiseta comparten la clase `camisa`. La temporada almacenada en el dataset no es una salida de esta API.

## Entorno y archivos necesarios

Se necesita una terminal Bash, una cuenta con permiso para instalar paquetes del sistema, acceso de lectura a los archivos entregados y conexión a Internet durante la instalación. El puerto 8081 debe estar libre; puede sustituirse por otro puerto en todos los comandos. No se ha establecido un mínimo medido de RAM ni de núcleos: el tamaño del archivo de pesos no representa el consumo total del proceso.

Se fijan PyTorch 2.5.1 y torchvision 0.20.1 para mantener la compatibilidad con el proyecto; la documentación oficial publica esa combinación para CPU (PyTorch, s. f.). Una instalación en Windows, macOS o ARM requiere adaptar y verificar el procedimiento; no queda validada por esta guía.

Preparar una carpeta con estos archivos, conservando sus nombres:

```text
prendas-api/
  inference_api.py
  train.py
  requirements.txt
  modelos-compartidos/
    mobilenetv3-small-best.pt
```

Los archivos están en `utilidades-entrenamiento/` dentro del repositorio entregado. `train.py` es necesario porque la API importa la clase `MultiTaskMobileNet`. No copiar solo el archivo `.pt`: el programa necesita también la definición de arquitectura y las bibliotecas.

El hash SHA-256 esperado del checkpoint compartido es:

```text
79407f5537418bc258857fa54723d8e39b152505ad3a6f6a6ea4f97e1dfcb35c
```

Este valor identifica los pesos documentados. El checkpoint debe provenir de la entrega del proyecto; su hash permite comprobar que corresponde al archivo esperado. Si el resultado difiere, detener la instalación y confirmar la versión del modelo antes de continuar.

## Preparación del sistema

Abrir una terminal Bash en Ubuntu. Los siguientes comandos instalan Python, el módulo de entornos virtuales y curl; requieren permisos administrativos en el equipo de destino:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl
python3 --version
uname -m
```

Resultado esperado: Python 3.12.x y arquitectura `x86_64`. Ejecutar los pasos de copia y de instalación de Python como usuario normal; usar `sudo` solo en los comandos administrativos que lo indican. Si se utiliza otra plataforma, revisar primero la compatibilidad de las distribuciones de PyTorch; no asumir que estos binarios CPU sirven para cualquier arquitectura.

Copiar los cuatro archivos desde la entrega del proyecto. En el ejemplo, sustituir `/ruta/al/repositorio` por la ruta real que contiene `utilidades-entrenamiento`:

```bash
mkdir -p "$HOME/prendas-api/modelos-compartidos"
cd /ruta/al/repositorio/utilidades-entrenamiento
cp inference_api.py train.py requirements.txt "$HOME/prendas-api/"
cp modelos-compartidos/mobilenetv3-small-best.pt \
  "$HOME/prendas-api/modelos-compartidos/"
cd "$HOME/prendas-api"
sha256sum modelos-compartidos/mobilenetv3-small-best.pt
```

Resultado esperado: los cuatro archivos están presentes y el hash coincide exactamente con el documentado. Comprobar también que la cuenta de ejecución puede leer el checkpoint. No ejecutar `train.py` ni inicializar SQLite.

## Instalación de dependencias

Crear el entorno virtual en la ubicación definitiva de instalación. Un entorno virtual contiene rutas del equipo donde se creó: si se traslada el servicio, recrearlo en el destino en vez de copiar `.venv` (Python Software Foundation, s. f.). Activarlo antes de instalar paquetes:

```bash
cd "$HOME/prendas-api"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.5.1 torchvision==0.20.1 \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pip check
```

El índice CPU instala PyTorch sin requerir un controlador NVIDIA. `requirements.txt` fija Pillow 10.2.0, PyYAML 6.0.2, FastAPI 0.115.12, python-multipart 0.0.20 y Uvicorn 0.34.2. PyYAML se necesita para importar el módulo de arquitectura. FastAPI utiliza python-multipart para procesar archivos enviados mediante formularios (FastAPI, s. f.).

Resultado esperado de `pip check`: `No broken requirements found.` Las versiones impresas deben ser `2.5.1+cpu` y `0.20.1+cpu`. Si hay errores de resolución, no continuar con el arranque hasta corregir el entorno. Los comandos fijan bibliotecas principales, pero no bloquean todas las dependencias transitivas; guardar el inventario de versiones instalado:

```bash
python -m pip freeze > dependencias-instaladas.txt
python -c 'import torch, torchvision; print(torch.__version__); print(torchvision.__version__)'
```

## Configuración y arranque de la API

Desde la carpeta de instalación y con el entorno activado, configurar la ubicación absoluta del checkpoint y los hilos de CPU:

```bash
cd "$HOME/prendas-api"
source .venv/bin/activate
export MODEL_CHECKPOINT="$PWD/modelos-compartidos/mobilenetv3-small-best.pt"
export API_CPU_THREADS=4
python -m uvicorn inference_api:app \
  --host 127.0.0.1 --port 8081 --workers 1
```

Uvicorn permite fijar dirección, puerto y número de procesos mediante opciones de ejecución (Uvicorn, s. f.). Se utiliza un proceso para cargar una sola instancia del modelo. `API_CPU_THREADS` controla los hilos de PyTorch; no fija el número total de clientes. La implementación limita a dos las inferencias que pueden entrar simultáneamente en su sección de ejecución.

`API_CPU_THREADS` debe ser un entero positivo; el valor 4 es el predeterminado, no una medición de capacidad del equipo. La variable `MODEL_CHECKPOINT` se lee al importar el módulo; si cambia, reiniciar el proceso. Si se omite, la API busca el archivo compartido en `modelos-compartidos/` junto a `inference_api.py`. Este comportamiento permite usar la estructura mínima anterior sin rutas dependientes de otro entorno.

Resultado esperado: Uvicorn informa que completó el arranque y está escuchando en `http://127.0.0.1:8081`. Si falla la carga del checkpoint, el arranque no se completa y el servicio puede no aceptar conexiones. Mantener esta terminal abierta durante la primera prueba. No utilizar `--reload` para el servicio permanente. Si el puerto 8081 está ocupado, elegir otro, por ejemplo 8082, y sustituirlo en todas las pruebas y clientes. Detener una ejecución manual con Ctrl+C.

## Verificación y envío de una imagen

En otra terminal, comprobar disponibilidad:

```bash
curl --fail-with-body http://127.0.0.1:8081/health
```

La respuesta esperada tras cargar el modelo es:

```json
{"status":"ok","device":"cpu"}
```

Abrir `http://127.0.0.1:8081/docs`, seleccionar `POST /v1/predict`, pulsar “Try it out”, adjuntar la fotografía en `garment_image` y ejecutar. La interfaz se genera a partir del contrato de la API.

Para hacer la misma solicitud desde una terminal, sustituir la ruta por una fotografía real:

```bash
curl --fail-with-body http://127.0.0.1:8081/v1/predict \
  -F 'garment_image=@/ruta/a/prenda.jpg'
```

El campo requerido es exactamente `garment_image`; el nombre del archivo puede variar. El cuerpo es `multipart/form-data`, no JSON ni una cadena base64. La opción `-F` de curl construye el formulario: no establecer manualmente su encabezado `Content-Type`, porque debe incluir el separador multipart. No se necesita `person_image`.

La API admite JPEG, PNG y WebP, hasta 10 MiB (10.485.760 bytes) y 25.000.000 de píxeles por imagen. El tamaño en píxeles se calcula como ancho por alto; no basta con cambiar la extensión de un archivo para convertirlo a un formato admitido. El servidor decodifica la imagen, la convierte a RGB y la redimensiona a 224 × 224 según el checkpoint compartido.

Ejemplo abreviado e ilustrativo de respuesta; los valores concretos dependen de la fotografía:

```json
{
  "descripcion_mas_probable": "Tipo probable: camisa; colores probables: azul; estilos probables: casual.",
  "tipo_prenda": {"valor": "camisa", "probabilidad": 0.95},
  "colores": [
    {"valor": "azul", "probabilidad": 0.90, "supera_umbral": true}
  ],
  "estilos": [
    {"valor": "casual", "probabilidad": 0.85, "supera_umbral": true}
  ],
  "umbral_multietiqueta": 0.5,
  "device": "cpu",
  "latencia_ms": {
    "preprocesamiento_imagen": 3.0,
    "inferencia_imagen": 20.0,
    "total_servidor": 23.0
  }
}
```

`descripcion_mas_probable` contiene el texto listo para mostrar. `tipo_prenda` incluye la categoría de mayor puntuación y su probabilidad; la API siempre selecciona un tipo y no aplica un umbral de rechazo a esa categoría. Una puntuación baja no se transforma automáticamente en «desconocido».

`colores` y `estilos` incluyen hasta cinco candidatos por propiedad, con `valor`, `probabilidad` y `supera_umbral`. La descripción utiliza solo candidatos que alcanzan el umbral del checkpoint, actualmente 0,5. Si ninguno lo alcanza, lo indica en el texto. Una probabilidad es una puntuación del modelo, no una garantía de acierto ni evidencia de calibración.

`latencia_ms.preprocesamiento_imagen` mide la transformación de la imagen ya decodificada. `inferencia_imagen` incluye la espera para entrar al semáforo y la ejecución del modelo. `total_servidor` es la suma de ambas mediciones: excluye transferencia HTTP, decodificación y parte de la construcción de la respuesta. Para medir la experiencia del cliente se debe cronometrar la solicitud completa.

## Integración desde otra aplicación

El cliente debe leer `descripcion_mas_probable` para mostrar el texto y utilizar las propiedades estructuradas si necesita filtros o indicadores de confianza. Ejemplo con Python; instalar requests en el entorno del cliente si no está disponible:

```bash
python -m pip install requests==2.32.3
```

```python
import requests

url = "http://127.0.0.1:8081/v1/predict"
with open("prenda.jpg", "rb") as image:
    response = requests.post(
        url,
        files={"garment_image": ("prenda.jpg", image, "image/jpeg")},
        timeout=60,
    )
response.raise_for_status()
print(response.json()["descripcion_mas_probable"])
```

Los errores HTTP deben tratarse antes de acceder al JSON de éxito; `raise_for_status()` cumple esa función en el ejemplo. El tiempo de espera de 60 segundos es un valor del cliente, no una promesa de latencia del modelo.

La aplicación 2.0.0 conserva `/v1/predict`, pero cambia el contrato anterior: ahora solo requiere la imagen de la prenda y devuelve las propiedades directamente en el objeto raíz. Los clientes anteriores deben dejar de depender de `prediccion_combinada`, `predicciones_por_imagen` y `metodo_combinacion`. La ruta y la versión del esquema de respuesta no deben confundirse.

## Ejecución permanente en Ubuntu

Después de completar la prueba manual, detener ese proceso con Ctrl+C para liberar el puerto y registrar un servicio systemd. Esta etapa es opcional para una prueba puntual; permite supervisar el proceso y arrancarlo al iniciar el equipo (systemd, s. f.-a). El ejemplo supone que la carpeta definitiva es `/home/ubuntu/prendas-api`, el usuario es `ubuntu` y el grupo es `ubuntu`. Sustituir esas rutas y nombres si el equipo utiliza otros; no ejecutar el servicio con una ruta de ejemplo inexistente.

Crear la unidad con un editor administrativo:

```bash
sudo nano /etc/systemd/system/prendas-api.service
```

Contenido de la unidad:

```ini
[Unit]
Description=API CPU de reconocimiento de prendas
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/prendas-api
Environment=API_CPU_THREADS=4
ExecStart=/home/ubuntu/prendas-api/.venv/bin/python -m uvicorn \
  inference_api:app --host 127.0.0.1 --port 8081 --workers 1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

La unidad utiliza la ruta predeterminada del checkpoint junto a `inference_api.py`. Para otro modelo, añadir una directiva `Environment=MODEL_CHECKPOINT=/ruta/absoluta/modelo.pt`. Las variables exportadas en una terminal no configuran por sí solas la unidad del sistema. La barra inversa al final de `ExecStart` continúa el comando en la línea siguiente (systemd, s. f.-b).

Comprobar la sintaxis antes de activar y revisar el servicio:

```bash
sudo systemd-analyze verify /etc/systemd/system/prendas-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now prendas-api
sudo systemctl status prendas-api --no-pager
sudo journalctl -u prendas-api -n 50 --no-pager
curl --fail-with-body http://127.0.0.1:8081/health
```

Resultado esperado: `systemctl status` muestra `active (running)` y la consulta de salud responde HTTP 200. La cuenta del servicio debe poder leer código, checkpoint y entorno virtual. La unidad utiliza el ejecutable de `.venv` y no requiere activación interactiva.

Para detenerlo, ejecutar `sudo systemctl stop prendas-api`. Después de cambiar código o un checkpoint compatible, ejecutar `sudo systemctl restart prendas-api` y repetir las pruebas de salud e imagen. Si cambia el archivo `.service`, ejecutar antes `sudo systemctl daemon-reload`.

## Acceso desde otro equipo

El servicio de este manual escucha en localhost. Para usarlo desde otro equipo mediante SSH:

```bash
ssh -L 8081:127.0.0.1:8081 usuario@servidor
```

Con el túnel abierto, usar `http://127.0.0.1:8081` en el equipo cliente. Si se requiere acceso público, definir un despliegue adicional con proxy, TLS, autenticación y límites de solicitudes. La API actual no incluye autenticación y no habilita orígenes CORS de navegador; una página de otro origen necesita una configuración específica o un proxy del mismo origen.

## Diagnóstico de fallos

La primera comprobación es distinguir un fallo de conexión de una respuesta HTTP con error. Si curl no conecta, revisar que el proceso siga activo y que cliente, puerto y túnel coincidan. Si existe respuesta HTTP, conservar su campo `detail` y consultar los registros del servicio.

Tabla 1

*Diagnóstico de incidencias de instalación y consumo*

| Síntoma | Causa que debe comprobarse | Acción |
|---|---|---|
| No conecta o puerto ocupado | Proceso detenido, puerto equivocado u otro servicio escuchando | Revisar Uvicorn o systemctl; consultar `ss -ltnp`; usar un puerto libre en servidor y cliente. |
| Error al importar | Entorno incorrecto o archivos/dependencias incompletos | Activar `.venv`, ejecutar desde la carpeta de instalación y revisar `python -m pip check`. |
| Fallo al cargar pesos | Ruta, permisos o checkpoint incompatible | Comprobar `MODEL_CHECKPOINT`, lectura del archivo, hash y catálogo; revisar el error de arranque. |
| HTTP 422 | Campo ausente, archivo vacío o contenido ilegible | Enviar el archivo real mediante `-F` y el nombre `garment_image`. |
| HTTP 413 o 415 | Exceso de bytes/píxeles o formato no admitido | Preparar una imagen dentro de los límites; convertir el archivo si el formato no corresponde. |
| HTTP 503 | Modelo no disponible dentro de la aplicación | Revisar la carga del checkpoint y los registros; no interpretar este código como fallo de clasificación. |
| Funciona con curl, pero no en navegador | Origen CORS diferente | Usar un proxy del mismo origen o definir los orígenes permitidos de forma explícita. |

Si un cliente anterior recibe HTTP 422 y el detalle exige `person_image`, sigue conectado a una instancia con el contrato antiguo. Reiniciar el servicio con el código actualizado y revisar su `/openapi.json`; el cuerpo requerido debe contener solo `garment_image`.

## Actualización y recuperación

Antes de actualizar, conservar una copia del código, checkpoint e inventario `dependencias-instaladas.txt` que funcionaban. No actualizar únicamente los pesos si cambia la arquitectura o el catálogo. Una vez sustituida una entrega compatible, reiniciar el proceso y repetir las pruebas de aceptación. Si falla, restaurar el conjunto anterior y reiniciar. Si cambian dependencias, preparar un entorno virtual nuevo con el inventario compatible en lugar de mezclar instalaciones sin registro.

## Criterios de aceptación

La instalación queda aceptada cuando se cumplen todos estos puntos: el hash coincide con la entrega; `pip check` no reporta incompatibilidades; el proceso completa el arranque; `/health` responde `status=ok` y `device=cpu`; y una petición con una sola fotografía devuelve HTTP 200 con una descripción no vacía, tipo, colores y estilos. Para una instalación permanente, comprobar además `active (running)` y repetir la petición después de un reinicio del servicio.

Estas comprobaciones acreditan funcionamiento técnico, no exactitud para todas las prendas ni capacidad bajo una carga no medida. El estado de salud no sustituye la prueba de inferencia. Una respuesta semánticamente incorrecta puede seguir siendo HTTP 200 y debe evaluarse con imágenes y etiquetas de referencia.

## Verificación de esta entrega

La instalación se comprobó en un entorno virtual temporal con Python 3.12, PyTorch 2.5.1+cpu y torchvision 0.20.1+cpu. Se copiaron únicamente los archivos de la estructura mínima y el checkpoint compartido. La API inició sin dataset en su carpeta de ejecución, `/health` informó CPU disponible y una solicitud multipart con una fotografía real devolvió HTTP 200, descripción y propiedades. El esquema OpenAPI exigió únicamente `garment_image`.

En la validación de la entrega anterior pasaron 19 pruebas automatizadas de entrenamiento e inferencia, incluidas solicitudes HTTP de una imagen y validación de errores. Esta comprobación valida el arranque y el contrato; no constituye una nueva evaluación de precisión ni una prueba de carga. Esta revisión del manual mantiene el código de la API y sus pesos; no vuelve a entrenar el modelo ni vuelve a medir su precisión. Los servicios previamente iniciados deben reiniciarse con el código actualizado para adoptar el nuevo contrato.

La presentación utiliza tamaño carta, márgenes de 2,54 cm, doble interlineado, numeración superior derecha y referencias con sangría francesa. El texto usa Times New Roman de 12 puntos y el código Courier New de 10 puntos, siguiendo las pautas aplicables de APA 7 (American Psychological Association, 2022, 2024, 2026). La portada se adapta al carácter técnico del documento.

## Referencias

American Psychological Association. (2022, julio). *Line spacing*. APA Style. https://apastyle.apa.org/style-grammar-guidelines/paper-format/line-spacing

American Psychological Association. (2024, noviembre). *Paper format*. APA Style. https://apastyle.apa.org/style-grammar-guidelines/paper-format

American Psychological Association. (2026, febrero). *Font*. APA Style. https://apastyle.apa.org/style-grammar-guidelines/paper-format/font

FastAPI. (s. f.). *Request files*. https://fastapi.tiangolo.com/tutorial/request-files/

Python Software Foundation. (s. f.). *venv—Creation of virtual environments*. Python 3.12 documentation. https://docs.python.org/3.12/library/venv.html

PyTorch. (s. f.). *Previous PyTorch versions*. https://pytorch.org/get-started/previous-versions/

systemd. (s. f.-a). *systemd.service—Service unit configuration*. https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html

systemd. (s. f.-b). *systemd.syntax—General syntax of systemd configuration files*. https://www.freedesktop.org/software/systemd/man/latest/systemd.syntax.html

Uvicorn. (s. f.). *Settings*. https://uvicorn.dev/settings/
