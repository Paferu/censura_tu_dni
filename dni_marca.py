"""Prepara copias del DNI con marca de agua y las monta en un PDF A4.

Todo ocurre en memoria y en local: no hay llamadas de red ni ficheros
intermedios. La lógica (funciones de arriba) es independiente de la
interfaz Tkinter (clase App), así que se puede usar y probar sin ventana.
"""

import io
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:  # HEIC opcional: solo si pillow-heif está instalado
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIC = True
except ImportError:
    HEIC = False

# A4 a 300 ppp
DPI = 300
A4 = (2480, 3508)
MARGEN = 200  # px alrededor de cada cara

FUENTES = [
    "arial.ttf",  # Windows (Pillow busca en C:\Windows\Fonts)
    "C:/Windows/Fonts/arial.ttf",
    "DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
]


def cargar_fuente(tamano):
    for nombre in FUENTES:
        try:
            return ImageFont.truetype(nombre, tamano)
        except OSError:
            continue
    return ImageFont.load_default(size=tamano)


def abrir_limpia(ruta):
    """Abre la imagen, aplica la orientación EXIF y devuelve una copia RGB sin metadatos."""
    with Image.open(ruta) as img:
        img = ImageOps.exif_transpose(img)
        rgb = img.convert("RGB")
    # Imagen nueva con solo los píxeles: no arrastra EXIF, GPS, ICC ni nada de .info
    limpia = Image.new("RGB", rgb.size)
    limpia.paste(rgb)
    return limpia


