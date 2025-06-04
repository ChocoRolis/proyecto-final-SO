"""
Implementa diferentes algoritmos de scheduling (planificación) de procesos.

Cada algoritmo debe poder decidir qué proceso(s) de la cola 'Ready'
deberían ejecutarse a continuación, basándose en sus propias reglas.
"""

from typing import List, Optional

from .process import Process


class SchedulerBase:
    """Clase base abstracta para los schedulers."""

    def schedule(
        self,
        ready_queue: List[Process],
        current_time: int,
        running_processes: List[Process],
        available_threads: int,
    ) -> Optional[Process]:
        """
        Selecciona el siguiente proceso a ejecutar desde la cola Ready.

        Args:
            ready_queue (List[Process]): La lista de procesos en estado Ready.
                                         IMPORTANTE: Esta lista será modificada por el método
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
        raise NotImplementedError(
            "El método 'schedule' debe ser implementado por las subclases."
        )

    def __str__(self):
        return self.__class__.__name__


# --- Implementaciones Específicas de Algoritmos ---


class SchedulerFCFS(SchedulerBase):
    """Algoritmo de Scheduling First-Come, First-Served (FCFS)."""

    def schedule(
        self,
        ready_queue: List[Process],
        current_time: int,
        running_processes: List[Process],
        available_threads: int,
    ) -> Optional[Process]:
        """
        Selecciona el proceso que llegó primero a la cola Ready.
        En caso de empate en arrival_time, el orden de llegada a la cola decide.
        """
        if not ready_queue:
            return None

        ready_queue.sort(key=lambda p: p.arrival_time)

        process_to_run = ready_queue.pop(0)
        return process_to_run


class SchedulerSJF(SchedulerBase):
    """
    Algoritmo de Scheduling Shortest Job First (SJF) - No Preemptivo.
    Selecciona el proceso con el menor burst_time total.
    En caso de empate, desempata por arrival_time.
    """

    def schedule(
        self,
        ready_queue: List[Process],
        current_time: int,
        running_processes: List[Process],
        available_threads: int,
    ) -> Optional[Process]:
        """
        Selecciona el proceso en la cola Ready con el menor `burst_time` total.
        """
        if not ready_queue:
            return None

        ready_queue.sort(key=lambda p: (p.burst_time, p.arrival_time))
        return ready_queue.pop(0)


class SchedulerSRTF(SchedulerBase):
    """
    Algoritmo de Scheduling Shortest Remaining Time First (SRTF) - Preemptivo.
    Selecciona el proceso con el menor tiempo de ráfaga restante (remaining_burst_time).
    En caso de empate, desempata por arrival_time.
    """

    def schedule(
        self,
        ready_queue: List[Process],
        current_time: int,
        running_processes: List[Process],
        available_threads: int,
    ) -> Optional[Process]:
        """
        Selecciona el proceso en la cola Ready con el menor `remaining_burst_time`.
        """
        if not ready_queue:
            return None

        ready_queue.sort(key=lambda p: (p.remaining_burst_time, p.arrival_time))
        return ready_queue.pop(0)


class SchedulerRR(SchedulerBase):
    """
    Algoritmo de Scheduling Round Robin (RR).
    Requiere un Quantum (timeslice) para la preempción por tiempo.
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

    def schedule(
        self,
        ready_queue: List[Process],
        current_time: int,
        running_processes: List[Process],
        available_threads: int,
    ) -> Optional[Process]:
        """
        Selecciona el siguiente proceso de la cola Ready (tratada como FIFO).
        """
        if not ready_queue:
            return None

        return ready_queue.pop(0)

    def __str__(self):
        return f"{self.__class__.__name__}(Quantum={self.quantum})"


class SchedulerHRRN(SchedulerBase):
    """
    High Response Ratio Next (HRRN) Scheduler.
    Selecciona el proceso con el mayor Response Ratio.
    Response Ratio = (Tiempo de Espera + Burst Time) / Burst Time.
    """

    def schedule(
        self,
        ready_queue: List[Process],
        current_time: int,
        running_processes: List[Process],
        available_threads: int,
    ) -> Optional[Process]:
        """
        Calcula el Response Ratio para cada proceso en la cola Ready
        y selecciona el proceso con el mayor ratio.
        """
        if not ready_queue:
            return None

        for process in ready_queue:
            wait_time = current_time - process.arrival_time
            # Evitar división por cero si burst_time es 0 (aunque debería ser >0)
            if process.burst_time == 0:
                process.response_ratio = float('inf')
            else:
                process.response_ratio = (wait_time + process.burst_time) / process.burst_time

        ready_queue.sort(key=lambda p: p.response_ratio, reverse=True)

        selected_process = ready_queue.pop(0)
        return selected_process

    def __str__(self):
        return "SchedulerHRRN"


class SchedulerPriorityNP(SchedulerBase):
    """
    Scheduler de Prioridad No Preemptiva.
    Selecciona el proceso con la mayor prioridad (menor número = mayor prioridad).
    En caso de empate en prioridad, desempata por arrival_time.
    """

    def schedule(
        self,
        ready_queue: List[Process],
        current_time: int,
        running_processes: List[Process],
        available_threads: int,
    ) -> Optional[Process]:
        """
        Selecciona el proceso de mayor prioridad de la cola Ready.
        """
        if not ready_queue:
            return None

        ready_queue.sort(key=lambda p: (p.priority, p.arrival_time))
        return ready_queue.pop(0)


