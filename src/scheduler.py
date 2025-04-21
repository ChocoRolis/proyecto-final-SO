# src/scheduler.py

"""
Implementa diferentes algoritmos de scheduling (planificación) de procesos.

Cada algoritmo debe poder decidir qué proceso(s) de la cola 'Ready'
deberían ejecutarse a continuación, basándose en sus propias reglas.
"""

from typing import List, Optional
# Asumiendo que process.py está en el mismo directorio (src/)
from .process import Process

# --- Clase Base (Opcional pero útil para definir interfaz) ---
class SchedulerBase:
    """Clase base abstracta para los schedulers (opcional)."""
    def schedule(self, ready_queue: List[Process], current_time: int, running_processes: List[Process], available_threads: int) -> Optional[Process]:
        """
        Selecciona el siguiente proceso a ejecutar desde la cola Ready.

        Args:
            ready_queue (List[Process]): La lista de procesos en estado Ready.
                                         IMPORTANTE: Esta lista PUEDE ser modificada por el método
                                         (ej. si el scheduler saca el proceso seleccionado).
            current_time (int): El tiempo actual de la simulación.
            running_processes (List[Process]): Lista de procesos actualmente en ejecución.
            available_threads (int): Número de 'CPUs' o 'threads' simulados que están libres.

        Returns:
            Optional[Process]: El proceso seleccionado para ejecutar, o None si no hay
                               ninguno apropiado o la cola está vacía.
                               Nota: Devuelve solo UN proceso. El bucle principal llamará
                               de nuevo si hay más threads libres.
        """
        raise NotImplementedError("El método 'schedule' debe ser implementado por las subclases.")

    def __str__(self):
        return self.__class__.__name__ # Devuelve el nombre de la clase como representación

# --- Implementaciones Específicas de Algoritmos ---

class SchedulerFCFS(SchedulerBase):
    """Algoritmo de Scheduling First-Come, First-Served (FCFS)."""
    def schedule(self, ready_queue: List[Process], current_time: int, running_processes: List[Process], available_threads: int) -> Optional[Process]:
        """
        Selecciona el proceso que llegó primero a la cola Ready.

        Args:
            ready_queue: Lista de procesos Ready. Se modificará si se selecciona un proceso.
            current_time: Tiempo actual (no usado directamente por FCFS simple).
            running_processes: Procesos en ejecución (no usado por FCFS simple).
            available_threads: Threads libres (implícitamente > 0 si se llama a este método).

        Returns:
            El proceso con el menor `arrival_time` en la `ready_queue`, o None si está vacía.
        """
        if not ready_queue:
            return None

        # Encuentra el proceso con el menor tiempo de llegada
        # Si hay empates, se podría desempatar por PID, pero FCFS puro no lo requiere.
        # Python min() es estable, así que si ya estaban ordenados por llegada, mantendrá el orden relativo.
        # O podemos ordenar explícitamente para asegurarnos:
        ready_queue.sort(key=lambda p: p.arrival_time)

        # Seleccionar y quitar el primero de la cola
        process_to_run = ready_queue.pop(0)
        return process_to_run

class SchedulerSJF(SchedulerBase):
    """
    Algoritmo de Scheduling Shortest Job First (SJF) - Versión No Preemptiva.
    (Shortest Remaining Time First - SRTF - sería la versión preemptiva).
    """
    def schedule(self, ready_queue: List[Process], current_time: int, running_processes: List[Process], available_threads: int) -> Optional[Process]:
        """
        Selecciona el proceso en la cola Ready con el menor `burst_time` total.

        Args:
            ready_queue: Lista de procesos Ready. Se modificará si se selecciona un proceso.
            current_time: Tiempo actual (no usado por SJF No Preemptivo).
            running_processes: Procesos en ejecución (no usado por SJF No Preemptivo).
            available_threads: Threads libres.

        Returns:
            El proceso con el menor `burst_time` en la `ready_queue`, o None si está vacía.
        """
        if not ready_queue:
            return None

        # TODO: Implementar la lógica de SJF No Preemptivo
        # 1. Encontrar el proceso en ready_queue con el menor `burst_time`.
        #    - Puedes usar `min(ready_queue, key=lambda p: p.burst_time)`
        # 2. Quitar ese proceso de la `ready_queue`.
        # 3. Devolver el proceso seleccionado.

        # Placeholder:
        # best_process = min(ready_queue, key=lambda p: p.burst_time)
        # ready_queue.remove(best_process)
        # return best_process

        print("SchedulerSJF: Método 'schedule' no implementado todavía.") # Placeholder
        # Temporalmente, devolvemos el primero para evitar errores
        if ready_queue:
            return ready_queue.pop(0)
        return None


