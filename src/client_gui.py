import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import socket
import threading
import json
import queue
import time
import os
import sys

from .process import Process
from .scheduler import (
    AVAILABLE_SCHEDULERS,
    SchedulerFCFS,
    SchedulerRR,
    SchedulerSJF,
    SchedulerHRRN,
    SchedulerPriorityNP,
)


class ClientApp:
    def __init__(self, root):
        """Inicializa la aplicación."""
        self.root = root
        self.root.title("Sistema de Simulación de Scheduling OS")
        self.root.geometry("1200x850")

        self.setup_theme()
        self._setup_output_dir()

        # Variables de estado de la conexión y comunicación
        self.receive_thread = None
        self.client_socket = None
        self.connected = False
        self.server_addr = tk.StringVar(value="127.0.0.1")
        self.server_port = tk.StringVar(value="65432")
        self.event_name_var = tk.StringVar(value="data_event")
        self.selected_event_unsub = tk.StringVar(value="")
        self.subscribed_events = set()
        self.message_queue = queue.Queue()

        # Configuración del cliente para enviar al servidor
        self.processing_mode_var = tk.StringVar(value="threads")
        self.worker_count_var = tk.IntVar(value=2)

        # Identificación del cliente y salida CSV
        self.client_id = f"client_{os.getpid()}_{int(time.time())}"
        self.output_csv_path = os.path.join("output", f"results_{self.client_id}.csv")
        self.csv_headers = [
            "PID_Servidor_Sim",
            "NombreArchivo",
            "Nombres",
            "Lugares",
            "Fechas",
            "ConteoPalabras",
            "EstadoServidor",
            "MsgErrorServidor",
        ]
        self.server_results_for_csv = []

        # Variables para la simulación visual
        self.server_assigned_files = []
        self.files_for_simulation_vars = {}
        self.process_params_entries = {}
        self.processes_to_simulate = []
        self.ready_queue_sim = []
        self.running_processes_sim = []
        self.completed_processes_sim = []
        self.simulation_time_sim = 0
        self.simulation_running_sim = False
        self.process_pid_counter_sim = 0
        self.selected_algorithm_var = tk.StringVar(value="FCFS")
        self.scheduler_sim = None
        self.simulation_update_ms = 500
        self.num_workers_for_sim_display = self.worker_count_var.get()
        self.quantum_var = tk.IntVar(value=2)
        self.selected_files_for_processing = [] # Para enviar al servidor

        # Configuración de colores para el diagrama de Gantt
        self.gantt_colors = {
            "ready": "#b3e0ff",
            "running": "#66cc99",
            "terminated": "#ffcc99",
        }
        self.gantt_data = {
            "last_time": -1,
            "process_colors": {},
            "process_rows": {},
            "time_width": 50,
            "row_height": 40,
            "next_color_index": 0,
            "colors": [
                "#3498DB",
                "#2ECC71",
                "#E74C3C",
                "#F39C12",
                "#9B59B6",
                "#1ABC9C",
                "#D35400",
                "#34495E",
                "#16A085",
                "#C0392B",
            ],
        }

        # Estilo del canvas
        self.canvas_style = {
            "bg": "#f5f5f5",
            "border_width": 1,
            "border_color": "#cccccc",
        }

        self._create_widgets()
        self.root.after(100, self.check_message_queue)

    def setup_theme(self):
        """Configura un tema personalizado para la GUI."""
        self.root.configure(bg="#EFF5F9")

        self.colors = {
            "bg_main": "#EFF5F9",
            "bg_frame": "#F8FAFC",
            "accent1": "#3498DB",
            "accent2": "#2980B9",
            "accent3": "#1ABC9C",
            "text_dark": "#2C3E50",
            "text_light": "#FFFFFF",
            "border": "#D6EAF8",
            "warning": "#E74C3C",
            "success": "#27AE60",
            "header_bg": "#D6EAF8",
            "table_row_alt": "#F5F9FC",
            "hover": "#C9E3F7",
        }

        style = ttk.Style()
        style.theme_use("default")

        style.configure(
            ".",
            background=self.colors["bg_main"],
            foreground=self.colors["text_dark"],
            font=("Segoe UI", 9),
            borderwidth=0,
        )

        style.configure("TFrame", background=self.colors["bg_main"])
        style.configure(
            "Card.TFrame",
            background=self.colors["bg_frame"],
            borderwidth=1,
            relief="solid",
            bordercolor=self.colors["border"],
        )

        style.configure(
            "TLabelframe",
            background=self.colors["bg_frame"],
            bordercolor=self.colors["border"],
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "TLabelframe.Label",
            font=("Segoe UI", 10, "bold"),
            background=self.colors["header_bg"],
            foreground=self.colors["text_dark"],
            padding=(10, 5),
        )

        style.configure(
            "TButton",
            background=self.colors["accent1"],
            foreground="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            padding=(10, 5),
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "TButton",
            background=[("active", self.colors["accent2"]), ("disabled", "#BDC3C7")],
            foreground=[("disabled", "#FFFFFF")],
        )

        style.configure(
            "Connect.TButton",
            background=self.colors["accent1"],
            foreground="#FFFFFF",
        )
        style.map(
            "Connect.TButton",
            background=[("active", self.colors["accent2"])],
            foreground=[("active", "#FFFFFF")],
        )

        style.configure(
            "Disconnect.TButton",
            background="#95A5A6",
            foreground="#FFFFFF",
        )
        style.map(
            "Disconnect.TButton",
            background=[("active", "#7F8C8D")],
            foreground=[("active", "#FFFFFF")],
        )

        style.configure(
            "Action.TButton",
            background=self.colors["accent1"],
            foreground="#FFFFFF",
        )
        style.map(
            "Action.TButton",
            background=[("active", self.colors["accent2"])],
            foreground=[("active", "#FFFFFF")],
        )

        style.configure(
            "Option.TButton",
            background=self.colors["bg_frame"],
            foreground=self.colors["text_dark"],
            borderwidth=1,
            relief="solid",
            bordercolor=self.colors["border"],
        )
        style.map(
            "Option.TButton",
            background=[("active", self.colors["header_bg"])],
            foreground=[("active", self.colors["text_dark"])],
        )

        style.configure(
            "TEntry",
            fieldbackground="white",
            foreground=self.colors["text_dark"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["border"],
            darkcolor=self.colors["border"],
            borderwidth=1,
            padding=5,
        )
        style.map(
            "TEntry",
            fieldbackground=[("focus", "white")],
            bordercolor=[("focus", self.colors["accent1"])],
        )

        style.configure(
            "TSpinbox",
            fieldbackground="white",
            foreground=self.colors["text_dark"],
            bordercolor=self.colors["border"],
            padding=5,
            arrowsize=13,
        )

        style.configure(
            "TLabel",
            background=self.colors["bg_main"],
            foreground=self.colors["text_dark"],
        )

        style.configure(
            "Header.TLabel",
            font=("Segoe UI", 12, "bold"),
            foreground=self.colors["accent2"],
            padding=10,
        )

        style.configure(
            "Subtitle.TLabel",
            font=("Segoe UI", 10, "italic"),
            foreground=self.colors["accent2"],
        )

        style.configure(
            "Status.TLabel",
            background="#F8F9FA",
            foreground=self.colors["text_dark"],
            font=("Segoe UI", 9),
            padding=8,
            relief="sunken",
            borderwidth=1,
        )

        style.configure(
            "StatusInfo.TLabel", background="#D6EAF8", foreground=self.colors["accent2"]
        )

        style.configure(
            "StatusWarning.TLabel", background="#FDEBD0", foreground="#E67E22"
        )

        style.configure(
            "TRadiobutton",
            background=self.colors["bg_main"],
            foreground=self.colors["text_dark"],
            indicatorcolor="white",
            indicatorbackground="white",
        )
        style.map(
            "TRadiobutton",
            background=[("active", self.colors["bg_main"])],
            indicatorcolor=[("selected", self.colors["accent1"])],
        )

        style.configure(
            "TCheckbutton",
            background=self.colors["bg_main"],
            foreground=self.colors["text_dark"],
        )
        style.map(
            "TCheckbutton",
            background=[("active", self.colors["bg_main"])],
            indicatorcolor=[("selected", self.colors["accent1"])],
        )

        style.configure(
            "TCombobox",
            fieldbackground="white",
            background="white",
            foreground=self.colors["text_dark"],
            arrowcolor=self.colors["accent1"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["border"],
            darkcolor=self.colors["border"],
            borderwidth=1,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "white")],
            selectbackground=[("readonly", self.colors["accent1"])],
            selectforeground=[("readonly", self.colors["text_light"])],
        )

        style.configure(
            "TScrollbar",
            background=self.colors["bg_frame"],
            troughcolor=self.colors["bg_main"],
            arrowcolor=self.colors["text_dark"],
            bordercolor=self.colors["border"],
        )

        style.configure(
            "Treeview",
            background="white",
            foreground=self.colors["text_dark"],
            fieldbackground="white",
            bordercolor=self.colors["border"],
            borderwidth=1,
            padding=0,
        )
        style.configure(
            "Treeview.Heading",
            background=self.colors["header_bg"],
            foreground=self.colors["text_dark"],
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padding=5,
        )
        style.map(
            "Treeview",
            background=[("selected", self.colors["accent1"])],
            foreground=[("selected", self.colors["text_light"])],
        )

        style.configure("TSeparator", background=self.colors["border"])

        self.canvas_style = {
            "bg": "white",
            "border_width": 1,
            "border_color": self.colors["border"],
            "highlight_color": self.colors["accent1"],
        }

    def _setup_output_dir(self):
        try:
            os.makedirs("output", exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error Directorio", f"No se pudo crear 'output/': {e}")

    def _create_widgets(self):
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(container, bg=self.colors["bg_main"])
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

        main_frame = ttk.Frame(canvas, padding="20 20 20 20", style="TFrame")

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor="nw")

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        def configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        main_frame.bind("<Configure>", configure_scroll)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        header = ttk.Label(
            main_frame,
            text="Sistema de Simulación de Scheduling OS",
            style="Header.TLabel",
        )
        header.pack(pady=(0, 15), fill="x")

        top_frame = ttk.Frame(main_frame, style="TFrame")
        top_frame.pack(padx=10, pady=10, fill="x")

        conn_frame = ttk.LabelFrame(
            top_frame, text="Conexión al Servidor", padding="15 10 15 15"
        )
        conn_frame.pack(side=tk.LEFT, padx=10, pady=5, fill="y")

        ttk.Label(conn_frame, text="IP:").grid(
            row=0, column=0, padx=5, pady=8, sticky="w"
        )
        ttk.Entry(conn_frame, textvariable=self.server_addr, width=15).grid(
            row=0, column=1, padx=5, pady=8, sticky="we"
        )
        ttk.Label(conn_frame, text="Puerto:").grid(
            row=1, column=0, padx=5, pady=8, sticky="w"
        )
        ttk.Entry(conn_frame, textvariable=self.server_port, width=7).grid(
            row=1, column=1, padx=5, pady=8, sticky="w"
        )

        self.connect_button = ttk.Button(
            conn_frame,
            text="Conectar",
            command=self.connect_server,
            style="Connect.TButton",
        )
        self.connect_button.grid(row=2, column=0, padx=5, pady=8, sticky="we")

        self.disconnect_button = ttk.Button(
            conn_frame,
            text="Desconectar",
            command=self.disconnect_server,
            state=tk.DISABLED,
            style="Disconnect.TButton",
        )
        self.disconnect_button.grid(row=2, column=1, padx=5, pady=8, sticky="we")

        client_config_frame = ttk.LabelFrame(
            top_frame, text="Configuración del Cliente", padding="15 10 15 15"
        )
        client_config_frame.pack(side=tk.LEFT, padx=10, pady=5, fill="y")

        ttk.Radiobutton(
            client_config_frame,
            text="Threads",
            variable=self.processing_mode_var,
            value="threads",
        ).grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(
            client_config_frame,
            text="Forks",
            variable=self.processing_mode_var,
            value="forks",
        ).grid(row=0, column=1, sticky="w", padx=8, pady=4)

        ttk.Label(client_config_frame, text="Cantidad:").grid(
            row=1, column=0, padx=8, pady=8, sticky="w"
        )
        ttk.Spinbox(
            client_config_frame,
            from_=1,
            to=16,
            textvariable=self.worker_count_var,
            width=5,
        ).grid(row=1, column=1, padx=8, pady=8, sticky="w")

        self.apply_config_button = ttk.Button(
            client_config_frame,
            text="Aplicar Config.",
            command=self.send_client_config,
            state=tk.DISABLED,
            style="Action.TButton",
        )
        self.apply_config_button.grid(
            row=2, column=0, columnspan=2, padx=5, pady=8, sticky="we"
        )

        sub_frame = ttk.LabelFrame(
            top_frame, text="Suscripción a Eventos", padding="15 10 15 15"
        )
        sub_frame.pack(side=tk.LEFT, padx=10, pady=5, fill="y")

        ttk.Label(sub_frame, text="Evento:").grid(
            row=0, column=0, padx=8, pady=8, sticky="w"
        )
        ttk.Entry(sub_frame, textvariable=self.event_name_var, width=15).grid(
            row=0, column=1, padx=8, pady=8, sticky="we"
        )

        sub_buttons_frame = ttk.Frame(sub_frame)
        sub_buttons_frame.grid(
            row=1, column=0, columnspan=2, padx=5, pady=8, sticky="we"
        )

        self.sub_button = ttk.Button(
            sub_buttons_frame,
            text="Suscribir",
            command=self.subscribe_event,
            state=tk.DISABLED,
            style="Action.TButton",
        )
        self.sub_button.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 2))

        self.unsub_button = ttk.Button(
            sub_buttons_frame,
            text="Desuscribir",
            command=self.unsubscribe_event,
            state=tk.DISABLED,
            style="Action.TButton",
        )
        self.unsub_button.pack(side=tk.RIGHT, fill="x", expand=True, padx=(2, 0))

        ttk.Label(sub_frame, text="Eventos suscritos:").grid(
            row=3, column=0, padx=8, pady=(15, 5), sticky="w"
        )

        self.unsub_combobox = ttk.Combobox(
            sub_frame,
            textvariable=self.selected_event_unsub,
            state="readonly",
            width=15,
        )
        self.unsub_combobox.grid(row=3, column=1, padx=8, pady=(15, 5), sticky="we")
        self.unsub_combobox.bind(
            "<<ComboboxSelected>>", self.on_event_selected_for_unsub
        )

        self.subscribed_label = ttk.Label(
            sub_frame,
            text="Suscrito a: Ninguno",
            width=30,
            wraplength=180,
            style="StatusInfo.TLabel",
            padding=(8, 5),
        )
        self.subscribed_label.grid(
            row=4, column=0, columnspan=2, padx=5, pady=(10, 5), sticky="we"
        )

        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=15)

        mid_frame = ttk.Frame(main_frame, style="TFrame")
        mid_frame.pack(padx=10, pady=10, fill="x")

        self.files_select_frame = ttk.LabelFrame(
            mid_frame, text="Archivos Asignados", padding="15 10 15 15"
        )
        self.files_select_frame.pack(
            side=tk.LEFT, padx=10, pady=5, fill="both", expand=True
        )

        self.files_canvas = tk.Canvas(
            self.files_select_frame,
            height=120,
            bg=self.canvas_style["bg"],
            highlightthickness=self.canvas_style["border_width"],
            highlightbackground=self.canvas_style["border_color"],
        )
        self.files_scrollbar = ttk.Scrollbar(
            self.files_select_frame, orient="vertical", command=self.files_canvas.yview
        )
        self.scrollable_files_frame = ttk.Frame(self.files_canvas, style="TFrame")
        self.scrollable_files_frame.bind(
            "<Configure>",
            lambda e: self.files_canvas.configure(
                scrollregion=self.files_canvas.bbox("all")
            ),
        )
        self.files_canvas_window = self.files_canvas.create_window(
            (0, 0), window=self.scrollable_files_frame, anchor="nw"
        )
        self.files_canvas.configure(yscrollcommand=self.files_scrollbar.set)
        self.files_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.files_scrollbar.pack(side="right", fill="y", pady=5)

        self.confirm_files_button = ttk.Button(
            self.files_select_frame,
            text="Definir Parámetros",
            command=self.setup_parameter_input_ui,
            state=tk.DISABLED,
            style="Action.TButton",
        )
        self.confirm_files_button.pack(side=tk.BOTTOM, pady=12, padx=5, fill="x")

        self.params_outer_frame = ttk.LabelFrame(
            mid_frame, text="Parámetros de Simulación", padding="15 10 15 15"
        )
        self.params_outer_frame.pack(
            side=tk.LEFT, padx=10, pady=5, fill="both", expand=True
        )

        self.params_canvas = tk.Canvas(
            self.params_outer_frame,
            height=120,
            bg=self.canvas_style["bg"],
            highlightthickness=self.canvas_style["border_width"],
            highlightbackground=self.canvas_style["border_color"],
        )
        self.params_scrollbar = ttk.Scrollbar(
            self.params_outer_frame, orient="vertical", command=self.params_canvas.yview
        )
        self.scrollable_params_frame = ttk.Frame(self.params_canvas)
        self.scrollable_params_frame.bind(
            "<Configure>",
            lambda e: self.params_canvas.configure(
                scrollregion=self.params_canvas.bbox("all")
            ),
        )
        self.params_canvas_window = self.params_canvas.create_window(
            (0, 0), window=self.scrollable_params_frame, anchor="nw"
        )
        self.params_canvas.configure(yscrollcommand=self.params_scrollbar.set)
        self.params_canvas.pack(side=tk.LEFT, fill="both", expand=True, padx=5, pady=5)
        self.params_scrollbar.pack(side=tk.RIGHT, fill="y", pady=5)

        sim_config_frame = ttk.LabelFrame(
            mid_frame, text="Configuración de Simulación", padding="15 10 15 15"
        )
        sim_config_frame.pack(side=tk.LEFT, padx=10, pady=5, fill="y")

        ttk.Label(sim_config_frame, text="Algoritmo:").grid(
            row=0, column=0, padx=8, pady=10, sticky="w"
        )
        self.algo_combo = ttk.Combobox(
            sim_config_frame,
            textvariable=self.selected_algorithm_var,
            values=list(AVAILABLE_SCHEDULERS.keys()),
            state="readonly",
            width=12,
        )
        self.algo_combo.grid(row=0, column=1, padx=8, pady=10, sticky="we")
        self.algo_combo.bind("<<ComboboxSelected>>", self.change_scheduler_sim)

        self.quantum_label = ttk.Label(sim_config_frame, text="Quantum (RR):")
        self.quantum_spinbox = ttk.Spinbox(
            sim_config_frame, from_=1, to=10, textvariable=self.quantum_var, width=5
        )

        self.start_sim_button = ttk.Button(
            sim_config_frame,
            text="Iniciar Simulación",
            command=self.start_simulation_visual,
            state=tk.DISABLED,
            style="Action.TButton",
        )
        self.start_sim_button.grid(
            row=2, column=0, columnspan=2, padx=5, pady=10, sticky="we"
        )

        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=15)

        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.tabs = ttk.Notebook(bottom_frame)
        self.tabs.pack(fill="both", expand=True, padx=5, pady=5)

        self.tab_proc_table = ttk.Frame(self.tabs)
        self.tabs.add(self.tab_proc_table, text="Tabla de Procesos")

        columns = (
            "pid_sim",
            "filename",
            "arrival",
            "burst",
            "start",
            "completion",
            "turnaround",
            "waiting",
            "state",
            "turnaround_formula",
            "waiting_formula",
        )
        self.proc_tree_sim = ttk.Treeview(
            self.tab_proc_table, columns=columns, show="headings", height=10
        )

        self.proc_tree_sim.heading("turnaround_formula", text="TAT operación")
        self.proc_tree_sim.column("turnaround_formula", width=120, anchor="center")

        self.proc_tree_sim.heading("pid_sim", text="PID")
        self.proc_tree_sim.column("pid_sim", width=40, anchor="center")

        self.proc_tree_sim.heading("filename", text="Archivo")
        self.proc_tree_sim.column("filename", width=150, anchor="w")

        self.proc_tree_sim.heading("arrival", text="Llegada")
        self.proc_tree_sim.column("arrival", width=70, anchor="center")

        self.proc_tree_sim.heading("burst", text="Ráfaga")
        self.proc_tree_sim.column("burst", width=70, anchor="center")

        self.proc_tree_sim.heading("start", text="Inicio")
        self.proc_tree_sim.column("start", width=70, anchor="center")

        self.proc_tree_sim.heading("completion", text="Finalización")
        self.proc_tree_sim.column("completion", width=90, anchor="center")

        self.proc_tree_sim.heading("turnaround", text="Turnaround")
        self.proc_tree_sim.column("turnaround", width=90, anchor="center")

        self.proc_tree_sim.heading("waiting", text="Espera")
        self.proc_tree_sim.column("waiting", width=70, anchor="center")

        self.proc_tree_sim.heading("state", text="Estado")
        self.proc_tree_sim.column("state", width=80, anchor="center")

        table_scroll_y = ttk.Scrollbar(
            self.tab_proc_table, orient="vertical", command=self.proc_tree_sim.yview
        )
        table_scroll_x = ttk.Scrollbar(
            self.tab_proc_table, orient="horizontal", command=self.proc_tree_sim.xview
        )
        self.proc_tree_sim.configure(
            yscrollcommand=table_scroll_y.set, xscrollcommand=table_scroll_x.set
        )

        self.proc_tree_sim.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        table_scroll_y.grid(row=0, column=1, sticky="ns", pady=5)
        table_scroll_x.grid(row=1, column=0, sticky="ew", padx=5)

        self.tab_proc_table.grid_rowconfigure(0, weight=1)
        self.tab_proc_table.grid_columnconfigure(0, weight=1)

        avg_frame = ttk.Frame(
            self.tab_proc_table, padding="10 10 10 10", style="Card.TFrame"
        )
        avg_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=10)

        ttk.Label(
            avg_frame, text="Métricas de Rendimiento:", style="Subtitle.TLabel"
        ).pack(side=tk.LEFT, padx=10)

        self.avg_turnaround_label = ttk.Label(
            avg_frame,
            text="Turnaround Promedio: 0.00",
            style="StatusInfo.TLabel",
            padding=(8, 5),
        )
        self.avg_turnaround_label.pack(side=tk.LEFT, padx=10)

        self.avg_waiting_label = ttk.Label(
            avg_frame,
            text="Tiempo de Espera Promedio: 0.00",
            style="StatusInfo.TLabel",
            padding=(8, 5),
        )
        self.avg_waiting_label.pack(side=tk.LEFT, padx=10)

        self.tab_gantt = ttk.Frame(self.tabs)
        self.tabs.add(self.tab_gantt, text="Diagrama de Gantt")

        self.gantt_frame = ttk.Frame(self.tab_gantt, padding="10 10 10 10")
        self.gantt_frame.pack(fill="both", expand=True, padx=5, pady=5)

        gantt_label = ttk.Label(
            self.gantt_frame,
            text="Simulación de Ejecución de Procesos",
            style="Header.TLabel",
        )
        gantt_label.pack(pady=10)

        gantt_info_frame = ttk.Frame(self.gantt_frame, style="Card.TFrame")
        gantt_info_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(
            gantt_info_frame,
            text="Cada barra representa un proceso en ejecución. Los números indican el PID del proceso.",
            style="Subtitle.TLabel",
            padding=(10, 5),
        ).pack(side=tk.LEFT, padx=10)

        gantt_canvas_frame = ttk.Frame(self.gantt_frame, style="Card.TFrame")
        gantt_canvas_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.gantt_canvas = tk.Canvas(
            gantt_canvas_frame,
            bg="white",
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )

        self.gantt_x_scrollbar = ttk.Scrollbar(
            gantt_canvas_frame, orient="horizontal", command=self.gantt_canvas.xview
        )
        self.gantt_y_scrollbar = ttk.Scrollbar(
            gantt_canvas_frame, orient="vertical", command=self.gantt_canvas.yview
        )

        self.gantt_canvas.configure(
            xscrollcommand=self.gantt_x_scrollbar.set,
            yscrollcommand=self.gantt_y_scrollbar.set,
        )

        self.gantt_y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.gantt_x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.gantt_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tab_results = ttk.Frame(self.tabs)
        self.tabs.add(self.tab_results, text="Resultados")

        results_label = ttk.Label(
            self.tab_results,
            text="Resultados del Servidor (Vista Previa del CSV)",
            style="Header.TLabel",
        )
        results_label.pack(pady=10)

        columns_csv = (
            "pid",
            "filename",
            "nombres",
            "lugares",
            "dates",
            "wordcount",
            "status",
            "error",
        )
        self.results_tree = ttk.Treeview(
            self.tab_results, columns=columns_csv, show="headings", height=10
        )

        self.results_tree.heading("pid", text="PID Servidor")
        self.results_tree.column("pid", width=80, anchor="center")

        self.results_tree.heading("filename", text="Archivo")
        self.results_tree.column("filename", width=150, anchor="w")

        self.results_tree.heading("nombres", text="Nombres")
        self.results_tree.column("nombres", width=150, anchor="w")

        self.results_tree.heading("lugares", text="Lugares")
        self.results_tree.column("lugares", width=150, anchor="w")

        self.results_tree.heading("dates", text="Fechas")
        self.results_tree.column("dates", width=120, anchor="w")

        self.results_tree.heading("wordcount", text="# Palabras")
        self.results_tree.column("wordcount", width=80, anchor="center")

        self.results_tree.heading("status", text="Estado")
        self.results_tree.column("status", width=80, anchor="center")

        self.results_tree.heading("error", text="Error")
        self.results_tree.column("error", width=150, anchor="w")

        results_scroll_y = ttk.Scrollbar(
            self.tab_results, orient="vertical", command=self.results_tree.yview
        )
        results_scroll_x = ttk.Scrollbar(
            self.tab_results, orient="horizontal", command=self.results_tree.xview
        )
        self.results_tree.configure(
            yscrollcommand=results_scroll_y.set, xscrollcommand=results_scroll_x.set
        )

        self.results_tree.pack(fill="both", expand=True, side=tk.LEFT, padx=5, pady=5)
        results_scroll_y.pack(fill="y", side=tk.RIGHT, pady=5)
        results_scroll_x.pack(fill="x", side=tk.BOTTOM, padx=5)

        button_frame = ttk.Frame(self.tab_results, padding="0 10 0 0")
        button_frame.pack(fill="x", padx=5, pady=5)

        self.save_csv_button = ttk.Button(
            button_frame,
            text="Guardar Resultados a CSV",
            command=self.save_results_to_csv,
            state=tk.DISABLED,
            style="Action.TButton",
        )
        self.save_csv_button.pack(pady=5)

        self.status_frame = ttk.Frame(main_frame, style="Card.TFrame")
        self.status_frame.pack(fill="x", padx=10, pady=10)

        self.status_label = ttk.Label(
            self.status_frame,
            text="Desconectado. Inicie conexión con el servidor.",
            style="Status.TLabel",
        )
        self.status_label.pack(fill="x")

        self.change_scheduler_sim()

    # --- Métodos de Conexión y Comunicación ---

    def connect_server(self):
        """Intenta conectar el cliente al servidor."""
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
            self.status_label.config(text=f"Conectado a {ip}:{port}")

            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
            self.apply_config_button.config(state=tk.NORMAL)
            self.sub_button.config(state=tk.NORMAL)
            self.unsub_button.config(state=tk.NORMAL)

            self.receive_thread = threading.Thread(
                target=self.listen_to_server, daemon=True
            )
            self.receive_thread.start()
            self.send_client_config()

        except ValueError:
            messagebox.showerror("Error", "Puerto inválido.")
        except socket.error as e:
            messagebox.showerror("Error de Conexión", f"No se pudo conectar: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error inesperado al conectar: {e}")

    def disconnect_server(self):
        """Desconecta el cliente del servidor y resetea la GUI."""
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
            self.status_label.config(text="Desconectado.")

            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
            self.apply_config_button.config(state=tk.DISABLED)
            self.sub_button.config(state=tk.DISABLED)
            self.unsub_button.config(state=tk.DISABLED)

            self.subscribed_events.clear()
            self.update_subscribed_label()
            self.clear_file_selection_ui()
            self.clear_parameter_input_ui()

    def send_message(self, message):
        """Envía un mensaje JSON al servidor."""
        if self.connected and self.client_socket:
            try:
                payload = json.dumps(message) + "\n"
                self.client_socket.sendall(payload.encode("utf-8"))
            except (BrokenPipeError, ConnectionResetError):
                self.disconnect_server()
                messagebox.showerror(
                    "Error de Red", "Conexión perdida con el servidor."
                )
            except Exception as e:
                messagebox.showerror(
                    "Error de Envío", f"No se pudo enviar mensaje: {e}"
                )
        else:
            messagebox.showwarning("Envío", "No estás conectado.")

    def listen_to_server(self):
        """Hilo para escuchar mensajes del servidor."""
        buffer = ""
        while self.connected and self.client_socket:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    if self.connected:
                        self.message_queue.put(
                            {"type": "ERROR", "payload": "Servidor desconectado."}
                        )
                    break

                buffer += data.decode("utf-8")

                while "\n" in buffer:
                    message_str, buffer = buffer.split("\n", 1)
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
            except socket.error as e:
                if self.connected:
                    self.message_queue.put(
                        {"type": "ERROR", "payload": f"Error de socket: {e}"}
                    )
                break
            except Exception as e:
                if self.connected:
                    self.message_queue.put(
                        {
                            "type": "ERROR",
                            "payload": f"Error inesperado en listener: {e}",
                        }
                    )
                break

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
            self.root.after(100, self.check_message_queue)

    def handle_server_message(self, message):
        """Procesa un mensaje recibido del servidor."""
        try:
            msg_type = message.get("type", "")
            payload = message.get("payload", {})

            if msg_type == "WELCOME":
                server_info = payload.get("server_info", {})
                version = server_info.get("version", "desconocida")
                self.status_label.config(
                    text=f"Conectado. Servidor v{version}. Listo para suscribir."
                )
                self.sub_button.config(state=tk.NORMAL)

            elif msg_type == "ACK_CONFIG":
                if payload.get("status") == "success":
                    cfg = payload.get("config")
                    self.status_label.config(
                        text=f"Config. aplicada por servidor: {cfg}"
                    )
                    self.num_workers_for_sim_display = cfg.get("count", 2)
                else:
                    messagebox.showwarning(
                        "Config Rechazada",
                        f"El servidor rechazó la configuración: {payload.get('message', 'Sin detalles')}",
                    )

            elif msg_type == "ACK_SUB":
                event_name = payload
                if isinstance(event_name, str) and event_name:
                    self.subscribed_events.add(event_name)
                    print(
                        f"Confirmación de suscripción recibida para evento: {event_name}"
                    )
                    self.status_label.config(
                        text=f"Confirmación suscripción a '{event_name}' recibida."
                    )
                    self.update_subscribed_label()
                else:
                    print(f"ACK_SUB recibido con payload inesperado: {payload}")
                    self.status_label.config(
                        text="Confirmación suscripción recibida (detalle incompleto)."
                    )

            elif msg_type == "ACK_UNSUB":
                event_name = payload
                if isinstance(event_name, str) and event_name:
                    if event_name in self.subscribed_events:
                        self.subscribed_events.remove(event_name)
                    print(
                        f"Confirmación de desuscripción recibida para evento: {event_name}"
                    )
                    self.status_label.config(
                        text=f"Desuscripción de '{event_name}' confirmada."
                    )
                    self.update_subscribed_label()
                else:
                    print(f"ACK_UNSUB recibido con payload inesperado: {payload}")
                    self.status_label.config(
                        text="Confirmación desuscripción recibida (detalle incompleto)."
                    )

            elif msg_type == "START_PROCESSING":
                self.server_assigned_files = payload.get("files", [])
                event = payload.get("event")
                num_files = len(self.server_assigned_files)
                self.status_label.config(
                    text=f"Servidor inició proc. evento '{event}'. Archivos: {num_files}"
                )
                if self.server_assigned_files:
                    self.display_file_selection_ui()

            elif msg_type == "PROCESSING_COMPLETE":
                event = payload.get("event")
                status = payload.get("status")
                self.status_label.config(
                    text=f"Servidor completó proc. '{event}'. Estado: {status}"
                )

                if status == "success":
                    self.server_results_for_csv = payload.get("results", [])
                    self.display_server_results()
                    self.save_csv_button.config(state=tk.NORMAL)
                else:
                    messagebox.showerror(
                        "Error Procesamiento",
                        f"Error en procesamiento: {payload.get('message', 'Sin detalles')}",
                    )

            elif msg_type == "SERVER_EXIT":
                messagebox.showinfo(
                    "Servidor Cerrando",
                    "El servidor está cerrando. Se desconectará ahora.",
                )
                self.disconnect_server()

            else:
                print(f"Mensaje desconocido recibido: {msg_type}")

        except json.JSONDecodeError:
            print(f"Error decodificando JSON: {message}")
        except Exception as e:
            print(f"Error manejando mensaje del servidor: {e}")

    def on_closing(self):
        """Manejador para cierre de ventana."""
        if messagebox.askokcancel("Salir", "¿Seguro que quieres salir?"):
            if self.connected:
                try:
                    self.disconnect_server()
                except:
                    pass
            self.root.destroy()

    # --- Métodos de Configuración Cliente y Suscripción ---

    def send_client_config(self):
        """Envía la configuración de workers al servidor."""
        mode = self.processing_mode_var.get()
        try:
            count = int(self.worker_count_var.get())
            if count <= 0:
                messagebox.showerror("Error Config", "Cantidad debe ser positiva.")
                return

            self.num_workers_for_sim_display = count

            config_payload = {"mode": mode, "count": count}
            self.send_message({"type": "SET_CONFIG", "payload": config_payload})
        except ValueError:
            messagebox.showerror("Error Config", "Cantidad de workers inválida.")

    def subscribe_event(self):
        """Suscribe al cliente a un evento en el servidor."""
        event = self.event_name_var.get()
        if not event:
            messagebox.showwarning("Suscripción", "Ingresa un nombre de evento.")
            return
        self.send_message({"type": "SUB", "payload": event})

    def unsubscribe_event(self):
        """Desuscribe al cliente de un evento específico."""
        event = self.selected_event_unsub.get()

        if not event:
            event = self.event_name_var.get()

        if not event:
            messagebox.showwarning(
                "Desuscripción", "Selecciona o ingresa un nombre de evento."
            )
            return

        if event not in self.subscribed_events:
            messagebox.showwarning(
                "Desuscripción", f"No estás suscrito al evento '{event}'."
            )
            return

        self.send_message({"type": "UNSUB", "payload": event})

    def on_event_selected_for_unsub(self, event=None):
        """Cuando se selecciona un evento en el combobox de desuscripción."""
        selected = self.selected_event_unsub.get()
        if selected:
            self.event_name_var.set(selected)

    def update_subscribed_label(self):
        """Actualiza la etiqueta que muestra las suscripciones activas."""
        if not self.subscribed_events:
            self.subscribed_label.config(text="Suscrito a: Ninguno")
            self.unsub_combobox["values"] = []
            self.unsub_combobox.set("")
        else:
            events_list = sorted(list(self.subscribed_events))
            events_text = ", ".join(events_list)
            self.subscribed_label.config(text=f"Suscrito a: {events_text}")
            self.unsub_combobox["values"] = events_list
            if not self.selected_event_unsub.get() in events_list:
                self.unsub_combobox.set("")

    # --- UI Selección Archivos y Parámetros Simulación ---

    def display_file_selection_ui(self):
        """Muestra checkboxes para seleccionar archivos para la simulación."""
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
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(
                self.scrollable_files_frame, text=filename, variable=var
            )
            cb.pack(anchor="w", padx=5, pady=1)
            self.files_for_simulation_vars[filename] = var

        self.confirm_files_button.config(state=tk.NORMAL)
        self.root.update_idletasks()
        self.files_canvas.config(scrollregion=self.files_canvas.bbox("all"))
        num_files = len(self.server_assigned_files)
        new_height = min(max(num_files * 25, 50), 150)
        self.files_canvas.config(height=new_height)

    def clear_file_selection_ui(self):
        """Limpia los checkboxes de selección de archivos."""
        for widget in self.scrollable_files_frame.winfo_children():
            widget.destroy()
        self.confirm_files_button.config(state=tk.DISABLED)

    def setup_parameter_input_ui(self):
        """Configura la UI para la entrada manual de parámetros de simulación."""
        self.clear_parameter_input_ui()
        self.processes_to_simulate.clear()
        self.process_pid_counter_sim = 0
        self.proc_tree_sim.delete(*self.proc_tree_sim.get_children())

        selected_files = [
            fname for fname, var in self.files_for_simulation_vars.items() if var.get()
        ]

        if not selected_files:
            messagebox.showinfo(
                "Simulación", "No se seleccionaron archivos para simular."
            )
            self.start_sim_button.config(state=tk.DISABLED)
            return

        header_frame = ttk.Frame(self.scrollable_params_frame)
        header_frame.pack(fill="x", pady=2)
        ttk.Label(header_frame, text="Archivo", width=20, relief=tk.RIDGE).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Label(header_frame, text="Llegada", width=7, relief=tk.RIDGE).pack(
            side=tk.LEFT, padx=1
        )
        ttk.Label(header_frame, text="Ráfaga", width=7, relief=tk.RIDGE).pack(
            side=tk.LEFT, padx=1
        )
        self.priority_header_label = ttk.Label(
            header_frame, text="Prioridad", width=7, relief=tk.RIDGE
        )

        self.process_params_entries.clear()

        for filename in selected_files:
            pid_sim = self.process_pid_counter_sim
            self.process_pid_counter_sim += 1

            entry_frame = ttk.Frame(self.scrollable_params_frame)
            entry_frame.pack(fill="x", pady=1)

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
            priority_entry = ttk.Entry(entry_frame, textvariable=priority_var, width=7)

            self.process_params_entries[pid_sim] = {
                "filename": filename,
                "arrival_var": arrival_var,
                "burst_var": burst_var,
                "priority_var": priority_var,
                "priority_entry_widget": priority_entry,
            }

        self.start_sim_button.config(state=tk.NORMAL)
        self.change_scheduler_sim()
        self.root.update_idletasks()
        self.params_canvas.config(scrollregion=self.params_canvas.bbox("all"))
        num_selected = len(selected_files)
        new_param_height = min(max(num_selected * 30, 50), 150)
        self.params_canvas.config(height=new_param_height)
        self.selected_files_for_processing = selected_files

    def clear_parameter_input_ui(self):
        """Limpia la UI de entrada de parámetros de simulación."""
        for widget in self.scrollable_params_frame.winfo_children():
            widget.destroy()
        self.start_sim_button.config(state=tk.DISABLED)

    # --- Simulación Visual ---

    def change_scheduler_sim(self, event=None):
        """Cambia el algoritmo de scheduling para la simulación visual."""
        algo = self.selected_algorithm_var.get()
        scheduler_class = AVAILABLE_SCHEDULERS.get(algo)
        show_priority = False
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
            else:
                self.scheduler_sim = scheduler_class()
        else:
            messagebox.showerror("Error", f"Algoritmo {algo} no implementado.")
            self.selected_algorithm_var.set("FCFS")
            self.scheduler_sim = SchedulerFCFS()

        if hasattr(self, "priority_header_label"):
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

        if show_quantum:
            self.quantum_label.grid(row=1, column=0, padx=5, pady=2, sticky="w")
            self.quantum_spinbox.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        else:
            self.quantum_label.grid_forget()
            self.quantum_spinbox.grid_forget()

        self.status_label.config(text=f"Algoritmo simulación: {self.scheduler_sim}")
        self.root.update_idletasks()
        if hasattr(self, "scrollable_params_frame"):
            self.params_canvas.config(scrollregion=self.params_canvas.bbox("all"))

    def start_simulation_visual(self):
        """Inicia o pausa la simulación visual de scheduling."""
        self.processes_to_simulate.clear()
        self.proc_tree_sim.delete(*self.proc_tree_sim.get_children())
        self.ready_queue_sim.clear()
        self.running_processes_sim.clear()
        self.completed_processes_sim.clear()
        self.gantt_canvas.delete("all")
        self.simulation_time_sim = 0

        try:
            self.num_workers_for_sim_display = int(self.worker_count_var.get())
        except ValueError:
            pass

        valid_input = True

        for pid_sim, params in self.process_params_entries.items():
            try:
                filename = params["filename"]
                arrival = int(params["arrival_var"].get())
                burst = int(params["burst_var"].get())
                priority = int(params["priority_var"].get())

                if burst <= 0:
                    msg = f"Ráfaga para '{filename}' debe ser positiva."
                    messagebox.showerror("Error Simulación", msg)
                    valid_input = False
                    break

                proc = Process(pid_sim, filename, arrival, burst, priority)
                self.processes_to_simulate.append(proc)
                self.proc_tree_sim.insert(
                    "",
                    tk.END,
                    iid=str(pid_sim),
                    values=(
                        pid_sim,
                        filename,
                        arrival,
                        burst,
                        -1,
                        -1,
                        -1,
                        -1,
                        "New",
                        "N/A",
                        "N/A",
                    ),
                )
            except ValueError:
                messagebox.showerror(
                    "Error Simulación", "Entrada inválida para parámetros."
                )
                valid_input = False
                break

        if not valid_input or not self.processes_to_simulate:
            self.start_sim_button.config(state=tk.NORMAL)
            return

        if not self.simulation_running_sim:
            self.simulation_running_sim = True
            self.start_sim_button.config(text="Pausar Sim. Visual")
            self.status_label.config(text="Simulación visual iniciada...")
            self.simulation_step_visual()

            if hasattr(self, "selected_files_for_processing"):
                self.send_message(
                    {
                        "type": "PROCESS_FILES",
                        "payload": {
                            "event": self.event_name_var.get(),
                            "files": self.selected_files_for_processing,
                        },
                    }
                )

        else:
            self.simulation_running_sim = False
            self.start_sim_button.config(text="Reanudar Sim. Visual")
            self.status_label.config(text="Simulación visual pausada.")

    def simulation_step_visual(self):
        """Ejecuta un paso (tick) de la simulación visual."""
        if not self.simulation_running_sim:
            return

        current_time = self.simulation_time_sim
        self.status_label.config(text=f"Tiempo Sim: {current_time}")

        remaining_to_schedule = []
        for proc in self.processes_to_simulate:
            if proc.arrival_time <= current_time:
                proc.state = "Ready"
                self.ready_queue_sim.append(proc)
                self.update_process_table_sim(proc.pid, {"state": "Ready"})
            else:
                remaining_to_schedule.append(proc)
        self.processes_to_simulate = remaining_to_schedule

        temp_running = []
        for proc in self.running_processes_sim:
            if proc.remaining_burst_time <= 0:
                self.handle_process_completion_sim(proc, current_time)
            else:
                temp_running.append(proc)
        self.running_processes_sim = temp_running

        available_threads_sim = self.num_workers_for_sim_display - len(
            self.running_processes_sim
        )

        if (
            isinstance(self.scheduler_sim, SchedulerHRRN)
            or isinstance(self.scheduler_sim, SchedulerSJF)
            or isinstance(self.scheduler_sim, SchedulerFCFS)
            or isinstance(self.scheduler_sim, SchedulerPriorityNP)
        ):
            if not self.running_processes_sim and self.ready_queue_sim:
                arrived = [
                    p for p in self.ready_queue_sim if p.arrival_time <= current_time
                ]
                if not arrived:
                    next_arrival = min(p.arrival_time for p in self.ready_queue_sim)
                    self.simulation_time_sim = next_arrival
                    self.root.after(
                        self.simulation_update_ms, self.simulation_step_visual
                    )
                    return

                next_process = self.scheduler_sim.schedule(
                    self.ready_queue_sim,
                    self.simulation_time_sim,
                    self.running_processes_sim,
                    1,
                )
                if next_process:
                    next_process.state = "Running"
                    if next_process.start_time == -1:
                        next_process.start_time = self.simulation_time_sim
                    self.running_processes_sim.append(next_process)
                    self.update_process_table_sim(
                        next_process.pid,
                        {"state": "Running", "start": next_process.start_time},
                    )
                    next_process.remaining_burst_time = 0
                    for t in range(
                        next_process.start_time,
                        next_process.start_time + next_process.burst_time,
                    ):
                        self.update_gantt_display_sim(t, [(next_process.pid, 0)])
                    self.handle_process_completion_sim(
                        next_process, next_process.start_time + next_process.burst_time
                    )
                    self.simulation_time_sim = (
                        next_process.start_time + next_process.burst_time
                    )
                    self.root.after(
                        self.simulation_update_ms, self.simulation_step_visual
                    )
                    return
        else:
            while available_threads_sim > 0 and self.ready_queue_sim:
                next_process = self.scheduler_sim.schedule(
                    self.ready_queue_sim,
                    current_time,
                    self.running_processes_sim,
                    available_threads_sim,
                )
                if next_process:
                    next_process.state = "Running"
                    if next_process.start_time == -1:
                        next_process.start_time = current_time
                    self.running_processes_sim.append(next_process)
                    self.update_process_table_sim(
                        next_process.pid,
                        {"state": "Running", "start": next_process.start_time},
                    )
                    available_threads_sim -= 1
                else:
                    break

        gantt_current_tick_sim = []
        processes_to_requeue_rr = []

        for i, proc in enumerate(self.running_processes_sim):
            proc.remaining_burst_time -= 1
            gantt_current_tick_sim.append((proc.pid, i))
            self.update_process_table_sim(
                proc.pid, {"Restante": proc.remaining_burst_time}
            )

            if isinstance(self.scheduler_sim, SchedulerRR):
                if not hasattr(proc, "ticks_in_current_burst"):
                    proc.ticks_in_current_burst = 0
                proc.ticks_in_current_burst += 1

                if (
                    proc.ticks_in_current_burst >= self.scheduler_sim.quantum
                    and proc.remaining_burst_time > 0
                ):
                    processes_to_requeue_rr.append(proc)

        if processes_to_requeue_rr:
            for proc_rr in processes_to_requeue_rr:
                self.running_processes_sim.remove(proc_rr)
                proc_rr.state = "Ready"
                proc_rr.ticks_in_current_burst = 0
                self.ready_queue_sim.append(proc_rr)
                self.update_process_table_sim(proc_rr.pid, {"state": "Ready"})

        if gantt_current_tick_sim:
            self.update_gantt_display_sim(current_time, gantt_current_tick_sim)

        self.simulation_time_sim += 1

        if (
            not self.processes_to_simulate
            and not self.ready_queue_sim
            and not self.running_processes_sim
        ):
            self.simulation_running_sim = False
            self.start_sim_button.config(text="Sim. Visual Completa", state=tk.DISABLED)
            self.status_label.config(
                text=f"Sim. visual completada en {current_time} ticks."
            )
            self.calculate_and_display_averages_sim()
        else:
            self.root.after(self.simulation_update_ms, self.simulation_step_visual)

    def handle_process_completion_sim(self, process, completion_time):
        """Maneja la finalización de un proceso en la simulación visual."""
        process.state = "Terminated"
        process.completion_time = completion_time
        process.turnaround_time = process.completion_time - process.arrival_time
        process.waiting_time = process.turnaround_time - process.burst_time

        process.turnaround_formula = (
            f"{process.completion_time} - {process.arrival_time} = "
            f"{process.turnaround_time}"
        )
        process.waiting_formula = (
            f"{process.turnaround_time} - {process.burst_time} = "
            f"{process.waiting_time}"
        )

        self.completed_processes_sim.append(process)
        self.update_process_table_sim(
            process.pid,
            {
                "state": "Terminated",
                "completion": process.completion_time,
                "turnaround": process.turnaround_time,
                "waiting": process.waiting_time,
                "turnaround_formula": process.turnaround_formula,
                "waiting_formula": process.waiting_formula,
                "burst": process.burst_time,
                "start": process.start_time,
                "Restante": 0,
            },
        )

    def update_process_table_sim(self, pid_sim, updates):
        """Actualiza una fila en la tabla de procesos con los datos proporcionados."""
        item_id = None
        for item in self.proc_tree_sim.get_children():
            if self.proc_tree_sim.item(item, "values")[0] == str(pid_sim):
                item_id = item
                break

        if item_id is None:
            values = [pid_sim]
            for key in [
                "filename",
                "state",
                "arrival",
                "burst",
                "remaining_burst_time",
                "start",
                "completion",
                "turnaround",
                "waiting",
            ]:
                values.append(updates.get(key, ""))
            self.proc_tree_sim.insert("", "end", values=values)
        else:
            current_values = list(self.proc_tree_sim.item(item_id, "values"))

            column_map = {
                "filename": 1,
                "arrival": 2,
                "burst": 3,
                "start": 4,
                "completion": 5,
                "turnaround": 6,
                "waiting": 7,
                "state": 8,
                "turnaround_formula": 9,
                "waiting_formula": 10,
            }

            for key, value in updates.items():
                if key in column_map:
                    current_values[column_map[key]] = value

            self.proc_tree_sim.item(item_id, values=current_values)

    def update_gantt_display_sim(self, time_tick, running_pids_with_threads):
        """Actualiza la visualización del diagrama de Gantt en el tiempo actual."""
        time_width = self.gantt_data["time_width"]
        row_height = self.gantt_data["row_height"]
        margin_top = 30

        num_workers = self.num_workers_for_sim_display

        if time_tick == 0:
            self.gantt_canvas.delete("all")
            self.gantt_data["last_time"] = -1
            self.gantt_data["process_colors"] = {}
            self.gantt_data["process_rows"] = {}
            self.gantt_data["next_color_index"] = 0

            for i in range(num_workers):
                y_pos = margin_top + (i + 0.5) * row_height
                self.gantt_canvas.create_text(
                    25,
                    y_pos,
                    text=f"CPU {i+1}",
                    font=("Segoe UI", 9, "bold"),
                    fill=self.colors["text_dark"],
                )

                if i > 0:
                    self.gantt_canvas.create_line(
                        50,
                        margin_top + i * row_height,
                        2000,
                        margin_top + i * row_height,
                        fill=self.colors["border"],
                        dash=(4, 2),
                    )

        if time_tick > self.gantt_data["last_time"]:
            self.gantt_data["last_time"] = time_tick

            x_pos = 50 + time_tick * time_width
            self.gantt_canvas.create_line(
                x_pos,
                margin_top,
                x_pos,
                margin_top + num_workers * row_height,
                fill=self.colors["border"],
            )

            if time_tick % 5 == 0 or time_tick == 0:
                self.gantt_canvas.create_text(
                    x_pos,
                    margin_top - 15,
                    text=f"t={time_tick}",
                    font=("Segoe UI", 8),
                    fill=self.colors["text_dark"],
                )

        for pid, thread_id in running_pids_with_threads:
            if thread_id >= num_workers:
                continue

            if pid not in self.gantt_data["process_colors"]:
                color_idx = self.gantt_data["next_color_index"] % len(
                    self.gantt_data["colors"]
                )
                self.gantt_data["process_colors"][pid] = self.gantt_data["colors"][
                    color_idx
                ]
                self.gantt_data["next_color_index"] += 1

            color = self.gantt_data["process_colors"][pid]

            x1 = 50 + time_tick * time_width
            y1 = margin_top + thread_id * row_height
            x2 = x1 + time_width
            y2 = y1 + row_height

            rect_id = self.gantt_canvas.create_rectangle(
                x1, y1, x2, y2, fill=color, outline=self.colors["border"]
            )

            text_id = self.gantt_canvas.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=f"P{pid}",
                fill="white",
                font=("Segoe UI", 9, "bold"),
            )

            self.gantt_data["process_rows"][pid] = thread_id

        self.gantt_canvas.configure(scrollregion=self.gantt_canvas.bbox("all"))

        if time_tick > 15:
            self.gantt_canvas.xview_moveto(
                (time_tick - 15) * time_width / self.gantt_canvas.bbox("all")[2]
            )

        if time_tick == 5:
            legend_y = margin_top + num_workers * row_height + 20

            self.gantt_canvas.create_text(
                100,
                legend_y,
                text="Leyenda de Procesos:",
                font=("Segoe UI", 10, "bold"),
                fill=self.colors["text_dark"],
            )

            legend_x = 250
            for pid, color in self.gantt_data["process_colors"].items():
                self.gantt_canvas.create_rectangle(
                    legend_x,
                    legend_y - 10,
                    legend_x + 20,
                    legend_y + 10,
                    fill=color,
                    outline=self.colors["border"],
                )
                self.gantt_canvas.create_text(
                    legend_x + 35,
                    legend_y,
                    text=f"P{pid}",
                    font=("Segoe UI", 9),
                    fill=self.colors["text_dark"],
                )
                legend_x += 80

    def calculate_and_display_averages_sim(self):
        """Calcula y muestra los tiempos promedio de la simulación."""
        if not self.completed_processes_sim:
            return

        count = len(self.completed_processes_sim)
        avg_T = (
            sum(p.turnaround_time for p in self.completed_processes_sim) / count
            if count
            else 0
        )
        avg_W = (
            sum(p.waiting_time for p in self.completed_processes_sim) / count
            if count
            else 0
        )

        self.avg_turnaround_label.config(text=f"Turnaround Promedio: {avg_T:.2f}")
        self.avg_waiting_label.config(text=f"Tiempo de Espera Promedio: {avg_W:.2f}")

    # --- Resultados Servidor y CSV ---

    def display_server_results(self):
        """Muestra resultados del servidor en la interfaz."""
        if not self.server_results_for_csv:
            return

        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        for result in self.server_results_for_csv:
            try:
                pid_server = result.get("pid_server", "N/A")
                filename = result.get("filename", "")

                data = result.get("data", {})
                nombres_raw = data.get("nombres_encontrados", [])
                lugares_raw = data.get("lugares_encontrados", [])
                fechas_raw = data.get("dates_found", [])
                word_count = str(data.get("word_count", 0))

                nombres = (
                    ", ".join(nombres_raw)[:50] + "..."
                    if len(nombres_raw) > 3
                    else ", ".join(nombres_raw)
                )
                lugares = (
                    ", ".join(lugares_raw)[:50] + "..."
                    if len(lugares_raw) > 3
                    else ", ".join(lugares_raw)
                )
                fechas = (
                    ", ".join(fechas_raw)[:50] + "..."
                    if len(fechas_raw) > 3
                    else ", ".join(fechas_raw)
                )

                status = result.get("status", "")
                error = result.get("error", "")

                self.results_tree.insert(
                    "",
                    "end",
                    values=(
                        pid_server,
                        filename,
                        nombres,
                        lugares,
                        fechas,
                        word_count,
                        status,
                        error,
                    ),
                )

            except Exception as e:
                print(f"Error al mostrar resultado: {e}")

        self.status_label.config(
            text=f"{len(self.server_results_for_csv)} resultados recibidos del servidor."
        )

    def save_results_to_csv(self):
        """Guarda los resultados en un archivo CSV."""
        if not self.server_results_for_csv:
            messagebox.showinfo("Info", "No hay resultados para guardar.")
            return

        try:
            import csv

            with open(self.output_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.csv_headers)

                for result in self.server_results_for_csv:
                    pid = result.get("pid_server", "")
                    filename = result.get("filename", "")

                    data = result.get("data", {})
                    nombres = "|".join(data.get("nombres_encontrados", []))
                    lugares = "|".join(data.get("lugares_encontrados", []))
                    fechas = "|".join(data.get("fechas_encontradas", []))
                    word_count = str(data.get("word_count", 0))

                    status = result.get("status", "")
                    error = result.get("error", "")

                    writer.writerow(
                        [
                            pid,
                            filename,
                            nombres,
                            lugares,
                            fechas,
                            word_count,
                            status,
                            error,
                        ]
                    )

            self.status_label.config(
                text=f"Resultados guardados en {self.output_csv_path}"
            )
            messagebox.showinfo(
                "Info", f"Resultados guardados en:\n{self.output_csv_path}"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar CSV: {e}")


if __name__ == "__main__":
    app_root = tk.Tk()
    app = ClientApp(app_root)
    app_root.protocol("WM_DELETE_WINDOW", app.on_closing)
    app_root.mainloop()
