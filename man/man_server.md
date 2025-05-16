# Documentación Detallada del Servidor (`src/server.py`)

Este documento describe el funcionamiento interno del script `server.py`. El servidor es responsable de gestionar eventos, clientes, configuraciones, y lo más importante, **procesar archivos de texto** según las solicitudes y configuraciones de los clientes.

## Orden General de Ejecución y Componentes

1.  **Inicio y Configuración Inicial:** Al ejecutar `python -m src.server`, el script primero importa las librerías necesarias, define constantes globales (como `HOST`, `PORT`, `TEXT_FILES_DIR`) y variables de estado compartidas (como `events`, `clients`, `client_queues`, `client_configs`, y los locks `state_lock`, `processing_lock`). Luego, configura el socket principal del servidor (`server_socket`) para escuchar conexiones entrantes y crea el directorio `TEXT_FILES_DIR` si no existe.
2.  **Lanzamiento de Hilos de Fondo:** Se inician dos hilos principales que corren en segundo plano:
    *   `command_thread`: Ejecuta la función `server_commands()` para manejar la entrada de administrador desde la terminal.
    *   `batch_worker_thread`: Ejecuta la función `manage_client_batch_processing()` que se encarga de procesar los lotes de archivos para los clientes.
3.  **Bucle Principal de Aceptación de Clientes:** El hilo principal del script entra en un bucle que espera (`server_socket.accept()`) y acepta nuevas conexiones de clientes. Por cada cliente que se conecta, se lanza un nuevo hilo que ejecuta la función `handle_client()`.
4.  **Manejo Concurrente:** Gracias a los hilos, el servidor puede:
    *   Aceptar nuevos clientes.
    *   Recibir y procesar comandos de administrador.
    *   Recibir y procesar mensajes de múltiples clientes conectados.
    *   Procesar lotes de archivos para los clientes de forma secuencial (un lote a la vez, pero el procesamiento de archivos dentro de un lote puede ser paralelo).

---

## Funciones Principales (en orden lógico de interacción)

### 1. `server_log(message: str)`

*   **Propósito:** Función de utilidad para imprimir mensajes desde el servidor a la consola.
*   **Funcionamiento:** Imprime una línea nueva (`\n`) antes del mensaje. Esto ayuda a que los mensajes asíncronos (que pueden aparecer mientras el administrador está escribiendo un comando) no se mezclen directamente con el prompt `Server> `. Sin embargo, el administrador podría necesitar presionar `Enter` para que el prompt `Server> ` se vuelva a mostrar correctamente después de un log.
*   **Concepto:** Manejo de salida en aplicaciones de consola multihilo.

### 2. `send_to_client(client_socket: socket.socket, message: dict)`

*   **Propósito:** Enviar un mensaje (diccionario Python) a un cliente específico.
*   **Funcionamiento:**
    1.  Verifica si el `client_socket` todavía es válido (no cerrado).
    2.  Convierte el diccionario `message` a una cadena JSON usando `json.dumps()`.
    3.  Añade un carácter de nueva línea (`\n`) al final de la cadena JSON. Este actúa como un delimitador para que el cliente pueda separar múltiples mensajes JSON si llegan juntos en un solo paquete TCP.
    4.  Codifica la cadena JSON a bytes (`utf-8`).
    5.  Envía todos los bytes al cliente usando `client_socket.sendall()`.
    6.  **Manejo de Errores:** Si ocurre un `BrokenPipeError` o `ConnectionResetError` (indican que el cliente se desconectó), o cualquier otra excepción durante el envío, se asume que el cliente ya no es accesible. En este caso, se lanza un nuevo hilo para ejecutar `handle_disconnect(client_socket)` y limpiar los datos de ese cliente.
*   **Concepto:** Comunicación por sockets, serialización JSON, manejo de errores de red.

### 3. `handle_disconnect(client_socket: socket.socket)`

