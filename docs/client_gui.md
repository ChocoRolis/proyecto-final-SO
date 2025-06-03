# Documentación Detallada del Cliente (`src/client_gui.py`)

Este documento describe el funcionamiento interno del script `client_gui.py`. La aplicación cliente proporciona una Interfaz Gráfica de Usuario (GUI) para interactuar con el servidor, configurar parámetros, y lo más importante, **simular y visualizar algoritmos de scheduling** basados en la información y los archivos que el servidor le asigna.

## Orden General de Ejecución y Componentes

1.  **Inicio y Configuración Inicial:** Al ejecutar `python -m src.client_gui`, el script:
    *   Importa librerías (Tkinter, socket, threading, json, queue, etc.) y los módulos locales `process.py` y `scheduler.py`.
    *   Define la clase principal `ClientApp`.
    *   En el bloque `if __name__ == "__main__":`:
        *   Crea la ventana principal de Tkinter (`tk.Tk()`).
        *   Crea una instancia de `ClientApp`.
        *   Configura el manejador para el evento de cierre de ventana (`on_closing`).
        *   Inicia el bucle principal de eventos de Tkinter (`root.mainloop()`).
2.  **Constructor `ClientApp.__init__(self, root)`:**
    *   Inicializa todas las variables de estado del cliente (conexión, suscripciones, configuración de workers, listas para la simulación, etc.).
    *   Crea una `queue.Queue` (`self.message_queue`) para la comunicación segura entre el hilo de red y el hilo principal de la GUI.
    *   Llama a `self._create_widgets()` para construir todos los elementos de la interfaz.
    *   Llama a `self._setup_output_dir()` para crear el directorio `output/`.
    *   Programa la primera llamada a `self.check_message_queue()` usando `root.after()`, iniciando un sondeo periódico de la cola de mensajes.
3.  **Construcción de la GUI (`_create_widgets`)**: Se crean todos los frames, botones, labels, entries, comboboxes, treeviews y scrolledtexts que componen la interfaz. Los widgets se organizan en secciones lógicas.
4.  **Interacción del Usuario y Flujo de Eventos:**
    *   El usuario interactúa con la GUI (ej. clic en "Conectar", "Suscribir", "Aplicar Config.", selecciona archivos, ingresa parámetros, inicia simulación).
    *   Estas acciones llaman a métodos específicos dentro de `ClientApp`.
    *   Los mensajes del servidor son recibidos por un hilo de red, puestos en `message_queue`, y procesados por `handle_server_message` en el hilo principal de la GUI.

---

## Funciones y Métodos Clave (agrupados por funcionalidad)

### A. Inicialización y GUI

#### 1. `ClientApp.__init__(self, root)`

*   **Propósito:** Constructor de la clase principal de la aplicación cliente.
*   **Funcionamiento:**
    *   Guarda la referencia a la ventana raíz `root`.
    *   Establece el título y tamaño de la ventana.
    *   Inicializa numerosas variables de instancia (`tk.StringVar`, `tk.IntVar`, listas, diccionarios, flags booleanos) para almacenar:
        *   Estado de la conexión al servidor (`self.client_socket`, `self.connected`, `self.server_addr`, `self.server_port`).
        *   Información de suscripción a eventos (`self.event_name_var`, `self.subscribed_events`).
        *   Configuración que el cliente enviará al servidor (`self.processing_mode_var`, `self.worker_count_var`).
        *   Datos para la simulación visual (`self.server_assigned_files`, `self.files_for_simulation_vars`, `self.process_params_entries`, `self.processes_to_simulate`, colas de simulación, `self.scheduler_sim`, etc.).
        *   Datos para el archivo CSV final (`self.output_csv_path`, `self.csv_headers`, `self.server_results_for_csv`).
    *   Crea `self.message_queue = queue.Queue()` para la comunicación segura entre el hilo de red y el hilo GUI.
    *   Llama a `self._create_widgets()` para construir la interfaz.
    *   Llama a `self._setup_output_dir()`.
    *   Inicia el sondeo de `self.message_queue` con `self.root.after(100, self.check_message_queue)`.
*   **Concepto:** Inicialización de un objeto, gestión de estado, configuración básica de Tkinter.

