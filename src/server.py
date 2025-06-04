import socket
import threading
import json
import os
import collections
import concurrent.futures
import time
import sys
import logging
from .extractor_regex import parse_file_regex as parse_file


# --- Configuración del Logger ---
LOG_FILENAME = "server_processing.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=LOG_FILENAME,
    filemode="a",
)


# --- Configuración General del Servidor ---
HOST = "127.0.0.1"
PORT = 65432

TEXT_FILES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "text_files")
)
print(f"[DEBUG] Buscando en ruta: {TEXT_FILES_DIR}")

if not os.path.isdir(TEXT_FILES_DIR):
    try:
        os.makedirs(TEXT_FILES_DIR)
        print(f"[DEBUG] Carpeta '{TEXT_FILES_DIR}' creada.")
    except Exception as e:
        print(f"[ERROR] No se pudo crear la carpeta '{TEXT_FILES_DIR}': {e}")
        sys.exit(1)
else:
    print(f"[DEBUG] Carpeta ya existe.")

text_files = [f for f in os.listdir(TEXT_FILES_DIR) if f.endswith(".txt")]
print(f"[DEBUG] Archivos encontrados: {text_files}")

DEFAULT_CLIENT_CONFIG = {"mode": "threads", "count": 1}


# --- Estado del Servidor (Protegido por Locks) ---
state_lock = threading.Lock()
events: dict[str, set] = {}
client_configs: dict = {}
client_queues: dict[str, collections.deque] = {}
clients: dict = {}
client_ids: dict = {}
next_client_id = 1

processing_lock = threading.Lock()
client_batch_processing_queue = collections.deque()
new_batch_event = threading.Event()


# --- Configuración del Socket del Servidor ---
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen()
print(f"Servidor escuchando en {HOST}:{PORT}")


# --- Funciones auxiliares para manejo de clientes ---

def get_client_id(client_socket):
    """Obtiene el ID de un cliente o devuelve None si no existe."""
    with state_lock:
        return client_ids.get(client_socket)


def get_client_events(client_socket):
    """Obtiene los eventos a los que está suscrito un cliente."""
    client_events = []
    try:
        with state_lock:
            for event_name, subscribers in events.items():
                if client_socket in subscribers:
                    client_events.append(event_name)
    except Exception as e:
        print(f"Error obteniendo eventos del cliente: {e}")
    return client_events


def show_client_subscriptions():
    """Muestra los clientes conectados y sus suscripciones."""
    try:
        client_info = []

        with state_lock:
            if not clients:
                print("  No hay clientes conectados.")
                return

            for sock, addr in clients.items():
                client_id = client_ids.get(sock, "?")
                events_for_client = []
                for event_name, subscribers in events.items():
                    if sock in subscribers:
                        events_for_client.append(event_name)
                client_info.append((client_id, events_for_client))

        for client_id, subscribed_events in client_info:
            if subscribed_events:
                events_str = ", ".join(subscribed_events)
                print(f"  Cliente {client_id} suscrito a: {events_str}")
            else:
                print(f"  Cliente {client_id} no está suscrito a ningún evento.")
    except Exception as e:
        print(f"  Error al mostrar suscripciones: {e}")


# --- Funciones Auxiliares Generales ---

def server_log(message):
    """Función centralizada para logs del servidor."""
    print(f"\n{message}")


def send_to_client(client_socket, message):
    """Envía un mensaje codificado en JSON a un cliente específico."""
    if client_socket.fileno() == -1:
        threading.Thread(
            target=handle_disconnect, args=(client_socket,), daemon=True
        ).start()
        return

    try:
        payload = json.dumps(message) + "\n"
        client_socket.sendall(payload.encode("utf-8"))

    except (BrokenPipeError, ConnectionResetError):
        threading.Thread(
            target=handle_disconnect, args=(client_socket,), daemon=True
        ).start()

    except Exception as e:
        server_log(f"Error enviando mensaje: {e}")
        threading.Thread(
            target=handle_disconnect, args=(client_socket,), daemon=True
        ).start()


