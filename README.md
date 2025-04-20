# Proyecto Final Sistemas Operativos

- Roberto Sandoval 598270
- Mauricio Gonzalez 594595
- Rolando Rivas 594276
- Carlos Garcia 613250

## Sistema de Eventos y Scheduling OS (Cliente-Servidor con GUI)

Este proyecto implementa un sistema distribuido simple basado en una arquitectura cliente-servidor en la que se manejan eventos, suscripciones y otras opciones para los clientes, los cuales se encargaran de analizar archivos de texto con regex mientras organizan su carga de trabajo con algoritmos de scheduling.

El directorio `src/` consta de dos programas principales:

1.  **Servidor (`server.py`):** 
	2. Programa CLI
	3. Gestiona eventos y las suscripciones
	4. dispara triggers
	5. Configura no. de threads a usar
5.  **Cliente (`client_gui.py`):** 
	6. Aplicación GUI
	7. Se conecta al servidor mediante una IP y puerto
	8. Opcion de suscribirse/desuscribirse a eventos
	9. Opcion de escoger el algoritmo que quieras
	10. Recibe triggers del server
	11. Procesa archivos `.txt`
	12. Visualiza el estado del procesamiento, las métricas de los procesos y el resultado de la extracción de datos en un archivo CSV.

## Estructura del Proyecto

├── README.md 		# Este archivo
├── CONTRIBUTING.md 	# Guía para colaboradores
├── TODO.md 		# Lista de tareas pendientes y mejoras
├── requirements.txt 	# Dependencias de Python
├── server.py 		# Código fuente del servidor
├── client_gui.py 	# Código fuente de la aplicación cliente con GUI
├── scheduler.py 	# (Propuesto) Módulo para algoritmos de scheduling
├── process.py 		# (Propuesto) Módulo para la clase Process/Task
└── text_files/ 	# Directorio para los archivos .txt a procesar (crear manualmente)


**Nota:** Los archivos `scheduler.py` y `process.py` son propuestas para mejorar la modularidad, pero actualmente su funcionalidad puede estar integrada en `client_gui.py` en el esqueleto inicial.

## Instalación

1.  Clona este repositorio:
    ```bash
    git clone https://github.com/ChocoRolis/proyecto-final-SO.git
    cd proyecto-final-SO/
    ```
2.  Instala las dependencias de Python usando pip:
    ```bash
    pip install -r requirements.txt
    ```

## Uso

1.  **Iniciar el Servidor:**
    Abre una terminal y ejecuta:
    ```bash
    python3 server.py
    ```
    El servidor se iniciará y esperará conexiones. Comandos: (`add <evento>`, `trigger <evento>`, `set_threads <N>`, `list`, `exit`).

2.  **Preparar Archivos `.txt`:**
    Coloca en `text_files` los archivos de texto (`.txt`) que quieres que los clientes procesen. Asegúrate de que contengan los patrones que definirás para la extracción con Regex.

3.  **Iniciar el Cliente(s):**
    Abre una o varias terminales (una por cada cliente que quieras simular) y ejecuta:
    ```bash
    python3 client_gui.py
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
