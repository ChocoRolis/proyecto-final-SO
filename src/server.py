# src/server.py

import socket
import threading
import json
import os
import collections
import concurrent.futures
import time
import re
import math
import sys # Para sys.stdout.flush()

# --- Configuración ---
HOST = '127.0.0.1'
PORT = 65432
TEXT_FILES_DIR = 'text_files'
DEFAULT_CLIENT_CONFIG = {'mode': 'threads', 'count': 1}

# --- Estado del Servidor (Protegido por Locks) ---
state_lock = threading.Lock()
events: dict[str, set] = {}
client_configs: dict = {}
client_queues: dict[str, collections.deque] = {}
clients: dict = {}

processing_lock = threading.Lock()
client_batch_processing_queue = collections.deque()
new_batch_event = threading.Event()


# --- Configuración del Socket del Servidor ---
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen()
print(f"Servidor escuchando en {HOST}:{PORT}")
print(f"Buscando archivos de texto en: ./{TEXT_FILES_DIR}/")

if not os.path.isdir(TEXT_FILES_DIR):
    try:
        os.makedirs(TEXT_FILES_DIR)
        print(f"Directorio '{TEXT_FILES_DIR}' creado.")
    except OSError as e:
        print(f"Error: No se pudo crear el directorio '{TEXT_FILES_DIR}': {e}")
        # sys.exit(1) # Considerar salir si es esencial


# --- Funciones Auxiliares ---

def server_log(message):
    """Función centralizada para logs del servidor."""
    print(f"\n{message}")


def send_to_client(client_socket, message):
    """Envía un mensaje codificado en JSON a un cliente específico."""
    if client_socket.fileno() == -1: # Socket ya cerrado
        # El log aquí podría ser problemático si handle_disconnect ya fue llamado
        # server_log(f"Intento de envío a socket cerrado")
        # Disparar handle_disconnect si aún no se ha hecho, es seguro
        threading.Thread(
            target=handle_disconnect, args=(client_socket,), daemon=True
        ).start()
        return

    try:
        payload = json.dumps(message) + "\n"
        client_socket.sendall(payload.encode('utf-8'))

    except (BrokenPipeError, ConnectionResetError):
        # No usar server_log aquí, ya que handle_disconnect lo hará
        # server_log(f"Error al enviar. Cliente parece desconectado.")
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
    processed_disconnect = False # Flag para evitar logs duplicados

    with state_lock:
        if client_socket in clients: # Solo procesar si el cliente aún está "registrado"
            addr_disconnected = clients.pop(client_socket, None)
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
                        # Evitar log dentro de log si esto viene de send_to_client
                        print(f"\nError removiendo de cola '{event_name}': {e}")
        # else: El cliente ya fue procesado por otro hilo de desconexión

    if processed_disconnect and addr_disconnected:
        server_log(f"Cliente {addr_disconnected} desconectado o removido.")

    try:
        if client_socket.fileno() != -1:
            client_socket.close()
    except Exception:
        pass # El socket podría ya estar cerrado, es un error esperado


def process_single_file_wrapper(filepath_tuple):
    """Wrapper para process_single_file para ProcessPoolExecutor."""
    filepath = filepath_tuple[0]
    filename = os.path.basename(filepath)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # --- TU LÓGICA REGEX AQUÍ ---
        emails = re.findall(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', content
        )
        dates = re.findall(
            r'\b(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\b', content
        )
        word_count = len(content.split())
        # --- FIN LÓGICA REGEX ---

        time.sleep(0.05) # Simular I/O o trabajo ligero

        result_data = {
            "emails_found": emails,
            "dates_found": dates,
            "word_count": word_count,
        }
        return {"filename": filename, "data": result_data, "status": "success"}

    except FileNotFoundError:
        return {"filename": filename, "error": "File not found.", "status": "error"}

    except Exception as e:
        return {"filename": filename, "error": str(e), "status": "error"}