def handle_disconnect(client_socket):
    """Limpia el estado del servidor cuando un cliente se desconecta."""
    addr_disconnected = None
    client_id_disconnected = None
    processed_disconnect = False

    with state_lock:
        if client_socket in clients:
            addr_disconnected = clients.pop(client_socket, None)
            client_id_disconnected = client_ids.pop(client_socket, None)
            client_configs.pop(client_socket, None)
            processed_disconnect = True

            for event_name in list(events.keys()):
                if events.get(event_name) and client_socket in events[event_name]:
                    events[event_name].discard(client_socket)

            for event_name in list(client_queues.keys()):
                queue = client_queues.get(event_name)
                if queue and client_socket in queue:
                    try:
                        new_queue = collections.deque(
                            [s for s in queue if s != client_socket]
                        )
                        client_queues[event_name] = new_queue
                    except Exception as e:
                        print(f"\nError removiendo de cola '{event_name}': {e}")

    if processed_disconnect and addr_disconnected:
        server_log(
            f"Cliente {client_id_disconnected} ({addr_disconnected}) "
            "desconectado o removido."
        )

    try:
        if client_socket.fileno() != -1:
            client_socket.close()
    except Exception:
        pass


# --- Funciones de Procesamiento de Archivos ---

def process_single_file_wrapper(arg_tuple):
    """
    Wrapper para procesar un solo archivo, adaptado para ThreadPool y ProcessPool.
    Muestra el PID del worker (hilo o proceso) al inicio y al final.
    """
    filepath, processing_mode = arg_tuple
    filename_base = os.path.basename(filepath)

    pid_label = ""
    worker_id_str = ""

    if processing_mode == "threads":
        pid_label = "THREAD ID"
        worker_id_str = str(threading.get_ident())
    elif processing_mode == "forks":
        pid_label = "FORK PID"
        worker_id_str = str(os.getpid())
    else:
        pid_label = "UNKNOWN WORKER ID"
        worker_id_str = "N/A"

    descriptive_worker_id = f"{pid_label}_{worker_id_str}"

    print(f"\n[{pid_label}: {worker_id_str}] Iniciando procesamiento de: {filename_base}")
    sys.stdout.flush()

    logging.info(
        f"[{descriptive_worker_id}] Iniciando procesamiento de archivo: {filepath}"
    )

    try:
        raw_result_from_extractor = parse_file(filepath, pid=descriptive_worker_id)

        logging.info(
            f"[{descriptive_worker_id}] Datos extraídos de {filename_base}: "
            f"Nombres: {len(raw_result_from_extractor.get('Nombres', []))}, "
            f"Fechas: {len(raw_result_from_extractor.get('Fechas', []))}, "
            f"Lugares: {len(raw_result_from_extractor.get('Lugares', []))}, "
            f"Palabras: {raw_result_from_extractor.get('ConteoPalabras', 0)}"
        )

        status_from_extractor = raw_result_from_extractor.get(
            "status", raw_result_from_extractor.get("estado", "error")
        )
        error_from_extractor = raw_result_from_extractor.get("error", "")

        final_filename = raw_result_from_extractor.get(
            "filename", raw_result_from_extractor.get("archivo", filename_base)
        )

        if status_from_extractor == "success":
            print(
                f"\n[{pid_label}: {worker_id_str}] Finalizado procesamiento de: "
                f"{final_filename} (Éxito)"
            )
            sys.stdout.flush()

            logging.info(
                f"[{descriptive_worker_id}] Finalizado procesamiento de "
                f"{final_filename} con ÉXITO."
            )

            data_for_client = {
                "nombres_encontrados": raw_result_from_extractor.get("Nombres", []),
                "fechas_encontradas": raw_result_from_extractor.get("Fechas", []),
                "lugares_encontrados": raw_result_from_extractor.get("Lugares", []),
                "word_count": raw_result_from_extractor.get("ConteoPalabras", 0),
            }

            final_result_for_server = {
                "pid_server": descriptive_worker_id,
                "filename": final_filename,
                "data": data_for_client,
                "status": "success",
                "error": "",
            }
        else:
            print(
                f"\n[{pid_label}: {worker_id_str}] Error durante extracción para "
                f"{final_filename} (ver log)."
            )
            sys.stdout.flush()

            logging.error(
                f"[{descriptive_worker_id}] Error durante extracción para "
                f"{final_filename}: {error_from_extractor}"
            )

            final_result_for_server = {
                "pid_server": descriptive_worker_id,
                "filename": final_filename,
                "data": {
                    "nombres_encontrados": [],
                    "fechas_encontradas": [],
                    "lugares_encontrados": [],
                    "word_count": 0,
                },
                "status": "error",
                "error": error_from_extractor,
            }
        return final_result_for_server

    except Exception as e:
        print(
            f"\n[{pid_label}: {worker_id_str}] Error INESPERADO en wrapper para "
            f"{filename_base} (ver log)."
        )
        sys.stdout.flush()

        logging.error(
            f"[{descriptive_worker_id}] Error INESPERADO en wrapper para "
            f"{filename_base}: {type(e).__name__} - {e}",
            exc_info=True,
        )

        return {
            "pid_server": descriptive_worker_id,
            "filename": filename_base,
            "data": {
                "nombres_encontrados": [],
                "fechas_encontradas": [],
                "lugares_encontrados": [],
                "word_count": 0,
            },
            "status": "error",
            "error": f"Error inesperado en wrapper: {str(e)}",
        }


