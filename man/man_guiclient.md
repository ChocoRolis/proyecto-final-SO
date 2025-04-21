# Documentación del Código Fuente: `src/client_gui.py`

Este documento detalla el funcionamiento interno del script `client_gui.py`, que implementa la aplicación cliente con interfaz gráfica para el sistema de eventos y scheduling.

## Propósito General

El cliente es la interfaz interactiva del usuario con el sistema. Sus responsabilidades son multifacéticas:

1.  **Interfaz Gráfica (GUI):** Proporcionar una ventana visual e interactiva (usando Tkinter) para que el usuario controle la conexión, las suscripciones y visualice la simulación.
2.  **Conexión al Servidor:** Establecer y mantener una conexión TCP con el `server.py`.
3.  **Comunicación:** Enviar comandos al servidor (como `SUB`, `UNSUB`) y recibir mensajes (como `TRIGGER`, `CONFIG`, `SERVER_EXIT`).
4.  **Manejo de Eventos:** Reaccionar a los `TRIGGER` recibidos del servidor, iniciando la carga de "tareas" (archivos `.txt`).
5.  **Simulación de Scheduling:**
    *   Gestionar una cola de procesos (tareas) basados en los archivos `.txt` cargados.
    *   Simular la ejecución de estos procesos usando un algoritmo de scheduling seleccionable (FCFS, SJF, RR).
    *   Simular la concurrencia utilizando un número configurable de "threads/forks" (definido por el servidor).
    *   Calcular métricas de rendimiento (Turnaround Time, Waiting Time, etc.).
6.  **Visualización:** Mostrar el estado de la simulación en tiempo real (o casi real) en la GUI, incluyendo una tabla de procesos, una visualización tipo Gantt simplificada, y métricas promedio.
7.  **Procesamiento Real de Archivos:** Una vez que un proceso *simulado* completa su ejecución, lanzar el procesamiento real del archivo `.txt` asociado.
8.  **Extracción de Datos (Regex):** Usar expresiones regulares para extraer información específica de los archivos `.txt`.
9.  **Almacenamiento (CSV):** Escribir los datos extraídos, junto con las métricas de scheduling, en un archivo CSV único para esta instancia del cliente.
10. **Visualización de CSV:** Mostrar el contenido del archivo CSV mientras se va llenando.
11. **Manejo de Concurrencia:** Utilizar hilos (`threading`) y colas (`queue`) para asegurar que las operaciones de red y el procesamiento de archivos no bloqueen la interfaz gráfica y la simulación principal.

## Tecnologías Clave

*   **Tkinter:** Para la construcción de la interfaz gráfica de usuario.
*   **socket:** Para la comunicación de red TCP con el servidor.
*   **threading:** Para ejecutar tareas en segundo plano (escucha de red, procesamiento de archivos) sin congelar la GUI.
*   **queue:** Para la comunicación segura entre los hilos secundarios (red, archivos) y el hilo principal de la GUI.
*   **json:** Para codificar/decodificar mensajes en el protocolo de comunicación con el servidor.
*   **re:** Para la extracción de datos de archivos usando expresiones regulares.
*   **csv:** Para leer y escribir datos en formato CSV.
*   **os, time, datetime:** Para funcionalidades auxiliares (manejo de archivos/directorios, tiempo, identificadores).

## Estructura de la Clase Principal: `ClientApp`

Casi toda la lógica del cliente está encapsulada dentro de la clase `ClientApp`.

### 1. Inicialización (`__init__`)

