# Documentación Detallada del Extractor Regex (`src/extractor_regex.py`)

El archivo `extractor_regex.py` es un módulo auxiliar utilizado por el servidor (`server.py`) para realizar el procesamiento real de los archivos de texto. Su función principal es buscar y extraer patrones específicos de información (como nombres, fechas y lugares) utilizando expresiones regulares.

## Propósito General

Este módulo centraliza toda la lógica de análisis de contenido de archivos de texto. Cuando el servidor necesita procesar un archivo para un cliente, invoca la función principal de este módulo para obtener los datos estructurados.

## Función Principal: `parse_file_regex`

### `parse_file_regex(filepath: str, pid: str) -> Dict`

```python
def parse_file_regex(filepath: str, pid: str) -> Dict:
    """
    Extrae información específica de un archivo de texto utilizando expresiones regulares.

    Args:
        filepath (str): La ruta completa del archivo de texto a procesar.
        pid (str): Un identificador del proceso/hilo que realiza la extracción
                   (ej. "FORK PID_12345" o "THREAD ID_123456789").

    Returns:
        Dict: Un diccionario con los datos extraídos (nombres, fechas, lugares,
              conteo de palabras) y el estado del procesamiento.
    """
    # ...
```

*   **Propósito:** Esta es la función principal del módulo. Se encarga de abrir un archivo, leer su contenido y aplicar varias expresiones regulares para encontrar información relevante.
*   **Argumentos:**
    *   `filepath` (str): La ruta completa al archivo de texto (`.txt`) que debe ser analizado.
    *   `pid` (str): Un identificador del worker (proceso o hilo) que está llamando a esta función. Se utiliza principalmente para propósitos de logging y para incluirlo en los resultados.
*   **Retorna:** Un diccionario (`Dict`) que contiene los resultados del análisis. La estructura de este diccionario es crucial, ya que es lo que el servidor envía de vuelta al cliente.
    *   **En caso de éxito:**
        *   `"Nombres"` (list): Lista de nombres propios encontrados.
        *   `"Fechas"` (list): Lista de fechas encontradas en varios formatos.
        *   `"Lugares"` (list): Lista de nombres de ciudades/lugares encontrados.
        *   `"ConteoPalabras"` (int): Número total de palabras en el archivo.
        *   `"filename"` (str): El nombre base del archivo procesado.
        *   `"status"` (str): Siempre "success" si la lectura y la extracción se completan sin errores.
        *   `"error"` (str): Cadena vacía.
    *   **En caso de error (ej., archivo no encontrado, error de lectura):**
        *   Contendrá claves como `"pid"`, `"archivo"`, `"status": "error_lectura"`, y `"error"` con un mensaje descriptivo. Los campos de datos (`"nombres"`, etc.) estarán vacíos.

### Funcionamiento Interno de `parse_file_regex`

1.  **Lectura del Archivo:**
    *   Intenta abrir el archivo especificado por `filepath` en modo lectura (`'r'`) con codificación `utf-8` y `errors='ignore'` para manejar caracteres que no puedan ser decodificados.
    *   Si la lectura falla (ej., `FileNotFoundError`), captura la excepción y retorna un diccionario de error.

2.  **Extracción de Nombres:**
    *   `re.findall(r"\b[A-ZÁÉÍÓÚÑÅÄÖ][a-záéíóúñåäö]+(?:\s+[A-ZÁÉÍÓÚÑÅÄÖ][a-záéíóúñåäö]+)+\b", content)`:
        *   Busca secuencias de palabras que comienzan con una letra mayúscula (incluyendo tildes y Ñ/ÅÄÖ para idiomas específicos).
        *   `\b`: Límite de palabra.
        *   `[A-ZÁÉÍÓÚÑÅÄÖ][a-záéíóúñåäö]+`: Una letra mayúscula seguida de una o más letras minúsculas.
        *   `(?:\s+[A-ZÁÉÍÓÚÑÅÄÖ][a-záéíóúñåäö]+)+`: Un grupo no capturante `(?:...)` que busca uno o más espacios seguidos de otra palabra que empieza con mayúscula. El `+` al final del grupo asegura que se capturen nombres compuestos (ej., "John Smith").
        *   **Propósito:** Identificar posibles nombres propios, que a menudo consisten en varias palabras capitalizadas.

