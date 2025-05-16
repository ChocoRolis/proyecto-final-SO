# Lista de Tareas Pendientes y Mejoras (Actualizada)


## Principales 

-   [ ] **Servidor: Implementar Procesamiento con Forks Reales**
    -   [ ] En `src/server.py`, modificar `manage_client_batch_processing` para usar `concurrent.futures.ProcessPoolExecutor` cuando `config['mode'] == 'forks'`.
    -   [ ] Asegurar que `process_single_file_wrapper` y los datos que maneja sean "pickleables" para que puedan pasarse entre procesos. (Las funciones simples y tipos de datos estándar suelen serlo).
    -   [ ] Probar y depurar el rendimiento y la estabilidad con múltiples procesos.

-   [ ] **Cliente: Implementar Schedulers de Prioridad (Ejemplo)**
    *   Objetivo: Añadir al menos un algoritmo de scheduling basado en prioridad (ej. Prioridad No Preemptiva).
    *   **Pasos:**
        1.  **`src/process.py`:** Añadir un atributo `priority` a la clase `Process` y a su constructor.
        2.  **`src/scheduler.py`:**
            *   Crear una nueva clase `SchedulerPriorityNP` (o similar).
            *   Implementar el método `schedule` para seleccionar el proceso con la mayor prioridad (menor número) de la `ready_queue`. Considerar el tiempo de llegada para desempates.
            *   Añadir la nueva clase a `AVAILABLE_SCHEDULERS`.
        3.  **`src/client_gui.py`:**
            *   Añadir la opción "Priority_NP" al `ttk.Combobox` de algoritmos.
            *   En `change_scheduler_sim`, manejar la selección de "Priority_NP", instanciar el scheduler y activar la lógica para mostrar la columna/entrada de "Prioridad".
            *   En `setup_parameter_input_ui`, asegurar que la cabecera y las `ttk.Entry` para "Prioridad" se muestren/oculten correctamente.
            *   En `start_simulation_visual`, leer el valor de prioridad ingresado por el usuario y pasarlo al constructor de `Process`. Actualizar la inserción en `self.proc_tree_sim`.

-   [ ] **Cliente: Mejorar Visualización Gantt con `tkinter.Canvas`**
    *   Objetivo: Reemplazar el Gantt basado en texto por una representación gráfica con barras en un `tk.Canvas`.
    *   **Pasos (en `src/client_gui.py`):**
        1.  **`_create_widgets`:** Reemplazar `self.gantt_text_sim` (ScrolledText) por un `tk.Canvas` (`self.gantt_canvas`) con scrollbars horizontal y vertical.
        2.  **`update_gantt_display_sim`:**
            *   Definir dimensiones (ancho por unidad de tiempo, alto de barra de thread).
            *   En cada tick, para cada proceso en ejecución, dibujar un `self.gantt_canvas.create_rectangle(...)` con un color distintivo y un `self.gantt_canvas.create_text(...)` para el PID.
            *   Manejar el `scrollregion` del canvas para que los scrollbars funcionen a medida que el diagrama crece.
        3.  **`start_simulation_visual` (o donde se reinicia la simulación):** Limpiar el canvas antes de una nueva simulación (`self.gantt_canvas.delete("all")`).
        4.  (Opcional) Crear una función `get_process_color(pid)` para asignar colores a las barras de los procesos.
        5.  (Opcional) Dibujar ejes o "calles" para los threads al inicio de la simulación.

## Secundarias

-   [ ] **Servidor: Manejo Más Fino del `processing_lock`:** Considerar si el `processing_lock` podría ser por evento en lugar de global, para permitir el procesamiento paralelo de diferentes eventos si los recursos lo permiten (esto aumentaría la complejidad).
-   [ ] **Servidor: Robustez en Desconexiones:** Revisar y mejorar el manejo de clientes que se desconectan abruptamente, especialmente si están en medio de una asignación de trigger o en la `client_batch_processing_queue`.
-   [ ] **Cliente: Validación de Entrada de Parámetros:** Mejorar la validación de los campos de Arrival, Burst, Priority (ej. asegurar que sean numéricos, rangos válidos).

## Tareas completadas

-   [X] Servidor: Implementar procesamiento con Threads.
-   [X] Servidor: División de archivos asignados entre workers del cliente.
-   [X] Servidor: División de archivos del evento entre clientes suscritos.
-   [X] Servidor y Cliente: Protocolo de comunicación actualizado.
-   [X] Cliente: Simulación de scheduling confinada al cliente.
-   [X] Cliente: Selección de archivos para simulación con checkboxes.
-   [X] Cliente: Entrada manual de parámetros de simulación (Arrival, Burst).
-   [X] Servidor: Comando `help` y mejora del problema del prompt (parcial).
-   [X] Cliente: Scrollbar para UI de parámetros.
-   [X] General: Legibilidad del código (longitud de línea, espaciado).
