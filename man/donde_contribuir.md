# Guías de Contribución y Extensión del Proyecto

Este documento proporciona orientación sobre cómo extender o modificar áreas clave del proyecto: la lógica de extracción Regex, los algoritmos de scheduling y la visualización Gantt.

## 1. Añadir/Modificar Lógica de Extracción Regex

La extracción de datos mediante expresiones regulares (Regex) se realiza exclusivamente en el **servidor**.

*   **Archivo Principal:** `src/server.py`
*   **Función Clave:** `process_single_file_wrapper(filepath_tuple)`

    ```python
    # Dentro de src/server.py
    def process_single_file_wrapper(filepath_tuple):
        filepath = filepath_tuple[0]
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # --- >>> ÁREA DE MODIFICACIÓN PARA REGEX <<< ---
            # Ejemplo existente:
            emails = re.findall(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', content
            )
            dates = re.findall(
                r'\b(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\b', content
            )
            word_count = len(content.split())

            # Para añadir más extracciones (ej. nombres propios que empiezan con mayúscula):
            # Nota: Este es un regex muy simple para nombres y puede tener falsos positivos.
            # nombres_propios = re.findall(r'\b[A-Z][a-z]+\b(?:\s+[A-Z][a-z]+)*', content)
            # --- >>> FIN ÁREA DE MODIFICACIÓN PARA REGEX <<< ---

            time.sleep(0.05) # Simular trabajo

            result_data = {
                "emails_found": emails,
                "dates_found": dates,
                "word_count": word_count,
                # "nombres_propios": nombres_propios, # Añadir al diccionario de resultados
            }
            return {"filename": filename, "data": result_data, "status": "success"}
        # ... (manejo de excepciones) ...
    ```

