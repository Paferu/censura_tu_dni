"""Pruebas con imágenes sintéticas creadas en memoria (nada se escribe en disco).

Ejecutar con:  python -m unittest -v
"""

import io
import unittest

from PIL import Image, ImageChops, ImageDraw, ImageStat
from PIL.PdfParser import PdfParser

import dni_marca


def imagen_falsa(color, texto, exif=None, tamano=(856, 540)):
    """Rectángulo de color con texto, devuelto como fichero JPEG en memoria."""
    img = Image.new("RGB", tamano, color)
    ImageDraw.Draw(img).text((40, 40), texto, fill="black", font=dni_marca.cargar_fuente(40))
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif or Image.Exif())
    buf.seek(0)
    return buf


def exif_con_gps_y_giro():
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: girar 90° a la derecha
    exif[0x010F] = "MarcaMovil"  # Make
    exif[0x8825] = {1: "N", 2: (40.0, 25.0, 0.0)}  # GPSInfo
    return exif


def es_gris(img):
    r, g, b = img.split()
    return ImageChops.difference(r, g).getbbox() is None and ImageChops.difference(g, b).getbbox() is None


class Pruebas(unittest.TestCase):
    def test_marca_cubre_toda_la_imagen(self):
        blanca = Image.new("RGB", (856, 540), "white")
        marcada = dni_marca.poner_marca(blanca, "SOLO PARA PRUEBA")
        celdas = 6
        for i in range(celdas):
            for j in range(celdas):
                caja = (i * 856 // celdas, j * 540 // celdas, (i + 1) * 856 // celdas, (j + 1) * 540 // celdas)
                trozo = marcada.crop(caja).convert("L")
                self.assertLess(trozo.getextrema()[0], 250, f"celda sin marca: {caja}")

    def test_documento_sigue_legible(self):
        negra = Image.new("RGB", (400, 300), "black")
        marcada = dni_marca.poner_marca(negra, "X").convert("L")
        # Semitransparente: el fondo negro sigue dominando
        self.assertLess(ImageStat.Stat(marcada).mean[0], 80)

    def test_blanco_y_negro(self):
        cara = dni_marca.procesar_cara(imagen_falsa((200, 30, 30), "ROJO"), "Prueba", byn=True)
        self.assertTrue(es_gris(cara))
        color = dni_marca.procesar_cara(imagen_falsa((200, 30, 30), "ROJO"), "Prueba", byn=False)
        self.assertFalse(es_gris(color))

    def test_sin_exif_y_orientacion_corregida(self):
        cara = dni_marca.abrir_limpia(imagen_falsa("lightblue", "GIRADA", exif_con_gps_y_giro()))
        self.assertEqual(cara.size, (540, 856))  # rotada según EXIF
        self.assertEqual(len(cara.getexif()), 0)
        self.assertEqual(cara.info, {})

    def test_pdf_dos_caras_sin_metadatos(self):
        pagina, datos = dni_marca.generar(
            imagen_falsa("lightblue", "ANVERSO", exif_con_gps_y_giro()),
            imagen_falsa("lightgreen", "REVERSO"),
            "Envío a Ñandú S.A. — válido solo para trámite",
        )
        self.assertTrue(datos.startswith(b"%PDF"))
        pdf = PdfParser(buf=datos)
        self.assertEqual(len(pdf.pages), 1)
        for clave in (b"Title", b"Author", b"Creator", b"Producer", b"CreationDate", b"ModDate"):
            self.assertNotIn(b"/" + clave, datos)
        for rastro in (b"Exif", b"MarcaMovil", b"GPS"):
            self.assertNotIn(rastro, datos)
        # Mitad superior e inferior de la página tienen contenido (las dos caras)
        alto = pagina.height
        for caja in ((0, 0, pagina.width, alto // 2), (0, alto // 2, pagina.width, alto)):
            self.assertLess(pagina.crop(caja).convert("L").getextrema()[0], 200)

    def test_solo_anverso(self):
        pagina, datos = dni_marca.generar(imagen_falsa("white", "ANVERSO"), None, "texto")
        self.assertEqual(pagina.size, dni_marca.A4)
        self.assertEqual(len(PdfParser(buf=datos).pages), 1)

    def test_texto_vacio_no_marca(self):
        img = Image.new("RGB", (100, 100), "white")
        self.assertEqual(dni_marca.poner_marca(img, "   ").getextrema(), ((255, 255),) * 3)


if __name__ == "__main__":
    unittest.main()
