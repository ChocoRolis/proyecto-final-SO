# Sistema de Eventos y Scheduling OS (Cliente-Servidor con GUI)

Este proyecto implementa un sistema distribuido simple basado en una arquitectura cliente-servidor para demostrar conceptos de sistemas operativos como la comunicación interprocesos, la gestión de eventos, la concurrencia simulada (con threads/forks) y algoritmos de scheduling (planificación de procesos).

El proyecto consta de dos componentes principales:

1.  **Servidor (`server.py`):** Encargado de gestionar eventos y las suscripciones de los clientes a estos eventos. También es el punto de control para disparar eventos (triggers) y configurar parámetros como el número de "threads/forks" simulados que los clientes deben usar.
2.  **Cliente (`client_gui.py`):** Una aplicación con interfaz gráfica que se conecta al servidor. Permite a los usuarios suscribirse/desuscribirse a eventos. Cuando un evento suscrito es disparado por el servidor, el cliente simula la ejecución de tareas (procesamiento de archivos `.txt`) utilizando diferentes algoritmos de scheduling configurables. La GUI visualiza el estado de la simulación, las métricas de los procesos y el resultado de la extracción de datos en un archivo CSV.

## Características

*   **Comunicación Cliente-Servidor:** Utiliza sockets TCP para la comunicación en tiempo real.
*   **Gestión de Eventos:** El servidor permite crear, eliminar y disparar eventos.
*   **Suscripción de Clientes:** Los clientes pueden suscribirse a eventos específicos para recibir notificaciones.
*   **Concurrencia Simulada:** El cliente simula la ejecución concurrente de tareas utilizando un número configurable de "threads/forks" (definido por el servidor).
*   **Algoritmos de Scheduling:** Implementación de (actualmente FCFS, con planes para añadir SJF, RR, etc.) para planificar la ejecución simulada de tareas.
*   **Procesamiento de Archivos:** Los clientes procesan archivos `.txt` utilizando expresiones regulares (Regex) al completar una tarea simulada.
*   **Extracción y Almacenamiento de Datos:** Los datos extraídos se guardan en un archivo CSV por cada cliente.
*   **Interfaz Gráfica (GUI):** Desarrollada con Tkinter, proporciona visualización del estado de la simulación, métricas de scheduling (PID, tiempos, promedios) y vista previa del CSV resultante.

## Estructura del Proyecto

├── README.md # Este archivo
├── CONTRIBUTING.md # Guía para colaboradores
├── TODO.md # Lista de tareas pendientes y mejoras
├── requirements.txt # Dependencias de Python
├── server.py # Código fuente del servidor
├── client_gui.py # Código fuente de la aplicación cliente con GUI
├── scheduler.py # (Propuesto) Módulo para algoritmos de scheduling
├── process.py # (Propuesto) Módulo para la clase Process/Task
├── text_files/ # Directorio para los archivos .txt a procesar (crear manualmente)
└── output/ # Directorio donde los clientes guardarán los CSVs (creado por el cliente)


**Nota:** Los archivos `scheduler.py` y `process.py` son propuestos para mejorar la modularidad, pero actualmente su funcionalidad puede estar integrada en `client_gui.py` en el esqueleto inicial.

## Requisitos

Necesitas tener Python instalado en tu sistema. Las librerías adicionales necesarias se listan en `requirements.txt`.

## Instalación

1.  Clona este repositorio:
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd <NOMBRE_DEL_REPOSITORIO>
    ```
2.  Instala las dependencias de Python usando pip:
    ```bash
    pip install -r requirements.txt
    ```

## Uso

1.  **Iniciar el Servidor:**
    Abre una terminal y ejecuta:
    ```bash
    python server.py
    ```
    El servidor se iniciará y esperará conexiones. Puedes interactuar con él mediante comandos en su terminal (`add <evento>`, `trigger <evento>`, `set_threads <N>`, `list`, `exit`).

2.  **Preparar Archivos `.txt`:**
    Crea un directorio llamado `text_files` en la raíz del proyecto. Coloca dentro los archivos de texto (`.txt`) que quieres que los clientes procesen. Asegúrate de que contengan los patrones que definirás para la extracción con Regex.

3.  **Iniciar el Cliente(s):**
    Abre una o varias terminales (una por cada cliente que quieras simular) y ejecuta:
    ```bash
    python client_gui.py
    ```
    Se abrirá la interfaz gráfica del cliente.

4.  **Interactuar con el Cliente (GUI):**
    *   Ingresa la IP y Puerto del servidor (por defecto `127.0.0.1:65432`) y haz clic en "Conectar".
    *   Una vez conectado, ingresa el nombre de un evento (ej. `data_ready`) y haz clic en "Suscribir".
    *   Selecciona un algoritmo de scheduling en el ComboBox.
    *   (Opcional) Espera a que el servidor dispare un evento o pídele a alguien que controle el servidor que dispare un evento al que estés suscrito.
    *   Cuando se reciban tareas (tras un trigger), haz clic en "Iniciar Simulación" para comenzar a procesarlas según el algoritmo seleccionado y el número de threads configurado por el servidor.
    *   Observa las pestañas "Tabla de Procesos", "Gantt" y "Vista Previa CSV" para ver el progreso.

5.  **Detener el Servidor:**
    En la terminal del servidor, escribe `exit` y presiona Enter. Esto notificará a los clientes que el servidor se está cerrando.

## Tareas Pendientes y Mejoras

Consulta el archivo [`TODO.md`](TODO.md) para ver la lista de funcionalidades a implementar y mejoras planeadas.

## Contribuciones

Si quieres contribuir a este proyecto (idealmente si eres un compañero de clase trabajando en la misma tarea), por favor, consulta el archivo [`CONTRIBUTING.md`](CONTRIBUTING.md) para conocer las pautas.

## Licencia

[Define tu licencia aquí, si aplica. Ej: MIT, sin licencia (Propiedad para la tarea), etc.]
