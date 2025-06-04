"""
Define la estructura de datos para representar un proceso o tarea
dentro de la simulación de scheduling.
"""

class Process:
    """
    Representa una única tarea (generalmente asociada a un archivo .txt)
    que será gestionada por el planificador (scheduler).
    """

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
            priority (int): Prioridad del proceso.
        """
        self.pid = pid
        self.filename = filename
        self.arrival_time = arrival_time
        self.burst_time = burst_time

        self.remaining_burst_time = burst_time
        self.priority = priority
        self.start_time = -1
        self.completion_time = -1
        self.waiting_time = 0
        self.turnaround_time = 0
        self.state = "New"
        self.turnaround_formula = ""
        self.waiting_formula = ""
        self.response_ratio = 0.0 # Para el algoritmo HRRN


    def __str__(self):
        """Representación simple en string del proceso."""
        return (
            f"PID: {self.pid}, File: {self.filename}, Arrival: {self.arrival_time}, "
            f"Burst: {self.burst_time}, Remaining: {self.remaining_burst_time}, "
            f"State: {self.state}"
        )

    def __repr__(self):
        """Representación más detallada, útil para debugging."""
        return (
            f"Process(pid={self.pid}, filename='{self.filename}', "
            f"arrival_time={self.arrival_time}, burst_time={self.burst_time}, "
            f"remaining_burst_time={self.remaining_burst_time}, "
            f"start_time={self.start_time}, completion_time={self.completion_time}, "
            f"waiting_time={self.waiting_time}, "
            f"turnaround_time={self.turnaround_time}, state='{self.state}', "
            f"priority={self.priority}, response_ratio={self.response_ratio})"
        )


if __name__ == "__main__":
    # Ejemplo de cómo crear y usar la clase Process (para pruebas rápidas)
    p1 = Process(pid=1, filename="doc1.txt", arrival_time=0, burst_time=5)
    p2 = Process(pid=2, filename="report.txt", arrival_time=2, burst_time=3, priority=1)
    p3 = Process(pid=3, filename="data.txt", arrival_time=1, burst_time=4, priority=0)

    print("Proceso 1:", p1)
    print("Proceso 2:", p2)
    print("Proceso 3:", p3)
    print("Representación detallada P1:", repr(p1))

    p1.state = "Ready"
    print("Proceso 1 (después de cambiar estado):", p1)
