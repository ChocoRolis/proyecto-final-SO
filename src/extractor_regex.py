import re
from typing import Dict


def parse_file_regex(filepath: str, pid: str) -> Dict:
    """
    Extrae información específica de un archivo de texto utilizando expresiones regulares.

    Args:
        filepath (str): La ruta completa del archivo de texto a procesar.
        pid (str): Un identificador del proceso/hilo que realiza la extracción
                   (ej. "FORK PID_12345").

    Returns:
        Dict: Un diccionario con los datos extraídos (nombres, fechas, lugares,
              conteo de palabras) y el estado del procesamiento.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return {
            "pid": pid,
            "archivo": filepath.split("/")[-1],
            "nombres": [],
            "fechas": [],
            "lugares": [],
            "num_palabras": 0,
            "status": "error_lectura",
            "error": f"Error al leer archivo: {str(e)}",
        }

    # --- Nombres (ej: John Smith, Anna Karlsson) ---
    # Busca palabras que empiezan con mayúscula, seguidas de minúsculas,
    # y que pueden tener más palabras así (para apellidos).
    nombres = re.findall(
        r"\b[A-ZÁÉÍÓÚÑÅÄÖ][a-záéíóúñåäö]+(?:\s+[A-ZÁÉÍÓÚÑÅÄÖ][a-záéíóúñåäö]+)+\b",
        content,
    )

    # --- Fechas en formatos comunes y naturales (es/en/sv) ---
    # Busca fechas textuales como "12 de enero de 1945" o "Jan 12, 1945"
    fechas_textuales = re.findall(
        r"\b(?:\d{1,2}(?:st|nd|rd|th)?(?:\s*(?:de\s+)?(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|"
        r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|maj))?(?:\s*[\.,]?\s*\d{2,4})?)\b",
        content,
        flags=re.IGNORECASE,
    )

    # Busca fechas numéricas como 12/03/1945 o 1945-03-12
    fechas_numericas = re.findall(
        r"\b(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\b",
        content,
    )
    fechas = fechas_textuales + fechas_numericas


    # --- Lugares/Ciudades ---
    # Lista de ciudades comunes para buscar.
    ciudades_comunes = [
        "New York", "Chicago", "Los Angeles", "San Francisco", "Boston",
        "Minneapolis", "Detroit", "Miami", "Stockholm", "Göteborg",
        "Malmö", "Uppsala", "Lund", "Karlstad", "Örebro",
        "Västerås", "Linköping", "Madrid", "Barcelona", "Sevilla",
        "Valencia", "Bilbao", "Zaragoza", "Málaga", "Murcia",
        "Granada", "Córdoba", "Alicante", "Valladolid", "Gijón",
        "Vigo", "A Coruña", "Oviedo", "Pamplona", "Salamanca"
    ]
    # Crea una regex para buscar cualquiera de estas ciudades.
    ciudades_regex = (
        r"\b(?:" + "|".join(re.escape(city) for city in ciudades_comunes) + r")\b"
    )
    lugares = re.findall(ciudades_regex, content)

    # --- Conteo de palabras ---
    # Busca secuencias de caracteres alfanuméricos como palabras.
    palabras = re.findall(r"\b\w+\b", content)
    num_palabras = len(palabras)

    return {
        "Nombres": sorted(list(set(nombres))) if nombres else [],
        "Fechas": sorted(list(set(fechas))) if fechas else [],
        "Lugares": sorted(list(set(lugares))) if lugares else [],
        "ConteoPalabras": num_palabras,
        "filename": os.path.basename(filepath), # Usar os.path.basename para consistencia
        "status": "success",
        "error": "",
    }
