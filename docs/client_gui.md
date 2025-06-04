# Documentación Detallada del Cliente (`src/client_gui.py`)

El script `client_gui.py` implementa la aplicación cliente con Interfaz Gráfica de Usuario (GUI) para interactuar con el servidor. Es el punto de control y visualización para el usuario.

## Propósito General

El cliente tiene múltiples roles:

1.  **Interfaz de Usuario (GUI):** Proporcionar una ventana visual e interactiva para que el usuario configure, controle y observe el sistema.
2.  **Comunicación con el Servidor:** Conectarse al servidor, enviar configuraciones y solicitudes (suscripciones, desuscripciones) y recibir notificaciones y resultados del procesamiento real.
3.  **Simulación de Scheduling:** Ejecutar una simulación visual de cómo se distribuiría el trabajo (archivos) entre workers (hilos/procesos simulados) bajo diferentes algoritmos de planificación.
4.  **Visualización de Simulación:** Mostrar el estado de los procesos simulados (tabla de procesos, diagrama de Gantt) y calcular métricas de rendimiento (tiempos promedio).
5.  **Visualización de Resultados Reales:** Mostrar los resultados del procesamiento de archivos realizado por el servidor y permitir guardarlos en un archivo CSV.

## Flujo General de Ejecución del Cliente

Cuando ejecutas `python -m src.client_gui`, el programa sigue este flujo:

1.  **Inicio y Configuración Inicial:**
    *   Se importan todas las librerías necesarias (Tkinter, socket, threading, JSON, etc.) y los módulos locales `process.py` y `scheduler.py`.
    *   Se define la clase principal `ClientApp`.
    *   En el bloque `if __name__ == "__main__":`:
        *   Se crea la ventana principal de Tkinter (`tk.Tk()`).
        *   Se crea una instancia de `ClientApp`, que inicializa todas las variables de estado y construye la GUI.
        *   Se configura el manejador para el evento de cierre de ventana (`on_closing`).
        *   Se inicia el bucle principal de eventos de Tkinter (`root.mainloop()`). Este bucle es el corazón de la GUI, procesando eventos de usuario y actualizaciones de la interfaz.

2.  **Constructor `ClientApp.__init__(self, root)`:**
    *   Este método se ejecuta una vez al inicio del programa.
    *   Guarda la referencia a la ventana raíz (`self.root`).
    *   Configura el tema visual de la GUI (`self.setup_theme()`).
    *   Asegura la existencia del directorio `output/` (`self._setup_output_dir()`).
    *   Inicializa **todas las variables de estado** de la aplicación:
        *   Variables de conexión y comunicación (sockets, estado conectado, direcciones, colas de mensajes).
        *   Variables para la configuración del cliente (modo y cantidad de workers para el servidor).
        *   Variables para la gestión de archivos (asignados por el servidor, seleccionados para simulación, parámetros manuales).
        *   Variables para la simulación visual (colas de procesos simulados, scheduler, tiempo de simulación, contadores, datos para Gantt).
        *   Variables para la gestión de resultados CSV.
    *   Crea `self.message_queue = queue.Queue()`: Esta cola es **fundamental** para la comunicación segura entre los hilos de fondo (como el hilo que escucha al servidor) y el hilo principal de la GUI.
    *   Llama a `self._create_widgets()` para construir toda la interfaz gráfica.
    *   Programa la primera llamada a `self.check_message_queue()` usando `self.root.after(100, self.check_message_queue)`. Esto establece un bucle periódico para procesar mensajes de la cola sin bloquear la GUI.