```python
class ClientApp:
    def __init__(self, root):
        self.root = root # La ventana principal de Tkinter
        # ... (configuración ventana: título, tamaño) ...

        # --- Estado del Cliente (Networking y General) ---
        self.client_socket = None
        self.connected = False
        self.server_addr = tk.StringVar(value="127.0.0.1") # Para Entry de IP
        self.server_port = tk.StringVar(value="65432") # Para Entry de Puerto
        self.event_name = tk.StringVar(value="data_ready") # Para Entry de Evento
        self.subscribed_events = set() # Eventos a los que está suscrito
        self.message_queue = queue.Queue() # Cola para mensajes Thread -> GUI
        self.num_simulated_threads = 2 # Configuración por defecto, la actualiza el server
        self.client_id = f"client_{os.getpid()}_{int(time.time())}" # ID único
        self.output_csv_path = os.path.join("output", f"results_{self.client_id}.csv")
        self.csv_writer = None
        self.csv_file = None
        self.csv_lock = threading.Lock() # IMPORTANTE: Para escritura segura en CSV

        # --- Estado de Simulación ---
        self.processes_to_schedule = [] # Tareas nuevas esperando llegar (arrival_time)
        self.ready_queue = []           # Tareas listas para ejecución
        self.running_processes = []     # Tareas actualmente en las 'CPUs' simuladas
        self.completed_processes = []   # Tareas terminadas
        self.simulation_time = 0        # Reloj de la simulación
        self.scheduler = SchedulerFCFS() # Scheduler por defecto (instancia de clase Scheduler)
        self.selected_algorithm = tk.StringVar(value="FCFS") # Para Combobox
        self.process_pid_counter = 0    # Para asignar PIDs únicos
        self.simulation_running = False # Flag para controlar el bucle de simulación
        self.simulation_update_ms = 500 # Velocidad de la simulación (ms entre ticks)
        self.gantt_data = [] # (Opcional) Para almacenar datos para un Gantt más complejo

        # --- Configuración del CSV ---
        self.csv_headers = [...] # Encabezados definidos
        self._setup_csv() # Intenta abrir/crear el archivo CSV

        # --- Crear Widgets de la GUI ---
        self._create_widgets()

        # Iniciar chequeo periódico de la cola de mensajes
        self.root.after(100, self.check_message_queue)
```

*   **Variables de Estado:** Se inicializan numerosas variables para mantener el estado de la conexión, la suscripción, la configuración, las colas de procesos de la simulación, el scheduler seleccionado, el estado del archivo CSV, etc.
*   **`message_queue`:** Una `queue.Queue` estándar de Python. Es fundamental para pasar información de forma segura desde el hilo de escucha de red (`listen_to_server`) al hilo principal donde corre la GUI.
*   **`csv_lock`:** Un `threading.Lock`. Es esencial para prevenir condiciones de carrera si múltiples hilos (de `process_text_file_thread`) intentan escribir en el archivo CSV simultáneamente. Se usa con `with self.csv_lock:` para adquirir y liberar el bloqueo automáticamente.
*   **Colas de Simulación:** `processes_to_schedule`, `ready_queue`, `running_processes`, `completed_processes` almacenan instancias de la clase `Process` (definida en `process.py` o dentro de este archivo) en sus diferentes etapas.
*   **`_setup_csv()`:** Intenta crear el directorio `output/` y abre el archivo CSV correspondiente a este cliente en modo `append` (`a+`). Escribe los encabezados si el archivo es nuevo.
*   **`_create_widgets()`:** Llama al método que construye todos los elementos visuales de la GUI.
*   **`root.after(100, self.check_message_queue)`:** Programa la primera llamada a `check_message_queue` después de 100ms. Esta función se volverá a programar a sí misma, creando un bucle periódico no bloqueante para procesar mensajes del hilo de red.

### 2. Creación de la GUI (`_create_widgets`)

```python
    def _create_widgets(self):
        # Frame Conexión (IP, Puerto, Botones Conectar/Desconectar)
        # Frame Suscripción (Evento, Botones Suscribir/Desuscribir, Label de estado)
        # Frame Configuración Simulación (Combobox Algoritmo, Label Threads, Botón Iniciar/Pausar Sim)
        # Frame Visualización (con ttk.Notebook para Tabs)
            # Tab: Tabla de Procesos (ttk.Treeview para mostrar PIDs, Tiempos, Estados)
            # Tab: Visualización Gantt (scrolledtext.ScrolledText para Gantt simple o tk.Canvas)
            # Tab: Vista Previa CSV (scrolledtext.ScrolledText para mostrar contenido CSV)
        # Frame Métricas Promedio (Labels para Avg Turnaround/Waiting, Tiempo Sim)
        # Barra de Estado (ttk.Label en la parte inferior para mensajes)
```

