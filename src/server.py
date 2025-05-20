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
import logging
from .extractor_regex import parse_file_regex as parse_file

# --- Configuración del Logger ---
LOG_FILENAME = 'server_processing.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILENAME,
    filemode='a'  # 'a' para append, 'w' para overwrite en cada inicio
)

# --- Configuración ---
HOST = '127.0.0.1'
PORT = 65432
import os

TEXT_FILES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'text_files'))
print(f"[DEBUG] Buscando en ruta: {TEXT_FILES_DIR}")

# Asegúrate de que la carpeta exista
if not os.path.isdir(TEXT_FILES_DIR):
    try:
        os.makedirs(TEXT_FILES_DIR)
        print(f"[DEBUG] Carpeta '{TEXT_FILES_DIR}' creada.")
    except Exception as e:
        print(f"[ERROR] No se pudo crear la carpeta '{TEXT_FILES_DIR}': {e}")
        exit(1)
else:
    print(f"[DEBUG] Carpeta ya existe.")

# Ahora sí, carga los archivos
text_files = [f for f in os.listdir(TEXT_FILES_DIR) if f.endswith('.txt')]
print(f"[DEBUG] Archivos encontrados: {text_files}")

DEFAULT_CLIENT_CONFIG = {'mode': 'threads', 'count': 1}

# --- Estado del Servidor (Protegido por Locks) ---
state_lock = threading.Lock()
events: dict[str, set] = {}
client_configs: dict = {}
client_queues: dict[str, collections.deque] = {}
clients: dict = {}
client_ids: dict = {}  # Mapeo socket -> ID del cliente
next_client_id = 1  # ID para el próximo cliente que se conecte

processing_lock = threading.Lock()
client_batch_processing_queue = collections.deque()
new_batch_event = threading.Event()

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
        
        # Recopilamos toda la información necesaria mientras tenemos el lock
        with state_lock:
            if not clients:
                print("  No hay clientes conectados.")
                return
                
            # Recopilamos la información primero con el lock
            for sock, addr in clients.items():
                client_id = client_ids.get(sock, "?")
                events_for_client = []
                for event_name, subscribers in events.items():
                    if sock in subscribers:
                        events_for_client.append(event_name)
                client_info.append((client_id, events_for_client))
        
        # Ya fuera del lock, procesamos la información
        for client_id, subscribed_events in client_info:
            if subscribed_events:
                events_str = ", ".join(subscribed_events)
                print(f"  Cliente {client_id} suscrito a: {events_str}")
            else:
                print(f"  Cliente {client_id} no está suscrito a ningún evento.")
    except Exception as e:
        print(f"  Error al mostrar suscripciones: {e}")

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
    client_id_disconnected = None
    processed_disconnect = False # Flag para evitar logs duplicados

    with state_lock:
        if client_socket in clients: # Solo procesar si el cliente aún está "registrado"
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
                        # Evitar log dentro de log si esto viene de send_to_client
                        print(f"\nError removiendo de cola '{event_name}': {e}")
        # else: El cliente ya fue procesado por otro hilo de desconexión

    if processed_disconnect and addr_disconnected:
        server_log(f"Cliente {client_id_disconnected} ({addr_disconnected}) desconectado o removido.")

    try:
        if client_socket.fileno() != -1:
            client_socket.close()
    except Exception:
        pass # El socket podría ya estar cerrado, es un error esperado