3.  **Construcción de la GUI (`_create_widgets`)**:
    *   Este método organiza y crea todos los elementos visuales (widgets) de la aplicación.
    *   Utiliza `ttk.Frame` y `ttk.LabelFrame` para agrupar lógicamente los widgets en secciones.
    *   **Sección Superior:** Contiene los controles de conexión al servidor, la configuración de workers del cliente (para enviar al servidor) y la suscripción/desuscripción a eventos.
    *   **Sección Media:** Dedicada a la simulación. Incluye:
        *   Un área para mostrar los archivos asignados por el servidor con `ttk.Checkbutton` para que el usuario seleccione cuáles simular. Esta área tiene un `tk.Canvas` con `ttk.Scrollbar` para manejar muchas entradas.
        *   Un área para la entrada manual de parámetros de simulación (Arrival Time, Burst Time, Prioridad) para los archivos seleccionados. También usa un `tk.Canvas` con `ttk.Scrollbar`.
        *   Controles para la configuración de la simulación visual (selección de algoritmo, quantum para RR, botón de inicio/pausa).
    *   **Sección Inferior:** Contiene un `ttk.Notebook` (pestañas) para las visualizaciones:
        *   **Tabla de Procesos:** Un `ttk.Treeview` para mostrar el estado y las métricas de los procesos simulados.
        *   **Diagrama de Gantt:** Un `tk.Canvas` con scrollbars para la visualización gráfica de la simulación.
        *   **Resultados del Servidor:** Un `ttk.Treeview` para mostrar los resultados del procesamiento real de archivos recibido del servidor, con un botón para guardar a CSV.
    *   **Barra de Estado:** Un `ttk.Label` en la parte inferior para mensajes informativos.
    *   Configura el tema visual aplicando estilos a los widgets.

---

## Funciones y Métodos Clave del Cliente

### A. Configuración y Estilo de la GUI

#### 1. `setup_theme(self)`

*   **Propósito:** Aplicar un tema visual moderno y consistente a toda la GUI.
*   **Funcionamiento:** Utiliza `ttk.Style()` para configurar colores, fuentes, padding y bordes para diferentes tipos de widgets (botones, entradas, labels, frames, treeviews, etc.). Define una paleta de colores personalizada y aplica estos estilos a través de `style.configure()` y `style.map()`.

#### 2. `_setup_output_dir(self)`

*   **Propósito:** Asegurar que el directorio `output/` exista en el sistema de archivos local.
*   **Funcionamiento:** Usa `os.makedirs("output", exist_ok=True)` para crear el directorio si no existe, sin generar un error si ya está presente.

### B. Conexión y Comunicación con el Servidor

#### 3. `connect_server(self)`

*   **Propósito:** Establecer la conexión TCP con el servidor.
*   **Funcionamiento:**
    1.  Obtiene la IP y el puerto de los campos de entrada.
    2.  Crea un `socket.socket()` y llama a `self.client_socket.connect()`.
    3.  Si la conexión es exitosa, actualiza el estado de la GUI (barra de estado, botones).
    4.  Crea y lanza `self.receive_thread`, que ejecutará `self.listen_to_server()` en un hilo separado.
    5.  Envía la configuración inicial del cliente al servidor llamando a `self.send_client_config()`.
    6.  Maneja errores de valor (puerto inválido) y errores de conexión de socket.

#### 4. `disconnect_server(self)`

*   **Propósito:** Cerrar la conexión actual con el servidor y resetear la interfaz de usuario a su estado inicial.
*   **Funcionamiento:**
    1.  Cierra `self.client_socket`.
    2.  Actualiza el estado `self.connected = False`.
    3.  Resetea todas las variables de estado relevantes (simulación, suscripciones, UI de archivos/parámetros).
    4.  Actualiza los botones y etiquetas de la GUI.

#### 5. `send_message(self, message: dict)`

*   **Propósito:** Enviar un mensaje estructurado (diccionario Python) al servidor.
*   **Funcionamiento:**
    1.  Convierte el diccionario `message` a una cadena JSON (`json.dumps()`).
    2.  Añade un carácter de nueva línea (`\n`) al final de la cadena JSON como delimitador.
    3.  Codifica la cadena JSON a bytes (`utf-8`).
    4.  Envía los bytes a través del socket usando `self.client_socket.sendall()`.
    5.  Maneja errores de red (`BrokenPipeError`, `ConnectionResetError`), llamando a `self.disconnect_server()` si la conexión se pierde.

#### 6. `listen_to_server(self)` (Ejecutada en `self.receive_thread`)