*   Este método organiza la interfaz usando `ttk.Frame` y `ttk.LabelFrame`.
*   Utiliza `ttk.Notebook` para crear una interfaz con pestañas para las diferentes visualizaciones.
*   Widgets clave:
    *   `ttk.Entry` vinculados a `tk.StringVar` para entrada de texto (IP, Puerto, Evento).
    *   `ttk.Button` para acciones (Conectar, Suscribir, Iniciar Sim).
    *   `ttk.Combobox` para seleccionar el algoritmo.
    *   `ttk.Label` para mostrar información estática o dinámica (Estado suscripción, Threads, Métricas).
    *   `ttk.Treeview` para mostrar datos tabulares (Tabla de procesos, potencialmente el CSV).
    *   `scrolledtext.ScrolledText` para áreas de texto con desplazamiento (Gantt simple, Vista CSV).

### 3. Lógica de Red

#### `connect_server()` / `disconnect_server()`

*   `connect_server`: Intenta crear un `socket`, conectarse a la IP/Puerto dados, actualiza el estado `self.connected`, habilita/deshabilita botones, inicia el hilo `listen_to_server`. Maneja errores de conexión.
*   `disconnect_server`: Cierra el `client_socket` (si existe), actualiza `self.connected`, resetea botones y estado de suscripción, detiene la simulación.

#### `send_message(message)`

*   Función centralizada para enviar mensajes al servidor.
*   Toma un diccionario `message`, lo convierte a JSON (`json.dumps`), lo codifica a bytes (`encode('utf-8')`) y lo envía usando `client_socket.sendall()`.
*   Maneja errores si la conexión se pierde durante el envío, llamando a `disconnect_server`.

#### `listen_to_server()` (Ejecutada en un Hilo Separado)

```python
    def listen_to_server(self):
        while self.connected and self.client_socket:
            try:
                data = self.client_socket.recv(4096) # Bloqueante
                if not data: break # Conexión cerrada por el servidor
                # Decodifica, puede haber múltiples JSONs, intenta parsearlos
                buffer = data.decode('utf-8')
                # ... (lógica para separar y parsear múltiples JSONs si es necesario) ...
                for msg_str in buffer.split(...): # Depende de cómo envíe el server
                    try:
                       message = json.loads(msg_str)
                       self.message_queue.put(message) # PONE el mensaje en la COLA
                    except json.JSONDecodeError:
                       # Manejar JSON inválido o parcial
            except (ConnectionResetError, BrokenPipeError): break # Error de conexión
            except socket.error: break # Otro error de socket
            except Exception as e: break # Error inesperado
        # Si el bucle termina, pone un mensaje especial o maneja la desconexión
        if self.connected:
             self.message_queue.put({"type": "_THREAD_EXIT_", "payload": None})
```

*   **¡CRÍTICO!** Esta función corre en un hilo (`threading.Thread`) dedicado.
*   Su propósito es escuchar continuamente mensajes del servidor sin bloquear el hilo principal de la GUI.
*   Usa `client_socket.recv()`, que es **bloqueante** (el hilo espera aquí).
*   Cuando recibe datos, los decodifica, intenta parsearlos como JSON.
*   **Importante:** En lugar de interactuar directamente con la GUI (lo cual sería peligroso desde un hilo secundario), **pone el mensaje parseado (`message`) en la `self.message_queue`**.
*   Maneja errores de conexión o cierre.

#### `check_message_queue()` (Ejecutada en el Hilo Principal de la GUI)