def poner_marca(img, texto, angulo=35, opacidad=90):
    """Repite `texto` en mosaico diagonal sobre toda la imagen."""
    if not texto.strip():
        return img.copy()
    w, h = img.size
    fuente = cargar_fuente(max(12, min(w, h) // 14))
    trazo = max(1, fuente.size // 20)
    caja = fuente.getbbox(texto + "   ", stroke_width=trazo)
    paso_x = caja[2] - caja[0]
    paso_y = int((caja[3] - caja[1]) * 2.2)

    # Capa cuadrada que cubre la diagonal para que al girarla no queden huecos
    lado = int(math.hypot(w, h)) + 2 * paso_y
    capa = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(capa)
    for fila, y in enumerate(range(0, lado, paso_y)):
        desfase = (fila % 2) * paso_x // 2  # filas al tresbolillo
        for x in range(-paso_x + desfase, lado, paso_x):
            dibujo.text(
                (x, y), texto, font=fuente,
                fill=(60, 60, 60, opacidad),
                stroke_width=trazo, stroke_fill=(255, 255, 255, opacidad),
            )
    capa = capa.rotate(angulo, resample=Image.BICUBIC)
    izq, arr = (lado - w) // 2, (lado - h) // 2
    capa = capa.crop((izq, arr, izq + w, arr + h))

    return Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")


def procesar_cara(ruta, texto, byn=True):
    img = abrir_limpia(ruta)
    if byn:
        img = img.convert("L").convert("RGB")
    return poner_marca(img, texto)


def montar_pagina(caras):
    """Coloca las caras una encima de otra, centradas, en una página A4 blanca."""
    pagina = Image.new("RGB", A4, "white")
    alto_hueco = (A4[1] - MARGEN * (len(caras) + 1)) // max(len(caras), 2)
    ancho_max = A4[0] - 2 * MARGEN
    y = MARGEN
    for cara in caras:
        escala = min(ancho_max / cara.width, alto_hueco / cara.height)
        cara = cara.resize((round(cara.width * escala), round(cara.height * escala)), Image.LANCZOS)
        pagina.paste(cara, ((A4[0] - cara.width) // 2, y + (alto_hueco - cara.height) // 2))
        y += alto_hueco + MARGEN
    return pagina


def pdf_bytes(pagina):
    """Devuelve el PDF en memoria, sin título, autor, fechas ni rutas."""
    buf = io.BytesIO()
    pagina.save(
        buf, "PDF", resolution=DPI, quality=90,
        title="", author="", subject="", keywords="", creator="", producer="",
        creationDate="", modDate="",
    )
    return buf.getvalue()


def generar(anverso, reverso, texto, byn=True):
    """Procesa las caras y devuelve (página, bytes del PDF)."""
    caras = [procesar_cara(anverso, texto, byn)]
    if reverso:
        caras.append(procesar_cara(reverso, texto, byn))
    pagina = montar_pagina(caras)
    return pagina, pdf_bytes(pagina)


# ---------------------------------------------------------------- interfaz


class App:
    def __init__(self, raiz):
        import tkinter as tk

        self.tk = tk
        self.raiz = raiz
        raiz.title("Marca de agua para DNI")
        self.anverso = tk.StringVar()
        self.reverso = tk.StringVar()
        self.texto = tk.StringVar()
        self.byn = tk.BooleanVar(value=True)
        self.foto = None  # referencia para que Tk no libere la vista previa

        marco = tk.Frame(raiz, padx=10, pady=10)
        marco.pack(side="left", fill="y")
        for fila, (etiqueta, var) in enumerate([("Anverso", self.anverso), ("Reverso (opcional)", self.reverso)]):
            tk.Label(marco, text=etiqueta).grid(row=fila, column=0, sticky="w")
            tk.Entry(marco, textvariable=var, width=35).grid(row=fila, column=1)
            tk.Button(marco, text="Elegir…", command=lambda v=var: self.elegir(v)).grid(row=fila, column=2)
        tk.Label(marco, text="Marca de agua").grid(row=2, column=0, sticky="w")
        tk.Entry(marco, textvariable=self.texto, width=35).grid(row=2, column=1, columnspan=2, sticky="w")
        tk.Checkbutton(marco, text="Blanco y negro", variable=self.byn).grid(row=3, column=1, sticky="w")
        tk.Button(marco, text="Vista previa", command=self.previsualizar).grid(row=4, column=1, sticky="we", pady=4)
        tk.Button(marco, text="Generar PDF", command=self.guardar).grid(row=5, column=1, sticky="we")

        self.vista = tk.Label(raiz, text="(vista previa)", width=40, relief="sunken")
        self.vista.pack(side="right", padx=10, pady=10)

    def elegir(self, var):
        from tkinter import filedialog

        tipos = "*.jpg *.jpeg *.png" + (" *.heic *.heif" if HEIC else "")
        ruta = filedialog.askopenfilename(filetypes=[("Imágenes", tipos), ("Todos", "*.*")])
        if ruta:
            var.set(ruta)

    def crear(self):
        from tkinter import messagebox

        if not self.anverso.get():
            messagebox.showwarning("Falta el anverso", "Elige al menos la imagen del anverso.")
            return None
        try:
            return generar(self.anverso.get(), self.reverso.get() or None, self.texto.get(), self.byn.get())
        except Exception as e:  # mostrar cualquier error de lectura al usuario
            messagebox.showerror("Error", str(e))
            return None

    def mostrar(self, pagina):
        from PIL import ImageTk

        vista = pagina.copy()
        vista.thumbnail((420, 600))
        self.foto = ImageTk.PhotoImage(vista)
        self.vista.config(image=self.foto, text="", width=vista.width, height=vista.height)

    def previsualizar(self):
        resultado = self.crear()
        if resultado:
            self.mostrar(resultado[0])

    def guardar(self):
        from tkinter import filedialog, messagebox

        resultado = self.crear()
        if not resultado:
            return
        pagina, datos = resultado
        self.mostrar(pagina)
        destino = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if destino:
            Path(destino).write_bytes(datos)
            messagebox.showinfo("Hecho", f"PDF guardado en:\n{destino}")


def main():
    import tkinter as tk

    raiz = tk.Tk()
    App(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    sys.exit(main())
