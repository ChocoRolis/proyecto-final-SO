# server.py
import socket
import threading
import json # Usar JSON para mensajes estructurados es buena idea

HOST = '127.0.0.1'
PORT = 65432

events = {} # event_name -> set(client_socket)
clients = {} # client_socket -> client_addr
client_configs = {} # client_socket -> {'threads': 2} # Default config
global_threads_config = 2 # Default global config

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()

print(f"Servidor escuchando en {HOST}:{PORT}")

def send_to_client(client_socket, message):
    try:
        client_socket.sendall(json.dumps(message).encode('utf-8'))
    except (BrokenPipeError, ConnectionResetError):
        print(f"Error al enviar a {clients.get(client_socket, 'desconocido')}. Cliente desconectado.")
        handle_disconnect(client_socket)
    except Exception as e:
        print(f"Error enviando mensaje: {e}")
        handle_disconnect(client_socket)

def handle_disconnect(client_socket):
    addr = clients.pop(client_socket, None)
    if addr:
        print(f"Cliente {addr} desconectado.")
    # Eliminar de todas las suscripciones
    for event in events:
        events[event].discard(client_socket)
    client_configs.pop(client_socket, None)
    try:
        client_socket.close()
    except Exception as e:
        print(f"Error cerrando socket: {e}")


def handle_client(client_socket, addr):
    global global_threads_config
    print(f"Cliente conectado: {addr}")
    clients[client_socket] = addr
    # Enviar config inicial (o el cliente la pide con GET_CONFIG)
    client_configs[client_socket] = {'threads': global_threads_config}
    send_to_client(client_socket, {"type": "CONFIG", "payload": {"threads": global_threads_config}})

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break # Cliente desconectado

            try:
                message = json.loads(data.decode('utf-8'))
                command = message.get("type")
                payload = message.get("payload")

                print(f"Recibido de {addr}: {message}") # Debug

                if command == "SUB":
                    event_name = payload
                    if event_name not in events:
                        events[event_name] = set()
                    events[event_name].add(client_socket)
                    print(f"Cliente {addr} suscrito a {event_name}")
                    send_to_client(client_socket, {"type": "ACK_SUB", "payload": event_name})

                elif command == "UNSUB":
                    event_name = payload
                    if event_name in events:
                        events[event_name].discard(client_socket)
                        print(f"Cliente {addr} desuscrito de {event_name}")
                        send_to_client(client_socket, {"type": "ACK_UNSUB", "payload": event_name})

                elif command == "GET_CONFIG":
                     send_to_client(client_socket, {"type": "CONFIG", "payload": {"threads": client_configs.get(client_socket, {}).get('threads', global_threads_config)}})

                elif command == "PROGRESS": # Cliente notifica progreso
                    print(f"Progreso de {addr}: {payload}")
                    # Podrías hacer algo con esta info, como reenviarla a una GUI central si existiera

                # Añadir más comandos si es necesario

            except json.JSONDecodeError:
                print(f"Error decodificando JSON de {addr}")
            except Exception as e:
                 print(f"Error procesando mensaje de {addr}: {e}")

    except (ConnectionResetError, BrokenPipeError):
        print(f"Conexión perdida con {addr}")
    except Exception as e:
        print(f"Error inesperado con cliente {addr}: {e}")
    finally:
        handle_disconnect(client_socket)


