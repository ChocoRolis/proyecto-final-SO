# Sistema de Eventos y Scheduling OS (Cliente-Servidor con GUI)

Este proyecto implementa un sistema distribuido simple basado en una arquitectura cliente-servidor para demostrar conceptos fundamentales de sistemas operativos. Permite la gestión de eventos, la configuración de concurrencia (hilos/procesos reales), el procesamiento de archivos y la simulación visual de algoritmos de planificación.

## Características Principales

*   **Arquitectura Cliente-Servidor:**
    *   **Servidor:** Centraliza la gestión de eventos, la administración de clientes y el **procesamiento real** de archivos `.txt` utilizando concurrencia (hilos o procesos "forks" reales) según la configuración del cliente.
    *   **Cliente:** Proporciona una Interfaz Gráfica de Usuario (GUI) para la configuración, suscripción a eventos y la **simulación visual** de algoritmos de scheduling con los archivos asignados por el servidor.
*   **Concurrencia Real y Simulada:**
    *   El **servidor** utiliza `ThreadPoolExecutor` o `ProcessPoolExecutor` para procesar archivos en paralelo.
    *   El **cliente** simula y visualiza cómo se distribuiría el trabajo entre "CPUs/hilos simulados" bajo diferentes algoritmos de scheduling.
*   **Gestión de Eventos y Colas:** El servidor administra eventos y mantiene una cola FIFO de clientes suscritos por evento para un procesamiento ordenado.
*   **Procesamiento de Archivos (Regex):** El servidor extrae información estructurada (nombres, fechas, lugares, conteo de palabras) de archivos `.txt` usando expresiones regulares.
*   **Algoritmos de Scheduling:** El cliente implementa y visualiza algoritmos como FCFS, SJF, SRTF, Round Robin, HRRN y Prioridad No Preemptiva.
*   **Visualización Detallada:** La GUI del cliente muestra tablas de procesos, un diagrama de Gantt animado, y métricas de rendimiento (tiempos de turnaround y espera, con sus fórmulas).
*   **Registro de Actividad:** El servidor genera un archivo de log (`server_processing.log`) con detalles del procesamiento de archivos.

## Estructura del Proyecto

```
.
├── docs/               # Documentación detallada del proyecto
│   ├── client.md       #   Documentación del cliente (client_gui.py)
│   ├── extractor.md    #   Documentación del extractor Regex (extractor_regex.py)
│   ├── process.md      #   Documentación de la clase Process (process.py)
│   ├── scheduler.md    #   Documentación de los algoritmos de scheduling (scheduler.py)
│   └── server.md       #   Documentación del servidor (server.py)
├── README.md           # Este archivo (visión general y ejecución)
├── requirements.txt    # Dependencias de Python
├── src/                # Código fuente de la aplicación
│   ├── client_gui.py   #   Aplicación cliente con GUI
│   ├── extractor_regex.py # Módulo para extracción de datos con Regex
│   ├── __init__.py     #   (Necesario para que 'src' sea un paquete Python)
│   ├── process.py      #   Definición de la clase Process/Task
│   ├── scheduler.py    #   Implementaciones de algoritmos de scheduling
│   └── server.py       #   Aplicación servidor
└── text_files/         # Directorio para los archivos .txt a procesar
    └── ... (ejemplos de archivos .txt)
```

## Requisitos

Necesitas tener **Python 3.7 o superior** instalado en tu sistema. Este proyecto utiliza únicamente librerías estándar de Python, por lo que no se requieren instalaciones adicionales con `pip`.

## Instalación

1.  **Clona este repositorio:**
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd <NOMBRE_DEL_REPOSITORIO>
    ```
2.  **Verifica el paquete `src`:** Asegúrate de que exista un archivo vacío llamado `__init__.py` dentro del directorio `src/`. Esto es crucial para que Python reconozca `src` como un paquete y permita las importaciones internas y la ejecución como módulo.
    ```bash
    touch src/__init__.py
    ```

## Uso

**Importante:** Todos los comandos deben ejecutarse desde el **directorio raíz del proyecto** (el que contiene el directorio `src/`).

1.  **Preparar Archivos de Texto:**
    Crea un directorio llamado `text_files` en la raíz del proyecto si no existe. Coloca dentro los archivos de texto (`.txt`) que deseas que el servidor procese. Asegúrate de que contengan patrones como nombres, fechas y lugares para que el extractor Regex pueda encontrarlos.

2.  **Iniciar el Servidor:**
    Abre una terminal y ejecuta:
    ```bash
    python -m src.server
    ```
    El servidor se iniciará y esperará conexiones. En su consola, verás mensajes de log y podrás usar comandos de administrador (escribe `help` para verlos). Los logs detallados del procesamiento se guardarán en `server_processing.log`.

3.  **Iniciar el Cliente(s):**
    Abre una o varias terminales (una por cada cliente que quieras simular) y ejecuta:
    ```bash
    python -m src.client_gui
    ```
    Se abrirá la interfaz gráfica del cliente.

4.  **Interactuar con el Cliente (GUI):**
    *   **Conectar:** En la sección "Conexión al Servidor", haz clic en "Conectar" (la IP y el Puerto por defecto suelen ser correctos).
    *   **Configurar Cliente:** En "Configuración del Cliente", selecciona el modo (`Threads` o `Forks`) y la `Cantidad` de workers que este cliente usará en el servidor. Haz clic en "Aplicar Config.".
    *   **Suscribir:** En "Suscripción a Eventos", ingresa un nombre de evento (ej., `data_event`) y haz clic en "Suscribir".
    *   **Disparar Evento (desde el Servidor):** En la terminal del servidor, escribe `trigger data_event` y presiona Enter.
    *   **Seleccionar Archivos para Simulación:** El cliente recibirá la lista de archivos asignados por el servidor. En la sección "Archivos Asignados", selecciona los archivos que deseas usar para la simulación visual (por defecto están deseleccionados). Haz clic en "Definir Parámetros".
    *   **Ingresar Parámetros de Simulación:** En "Parámetros de Simulación", ingresa manualmente el "Llegada" (Arrival Time), "Ráfaga" (Burst Time) y "Prioridad" (si el algoritmo lo requiere) para cada archivo seleccionado.
    *   **Iniciar Simulación Visual:** En "Configuración de Simulación", selecciona un "Algoritmo" de scheduling (ej., FCFS, RR, SJF). Haz clic en "Iniciar Simulación".
    *   **Observar:**
        *   La pestaña "Tabla de Procesos" mostrará el estado y las métricas de los procesos simulados.
        *   La pestaña "Diagrama de Gantt" visualizará la ejecución simulada en el tiempo.
        *   La pestaña "Resultados" mostrará los datos extraídos por el servidor y te permitirá "Guardar Resultados a CSV".

5.  **Detener el Servidor:**
    En la terminal del servidor, escribe `exit` y presiona Enter. Esto notificará a todos los clientes que el servidor se está cerrando.

## Documentación Detallada y Contribuciones

Para una comprensión profunda del funcionamiento interno del proyecto, la arquitectura, los algoritmos y cómo extenderlo, consulta la carpeta `docs/`:

*   [**Documentación del Servidor**](docs/server.md)
*   [**Documentación del Cliente**](docs/client.md)
*   [**Documentación de la Clase Process**](docs/process.md)
*   [**Documentación de los Algoritmos de Scheduling**](docs/docs/scheduler.md)
*   [**Documentación del Extractor Regex**](docs/extractor.md)