def process_single_file_wrapper(arg_tuple):
    filepath, processing_mode = arg_tuple
    filename_base = os.path.basename(filepath)

    pid_label = ""
    worker_id_str = ""

    if processing_mode == 'threads':
        pid_label = "THREAD ID"
        worker_id_str = str(threading.get_ident())
    elif processing_mode == 'forks':
        pid_label = "FORK PID"
        worker_id_str = str(os.getpid())
    else:
        pid_label = "UNKNOWN WORKER ID"
        worker_id_str = "N/A"

    descriptive_worker_id = f"{pid_label}_{worker_id_str}"

    # --- Mensaje de inicio a CONSOLA ---
    # print(f"\n[{pid_label}: {worker_id_str}] Iniciando procesamiento de: {filename_base}")
    sys.stdout.flush()
    # --- Fin mensaje de inicio a CONSOLA ---

    # Log de inicio al ARCHIVO DE LOG
    logging.info(f"[{descriptive_worker_id}] Iniciando procesamiento de archivo: {filepath}")

    try:
        # Llamar a tu función de extracción Regex
        # Tu función parse_file podría tener sus propios prints.
        # Si quieres que esos también vayan al log, necesitarías modificarla
        # para que acepte un logger o use el logger global.
        raw_result_from_extractor = parse_file(filepath, pid=descriptive_worker_id)
        
        # Ejemplo de log de detalles del extractor al ARCHIVO DE LOG
        logging.info(f"[{descriptive_worker_id}] Datos extraídos de {filename_base}: "
                     f"Emails: {len(raw_result_from_extractor.get('Emails', []))}, "
                     f"Fechas: {len(raw_result_from_extractor.get('Fechas', []))}, "
                     f"Palabras: {raw_result_from_extractor.get('ConteoPalabras', 0)}")


        status_from_extractor = raw_result_from_extractor.get("status",
                                raw_result_from_extractor.get("estado", "error"))
        error_from_extractor = raw_result_from_extractor.get("error", "")
        
        final_filename = raw_result_from_extractor.get("filename",
                           raw_result_from_extractor.get("archivo", filename_base))

        if status_from_extractor == "success":
            # --- Mensaje de fin a CONSOLA ---
            # print(f"\n[{pid_label}: {worker_id_str}] Finalizado procesamiento de: {final_filename} (Éxito)")
            # sys.stdout.flush()
            # --- Fin mensaje de fin a CONSOLA ---
            logging.info(f"[{descriptive_worker_id}] Finalizado procesamiento de {final_filename} con ÉXITO.")

            data_for_client = {
                "emails_found": raw_result_from_extractor.get("Emails", []),
                "dates_found": raw_result_from_extractor.get("Fechas", []),
                "word_count": raw_result_from_extractor.get("ConteoPalabras", 0)
            }
            
            final_result_for_server = {
                "pid_server": descriptive_worker_id,
                "filename": final_filename,
                "data": data_for_client,
                "status": "success",
                "error": "" 
            }
        else: # Error ocurrió dentro de parse_file
            # --- Mensaje de fin a CONSOLA (con error del extractor) ---
            print(f"\n[{pid_label}: {worker_id_str}] Error durante extracción para {final_filename} (ver log).")
            sys.stdout.flush()
            # --- Fin mensaje de fin a CONSOLA ---
            logging.error(f"[{descriptive_worker_id}] Error durante extracción para {final_filename}: {error_from_extractor}")
            
            final_result_for_server = {
                "pid_server": descriptive_worker_id,
                "filename": final_filename,
                "data": {"emails_found": [], "dates_found": [], "word_count": 0},
                "status": "error",
                "error": error_from_extractor
            }
        return final_result_for_server

    except Exception as e:
        # --- Mensaje de fin a CONSOLA (con error INESPERADO en wrapper) ---
        print(f"\n[{pid_label}: {worker_id_str}] Error INESPERADO en wrapper para {filename_base} (ver log).")
        sys.stdout.flush()
        # --- Fin mensaje de fin a CONSOLA ---
        logging.error(
            f"[{descriptive_worker_id}] Error INESPERADO en wrapper para {filename_base}: {type(e).__name__} - {e}",
            exc_info=True # Incluye el traceback en el log
        )
        return {
            "pid_server": descriptive_worker_id,
            "filename": filename_base,
            "data": {"emails_found": [], "dates_found": [], "word_count": 0},
            "status": "error",
            "error": f"Error inesperado en wrapper: {str(e)}"
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
                    f"Cliente para lote de '{event_name}' ya no conectado. Lote descartado."
                )

        if not is_client_valid or not assigned_files:
            continue

        with processing_lock:
            start_time_batch = time.time()
            results = []
            # Para almacenar los PIDs/IDs de los workers que participaron en este lote
            worker_identifiers_used = set() # Usamos un set para evitar duplicados

            try:
                send_to_client(client_socket, {
                    "type": "START_PROCESSING",
                    "payload": {"event": event_name, "files": assigned_files}
                })

                num_workers = config.get('count', DEFAULT_CLIENT_CONFIG['count'])
                processing_mode = config.get('mode', DEFAULT_CLIENT_CONFIG['mode'])
                if num_workers < 1:
                    num_workers = 1

                full_paths = [
                    os.path.join(TEXT_FILES_DIR, f) for f in assigned_files
                ]

                executor_cls = None
                if processing_mode == 'threads':
                    executor_cls = concurrent.futures.ThreadPoolExecutor
                elif processing_mode == 'forks':
                    executor_cls = concurrent.futures.ProcessPoolExecutor
                else:
                    raise ValueError(f"Modo de proc. inválido: {processing_mode}")

                with executor_cls(max_workers=num_workers) as executor:
                    map_input = [(fp, processing_mode) for fp in full_paths]
                    
                    # executor.map devuelve un iterador. Lo convertimos a lista
                    # para asegurar que todos los trabajos se completen antes de continuar.
                    # Esto también nos permite acceder a los resultados para obtener los PIDs.
                    map_results_list = list(executor.map(process_single_file_wrapper, map_input))
                    
                    results.extend(map_results_list)

                    # Recopilar los PIDs/IDs de los workers de los resultados
                    for res_item in map_results_list:
                        if "pid_server" in res_item:
                            worker_identifiers_used.add(res_item["pid_server"])


                duration = time.time() - start_time_batch
                server_log( # ESTA ES LA LÍNEA QUE MENCIONASTE
                    f"Lote para {client_addr_log} ({event_name}) "
                    f"completado en {duration:.2f}s."
                )

                # --- IMPRIMIR LOS WORKERS UTILIZADOS ---
                if worker_identifiers_used:
                    # El log ya imprime una nueva línea antes.
                    # Ajustamos el mensaje para que sea más legible.
                    # server_log(f"    Workers utilizados para este lote: {sorted(list(worker_identifiers_used))}")
                    print(f"    Workers utilizados para este lote ({processing_mode}):")
                    for worker_id_str in sorted(list(worker_identifiers_used)):
                        print(f"      - {worker_id_str}")
                    sys.stdout.flush() # Asegurar que se imprima
                # --- FIN DE IMPRIMIR WORKERS ---


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
                except:
                    pass
            # El processing_lock se libera automáticamente