```python
    def check_message_queue(self):
        try:
            while True: # Procesa todos los mensajes pendientes en la cola
                message = self.message_queue.get_nowait() # Saca mensaje SIN bloquear
                self.handle_server_message(message) # Procesa en el hilo GUI
        except queue.Empty:
            pass # La cola está vacía, no hay nada que hacer ahora
        finally:
            # Vuelve a programarse para ejecutarse de nuevo más tarde
            self.root.after(100, self.check_message_queue)
```

*   Esta función se ejecuta periódicamente en el **hilo principal de la GUI** gracias a `root.after`.
*   Intenta sacar mensajes de la `message_queue` usando `get_nowait()` (no bloqueante).
*   Si encuentra un mensaje, llama a `handle_server_message` **desde el hilo principal**, lo cual es seguro para actualizar la GUI.
*   Si la cola está vacía, simplemente no hace nada y espera a la siguiente ejecución programada.
*   Se reprograma a sí misma usando `root.after`, creando el bucle de chequeo.

#### `handle_server_message(message)` (Ejecutada en el Hilo Principal de la GUI)

```python
    def handle_server_message(self, message):
        msg_type = message.get("type")
        payload = message.get("payload")
        # --- Lógica para actuar según el tipo de mensaje ---
        if msg_type == "TRIGGER":
            # Carga archivos .txt, crea procesos, los añade a self.processes_to_schedule
            self.load_files_for_event(payload)
            # Actualiza GUI (status bar, quizás habilita botón 'Iniciar Sim')
        elif msg_type == "CONFIG":
            # Actualiza self.num_simulated_threads
            # Actualiza Label en la GUI
        elif msg_type == "ACK_SUB" / "ACK_UNSUB":
            # Actualiza self.subscribed_events
            # Actualiza Label en la GUI
        elif msg_type == "SERVER_EXIT":
            # Muestra mensaje y llama a self.disconnect_server()
        elif msg_type == "ERROR" or msg_type == "_THREAD_EXIT_":
            # Muestra error y llama a self.disconnect_server()
        # ... otros tipos de mensaje ...
```

*   Este método, llamado desde `check_message_queue`, contiene la lógica para reaccionar a los diferentes tipos de mensajes recibidos del servidor.
*   Como se ejecuta en el hilo principal, **puede modificar directamente la GUI** (actualizar labels, botones, etc.) y el estado de la simulación de forma segura.
*   Para `TRIGGER`, llama a `load_files_for_event`.
*   Para `CONFIG`, actualiza la variable local y la GUI.

### 4. Lógica de Suscripción

*   `subscribe_event()` / `unsubscribe_event()`: Toman el nombre del evento del `tk.StringVar`, validan la entrada y llaman a `send_message` para enviar el comando `SUB` o `UNSUB` al servidor.
*   `update_subscribed_label()`: Actualiza la etiqueta en la GUI para mostrar la lista actual de eventos suscritos.

### 5. Lógica de Simulación de Scheduling

#### `change_scheduler(event=None)`

*   Se llama cuando se selecciona un nuevo algoritmo en el `ttk.Combobox`.
*   Obtiene el nombre del algoritmo seleccionado.
*   Busca la clase correspondiente en `AVAILABLE_SCHEDULERS` (importado de `scheduler.py`) o usa `if/elif` para instanciar el objeto scheduler correcto (`SchedulerFCFS()`, `SchedulerSJF()`, `SchedulerRR(quantum=...)`).
*   Almacena la instancia del scheduler en `self.scheduler`.

#### `load_files_for_event(event_name)`

*   Se llama cuando se recibe un `TRIGGER`.
*   Busca archivos `.txt` en el directorio `text_files/`.
*   Para cada archivo encontrado:
    *   Calcula un `burst_time` simulado (ej. basado en el tamaño del archivo).
    *   Genera un `pid` único (`self.process_pid_counter`).
    *   Obtiene el `arrival_time` (que es el `self.simulation_time` actual).
    *   Crea una instancia de `Process(pid, filename, arrival_time, burst_time)`.
    *   Añade el nuevo objeto `Process` a la lista `self.processes_to_schedule`.
    *   Inserta una nueva fila en el `ttk.Treeview` de la tabla de procesos con los datos iniciales.