#### 2. `_setup_output_dir(self)`

*   **Propósito:** Asegurar que el directorio `output/` exista.
*   **Funcionamiento:** Usa `os.makedirs("output", exist_ok=True)` que crea el directorio si no existe y no da error si ya existe.

#### 3. `_create_widgets(self)`

*   **Propósito:** Construir y organizar todos los elementos visuales (widgets) de la GUI.
*   **Funcionamiento:**
    *   Crea `ttk.Frame` y `ttk.LabelFrame` para agrupar lógicamente los widgets.
    *   **Sección Superior:** Contiene frames para "Conexión Servidor", "Config. Cliente (p/ Servidor)", y "Suscripción Eventos".
        *   Widgets: `ttk.Entry` para IP/Puerto/Evento, `ttk.Button` para Conectar/Desconectar/Suscribir/Desuscribir/Aplicar Config, `ttk.Radiobutton` para modo Threads/Forks, `ttk.Spinbox` para cantidad de workers, `ttk.Label` para mostrar estado.
    *   **Sección Media:** Contiene frames para "Archivos Asignados (Seleccionar para Simulación)", "Parámetros de Simulación (Entrada Manual)", y "Config. Simulación Visual".
        *   **Selección de Archivos:** Usa un `tk.Canvas` con `ttk.Scrollbar` (`self.files_canvas`, `self.scrollable_files_frame`) para mostrar una lista de `ttk.Checkbutton` (uno por archivo asignado por el servidor). Un `ttk.Button` ("Definir Parámetros") confirma la selección.
        *   **Parámetros de Simulación:** Similarmente, usa un `tk.Canvas` con `ttk.Scrollbar` (`self.params_canvas`, `self.scrollable_params_frame`) para mostrar `ttk.Entry` donde el usuario ingresará Arrival Time, Burst Time (y Prioridad si aplica) para cada archivo seleccionado.
        *   **Config. Simulación Visual:** `ttk.Combobox` para el algoritmo de scheduling, `ttk.Spinbox` para el quantum (si es RR), y `ttk.Button` ("Iniciar Sim. Visual").
    *   **Sección Inferior:** Contiene un `ttk.Notebook` con pestañas para la "Tabla Procesos (Sim.)" y "Gantt (Sim.)". Al lado, un frame para "Métricas Promedio (Simulación)" y "Resultados del Servidor (para CSV)".
        *   Widgets: `ttk.Treeview` para la tabla de procesos simulados, `scrolledtext.ScrolledText` para el Gantt simulado y para mostrar los resultados del servidor, `ttk.Label` para métricas, `ttk.Button` para guardar CSV.
    *   **Barra de Estado:** Un `ttk.Label` en la parte inferior para mensajes generales.
    *   Llama a `self.change_scheduler_sim()` al final para configurar la visibilidad inicial de campos como el quantum.
*   **Concepto:** Diseño de GUI con Tkinter, uso de diferentes widgets, layout managers (pack, grid).

### B. Conexión y Comunicación con el Servidor

#### 4. `connect_server(self)`

*   **Propósito:** Establecer la conexión con el servidor.
*   **Funcionamiento:**
    1.  Obtiene la IP y el puerto de los `tk.StringVar`.
    2.  Crea un `socket.socket(socket.AF_INET, socket.SOCK_STREAM)`.
    3.  Intenta conectar con `self.client_socket.connect((ip, port))`.
    4.  Si tiene éxito:
        *   Actualiza `self.connected = True` y la barra de estado.
        *   Habilita/deshabilita botones correspondientes (Desconectar, Aplicar Config, Suscribir).
        *   Crea e inicia `self.receive_thread` (que ejecuta `self.listen_to_server()`).
        *   Llama a `self.send_client_config()` para enviar la configuración inicial del cliente al servidor.
    5.  Maneja `ValueError` (puerto inválido) y `socket.error` (fallo de conexión).
*   **Concepto:** Establecimiento de conexión TCP cliente.

#### 5. `disconnect_server(self)`