def manage_client_batch_processing():
    """
    Hilo trabajador que toma lotes de client_batch_processing_queue
    y los procesa uno a la vez.
    """
    while True:
        new_batch_event.wait()

        client_socket, assigned_files, event_name, config = (None,) * 4

        with state_lock:
            if client_batch_processing_queue:
                item = client_batch_processing_queue.popleft()
                client_socket, assigned_files, event_name, config = item
            else:
                new_batch_event.clear()
                continue

        client_addr_log, is_client_valid = "Dirección Desconocida", False

        with state_lock:
            if client_socket in clients:
                client_addr_log = str(clients[client_socket])
                is_client_valid = True
            else:
                server_log(
                    f"Cliente para lote de '{event_name}' ya no conectado. "
                    "Lote descartado."
                )

        if not is_client_valid or not assigned_files:
            continue

        with processing_lock:
            start_time_batch = time.time()
            results = []
            worker_identifiers_used = set()

            try:
                send_to_client(
                    client_socket,
                    {
                        "type": "START_PROCESSING",
                        "payload": {"event": event_name, "files": assigned_files},
                    },
                )

                num_workers = config.get("count", DEFAULT_CLIENT_CONFIG["count"])
                processing_mode = config.get("mode", DEFAULT_CLIENT_CONFIG["mode"])

                num_workers = max(num_workers, 1)

                full_paths = [os.path.join(TEXT_FILES_DIR, f) for f in assigned_files]

                executor_cls = None
                if processing_mode == "threads":
                    executor_cls = concurrent.futures.ThreadPoolExecutor
                elif processing_mode == "forks":
                    executor_cls = concurrent.futures.ProcessPoolExecutor
                else:
                    raise ValueError(f"Modo de proc. inválido: {processing_mode}")

                with executor_cls(max_workers=num_workers) as executor:
                    map_input = [(fp, processing_mode) for fp in full_paths]
                    map_results_list = list(
                        executor.map(process_single_file_wrapper, map_input)
                    )
                    results.extend(map_results_list)

                    for res_item in map_results_list:
                        if "pid_server" in res_item:
                            worker_identifiers_used.add(res_item["pid_server"])

                duration = time.time() - start_time_batch
                server_log(
                    f"Lote para {client_addr_log} ({event_name}) "
                    f"completado en {duration:.2f}s."
                )

                if worker_identifiers_used:
                    print(f"    Workers utilizados para este lote ({processing_mode}):")
                    for worker_id_str in sorted(list(worker_identifiers_used)):
                        print(f"      - {worker_id_str}")
                    sys.stdout.flush()

                send_to_client(
                    client_socket,
                    {
                        "type": "PROCESSING_COMPLETE",
                        "payload": {
                            "event": event_name,
                            "status": "success",
                            "results": results,
                            "duration_seconds": duration,
                        },
                    },
                )

            except Exception as e:
                server_log(
                    f"Error en procesamiento de lote para {client_addr_log}: {e}"
                )
                try:
                    send_to_client(
                        client_socket,
                        {
                            "type": "PROCESSING_COMPLETE",
                            "payload": {
                                "event": event_name,
                                "status": "failure",
                                "message": str(e),
                                "results": [],
                            },
                        },
                    )
                except:
                    pass


