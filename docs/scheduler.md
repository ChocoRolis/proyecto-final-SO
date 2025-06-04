# Documentación Detallada de los Algoritmos de Scheduling (`src/scheduler.py`)

El archivo `scheduler.py` es un módulo fundamental en la aplicación cliente. Contiene las implementaciones de varios algoritmos de planificación (scheduling) de procesos, que son utilizados por la simulación visual para decidir qué tarea debe ejecutarse a continuación.

## Propósito General

Este módulo centraliza la lógica de los diferentes algoritmos de scheduling. Cada algoritmo es una clase separada que hereda de una base común, lo que facilita la adición de nuevos algoritmos y la selección entre ellos en la interfaz gráfica del cliente.

## Clase Base: `SchedulerBase`

```python
class SchedulerBase:
    """Clase base abstracta para los schedulers."""
    # ...
```

*   **Propósito:** Define una interfaz común que todos los algoritmos de scheduling deben seguir. Esto asegura que la lógica de simulación en `client_gui.py` pueda interactuar con cualquier scheduler de la misma manera, sin importar su implementación interna.

### `schedule(self, ready_queue: List[Process], current_time: int, running_processes: List[Process], available_threads: int) -> Optional[Process]`

```python
    def schedule(
        self,
        ready_queue: List[Process],
        current_time: int,
        running_processes: List[Process],
        available_threads: int,
    ) -> Optional[Process]:
        # ...
```

*   **Propósito:** Este es el método principal que cada algoritmo debe implementar. Es el "cerebro" del planificador, decidiendo qué proceso ejecutar.
*   **Argumentos:**
    *   `ready_queue` (List[Process]): Una lista de objetos `Process` que están en estado "Ready" (listos para ejecutarse). El scheduler puede (y a menudo debe) modificar esta lista, por ejemplo, eliminando el proceso que selecciona.
    *   `current_time` (int): El tiempo actual de la simulación. Útil para algoritmos que consideran el tiempo de espera (ej., HRRN) o el tiempo de llegada.
    *   `running_processes` (List[Process]): Una lista de los procesos que actualmente se están ejecutando en las CPUs simuladas. Útil para algoritmos preemptivos que necesitan saber qué está corriendo.
    *   `available_threads` (int): El número de "CPUs" o "hilos simulados" que están libres y pueden aceptar un nuevo proceso.
*   **Retorna:** Un objeto `Process` que el scheduler ha decidido que debe ejecutarse a continuación, o `None` si la cola de listos está vacía o no hay un proceso adecuado para ejecutar en este momento.
*   **Nota:** Este método solo selecciona **un** proceso. El bucle de simulación en `client_gui.py` lo llamará repetidamente si hay múltiples "CPUs" disponibles.

## Implementaciones Específicas de Algoritmos

Cada una de estas clases hereda de `SchedulerBase` e implementa su propia lógica en el método `schedule`.

### 1. `SchedulerFCFS` (First-Come, First-Served)

```python
class SchedulerFCFS(SchedulerBase):
    """Algoritmo de Scheduling First-Come, First-Served (FCFS)."""
    # ...
```

*   **Propósito:** Planifica los procesos en el estricto orden en que llegaron a la cola de listos. Es el algoritmo más simple.
*   **Funcionamiento de `schedule`:**
    1.  Verifica si `ready_queue` está vacía.
    2.  Ordena la `ready_queue` por `arrival_time` (aunque en FCFS puro, el orden de llegada a la cola ya debería ser suficiente).
    3.  Toma y elimina el primer proceso de la cola (`ready_queue.pop(0)`).
    4.  Retorna el proceso seleccionado.
*   **Concepto:** No-preemptivo, simple, justo en el orden de llegada.

### 2. `SchedulerSJF` (Shortest Job First)

```python
class SchedulerSJF(SchedulerBase):
    """
    Algoritmo de Scheduling Shortest Job First (SJF) - No Preemptivo.
    """
    # ...
```

*   **Propósito:** Planifica el proceso con el `burst_time` (tiempo de ráfaga total) más corto entre los que están listos. Busca minimizar el tiempo de espera promedio.
*   **Funcionamiento de `schedule`:**
    1.  Verifica si `ready_queue` está vacía.
    2.  Ordena la `ready_queue` por `burst_time` (ascendente). En caso de empate en `burst_time`, desempata por `arrival_time`.
    3.  Toma y elimina el primer proceso de la cola.
    4.  Retorna el proceso seleccionado.
*   **Concepto:** No-preemptivo, óptimo para minimizar el tiempo de espera promedio (si se conoce el `burst_time` de antemano).

### 3. `SchedulerSRTF` (Shortest Remaining Time First)

```python
class SchedulerSRTF(SchedulerBase):
    """
    Algoritmo de Scheduling Shortest Remaining Time First (SRTF) - Preemptivo.
    """
    # ...
```

