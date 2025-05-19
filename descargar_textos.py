import os
import requests
from bs4 import BeautifulSoup

URL_BASE = "https://ubiquitous.udem.edu/~raulms/Suecia/Museum/english_text_files/"
CARPETA_DESTINO = os.path.join("src", "text_files")

def descargar_txts():
    os.makedirs(CARPETA_DESTINO, exist_ok=True)
    print("🔍 Buscando archivos en la web...")
    r = requests.get(URL_BASE)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, 'html.parser')
    enlaces = [a.get('href') for a in soup.find_all('a') if '.txt' in a.get('href', '')]

    if not enlaces:
        print("⚠️ No se encontraron archivos .txt en la página.")
        return

    print(f"📄 Se encontraron {len(enlaces)} archivos. Descargando...\n")

    for enlace in enlaces:
        nombre = enlace.split('/')[-1]
        ruta = os.path.join(CARPETA_DESTINO, nombre)
        url_completa = URL_BASE + enlace
        print(f"⬇️ {nombre}")

        try:
            with requests.get(url_completa, stream=True) as f:
                f.raise_for_status()
                with open(ruta, 'wb') as out:
                    for chunk in f.iter_content(chunk_size=8192):
                        out.write(chunk)
        except Exception as e:
            print(f"❌ Error con {nombre}: {e}")

    print(f"\n✅ Descarga completa. Archivos guardados en ./{CARPETA_DESTINO}/")

if __name__ == "__main__":
    descargar_txts()