# --- Hilo Manejador de Cliente ---
def handle_client(client_socket, addr):
    """Maneja la comunicación con un cliente conectado."""
    global next_client_id

    client_id = next_client_id
    next_client_id += 1

    with state_lock:
        clients[client_socket] = addr
        client_ids[client_socket] = client_id
        if client_socket not in client_configs:
            client_configs[client_socket] = DEFAULT_CLIENT_CONFIG.copy()

    server_log(f"Cliente {client_id} conectado desde {addr}")

    send_to_client(
        client_socket,
        {
            "type": "WELCOME",
            "payload": {"server_info": {"version": "1.0"}, "client_id": client_id},
        },
    )

    buffer = ""
    try:
        while True:
            try:
                data = client_socket.recv(4096)
            except ConnectionResetError:
                server_log(f"Conexión reseteada por cliente {client_id} ({addr}).")
                break
            except Exception as e:
                server_log(f"Error en recv() para cliente {client_id} ({addr}): {e}")
                break

            if not data:
                server_log(f"Cliente {client_id} ({addr}) cerró conexión.")
                break

            buffer += data.decode("utf-8")

            while "\n" in buffer:
                message_str, buffer = buffer.split("\n", 1)
                if not message_str.strip():
                    continue

                try:
                    message = json.loads(message_str)
                    command = message.get("type")
                    payload = message.get("payload")

                    if command == "SET_CONFIG":
                        if (
                            isinstance(payload, dict)
                            and "mode" in payload
                            and "count" in payload
                        ):
                            mode = payload["mode"]
                            count = payload["count"]
                            if (
                                mode in ["threads", "forks"]
                                and isinstance(count, int)
                                and count > 0
                            ):
                                with state_lock:
                                    client_configs[client_socket] = {
                                        "mode": mode,
                                        "count": count,
                                    }
                                cfg = client_configs[client_socket]
                                send_to_client(
                                    client_socket,
                                    {
                                        "type": "ACK_CONFIG",
                                        "payload": {"status": "success", "config": cfg},
                                    },
                                )
                            else:
                                send_to_client(
                                    client_socket,
                                    {
                                        "type": "ACK_CONFIG",
                                        "payload": {
                                            "status": "error",
                                            "message": "Modo/cantidad inválido.",
                                        },
                                    },
                                )
                        else:
                            send_to_client(
                                client_socket,
                                {
                                    "type": "ACK_CONFIG",
                                    "payload": {
                                        "status": "error",
                                        "message": "Payload SET_CONFIG inválido.",
                                    },
                                },
                            )

                    elif command == "SUB":
                        event_name = payload
                        if isinstance(event_name, str) and event_name:
                            with state_lock:
                                if event_name not in events:
                                    events[event_name] = set()
                                events[event_name].add(client_socket)

                                if event_name not in client_queues:
                                    client_queues[event_name] = collections.deque()
                                if client_socket not in client_queues[event_name]:
                                    client_queues[event_name].append(client_socket)

                            server_log(
                                f"Cliente {client_id} suscrito a evento '{event_name}'"
                            )
                            send_to_client(
                                client_socket,
                                {"type": "ACK_SUB", "payload": event_name},
                            )
                        else:
                            send_to_client(
                                client_socket,
                                {"type": "ERROR", "payload": "SUB inválido."},
                            )

                    elif command == "UNSUB":
                        event_name = payload
                        if isinstance(event_name, str) and event_name:
                            with state_lock:
                                if event_name in events:
                                    events[event_name].discard(client_socket)
                                if event_name in client_queues:
                                    new_q = collections.deque(
                                        [
                                            s
                                            for s in client_queues[event_name]
                                            if s != client_socket
                                        ]
                                    )
                                    client_queues[event_name] = new_q

                            server_log(
                                f"Cliente {client_id} desuscrito de evento '{event_name}'"
                            )
                            send_to_client(
                                client_socket,
                                {"type": "ACK_UNSUB", "payload": event_name},
                            )
                        else:
                            send_to_client(
                                client_socket,
                                {"type": "ERROR", "payload": "UNSUB inválido."},
                            )

                    elif command == "PROCESS_FILES":
                        event_name = payload.get("event", "sin_evento")
                        files = payload.get("files", [])

                        if not files:
                            send_to_client(
                                client_socket,
                                {
                                    "type": "PROCESSING_COMPLETE",
                                    "payload": {
                                        "event": event_name,
                                        "status": "success",
                                        "message": "No files provided.",
                                        "results": [],
                                    },
                                },
                            )
                            continue

                        try:
                            full_paths = [
                                os.path.join(TEXT_FILES_DIR, f)
                                for f in files
                                if os.path.isfile(os.path.join(TEXT_FILES_DIR, f))
                            ]

                            num_workers = client_configs.get(client_socket, {}).get(
                                "count", 2
                            )
                            mode = client_configs.get(client_socket, {}).get(
                                "mode", "threads"
                            )

                            executor_cls = (
                                concurrent.futures.ThreadPoolExecutor
                                if mode == "threads"
                                else concurrent.futures.ProcessPoolExecutor
                            )

                            with executor_cls(max_workers=num_workers) as executor:
                                map_input = [(fp, mode) for fp in full_paths]
                                map_results = list(
                                    executor.map(process_single_file_wrapper, map_input)
                                )

                            send_to_client(
                                client_socket,
                                {
                                    "type": "PROCESSING_COMPLETE",
                                    "payload": {
                                        "event": event_name,
                                        "status": "success",
                                        "results": map_results,
                                        "duration_seconds": 0,
                                    },
                                },
                            )

                        except Exception as e:
                            send_to_client(
                                client_socket,
                                {
                                    "type": "PROCESSING_COMPLETE",
                                    "payload": {
                                        "event": event_name,
                                        "status": "failure",
                                        "message": str(e),
                                        "results": [],
                                    },
                                },
                            )

                except json.JSONDecodeError:
                    server_log(f"JSON inválido de {addr}: '{message_str}'")
                except Exception as e:
                    server_log(f"Error procesando msg de {addr}: {e}")
    finally:
        handle_disconnect(client_socket)