def manage_client_batch_processing():
    """
    Hilo trabajador que toma lotes de client_batch_processing_queue
    y los procesa uno a la vez.
    """
    while True:
        new_batch_event.wait() # Espera hasta que haya algo en la cola

        client_socket, assigned_files, event_name, config = (None,) * 4

        with state_lock: # Proteger el pop de la cola
            if client_batch_processing_queue:
                item = client_batch_processing_queue.popleft()
                client_socket, assigned_files, event_name, config = item
            else:
                new_batch_event.clear() # No hay más, esperar de nuevo
                continue # Volver al inicio del while

        client_addr_log, is_client_valid = "Dirección Desconocida", False
        with state_lock:
            if client_socket in clients:
                client_addr_log = str(clients[client_socket])
                is_client_valid = True
            else:
                server_log(
                    f"Cliente para lote de '{event_name}' ya no conectado. Lote descartado."
                )

        if not is_client_valid or not assigned_files:
            continue

        # server_log(f"Trabajador: Intentando lock para {client_addr_log}")
        with processing_lock: # Adquiere lock
            # server_log(f"Trabajador: lock adquirido para {client_addr_log}")
            start_time_batch = time.time()
            results = []

            try:
                send_to_client(client_socket, {
                    "type": "START_PROCESSING",
                    "payload": {"event": event_name, "files": assigned_files}
                })

                num_workers = config.get('count', DEFAULT_CLIENT_CONFIG['count'])
                mode = config.get('mode', DEFAULT_CLIENT_CONFIG['mode'])
                if num_workers < 1:
                    num_workers = 1

                full_paths = [
                    os.path.join(TEXT_FILES_DIR, f) for f in assigned_files
                ]

                executor_cls = None
                if mode == 'threads':
                    executor_cls = concurrent.futures.ThreadPoolExecutor
                elif mode == 'forks':
                    executor_cls = concurrent.futures.ProcessPoolExecutor
                else:
                    raise ValueError(f"Modo de proc. inválido: {mode}")

                with executor_cls(max_workers=num_workers) as executor:
                    # Usamos una tupla de un solo elemento para el wrapper
                    map_input = [(fp,) for fp in full_paths]
                    map_results = list(executor.map(process_single_file_wrapper, map_input))
                    results.extend(map_results)

                duration = time.time() - start_time_batch
                server_log(
                    f"Lote para {client_addr_log} ({event_name}) "
                    f"completado en {duration:.2f}s."
                )
                send_to_client(client_socket, {
                    "type": "PROCESSING_COMPLETE",
                    "payload": {"event": event_name, "status": "success",
                                "results": results, "duration_seconds": duration}
                })

            except Exception as e:
                server_log(f"Error en procesamiento de lote para {client_addr_log}: {e}")
                try:
                    send_to_client(client_socket, {
                        "type": "PROCESSING_COMPLETE",
                        "payload": {"event": event_name, "status": "failure",
                                    "message": str(e), "results": []}
                    })
                except: # Cliente ya podría estar desconectado
                    pass
            # El processing_lock se libera automáticamente al salir del 'with'


# --- Hilo Manejador de Cliente ---
def handle_client(client_socket, addr):
    """Maneja la comunicación con un cliente conectado."""
    server_log(f"Cliente conectado: {addr}")

    with state_lock:
        clients[client_socket] = addr
        if client_socket not in client_configs:
            client_configs[client_socket] = DEFAULT_CLIENT_CONFIG.copy()

    buffer = ""
    try:
        while True:
            try:
                data = client_socket.recv(4096)
            except ConnectionResetError:
                server_log(f"Conexión reseteada por {addr}.")
                break
            except Exception as e:
                server_log(f"Error en recv() para {addr}: {e}")
                break

            if not data:
                server_log(f"Cliente {addr} cerró conexión.")
                break

            buffer += data.decode('utf-8')

            while '\n' in buffer:
                message_str, buffer = buffer.split('\n', 1)
                if not message_str.strip():
                    continue

                try:
                    message = json.loads(message_str)
                    command = message.get("type")
                    payload = message.get("payload")
                    # server_log(f"De {addr}: {command}") # Demasiado verboso

                    if command == "SET_CONFIG":
                        if (isinstance(payload, dict) and
                                'mode' in payload and 'count' in payload):
                            mode = payload['mode']
                            count = payload['count']
                            if (mode in ['threads', 'forks'] and
                                    isinstance(count, int) and count > 0):
                                with state_lock:
                                    client_configs[client_socket] = {
                                        'mode': mode, 'count': count
                                    }
                                cfg = client_configs[client_socket]
                                # server_log(f"Config actualizada para {addr}: {cfg}")
                                send_to_client(client_socket, {
                                    "type": "ACK_CONFIG",
                                    "payload": {"status": "success", "config": cfg}
                                })
                            else:
                                send_to_client(client_socket, {
                                    "type": "ACK_CONFIG",
                                    "payload": {"status": "error",
                                                "message": "Modo/cantidad inválido."}
                                })
                        else:
                            send_to_client(client_socket, {
                                "type": "ACK_CONFIG",
                                "payload": {"status": "error",
                                            "message": "Payload SET_CONFIG inválido."}
                            })

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
                            send_to_client(client_socket,
                                           {"type": "ACK_SUB", "payload": event_name})
                        else:
                            send_to_client(client_socket,
                                           {"type": "ERROR", "payload": "SUB inválido."})

                    elif command == "UNSUB":
                        event_name = payload
                        if isinstance(event_name, str) and event_name:
                            with state_lock:
                                if event_name in events:
                                    events[event_name].discard(client_socket)
                                if event_name in client_queues:
                                    # Reconstruir la cola sin el cliente
                                    new_q = collections.deque(
                                        [s for s in client_queues[event_name]
                                         if s != client_socket]
                                    )
                                    client_queues[event_name] = new_q
                            send_to_client(client_socket,
                                           {"type": "ACK_UNSUB", "payload": event_name})
                        else:
                             send_to_client(client_socket,
                                            {"type": "ERROR", "payload": "UNSUB inválido."})

                except json.JSONDecodeError:
                    server_log(f"JSON inválido de {addr}: '{message_str}'")
                except Exception as e:
                    server_log(f"Error procesando msg de {addr}: {e}")
    finally:
        handle_disconnect(client_socket)