*   **Propósito:** Cerrar la conexión con el servidor y resetear el estado del cliente.
*   **Funcionamiento:**
    1.  Intenta cerrar `self.client_socket` si existe.
    2.  Resetea `self.client_socket = None`, `self.connected = False`, `self.simulation_running_sim = False`.
    3.  Actualiza la barra de estado y el estado de los botones.
    4.  Limpia `self.subscribed_events`, la UI de selección de archivos y la UI de parámetros.
*   **Concepto:** Cierre de conexión, reseteo de estado de la aplicación.

#### 6. `send_message(self, message: dict)`

*   **Propósito:** Función centralizada para enviar mensajes JSON al servidor.
*   **Funcionamiento:** Similar a `send_to_client` del servidor: convierte `message` a JSON, añade `\n`, codifica a `utf-8` y envía. Maneja errores de envío, llamando a `self.disconnect_server()` si la conexión se pierde.

#### 7. `listen_to_server(self)` (Ejecutada en `self.receive_thread`)

*   **Propósito:** Hilo dedicado a escuchar continuamente mensajes del servidor.
*   **Funcionamiento:**
    1.  Bucle `while self.connected and self.client_socket`.
    2.  Llama a `self.client_socket.recv(4096)` (bloqueante).
    3.  Si no hay datos, el servidor cerró la conexión. Se pone un mensaje de error en `self.message_queue`.
    4.  Decodifica los datos y los añade a un `buffer`.
    5.  Procesa el `buffer` buscando `\n` para separar mensajes JSON.
    6.  Por cada mensaje JSON parseado, lo pone en `self.message_queue` usando `self.message_queue.put(message)`.
    7.  Maneja errores de red y de parsing.
    8.  Si el bucle termina y el cliente aún se consideraba conectado, pone un mensaje `_THREAD_EXIT_` en la cola.