# --- Comandos del Servidor ---

def print_help():
    """Muestra la ayuda de comandos del servidor."""
    print("\n--- Comandos del Servidor ---")
    print("  help                          - Muestra esta ayuda.")
    print("  add <nombre_evento>           - Crea un nuevo evento.")
    print("  remove <nombre_evento>        - Elimina un evento y su cola.")
    print(
        "  trigger <nombre_evento>       - Dispara un evento para los clientes en cola."
    )
    print(
        "  list                          - Muestra estado de eventos, colas y clientes."
    )
    print("  clients                       - Muestra clientes y sus eventos suscritos.")
    print(
        "  status                        - Muestra si el servidor está Ocupado o Idle."
    )
    print(
        "  exit                          - Cierra el servidor y notifica a los clientes."
    )
    print("-----------------------------\n")


def server_commands():
    """Maneja comandos ingresados en la terminal del servidor."""
    print_help()

    while True:
        try:
            cmd_input = input("Server> ").strip()

            if not cmd_input:
                continue

            parts = cmd_input.split()
            command = parts[0].lower()

            print()

            if command == "help":
                print_help()

            elif command == "add" and len(parts) > 1:
                event_name = parts[1]
                with state_lock:
                    if event_name not in events:
                        events[event_name] = set()
                        client_queues[event_name] = collections.deque()
                        print(f"Evento '{event_name}' creado.")
                    else:
                        print(f"Evento '{event_name}' ya existe.")

            elif command == "remove" and len(parts) > 1:
                event_name = parts[1]
                with state_lock:
                    if event_name in events:
                        del events[event_name]
                        if event_name in client_queues:
                            client_queues[event_name].clear()
                            del client_queues[event_name]
                        print(f"Evento '{event_name}' y su cola eliminados.")
                    else:
                        print(f"Evento '{event_name}' no encontrado.")

            elif command == "clients":
                print("--- Clientes y Sus Suscripciones ---")
                try:
                    show_client_subscriptions()
                except Exception as e:
                    print(f"  Error al ejecutar comando 'clients': {e}")
                finally:
                    print("------------------------------------")

            elif command == "list":
                with state_lock:
                    print("--- Estado del Servidor ---")
                    print("\nEventos y Suscriptores:")
                    if not events:
                        print("  (Ninguno)")
                    for ev, subs in events.items():
                        client_id_list = [
                            f"Cliente {client_ids.get(s, '?')}" for s in subs
                        ]
                        print(f"- {ev}: {len(subs)} subs -> {client_id_list}")

                    print("\nColas de Eventos (Clientes en Espera):")
                    if not client_queues:
                        print("  (Ninguna)")
                    for ev, q in client_queues.items():
                        q_client_ids = [f"Cliente {client_ids.get(s, '?')}" for s in q]
                        print(f"- {ev}: {len(q)} en cola -> {q_client_ids}")

                    print("\nClientes Conectados y su Configuración:")
                    if not clients:
                        print("  (Ninguno)")
                    for sock, addr in clients.items():
                        cfg = client_configs.get(sock, "N/A")
                        client_id = client_ids.get(sock, "?")
                        print(f"- Cliente {client_id} ({addr}): {cfg}")
                    print("-------------------------")

            elif command == "status":
                is_worker_busy, q_len = False, 0
                with state_lock:
                    if client_batch_processing_queue:
                        is_worker_busy = True
                        q_len = len(client_batch_processing_queue)

                if is_worker_busy or processing_lock.locked():
                    print(f"Estado: Ocupado (Procesando o con {q_len} lotes en cola)")
                else:
                    print("Estado: Idle")

            elif command == "trigger" and len(parts) > 1:
                event_name = parts[1]
                print(f"Disparando evento '{event_name}'...")

                active_clients_for_event = []
                with state_lock:
                    if event_name not in client_queues or not client_queues[event_name]:
                        print(f"Sin clientes en espera para '{event_name}'.")
                        continue

                    clients_in_q_snapshot = list(client_queues[event_name])
                    client_queues[event_name].clear()

                    for sock in clients_in_q_snapshot:
                        if sock in clients and sock in client_configs:
                            active_clients_for_event.append(sock)
                        else:
                            print(
                                f"Cliente {str(clients.get(sock))} de '{event_name}' "
                                "omitido (desconectado/sin config)."
                            )

                if not active_clients_for_event:
                    print(f"Sin clientes válidos activos para procesar '{event_name}'.")
                    continue

                try:
                    all_files = [
                        f
                        for f in os.listdir(TEXT_FILES_DIR)
                        if f.endswith(".txt")
                        and os.path.isfile(os.path.join(TEXT_FILES_DIR, f))
                    ]
                except Exception as e:
                    print(f"Error listando archivos para '{event_name}': {e}")
                    continue

                if not all_files:
                    print(
                        f"Sin archivos .txt en '{TEXT_FILES_DIR}' para '{event_name}'."
                    )
                    for sock in active_clients_for_event:
                        send_to_client(
                            sock,
                            {
                                "type": "PROCESSING_COMPLETE",
                                "payload": {
                                    "event": event_name,
                                    "status": "success",
                                    "message": "No files to process.",
                                    "results": [],
                                },
                            },
                        )
                    continue

                num_clients = len(active_clients_for_event)
                total_files = len(all_files)
                start_idx = 0
                batches_created = 0

                for i, client_sock in enumerate(active_clients_for_event):
                    files_this_client = total_files // num_clients
                    if i < (total_files % num_clients):
                        files_this_client += 1

                    end_idx = start_idx + files_this_client
                    assigned_files = all_files[start_idx:end_idx]
                    start_idx = end_idx

                    if not assigned_files:
                        send_to_client(
                            client_sock,
                            {
                                "type": "PROCESSING_COMPLETE",
                                "payload": {
                                    "event": event_name,
                                    "status": "success",
                                    "message": "No files assigned for this trigger.",
                                    "results": [],
                                },
                            },
                        )
                        continue

                    client_cfg = None
                    with state_lock:
                        client_cfg = client_configs.get(client_sock)

                    if client_cfg:
                        batch = (client_sock, assigned_files, event_name, client_cfg)
                        with state_lock:
                            client_batch_processing_queue.append(batch)
                        batches_created += 1
                    else:
                        print(
                            f"Cliente {clients.get(client_sock)} ya no tiene config. "
                            "Lote descartado."
                        )

                if batches_created > 0:
                    new_batch_event.set()
                print(
                    f"{batches_created} lotes para '{event_name}' añadidos "
                    "a cola de procesamiento."
                )

            elif command == "exit":
                print("Cerrando servidor...")
                new_batch_event.set()
                time.sleep(0.5)

                with state_lock:
                    client_list = list(clients.keys())

                for sock in client_list:
                    send_to_client(sock, {"type": "SERVER_EXIT", "payload": None})
                    time.sleep(0.1)
                    handle_disconnect(sock)

                server_socket.close()
                print("Servidor terminado.")
                os._exit(0)

            else:
                print("Comando desconocido. Escribe 'help' para ver la lista.")

            print()

        except EOFError:
            print("\nCerrando servidor por EOF...")
            new_batch_event.set()
            time.sleep(0.5)
            with state_lock:
                client_list = list(clients.keys())
            for sock in client_list:
                try:
                    send_to_client(sock, {"type": "SERVER_EXIT", "payload": None})
                except:
                    pass
                handle_disconnect(sock)
            server_socket.close()
            os._exit(0)

        except Exception as e:
            print(f"Error en bucle de comandos del servidor: {e}")