def server_commands():
    global global_threads_config
    while True:
        try:
            cmd_input = input("Server> ").strip().split()
            if not cmd_input: continue
            command = cmd_input[0].lower()

            if command == "add" and len(cmd_input) > 1:
                event_name = cmd_input[1]
                if event_name not in events:
                    events[event_name] = set()
                    print(f"Evento '{event_name}' creado.")
                else:
                    print(f"Evento '{event_name}' ya existe.")

            elif command == "remove" and len(cmd_input) > 1:
                event_name = cmd_input[1]
                if event_name in events:
                    # Opcional: Notificar a los suscritos antes de eliminar?
                    del events[event_name]
                    print(f"Evento '{event_name}' eliminado.")
                else:
                    print(f"Evento '{event_name}' no encontrado.")

            elif command == "trigger" and len(cmd_input) > 1:
                event_name = cmd_input[1]
                if event_name in events:
                    print(f"Disparando evento '{event_name}' a {len(events[event_name])} clientes...")
                    # Hacemos una copia por si el set cambia durante la iteración (debido a desconexiones)
                    subscribers = list(events[event_name])
                    for sock in subscribers:
                        send_to_client(sock, {"type": "TRIGGER", "payload": event_name})
                else:
                    print(f"Evento '{event_name}' no encontrado.")

            elif command == "set_threads" and len(cmd_input) > 1:
                 try:
                     num_threads = int(cmd_input[1])
                     if num_threads > 0:
                         global_threads_config = num_threads
                         print(f"Configuración global de threads establecida a {num_threads}.")
                         # Opcional: Enviar la nueva config a todos los clientes conectados
                         print("Enviando nueva configuración a los clientes...")
                         client_list = list(clients.keys()) # Copia para evitar problemas si hay desconexiones
                         for sock in client_list:
                             client_configs[sock] = {'threads': global_threads_config}
                             send_to_client(sock, {"type": "CONFIG", "payload": {"threads": global_threads_config}})
                     else:
                         print("El número de threads debe ser positivo.")
                 except ValueError:
                     print("Uso: set_threads <numero>")


            elif command == "list":
                 print("Eventos y suscriptores:")
                 for event, subscribers in events.items():
                     print(f"- {event}: {len(subscribers)} suscriptores")
                 print("Clientes conectados:")
                 for sock, addr in clients.items():
                     print(f"- {addr} (Threads: {client_configs.get(sock, {}).get('threads', 'N/A')})")


            elif command == "exit":
                print("Cerrando servidor...")
                client_list = list(clients.keys()) # Copia
                for sock in client_list:
                    send_to_client(sock, {"type": "SERVER_EXIT", "payload": None})
                    handle_disconnect(sock) # Cierra la conexión
                server_socket.close()
                print("Servidor cerrado.")
                # Forzar salida del hilo de comandos (y del programa)
                # Esto es un poco brusco, idealmente los hilos deberían terminar limpiamente
                import os
                os._exit(0)


            else:
                print("Comando desconocido o inválido.")
                print("Comandos: add <evt>, remove <evt>, trigger <evt>, set_threads <N>, list, exit")

        except EOFError: # Ctrl+D
             print("\nCerrando servidor por EOF...")
             # Código de cierre similar a 'exit'
             client_list = list(clients.keys())
             for sock in client_list:
                 try: send_to_client(sock, {"type": "SERVER_EXIT", "payload": None})
                 except: pass # Ignorar errores al cerrar
                 handle_disconnect(sock)
             server_socket.close()
             print("Servidor cerrado.")
             import os
             os._exit(0) # Salida forzada
        except Exception as e:
            print(f"Error en el bucle de comandos del servidor: {e}")


# Iniciar hilo para comandos de servidor
command_thread = threading.Thread(target=server_commands, daemon=True)
command_thread.start()

# Bucle principal para aceptar clientes
try:
    while True:
        client_sock, client_addr = server_socket.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_sock, client_addr), daemon=True)
        client_handler.start()
except KeyboardInterrupt:
    print("\nCerrando servidor por KeyboardInterrupt...")
    # Código de cierre similar a 'exit'
    client_list = list(clients.keys())
    for sock in client_list:
        try: send_to_client(sock, {"type": "SERVER_EXIT", "payload": None})
        except: pass
        handle_disconnect(sock)
    server_socket.close()
    print("Servidor cerrado.")
except Exception as e:
    print(f"Error en el bucle principal del servidor: {e}")
finally:
     if not server_socket._closed:
         server_socket.close()
