# client_gui.py (Esqueleto / Pseudocódigo)
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import socket
import threading
import json
import queue
import time
import re
import csv
import os
from datetime import datetime

# --- Clases/Módulos Opcionales (podrían estar en process.py, scheduler.py) ---
class Process:
    def __init__(self, pid, filename, arrival_time, burst_time):
        self.pid = pid
        self.filename = filename
        self.arrival_time = arrival_time
        self.burst_time = burst_time
        self.remaining_burst_time = burst_time
        self.completion_time = 0
        self.turnaround_time = 0
        self.waiting_time = 0
        self.start_time = -1 # Tiempo en que empieza a ejecutarse por primera vez
        self.state = "New" # New, Ready, Running, Waiting (I/O), Terminated

# --- Implementaciones de Scheduler (simplificadas) ---
# (Idealmente en scheduler.py)
class SchedulerFCFS:
    def schedule(self, ready_queue, current_time):
        # Devuelve el proceso a ejecutar (o None si no hay)
        if ready_queue:
            # Ordena por tiempo de llegada (aunque ya deberían estar más o menos)
            ready_queue.sort(key=lambda p: p.arrival_time)
            return ready_queue[0] # Devuelve el primero que llegó
        return None

# ... otras clases de Scheduler (RR, SJF) ...

