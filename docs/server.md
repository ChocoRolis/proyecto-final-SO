# Documentación Detallada del Servidor (`src/server.py`)

El script `server.py` es el corazón de nuestro sistema de simulación de sistemas operativos. Su función principal es actuar como un **coordinador central y procesador de tareas**.

## Propósito General

El servidor tiene varias responsabilidades clave:

1.  **Gestión de Conexiones:** Aceptar y mantener conexiones con múltiples clientes (`client_gui.py`).
2.  **Administración de Eventos:** Crear, eliminar y gestionar eventos, así como las suscripciones de los clientes a estos.
3.  **Gestión de Clientes:** Asignar IDs únicos a los clientes, almacenar sus configuraciones (número de workers y modo: hilos/procesos) y mantener colas de clientes por evento.
4.  **Procesamiento de Archivos:** Realizar el trabajo pesado de leer archivos de texto y extraer información utilizando expresiones regulares (Regex). Este procesamiento se hace en paralelo usando hilos o procesos reales, según la configuración de cada cliente.
5.  **Notificación a Clientes:** Informar a los clientes sobre el inicio y la finalización del procesamiento de sus archivos, y enviarles los resultados.
6.  **Administración por Consola:** Permitir al administrador controlar el servidor mediante comandos de texto.

## Flujo General de Ejecución del Servidor

Cuando ejecutas `python -m src.server`, el programa sigue este flujo:

1.  **Configuración Inicial y Preparación:**
    *   Se importan todas las librerías necesarias (red, concurrencia, JSON, sistema de archivos, logging).
    *   Se definen constantes como la IP (`HOST`), el puerto (`PORT`) y el directorio donde se esperan los archivos de texto (`TEXT_FILES_DIR`).
    *   Se configura el sistema de **logging** para que los detalles del procesamiento vayan a un archivo (`server_processing.log`), manteniendo la consola limpia.
    *   Se inicializan las estructuras de datos globales que almacenan el estado del servidor (eventos, clientes, configuraciones, colas) y los **locks** (`state_lock`, `processing_lock`) para protegerlas en entornos concurrentes.
    *   Se configura el socket principal del servidor (`server_socket`) y se pone en modo de escucha.
    *   Se verifica y crea el directorio `TEXT_FILES_DIR` si no existe.

2.  **Lanzamiento de Hilos de Fondo:**
    *   Se crean y se inician dos hilos (`threading.Thread`) que operarán en segundo plano, de forma concurrente con el bucle principal:
        *   `command_thread`: Ejecuta la función `server_commands()`, que maneja los comandos de administrador ingresados en la terminal del servidor.
        *   `batch_worker_thread`: Ejecuta la función `manage_client_batch_processing()`, que es responsable de tomar lotes de archivos de una cola y procesarlos.

3.  **Bucle Principal de Aceptación de Clientes (`main_server_loop`):**
    *   El hilo principal del script entra en un bucle infinito que espera y acepta nuevas conexiones de clientes.
    *   Por cada cliente que se conecta, se lanza un **nuevo hilo** (`threading.Thread`) que ejecuta la función `handle_client()`. Este hilo se encargará de toda la comunicación con ese cliente específico.

Este diseño multihilo permite que el servidor realice varias tareas simultáneamente: aceptar nuevas conexiones, responder a comandos del administrador y comunicarse con múltiples clientes, todo mientras procesa archivos en segundo plano.

---

## Estructuras de Datos y Locks Globales

Estas variables son compartidas y accedidas por múltiples hilos, por lo que su acceso está protegido por locks para evitar **condiciones de carrera** (cuando múltiples hilos intentan modificar la misma información al mismo tiempo, llevando a resultados impredecibles).

