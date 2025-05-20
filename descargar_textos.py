# descargar_textos.py

import os
import requests
from bs4 import BeautifulSoup

URL_BASE = "https://ubiquitous.udem.edu/~raulms/Suecia/Museum/english_text_files/"
CARPETA_DESTINO = os.path.join(os.path.dirname(__file__), "text_files")

def descargar_txts():
    os.makedirs(CARPETA_DESTINO, exist_ok=True)

    try:
        r = requests.get(URL_BASE)
        soup = BeautifulSoup(r.text, 'html.parser')
        enlaces = [a['href'] for a in soup.find_all('a') if a.get('href', '').endswith('.txt')]
    except Exception as e:
        print(f"[ERROR] No se pudieron obtener los archivos: {e}")
        return

    for enlace in enlaces:
        nombre = enlace.split('/')[-1]
        ruta = os.path.join(CARPETA_DESTINO, nombre)
        print(f"Descargando {nombre}...")

        try:
            with requests.get(URL_BASE + enlace, stream=True) as f:
                with open(ruta, 'wb') as out:
                    for chunk in f.iter_content(chunk_size=8192):
                        out.write(chunk)
        except Exception as e:
            print(f"[ERROR] No se pudo descargar {nombre}: {e}")

    print(f"\n✅ {len(enlaces)} archivos descargados en: {os.path.abspath(CARPETA_DESTINO)}")

if __name__ == "__main__":
    descargar_txts()