# --- Lógica Principal de la Aplicación Tkinter ---
class ClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cliente de Scheduling OS")
        self.root.geometry("1000x700")

        # --- Estado del Cliente ---
        self.client_socket = None
        self.connected = False
        self.server_addr = tk.StringVar(value="127.0.0.1")
        self.server_port = tk.StringVar(value="65432")
        self.event_name = tk.StringVar(value="data_ready")
        self.subscribed_events = set()
        self.message_queue = queue.Queue() # Para comunicación Thread -> GUI
        self.num_simulated_threads = 2 # Valor por defecto, actualizado por el servidor
        self.client_id = f"client_{os.getpid()}_{int(time.time())}" # ID único para este cliente
        self.output_csv_path = os.path.join("output", f"results_{self.client_id}.csv")
        self.csv_writer = None
        self.csv_file = None
        self.csv_lock = threading.Lock() # Para escribir en CSV de forma segura

        # --- Estado de Simulación ---
        self.processes_to_schedule = [] # Tareas añadidas por triggers
        self.ready_queue = []
        self.running_processes = [] # Procesos actualmente en las 'CPUs' simuladas
        self.completed_processes = []
        self.simulation_time = 0
        self.scheduler = SchedulerFCFS() # Scheduler por defecto
        self.selected_algorithm = tk.StringVar(value="FCFS")
        self.process_pid_counter = 0
        self.simulation_running = False
        self.simulation_update_ms = 500 # Velocidad de la simulación (ms por tick)
        self.gantt_data = [] # Lista de tuplas (pid, start, end, thread_id)

        # --- Configuración del CSV ---
        self.csv_headers = ["PID", "FileName", "ArrivalTime", "BurstTime", "CompletionTime", "TurnaroundTime", "WaitingTime", "ExtractedData1", "ExtractedData2"] # Ejemplo
        self._setup_csv()


        # --- Crear Widgets de la GUI ---
        self._create_widgets()

        # Iniciar chequeo periódico de la cola de mensajes
        self.root.after(100, self.check_message_queue)

    def _setup_csv(self):
        try:
            os.makedirs("output", exist_ok=True)
            # Abrir en modo 'a+' para añadir y leer si existe, 'w' para escribir encabezado si no
            self.csv_file = open(self.output_csv_path, 'a+', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)
            # Escribir encabezado si el archivo está vacío
            self.csv_file.seek(0, os.SEEK_END)
            if self.csv_file.tell() == 0:
                self.csv_writer.writerow(self.csv_headers)
                self.csv_file.flush() # Asegurar escritura
        except Exception as e:
             messagebox.showerror("Error CSV", f"No se pudo abrir o crear el archivo CSV: {e}")
             # Deshabilitar funcionalidad CSV?

    def _create_widgets(self):
        # Frame Conexión
        conn_frame = ttk.LabelFrame(self.root, text="Conexión Servidor")
        conn_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(conn_frame, text="IP:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(conn_frame, textvariable=self.server_addr).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(conn_frame, text="Puerto:").grid(row=0, column=2, padx=5, pady=5)
        ttk.Entry(conn_frame, textvariable=self.server_port).grid(row=0, column=3, padx=5, pady=5)
        self.connect_button = ttk.Button(conn_frame, text="Conectar", command=self.connect_server)
        self.connect_button.grid(row=0, column=4, padx=5, pady=5)
        self.disconnect_button = ttk.Button(conn_frame, text="Desconectar", command=self.disconnect_server, state=tk.DISABLED)
        self.disconnect_button.grid(row=0, column=5, padx=5, pady=5)

        # Frame Suscripción
        sub_frame = ttk.LabelFrame(self.root, text="Suscripción Eventos")
        sub_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(sub_frame, text="Evento:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(sub_frame, textvariable=self.event_name).grid(row=0, column=1, padx=5, pady=5)
        self.sub_button = ttk.Button(sub_frame, text="Suscribir", command=self.subscribe_event, state=tk.DISABLED)
        self.sub_button.grid(row=0, column=2, padx=5, pady=5)
        self.unsub_button = ttk.Button(sub_frame, text="Desuscribir", command=self.unsubscribe_event, state=tk.DISABLED)
        self.unsub_button.grid(row=0, column=3, padx=5, pady=5)
        self.subscribed_label = ttk.Label(sub_frame, text="Suscrito a: Ninguno")
        self.subscribed_label.grid(row=0, column=4, padx=10, pady=5)


        # Frame Configuración Simulación
        sim_config_frame = ttk.LabelFrame(self.root, text="Configuración Simulación")
        sim_config_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(sim_config_frame, text="Algoritmo:").grid(row=0, column=0, padx=5, pady=5)
        algo_combo = ttk.Combobox(sim_config_frame, textvariable=self.selected_algorithm,
                                  values=["FCFS", "SJF", "RR"], state="readonly") # Añadir más algos
        algo_combo.grid(row=0, column=1, padx=5, pady=5)
        algo_combo.bind("<<ComboboxSelected>>", self.change_scheduler)
        self.threads_label = ttk.Label(sim_config_frame, text=f"Threads/Forks (Servidor): {self.num_simulated_threads}")
        self.threads_label.grid(row=0, column=2, padx=10, pady=5)
        # Botón para iniciar/pausar la simulación (si es necesario control manual)
        self.start_sim_button = ttk.Button(sim_config_frame, text="Iniciar Simulación", command=self.start_simulation, state=tk.DISABLED)
        self.start_sim_button.grid(row=0, column=3, padx=5, pady=5)


        # Frame Visualización (Tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(padx=10, pady=10, fill="both", expand=True)

        # Tab: Tabla de Procesos
        proc_frame = ttk.Frame(notebook)
        notebook.add(proc_frame, text='Tabla de Procesos')
        cols = ("PID", "Archivo", "Estado", "Llegada", "Ráfaga", "Restante", "Comienzo", "Fin", "Retorno", "Espera")
        self.proc_tree = ttk.Treeview(proc_frame, columns=cols, show='headings')
        for col in cols:
            self.proc_tree.heading(col, text=col)
            self.proc_tree.column(col, width=80, anchor=tk.CENTER)
        self.proc_tree.pack(fill="both", expand=True)
        # Añadir scrollbars si es necesario

        # Tab: Visualización Gantt (Simplificada con Texto o Canvas)
        gantt_frame = ttk.Frame(notebook)
        notebook.add(gantt_frame, text='Gantt (Simulado)')
        self.gantt_text = scrolledtext.ScrolledText(gantt_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.gantt_text.pack(fill="both", expand=True, padx=5, pady=5)
        # Alternativa: Usar un Canvas para dibujar rectángulos

        # Tab: Vista Previa CSV
        csv_frame = ttk.Frame(notebook)
        notebook.add(csv_frame, text='Vista Previa CSV')
        self.csv_text = scrolledtext.ScrolledText(csv_frame, height=10, wrap=tk.NONE, state=tk.DISABLED)
        self.csv_text.pack(fill="both", expand=True, padx=5, pady=5)
        save_csv_button = ttk.Button(csv_frame, text="Guardar/Actualizar CSV", command=self.save_or_update_csv_view)
        save_csv_button.pack(pady=5)


        # Frame Métricas Promedio
        avg_frame = ttk.LabelFrame(self.root, text="Métricas Promedio")
        avg_frame.pack(padx=10, pady=5, fill="x")
        self.avg_turnaround_label = ttk.Label(avg_frame, text="Retorno Promedio: N/A")
        self.avg_turnaround_label.pack(side=tk.LEFT, padx=10)
        self.avg_waiting_label = ttk.Label(avg_frame, text="Espera Promedio: N/A")
        self.avg_waiting_label.pack(side=tk.LEFT, padx=10)
        self.sim_time_label = ttk.Label(avg_frame, text="Tiempo Simulación: 0")
        self.sim_time_label.pack(side=tk.RIGHT, padx=10)

        # Barra de Estado
        self.status_bar = ttk.Label(self.root, text="Desconectado.", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill="x")

    # --- Métodos de Conexión y Comunicación ---
    def connect_server(self):
        if self.connected:
            messagebox.showwarning("Conexión", "Ya estás conectado.")
            return

        ip = self.server_addr.get()
        port_str = self.server_port.get()
        try:
            port = int(port_str)
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((ip, port))
            self.connected = True
            self.status_bar.config(text=f"Conectado a {ip}:{port}")
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
            self.sub_button.config(state=tk.NORMAL)
            #self.unsub_button.config(state=tk.NORMAL) # Habilitar sólo si hay suscripciones
            self.start_sim_button.config(state=tk.NORMAL)


            # Iniciar hilo para escuchar al servidor
            self.receive_thread = threading.Thread(target=self.listen_to_server, daemon=True)
            self.receive_thread.start()

            # Pedir config al servidor (opcional, si no la envía al conectar)
            # self.send_message({"type": "GET_CONFIG", "payload": None})

        except ValueError:
            messagebox.showerror("Error", "Puerto inválido.")
        except socket.error as e:
            messagebox.showerror("Error de Conexión", f"No se pudo conectar: {e}")
            self.connected = False
            if self.client_socket: self.client_socket.close()
            self.client_socket = None
        except Exception as e:
            messagebox.showerror("Error", f"Error inesperado al conectar: {e}")
            self.connected = False
            if self.client_socket: self.client_socket.close()
            self.client_socket = None

    def disconnect_server(self):
        if not self.connected: return
        try:
            # Avisar al servidor (opcional, el servidor detectará la desconexión)
             # self.send_message({"type": "DISCONNECT", "payload": None}) # Necesitarías manejar esto en el server
             if self.client_socket:
                 self.client_socket.close()
        except Exception as e:
            print(f"Error al cerrar socket: {e}") # Log a consola
        finally:
            self.client_socket = None
            self.connected = False
            self.simulation_running = False # Detener simulación
            self.status_bar.config(text="Desconectado.")
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
            self.sub_button.config(state=tk.DISABLED)
            self.unsub_button.config(state=tk.DISABLED)
            self.start_sim_button.config(state=tk.DISABLED)
            self.subscribed_events.clear()
            self.subscribed_label.config(text="Suscrito a: Ninguno")
            # El hilo listener debería terminar solo al cerrarse el socket


    def send_message(self, message):
        if self.connected and self.client_socket:
            try:
                self.client_socket.sendall(json.dumps(message).encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError):
                 messagebox.showerror("Error de Red", "Conexión perdida con el servidor.")
                 self.disconnect_server() # Maneja la desconexión
            except Exception as e:
                messagebox.showerror("Error de Envío", f"No se pudo enviar mensaje: {e}")
        else:
            messagebox.showwarning("Envío", "No estás conectado.")

    def listen_to_server(self):
        while self.connected and self.client_socket:
            try:
                data = self.client_socket.recv(4096) # Buffer más grande por si acaso
                if not data:
                    # Servidor cerró la conexión o se perdió
                    if self.connected: # Evitar doble mensaje si ya nos desconectamos
                       self.message_queue.put({"type": "ERROR", "payload": "Servidor desconectado."})
                    break

                # Puede haber múltiples mensajes JSON en un solo recv
                buffer = data.decode('utf-8')
                for msg_str in buffer.split('\n'): # Asumiendo que se envían separados por newline, o usar un delimitador
                    if not msg_str.strip(): continue
                    try:
                       message = json.loads(msg_str)
                       self.message_queue.put(message)
                    except json.JSONDecodeError:
                        print(f"Error decodificando parte del mensaje: {msg_str}") # Log
                        # Podríamos intentar acumular el buffer si el JSON está partido

            except (ConnectionResetError, BrokenPipeError):
                 if self.connected:
                    self.message_queue.put({"type": "ERROR", "payload": "Conexión perdida."})
                 break
            except socket.error as e:
                 # Podría ser que cerramos el socket desde disconnect_server
                 if self.connected:
                    self.message_queue.put({"type": "ERROR", "payload": f"Error de socket: {e}"})
                 break
            except Exception as e:
                 # Otros errores inesperados
                 if self.connected:
                     self.message_queue.put({"type": "ERROR", "payload": f"Error inesperado en listener: {e}"})
                 break
        # Cuando el bucle termina (por desconexión o error), nos aseguramos que la GUI sepa
        if self.connected:
             self.message_queue.put({"type": "_THREAD_EXIT_", "payload": None})


    def check_message_queue(self):
        """Revisa la cola de mensajes del hilo listener y procesa en el hilo de la GUI."""
        try:
            while True:
                message = self.message_queue.get_nowait()
                self.handle_server_message(message)
        except queue.Empty:
            pass
        finally:
            # Volver a programar el chequeo
            self.root.after(100, self.check_message_queue)

    def handle_server_message(self, message):
        """Procesa mensajes recibidos del servidor."""
        msg_type = message.get("type")
        payload = message.get("payload")
        print(f"GUI recibió: {message}") # Debug

        if msg_type == "TRIGGER":
            event_name = payload
            self.status_bar.config(text=f"¡Trigger recibido para '{event_name}'!")
            # Cargar archivos y añadirlos como procesos a la simulación
            self.load_files_for_event(event_name)

        elif msg_type == "CONFIG":
            self.num_simulated_threads = payload.get("threads", self.num_simulated_threads)
            self.threads_label.config(text=f"Threads/Forks (Servidor): {self.num_simulated_threads}")
            self.status_bar.config(text=f"Configuración de threads recibida: {self.num_simulated_threads}")

        elif msg_type == "ACK_SUB":
            event_name = payload
            self.subscribed_events.add(event_name)
            self.update_subscribed_label()
            self.unsub_button.config(state=tk.NORMAL)
            self.status_bar.config(text=f"Suscrito a '{event_name}'.")

        elif msg_type == "ACK_UNSUB":
            event_name = payload
            self.subscribed_events.discard(event_name)
            self.update_subscribed_label()
            if not self.subscribed_events:
                self.unsub_button.config(state=tk.DISABLED)
            self.status_bar.config(text=f"Desuscrito de '{event_name}'.")

        elif msg_type == "SERVER_EXIT":
            messagebox.showinfo("Servidor", "El servidor ha cerrado la conexión.")
            self.disconnect_server()

        elif msg_type == "ERROR":
            messagebox.showerror("Error de Red", payload)
            self.disconnect_server()

        elif msg_type == "_THREAD_EXIT_":
             # El hilo listener ha terminado, probablemente por desconexión
             if self.connected: # Si no nos habíamos desconectado ya
                 messagebox.showwarning("Conexión", "Se perdió la conexión con el servidor.")
                 self.disconnect_server()

        else:
             print(f"Mensaje desconocido recibido: {message}")


    # --- Métodos de Suscripción ---
    def subscribe_event(self):
        event = self.event_name.get()
        if not event:
            messagebox.showwarning("Suscripción", "Ingresa un nombre de evento.")
            return
        if event in self.subscribed_events:
            messagebox.showinfo("Suscripción", f"Ya estás suscrito a '{event}'.")
            return
        self.send_message({"type": "SUB", "payload": event})

    def unsubscribe_event(self):
        event = self.event_name.get() # Usa el evento en el campo de texto
        if not event:
            messagebox.showwarning("Suscripción", "Ingresa un nombre de evento para desuscribir.")
            return
        if event not in self.subscribed_events:
             messagebox.showinfo("Suscripción", f"No estás suscrito a '{event}'.")
             return
        self.send_message({"type": "UNSUB", "payload": event})
        # La confirmación viene del servidor (ACK_UNSUB)

    def update_subscribed_label(self):
         if self.subscribed_events:
              self.subscribed_label.config(text=f"Suscrito a: {', '.join(self.subscribed_events)}")
         else:
              self.subscribed_label.config(text="Suscrito a: Ninguno")


    # --- Métodos de Simulación ---
    def change_scheduler(self, event=None):
        algo = self.selected_algorithm.get()
        if algo == "FCFS":
            self.scheduler = SchedulerFCFS()
        # elif algo == "SJF":
        #     self.scheduler = SchedulerSJF() # Necesitas implementarla
        # elif algo == "RR":
        #     # Necesitarás un campo para el Quantum
        #     quantum = 2 # Ejemplo, obtener de la GUI
        #     self.scheduler = SchedulerRR(quantum) # Necesitas implementarla
        else:
            messagebox.showerror("Error", f"Algoritmo {algo} no implementado.")
            self.selected_algorithm.set("FCFS") # Volver al default
            self.scheduler = SchedulerFCFS()
        self.status_bar.config(text=f"Algoritmo cambiado a {algo}")
        print(f"Usando scheduler: {self.scheduler.__class__.__name__}")

    def load_files_for_event(self, event_name):
        # Aquí decides qué archivos procesar. Ejemplo: todos los .txt en 'text_files/'
        source_dir = "text_files"
        if not os.path.isdir(source_dir):
             messagebox.showwarning("Archivos", f"El directorio '{source_dir}' no existe. Crea algunos archivos .txt ahí.")
             return

        new_processes_found = 0
        for filename in os.listdir(source_dir):
             if filename.endswith(".txt"):
                 filepath = os.path.join(source_dir, filename)
                 # Evitar añadir el mismo archivo dos veces si ya está en cola? O permitirlo?
                 # Por ahora, lo permitimos.

                 # Simular Burst Time (ejemplo: basado en tamaño de archivo)
                 try:
                     burst_estimate = max(1, os.path.getsize(filepath) // 100) # 1 tick por cada 100 bytes, mínimo 1
                 except OSError:
                     burst_estimate = 5 # Valor por defecto si no se puede leer

                 pid = self.process_pid_counter
                 self.process_pid_counter += 1
                 arrival = self.simulation_time # Llega "ahora" en la simulación

                 process = Process(pid, filename, arrival, burst_estimate)
                 self.processes_to_schedule.append(process)
                 new_processes_found += 1
                 # Añadir a la tabla de la GUI
                 self.proc_tree.insert("", tk.END, iid=str(pid), values=(
                     pid, filename, process.state, arrival, burst_estimate, burst_estimate,
                     "N/A", "N/A", "N/A", "N/A"
                 ))

        if new_processes_found > 0:
            self.status_bar.config(text=f"Cargados {new_processes_found} archivos para procesar.")
            # Si la simulación no está corriendo, ofrecer iniciarla
            if not self.simulation_running:
                 self.start_sim_button.config(state=tk.NORMAL)
                 messagebox.showinfo("Simulación", f"Se añadieron {new_processes_found} tareas. Presiona 'Iniciar Simulación'.")
            # Si ya está corriendo, las tareas se añadirán en el siguiente tick
        else:
             self.status_bar.config(text=f"No se encontraron nuevos archivos .txt en '{source_dir}'.")


    def start_simulation(self):
         if not self.processes_to_schedule and not self.ready_queue and not self.running_processes:
             messagebox.showinfo("Simulación", "No hay procesos para simular. Espera un trigger.")
             return
         if not self.simulation_running:
             self.simulation_running = True
             self.start_sim_button.config(text="Pausar Simulación") # Ocultar/deshabilitar?
             self.status_bar.config(text="Simulación iniciada...")
             self.simulation_step() # Iniciar el primer paso
         else:
             # Pausar lógica (opcional)
             self.simulation_running = False
             self.start_sim_button.config(text="Reanudar Simulación")
             self.status_bar.config(text="Simulación pausada.")


    def simulation_step(self):
        if not self.simulation_running:
            return # No hacer nada si está pausada

        current_time = self.simulation_time
        self.sim_time_label.config(text=f"Tiempo Simulación: {current_time}")

        # 1. Mover procesos nuevos a la cola Ready si llegaron
        remaining_processes = []
        for proc in self.processes_to_schedule:
            if proc.arrival_time <= current_time:
                proc.state = "Ready"
                self.ready_queue.append(proc)
                self.update_process_table(proc.pid, {"Estado": "Ready"})
            else:
                remaining_processes.append(proc)
        self.processes_to_schedule = remaining_processes

        # 2. Manejar procesos terminados en el ciclo anterior
        # (Limpiar los slots de 'running_processes')
        # Esto se hace implícitamente al asignar nuevos procesos

        # 3. Seleccionar procesos para ejecutar (Scheduling)
        # Liberar 'threads' de procesos que terminaron en este tick
        processes_just_finished = []
        active_threads = len(self.running_processes)

        temp_running = []
        for proc in self.running_processes:
             if proc.remaining_burst_time <= 0: # Proceso terminó en el tick anterior
                 processes_just_finished.append(proc)
                 # Aquí se calcula métricas y se lanza el procesamiento real
                 self.handle_process_completion(proc, current_time)
             else:
                 temp_running.append(proc) # Sigue corriendo o esperando
        self.running_processes = temp_running
        active_threads = len(self.running_processes)


        # Asignar nuevos procesos a los threads libres
        available_threads = self.num_simulated_threads - active_threads
        while available_threads > 0 and self.ready_queue:
             # Aplicar algoritmo de scheduling para elegir el siguiente
             # Nota: Un scheduler más complejo podría necesitar la lista completa de running_processes
             #       y el estado de la ready_queue. Esta implementación es simplificada.
             #       Para RR o SJF necesitaríamos ordenar o buscar en ready_queue.
             if isinstance(self.scheduler, SchedulerFCFS):
                # FCFS: Ordenar por llegada (si no está ya) y tomar el primero
                self.ready_queue.sort(key=lambda p: p.arrival_time)
                next_process = self.ready_queue.pop(0) # Tomar y quitar de ready
             # elif isinstance(self.scheduler, SchedulerSJF):
             #     # SJF: Ordenar por burst time, tomar el más corto
             #     self.ready_queue.sort(key=lambda p: p.burst_time) # O remaining_burst_time si es preemptive
             #     next_process = self.ready_queue.pop(0)
             # elif isinstance(self.scheduler, SchedulerRR):
             #     # RR: Tomar el siguiente de la cola circular (ready_queue)
             #     if self.ready_queue:
             #        next_process = self.ready_queue.pop(0) # Tomar del frente
             #        # Falta lógica para reencolar si no termina en el quantum
             else: # Default FCFS si algo falla
                  self.ready_queue.sort(key=lambda p: p.arrival_time)
                  next_process = self.ready_queue.pop(0)


             if next_process:
                next_process.state = "Running"
                if next_process.start_time == -1: # Primera vez que corre
                    next_process.start_time = current_time
                self.running_processes.append(next_process)
                self.update_process_table(next_process.pid, {"Estado": "Running", "Comienzo": next_process.start_time})
                available_threads -= 1
                active_threads +=1


        # 4. Simular la ejecución en los 'threads'
        gantt_current_tick = [] # (pid, thread_id) for this tick
        for i, proc in enumerate(self.running_processes):
            proc.remaining_burst_time -= 1
            gantt_current_tick.append((proc.pid, i)) # PID y el 'thread' simulado (índice)
            self.update_process_table(proc.pid, {"Restante": proc.remaining_burst_time})
            # Lógica RR: Si se cumple el quantum y no ha terminado, mover a Ready
            # if isinstance(self.scheduler, SchedulerRR) and quantum_expired:
            #    proc.state = "Ready"
            #    self.ready_queue.append(proc) # Poner al final de ready
            #    # Quitar de running_processes (se hará en el siguiente ciclo)


        # Actualizar Gantt (Simplificado - añadir info del tick actual)
        if gantt_current_tick:
            self.update_gantt_display(current_time, gantt_current_tick)


        # 5. Incrementar tiempo de simulación
        self.simulation_time += 1

        # 6. Comprobar si la simulación ha terminado
        if not self.processes_to_schedule and not self.ready_queue and not self.running_processes:
            self.simulation_running = False
            self.start_sim_button.config(text="Simulación Completa", state=tk.DISABLED)
            self.status_bar.config(text=f"Simulación completada en {current_time} ticks.")
            self.calculate_and_display_averages()
        else:
            # Programar el siguiente paso
            self.root.after(self.simulation_update_ms, self.simulation_step)


    def handle_process_completion(self, process, completion_time):
         process.state = "Terminated"
         process.completion_time = completion_time
         process.turnaround_time = process.completion_time - process.arrival_time
         # Waiting time = Turnaround Time - Burst Time
         # O más preciso: Tiempo total - tiempo ejecutando - tiempo de llegada?
         # Waiting = Completion - Arrival - Burst
         process.waiting_time = process.turnaround_time - process.burst_time # Asume no hay I/O

         self.completed_processes.append(process)

         # Actualizar tabla
         self.update_process_table(process.pid, {
             "Estado": "Terminated",
             "Fin": process.completion_time,
             "Retorno": process.turnaround_time,
             "Espera": process.waiting_time,
             "Restante": 0
         })

         # Enviar progreso al servidor (opcional)
         self.send_message({"type": "PROGRESS", "payload": {"pid": process.pid, "status": "completed"}})

         # Lanzar el procesamiento real del archivo en un hilo
         file_processing_thread = threading.Thread(
             target=self.process_text_file_thread,
             args=(process.filename, process.pid),
             daemon=True
         )
         file_processing_thread.start()


    def update_process_table(self, pid, updates):
        """Actualiza una fila específica en el Treeview de procesos."""
        item_id = str(pid)
        if self.proc_tree.exists(item_id):
             current_values = list(self.proc_tree.item(item_id, 'values'))
             cols = list(self.proc_tree['columns'])
             new_values = list(current_values) # Hacer copia
             for key, value in updates.items():
                 try:
                     index = cols.index(key) # Busca el nombre de columna ('Estado', 'Fin', etc.)
                     new_values[index] = value
                 except ValueError:
                     print(f"Advertencia: Columna '{key}' no encontrada en la tabla de procesos.")

             self.proc_tree.item(item_id, values=tuple(new_values))


    def update_gantt_display(self, time, running_pids_with_threads):
         """Actualiza la visualización Gantt (ejemplo con texto)."""
         self.gantt_text.config(state=tk.NORMAL)
         gantt_line = f"T={time}: "
         running_strs = []
         for pid, thread_id in running_pids_with_threads:
              running_strs.append(f"[T{thread_id}:P{pid}]")

         # Rellenar threads inactivos
         inactive_threads = self.num_simulated_threads - len(running_pids_with_threads)
         for i in range(inactive_threads):
              thread_id_actual = len(running_pids_with_threads) + i
              running_strs.append(f"[T{thread_id_actual}:Idle]")

         gantt_line += " ".join(running_strs) + "\n"
         self.gantt_text.insert(tk.END, gantt_line)
         self.gantt_text.see(tk.END) # Auto-scroll
         self.gantt_text.config(state=tk.DISABLED)


    def calculate_and_display_averages(self):
        if not self.completed_processes:
            return
        total_turnaround = sum(p.turnaround_time for p in self.completed_processes)
        total_waiting = sum(p.waiting_time for p in self.completed_processes)
        count = len(self.completed_processes)
        avg_turnaround = total_turnaround / count
        avg_waiting = total_waiting / count

        self.avg_turnaround_label.config(text=f"Retorno Promedio: {avg_turnaround:.2f}")
        self.avg_waiting_label.config(text=f"Espera Promedio: {avg_waiting:.2f}")


    # --- Métodos de Procesamiento de Archivos y CSV ---
    def process_text_file_thread(self, filename, pid):
        """Ejecuta la extracción regex y escritura CSV en un hilo."""
        filepath = os.path.join("text_files", filename)
        extracted_data = ["N/A"] * 2 # Placeholder para datos extraídos
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # --- DEFINE TUS REGEX AQUÍ ---
                # Ejemplo: buscar fechas (dd/mm/yyyy)
                dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', content)
                if dates: extracted_data[0] = dates[0] # Tomar la primera

                # Ejemplo: buscar emails
                emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)
                if emails: extracted_data[1] = emails[0]

        except FileNotFoundError:
             print(f"Error: Archivo {filepath} no encontrado para procesamiento.")
             extracted_data = ["FILE_NOT_FOUND"] * 2
        except Exception as e:
            print(f"Error procesando archivo {filepath}: {e}")
            extracted_data = ["PROCESSING_ERROR"] * 2

        # Escribir en CSV de forma segura
        process_info = next((p for p in self.completed_processes if p.pid == pid), None)
        if process_info:
            row_data = [
                process_info.pid, process_info.filename, process_info.arrival_time,
                process_info.burst_time, process_info.completion_time,
                process_info.turnaround_time, process_info.waiting_time
            ] + extracted_data

            with self.csv_lock:
                if self.csv_writer and self.csv_file and not self.csv_file.closed:
                     try:
                        self.csv_writer.writerow(row_data)
                        self.csv_file.flush() # Asegurar escritura inmediata
                        # Actualizar la vista previa (usando la cola para seguridad de hilos)
                        self.message_queue.put({"type": "_UPDATE_CSV_VIEW_", "payload": row_data})
                     except Exception as e:
                         print(f"Error escribiendo al CSV: {e}")


    def update_csv_preview(self, row_data):
         """Añade una fila a la vista previa del CSV en la GUI."""
         self.csv_text.config(state=tk.NORMAL)
         # Formatear la fila como texto CSV
         formatted_row = ",".join(map(str, row_data)) + "\n"
         self.csv_text.insert(tk.END, formatted_row)
         self.csv_text.see(tk.END)
         self.csv_text.config(state=tk.DISABLED)

    def save_or_update_csv_view(self):
         """Lee el archivo CSV y actualiza la vista completa."""
         if not self.csv_file or self.csv_file.closed:
              messagebox.showerror("CSV", "El archivo CSV no está abierto.")
              return

         self.csv_text.config(state=tk.NORMAL)
         self.csv_text.delete('1.0', tk.END) # Limpiar vista previa
         try:
             with self.csv_lock: # Asegurar que no se escriba mientras leemos
                self.csv_file.seek(0) # Ir al inicio del archivo
                content = self.csv_file.read()
                self.csv_text.insert('1.0', content)
             self.status_bar.config(text=f"Vista previa del CSV actualizada desde {self.output_csv_path}")
         except Exception as e:
             messagebox.showerror("Error CSV", f"No se pudo leer el archivo CSV: {e}")
         finally:
              self.csv_text.config(state=tk.DISABLED)


    # --- Método de Cierre ---
    def on_closing(self):
        if messagebox.askokcancel("Salir", "¿Seguro que quieres salir?"):
            self.disconnect_server() # Intenta desconectar limpiamente
            # Cerrar archivo CSV si está abierto
            if self.csv_file and not self.csv_file.closed:
                with self.csv_lock:
                    self.csv_file.close()
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ClientApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing) # Manejar cierre de ventana
    root.mainloop()
