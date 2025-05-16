# Proyecto Final Sistemas Operativos

- Roberto Sandoval 598270
- Mauricio Gonzalez 594595
- Rolando Rivas 594276
- Carlos Garcia 613250

## Sistema de Eventos y Scheduling OS (Cliente-Servidor con GUI)

Este proyecto implementa un sistema distribuido simple basado en una arquitectura cliente-servidor en la que se manejan eventos, suscripciones y otras opciones para los clientes, los cuales se encargaran de analizar archivos de texto con regex mientras organizan su carga de trabajo con algoritmos de scheduling.

El directorio `src/` consta de dos programas principales:

1.  **Servidor (`server.py`):** 
	1. Programa CLI
	2. Gestiona eventos y las suscripciones
	3. dispara triggers
	4. Configura no. de threads a usar
2.  **Cliente (`client_gui.py`):** 
	1. Aplicación GUI
	2. Se conecta al servidor mediante una IP y puerto
	3. Opcion de suscribirse/desuscribirse a eventos
	4. Opcion de escoger el algoritmo que quieras
	5. Recibe triggers del server
	6. Procesa archivos `.txt`
	7. Visualiza el estado del procesamiento, las métricas de los procesos y el resultado de la extracción de datos en un archivo CSV.

## Estructura del Proyecto

```text
.
├── README.md           # Este archivo
├── CONTRIBUTING.md     # Guía para colaboradores
├── TODO.md             # Lista de tareas pendientes y mejoras
├── requirements.txt    # Dependencias de Python
├── src/                # Directorio/Paquete con el código fuente
│   ├── __init__.py     #   (Necesario, puede estar vacío) Indica a Python que 'src' es un paquete
│   ├── server.py       #   Código fuente del servidor
│   └── client_gui.py   #   Código fuente de la aplicación cliente con GUI
│   ├── scheduler.py    #   Módulo para algoritmos de scheduling
│   └── process.py      #   Módulo para la clase Process
├── text_files/         # Directorio para los archivos .txt a procesar (crear manualmente)
└── output/             # Directorio donde los clientes guardarán los CSVs (creado por el cliente)
```

**Nota:** Los archivos `scheduler.py` y `process.py` son propuestas para mejorar la modularidad, pero actualmente su funcionalidad puede estar integrada en `client_gui.py` en el esqueleto inicial.

## Instalación

1.  Clona este repositorio:
    ```bash
    git clone https://github.com/ChocoRolis/proyecto-final-SO.git
    cd proyecto-final-SO/
    ```

## Uso

1.  **Iniciar el Servidor:**
    Abre una terminal y ejecuta:
    ```bash
    python3 -m src.server
    ```
    El servidor se iniciará y esperará conexiones. Comandos: (`add <evento>`, `trigger <evento>`, `set_threads <N>`, `list`, `exit`).

2.  **Preparar Archivos `.txt`:**
    Coloca en `text_files` los archivos de texto (`.txt`) que quieres que los clientes procesen. Asegúrate de que contengan los patrones que definirás para la extracción con Regex.

3.  **Iniciar el Cliente(s):**
    Abre una o varias terminales (una por cada cliente que quieras simular) y ejecuta:
    ```bash
    python3 -m src.client_gui
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

## Tareas Pendientes 

Consulta el archivo to-do [`TODO.md`](TODO.md) para ver la lista de funcionalidades que faltan implementar.

## Contribuciones

Revisa el archivo [`CONTRIBUTING.md`](CONTRIBUTING.md) para ver como contribuir codigo a este repo.