# --- Bucle Principal del Servidor ---

def main_server_loop():
    """Bucle principal para aceptar conexiones de clientes."""
    try:
        while True:
            try:
                client_sock, client_addr = server_socket.accept()
                client_handler_thread = threading.Thread(
                    target=handle_client, args=(client_sock, client_addr), daemon=True
                )
                client_handler_thread.start()
            except OSError as e:
                print(f"Error aceptando conexión (puede ser normal al cerrar): {e}")
                break
            except Exception as e:
                print(f"Error inesperado en bucle de aceptación: {e}")
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nCerrando servidor por KeyboardInterrupt...")
        new_batch_event.set()
        time.sleep(0.5)
        with state_lock:
            client_list = list(clients.keys())
        for sock in client_list:
            try:
                send_to_client(sock, {"type": "SERVER_EXIT", "payload": None})
            except:
                pass
            handle_disconnect(sock)
        server_socket.close()

    finally:
        if server_socket and not getattr(server_socket, "_closed", True):
            try:
                server_socket.close()
                print("Socket del servidor cerrado en bloque finally.")
            except Exception:
                pass


if __name__ == "__main__":
    # Iniciar hilos de fondo
    command_thread = threading.Thread(target=server_commands, daemon=True)
    command_thread.start()

    batch_worker_thread = threading.Thread(
        target=manage_client_batch_processing, daemon=True
    )
    batch_worker_thread.start()

    # Iniciar el bucle principal de aceptación de clientes
    main_server_loop()
