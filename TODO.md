# Lista de Tareas Pendientes 

> **ESTA LISTA NO ES EXACTA. Aun estoy haciendo la oficial.**

Aqui se muestran las funcionalidades que faltan, los arreglos de bugs y las mejoras que aún deben implementarse o considerarse para este proyecto.

## Lo principal

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

-   [ ] **Regex**
    -   [ ] Definir y codificar los patrones Regex específicos para extraer los "datos o columnas a extraer de archivos .txt" según las instrucciones exactas de la tarea.
    -   [ ] Asegurar que los datos extraídos se mapean correctamente a las columnas del CSV.
    -   [ ] Actualizar `client_gui.py` para usar estos patrones específicos en `process_text_file_thread`.

-   [ ] **GUI**
    -   [ ] Mejorar la visualización Gantt:
        -   [ ] Usar un `tkinter.Canvas` para dibujar barras que representen la ejecución de procesos en el tiempo para cada thread simulado.
        -   [ ] Mostrar PID y tiempo de ejecución dentro de las barras.
        -   [ ] Mejorar el auto-scroll o añadir scrollbars.
    -   [ ] Mejorar la "Tabla de Procesos" (`ttk.Treeview`):
        -   [ ] Asegurar que las columnas se redimensionen o permitan desplazamiento horizontal si el contenido es largo.
        -   [ ] Considerar añadir colores para los estados del proceso.
    -   [ ] Mejorar la "Vista Previa CSV":
        -   [ ] Posiblemente usar otro `ttk.Treeview` para mostrar el CSV como una tabla estructurada en lugar de texto plano.

## Tareas secundarias

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
    -   [ ] Documentar jos patrones Regex utilizados.