*   **Propósito:** Escuchar continuamente mensajes entrantes del servidor en un hilo de fondo.
*   **Funcionamiento:**
    1.  Se ejecuta en un bucle `while True` dentro de `self.receive_thread`.
    2.  Llama a `self.client_socket.recv(4096)` para recibir datos. Esta llamada es **bloqueante**; el hilo espera aquí hasta que llegan datos.
    3.  Los datos recibidos se decodifican, se añaden a un `buffer`, y se procesan para extraer mensajes JSON completos (usando `\n` como delimitador).
    4.  Cada mensaje JSON parseado se coloca en `self.message_queue` usando `self.message_queue.put(message)`. Esto es crucial para la **comunicación segura entre hilos**, ya que el hilo de red no debe interactuar directamente con los widgets de Tkinter.
    5.  Maneja errores de conexión (ej., servidor desconectado) o de parsing JSON.

#### 7. `check_message_queue(self)` (Ejecutada periódicamente en el hilo principal de la GUI)

*   **Propósito:** Procesar mensajes de la cola de mensajes de forma segura en el hilo principal de la GUI.
*   **Funcionamiento:**
    1.  Se llama periódicamente (`self.root.after(100, ...)`).
    2.  Intenta obtener mensajes de `self.message_queue` usando `self.message_queue.get_nowait()` (no bloqueante).
    3.  Si hay un mensaje, llama a `self.handle_server_message(message)` para procesarlo.
    4.  Si la cola está vacía (`queue.Empty`), simplemente no hace nada hasta la siguiente llamada.
    *   **Concepto: Patrón Productor-Consumidor (Hilos):** `listen_to_server` es el "productor" (pone mensajes en la cola), y `check_message_queue` es el "consumidor" (saca y procesa mensajes en el hilo de la GUI).

#### 8. `handle_server_message(self, message: dict)` (Ejecutada en el hilo principal de la GUI)

*   **Propósito:** Interpretar y reaccionar a los mensajes recibidos del servidor.
*   **Funcionamiento:**
    *   Analiza el `msg_type` del mensaje recibido:
        *   **`WELCOME`**: Mensaje inicial del servidor. Actualiza la barra de estado.
        *   **`ACK_CONFIG`**: Confirma que el servidor recibió la configuración del cliente. Actualiza `self.num_workers_for_sim_display` para el Gantt.
        *   **`ACK_SUB` / `ACK_UNSUB`**: Confirma suscripción/desuscripción. Actualiza `self.subscribed_events` y la etiqueta de suscripciones.
        *   **`START_PROCESSING`**: El servidor informa que va a procesar un lote de archivos para este cliente. Guarda la lista de `payload['files']` en `self.server_assigned_files` y llama a `self.display_file_selection_ui()` para que el usuario elija qué simular.
        *   **`PROCESSING_COMPLETE`**: El servidor ha terminado de procesar el lote de archivos real. Guarda `payload['results']` en `self.server_results_for_csv`, llama a `self.display_server_results()` y habilita el botón para guardar CSV.
        *   **`SERVER_EXIT`**: El servidor se está cerrando. Muestra un mensaje y llama a `self.disconnect_server()`.
        *   **`ERROR` / `_THREAD_EXIT_`**: Maneja errores de comunicación.
    *   Todas las actualizaciones de la GUI se realizan aquí, ya que este método se ejecuta en el hilo principal, lo cual es seguro.

### C. Configuración del Cliente y Suscripción a Eventos

#### 9. `send_client_config(self)`

*   **Propósito:** Recopilar la configuración de workers (modo: threads/forks, cantidad) del usuario y enviarla al servidor.
*   **Funcionamiento:** Obtiene los valores de `self.processing_mode_var` y `self.worker_count_var`. Valida la cantidad y envía un mensaje `SET_CONFIG` al servidor.

#### 10. `subscribe_event(self)`

*   **Propósito:** Suscribir al cliente a un evento específico en el servidor.
*   **Funcionamiento:** Obtiene el nombre del evento de `self.event_name_var`, valida, y envía un mensaje `SUB` al servidor.