*   **Cómo Contribuir:**
    1.  **Define tus Patrones Regex:** Utiliza herramientas online como [Regex101](https://regex101.com/) para construir y probar tus expresiones regulares contra ejemplos de texto.
    2.  **Añade `re.findall()` o `re.search()`:** Dentro de la sección marcada, añade nuevas llamadas a `re.findall()` (para encontrar todas las coincidencias) o `re.search()` (para la primera coincidencia) con tus nuevos patrones.
    3.  **Almacena los Resultados:** Guarda los resultados de tus nuevas extracciones en variables locales.
    4.  **Actualiza `result_data`:** Añade nuevas claves y los valores extraídos correspondientes al diccionario `result_data`. Estas claves serán las que el cliente recibirá y podrá usar para mostrar o guardar en el CSV.
    5.  **Actualiza el Cliente (opcional pero recomendado):**
        *   Si quieres que estos nuevos datos se muestren en la GUI del cliente (en la sección "Resultados del Servidor") o se guarden en el CSV, necesitarás modificar `src/client_gui.py`:
            *   **Para el CSV:** Actualiza `self.csv_headers` en `ClientApp.__init__` y la lógica de construcción de `row_to_write` dentro de `save_results_to_csv` para incluir estas nuevas columnas y extraer los datos del `result_data` que el servidor envía.
            *   **Para la GUI (Vista Previa):** Puedes modificar `display_server_results` si quieres mostrar los nuevos campos directamente en el `scrolledtext`.

*   **Recursos Regex:**
    *   [Documentación oficial de `re` en Python](https://docs.python.org/3/library/re.html)
    *   [Regex101 (Herramienta Online)](https://regex101.com/)
    *   [Google's Python Regex Tutorial](https://developers.google.com/edu/python/regular-expressions)

## 2. Contribuir a Algoritmos de Scheduling y Simulación

La simulación de scheduling y la lógica de los algoritmos se encuentran en el **cliente**, ya que es una simulación visual.

*   **Archivos Principales:**
    *   `src/scheduler.py`: Donde se definen las clases de los algoritmos de scheduling (ej. `SchedulerFCFS`, `SchedulerSJF`, `SchedulerRR`).
    *   `src/client_gui.py`: Donde se controla la simulación (`simulation_step_visual`) y se interactúa con los objetos scheduler.
    *   `src/process.py`: Define la clase `Process` que usan los schedulers y la simulación.

*   **Para Añadir un Nuevo Algoritmo de Scheduling (ej. Prioridad No Preemptiva):**

    1.  **En `src/scheduler.py`:**
        *   Crea una nueva clase que herede de `SchedulerBase` (si la tienes) o simplemente implemente un método `schedule`.
            ```python
            # En src/scheduler.py
            class SchedulerPriorityNP(SchedulerBase): # NP = Non-Preemptive
                def schedule(self, ready_queue: list[Process], current_time: int,
                             running_processes: list[Process], available_threads: int) -> Process | None:
                    if not ready_queue:
                        return None
                    
                    # Ordenar por prioridad (asumiendo menor número = mayor prioridad)
                    # Luego por tiempo de llegada para desempatar si las prioridades son iguales
                    ready_queue.sort(key=lambda p: (p.priority, p.arrival_time)) # Necesitas añadir 'priority' a la clase Process
                    
                    process_to_run = ready_queue.pop(0) # Tomar el de mayor prioridad (menor número)
                    return process_to_run
            ```
        *   Añade tu nueva clase al diccionario `AVAILABLE_SCHEDULERS`:
            ```python
            AVAILABLE_SCHEDULERS = {
                "FCFS": SchedulerFCFS,
                "SJF": SchedulerSJF,
                "RR": SchedulerRR,
                "Priority_NP": SchedulerPriorityNP, # Tu nuevo scheduler
            }
            ```

    2.  **En `src/process.py` (o donde definas `Process`):**
        *   Añade el atributo `priority` a la clase `Process` y a su constructor.
            ```python
            class Process:
                def __init__(self, pid: int, filename: str, arrival_time: int, burst_time: int, priority: int = 0): # Añadir priority
                    # ...
                    self.priority = priority # Nuevo atributo
                    # ...
            ```

    3.  **En `src/client_gui.py`:**
        *   **Actualiza `self.algo_combo`:** Añade "Priority_NP" a la lista de `values` en `_create_widgets`.
        *   **Actualiza `change_scheduler_sim`:**
            *   Añade un `elif` para "Priority_NP" para instanciar `SchedulerPriorityNP()`.
            *   Controla la variable `show_priority = True` cuando este algoritmo esté seleccionado. Esto hará que la UI de parámetros muestre la columna y entrada de prioridad.
        *   **Actualiza `setup_parameter_input_ui`:**
            *   Asegúrate de que la etiqueta de cabecera "Prioridad" (`self.priority_header_label`) y las entradas de prioridad (`priority_entry_widget`) se muestren/oculten correctamente según `show_priority` (controlado por `change_scheduler_sim`).
            *   Cuando creas `tk.StringVar` para los parámetros, incluye `priority_var`.
        *   **Actualiza `start_simulation_visual`:**
            *   Cuando recoges los parámetros, obtén el valor de `priority_var`.
            *   Pasa la prioridad al constructor de `Process`.
            *   Actualiza la inserción en `self.proc_tree_sim` para incluir la columna de prioridad.
        *   **Actualiza `simulation_step_visual` (si es necesario):** Para algoritmos preemptivos (como SRTF o Prioridad Preemptiva), necesitarías lógica adicional aquí para interrumpir procesos en ejecución si llega uno de mayor prioridad. Para No Preemptivo, la selección principal ocurre cuando un "thread simulado" queda libre. El ordenamiento de `ready_queue_sim` antes de llamar a `self.scheduler_sim.schedule` puede ser suficiente para muchos algoritmos no preemptivos basados en ordenación (como SJF o Prioridad NP).

*   **Para Modificar la Lógica de Simulación General:**
    *   La función principal es `simulation_step_visual` en `src/client_gui.py`.
    *   Aquí puedes cambiar cómo se actualiza el tiempo, cómo se mueven los procesos entre colas, cómo se maneja la preempción (si la implementas), o cómo se interactúa con los objetos scheduler.

*   **Conceptos:** Algoritmos de scheduling (FCFS, SJF, RR, Prioridad), simulación de eventos discretos, preempción vs. no preempción.
    *   **Recurso sobre Scheduling:** [Operating System - Process Scheduling (TutorialsPoint)](https://www.tutorialspoint.com/operating_system/os_process_scheduling.htm)

## 3. Contribuir a la Visualización de Gantt

La visualización actual del Gantt en `src/client_gui.py` es muy simple y basada en texto (`scrolledtext.ScrolledText`). Para una visualización más rica, usar `tkinter.Canvas` es una buena opción.

*   **Archivo Principal:** `src/client_gui.py`
*   **Función Clave Actual:** `update_gantt_display_sim(self, time_tick: int, running_pids_with_threads: list)`
*   **Widget Actual:** `self.gantt_text_sim` (un `scrolledtext.ScrolledText`)

*   **Cómo Empezar con `tkinter.Canvas`:**

    1.  **En `_create_widgets`:**
        *   Reemplaza la creación de `self.gantt_text_sim` con un `tk.Canvas`.
            ```python
            # En _create_widgets, dentro del Tab de Gantt
            # self.gantt_text_sim = scrolledtext.ScrolledText(...) # Línea anterior
            self.gantt_canvas = tk.Canvas(gantt_frame_sim, bg="white", scrollregion=("0 0 1000 500")) # scrollregion inicial
            # Puedes añadir scrollbars horizontales y verticales al canvas
            h_scroll = ttk.Scrollbar(gantt_frame_sim, orient=tk.HORIZONTAL, command=self.gantt_canvas.xview)
            v_scroll = ttk.Scrollbar(gantt_frame_sim, orient=tk.VERTICAL, command=self.gantt_canvas.yview)
            self.gantt_canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
            
            self.gantt_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
            v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            ```
    2.  **En `update_gantt_display_sim`:**
        *   En lugar de añadir texto, dibujarás rectángulos en el `self.gantt_canvas`.
        *   Necesitarás definir:
            *   `time_unit_width`: Ancho en píxeles para cada unidad de tiempo en el eje X.
            *   `thread_bar_height`: Alto en píxeles para la barra de cada "thread simulado".
            *   `y_offset_per_thread`: Espaciado vertical entre las barras de los threads.
        *   Al inicio de la simulación (`start_simulation_visual`), podrías dibujar los ejes o las "calles" para cada thread.
        *   En cada `update_gantt_display_sim` (que representa un `time_tick`):
            ```python
            # Dentro de update_gantt_display_sim
            # self.gantt_canvas.delete("process_tick_" + str(time_tick -1)) # Opcional: borrar marcas anteriores si animas
            
            time_unit_width = 20  # Ejemplo: 20px por tick
            thread_bar_height = 30
            y_offset_base = 10
            y_spacing = 5

            for pid, thread_index_in_list in running_pids_with_threads:
                # thread_index_in_list es el índice 0, 1, ... de los workers simulados
                # Necesitas mapear esto al 'thread_id visual' si num_workers_for_sim_display es menor que el total de workers
                # Por ahora, asumamos que thread_index_in_list es el ID visual 0, 1...
                
                x1 = time_tick * time_unit_width
                y1 = y_offset_base + (thread_index_in_list * (thread_bar_height + y_spacing))
                x2 = (time_tick + 1) * time_unit_width
                y2 = y1 + thread_bar_height
                
                # Elige un color para el proceso (puedes tener un mapa PID -> color)
                color = self.get_process_color(pid) # Necesitarías implementar esta función

                self.gantt_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black", tags=("process_bar", "pid_" + str(pid)))
                self.gantt_canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=f"P{pid}", tags=("process_text", "pid_" + str(pid)))
            
            # Actualizar scrollregion si es necesario para que los scrollbars funcionen
            # self.gantt_canvas.config(scrollregion=self.gantt_canvas.bbox("all"))
            ```
    3.  **Limpieza:** En `start_simulation_visual` (o donde reinicies la simulación), necesitarás limpiar el canvas: `self.gantt_canvas.delete("all")` o borrar por tags específicos.
    4.  **Colores:** Implementa una función `get_process_color(pid)` que asigne un color diferente a cada PID para distinguir las barras.

*   **Conceptos:** Dibujo en Tkinter Canvas, coordenadas, creación de formas (rectángulos, texto), manejo de scrollbars.
    *   **Recurso sobre Tkinter Canvas:** [Tkinter Canvas Widget (TutorialsPoint)](https://www.tutorialspoint.com/python/tk_canvas.htm)

---
