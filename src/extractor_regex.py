# src/extractor_regex.py

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
            "emails": "",
            "fechas": "",
            "num_palabras": 0,
            "estado": "",
            "error": f"Error al leer archivo: {str(e)}"
        }

    # --- Correos electrónicos más flexibles ---
    correos = re.findall(r"[a-zA-Z0-9_.+%-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", content)

    # --- Fechas en formatos comunes y naturales (es/en/sv) ---
    fechas = re.findall(
        r'\b(?:\d{1,2}(?:st|nd|rd|th)?(?:\s*(?:de\s+)?(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|'
        r'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|maj))?(?:\s*[\.,]?\s*\d{2,4})?)\b',
        content, flags=re.IGNORECASE)

    # También fechas numéricas como 12/03/1945 o 1945-03-12
    fechas.extend(re.findall(r"\b(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\b", content))

    # --- Conteo de palabras ---
    palabras = re.findall(r'\b\w+\b', content)
    num_palabras = len(palabras)

    # --- Debug en consola ---
    print(f"[DEBUG] Procesado: {filepath}")
    print(f"[DEBUG] Emails: {correos}")
    print(f"[DEBUG] Fechas: {fechas}")
    print(f"[DEBUG] Palabras: {num_palabras}")

    return {
        "Emails": sorted(set(correos)) if correos else [],
        "Fechas": sorted(set(fechas)) if fechas else [],
        "ConteoPalabras": num_palabras,
        "filename": filepath.replace("\\", "/").split("/")[-1],
        "status": "success",
        "error": ""
    }