#### 11. `unsubscribe_event(self)`

*   **Propósito:** Desuscribir al cliente de un evento.
*   **Funcionamiento:** Obtiene el nombre del evento (preferentemente del `ttk.Combobox` de eventos suscritos, o del campo de entrada). Valida si el cliente está suscrito y envía un mensaje `UNSUB` al servidor.

#### 12. `on_event_selected_for_unsub(self, event=None)`

*   **Propósito:** Listener para el `ttk.Combobox` de desuscripción.
*   **Funcionamiento:** Cuando el usuario selecciona un evento en el combobox, actualiza el campo de entrada `self.event_name_var` para mayor comodidad.

#### 13. `update_subscribed_label(self)`

*   **Propósito:** Actualizar la etiqueta que muestra la lista de eventos a los que el cliente está suscrito, y también actualizar las opciones del `ttk.Combobox` de desuscripción.

### D. UI para Selección de Archivos y Parámetros de Simulación

#### 14. `display_file_selection_ui(self)`

*   **Propósito:** Mostrar los archivos que el servidor ha asignado a este cliente, permitiendo al usuario seleccionar cuáles quiere incluir en la simulación visual.
*   **Funcionamiento:**
    1.  Limpia las UIs de selección de archivos y de parámetros anteriores.
    2.  Para cada archivo en `self.server_assigned_files`, crea un `ttk.Checkbutton` con `tk.BooleanVar(value=False)` (deseleccionado por defecto).
    3.  Añade los checkboxes a `self.scrollable_files_frame` (dentro del `tk.Canvas` para scroll).
    4.  Habilita el botón "Definir Parámetros".
    5.  Ajusta dinámicamente la altura del `tk.Canvas` de archivos.

#### 15. `clear_file_selection_ui(self)`

*   **Propósito:** Eliminar todos los `ttk.Checkbutton` del área de selección de archivos.

#### 16. `setup_parameter_input_ui(self)`

*   **Propósito:** Crear dinámicamente los campos de entrada (`ttk.Entry`) para que el usuario especifique el Arrival Time, Burst Time (y Prioridad) para cada archivo que seleccionó para la simulación.
*   **Funcionamiento:**
    1.  Limpia la UI de parámetros anterior.
    2.  Obtiene la lista de archivos seleccionados por el usuario.
    3.  Crea etiquetas de cabecera para "Archivo", "Llegada", "Ráfaga" y "Prioridad".
    4.  Para cada archivo seleccionado, crea una fila de `ttk.Entry` (vinculados a `tk.StringVar`) para sus parámetros.
    5.  Almacena estas `tk.StringVar` y los widgets de prioridad en `self.process_params_entries` para poder acceder a los valores y controlar la visibilidad de la prioridad.
    6.  Habilita el botón "Iniciar Simulación".
    7.  Llama a `self.change_scheduler_sim()` para asegurar que la columna de prioridad se muestre/oculte correctamente según el algoritmo elegido.
    8.  Ajusta dinámicamente la altura del `tk.Canvas` de parámetros.
    9.  Almacena los `selected_files` en `self.selected_files_for_processing` para enviarlos al servidor más tarde.

#### 17. `clear_parameter_input_ui(self)`

*   **Propósito:** Eliminar todos los `ttk.Entry` del área de entrada de parámetros.

### E. Simulación Visual de Scheduling

#### 18. `change_scheduler_sim(self, event=None)`

*   **Propósito:** Actualizar el algoritmo de scheduling que se usará en la simulación visual cuando el usuario selecciona uno en el `ttk.Combobox`.
*   **Funcionamiento:**
    1.  Obtiene el nombre del algoritmo seleccionado.
    2.  Instancia la clase de scheduler correspondiente de `AVAILABLE_SCHEDULERS` (ej., `SchedulerFCFS()`, `SchedulerRR(quantum=...)`, `SchedulerPriorityNP()`).
    3.  Actualiza `self.scheduler_sim`.
    4.  Controla la visibilidad de la etiqueta y los campos de entrada para "Prioridad" y "Quantum" en la UI de parámetros, dependiendo del algoritmo seleccionado.
    5.  Actualiza la barra de estado.