*   **Propósito:** Es la versión preemptiva de SJF. Planifica el proceso con el `remaining_burst_time` (tiempo de ráfaga restante) más corto. Si un nuevo proceso llega con un `remaining_burst_time` menor que el del proceso que está actualmente ejecutándose, el proceso actual es interrumpido (preempted) y el nuevo proceso toma la CPU.
*   **Funcionamiento de `schedule`:**
    1.  Verifica si `ready_queue` está vacía.
    2.  Ordena la `ready_queue` por `remaining_burst_time` (ascendente). En caso de empate, desempata por `arrival_time`.
    3.  Toma y elimina el primer proceso de la cola.
    4.  Retorna el proceso seleccionado.
*   **Concepto:** Preemptivo, busca minimizar el tiempo de espera promedio, requiere que el sistema operativo pueda cambiar de contexto rápidamente.

### 4. `SchedulerRR` (Round Robin)

```python
class SchedulerRR(SchedulerBase):
    """
    Algoritmo de Scheduling Round Robin (RR).
    """
    # ...
```

*   **Propósito:** Diseñado para sistemas de tiempo compartido. Cada proceso recibe una pequeña cantidad de tiempo de CPU (un "quantum" o "timeslice"). Si el proceso no termina dentro de su quantum, es interrumpido y movido al final de la cola de listos.
*   **Constructor `__init__(self, quantum: int = 2)`:**
    *   Toma un argumento `quantum` que define la duración del timeslice.
*   **Funcionamiento de `schedule`:**
    1.  Verifica si `ready_queue` está vacía.
    2.  Simplemente toma y elimina el primer proceso de la cola (`ready_queue.pop(0)`).
    3.  **Nota:** La lógica de preempción por quantum (interrumpir el proceso si su tiempo de ejecución en el tick actual excede el quantum y moverlo de vuelta a la cola `ready_queue_sim`) se maneja en el bucle de simulación principal (`simulation_step_visual` en `client_gui.py`), no dentro de este método `schedule`. Este método solo decide "quién va primero" de la cola.
*   **Concepto:** Preemptivo (por tiempo), equitativo, bueno para respuesta interactiva.

### 5. `SchedulerHRRN` (High Response Ratio Next)

```python
class SchedulerHRRN(SchedulerBase):
    """High Response Ratio Next (HRRN) Scheduler."""
    # ...
```

*   **Propósito:** Un algoritmo no-preemptivo que busca un equilibrio entre SJF (favoreciendo trabajos cortos) y FCFS (evitando la inanición de trabajos largos). Selecciona el proceso con el mayor "Response Ratio".
*   **Fórmula:** Response Ratio = (Tiempo de Espera + Burst Time) / Burst Time.
*   **Funcionamiento de `schedule`:**
    1.  Verifica si `ready_queue` está vacía.
    2.  Para cada proceso en `ready_queue`, calcula su `response_ratio` usando el `current_time` de la simulación y lo almacena en el atributo `process.response_ratio`.
    3.  Ordena la `ready_queue` por `response_ratio` en orden descendente (mayor ratio primero).
    4.  Toma y elimina el primer proceso de la cola.
    5.  Retorna el proceso seleccionado.
*   **Concepto:** No-preemptivo, busca reducir el tiempo de respuesta y evitar la inanición.

### 6. `SchedulerPriorityNP` (Prioridad No Preemptiva)

```python
class SchedulerPriorityNP(SchedulerBase):
    """Scheduler de Prioridad No Preemptiva (menor número = mayor prioridad)."""
    # ...
```

*   **Propósito:** Planifica los procesos basándose en un valor de prioridad asignado. Los procesos con mayor prioridad se ejecutan antes.
*   **Funcionamiento de `schedule`:**
    1.  Verifica si `ready_queue` está vacía.
    2.  Ordena la `ready_queue` primero por `priority` (ascendente, ya que un número menor significa mayor prioridad) y luego por `arrival_time` (para desempatar si las prioridades son iguales).
    3.  Toma y elimina el primer proceso de la cola.
    4.  Retorna el proceso seleccionado.
*   **Concepto:** No-preemptivo, útil para sistemas donde algunas tareas son más críticas que otras.

## Diccionario de Schedulers Disponibles

### `AVAILABLE_SCHEDULERS` (dict)

```python
AVAILABLE_SCHEDULERS = {
    "FCFS": SchedulerFCFS,
    "SJF": SchedulerSJF,
    "SRTF": SchedulerSRTF,
    "RR": SchedulerRR,
    "HRRN": SchedulerHRRN,
    "Priority_NP": SchedulerPriorityNP,
}
```

*   **Propósito:** Este diccionario facilita que `client_gui.py` pueda instanciar el scheduler correcto simplemente usando una cadena de texto (el nombre del algoritmo seleccionado por el usuario en el `ttk.Combobox`).