*   **Concepto:** Recepción de datos en hilos, buffering, parsing, comunicación inter-hilos segura mediante colas.
    *   **Recurso sobre `queue.Queue`:** [Real Python - An Intro to Threading in Python](https://realpython.com/intro-to-python-threading/#using-a-queue-with-threads)

#### 8. `check_message_queue(self)` (Ejecutada periódicamente en el hilo GUI)

*   **Propósito:** Sacar mensajes de `self.message_queue` y procesarlos en el hilo principal de la GUI.
*   **Funcionamiento:**
    1.  Bucle `while True` para procesar todos los mensajes actualmente en la cola.
    2.  Usa `self.message_queue.get_nowait()` para obtener un mensaje sin bloquear.
    3.  Si hay un mensaje, llama a `self.handle_server_message(message)`.
    4.  Si la cola está vacía (`queue.Empty`), sale del bucle `while`.
    5.  En el bloque `finally`, se reprograma a sí misma con `self.root.after(100, self.check_message_queue)`.
*   **Concepto:** Patrón de sondeo de cola no bloqueante, ejecución de lógica de UI en el hilo principal.

#### 9. `handle_server_message(self, message: dict)` (Ejecutada en el hilo GUI)

*   **Propósito:** Reaccionar a los mensajes recibidos del servidor y actualizar la GUI y el estado del cliente.
*   **Funcionamiento:** Un gran `if/elif` basado en `message.get("type")`:
    *   **`ACK_CONFIG`**: Actualiza la barra de estado. Actualiza `self.num_workers_for_sim_display` con la cantidad confirmada por el servidor, que se usará para la visualización del Gantt simulado.
    *   **`START_PROCESSING`**: Guarda la lista de `payload['files']` en `self.server_assigned_files`. Actualiza la barra de estado. Limpia resultados CSV anteriores. Llama a `self.display_file_selection_ui()` para mostrar los checkboxes de los archivos.
    *   **`PROCESSING_COMPLETE`**: Actualiza la barra de estado. Si `status` es "success", guarda `payload['results']` en `self.server_results_for_csv`, llama a `self.display_server_results()`, y habilita el botón para guardar CSV. Si es "failure", muestra un error.
    *   **`ACK_SUB` / `ACK_UNSUB`**: Actualiza `self.subscribed_events` y la etiqueta en la GUI.
    *   **`SERVER_EXIT` / `ERROR` / `_THREAD_EXIT_`**: Muestra un mensaje y llama a `self.disconnect_server()`.
*   **Concepto:** Manejo de eventos de red, actualización de la interfaz de usuario.

### C. Lógica de Configuración del Cliente y Suscripción a Eventos

#### 10. `send_client_config(self)`

*   **Propósito:** Enviar la configuración de modo (threads/forks) y cantidad al servidor.
*   **Funcionamiento:** Obtiene los valores de `self.processing_mode_var` y `self.worker_count_var`. Valida que la cantidad sea positiva. Envía un mensaje `SET_CONFIG` al servidor. Actualiza `self.num_workers_for_sim_display` localmente (aunque el valor autoritativo para la simulación Gantt vendrá del `ACK_CONFIG`).

#### 11. `subscribe_event(self)` y `unsubscribe_event(self)`

*   **Propósito:** Enviar solicitudes de suscripción/desuscripción al servidor.
*   **Funcionamiento:** Obtienen el nombre del evento de `self.event_name_var`. Validan. Envían mensajes `SUB` o `UNSUB`.

#### 12. `update_subscribed_label(self)`

*   **Propósito:** Actualizar la etiqueta en la GUI que muestra a qué eventos está suscrito el cliente.

### D. UI para Selección de Archivos y Parámetros de Simulación

#### 13. `display_file_selection_ui(self)`

*   **Propósito:** Crear dinámicamente los `ttk.Checkbutton` para que el usuario seleccione qué archivos (de los asignados por el servidor) incluir en la simulación visual.
*   **Funcionamiento:**
    1.  Llama a `self.clear_file_selection_ui()` y `self.clear_parameter_input_ui()`.
    2.  Si `self.server_assigned_files` está vacío, muestra un mensaje.
    3.  Para cada `filename` en `self.server_assigned_files`:
        *   Crea un `tk.BooleanVar(value=False)` (CORRECCIÓN: archivos deseleccionados por defecto).
        *   Crea un `ttk.Checkbutton` asociado a esa variable, con el `filename` como texto.
        *   Lo añade a `self.scrollable_files_frame`.
        *   Guarda la `BooleanVar` en `self.files_for_simulation_vars` (mapeando `filename` a su variable).
    4.  Habilita `self.confirm_files_button`.
    5.  Ajusta la altura del `self.files_canvas` dinámicamente.

#### 14. `clear_file_selection_ui(self)`

*   **Propósito:** Eliminar todos los widgets del `self.scrollable_files_frame` (los checkboxes).

#### 15. `setup_parameter_input_ui(self)`

*   **Propósito:** Crear dinámicamente los `ttk.Entry` para que el usuario ingrese Arrival Time, Burst Time (y Prioridad) para cada archivo que *seleccionó* en el paso anterior.
*   **Funcionamiento:**
    1.  Llama a `self.clear_parameter_input_ui()`.
    2.  Limpia datos de simulación previos (`self.processes_to_simulate`, `self.proc_tree_sim`).
    3.  Obtiene la lista de `selected_files` de `self.files_for_simulation_vars`.
    4.  Si no hay archivos seleccionados, muestra un mensaje y deshabilita el botón de iniciar simulación.
    5.  Crea etiquetas de cabecera ("Archivo", "Llegada", "Ráfaga", "Prioridad") en `self.scrollable_params_frame`.
    6.  Para cada `filename` en `selected_files`:
        *   Asigna un `pid_sim` (simulado, solo para esta GUI).
        *   Crea un `ttk.Frame` para la fila de entradas de este archivo.
        *   Crea `tk.StringVar` para Arrival, Burst, Priority con valores por defecto.
        *   Crea `ttk.Entry` asociados a estas `StringVar`.
        *   Guarda las `StringVar` y el widget de `Entry` de prioridad en `self.process_params_entries` (mapeando `pid_sim` a un diccionario con estas variables/widgets). Esto permite luego acceder a los valores ingresados y controlar la visibilidad del campo de prioridad.
    7.  Habilita `self.start_sim_button`.
    8.  Llama a `self.change_scheduler_sim()` para ajustar la visibilidad de la columna/entrada de prioridad y el scroll.
    9.  Ajusta la altura del `self.params_canvas` dinámicamente.

#### 16. `clear_parameter_input_ui(self)`

*   **Propósito:** Eliminar todos los widgets del `self.scrollable_params_frame` (las entradas de parámetros).

### E. Lógica de Simulación Visual

#### 17. `change_scheduler_sim(self, event=None)`

*   **Propósito:** Se llama cuando el usuario selecciona un nuevo algoritmo de scheduling en el `ttk.Combobox`.
*   **Funcionamiento:**
    1.  Obtiene el nombre del algoritmo.
    2.  Busca la clase de scheduler correspondiente en `AVAILABLE_SCHEDULERS` (de `scheduler.py`).
    3.  Crea una instancia del scheduler y la guarda en `self.scheduler_sim`. Si es "RR", también obtiene el valor del quantum del `self.quantum_spinbox`.
    4.  Determina si el scheduler seleccionado requiere campos de "Prioridad" o "Quantum".
    5.  Muestra u oculta las etiquetas/entradas de "Prioridad" en la UI de parámetros (`self.priority_header_label` y los `priority_entry_widget` individuales) y el `quantum_spinbox` según sea necesario.
    6.  Actualiza la barra de estado.

#### 18. `start_simulation_visual(self)`

*   **Propósito:** Iniciar o pausar la simulación visual.
*   **Funcionamiento:**
    1.  Si la simulación no está corriendo:
        *   Limpia datos de simulación previos (listas de procesos, tabla, Gantt).
        *   Itera sobre `self.process_params_entries` para cada archivo que el usuario configuró:
            *   Obtiene los valores de Arrival, Burst (y Priority) de las `tk.StringVar`.
            *   Valida que Burst sea positivo.
            *   Crea un objeto `Process` (de `process.py`) con estos datos.
            *   Añade el objeto a `self.processes_to_simulate`.
            *   Inserta una fila en la tabla `self.proc_tree_sim`.
        *   Si la validación falla o no hay procesos, no inicia.
        *   Establece `self.simulation_running_sim = True`.
        *   Actualiza el texto del botón a "Pausar Sim. Visual".
        *   Llama a `self.simulation_step_visual()` para el primer tick.
    2.  Si la simulación ya está corriendo (se presiona "Pausar"):
        *   Establece `self.simulation_running_sim = False`.
        *   Actualiza el texto del botón a "Reanudar Sim. Visual".

#### 19. `simulation_step_visual(self)` (El corazón de la simulación visual)

*   **Propósito:** Ejecutar un "tick" de la simulación visual. Se llama repetidamente mediante `root.after()`.
*   **Funcionamiento:**
    1.  Si `self.simulation_running_sim` es `False`, no hace nada.
    2.  Obtiene `current_time = self.simulation_time_sim`. Actualiza la etiqueta del tiempo.
    3.  **Llegadas:** Mueve procesos de `self.processes_to_simulate` a `self.ready_queue_sim` si `arrival_time <= current_time`. Actualiza su estado.
    4.  **Finalizaciones:** Itera sobre `self.running_processes_sim`. Si un proceso tiene `remaining_burst_time <= 0`, llama a `self.handle_process_completion_sim()`. Los que no terminan se mantienen.
    5.  **Scheduling:**
        *   Calcula `available_threads_sim` (basado en `self.num_workers_for_sim_display` que refleja la configuración del cliente y la cantidad actual en `self.running_processes_sim`).
        *   Si el algoritmo lo requiere (ej. SJF), ordena `self.ready_queue_sim`.
        *   Mientras haya `available_threads_sim` y procesos en `self.ready_queue_sim`:
            *   Llama a `self.scheduler_sim.schedule(...)` para obtener el `next_process`. El método `schedule` del scheduler es responsable de quitar el proceso de la `ready_queue_sim` si lo selecciona.
            *   Si se selecciona un proceso, se mueve a `self.running_processes_sim`, se actualiza su estado y `start_time`.
    6.  **Ejecución Simulada y RR:**
        *   Itera sobre `self.running_processes_sim`:
            *   Decrementa `proc.remaining_burst_time`.
            *   Registra el PID y el "thread simulado" (índice `i`) para el Gantt.
            *   Actualiza la tabla.
            *   **Para Round Robin (RR):** Si el scheduler es RR, incrementa un contador de `ticks_in_current_burst` para el proceso. Si este contador alcanza el `quantum` y el proceso aún no ha terminado, se añade a una lista `processes_to_requeue_rr`.
        *   Si `processes_to_requeue_rr` no está vacía, mueve esos procesos de `running_processes_sim` de vuelta al final de `ready_queue_sim` y resetea su `ticks_in_current_burst`.
    7.  Llama a `self.update_gantt_display_sim()`.
    8.  Incrementa `self.simulation_time_sim`.
    9.  **Comprueba Condición de Fin:** Si todas las listas de procesos (`processes_to_simulate`, `ready_queue_sim`, `running_processes_sim`) están vacías, la simulación termina. Se actualiza el botón, la barra de estado y se llama a `self.calculate_and_display_averages_sim()`.
    10. Si no ha terminado, se reprograma con `self.root.after(self.simulation_update_ms, self.simulation_step_visual)`.
*   **Concepto:** Simulación por eventos discretos (basada en ticks), implementación de la lógica de diferentes algoritmos de scheduling, interacción con objetos scheduler.

#### 20. `handle_process_completion_sim(self, process: Process, completion_time: int)`

*   **Propósito:** Se llama cuando un proceso simulado termina.
*   **Funcionamiento:** Actualiza el estado del `process` a "Terminated", calcula `completion_time`, `turnaround_time`, `waiting_time`. Lo mueve a `self.completed_processes_sim`. Actualiza la fila en `self.proc_tree_sim`. **No hay procesamiento de archivo real aquí.**

#### 21. `update_process_table_sim(self, pid_sim: int, updates: dict)`

*   **Propósito:** Actualizar una fila específica en la tabla de procesos simulados (`self.proc_tree_sim`).

#### 22. `update_gantt_display_sim(self, time_tick: int, running_pids_with_threads: list)`

*   **Propósito:** Añadir una nueva línea al `scrolledtext.ScrolledText` del Gantt simulado.
*   **Funcionamiento:** Construye una cadena como `T=5: [T0:P1] [T1:Idle] ...` basada en `running_pids_with_threads` y `self.num_workers_for_sim_display`.

#### 23. `calculate_and_display_averages_sim(self)`

*   **Propósito:** Calcular y mostrar el Turnaround Time Promedio y Waiting Time Promedio de los procesos simulados.

### F. Resultados del Servidor y Guardado de CSV

#### 24. `display_server_results(self)`

*   **Propósito:** Mostrar los resultados del procesamiento real (recibidos del servidor) en un `scrolledtext.ScrolledText`.
*   **Funcionamiento:** Limpia el área de texto. Itera sobre `self.server_results_for_csv` y formatea cada resultado (nombre de archivo, estado, datos extraídos o mensaje de error) para mostrarlo.

#### 25. `save_results_to_csv(self)`

*   **Propósito:** Guardar los `self.server_results_for_csv` (que contienen los datos extraídos por el servidor) en un archivo CSV.
*   **Funcionamiento:**
    1.  Abre `self.output_csv_path` en modo escritura (`'w'`).
    2.  Crea un `csv.writer`.
    3.  Escribe `self.csv_headers`.
    4.  Itera sobre `self.server_results_for_csv`. Para cada resultado:
        *   Extrae los datos relevantes (nombre de archivo, estado, datos específicos como emails, fechas, conteo de palabras, mensaje de error).
        *   Construye una `row_to_write` que coincida con el orden de `self.csv_headers`.
        *   Escribe la fila en el CSV.
    5.  Muestra un mensaje de éxito o error.
    *   **Importante:** La estructura de `self.csv_headers` y la forma en que se construye `row_to_write` deben coincidir con los datos que `server.py` (en `process_single_file_wrapper`) está enviando en el `payload` del mensaje `PROCESSING_COMPLETE`.

### G. Cierre de la Aplicación

#### 26. `on_closing(self)`

*   **Propósito:** Manejar el evento de cierre de la ventana principal.
*   **Funcionamiento:** Pregunta al usuario si está seguro. Si confirma, llama a `self.disconnect_server()` y luego a `self.root.destroy()`.

---
