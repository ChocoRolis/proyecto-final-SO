# Documentación Detallada de la Clase `Process` (`src/process.py`)

El archivo `process.py` es un módulo simple pero fundamental en nuestro sistema. Define la estructura de datos que representa una "tarea" o "proceso" en la simulación de scheduling.

## Propósito General

La clase `Process` encapsula toda la información necesaria para simular la ejecución de una tarea en un sistema operativo. Cada instancia de `Process` representa un archivo de texto que el cliente simulará procesar.

## Estructura de la Clase `Process`

### `class Process:`

```python
class Process:
    """
    Representa una única tarea (generalmente asociada a un archivo .txt)
    que será gestionada por el planificador (scheduler).
    """
    # ... (métodos y atributos) ...
```

*   **Propósito:** Define el molde para crear objetos que representen cada tarea en nuestra simulación.

### `__init__(self, pid: int, filename: str, arrival_time: int, burst_time: int, priority: int = 0)`

```python
    def __init__(
        self,
        pid: int,
        filename: str,
        arrival_time: int,
        burst_time: int,
        priority: int = 0,
    ):
        """
        Inicializa un nuevo proceso.

        Args:
            pid (int): Identificador único del proceso.
            filename (str): Nombre del archivo .txt asociado a esta tarea.
            arrival_time (int): Tiempo de llegada simulado del proceso a la cola Ready.
            burst_time (int): Tiempo total de CPU simulado requerido por el proceso.
            priority (int): Prioridad del proceso. (Menor número = mayor prioridad).
        """
        # ... (inicialización de atributos) ...
```

*   **Propósito:** Este es el constructor de la clase. Se llama automáticamente cada vez que creas un nuevo objeto `Process`.
*   **Argumentos:**
    *   `pid` (int): Un identificador único para este proceso dentro de la simulación del cliente. No es el PID real del sistema operativo, sino un ID simbólico para la GUI.
    *   `filename` (str): El nombre del archivo de texto al que está asociada esta tarea.
    *   `arrival_time` (int): El momento (tick de tiempo simulado) en que este proceso llega y está listo para ser planificado.
    *   `burst_time` (int): El tiempo total de CPU (en ticks simulados) que este proceso necesita para completarse.
    *   `priority` (int, opcional, por defecto 0): Un valor numérico que indica la prioridad del proceso. Se usa en algoritmos de planificación basados en prioridad (ej., `SchedulerPriorityNP`). Un número menor generalmente indica una prioridad más alta.

### Atributos de Instancia

Una vez que un objeto `Process` es creado, tiene los siguientes atributos que almacenan su estado y métricas durante la simulación:

*   **`pid` (int):** El ID único del proceso.
*   **`filename` (str):** El nombre del archivo asociado.
*   **`arrival_time` (int):** Tiempo de llegada.
*   **`burst_time` (int):** Tiempo total de CPU requerido.
*   **`priority` (int):** Prioridad del proceso.

*   **`remaining_burst_time` (int):** El tiempo de CPU que le queda al proceso por ejecutar. Se inicializa con `burst_time` y se decrementa a medida que el proceso se ejecuta.
*   **`start_time` (int):** El momento (tick) en que el proceso comenzó a ejecutarse por primera vez. Se inicializa en -1 y se actualiza cuando el proceso pasa a estado "Running" por primera vez.
*   **`completion_time` (int):** El momento (tick) en que el proceso termina su ejecución. Se inicializa en -1 y se actualiza cuando el proceso pasa a estado "Terminated".
*   **`waiting_time` (int):** El tiempo total que el proceso ha pasado en la cola "Ready" esperando por la CPU.
*   **`turnaround_time` (int):** El tiempo total desde que el proceso llegó hasta que completó su ejecución (`completion_time - arrival_time`).
*   **`state` (str):** El estado actual del proceso en la simulación. Puede ser:
    *   `"New"`: Recién creado, esperando su `arrival_time`.
    *   `"Ready"`: Ha llegado y está esperando en la cola para ser ejecutado.
    *   `"Running"`: Actualmente ejecutándose en una CPU simulada.
    *   `"Terminated"`: Ha completado su ejecución.
*   **`turnaround_formula` (str):** Una cadena de texto que muestra la fórmula de cálculo del tiempo de turnaround (ej., "10 - 2 = 8").
*   **`waiting_formula` (str):** Una cadena de texto que muestra la fórmula de cálculo del tiempo de espera (ej., "8 - 5 = 3").
*   **`response_ratio` (float):** Atributo específico para el algoritmo HRRN (High Response Ratio Next). Almacena el ratio de respuesta calculado para el proceso.

### `__str__(self)`

```python
    def __str__(self):
        """Representación simple en string del proceso."""
        # ...
```

*   **Propósito:** Define cómo se ve el objeto `Process` cuando lo imprimes directamente (ej., `print(mi_proceso)`). Proporciona un resumen conciso.

### `__repr__(self)`

```python
    def __repr__(self):
        """Representación más detallada, útil para debugging."""
        # ...
```

*   **Propósito:** Define la representación "oficial" del objeto, útil para depuración (ej., cuando el objeto aparece en una lista o en una salida de depuración). Proporciona una vista más completa de todos sus atributos.

## Uso en la Simulación

Los objetos `Process` son el corazón de la simulación en `client_gui.py`. Son creados por el usuario (a partir de los archivos que el servidor asigna y los parámetros manuales), se mueven entre diferentes listas (`processes_to_simulate`, `ready_queue_sim`, `running_processes_sim`, `completed_processes_sim`) a medida que avanza la simulación, y sus atributos se actualizan en cada "tick" de tiempo simulado.