# --- Hilo de Comandos del Servidor ---

def print_help():
    print("\n--- Comandos del Servidor ---")
    print("  help                          - Muestra esta ayuda.")
    print("  add <nombre_evento>           - Crea un nuevo evento.")
    print("  remove <nombre_evento>        - Elimina un evento y su cola.")
    print("  trigger <nombre_evento>       - Dispara un evento para los clientes en cola.")
    print("  list                          - Muestra estado de eventos, colas y clientes.")
    print("  status                        - Muestra si el servidor está Ocupado o Idle.")
    print("  exit                          - Cierra el servidor y notifica a los clientes.")
    print("-----------------------------\n")


def server_commands():
    """Maneja comandos ingresados en la terminal del servidor."""
    print_help() # Mostrar ayuda al inicio

    while True:
        try:
            # El prompt se imprime por input(). Si un log interfiere,
            # el usuario presiona Enter para "ver" el prompt de nuevo.
            cmd_input = input("Server> ").strip()

            if not cmd_input:
                continue

            parts = cmd_input.split()
            command = parts[0].lower()

            print() # Línea en blanco después del input para separar la salida

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
                            client_queues[event_name].clear() # Vaciarla
                            del client_queues[event_name]
                        print(f"Evento '{event_name}' y su cola eliminados.")
                    else:
                        print(f"Evento '{event_name}' no encontrado.")

            elif command == "list":
                with state_lock:
                    print("--- Estado del Servidor ---")
                    print("\nEventos y Suscriptores:")
                    if not events: print("  (Ninguno)")
                    for ev, subs in events.items():
                        addrs = [str(clients.get(s, "N/A")) for s in subs]
                        print(f"- {ev}: {len(subs)} subs -> {addrs}")

                    print("\nColas de Eventos (Clientes en Espera):")
                    if not client_queues: print("  (Ninguna)")
                    for ev, q in client_queues.items():
                        q_addrs = [str(clients.get(s, "N/A")) for s in q]
                        print(f"- {ev}: {len(q)} en cola -> {q_addrs}")

                    print("\nClientes Conectados y su Configuración:")
                    if not clients: print("  (Ninguno)")
                    for sock, addr in clients.items():
                        cfg = client_configs.get(sock, "N/A")
                        print(f"- {addr}: {cfg}")
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
                    if (event_name not in client_queues or
                            not client_queues[event_name]):
                        print(f"Sin clientes en espera para '{event_name}'.")
                        continue

                    clients_in_q_snapshot = list(client_queues[event_name])
                    client_queues[event_name].clear() # Clientes serán procesados

                    for sock in clients_in_q_snapshot:
                        if sock in clients and sock in client_configs:
                            active_clients_for_event.append(sock)
                        else:
                            print(f"Cliente {str(clients.get(sock))} de '{event_name}' omitido (desconectado/sin config).")

                if not active_clients_for_event:
                    print(f"Sin clientes válidos activos para procesar '{event_name}'.")
                    continue

                try:
                    all_files = [
                        f for f in os.listdir(TEXT_FILES_DIR)
                        if f.endswith(".txt") and
                        os.path.isfile(os.path.join(TEXT_FILES_DIR, f))
                    ]
                except Exception as e:
                    print(f"Error listando archivos para '{event_name}': {e}")
                    continue

                if not all_files:
                    print(f"Sin archivos .txt en '{TEXT_FILES_DIR}' para '{event_name}'.")
                    for sock in active_clients_for_event:
                        send_to_client(sock, {
                            "type": "PROCESSING_COMPLETE",
                            "payload": {"event": event_name, "status": "success",
                                        "message": "No files to process.", "results": []}
                        })
                    continue

                num_clients = len(active_clients_for_event)
                total_files = len(all_files)
                start_idx = 0
                batches_created = 0

                for i, client_sock in enumerate(active_clients_for_event):
                    # Distribuir archivos
                    files_this_client = total_files // num_clients
                    if i < (total_files % num_clients):
                        files_this_client += 1

                    end_idx = start_idx + files_this_client
                    assigned_files = all_files[start_idx:end_idx]
                    start_idx = end_idx

                    if not assigned_files: # Si un cliente no obtiene archivos
                        send_to_client(client_sock, {
                            "type": "PROCESSING_COMPLETE",
                            "payload": {"event": event_name, "status": "success",
                                        "message": "No files assigned for this trigger.",
                                        "results": []}
                        })
                        continue

                    client_cfg = None
                    with state_lock: # Obtener la última config del cliente
                        client_cfg = client_configs.get(client_sock)

                    if client_cfg:
                        batch = (client_sock, assigned_files, event_name, client_cfg)
                        with state_lock: # Proteger la cola de lotes
                            client_batch_processing_queue.append(batch)
                        batches_created += 1
                    else:
                        print(
                            f"Cliente {clients.get(client_sock)} ya no tiene config. Lote descartado."
                        )

                if batches_created > 0:
                    new_batch_event.set() # Notificar al hilo trabajador
                print(
                    f"{batches_created} lotes para '{event_name}' añadidos a cola de procesamiento."
                )

            elif command == "exit":
                print("Cerrando servidor...")
                new_batch_event.set() # Despertar al hilo trabajador
                time.sleep(0.5) # Dar tiempo a que reaccione

                with state_lock:
                    client_list = list(clients.keys())

                for sock in client_list:
                    send_to_client(sock, {"type": "SERVER_EXIT", "payload": None})
                    time.sleep(0.1) # Pequeña pausa para envío
                    handle_disconnect(sock)

                server_socket.close()
                print("Servidor terminado.")
                os._exit(0) # Salida forzada

            else:
                print("Comando desconocido. Escribe 'help' para ver la lista.")

            print() # Línea en blanco antes del siguiente prompt

        except EOFError: # Ctrl+D
            print("\nCerrando servidor por EOF...")
            new_batch_event.set()
            time.sleep(0.5)
            with state_lock:
                client_list = list(clients.keys())
            for sock in client_list:
                try:
                    send_to_client(sock, {"type": "SERVER_EXIT", "payload": None})
                except:
                    pass # Ignorar errores al notificar cierre
                handle_disconnect(sock)
            server_socket.close()
            os._exit(0)

        except Exception as e:
            print(f"Error en bucle de comandos del servidor: {e}")