class SchedulerRR(SchedulerBase):
    """
    Algoritmo de Scheduling Round Robin (RR).
    Requiere un Quantum (timeslice).
    """
    def __init__(self, quantum: int = 2):
        """
        Inicializa el scheduler Round Robin.

        Args:
            quantum (int): La duración del timeslice (ráfaga de tiempo) asignada a cada proceso.
        """
        if quantum <= 0:
            raise ValueError("Quantum debe ser un entero positivo.")
        self.quantum = quantum
        # Nota: El manejo del temporizador del quantum y mover procesos de Running
        # de vuelta a Ready generalmente se hace en el bucle principal de la simulación,
        # no dentro del método schedule directamente.

    def schedule(self, ready_queue: List[Process], current_time: int, running_processes: List[Process], available_threads: int) -> Optional[Process]:
        """
        Selecciona el siguiente proceso de la cola Ready (tratada como FIFO).

        Args:
            ready_queue: Lista de procesos Ready. Se asume que los procesos que
                         expiraron su quantum o llegaron nuevos se añaden al final.
                         Se modificará si se selecciona un proceso.
            current_time: Tiempo actual.
            running_processes: Procesos en ejecución.
            available_threads: Threads libres.

        Returns:
            El primer proceso en la `ready_queue`, o None si está vacía.
        """
        if not ready_queue:
            return None

        # TODO: Implementar la lógica de RR
        # 1. Simplemente toma el primer proceso de la cola (FIFO).
        # 2. Quita ese proceso de la `ready_queue`.
        # 3. Devuelve el proceso seleccionado.
        #    (El bucle principal se encargará de limitar su tiempo de ejecución al quantum
        #     y devolverlo a la cola si no ha terminado).

        # Placeholder:
        # process_to_run = ready_queue.pop(0)
        # return process_to_run

        print("SchedulerRR: Método 'schedule' no implementado todavía.") # Placeholder
        # Temporalmente, devolvemos el primero para evitar errores
        if ready_queue:
             return ready_queue.pop(0)
        return None

    def __str__(self):
        return f"{self.__class__.__name__}(Quantum={self.quantum})"

# --- Diccionario para acceder fácilmente a los schedulers por nombre ---
AVAILABLE_SCHEDULERS = {
    "FCFS": SchedulerFCFS,
    "SJF": SchedulerSJF,
    # "SRTF": SchedulerSRTF, # Si implementas preemptive SJF
    "RR": SchedulerRR,
    # Añade aquí otros algoritmos que implementes
}

if __name__ == '__main__':
    # Ejemplo de cómo usar las clases de Scheduler (para pruebas rápidas)
    p1 = Process(pid=1, filename="doc1.txt", arrival_time=0, burst_time=5)
    p2 = Process(pid=2, filename="report.txt", arrival_time=2, burst_time=3)
    p3 = Process(pid=3, filename="data.txt", arrival_time=1, burst_time=4)

    ready_processes = [p1, p3, p2] # Llegan en orden 0, 1, 2

    print("--- Probando FCFS ---")
    fcfs_scheduler = SchedulerFCFS()
    print(f"Usando: {fcfs_scheduler}")
    ready_copy_fcfs = list(ready_processes) # Trabajar con una copia
    next_proc = fcfs_scheduler.schedule(ready_copy_fcfs, 0, [], 1)
    print(f"FCFS seleccionó: {next_proc}") # Debería ser P1 (arrival 0)
    next_proc = fcfs_scheduler.schedule(ready_copy_fcfs, 1, [], 1)
    print(f"FCFS seleccionó: {next_proc}") # Debería ser P3 (arrival 1)
    next_proc = fcfs_scheduler.schedule(ready_copy_fcfs, 2, [], 1)
    print(f"FCFS seleccionó: {next_proc}") # Debería ser P2 (arrival 2)
    print(f"Cola restante: {ready_copy_fcfs}")

    print("\n--- Probando SJF (Placeholder) ---")
    sjf_scheduler = SchedulerSJF()
    print(f"Usando: {sjf_scheduler}")
    ready_copy_sjf = list(ready_processes)
    next_proc = sjf_scheduler.schedule(ready_copy_sjf, 0, [], 1)
    print(f"SJF (placeholder) seleccionó: {next_proc}") # Placeholder devuelve el primero
    # Cuando esté implementado, debería seleccionar P2 (burst 3)
    print(f"Cola restante: {ready_copy_sjf}")


    print("\n--- Probando RR (Placeholder) ---")
    rr_scheduler = SchedulerRR(quantum=2)
    print(f"Usando: {rr_scheduler}")
    ready_copy_rr = list(ready_processes)
    next_proc = rr_scheduler.schedule(ready_copy_rr, 0, [], 1)
    print(f"RR (placeholder) seleccionó: {next_proc}") # Placeholder devuelve el primero (P1)
    # La lógica de RR real toma el primero de la cola
    print(f"Cola restante: {ready_copy_rr}")
