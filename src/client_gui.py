# src/client_gui.py

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import socket
import threading
import json
import queue
import time
import os

from .process import Process
from .scheduler import AVAILABLE_SCHEDULERS, SchedulerFCFS, SchedulerRR, SchedulerSJF

class ClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cliente de Scheduling OS")
        self.root.geometry("1200x850")
       

        self.client_socket = None
        self.connected = False
        self.server_addr = tk.StringVar(value="127.0.0.1")
        self.server_port = tk.StringVar(value="65432")
        self.event_name_var = tk.StringVar(value="data_event")
        self.subscribed_events = set()
        self.message_queue = queue.Queue()

        self.processing_mode_var = tk.StringVar(value="threads")
        self.worker_count_var = tk.IntVar(value=2)

        self.server_assigned_files = []
        self.files_for_simulation_vars: dict[str, tk.BooleanVar] = {}
        self.process_params_entries: dict = {}

        self.client_id = f"client_{os.getpid()}_{int(time.time())}"
        self.output_csv_path = os.path.join(
            "output", f"results_{self.client_id}.csv"
        )
        # Adaptar estos encabezados a los datos que realmente envíe el servidor
        self.csv_headers = [
            "PID_Servidor_Sim", "NombreArchivo", "Emails", "Fechas",
            "ConteoPalabras", "EstadoServidor", "MsgErrorServidor"
        ]
        self.server_results_for_csv = []

        self.processes_to_simulate = []
        self.ready_queue_sim = []
        self.running_processes_sim = []
        self.completed_processes_sim = []
        self.simulation_time_sim = 0
        self.scheduler_sim = SchedulerFCFS()
        self.selected_algorithm_var = tk.StringVar(value="FCFS")
        self.process_pid_counter_sim = 0
        self.simulation_running_sim = False
        self.simulation_update_ms = 500
        self.num_workers_for_sim_display = 2
        self.quantum_var = tk.IntVar(value=2)

        self._create_widgets()
        self._setup_output_dir()
        self.cargar_archivos_locales()
        self.root.after(100, self.check_message_queue)

    def _setup_output_dir(self):
        try:
            os.makedirs("output", exist_ok=True)
        except Exception as e:
            messagebox.showerror(
                "Error Directorio", f"No se pudo crear 'output/': {e}"
            )

    def cargar_archivos_locales(self):
        carpeta = os.path.join("src", "text_files")
        if not os.path.isdir(carpeta):
            messagebox.showwarning("Archivos", f"No se encontró la carpeta: {carpeta}")
            return

        archivos = [f for f in os.listdir(carpeta) if f.endswith(".txt")]
        archivos.sort()

        if not archivos:
            messagebox.showinfo("Archivos", "No se encontraron archivos .txt en la carpeta local.")
            return

        self.server_assigned_files = [os.path.join("src/text_files", f) for f in archivos]
        self.display_file_selection_ui()



    def _create_widgets(self):
        # --- Sección Superior (Conexión, Config Cliente, Suscripción) ---
        top_frame = ttk.Frame(self.root)
        top_frame.pack(padx=10, pady=5, fill="x")

        # Conexión
        conn_frame = ttk.LabelFrame(top_frame, text="Conexión Servidor")
        conn_frame.pack(side=tk.LEFT, padx=5, pady=5, fill="y")

        ttk.Label(conn_frame, text="IP:").grid(
            row=0, column=0, padx=5, pady=2, sticky="w"
        )
        ttk.Entry(conn_frame, textvariable=self.server_addr, width=15).grid(
            row=0, column=1, padx=5, pady=2
        )
        ttk.Label(conn_frame, text="Puerto:").grid(
            row=1, column=0, padx=5, pady=2, sticky="w"
        )
        ttk.Entry(conn_frame, textvariable=self.server_port, width=7).grid(
            row=1, column=1, padx=5, pady=2, sticky="w"
        )

        self.connect_button = ttk.Button(
            conn_frame, text="Conectar", command=self.connect_server
        )
        self.connect_button.grid(row=2, column=0, padx=5, pady=5)

        self.disconnect_button = ttk.Button(
            conn_frame, text="Desconectar",
            command=self.disconnect_server, state=tk.DISABLED
        )
        self.disconnect_button.grid(row=2, column=1, padx=5, pady=5)

        # Configuración Cliente
        client_config_frame = ttk.LabelFrame(
            top_frame, text="Config. Cliente (p/ Servidor)"
        )
        client_config_frame.pack(side=tk.LEFT, padx=5, pady=5, fill="y")

        ttk.Radiobutton(
            client_config_frame, text="Threads",
            variable=self.processing_mode_var, value="threads"
        ).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Radiobutton(
            client_config_frame, text="Forks",
            variable=self.processing_mode_var, value="forks"
        ).grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(client_config_frame, text="Cantidad:").grid(
            row=1, column=0, padx=5, pady=2, sticky="w"
        )
        ttk.Spinbox(
            client_config_frame, from_=1, to=16,
            textvariable=self.worker_count_var, width=5
        ).grid(row=1, column=1, padx=5, pady=2, sticky="w")

        self.apply_config_button = ttk.Button(
            client_config_frame, text="Aplicar Config.",
            command=self.send_client_config, state=tk.DISABLED
        )
        self.apply_config_button.grid(
            row=2, column=0, columnspan=2, padx=5, pady=5
        )

        # Suscripción Eventos
        sub_frame = ttk.LabelFrame(top_frame, text="Suscripción Eventos")
        sub_frame.pack(side=tk.LEFT, padx=5, pady=5, fill="y")

        ttk.Label(sub_frame, text="Evento:").grid(
            row=0, column=0, padx=5, pady=2, sticky="w"
        )
        ttk.Entry(
            sub_frame, textvariable=self.event_name_var, width=15
        ).grid(row=0, column=1, padx=5, pady=2)

        self.sub_button = ttk.Button(
            sub_frame, text="Suscribir",
            command=self.subscribe_event, state=tk.DISABLED
        )
        self.sub_button.grid(row=1, column=0, padx=5, pady=5)

        self.unsub_button = ttk.Button(
            sub_frame, text="Desuscribir",
            command=self.unsubscribe_event, state=tk.DISABLED
        )
        self.unsub_button.grid(row=1, column=1, padx=5, pady=5)

        self.subscribed_label = ttk.Label(
            sub_frame, text="Suscrito a: Ninguno", width=30, wraplength=180
        )
        self.subscribed_label.grid(
            row=2, column=0, columnspan=2, padx=5, pady=2
        )

        # --- Sección Media (Selección Archivos Sim, Parámetros Sim, Config Sim Visual) ---
        mid_frame = ttk.Frame(self.root)
        mid_frame.pack(padx=10, pady=5, fill="x")

        # Selección de Archivos
        self.files_select_frame = ttk.LabelFrame(
            mid_frame, text="Archivos Asignados (Seleccionar para Simulación)"
        )
        self.files_select_frame.pack(
            side=tk.LEFT, padx=5, pady=5, fill="both", expand=True
        )
        self.files_canvas = tk.Canvas(self.files_select_frame, height=100)
        self.files_scrollbar = ttk.Scrollbar(
            self.files_select_frame, orient="vertical", command=self.files_canvas.yview
        )
        self.scrollable_files_frame = ttk.Frame(self.files_canvas)
        self.scrollable_files_frame.bind(
            "<Configure>",
            lambda e: self.files_canvas.configure(
                scrollregion=self.files_canvas.bbox("all")
            )
        )
        self.files_canvas_window = self.files_canvas.create_window(
            (0, 0), window=self.scrollable_files_frame, anchor="nw"
        )
        self.files_canvas.configure(yscrollcommand=self.files_scrollbar.set)
        self.files_canvas.pack(side="left", fill="both", expand=True)
        self.files_scrollbar.pack(side="right", fill="y")

        self.confirm_files_button = ttk.Button(
            self.files_select_frame, text="Definir Parámetros",
            command=self.setup_parameter_input_ui, state=tk.DISABLED
        )
        self.confirm_files_button.pack(side=tk.BOTTOM, pady=5)

        # Parámetros de Simulación
        self.params_outer_frame = ttk.LabelFrame(
            mid_frame, text="Parámetros de Simulación (Entrada Manual)"
        )
        self.params_outer_frame.pack(
            side=tk.LEFT, padx=5, pady=5, fill="both", expand=True
        )
        self.params_canvas = tk.Canvas(self.params_outer_frame, height=100)
        self.params_scrollbar = ttk.Scrollbar(
            self.params_outer_frame, orient="vertical", command=self.params_canvas.yview
        )
        self.scrollable_params_frame = ttk.Frame(self.params_canvas)
        self.scrollable_params_frame.bind(
            "<Configure>",
            lambda e: self.params_canvas.configure(
                scrollregion=self.params_canvas.bbox("all")
            )
        )
        self.params_canvas_window = self.params_canvas.create_window(
            (0,0), window=self.scrollable_params_frame, anchor="nw"
        )
        self.params_canvas.configure(yscrollcommand=self.params_scrollbar.set)
        self.params_canvas.pack(side=tk.LEFT, fill="both", expand=True)
        self.params_scrollbar.pack(side="right", fill="y")

        # Configuración Simulación Visual
        sim_config_frame = ttk.LabelFrame(mid_frame, text="Config. Simulación Visual")
        sim_config_frame.pack(side=tk.LEFT, padx=5, pady=5, fill="y")

        ttk.Label(sim_config_frame, text="Algoritmo:").grid(
            row=0, column=0, padx=5, pady=2, sticky="w"
        )
        self.algo_combo = ttk.Combobox(
            sim_config_frame, textvariable=self.selected_algorithm_var,
            values=list(AVAILABLE_SCHEDULERS.keys()), state="readonly", width=12
        )
        self.algo_combo.grid(row=0, column=1, padx=5, pady=2)
        self.algo_combo.bind("<<ComboboxSelected>>", self.change_scheduler_sim)

        self.quantum_label = ttk.Label(sim_config_frame, text="Quantum (RR):")
        self.quantum_spinbox = ttk.Spinbox(
            sim_config_frame, from_=1, to=10,
            textvariable=self.quantum_var, width=5
        )
        # (grid/grid_forget se maneja en change_scheduler_sim)

        self.start_sim_button = ttk.Button(
            sim_config_frame, text="Iniciar Sim. Visual",
            command=self.start_simulation_visual, state=tk.DISABLED
        )
        self.start_sim_button.grid(
            row=2, column=0, columnspan=2, padx=5, pady=10
        )

        # --- Sección Inferior (Visualización) ---
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(padx=10, pady=10, fill="both", expand=True)

        notebook = ttk.Notebook(bottom_frame)
        notebook.pack(fill="both", expand=True, side=tk.LEFT, padx=5)

        # Tab: Tabla de Procesos (Simulación)
        proc_frame_sim = ttk.Frame(notebook)
        notebook.add(proc_frame_sim, text='Tabla Procesos (Sim.)')
        cols_sim = (
            "PID_Sim", "Archivo", "Estado", "Llegada", "Ráfaga",
            "Prioridad", "Restante", "Comienzo", "Fin", "Retorno", "Espera"
        )
        self.proc_tree_sim = ttk.Treeview(
            proc_frame_sim, columns=cols_sim, show='headings', height=8
        )
        for col in cols_sim:
            self.proc_tree_sim.heading(col, text=col)
            self.proc_tree_sim.column(col, width=75, anchor=tk.CENTER)
        self.proc_tree_sim.pack(fill="both", expand=True)

        # Tab: Gantt (Simulado)
        gantt_frame_sim = ttk.Frame(notebook)
        notebook.add(gantt_frame_sim, text='Gantt (Sim.)')
        self.gantt_text_sim = scrolledtext.ScrolledText(
            gantt_frame_sim, height=10, wrap=tk.WORD, state=tk.DISABLED
        )
        self.gantt_text_sim.pack(fill="both", expand=True, padx=5, pady=5)

        # Frame derecho para resultados del servidor y CSV
        server_results_main_frame = ttk.Frame(bottom_frame)
        server_results_main_frame.pack(
            fill="both", expand=True, side=tk.LEFT, padx=5
        )

        avg_frame_sim = ttk.LabelFrame(
            server_results_main_frame, text="Métricas Promedio (Simulación)"
        )
        avg_frame_sim.pack(padx=5, pady=5, fill="x")
        self.avg_turnaround_label_sim = ttk.Label(
            avg_frame_sim, text="Retorno Promedio: N/A"
        )
        self.avg_turnaround_label_sim.pack(side=tk.LEFT, padx=10)
        self.avg_waiting_label_sim = ttk.Label(
            avg_frame_sim, text="Espera Promedio: N/A"
        )
        self.avg_waiting_label_sim.pack(side=tk.LEFT, padx=10)
        self.sim_time_label_display = ttk.Label(
            avg_frame_sim, text="Tiempo Simulación: 0"
        )
        self.sim_time_label_display.pack(side=tk.RIGHT, padx=10)

        csv_frame = ttk.LabelFrame(
            server_results_main_frame, text="Resultados del Servidor (para CSV)"
        )
        csv_frame.pack(padx=5, pady=5, fill="both", expand=True)
        self.server_results_text = scrolledtext.ScrolledText(
            csv_frame, height=10, wrap=tk.NONE, state=tk.DISABLED
        )
        self.server_results_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.save_csv_button = ttk.Button(
            csv_frame, text="Guardar Resultados a CSV",
            command=self.save_results_to_csv, state=tk.DISABLED
        )
        self.save_csv_button.pack(pady=5)

        self.status_bar = ttk.Label(
            self.root, text="Desconectado.", relief=tk.SUNKEN, anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill="x")

        self.change_scheduler_sim() # Para ocultar quantum inicialmente

    # --- Conexión y Comunicación ---
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
            self.apply_config_button.config(state=tk.NORMAL)
            self.sub_button.config(state=tk.NORMAL)

            self.receive_thread = threading.Thread(
                target=self.listen_to_server, daemon=True
            )
            self.receive_thread.start()
            self.send_client_config() # Enviar config inicial

        except ValueError:
            messagebox.showerror("Error", "Puerto inválido.")
        except socket.error as e:
            messagebox.showerror("Error de Conexión", f"No se pudo conectar: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error inesperado al conectar: {e}")

    def disconnect_server(self):
        if not self.connected:
            return

        try:
            if self.client_socket:
                self.client_socket.close()
        except Exception as e:
            print(f"Error al cerrar socket: {e}")
        finally:
            self.client_socket = None
            self.connected = False
            self.simulation_running_sim = False
            self.status_bar.config(text="Desconectado.")

            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
            self.apply_config_button.config(state=tk.DISABLED)
            self.sub_button.config(state=tk.DISABLED)
            self.unsub_button.config(state=tk.DISABLED)
            self.start_sim_button.config(state=tk.DISABLED)
            self.confirm_files_button.config(state=tk.DISABLED)

            self.subscribed_events.clear()
            self.update_subscribed_label()
            self.clear_file_selection_ui()
            self.clear_parameter_input_ui()

    def send_message(self, message):
        if self.connected and self.client_socket:
            try:
                payload = json.dumps(message) + "\n"
                self.client_socket.sendall(payload.encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError):
                self.disconnect_server() # Maneja la desconexión
                messagebox.showerror("Error de Red", "Conexión perdida con el servidor.")
            except Exception as e:
                messagebox.showerror("Error de Envío", f"No se pudo enviar mensaje: {e}")
        else:
            messagebox.showwarning("Envío", "No estás conectado.")

    def listen_to_server(self):
        buffer = ""
        while self.connected and self.client_socket:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    if self.connected:
                        self.message_queue.put(
                            {"type": "ERROR", "payload": "Servidor desconectado."}
                        )
                    break # Conexión cerrada por el servidor

                buffer += data.decode('utf-8')

                while '\n' in buffer:
                    message_str, buffer = buffer.split('\n', 1)
                    if not message_str.strip():
                        continue
                    try:
                        message = json.loads(message_str)
                        self.message_queue.put(message)
                    except json.JSONDecodeError:
                        print(f"Error decodificando parte del mensaje: {message_str}")

            except (ConnectionResetError, BrokenPipeError):
                if self.connected:
                    self.message_queue.put(
                        {"type": "ERROR", "payload": "Conexión perdida."}
                    )
                break
            except socket.error as e: # Podría ser que cerramos el socket desde disconnect_server
                if self.connected:
                    self.message_queue.put(
                        {"type": "ERROR", "payload": f"Error de socket: {e}"}
                    )
                break
            except Exception as e: # Otros errores inesperados
                if self.connected:
                    self.message_queue.put(
                        {"type": "ERROR", "payload": f"Error inesperado en listener: {e}"}
                    )
                break

        if self.connected: # Si el bucle termina y aún estábamos "conectados"
            self.message_queue.put({"type": "_THREAD_EXIT_", "payload": None})

    def check_message_queue(self):
        """Revisa la cola de mensajes del hilo listener y procesa en el hilo de la GUI."""
        try:
            while True: # Procesa todos los mensajes pendientes en la cola
                message = self.message_queue.get_nowait()
                self.handle_server_message(message)
        except queue.Empty:
            pass # La cola está vacía, no hay nada que hacer ahora
        finally:
            self.root.after(100, self.check_message_queue) # Volver a programar

    def handle_server_message(self, message):
        msg_type = message.get("type")
        payload = message.get("payload")
        # print(f"GUI recibió: Tipo={msg_type}") # Comentar para menos logs

        if msg_type == "ACK_CONFIG":
            if payload.get("status") == "success":
                cfg = payload.get('config')
                self.status_bar.config(text=f"Config. aplicada por servidor: {cfg}")
                self.num_workers_for_sim_display = cfg.get('count', 2)
            else:
                msg = payload.get('message')
                messagebox.showerror("Error Config.", f"Servidor rechazó config: {msg}")

        elif msg_type == "START_PROCESSING":
            self.server_assigned_files = payload.get("files", [])
            event = payload.get('event')
            num_files = len(self.server_assigned_files)
            self.status_bar.config(
                text=f"Servidor inició proc. evento '{event}'. Archivos: {num_files}"
            )
            self.server_results_for_csv.clear() # Limpiar resultados anteriores
            self.save_csv_button.config(state=tk.DISABLED)
            self.display_file_selection_ui() # Mostrar checkboxes

        elif msg_type == "PROCESSING_COMPLETE":
            event = payload.get('event')
            status = payload.get('status')
            self.status_bar.config(
                text=f"Servidor completó proc. '{event}'. Estado: {status}"
            )
            if status == "success":
                self.server_results_for_csv = payload.get("results", [])
                self.display_server_results()
                if self.server_results_for_csv:
                    self.save_csv_button.config(state=tk.NORMAL)
            else:
                msg = payload.get('message')
                messagebox.showerror("Error Procesamiento Servidor", f"Error: {msg}")

        elif msg_type == "ACK_SUB":
            event_name = payload
            self.subscribed_events.add(event_name)
            self.update_subscribed_label()
            self.unsub_button.config(state=tk.NORMAL)

        elif msg_type == "ACK_UNSUB":
            event_name = payload
            self.subscribed_events.discard(event_name)
            self.update_subscribed_label()
            if not self.subscribed_events:
                self.unsub_button.config(state=tk.DISABLED)

        elif msg_type == "SERVER_EXIT":
            messagebox.showinfo("Servidor", "El servidor ha cerrado la conexión.")
            self.disconnect_server()

        elif msg_type == "ERROR" or msg_type == "_THREAD_EXIT_":
            if self.connected: # Evitar doble mensaje
                err_payload = payload if isinstance(payload, str) else "Error o desconexión."
                messagebox.showerror("Error de Red", err_payload)
                self.disconnect_server()

    # --- Configuración Cliente y Suscripción ---
    def send_client_config(self):
        mode = self.processing_mode_var.get()
        try:
            count = int(self.worker_count_var.get())
            if count <= 0:
                messagebox.showerror("Error Config", "Cantidad debe ser positiva.")
                return

            config_payload = {"mode": mode, "count": count}
            self.send_message({"type": "SET_CONFIG", "payload": config_payload})
            # self.num_workers_for_sim_display se actualiza con ACK_CONFIG del servidor
        except ValueError:
            messagebox.showerror("Error Config", "Cantidad de workers inválida.")

    def subscribe_event(self):
        event = self.event_name_var.get()
        if not event:
            messagebox.showwarning("Suscripción", "Ingresa un nombre de evento.")
            return
        self.send_message({"type": "SUB", "payload": event})

    def unsubscribe_event(self):
        event = self.event_name_var.get()
        if not event:
            messagebox.showwarning("Suscripción", "Ingresa un nombre de evento.")
            return
        if event not in self.subscribed_events:
            messagebox.showinfo("Suscripción", f"No estás suscrito a '{event}'.")
            return
        self.send_message({"type": "UNSUB", "payload": event})

    def update_subscribed_label(self):
        text = f"Suscrito a: {', '.join(self.subscribed_events) if self.subscribed_events else 'Ninguno'}"
        self.subscribed_label.config(text=text)

    # --- UI Selección Archivos y Parámetros Simulación ---
    def display_file_selection_ui(self):
        self.clear_file_selection_ui()
        self.clear_parameter_input_ui()
        self.files_for_simulation_vars.clear()

        if not self.server_assigned_files:
            ttk.Label(
                self.scrollable_files_frame, text="No hay archivos asignados."
            ).pack(padx=5, pady=5)
            self.confirm_files_button.config(state=tk.DISABLED)
            return

        for filename in self.server_assigned_files:
            var = tk.BooleanVar(value=False) # CORRECCIÓN: Deseleccionado por defecto
            cb = ttk.Checkbutton(
                self.scrollable_files_frame, text=filename, variable=var
            )
            cb.pack(anchor="w", padx=5, pady=1) # Pequeño pady
            self.files_for_simulation_vars[filename] = var

        self.confirm_files_button.config(state=tk.NORMAL)
        self.root.update_idletasks() # Actualizar para que bbox sea correcto
        self.files_canvas.config(scrollregion=self.files_canvas.bbox("all"))
        num_files = len(self.server_assigned_files)
        new_height = min(max(num_files * 25, 50), 150) # altura entre 50 y 150px
        self.files_canvas.config(height=new_height)


    def clear_file_selection_ui(self):
        for widget in self.scrollable_files_frame.winfo_children():
            widget.destroy()
        self.confirm_files_button.config(state=tk.DISABLED)

    def setup_parameter_input_ui(self):
        self.clear_parameter_input_ui()
        self.processes_to_simulate.clear()
        self.process_pid_counter_sim = 0
        self.proc_tree_sim.delete(*self.proc_tree_sim.get_children())

        selected_files = [
            fname for fname, var in self.files_for_simulation_vars.items() if var.get()
        ]

        if not selected_files:
            messagebox.showinfo("Simulación", "No se seleccionaron archivos para simular.")
            self.start_sim_button.config(state=tk.DISABLED)
            return

        # Crear cabeceras dentro de self.scrollable_params_frame
        header_frame = ttk.Frame(self.scrollable_params_frame)
        header_frame.pack(fill="x", pady=2)
        ttk.Label(
            header_frame, text="Archivo", width=20, relief=tk.RIDGE
        ).pack(side=tk.LEFT, padx=1)
        ttk.Label(
            header_frame, text="Llegada", width=7, relief=tk.RIDGE
        ).pack(side=tk.LEFT, padx=1)
        ttk.Label(
            header_frame, text="Ráfaga", width=7, relief=tk.RIDGE
        ).pack(side=tk.LEFT, padx=1)
        self.priority_header_label = ttk.Label(
            header_frame, text="Prioridad", width=7, relief=tk.RIDGE
        ) # Se mostrará/ocultará

        self.process_params_entries.clear()

        for filename in selected_files:
            pid_sim = self.process_pid_counter_sim
            self.process_pid_counter_sim += 1

            entry_frame = ttk.Frame(self.scrollable_params_frame) # Añadir a scrollable
            entry_frame.pack(fill="x", pady=1) # Pequeño pady entre filas

            ttk.Label(entry_frame, text=filename, width=20, anchor="w").pack(
                side=tk.LEFT, padx=1
            )

            arrival_var = tk.StringVar(value="0")
            burst_var = tk.StringVar(value="5")
            priority_var = tk.StringVar(value="1")

            ttk.Entry(entry_frame, textvariable=arrival_var, width=7).pack(
                side=tk.LEFT, padx=1
            )
            ttk.Entry(entry_frame, textvariable=burst_var, width=7).pack(
                side=tk.LEFT, padx=1
            )
            priority_entry = ttk.Entry(
                entry_frame, textvariable=priority_var, width=7
            )
            # priority_entry.pack() se maneja en change_scheduler_sim

            self.process_params_entries[pid_sim] = {
                "filename": filename,
                "arrival_var": arrival_var,
                "burst_var": burst_var,
                "priority_var": priority_var,
                "priority_entry_widget": priority_entry
            }

        self.start_sim_button.config(state=tk.NORMAL)
        self.change_scheduler_sim() # Para mostrar/ocultar prioridad y ajustar scroll
        self.root.update_idletasks() # Forzar actualización para bbox
        self.params_canvas.config(scrollregion=self.params_canvas.bbox("all"))
        num_selected = len(selected_files)
        new_param_height = min(max(num_selected * 30, 50), 150) # Ajustar altura
        self.params_canvas.config(height=new_param_height)


    def clear_parameter_input_ui(self):
        # Limpiar el contenido de self.scrollable_params_frame
        for widget in self.scrollable_params_frame.winfo_children():
            widget.destroy()
        self.start_sim_button.config(state=tk.DISABLED)

    # --- Simulación Visual ---
    def change_scheduler_sim(self, event=None):
        algo = self.selected_algorithm_var.get()
        scheduler_class = AVAILABLE_SCHEDULERS.get(algo)
        show_priority = False # Implementar si se añaden schedulers de prioridad
        show_quantum = False

        if scheduler_class:
            if algo == "RR":
                quantum_val = self.quantum_var.get()
                self.scheduler_sim = scheduler_class(
                    quantum=quantum_val if quantum_val > 0 else 2
                )
                show_quantum = True
            elif algo == "Priority_NP":
                self.scheduler_sim = scheduler_class()
                show_priority = True
            elif algo == "HRRN":
                self.scheduler_sim = scheduler_class()
            # elif algo in ["Priority_NP", "Priority_P"]: # Ejemplo
            #     self.scheduler_sim = scheduler_class()
            #     show_priority = True
            else: # FCFS, SJF
                self.scheduler_sim = scheduler_class()
        else:
            messagebox.showerror("Error", f"Algoritmo {algo} no implementado.")
            self.selected_algorithm_var.set("FCFS")
            self.scheduler_sim = SchedulerFCFS()

        # Mostrar/ocultar campos de prioridad
        if hasattr(self, 'priority_header_label'):
            if show_priority:
                self.priority_header_label.pack(side=tk.LEFT, padx=1)
            else:
                self.priority_header_label.pack_forget()

        for params_data in self.process_params_entries.values():
            widget = params_data.get("priority_entry_widget")
            if widget:
                if show_priority:
                    widget.pack(side=tk.LEFT, padx=1)
                else:
                    widget.pack_forget()

        # Mostrar/ocultar campo de quantum
        if show_quantum:
            self.quantum_label.grid(row=1, column=0, padx=5, pady=2, sticky="w")
            self.quantum_spinbox.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        else:
            self.quantum_label.grid_forget()
            self.quantum_spinbox.grid_forget()

        self.status_bar.config(text=f"Algoritmo simulación: {self.scheduler_sim}")
        self.root.update_idletasks() # Para que los pack_forget/grid_forget se apliquen
        if hasattr(self, 'scrollable_params_frame'): # Asegurar que el frame existe
            self.params_canvas.config(scrollregion=self.params_canvas.bbox("all"))

    def start_simulation_visual(self):
        self.processes_to_simulate.clear()
        self.proc_tree_sim.delete(*self.proc_tree_sim.get_children())
        self.ready_queue_sim.clear()
        self.running_processes_sim.clear()
        self.completed_processes_sim.clear()
        self.gantt_text_sim.config(state=tk.NORMAL)
        self.gantt_text_sim.delete('1.0', tk.END)
        self.gantt_text_sim.config(state=tk.DISABLED)
        self.simulation_time_sim = 0
        valid_input = True

        for pid_sim, params in self.process_params_entries.items():
            try:
                filename = params["filename"]
                arrival = int(params["arrival_var"].get())
                burst = int(params["burst_var"].get())
                priority = int(params["priority_var"].get()) # Si se usa

                if burst <= 0:
                    msg = f"Ráfaga para '{filename}' debe ser positiva."
                    messagebox.showerror("Error Simulación", msg)
                    valid_input = False
                    break
                
                proc = Process(pid_sim, filename, arrival, burst, priority) # Añadir priority si es necesario
                self.processes_to_simulate.append(proc)
                self.proc_tree_sim.insert("", tk.END, iid=str(pid_sim), values=(
                     pid_sim, filename, proc.state, arrival, burst, priority,
                     burst, "N/A", "N/A", "N/A", "N/A"
                 ))
            except ValueError:
                messagebox.showerror("Error Simulación", "Entrada inválida para parámetros.")
                valid_input = False
                break

        if not valid_input or not self.processes_to_simulate:
            self.start_sim_button.config(state=tk.NORMAL) # Permitir reintentar
            return

        if not self.simulation_running_sim:
            self.simulation_running_sim = True
            self.start_sim_button.config(text="Pausar Sim. Visual")
            self.status_bar.config(text="Simulación visual iniciada...")
            self.simulation_step_visual()
        else: # Pausar
            self.simulation_running_sim = False
            self.start_sim_button.config(text="Reanudar Sim. Visual")
            self.status_bar.config(text="Simulación visual pausada.")

    def simulation_step_visual(self):
        if not self.simulation_running_sim:
            return

        current_time = self.simulation_time_sim
        self.sim_time_label_display.config(text=f"Tiempo Sim: {current_time}")

        # 1. Mover de self.processes_to_simulate a self.ready_queue_sim
        remaining_to_schedule = []
        for proc in self.processes_to_simulate:
            if proc.arrival_time <= current_time:
                proc.state = "Ready"
                self.ready_queue_sim.append(proc)
                self.update_process_table_sim(proc.pid, {"Estado": "Ready"})
            else:
                remaining_to_schedule.append(proc)
        self.processes_to_simulate = remaining_to_schedule

        # 2. Manejar procesos terminados
        temp_running = []
        for proc in self.running_processes_sim:
            if proc.remaining_burst_time <= 0:
                self.handle_process_completion_sim(proc, current_time)
            else:
                temp_running.append(proc)
        self.running_processes_sim = temp_running

        # 3. Scheduling (Visual)
        available_threads_sim = (
            self.num_workers_for_sim_display - len(self.running_processes_sim)
        )

        if isinstance(self.scheduler_sim, SchedulerSJF): # SJF No Preemptivo
            self.ready_queue_sim.sort(key=lambda p: p.burst_time)
        # ... (más ordenamientos para otros schedulers si es necesario) ...

        while available_threads_sim > 0 and self.ready_queue_sim:
            next_process = self.scheduler_sim.schedule(
                self.ready_queue_sim, current_time,
                self.running_processes_sim, available_threads_sim
            ) # Este método DEBE quitar el proceso de ready_queue_sim si lo selecciona

            if next_process:
                next_process.state = "Running"
                if next_process.start_time == -1:
                    next_process.start_time = current_time
                self.running_processes_sim.append(next_process)
                self.update_process_table_sim(
                    next_process.pid,
                    {"Estado": "Running", "Comienzo": next_process.start_time}
                )
                available_threads_sim -= 1
            else: # No más procesos adecuados según el scheduler
                break

        # 4. Simular ejecución y manejo de RR
        gantt_current_tick_sim = []
        processes_to_requeue_rr = []

        for i, proc in enumerate(self.running_processes_sim):
            proc.remaining_burst_time -= 1
            gantt_current_tick_sim.append((proc.pid, i)) # i es el "thread simulado"
            self.update_process_table_sim(
                proc.pid, {"Restante": proc.remaining_burst_time}
            )

            if isinstance(self.scheduler_sim, SchedulerRR):
                if not hasattr(proc, 'ticks_in_current_burst'):
                    proc.ticks_in_current_burst = 0
                proc.ticks_in_current_burst +=1

                if (proc.ticks_in_current_burst >= self.scheduler_sim.quantum and
                        proc.remaining_burst_time > 0):
                    processes_to_requeue_rr.append(proc)

        # Mover procesos de RR de vuelta a la cola de listos
        if processes_to_requeue_rr:
            for proc_rr in processes_to_requeue_rr:
                self.running_processes_sim.remove(proc_rr)
                proc_rr.state = "Ready"
                proc_rr.ticks_in_current_burst = 0 # Resetear contador
                self.ready_queue_sim.append(proc_rr) # Añadir al final
                self.update_process_table_sim(proc_rr.pid, {"Estado": "Ready"})

        if gantt_current_tick_sim:
            self.update_gantt_display_sim(current_time, gantt_current_tick_sim)

        # 5. Incrementar tiempo
        self.simulation_time_sim += 1

        # 6. Comprobar fin
        if (not self.processes_to_simulate and
                not self.ready_queue_sim and
                not self.running_processes_sim):
            self.simulation_running_sim = False
            self.start_sim_button.config(
                text="Sim. Visual Completa", state=tk.DISABLED
            )
            self.status_bar.config(
                text=f"Sim. visual completada en {current_time} ticks."
            )
            self.calculate_and_display_averages_sim()
        else:
            self.root.after(self.simulation_update_ms, self.simulation_step_visual)

    def handle_process_completion_sim(self, process, completion_time):
        process.state = "Terminated"
        process.completion_time = completion_time
        process.turnaround_time = process.completion_time - process.arrival_time
        process.waiting_time = process.turnaround_time - process.burst_time

        self.completed_processes_sim.append(process)
        self.update_process_table_sim(process.pid, {
             "Estado": "Terminated", "Fin": process.completion_time,
             "Retorno": process.turnaround_time, "Espera": process.waiting_time,
             "Restante": 0
         })

    def update_process_table_sim(self, pid_sim, updates):
        item_id = str(pid_sim)
        if self.proc_tree_sim.exists(item_id):
            current_values = list(self.proc_tree_sim.item(item_id, 'values'))
            cols = list(self.proc_tree_sim['columns'])
            new_values = list(current_values) # Copia
            for key, value in updates.items():
                try:
                    index = cols.index(key)
                    new_values[index] = value
                except ValueError:
                    pass # Columna no encontrada, ignorar
            self.proc_tree_sim.item(item_id, values=tuple(new_values))

    def update_gantt_display_sim(self, time_tick, running_pids_with_threads):
        self.gantt_text_sim.config(state=tk.NORMAL)
        gantt_line = f"T={time_tick}: "
        running_strs = []
        # Mapeo de PID a su thread_id asignado en este tick
        active_map = {pid: th_id for pid, th_id in running_pids_with_threads}

        for i in range(self.num_workers_for_sim_display): # Iterar sobre "slots" de threads
            found_proc_on_thread = False
            # Verificar si algún proceso se está ejecutando en este "slot" de thread (i)
            # Nota: running_pids_with_threads da (pid, índice_en_running_list)
            # Necesitamos asegurar que el índice_en_running_list corresponda a 'i'
            for pid, assigned_thread_index_in_list in active_map.items():
                if assigned_thread_index_in_list == i :
                    running_strs.append(f"[T{i}:P{pid}]")
                    found_proc_on_thread = True
                    break # Solo un proceso por slot de thread
            if not found_proc_on_thread:
                running_strs.append(f"[T{i}:Idle]")
        
        gantt_line += " ".join(running_strs) + "\n"
        self.gantt_text_sim.insert(tk.END, gantt_line)
        self.gantt_text_sim.see(tk.END) # Auto-scroll
        self.gantt_text_sim.config(state=tk.DISABLED)

    def calculate_and_display_averages_sim(self):
        if not self.completed_processes_sim:
            return

        count = len(self.completed_processes_sim)
        avg_T = sum(p.turnaround_time for p in self.completed_processes_sim) / count if count else 0
        avg_W = sum(p.waiting_time for p in self.completed_processes_sim) / count if count else 0

        self.avg_turnaround_label_sim.config(text=f"Retorno Prom: {avg_T:.2f}")
        self.avg_waiting_label_sim.config(text=f"Espera Prom: {avg_W:.2f}")

    # --- Resultados Servidor y CSV ---
    def display_server_results(self):
        self.server_results_text.config(state=tk.NORMAL)
        self.server_results_text.delete('1.0', tk.END)

        if not self.server_results_for_csv:
            self.server_results_text.insert(tk.END, "No hay resultados del servidor.")
            self.server_results_text.config(state=tk.DISABLED)
            return

        for i, res_item in enumerate(self.server_results_for_csv):
            status = res_item.get("status", "N/A")
            fname = res_item.get("filename", "N/A")
            line = f"Archivo: {fname}, Estado: {'OK' if status == 'success' else 'ERROR'}"
            if status == "success":
                data = res_item.get("data", {})
                # Truncar datos largos para visualización
                display_data = {k: (v[:50] + '...' if isinstance(v, list) and len(v) > 3 else v) for k,v in data.items()}
                line += f", Datos: {json.dumps(display_data, indent=2)}"
            else:
                error_msg = res_item.get("error", "Error desconocido")
                line += f", Msg: {error_msg}"
            self.server_results_text.insert(tk.END, line + "\n---\n")

            if i > 20 and len(self.server_results_for_csv) > 25 : # Limitar para no sobrecargar
                remaining = len(self.server_results_for_csv) - i - 1
                self.server_results_text.insert(tk.END, f"... y {remaining} más resultados.")
                break
        self.server_results_text.config(state=tk.DISABLED)

    def save_results_to_csv(self):
        if not self.server_results_for_csv:
            messagebox.showinfo("CSV", "No hay resultados del servidor para guardar.")
            return

        try:
            with open(self.output_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.csv_headers)

                for i, res_item in enumerate(self.server_results_for_csv):
                    fname = res_item.get("filename", f"unknown_file_{i}")
                    server_status = res_item.get("status", "error")
                    error_message = res_item.get("error", "") if server_status == "error" else ""
                    data = res_item.get("data", {}) if server_status == "success" else {}

                    # Construir la fila basada en self.csv_headers
                    # ["PID_Servidor_Sim", "NombreArchivo", "Emails", "Fechas", "ConteoPalabras", "EstadoServidor", "MsgErrorServidor"]
                    row_to_write = [
                        i, # PID simulado para el resultado del servidor
                        fname,
                        (data.get("emails_found") or ["N/A"])[0], # Tomar el primero o N/A
                        (data.get("dates_found") or ["N/A"])[0],  # Tomar el primero o N/A
                        data.get("word_count", "N/A"),
                        server_status.upper(),
                        error_message[:100] # Limitar longitud del mensaje de error
                    ]
                    writer.writerow(row_to_write[:len(self.csv_headers)]) # Asegurar no exceder headers

            messagebox.showinfo(
                "CSV Guardado", f"Resultados guardados en:\n{self.output_csv_path}"
            )
        except Exception as e:
            messagebox.showerror(
                "Error Guardando CSV", f"No se pudo guardar el archivo CSV: {e}"
            )

    def on_closing(self):
        if messagebox.askokcancel("Salir", "¿Seguro que quieres salir?"):
            self.disconnect_server()
            self.root.destroy()


if __name__ == "__main__":
    # Verificaciones simples de que los módulos existen
    if not all([SchedulerFCFS, SchedulerRR, SchedulerSJF]):
        print("Error: Clases de Scheduler no encontradas. "
              "Asegúrate que scheduler.py existe y es correcto.")
        sys.exit(1) # Usar sys.exit para salir limpiamente
    if not Process:
        print("Error: Clase Process no encontrada. "
              "Asegúrate que process.py existe y es correcto.")
        sys.exit(1)

    app_root = tk.Tk()
    app = ClientApp(app_root)
    app_root.protocol("WM_DELETE_WINDOW", app.on_closing)
    app_root.mainloop()