# --- Iniciar Hilos del Servidor ---
command_thread = threading.Thread(target=server_commands, daemon=True)
command_thread.start()

batch_worker_thread = threading.Thread(
    target=manage_client_batch_processing, daemon=True
)
batch_worker_thread.start()

# --- Bucle Principal para Aceptar Clientes ---
try:
    while True:
        try:
            client_sock, client_addr = server_socket.accept()
            client_handler_thread = threading.Thread(
                target=handle_client, args=(client_sock, client_addr), daemon=True
            )
            client_handler_thread.start()
        except OSError as e:
            # Esto puede ocurrir si el socket se cierra mientras accept() está bloqueado
            print(f"Error aceptando conexión (puede ser normal al cerrar): {e}")
            break
        except Exception as e:
            print(f"Error inesperado en bucle de aceptación: {e}")
            time.sleep(1) # Prevenir spinning rápido en errores continuos

except KeyboardInterrupt:
    print("\nCerrando servidor por KeyboardInterrupt...")
    new_batch_event.set() # Notificar al worker para que pueda salir si está esperando
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
    if server_socket and not getattr(server_socket, '_closed', True):
        try:
            server_socket.close()
            print("Socket del servidor cerrado en bloque finally.")
        except Exception: # e:
            # print(f"Error cerrando socket del servidor en finally: {e}")
            pass