# --- Diccionario para acceder fácilmente a los schedulers por nombre ---
AVAILABLE_SCHEDULERS = {
    "FCFS": SchedulerFCFS,
    "SJF": SchedulerSJF,
    "SRTF": SchedulerSRTF,
    "RR": SchedulerRR,
    "HRRN": SchedulerHRRN,
    "Priority_NP": SchedulerPriorityNP,
}


if __name__ == "__main__":
    # Ejemplo de cómo usar las clases de Scheduler (para pruebas rápidas)
    p1 = Process(pid=1, filename="doc1.txt", arrival_time=0, burst_time=5)
    p2 = Process(pid=2, filename="report.txt", arrival_time=2, burst_time=3)
    p3 = Process(pid=3, filename="data.txt", arrival_time=1, burst_time=4)

    ready_processes = [p1, p3, p2]

    print("--- Probando FCFS ---")
    fcfs_scheduler = SchedulerFCFS()
    print(f"Usando: {fcfs_scheduler}")
    ready_copy_fcfs = list(ready_processes)
    next_proc = fcfs_scheduler.schedule(ready_copy_fcfs, 0, [], 1)
    print(f"FCFS seleccionó: {next_proc}")
    next_proc = fcfs_scheduler.schedule(ready_copy_fcfs, 1, [], 1)
    print(f"FCFS seleccionó: {next_proc}")
    next_proc = fcfs_scheduler.schedule(ready_copy_fcfs, 2, [], 1)
    print(f"FCFS seleccionó: {next_proc}")
    print(f"Cola restante: {ready_copy_fcfs}")

    print("\n--- Probando SJF ---")
    sjf_scheduler = SchedulerSJF()
    print(f"Usando: {sjf_scheduler}")
    ready_copy_sjf = list(ready_processes)
    next_proc = sjf_scheduler.schedule(ready_copy_sjf, 0, [], 1)
    print(f"SJF seleccionó: {next_proc}")
    print(f"Cola restante: {ready_copy_sjf}")

    print("\n--- Probando SRTF ---")
    srtf_scheduler = SchedulerSRTF()
    print(f"Usando: {srtf_scheduler}")
    p4 = Process(pid=4, filename="fast.txt", arrival_time=0, burst_time=2)
    p5 = Process(pid=5, filename="slow.txt", arrival_time=0, burst_time=10)
    ready_copy_srtf = [p4, p5]
    next_proc = srtf_scheduler.schedule(ready_copy_srtf, 0, [], 1)
    print(f"SRTF seleccionó: {next_proc}")
    print(f"Cola restante: {ready_copy_srtf}")

    print("\n--- Probando RR ---")
    rr_scheduler = SchedulerRR(quantum=2)
    print(f"Usando: {rr_scheduler}")
    ready_copy_rr = list(ready_processes)
    next_proc = rr_scheduler.schedule(ready_copy_rr, 0, [], 1)
    print(f"RR seleccionó: {next_proc}")
    print(f"Cola restante: {ready_copy_rr}")

    print("\n--- Probando HRRN ---")
    hrrn_scheduler = SchedulerHRRN()
    print(f"Usando: {hrrn_scheduler}")
    p_hrrn1 = Process(pid=10, filename="A.txt", arrival_time=0, burst_time=5)
    p_hrrn2 = Process(pid=11, filename="B.txt", arrival_time=2, burst_time=3)
    p_hrrn3 = Process(pid=12, filename="C.txt", arrival_time=1, burst_time=8)
    ready_copy_hrrn = [p_hrrn1, p_hrrn2, p_hrrn3]
    # Simular en tiempo 2 para HRRN
    next_proc = hrrn_scheduler.schedule(ready_copy_hrrn, 2, [], 1)
    print(f"HRRN (t=2) seleccionó: {next_proc}")
    print(f"Cola restante: {ready_copy_hrrn}")

    print("\n--- Probando Priority_NP ---")
    priority_scheduler = SchedulerPriorityNP()
    print(f"Usando: {priority_scheduler}")
    p_prio1 = Process(pid=20, filename="HighPrio.txt", arrival_time=0, burst_time=5, priority=1)
    p_prio2 = Process(pid=21, filename="LowPrio.txt", arrival_time=0, burst_time=3, priority=2)
    p_prio3 = Process(pid=22, filename="MedPrio.txt", arrival_time=1, burst_time=8, priority=1) # Misma prioridad que P1
    ready_copy_prio = [p_prio1, p_prio2, p_prio3]
    ready_copy_prio.sort(key=lambda p: p.arrival_time) # Asegurar orden de llegada inicial
    
    next_proc = priority_scheduler.schedule(ready_copy_prio, 0, [], 1)
    print(f"Priority_NP seleccionó: {next_proc}") # Debería ser P20 (Prio 1, Arr 0)
    print(f"Cola restante: {ready_copy_prio}")

    next_proc = priority_scheduler.schedule(ready_copy_prio, 1, [], 1)
    print(f"Priority_NP seleccionó: {next_proc}") # Debería ser P22 (Prio 1, Arr 1)
    print(f"Cola restante: {ready_copy_prio}")