#### 19. `start_simulation_visual(self)`

*   **Propósito:** Iniciar o pausar la simulación visual de scheduling.
*   **Funcionamiento:**
    1.  Si la simulación no está corriendo:
        *   Limpia el estado de la simulación anterior (colas de procesos, tabla, Gantt).
        *   Recopila los parámetros (Arrival, Burst, Priority) de los `ttk.Entry` que el usuario ingresó.
        *   Crea objetos `Process` (de `process.py`) con estos parámetros y los añade a `self.processes_to_simulate`.
        *   Inserta las filas iniciales en la tabla `self.proc_tree_sim`.
        *   Valida la entrada (ej., ráfaga positiva).
        *   Establece `self.simulation_running_sim = True`.
        *   Actualiza el botón a "Pausar Sim. Visual".
        *   Llama a `self.simulation_step_visual()` para iniciar el primer "tick".
        *   **Envía `PROCESS_FILES` al servidor:** Una vez que la simulación visual comienza, envía los archivos que el usuario seleccionó para su simulación al servidor, pidiéndole que los procese realmente.
    2.  Si la simulación ya está corriendo (se presiona "Pausar"):
        *   Establece `self.simulation_running_sim = False` y actualiza el botón.

#### 20. `simulation_step_visual(self)` (El corazón de la simulación visual)

*   **Propósito:** Ejecutar un solo paso (tick) de la simulación de scheduling. Se llama repetidamente usando `self.root.after()`.
*   **Funcionamiento:**
    1.  Incrementa `self.simulation_time_sim`.
    2.  **Llegadas:** Mueve procesos de `self.processes_to_simulate` a `self.ready_queue_sim` si su `arrival_time` es menor o igual al `current_time`.
    3.  **Finalizaciones:** Identifica procesos en `self.running_processes_sim` que han terminado (`remaining_burst_time <= 0`) y llama a `self.handle_process_completion_sim()` para ellos.
    4.  **Scheduling:**
        *   Calcula `available_threads_sim` (basado en `self.num_workers_for_sim_display`).
        *   Si el algoritmo es no-preemptivo (FCFS, SJF, HRRN, Priority_NP) y no hay procesos corriendo, se asegura de que el tiempo avance al `arrival_time` del siguiente proceso si la cola de listos está vacía.
        *   Llama a `self.scheduler_sim.schedule()` para seleccionar el siguiente proceso(s) de la `self.ready_queue_sim`. El scheduler es responsable de ordenar la cola y sacar el proceso seleccionado.
        *   Mueve los procesos seleccionados a `self.running_processes_sim` y actualiza su estado.
    5.  **Ejecución Simulada y Manejo de RR:**
        *   Para cada proceso en `self.running_processes_sim`:
            *   Decrementa `proc.remaining_burst_time`.
            *   Actualiza la tabla de procesos.
            *   Para Round Robin, gestiona el `ticks_in_current_burst` y mueve el proceso de vuelta a `self.ready_queue_sim` si su quantum expira y no ha terminado.
    6.  **Actualización de Gantt:** Llama a `self.update_gantt_display_sim()`.
    7.  **Comprobación de Fin:** Si todas las colas de procesos están vacías, la simulación termina. Se actualiza la GUI y se calculan los promedios.
    8.  De lo contrario, se programa la siguiente llamada a `simulation_step_visual()` usando `self.root.after()`.

#### 21. `handle_process_completion_sim(self, process: Process, completion_time: int)`

*   **Propósito:** Gestionar la finalización de un proceso en la simulación visual.
*   **Funcionamiento:**
    1.  Actualiza el estado del `process` a "Terminated".
    2.  Calcula las métricas de rendimiento: `completion_time`, `turnaround_time`, `waiting_time`.
    3.  Calcula y almacena las **fórmulas** para Turnaround y Waiting Time (`turnaround_formula`, `waiting_formula`).
    4.  Añade el proceso a `self.completed_processes_sim`.
    5.  Actualiza la fila correspondiente en `self.proc_tree_sim` con los tiempos y fórmulas finales.