3.  **Extracción de Fechas:**
    *   Combina dos expresiones regulares:
        *   `re.findall(r"\b(?:\d{1,2}(?:st|nd|rd|th)?(?:\s*(?:de\s+)?(?:enero|febrero|marzo|...))?(?:\s*[\.,]?\s*\d{2,4})?)\b", content, flags=re.IGNORECASE)`: Busca fechas en formato textual (ej., "12 de enero de 1945", "Jan 12, 1945"). Incluye sufijos ordinales (st, nd, rd, th) y nombres de meses en varios idiomas.
        *   `re.findall(r"\b(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\b", content)`: Busca fechas en formato numérico común (ej., "12/03/1945", "1945-03-12").
    *   Los resultados de ambas búsquedas se combinan en una sola lista `fechas`.

4.  **Extracción de Lugares/Ciudades:**
    *   `ciudades_comunes`: Una lista predefinida de nombres de ciudades.
    *   `ciudades_regex = r"\b(?:" + "|".join(re.escape(city) for city in ciudades_comunes) + r")\b"`: Construye dinámicamente una expresión regular que buscará cualquiera de las ciudades en la lista. `re.escape()` se usa para asegurar que caracteres especiales en los nombres de ciudades (si los hubiera) sean tratados literalmente.
    *   `re.findall(ciudades_regex, content)`: Busca todas las ocurrencias de estas ciudades.

5.  **Conteo de Palabras:**
    *   `re.findall(r"\b\w+\b", content)`: Encuentra todas las secuencias de caracteres alfanuméricos (letras, números, guiones bajos) que están delimitadas por límites de palabra.
    *   `num_palabras = len(palabras)`: El conteo de palabras es simplemente la longitud de la lista resultante.

6.  **Formato de Salida:**
    *   Los resultados de las extracciones (`nombres`, `fechas`, `lugares`) se convierten a un `set` para eliminar duplicados, luego a una lista ordenada para consistencia, y finalmente se almacenan en el diccionario de retorno.
    *   El `filename` se obtiene usando `os.path.basename(filepath)` para asegurar que solo se devuelva el nombre del archivo sin la ruta completa.
    *   Los campos `status` y `error` indican el éxito o fracaso de la extracción.

## Cómo Contribuir a este Módulo

*   **Añadir Nuevos Patrones de Extracción:**
    1.  Identifica el tipo de información que deseas extraer (ej., números de teléfono, direcciones, códigos postales, URLs).
    2.  Crea una expresión regular (`regex`) que capture ese patrón. Puedes usar herramientas como [Regex101](https://regex101.com/) para probar tus regex.
    3.  Añade una nueva línea `re.findall()` (o `re.search()`) en la función `parse_file_regex` para aplicar tu regex al `content` del archivo.
    4.  Almacena el resultado en una nueva variable.
    5.  Añade esta nueva variable al diccionario de retorno. Por ejemplo, si extraes números de teléfono, añadirías `"Telefonos": sorted(list(set(telefonos))) if telefonos else []`.
*   **Mejorar Patrones Existentes:** Si encuentras que los patrones actuales para nombres, fechas o lugares no son lo suficientemente precisos, puedes modificarlos directamente.
*   **Manejo de Errores:** Si hay casos de error específicos en la extracción (ej., un formato de archivo inesperado), puedes añadir más bloques `try-except` para manejarlos y devolver mensajes de error más detallados.
*   **Optimización:** Para archivos muy grandes, considera leerlos en bloques o usar técnicas de procesamiento más eficientes si el rendimiento se convierte en un problema.