*   Actualiza la barra de estado.

#### `start_simulation()`

*   Cambia el flag `self.simulation_running` a `True`.
*   Actualiza el texto del botón (ej. a "Pausar Simulación").
*   Llama a `self.simulation_step()` para iniciar el primer "tick" de la simulación.

#### `simulation_step()` (El Corazón de la Simulación - Ejecutada en el Hilo Principal vía `root.after`)

```python
    def simulation_step(self):
        if not self.simulation_running: return # Si está pausada

        current_time = self.simulation_time
        # Actualizar label de tiempo en GUI

        # 1. Mover procesos de 'processes_to_schedule' a 'ready_queue'
        #    si su arrival_time <= current_time. Actualizar estado y tabla GUI.

        # 2. Manejar procesos que terminaron en el tick ANTERIOR:
        #    (Se hace implícito al quitar de running_processes, pero la lógica
        #     de cálculo de métricas y lanzamiento de file processing está en
        #     handle_process_completion, llamada al final del tick de ejecución)
        #    (Revisión: Mejor manejar la finalización ANTES de asignar nuevos)
        processes_just_finished = []
        temp_running = []
        for proc in self.running_processes:
             if proc.remaining_burst_time <= 0: # Proceso terminó en este tick
                 processes_just_finished.append(proc)
                 self.handle_process_completion(proc, current_time) # Calcula métricas, lanza thread de archivo
             else:
                 temp_running.append(proc) # Sigue corriendo
        self.running_processes = temp_running


        # 3. Seleccionar procesos para ejecutar (Scheduling):
        #    - Calcular `available_threads = self.num_simulated_threads - len(self.running_processes)`
        #    - Mientras `available_threads > 0` y `self.ready_queue` no esté vacía:
        #        - Llamar a `next_process = self.scheduler.schedule(self.ready_queue, current_time, self.running_processes, available_threads)`
        #        - Si `next_process` no es None:
        #            - Mover `next_process` de `ready_queue` a `running_processes`.
        #            - Actualizar estado, registrar `start_time` si es la primera vez.
        #            - Actualizar tabla GUI.
        #            - Decrementar `available_threads`.

        # 4. Simular la ejecución en los 'threads'/'CPUs':
        #    - Para cada `proc` en `self.running_processes`:
        #        - Decrementar `proc.remaining_burst_time -= 1`.
        #        - Actualizar columna "Restante" en tabla GUI.
        #        - Añadir info a la visualización Gantt (`update_gantt_display`).
        #        - (Si es RR: comprobar si se agotó el quantum. Si sí, mover a Ready).

        # 5. Incrementar tiempo de simulación: `self.simulation_time += 1`

        # 6. Comprobar si la simulación ha terminado:
        #    - Si `processes_to_schedule`, `ready_queue` y `running_processes` están vacías:
        #        - `self.simulation_running = False`
        #        - Actualizar botón y status bar.
        #        - Calcular y mostrar promedios (`calculate_and_display_averages`).
        #    - Else:
        #        - Programar el siguiente paso: `self.root.after(self.simulation_update_ms, self.simulation_step)`
```