*   **`state_lock` (threading.Lock):** Un lock fundamental que protege el acceso a la mayoría de las estructuras de datos que definen el estado del servidor. Siempre que se vaya a leer o modificar `events`, `client_configs`, `client_queues`, `clients`, o `client_ids`, se debe adquirir este lock.
    *   **Concepto: Locks:** Un lock (o mutex) es un mecanismo de sincronización que permite que solo un hilo acceda a un recurso compartido a la vez. Si un hilo intenta adquirir un lock que ya está en posesión de otro, se bloqueará hasta que el lock sea liberado. [Más sobre Locks en Python](https://realpython.com/intro-to-python-threading/#how-to-use-a-lock)

*   **`events` (dict[str, set]):** Un diccionario donde las claves son los nombres de los eventos (ej., "data_event") y los valores son conjuntos (`set`) de los sockets de los clientes que están suscritos a ese evento.

*   **`client_configs` (dict):** Un diccionario que mapea el objeto `socket` de cada cliente a un diccionario que contiene su configuración (ej., `{'mode': 'threads', 'count': 4}`).

*   **`client_queues` (dict[str, collections.deque]):** Un diccionario donde las claves son los nombres de los eventos y los valores son colas (`collections.deque`) de los sockets de los clientes que están esperando ser procesados para ese evento. Es una cola FIFO (First-In, First-Out).

*   **`clients` (dict):** Un diccionario que mapea el objeto `socket` de cada cliente a su dirección de red (tupla `(IP, Puerto)`).

*   **`client_ids` (dict):** Un diccionario que mapea el objeto `socket` de cada cliente a un ID numérico único asignado por el servidor.

*   **`next_client_id` (int):** Un contador para asignar el próximo ID único a un cliente nuevo.

*   **`processing_lock` (threading.Lock):** Un lock específico que asegura que solo **un lote de archivos de un cliente** se esté procesando activamente en el servidor en un momento dado. Esto serializa el trabajo pesado para evitar sobrecargar el sistema, aunque el procesamiento *interno* de ese lote pueda ser paralelo (usando hilos o procesos).

*   **`client_batch_processing_queue` (collections.deque):** Una cola donde se almacenan los "lotes de procesamiento" que el comando `trigger` genera. Cada lote es una tupla `(client_socket, assigned_files_list, event_name, client_config)`. El hilo `manage_client_batch_processing` consume elementos de esta cola.

*   **`new_batch_event` (threading.Event):** Un objeto de sincronización que permite al hilo `server_commands` (cuando añade un lote a la cola) "despertar" al hilo `manage_client_batch_processing` si este está esperando por nuevos lotes.
    *   **Concepto: `threading.Event`:** Un `Event` es una bandera simple que puede estar en estado "establecido" (set) o "limpiado" (clear). Un hilo puede `wait()` en un evento, bloqueándose hasta que otro hilo lo `set()`. [Más sobre `threading.Event`](https://docs.python.org/3/library/threading.html#event-objects)

---

## Funciones Principales del Servidor

Las funciones se describen en un orden lógico para entender su interacción.

### 1. `server_log(message: str)`

*   **Propósito:** Centralizar la impresión de mensajes de log del servidor a la consola.
*   **Funcionamiento:** Imprime el `message` precedido por una nueva línea (`\n`). Esto ayuda a que los mensajes de hilos de fondo no se mezclen con el prompt `Server> ` del administrador. Sin embargo, el administrador podría necesitar presionar `Enter` para que el prompt se muestre correctamente después de un log asíncrono.

### 2. `send_to_client(client_socket: socket.socket, message: dict)`

*   **Propósito:** Enviar un mensaje estructurado (diccionario Python) a un cliente específico a través de su socket.
*   **Funcionamiento:**
    1.  Verifica si el `client_socket` aún está abierto.
    2.  Convierte el diccionario `message` a una cadena JSON (`json.dumps()`).
    3.  Añade un carácter de nueva línea (`\n`) al final de la cadena JSON. Esta es la clave del protocolo: el cliente usa `\n` para saber dónde termina un mensaje JSON y dónde empieza el siguiente.
    4.  Codifica la cadena JSON a bytes usando `utf-8`.
    5.  Envía los bytes a través del socket usando `client_socket.sendall()`.
    6.  **Manejo de Errores:** Si la conexión se rompe (`BrokenPipeError`, `ConnectionResetError`) o hay otro error de envío, se asume que el cliente se desconectó. Se inicia un nuevo hilo para llamar a `handle_disconnect()` y limpiar el estado del cliente.

### 3. `handle_disconnect(client_socket: socket.socket)`

*   **Propósito:** Limpiar todas las referencias a un cliente que se ha desconectado (ya sea de forma limpia o por un error).
*   **Funcionamiento:**
    1.  **Adquiere `state_lock`:** Protege el acceso a las estructuras de datos compartidas.
    2.  Elimina al cliente de `clients`, `client_ids` y `client_configs`.
    3.  Itera sobre `events` y `client_queues` para eliminar cualquier referencia al `client_socket` de las suscripciones y colas.
    4.  **Libera `state_lock`**.
    5.  Imprime un log de desconexión.
    6.  Intenta cerrar el `client_socket` para liberar recursos del sistema operativo.

### 4. `get_client_id(client_socket: socket.socket)` / `get_client_events(client_socket: socket.socket)` / `show_client_subscriptions()`

*   **Propósito:** Funciones auxiliares para obtener información específica de los clientes y sus suscripciones, usadas principalmente por los comandos de administración.
*   **Funcionamiento:** Acceden a las estructuras de datos globales (`client_ids`, `events`) siempre bajo la protección de `state_lock` para garantizar la consistencia. `show_client_subscriptions()` es utilizada por el comando `clients`.

### 5. `process_single_file_wrapper(arg_tuple: tuple)`

*   **Propósito:** Esta es la función que ejecuta el trabajo real de procesamiento de un solo archivo. Es invocada por los workers del pool de hilos o procesos (`ThreadPoolExecutor` o `ProcessPoolExecutor`).
*   **Funcionamiento:**
    1.  **Desempaqueta `arg_tuple`:** Recibe una tupla `(filepath, processing_mode)` y la desempaqueta.
    2.  **Identificación del Worker:**
        *   Si `processing_mode` es `'threads'`: `pid_label` es "THREAD ID", `worker_id_str` es `str(threading.get_ident())` (ID único del hilo de Python).
        *   Si `processing_mode` es `'forks'`: `pid_label` es "FORK PID", `worker_id_str` es `str(os.getpid())` (PID real del proceso fork).
        *   Se crea `descriptive_worker_id` (ej., "FORK PID\_12345") para logs y resultados.
    3.  **Impresión en Consola (Inicio/Fin):** Imprime un mensaje `print()` en la consola del servidor indicando que el worker (con su PID/ID) está iniciando o finalizando el procesamiento de un archivo. `sys.stdout.flush()` asegura que el mensaje aparezca inmediatamente.
    4.  **Logging Detallado:** Utiliza `logging.info()` para registrar el inicio y la finalización del procesamiento de cada archivo en el archivo `server_processing.log`.
    5.  **Llama a `parse_file`:** Invoca la función `parse_file()` (que es un alias de `parse_file_regex` de `extractor_regex.py`), pasándole la ruta del archivo y el `descriptive_worker_id`.
    6.  **Procesa el Resultado de `parse_file`:**
        *   Verifica el `status` y `error` devueltos por `parse_file`.
        *   Si `status` es "success", construye un diccionario de resultados para enviar al cliente con los datos extraídos.
        *   Si `status` es de error, construye un diccionario de resultados con el error.
        *   Los detalles de los datos extraídos o errores se loguean en el archivo.
    7.  **Manejo de Errores Inesperados:** Si ocurre una excepción *dentro de esta función `process_single_file_wrapper`* (no manejada por `parse_file`), se loguea un error con el traceback completo en el archivo de log (`logging.error(..., exc_info=True)`).
*   **Concepto: Paralelismo (ThreadPoolExecutor/ProcessPoolExecutor):** Estas clases de `concurrent.futures` permiten ejecutar funciones en paralelo. `ThreadPoolExecutor` usa hilos (comparten memoria, más ligeros), mientras que `ProcessPoolExecutor` usa procesos (memoria separada, más robustos para CPU-bound, implican "forks" en Linux/macOS).
    *   [Más sobre `concurrent.futures`](https://realpython.com/python-concurrency/#the-concurrentfutures-module)
    *   [Diferencia entre Hilos y Procesos](https://realpython.com/intro-to-python-threading/#processes-vs-threads)

### 6. `manage_client_batch_processing()`

*   **Propósito:** Este hilo trabajador es el "consumidor" de los lotes de archivos que el comando `trigger` genera. Procesa estos lotes uno a la vez.
*   **Funcionamiento:**
    1.  Bucle `while True`.
    2.  `new_batch_event.wait()`: Espera hasta que el comando `trigger` (o cualquier otra parte que añada un lote) llame a `new_batch_event.set()`.
    3.  **Adquiere `state_lock`:** Extrae un lote de `client_batch_processing_queue`. Si la cola está vacía, limpia el evento y vuelve a esperar.
    4.  **Libera `state_lock`**.
    5.  Verifica si el cliente del lote sigue conectado. Si no, descarta el lote.
    6.  **Adquiere `processing_lock`:** Este es el lock global que asegura que solo este lote se procese en el servidor en este momento.
    7.  **Procesamiento del Lote:**
        *   Envía un mensaje `START_PROCESSING` al cliente.
        *   Determina el `num_workers` y `processing_mode` del cliente.
        *   Selecciona el ejecutor (`ThreadPoolExecutor` o `ProcessPoolExecutor`) basado en `processing_mode`.
        *   Usa `executor.map(process_single_file_wrapper, map_input)` para distribuir los archivos del lote a los workers. `map_input` contiene tuplas `(filepath, processing_mode)`.
        *   Recopila los resultados de todos los workers.
        *   **Recopila PIDs/IDs de Workers:** Itera sobre los resultados y añade los `pid_server` (ej. "FORK PID\_12345") a un `set` (`worker_identifiers_used`) para obtener una lista única de los workers que participaron en este lote.
        *   Calcula la duración total del procesamiento del lote.
        *   **Imprime Resumen de Workers:** Imprime en la consola del servidor la línea "Lote para (...) completado en X.XXs." y luego una lista detallada de los "Workers utilizados" (con sus PIDs/IDs y el modo).
        *   Envía un mensaje `PROCESSING_COMPLETE` al cliente con todos los resultados.
    8.  **Manejo de Errores:** Si ocurre una excepción durante el procesamiento del lote, se loguea y se intenta notificar al cliente.
    9.  El `processing_lock` se libera automáticamente al salir del bloque `with`.
*   **Concepto: Patrón Productor-Consumidor:** El `trigger` (productor) añade lotes a la cola, y `manage_client_batch_processing` (consumidor) los procesa.

### 7. `handle_client(client_socket: socket.socket, addr: tuple)`

*   **Propósito:** Hilo dedicado que gestiona la comunicación bidireccional con un único cliente conectado.
*   **Funcionamiento:**
    1.  Asigna un `client_id` único al nuevo cliente.
    2.  **Adquiere `state_lock`:** Registra el cliente en `clients` y `client_ids`, y le asigna una configuración por defecto.
    3.  **Libera `state_lock`**.
    4.  Envía un mensaje `WELCOME` al cliente con su ID asignado y otra información.
    5.  Entra en un bucle `while True` para recibir mensajes del cliente:
        *   Llama a `client_socket.recv(4096)` (bloqueante).
        *   Decodifica y procesa los mensajes JSON delimitados por `\n`.
        *   **Procesa Comandos del Cliente:**
            *   **`SET_CONFIG`**: Actualiza la `client_configs` del cliente (bajo `state_lock`) y envía un `ACK_CONFIG`.
            *   **`SUB`**: Añade el cliente a `events` y `client_queues` para el evento especificado (bajo `state_lock`), y envía `ACK_SUB`. Imprime un log.
            *   **`UNSUB`**: Elimina el cliente de `events` y `client_queues` (bajo `state_lock`), y envía `ACK_UNSUB`. Imprime un log.
            *   **`PROCESS_FILES`**: **Este es un comando especial del cliente.** El cliente le pide al servidor que procese una lista específica de archivos (los que el usuario seleccionó para su simulación).
                *   El servidor toma estos archivos, obtiene la configuración de workers de *ese cliente*, y los procesa **directamente** usando `ThreadPoolExecutor` o `ProcessPoolExecutor` (similar a `manage_client_batch_processing`, pero sin pasar por la cola global `client_batch_processing_queue` o el `processing_lock`).
                *   Envía `PROCESSING_COMPLETE` al cliente con los resultados.
        *   Maneja errores de JSON y de conexión, llamando a `handle_disconnect()` si es necesario.
    6.  El bloque `finally` asegura que `handle_disconnect()` se llame al salir del bucle.

### 8. `print_help()`

*   **Propósito:** Muestra la lista de comandos disponibles para el administrador del servidor.

### 9. `server_commands()`

*   **Propósito:** Hilo dedicado que maneja los comandos que el administrador ingresa en la terminal del servidor.
*   **Funcionamiento:**
    1.  Llama a `print_help()` al inicio.
    2.  Bucle `while True` que espera `input("Server> ")` (bloqueante).
    3.  Procesa el comando ingresado:
        *   **`help`**: Llama a `print_help()`.
        *   **`add <evento>`**: Crea un nuevo evento en `events` y `client_queues` (bajo `state_lock`).
        *   **`remove <evento>`**: Elimina un evento (bajo `state_lock`).
        *   **`list`**: Muestra el estado actual de todos los eventos, colas y clientes conectados (bajo `state_lock`).
        *   **`clients`**: Muestra una lista de clientes y a qué eventos están suscritos (usando `show_client_subscriptions()`).
        *   **`status`**: Muestra si el servidor está ocupado (procesando un lote o con lotes en cola).
        *   **`trigger <evento>`**:
            *   **Adquiere `state_lock`:** Toma una "instantánea" de los clientes en la cola del evento y luego limpia esa cola.
            *   Filtra los clientes para asegurarse de que sigan conectados.
            *   Obtiene todos los archivos `.txt` del `TEXT_FILES_DIR`.
            *   **Distribuye los archivos:** Divide equitativamente los archivos entre los clientes activos que estaban en la cola para este `trigger`.
            *   Para cada cliente con archivos asignados, crea un "lote" `(client_socket, assigned_files, event_name, client_cfg)` y lo añade a `client_batch_processing_queue` (bajo `state_lock`).
            *   Llama a `new_batch_event.set()` para despertar al hilo `manage_client_batch_processing`.
        *   **`exit`**: Cierra el servidor. Notifica a todos los clientes, cierra sus sockets y el socket principal del servidor, y fuerza la salida del programa (`os._exit(0)`).
    4.  Maneja `EOFError` (Ctrl+D) y otras excepciones.

### 10. `main_server_loop()`

*   **Propósito:** El bucle principal del programa, responsable de aceptar nuevas conexiones de clientes.
*   **Funcionamiento:**
    1.  Bucle `while True`.
    2.  `server_socket.accept()`: Espera una nueva conexión. Esta llamada bloquea el hilo principal hasta que un cliente se conecta.
    3.  Cuando una conexión es aceptada, se crea un nuevo hilo (`client_handler_thread`) que ejecutará `handle_client()` para ese cliente específico.
    4.  El bucle vuelve a `accept()` inmediatamente, listo para la siguiente conexión.
    5.  **Manejo de Cierre:** El bucle está envuelto en un `try...except KeyboardInterrupt...finally` para asegurar un cierre ordenado si el servidor se interrumpe (ej., Ctrl+C). Notifica a los workers y clientes, y cierra los sockets.

---

## Protocolo de Comunicación (Mensajes JSON)

La comunicación entre el cliente y el servidor se realiza mediante mensajes JSON. Cada mensaje es un diccionario Python con una clave `"type"` (el comando o tipo de mensaje) y una clave `"payload"` (los datos asociados). Los mensajes están delimitados por un carácter de nueva línea (`\n`).

**Ejemplos de Mensajes Clave:**

*   **Cliente -> Servidor:**
    *   `{"type": "SET_CONFIG", "payload": {"mode": "threads", "count": 4}}`
    *   `{"type": "SUB", "payload": "data_event"}`
    *   `{"type": "UNSUB", "payload": "data_event"}`
    *   `{"type": "PROCESS_FILES", "payload": {"event": "data_event", "files": ["file1.txt", "file2.txt"]}}` (Cuando el cliente quiere que el servidor procese archivos específicos para su simulación).

*   **Servidor -> Cliente:**
    *   `{"type": "WELCOME", "payload": {"server_info": {"version": "1.0"}, "client_id": 1}}`
    *   `{"type": "ACK_CONFIG", "payload": {"status": "success", "config": {"mode": "threads", "count": 4}}}`
    *   `{"type": "ACK_SUB", "payload": "data_event"}`
    *   `{"type": "START_PROCESSING", "payload": {"event": "data_event", "files": ["file1.txt", "file2.txt"]}}` (El servidor le dice al cliente que va a procesar *su* lote de archivos).
    *   `{"type": "PROCESSING_COMPLETE", "payload": {"event": "data_event", "status": "success", "results": [...], "duration_seconds": 1.23}}` (Envía los resultados del procesamiento real).
    *   `{"type": "SERVER_EXIT", "payload": null}` (El servidor se está cerrando).

---

## Modelo de Concurrencia

El servidor utiliza una combinación de hilos (threading) y procesos (multiprocessing) para lograr la concurrencia:

*   **Hilo Principal:** Acepta nuevas conexiones de clientes.
*   **Hilos de Manejo de Clientes (`handle_client`):** Un hilo por cada cliente conectado, manejando su comunicación de forma independiente.
*   **Hilo de Comandos (`server_commands`):** Un hilo para la interfaz de línea de comandos del administrador.
*   **Hilo de Procesamiento de Lotes (`manage_client_batch_processing`):** Un hilo que serializa el procesamiento de lotes de clientes (uno a la vez) para evitar sobrecargas.
*   **Pool de Workers (`ThreadPoolExecutor` / `ProcessPoolExecutor`):** Dentro de `manage_client_batch_processing` (y en el manejo del comando `PROCESS_FILES`), se utilizan pools de hilos o procesos para ejecutar la función `process_single_file_wrapper` en paralelo.
    *   `ThreadPoolExecutor` es para el modo "threads": los workers son hilos dentro del mismo proceso del servidor.
    *   `ProcessPoolExecutor` es para el modo "forks": los workers son procesos separados (forks) del servidor.
*   **Locks (`state_lock`, `processing_lock`):** Se utilizan para proteger el acceso a los datos compartidos y para serializar el procesamiento de lotes, evitando condiciones de carrera y asegurando la consistencia del estado del servidor.
*   **Eventos (`new_batch_event`):** Para la comunicación entre el hilo de comandos y el hilo de procesamiento de lotes.

---

## Archivo de Log de Procesamiento

El servidor genera un archivo de log llamado `server_processing.log` en el mismo directorio donde se ejecuta el script. Este archivo contiene:

*   Marcas de tiempo para cada evento.
*   El nivel del log (INFO, ERROR).
*   Mensajes detallados sobre el inicio y fin del procesamiento de cada archivo por los workers (hilos o forks).
*   Detalles de los datos extraídos (si se configuran en `extractor_regex.py`).
*   Mensajes de error detallados, incluyendo el traceback completo si ocurren excepciones inesperadas durante el procesamiento.