# --- Hilo Manejador de Cliente ---
def handle_client(client_socket, addr):
    """Maneja la comunicación con un cliente conectado."""
    global next_client_id
    
    # Asignar ID al cliente
    client_id = next_client_id
    next_client_id += 1
    
    with state_lock:
        clients[client_socket] = addr
        client_ids[client_socket] = client_id
        if client_socket not in client_configs:
            client_configs[client_socket] = DEFAULT_CLIENT_CONFIG.copy()
    
    server_log(f"Cliente {client_id} conectado desde {addr}")

    # Enviar mensaje de bienvenida con ID asignado
    send_to_client(client_socket, {
        "type": "WELCOME",
        "payload": {
            "server_info": {"version": "1.0"},
            "client_id": client_id
        }
    })

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

            buffer += data.decode('utf-8')

            while '\n' in buffer:
                message_str, buffer = buffer.split('\n', 1)
                if not message_str.strip():
                    continue

                try:
                    message = json.loads(message_str)
                    command = message.get("type")
                    payload = message.get("payload")

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
                            
                            # Mostrar mensaje de suscripción
                            server_log(f"Cliente {client_id} suscrito a evento '{event_name}'")
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
                                    new_q = collections.deque(
                                        [s for s in client_queues[event_name]
                                         if s != client_socket]
                                    )
                                    client_queues[event_name] = new_q
                            
                            # Mostrar mensaje de desuscripción
                            server_log(f"Cliente {client_id} desuscrito de evento '{event_name}'")
                            send_to_client(client_socket,
                                           {"type": "ACK_UNSUB", "payload": event_name})
                        else:
                             send_to_client(client_socket,
                                            {"type": "ERROR", "payload": "UNSUB inválido."})

                    elif command == "PROCESS_FILES":
                        event_name = payload.get("event", "sin_evento")
                        files = payload.get("files", [])

                        if not files:
                            send_to_client(client_socket, {
                                "type": "PROCESSING_COMPLETE",
                                "payload": {
                                    "event": event_name,
                                    "status": "success",
                                    "message": "No files provided.",
                                    "results": []
                                }
                            })
                            continue

                        try:
                            full_paths = [
                                os.path.join(TEXT_FILES_DIR, f) for f in files
                                if os.path.isfile(os.path.join(TEXT_FILES_DIR, f))
                            ]

                            num_workers = client_configs.get(client_socket, {}).get('count', 2)
                            mode = client_configs.get(client_socket, {}).get('mode', 'threads')

                            executor_cls = (
                                concurrent.futures.ThreadPoolExecutor
                                if mode == 'threads'
                                else concurrent.futures.ProcessPoolExecutor
                            )

                            with executor_cls(max_workers=num_workers) as executor:
                                map_input = [(fp,) for fp in full_paths]
                                map_results = list(executor.map(process_single_file_wrapper, map_input))

                            send_to_client(client_socket, {
                                "type": "PROCESSING_COMPLETE",
                                "payload": {
                                    "event": event_name,
                                    "status": "success",
                                    "results": map_results,
                                    "duration_seconds": 0
                                }
                            })

                        except Exception as e:
                            send_to_client(client_socket, {
                                "type": "PROCESSING_COMPLETE",
                                "payload": {
                                    "event": event_name,
                                    "status": "failure",
                                    "message": str(e),
                                    "results": []
                                }
                            })

                except json.JSONDecodeError:
                    server_log(f"JSON inválido de {addr}: '{message_str}'")
                except Exception as e:
                    server_log(f"Error procesando msg de {addr}: {e}")
    finally:
        handle_disconnect(client_socket)


def print_help():
    print("\n--- Comandos del Servidor ---")
    print("  help                          - Muestra esta ayuda.")
    print("  add <nombre_evento>           - Crea un nuevo evento.")
    print("  remove <nombre_evento>        - Elimina un evento y su cola.")
    print("  trigger <nombre_evento>       - Dispara un evento para los clientes en cola.")
    print("  list                          - Muestra estado de eventos, colas y clientes.")
    print("  clients                       - Muestra clientes y sus eventos suscritos.")
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
                    if not events: print("  (Ninguno)")
                    for ev, subs in events.items():
                        client_id_list = [f"Cliente {client_ids.get(s, '?')}" for s in subs]
                        print(f"- {ev}: {len(subs)} subs -> {client_id_list}")

                    print("\nColas de Eventos (Clientes en Espera):")
                    if not client_queues: print("  (Ninguna)")
                    for ev, q in client_queues.items():
                        q_client_ids = [f"Cliente {client_ids.get(s, '?')}" for s in q]
                        print(f"- {ev}: {len(q)} en cola -> {q_client_ids}")

                    print("\nClientes Conectados y su Configuración:")
                    if not clients: print("  (Ninguno)")
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