*   Este método se llama repetidamente usando `root.after`, avanzando la simulación un "tick" cada vez.
*   **Fase 1 (Llegadas):** Mueve procesos cuya hora de llegada ha llegado desde la lista de espera a la `ready_queue`.
*   **Fase 2 (Finalizaciones):** Identifica los procesos en `running_processes` cuyo `remaining_burst_time` llegó a 0 o menos en el tick anterior. Llama a `handle_process_completion` para cada uno. Limpia la lista `running_processes`.
*   **Fase 3 (Scheduling):** Mientras haya "threads" simulados libres y procesos en la `ready_queue`, pide al objeto `self.scheduler` que seleccione el siguiente proceso a ejecutar (`self.scheduler.schedule(...)`). Mueve el proceso seleccionado a `running_processes`.
*   **Fase 4 (Ejecución):** Para cada proceso en `running_processes`, decrementa su tiempo restante y actualiza la GUI (tabla, Gantt). Implementa lógica de quantum para RR aquí si es necesario.
*   **Fase 5 (Avance del Tiempo):** Incrementa el reloj de la simulación.
*   **Fase 6 (Terminación/Continuación):** Comprueba si quedan procesos por ejecutar. Si no, detiene la simulación y calcula promedios. Si sí, usa `root.after` para programar la siguiente llamada a `simulation_step`.

#### `handle_process_completion(process, completion_time)`

*   Se llama cuando un proceso termina su ejecución simulada.
*   Calcula las métricas finales: `completion_time`, `turnaround_time`, `waiting_time`.
*   Actualiza el estado del proceso a "Terminated".
*   Mueve el proceso de `running_processes` (implícitamente, ya se quitó antes) a `completed_processes`.
*   Actualiza la fila correspondiente en la tabla de procesos (`ttk.Treeview`) con los tiempos finales.
*   **¡CRÍTICO!** Inicia un **nuevo hilo** (`threading.Thread`) que ejecutará `self.process_text_file_thread`, pasándole el nombre del archivo y el PID, para realizar el procesamiento real del archivo.

### 6. Procesamiento de Archivos y CSV

#### `process_text_file_thread(filename, pid)` (Ejecutada en un Hilo Separado)

```python
    def process_text_file_thread(self, filename, pid):
        filepath = os.path.join("text_files", filename)
        extracted_data = ["N/A"] * N # Placeholder para N datos a extraer
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # --- Ejecutar REGEX ---
                # dates = re.findall(r'...', content)
                # emails = re.findall(r'...', content)
                # if dates: extracted_data[0] = ...
                # if emails: extracted_data[1] = ...
        except Exception as e:
            # Manejar error de lectura o regex

        # --- Escribir en CSV (con bloqueo) ---
        process_info = next((p for p in self.completed_processes if p.pid == pid), None)
        if process_info:
            row_data = [ ... métricas ... ] + extracted_data
            with self.csv_lock: # Adquirir bloqueo ANTES de escribir
                if self.csv_writer and self.csv_file and not self.csv_file.closed:
                     try:
                        self.csv_writer.writerow(row_data)
                        self.csv_file.flush()
                        # Enviar datos a la GUI para actualizar vista previa
                        self.message_queue.put({"type": "_UPDATE_CSV_VIEW_", "payload": row_data})
                     except Exception as e:
                         # Manejar error de escritura
            # El bloqueo se libera automáticamente al salir del 'with'
```

*   Se ejecuta en un hilo separado para **no bloquear la simulación ni la GUI** durante la lectura de archivos y la ejecución de regex (que podrían ser lentas).
*   Abre y lee el archivo `.txt` correspondiente.
*   **Aquí es donde se definen y ejecutan las expresiones regulares (`re.findall`, `re.search`)** para extraer la información necesaria.
*   Construye la fila de datos que irá al CSV (métricas del `process_info` + datos extraídos).
*   **Usa `with self.csv_lock:` para escribir en el archivo CSV de forma segura**, evitando que dos hilos escriban al mismo tiempo y corrompan el archivo.
*   Después de escribir, pone un mensaje en la `message_queue` (`_UPDATE_CSV_VIEW_`) para que el hilo principal actualice la vista previa del CSV en la GUI.

#### `_setup_csv()` / `save_or_update_csv_view()` / `update_csv_preview(row_data)`

