# censura_tu_dni

Herramienta personal para preparar copias del DNI antes de enviarlas:
añade una marca de agua en diagonal, pasa a blanco y negro, quita los
metadatos y monta anverso y reverso en un PDF A4.

- Todo en local: ninguna llamada de red.
- Elimina EXIF/GPS (corrigiendo antes la orientación de las fotos del móvil).
- El PDF no lleva autor, título, fechas ni rutas.
- No escribe ficheros intermedios: solo el PDF que tú guardas.

## Requisitos

- Python 3.10 o superior con Tkinter.
- Pillow (y opcionalmente `pillow-heif` para fotos HEIC del iPhone; sin él
  se aceptan JPG y PNG).

## Instalación

### Windows

1. Instala Python desde <https://www.python.org/downloads/> (marca
   *Add python.exe to PATH*; Tkinter viene incluido).
2. En una terminal (PowerShell), dentro de la carpeta del proyecto:

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Linux

```bash
sudo apt install python3-venv python3-tk   # Debian/Ubuntu (Fedora: python3-tkinter)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Si `pillow-heif` no se instala en tu sistema, puedes quitarlo de
`requirements.txt`: la herramienta funcionará igual con JPG y PNG.

## Uso

Con el entorno activado:

```bash
python dni_marca.py
```

1. Elige la imagen del **anverso** y, si quieres, la del **reverso**.
2. Escribe el texto de la marca de agua (por ejemplo, para quién es la
   copia y para qué trámite). Se usa tal cual lo escribas.
3. Deja marcada o desmarca **Blanco y negro**.
4. **Vista previa** para ver el resultado, **Generar PDF** para guardarlo.

## Uso sin ventana

La lógica está separada de la interfaz:

```python
from pathlib import Path
import dni_marca

pagina, pdf = dni_marca.generar("anverso.jpg", "reverso.jpg", "Solo para trámite X", byn=True)
Path("dni.pdf").write_bytes(pdf)
```

## Pruebas

Usan imágenes sintéticas generadas en memoria (nada real ni nada en disco):

```bash
python -m unittest -v
```

## Licencia

MIT
