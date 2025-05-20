# src/process.py


"""
Define la estructura de datos para representar un proceso o tarea
dentro de la simulación de scheduling.
"""

class Process:
    """
    Representa una única tarea (generalmente asociada a un archivo .txt)
    que será gestionada por el planificador (scheduler).
    """
    def __init__(self, pid: int, filename: str, arrival_time: int, burst_time: int, priority: int = 0):
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

        # --- Atributos para la simulación y métricas ---
        self.remaining_burst_time = burst_time # Tiempo de CPU que aún falta por ejecutar.
        self.priority = priority      # Prioridad del proceso (si se usa un algoritmo basado en prioridades).
        self.start_time = -1          # Tiempo en que el proceso comienza a ejecutarse por primera vez. -1 si aún no ha empezado.
        self.completion_time = -1     # Tiempo en que el proceso termina su ejecución. -1 si no ha terminado.
        self.waiting_time = 0         # Tiempo total que el proceso pasa en la cola Ready esperando CPU.
        self.turnaround_time = 0      # Tiempo total desde la llegada hasta la finalización (Completion - Arrival).
        self.state = "New"            # Estado actual del proceso: New, Ready, Running, Terminated.
        self.turnaround_formula=""    # Fórmula para calcular el tiempo de turnaround (si se necesita).
        self.waiting_formula=""       # Fórmula para calcular el tiempo de espera (si se necesita).


        # --- Atributos adicionales (opcionales) ---
        # self.priority = 0           # Para algoritmos basados en prioridad.
        # self.io_burst_time = 0      # Si se simulara I/O.
        # self.memory_required = 0    # Si se simulara gestión de memoria.

    def __str__(self):
        """Representación simple en string del proceso."""
        return (f"PID: {self.pid}, File: {self.filename}, Arrival: {self.arrival_time}, "
                f"Burst: {self.burst_time}, Remaining: {self.remaining_burst_time}, State: {self.state}")

    def __repr__(self):
        """Representación más detallada, útil para debugging."""
        return (f"Process(pid={self.pid}, filename='{self.filename}', arrival_time={self.arrival_time}, "
                f"burst_time={self.burst_time}, remaining_burst_time={self.remaining_burst_time}, "
                f"start_time={self.start_time}, completion_time={self.completion_time}, "
                f"waiting_time={self.waiting_time}, turnaround_time={self.turnaround_time}, state='{self.state}')")

# --- Puedes añadir funciones de utilidad relacionadas con procesos aquí si es necesario ---
# Ej: def calculate_metrics(process): ... (aunque es más común hacerlo en el bucle principal)

if __name__ == '__main__':
    # Ejemplo de cómo crear y usar la clase Process (para pruebas rápidas)
    p1 = Process(pid=1, filename="doc1.txt", arrival_time=0, burst_time=5)
    p2 = Process(pid=2, filename="report.txt", arrival_time=2, burst_time=3)

    print("Proceso 1:", p1)
    print("Proceso 2:", p2)
    print("Representación detallada P1:", repr(p1))

    # Simulación simple (manual)
    p1.state = "Ready"
    # ... más lógica de simulación ...
