import re
from typing import Dict

def parse_file_regex(filepath: str, pid: str) -> Dict:
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return {
            "pid": pid,
            "archivo": filepath.split('/')[-1],
            "nombres": "",
            "fechas": "",
            "lugares": "",
            "num_palabras": 0,
            "estado": "",
            "error": f"Error al leer archivo: {str(e)}"
        }

    # --- Nombres (ej: John Smith, Anna Karlsson) ---
    nombres = re.findall(r'\b[A-ZÁÉÍÓÚÑÅÄÖ][a-záéíóúñåäö]+(?:\s+[A-ZÁÉÍÓÚÑÅÄÖ][a-záéíóúñåäö]+)+\b', content)

    # --- Fechas (igual que antes) ---
    fechas = re.findall(
        r'\b(?:\d{1,2}(?:st|nd|rd|th)?(?:\s*(?:de\s+)?(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|'
        r'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|maj))?(?:\s*[\.,]?\s*\d{2,4})?)\b',
        content, flags=re.IGNORECASE)

    fechas.extend(re.findall(r"\b(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\b", content))

    # --- Lugares/Ciudades ---
    ciudades_comunes = [
        "New York", "Chicago", "Los Angeles", "San Francisco", "Boston",
        "Minneapolis", "Detroit", "Miami", "Stockholm", "Göteborg", "Malmö",
        "Uppsala", "Lund", "Karlstad", "Örebro", "Västerås", "Linköping"
    ]
    ciudades_regex = r'\b(?:' + '|'.join(re.escape(city) for city in ciudades_comunes) + r')\b'
    lugares = re.findall(ciudades_regex, content)

    # --- Conteo de palabras ---
    palabras = re.findall(r'\b\w+\b', content)
    num_palabras = len(palabras)

    # --- Debug ---
    # print(f"[DEBUG] Procesado: {filepath}")
    # print(f"[DEBUG] Nombres: {nombres}")
    # print(f"[DEBUG] Fechas: {fechas}")
    # print(f"[DEBUG] Lugares: {lugares}")
    # print(f"[DEBUG] Palabras: {num_palabras}")

    return {
        "Nombres": sorted(set(nombres)) if nombres else [],
        "Fechas": sorted(set(fechas)) if fechas else [],
        "Lugares": sorted(set(lugares)) if lugares else [],
        "ConteoPalabras": num_palabras,
        "filename": filepath.replace("\\", "/").split("/")[-1],
        "status": "success",
        "error": ""
    }