*   `_setup_csv`: Inicializa el archivo CSV al principio.
*   `save_or_update_csv_view`: (Llamado por un botón) Lee el contenido completo del archivo CSV (con el lock) y lo muestra en el `scrolledtext.ScrolledText` de la vista previa.
*   `update_csv_preview`: (Llamado desde `handle_server_message` cuando llega `_UPDATE_CSV_VIEW_`) Añade una sola fila formateada al final del `scrolledtext.ScrolledText` de la vista previa, proporcionando una actualización más "en vivo".

### 7. Actualizaciones de la GUI y Métricas

*   `update_process_table(pid, updates)`: Encuentra la fila con el `pid` dado en el `ttk.Treeview` de procesos y actualiza las columnas especificadas en el diccionario `updates`.
*   `update_gantt_display(time, running_pids_with_threads)`: Añade una línea al `scrolledtext.ScrolledText` del Gantt, mostrando qué PID se está ejecutando en qué "thread" simulado en el `time` actual.
*   `calculate_and_display_averages()`: Se llama al final de la simulación. Itera sobre `self.completed_processes`, calcula los promedios de Turnaround y Waiting Time, y actualiza las `ttk.Label` correspondientes en la GUI.

### 8. Manejo del Cierre (`on_closing`)

*   Se asocia al evento de cierre de la ventana (`WM_DELETE_WINDOW`).
*   Pregunta al usuario si está seguro.
*   Llama a `disconnect_server()` para intentar un cierre limpio de la conexión.
*   Cierra el archivo CSV (`self.csv_file.close()`) de forma segura (usando el `csv_lock`).
*   Destruye la ventana principal (`self.root.destroy()`).

### 9. Bloque Principal (`if __name__ == "__main__":`)

*   Crea la ventana raíz de Tkinter (`tk.Tk()`).
*   Crea una instancia de `ClientApp(root)`.
*   Configura el manejador `on_closing` para el cierre de la ventana.
*   Inicia el bucle principal de eventos de Tkinter (`root.mainloop()`), que hace que la ventana aparezca y responda a las interacciones del usuario y a los eventos `root.after`.

## Modelo de Concurrencia

El cliente utiliza un modelo de concurrencia cuidadoso para mantener la GUI receptiva:

1.  **Hilo Principal:** Ejecuta el bucle de eventos de Tkinter (`root.mainloop`). Maneja todas las interacciones del usuario, las actualizaciones directas de la GUI y el bucle de simulación (`simulation_step` llamado vía `root.after`).
2.  **Hilo de Escucha de Red (`listen_to_server`):** Un `threading.Thread` dedicado a esperar (`socket.recv()`) mensajes del servidor. **NO** interactúa directamente con la GUI. Pasa los mensajes recibidos al hilo principal a través de `message_queue`.
3.  **Hilos de Procesamiento de Archivos (`process_text_file_thread`):** Se crea un `threading.Thread` por cada proceso simulado que termina. Estos hilos leen archivos y ejecutan regex. **NO** interactúan directamente con la GUI principal, excepto para poner mensajes en la `message_queue` para actualizar la vista previa del CSV. Usan `csv_lock` para acceder de forma segura al archivo CSV compartido.
4.  **Comunicación Hilo->GUI:** La `queue.Queue` (`message_queue`) y el mecanismo `root.after(..., check_message_queue)` son el puente seguro para que los hilos secundarios pasen información al hilo principal para que éste pueda actualizar la GUI sin riesgo de condiciones de carrera o errores de Tkinter.

## Conclusión

`client_gui.py` es una aplicación compleja que integra múltiples conceptos: interfaz gráfica, red, simulación de algoritmos de SO, procesamiento de archivos y manejo seguro de concurrencia. La separación de tareas en hilos y el uso de una cola para la comunicación inter-hilos son clave para su funcionamiento correcto y responsivo. La clase `ClientApp` orquesta todas estas piezas, manteniendo el estado de la aplicación y respondiendo a eventos tanto del usuario como del servidor.