#### 22. `update_process_table_sim(self, pid_sim: int, updates: dict)`

*   **Propósito:** Actualizar una fila específica en la tabla de procesos simulados (`self.proc_tree_sim`).
*   **Funcionamiento:** Busca el `item_id` del proceso por su `pid_sim`. Si lo encuentra, actualiza las columnas especificadas en el diccionario `updates`. Si no existe, lo inserta (aunque esto no debería pasar si los procesos se añaden al inicio).

#### 23. `update_gantt_display_sim(self, time_tick: int, running_pids_with_threads: list)`

*   **Propósito:** Dibujar un "tick" de la simulación en el diagrama de Gantt (`self.gantt_canvas`).
*   **Funcionamiento:**
    1.  En el `time_tick == 0`, inicializa el canvas (lo limpia, dibuja etiquetas de CPU/Thread).
    2.  Dibuja líneas verticales para cada unidad de tiempo.
    3.  Para cada proceso en `running_pids_with_threads`:
        *   Asigna un color consistente al proceso (si no tiene uno ya) de una paleta predefinida.
        *   Calcula las coordenadas (x1, y1, x2, y2) para un rectángulo que representa la ejecución del proceso en ese tick y en la "fila" de su CPU/Thread simulado.
        *   Dibuja el rectángulo (`self.gantt_canvas.create_rectangle()`) y el texto del PID (`self.gantt_canvas.create_text()`).
    4.  Actualiza el `scrollregion` del canvas.
    5.  Implementa auto-scroll horizontal si la simulación se extiende mucho.
    6.  Añade una leyenda de colores al Gantt después de unos pocos ticks.

#### 24. `calculate_and_display_averages_sim(self)`

*   **Propósito:** Calcular el Turnaround Time Promedio y el Waiting Time Promedio de los procesos simulados que han completado su ejecución.
*   **Funcionamiento:** Itera sobre `self.completed_processes_sim`, suma los tiempos y los divide por el número de procesos completados. Actualiza las etiquetas en la GUI.

### F. Resultados del Servidor y Guardado de CSV

#### 25. `display_server_results(self)`

*   **Propósito:** Mostrar los resultados del procesamiento real de archivos (recibidos del servidor) en el `ttk.Treeview` de la pestaña "Resultados".
*   **Funcionamiento:**
    1.  Limpia la tabla `self.results_tree`.
    2.  Itera sobre `self.server_results_for_csv` (la lista de diccionarios de resultados del servidor).
    3.  Para cada resultado, extrae los datos relevantes (PID del servidor, nombre de archivo, nombres, lugares, fechas, conteo de palabras, estado, error).
    4.  Formatea los datos (ej., uniendo listas con comas, truncando si son muy largos).
    5.  Inserta una nueva fila en `self.results_tree` con estos valores.
    6.  Actualiza la barra de estado.

#### 26. `save_results_to_csv(self)`

*   **Propósito:** Guardar los resultados del procesamiento real (recibidos del servidor) en un archivo CSV local.
*   **Funcionamiento:**
    1.  Abre `self.output_csv_path` en modo escritura (`'w'`).
    2.  Crea un `csv.writer`.
    3.  Escribe `self.csv_headers` como la primera fila.
    4.  Itera sobre `self.server_results_for_csv`. Para cada resultado:
        *   Extrae los datos relevantes, similar a `display_server_results`, pero los une con un delimitador (`|`) para el CSV.
        *   Escribe la fila en el archivo CSV.
    5.  Muestra un mensaje de éxito o error al usuario.

### G. Cierre de la Aplicación

#### 27. `on_closing(self)`

*   **Propósito:** Manejar el evento cuando el usuario intenta cerrar la ventana principal de la aplicación.
*   **Funcionamiento:** Muestra un cuadro de diálogo de confirmación. Si el usuario confirma, intenta `self.disconnect_server()` (para cerrar la conexión limpiamente) y luego `self.root.destroy()` para cerrar la ventana.