*   **Propósito:** Función crucial para limpiar toda la información y recursos asociados a un cliente que se ha desconectado o ha causado un error irrecuperable.
*   **Funcionamiento:**
    1.  **Adquiere `state_lock`:** Esto es vital para modificar de forma segura las estructuras de datos compartidas (`clients`, `client_configs`, `events`, `client_queues`).
    2.  Verifica si el `client_socket` todavía está en el diccionario `clients`. Esto evita procesar desconexiones duplicadas si la función es llamada por múltiples caminos.
    3.  Si el cliente está registrado:
        *   Lo elimina de `clients` y `client_configs`.
        *   Itera sobre todas las listas de suscripción en `events` y elimina el `client_socket` de ellas.
        *   Itera sobre todas las colas de eventos en `client_queues` y reconstruye cada cola para quitar el `client_socket` (si estaba presente).
    4.  Si se procesó la desconexión (el cliente estaba registrado), imprime un mensaje de log.
    5.  **Libera `state_lock`**.
    6.  Intenta cerrar el `client_socket` del servidor (el que usa el servidor para comunicarse con ese cliente específico). Se manejan excepciones aquí porque el socket podría ya estar cerrado.
*   **Concepto:** Gestión de estado en sistemas concurrentes, uso de locks (`threading.Lock`) para evitar condiciones de carrera, limpieza de recursos.
    *   **Recurso sobre Locks:** [Real Python - An Intro to Threading in Python](https://realpython.com/intro-to-python-threading/#how-to-use-a-lock)

### 4. `handle_client(client_socket: socket.socket, addr: tuple)`

*   **Propósito:** Esta función se ejecuta en un hilo dedicado por cada cliente conectado. Maneja toda la comunicación entrante de ese cliente.
*   **Funcionamiento:**
    1.  Imprime un log de que el cliente se conectó.
    2.  **Adquiere `state_lock`:**
        *   Añade el cliente al diccionario `clients`.
        *   Si el cliente no tiene una configuración almacenada, le asigna `DEFAULT_CLIENT_CONFIG`.
    3.  **Libera `state_lock`**.
    4.  Entra en un bucle `while True` para recibir datos continuamente:
        *   Llama a `client_socket.recv(4096)` para leer hasta 4096 bytes. Esta llamada es **bloqueante** (el hilo espera aquí hasta que lleguen datos).
        *   Si `recv()` devuelve datos vacíos, el cliente cerró la conexión limpiamente, y el bucle se rompe.
        *   Los datos recibidos se decodifican de `utf-8` y se añaden a un `buffer` de string.
        *   Procesa el `buffer` buscando el delimitador `\n`. Si se encuentra, extrae un mensaje JSON completo.
        *   Intenta parsear el mensaje con `json.loads()`.
        *   Según el `"type"` del mensaje:
            *   **`SET_CONFIG`**: Valida el `payload`. Si es correcto, actualiza `client_configs[client_socket]` (protegido por `state_lock`) y envía un `ACK_CONFIG` al cliente.
            *   **`SUB`**: Valida el `payload` (nombre del evento). Con `state_lock`, añade el `client_socket` al conjunto de suscriptores en `events[event_name]` y a la cola FIFO en `client_queues[event_name]` (si no estaba ya). Envía `ACK_SUB`.
            *   **`UNSUB`**: Similar a `SUB`, pero elimina al cliente de `events` y `client_queues`. Envía `ACK_UNSUB`.
        *   Maneja `json.JSONDecodeError` si el mensaje no es JSON válido y otras excepciones.
    5.  Si el bucle `while` termina (por desconexión, error, etc.), el bloque `finally` asegura que `handle_disconnect(client_socket)` sea llamado para limpiar.
*   **Concepto:** Manejo de clientes concurrentes con hilos, bucles de recepción de red, parsing de protocolos (JSON sobre TCP), gestión de estado del cliente.

### 5. `print_help()`

*   **Propósito:** Imprimir la lista de comandos de administrador disponibles en la consola del servidor.
*   **Funcionamiento:** Simplemente imprime varias líneas de texto formateado.

### 6. `server_commands()`

*   **Propósito:** Esta función se ejecuta en un hilo dedicado (`command_thread`) y maneja los comandos ingresados por el administrador en la terminal del servidor.
*   **Funcionamiento:**
    1.  Llama a `print_help()` al inicio.
    2.  Entra en un bucle `while True`:
        *   Llama a `input("Server> ")`. Esta llamada es **bloqueante**.
        *   Procesa la entrada del usuario.
        *   Imprime una línea en blanco para separar la salida del comando del siguiente prompt.
        *   Según el comando:
            *   **`help`**: Llama a `print_help()`.
            *   **`add <evento>`**: Con `state_lock`, crea una nueva entrada en `events` (un `set` vacío) y en `client_queues` (un `collections.deque` vacío) si el evento no existe.
            *   **`remove <evento>`**: Con `state_lock`, elimina el evento de `events` y `client_queues`.
            *   **`list`**: Con `state_lock`, itera sobre `events`, `client_queues`, y `clients` e imprime su contenido de forma legible.
            *   **`status`**: Verifica si `client_batch_processing_queue` tiene elementos o si `processing_lock` está adquirido para determinar si el servidor está "Ocupado" o "Idle".
            *   **`trigger <evento>`**:
                1.  Imprime que se está intentando disparar el evento.
                2.  **Adquiere `state_lock` brevemente:**
                    *   Verifica si hay clientes en la cola para `event_name`.
                    *   Crea una copia (`clients_in_q_snapshot`) de los clientes actualmente en la cola `client_queues[event_name]`.
                    *   **Limpia `client_queues[event_name]`**. Esto significa que estos clientes han sido "tomados" para este trigger específico. Si se vuelven a suscribir, entrarán en la cola para un *futuro* trigger.
                    *   Filtra `clients_in_q_snapshot` para obtener `active_clients_for_event` (aquellos que siguen conectados y tienen configuración).
                3.  **Libera `state_lock`**.
                4.  Si no hay clientes activos, no hace nada más para este trigger.
                5.  Obtiene la lista de todos los archivos `.txt` del `TEXT_FILES_DIR`.
                6.  Si no hay archivos, notifica a los `active_clients_for_event` con un `PROCESSING_COMPLETE` indicando que no hay archivos y termina.
                7.  **Divide los archivos (`all_files`) entre los `active_clients_for_event`:** Calcula cuántos archivos le tocan a cada cliente, asegurando una distribución lo más equitativa posible.
                8.  Para cada cliente en `active_clients_for_event` y su lista de `assigned_files`:
                    *   Si el cliente no tiene archivos asignados (puede pasar si hay más clientes que archivos), le envía un `PROCESSING_COMPLETE` vacío.
                    *   Obtiene la configuración del cliente (`client_cfg`) con `state_lock`.
                    *   Si tiene configuración, crea una tupla de "lote": `(client_socket, assigned_files, event_name, client_cfg)`.
                    *   Añade este `batch` a la cola global `client_batch_processing_queue` (protegido por `state_lock`).
                9.  Si se crearon lotes, llama a `new_batch_event.set()` para despertar al hilo `batch_worker_thread`.
            *   **`exit`**: Notifica a todos los clientes conectados con `SERVER_EXIT`, los desconecta, cierra el socket principal y termina el proceso del servidor con `os._exit(0)`.
        *   Maneja `EOFError` (Ctrl+D) para un cierre similar a `exit`.
*   **Concepto:** Interfaz de línea de comandos (CLI), gestión de estado global, lógica de disparo de eventos, distribución de tareas.

### 7. `manage_client_batch_processing()`

*   **Propósito:** Esta función se ejecuta en un hilo dedicado (`batch_worker_thread`). Su única tarea es tomar "lotes de procesamiento de cliente" de la `client_batch_processing_queue` y procesarlos uno por uno.
*   **Funcionamiento:**
    1.  Entra en un bucle `while True`:
        *   Espera en `new_batch_event.wait()`. El hilo se bloquea aquí hasta que `new_batch_event.set()` es llamado (generalmente por el comando `trigger`).
        *   **Adquiere `state_lock` brevemente:**
            *   Intenta sacar un lote `(client_socket, assigned_files, event_name, config)` de `client_batch_processing_queue`.
            *   Si la cola está vacía, llama a `new_batch_event.clear()` y vuelve a esperar.
        *   **Libera `state_lock`**.
        *   Verifica si el `client_socket` del lote sigue conectado (consultando `clients` con `state_lock`). Si no, descarta el lote.
        *   **Adquiere `processing_lock` global:** Esto asegura que solo un lote de cliente se procese activamente en todo el servidor a la vez.
        *   **Procesa el Lote:**
            1.  Envía el mensaje `START_PROCESSING` al cliente, incluyendo la lista de `assigned_files` que le corresponden.
            2.  Obtiene `num_workers` y `mode` ('threads' o 'forks') de la `config` del cliente.
            3.  Construye las rutas completas a los archivos.
            4.  Selecciona la clase de ejecutor: `concurrent.futures.ThreadPoolExecutor` para 'threads' o `concurrent.futures.ProcessPoolExecutor` para 'forks'.
            5.  Crea una instancia del ejecutor con `max_workers=num_workers`.
            6.  Usa `executor.map(process_single_file_wrapper, input_list)` para distribuir el procesamiento de cada archivo a los workers. `input_list` es una lista de tuplas `(filepath,)`. `map` aplica la función a cada elemento y devuelve los resultados en orden.
            7.  Recopila todos los `results` de los workers.
            8.  Envía `PROCESSING_COMPLETE` al cliente con los `results` y la duración.
        *   Maneja excepciones durante el procesamiento, enviando un `PROCESSING_COMPLETE` con estado de "failure" si es posible.
        *   **Libera `processing_lock`** (fundamental, en un bloque `finally` implícito por el `with`).
*   **Concepto:** Patrón Productor-Consumidor (el `trigger` produce lotes, este hilo los consume), uso de `threading.Event` para señalización, pools de workers (`ThreadPoolExecutor`, `ProcessPoolExecutor`) para paralelismo, serialización del acceso a recursos críticos con `processing_lock`.
    *   **Recurso sobre ThreadPoolExecutor/ProcessPoolExecutor:** [Real Python - Speed Up Your Python Program With Concurrency](https://realpython.com/python-concurrency/# মৃত্যুপথ-যাত্রী-processes-and-threads) (ver secciones sobre `concurrent.futures`)
    *   **Recurso sobre `threading.Event`:** [Python `threading` — Thread-based parallelism](https://docs.python.org/3/library/threading.html#event-objects)

### 8. `process_single_file_wrapper(filepath_tuple: tuple)`

*   **Propósito:** Función que realmente procesa un único archivo. Es llamada por los workers del `ThreadPoolExecutor` o `ProcessPoolExecutor`.
*   **Funcionamiento:**
    1.  Desempaqueta el `filepath` de la `filepath_tuple` (ya que `map` pasa cada elemento del iterable de entrada como un argumento individual).
    2.  Obtiene el `filename` base.
    3.  Abre y lee el contenido del archivo.
    4.  **AQUÍ SE EJECUTA LA LÓGICA DE EXPRESIONES REGULARES (REGEX)** para encontrar patrones (emails, fechas, etc.).
    5.  Simula un pequeño retardo con `time.sleep()`.
    6.  Construye un diccionario `result_data` con los hallazgos.
    7.  Devuelve un diccionario con `{"filename": ..., "data": ..., "status": "success"}` o `{"filename": ..., "error": ..., "status": "error"}`.
*   **Concepto:** Procesamiento de archivos, expresiones regulares.

### 9. Bucle Principal de Aceptación (al final del script)

*   **Propósito:** El hilo principal del servidor se dedica a aceptar nuevas conexiones de clientes.
*   **Funcionamiento:**
    1.  Entra en un bucle `while True`.
    2.  Llama a `server_socket.accept()`. Esta es una llamada **bloqueante**.
    3.  Cuando un cliente se conecta, `accept()` devuelve un nuevo socket para ese cliente (`client_sock`) y su dirección (`client_addr`).
    4.  Crea un nuevo hilo (`client_handler_thread`) que ejecutará la función `handle_client` con los datos del nuevo cliente.
    5.  Inicia el `client_handler_thread`.
    6.  El bucle vuelve inmediatamente a `accept()` para esperar al siguiente cliente.
*   **Manejo de Cierre:** El bucle está dentro de un `try...except KeyboardInterrupt...finally` para intentar cerrar el servidor de forma ordenada si se presiona Ctrl+C o si ocurre un error fatal.

---
