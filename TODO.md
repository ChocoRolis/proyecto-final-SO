# Lista de Tareas Pendientes y Mejoras

Este documento lista las funcionalidades planificadas, los arreglos de bugs y las mejoras que aún deben implementarse o considerarse para este proyecto. Si vas a trabajar en alguna de estas tareas, por favor, crea una rama y un Pull Request siguiendo las pautas en [`CONTRIBUTING.md`](CONTRIBUTING.md). Idealmente, añade el número de la tarea (si se convierte en una "Issue" en el repositorio) al título de tu rama y Pull Request (ej. `feat/implement-sjf-scheduler-3`).

## Funcionalidades Principales Pendientes

-   [ ] **Implementar Algoritmos de Scheduling Adicionales:**
    -   [ ] Scheduler SJF (Shortest Job First)
        -   [ ] Versión No-Preemptiva
        -   [ ] Versión Preemptiva (Shortest Remaining Time First - SRTF)
    -   [ ] Scheduler Round Robin (RR)
        -   [ ] Añadir control para el Quantum en la GUI o configuración.
    -   [ ] Integrar la selección de algoritmos en la lógica de simulación del cliente.

-   [ ] **Mejorar Simulación de Scheduling:**
    -   [ ] Ajustar la simulación para manejar correctamente la preempción (necesario para SRTF y RR).
    -   [ ] Afinar la lógica de asignación de procesos a los "threads" simulados en cada tick.
    -   [ ] Considerar posibles estados de proceso adicionales (ej. Waiting for I/O, aunque la tarea no lo pide explícitamente).

-   [ ] **Implementar Operaciones Regex Específicas:**
    -   [ ] Definir y codificar los patrones Regex específicos para extraer los "datos o columnas a extraer de archivos .txt" según las instrucciones exactas de la tarea.
    -   [ ] Asegurar que los datos extraídos se mapean correctamente a las columnas del CSV.
    -   [ ] Actualizar `client_gui.py` para usar estos patrones específicos en `process_text_file_thread`.

-   [ ] **Mejorar Visualización de la GUI:**
    -   [ ] Mejorar la visualización Gantt:
        -   [ ] Usar un `tkinter.Canvas` para dibujar barras que representen la ejecución de procesos en el tiempo para cada thread simulado.
        -   [ ] Mostrar PID y tiempo de ejecución dentro de las barras.
        -   [ ] Mejorar el auto-scroll o añadir scrollbars.
    -   [ ] Mejorar la "Tabla de Procesos" (`ttk.Treeview`):
        -   [ ] Asegurar que las columnas se redimensionen o permitan desplazamiento horizontal si el contenido es largo.
        -   [ ] Considerar añadir colores para los estados del proceso.
    -   [ ] Mejorar la "Vista Previa CSV":
        -   [ ] Posiblemente usar otro `ttk.Treeview` para mostrar el CSV como una tabla estructurada en lugar de texto plano.

## Tareas Secundarias y Mejoras

-   [ ] **Manejo de Errores:**
    -   [ ] Mejorar el manejo de errores de red (conexión perdida, etc.).
    -   [ ] Manejar errores durante la lectura/escritura de archivos.
    -   [ ] Manejar errores durante la ejecución de Regex.
    -   [ ] Proporcionar feedback más útil al usuario a través de la GUI.
-   [ ] **Configuración:**
    -   [ ] Permitir al cliente solicitar una configuración de threads/forks al servidor (si el servidor lo permite).
    -   [ ] Añadir configuración para la velocidad de simulación (`simulation_update_ms`).
-   [ ] **Usabilidad:**
    -   [ ] Añadir opción en la GUI para seleccionar el directorio de archivos `.txt`.
    -   [ ] Añadir un botón para limpiar los datos de la simulación y la tabla/CSV.
    -   [ ] Permitir al usuario guardar el archivo CSV en una ubicación específica.
-   [ ] **Documentación:**
    -   [ ] Añadir comentarios al código para explicar las partes complejas.
    -   [ ] Actualizar este `TODO.md` a medida que se completen tareas o surjan nuevas.
    -   [ ] Documentar los patrones Regex utilizados.
-   [ ] **Modularización:**
    -   [ ] Mover la lógica de los algoritmos de scheduling a `scheduler.py`.
    -   [ ] Mover la definición de la clase `Process` a `process.py`.
