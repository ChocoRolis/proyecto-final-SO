---

```markdown
# Documentación del Código Fuente: `src/server.py`

Este documento explica el funcionamiento interno del script `server.py`, que actúa como el componente servidor en nuestro sistema de eventos y scheduling.

## Propósito General

El servidor es el núcleo central del sistema. Sus responsabilidades principales son:

1.  **Escuchar Conexiones:** Esperar y aceptar conexiones TCP entrantes de los clientes (`client_gui.py`).
2.  **Gestionar Múltiples Clientes:** Utilizar hilos (`threading`) para manejar a cada cliente conectado de forma concurrente, sin que uno bloquee a los demás.
3.  **Administrar Eventos:** Mantener un registro de los eventos existentes y qué clientes están suscritos a cada uno.
4.  **Procesar Comandos:** Recibir y ejecutar comandos tanto desde su propia terminal (para administración) como desde los clientes (suscripciones, etc.).
5.  **Notificar a Clientes:** Enviar mensajes a los clientes relevantes cuando ocurren acciones (ej. un `trigger` de evento, un cambio de configuración, o el cierre del servidor).
6.  **Gestionar Configuración:** Mantener y distribuir la configuración compartida (como el número de "threads" simulados para los clientes).

## Componentes Clave y Flujo

### 1. Imports y Variables Globales

```python
import socket
import threading
import json
import os # Usado para os._exit

# Configuración de Red
HOST = '127.0.0.1'  # Escucha solo en la máquina local
PORT = 65432        # Puerto para las conexiones

# Estado Compartido del Servidor (¡Importante!)
events = {}         # Diccionario: event_name (str) -> set(client_socket)
clients = {}        # Diccionario: client_socket -> client_addr (tuple)
client_configs = {} # Diccionario: client_socket -> {'threads': int}
global_threads_config = 2 # Configuración por defecto de threads para nuevos clientes
```

*   **Imports:** Se usan las librerías estándar:
    *   `socket`: Para la comunicación de red TCP.
    *   `threading`: Para manejar múltiples clientes y la entrada de comandos simultáneamente.
    *   `json`: Para codificar/decodificar los mensajes enviados/recibidos en un formato estándar.
    *   `os`: Utilizado específicamente para `os._exit()` en el comando `exit`, que fuerza la terminación del proceso (una medida un poco drástica, pero efectiva aquí).
*   **Variables Globales:** Estas estructuras almacenan el estado *compartido* del servidor. Como múltiples hilos (uno por cliente, más el de comandos) accederán y modificarán estas variables, son cruciales para el funcionamiento.
    *   `events`: Guarda qué sockets de clientes están interesados en qué eventos. Usar un `set` es eficiente para añadir/eliminar suscriptores y evitar duplicados.
    *   `clients`: Mapea el objeto `socket` de un cliente a su dirección (`(ip, puerto)`), útil para logging e identificación.
    *   `client_configs`: Almacena la configuración específica enviada a cada cliente (en este caso, el número de threads).
    *   `global_threads_config`: El valor por defecto o el último valor global establecido para los threads simulados.

### 2. Configuración Inicial del Socket del Servidor

```python
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()
print(f"Servidor escuchando en {HOST}:{PORT}")
```

*   Se crea un socket TCP (`socket.AF_INET`, `socket.SOCK_STREAM`).
*   `bind()` asocia el socket a la dirección IP (`HOST`) y puerto (`PORT`) definidos.
*   `listen()` pone el socket en modo de escucha, listo para aceptar conexiones entrantes.

### 3. Funciones Auxiliares

#### `send_to_client(client_socket, message)`

```python
def send_to_client(client_socket, message):
    try:
        # Codifica el mensaje (un diccionario Python) a JSON y luego a bytes UTF-8
        client_socket.sendall(json.dumps(message).encode('utf-8'))
    except (BrokenPipeError, ConnectionResetError):
        # Error común si el cliente se desconectó abruptamente
        print(f"Error al enviar a {clients.get(client_socket, 'desconocido')}. Cliente desconectado.")
        handle_disconnect(client_socket) # Limpia el estado del cliente
    except Exception as e:
        print(f"Error enviando mensaje: {e}")
        handle_disconnect(client_socket) # Asume desconexión en otros errores
```

*   Esta función centraliza el envío de mensajes.
*   Toma un diccionario Python (`message`), lo convierte a una cadena JSON, lo codifica a bytes (`utf-8`), y lo envía por el socket del cliente.
*   Incluye manejo de errores básico para cuando el cliente ya no está conectado, llamando a `handle_disconnect` para limpiar.

#### `handle_disconnect(client_socket)`

```python
def handle_disconnect(client_socket):
    # Elimina al cliente de todas las estructuras de datos globales
    addr = clients.pop(client_socket, None)
    if addr:
        print(f"Cliente {addr} desconectado.")
    # Quita al cliente de todas las listas de suscripción de eventos
    for event in events:
        events[event].discard(client_socket) # discard no da error si no existe
    client_configs.pop(client_socket, None)
    try:
        client_socket.close() # Cierra el socket del servidor para ese cliente
    except Exception as e:
        print(f"Error cerrando socket: {e}")
```

*   Función clave para la limpieza cuando un cliente se va (o se detecta un error).
*   Elimina las referencias al `client_socket` de los diccionarios `clients`, `client_configs` y de todos los `set` de suscripción en `events`.
*   Finalmente, cierra el objeto `socket` asociado a ese cliente.

### 4. Manejo de Clientes Individuales: `handle_client(client_socket, addr)`

```python
def handle_client(client_socket, addr):
    # ... (Código para añadir cliente a 'clients' y enviar config inicial) ...
    try:
        while True: # Bucle principal para recibir mensajes de este cliente
            data = client_socket.recv(1024) # Espera bloqueante hasta recibir datos
            if not data:
                break # Cliente cerró la conexión limpiamente

            try:
                message = json.loads(data.decode('utf-8')) # Decodifica JSON
                command = message.get("type")
                payload = message.get("payload")

                # --- Lógica para procesar comandos del cliente ---
                if command == "SUB":
                    # Añadir cliente a la lista de suscripción del evento
                elif command == "UNSUB":
                    # Quitar cliente de la lista de suscripción
                elif command == "GET_CONFIG":
                    # Enviar la configuración actual de threads
                elif command == "PROGRESS":
                    # Simplemente imprime el progreso recibido (podría hacer más)
                # ... (otros comandos si se añaden) ...

            except json.JSONDecodeError: # Mensaje no es JSON válido
            except Exception as e: # Otro error procesando

    except (ConnectionResetError, BrokenPipeError): # El cliente se desconectó
    except Exception as e: # Error inesperado
    finally:
        handle_disconnect(client_socket) # Asegura la limpieza SIEMPRE
```

*   Esta función se ejecuta en un **hilo separado para cada cliente conectado**.
*   Registra al cliente y le envía su configuración inicial (`global_threads_config`).
*   Entra en un bucle infinito que:
    *   Espera recibir datos con `client_socket.recv(1024)`. Esta llamada es **bloqueante** (el hilo espera aquí hasta que lleguen datos o haya un error).
    *   Si `recv` devuelve datos vacíos, significa que el cliente cerró la conexión.
    *   Intenta decodificar los datos recibidos como JSON.
    *   Procesa el mensaje basándose en el campo `"type"` (el comando). Modifica el estado global (`events`) según sea necesario (`SUB`, `UNSUB`) o envía respuestas (`GET_CONFIG`).
    *   Maneja errores de JSON o de conexión.
*   El bloque `finally` asegura que `handle_disconnect` se llame siempre que el hilo termine (ya sea por desconexión normal, error, etc.).

### 5. Manejo de Comandos del Servidor: `server_commands()`

```python
def server_commands():
    global global_threads_config # Necesita modificar la config global
    while True:
        try:
            cmd_input = input("Server> ").strip().split()
            # ... (validación de entrada) ...
            command = cmd_input[0].lower()

            # --- Lógica para procesar comandos de la terminal ---
            if command == "add" and len(cmd_input) > 1:
                # Añade un nuevo evento (si no existe) al diccionario 'events'
            elif command == "remove" and len(cmd_input) > 1:
                # Elimina un evento del diccionario 'events'
            elif command == "trigger" and len(cmd_input) > 1:
                # Obtiene la lista de sockets suscritos a ese evento
                # Itera y llama a send_to_client para enviar el TRIGGER a cada uno
            elif command == "set_threads" and len(cmd_input) > 1:
                # Actualiza 'global_threads_config'
                # Opcionalmente, notifica a TODOS los clientes conectados de la nueva config
            elif command == "list":
                # Muestra información sobre eventos y clientes conectados
            elif command == "exit":
                # Notifica a TODOS los clientes con SERVER_EXIT
                # Llama a handle_disconnect para cada cliente
                # Cierra el server_socket principal
                # Termina el proceso del servidor con os._exit(0)
            else:
                # Comando no reconocido

        except EOFError: # Si se presiona Ctrl+D
            # Lógica de cierre similar a 'exit'
        except Exception as e: # Otros errores
```

*   Esta función se ejecuta en **su propio hilo**, independiente de los clientes y del hilo principal.
*   Entra en un bucle infinito que:
    *   Espera entrada del usuario en la terminal del servidor (`input()`). Esta llamada también es **bloqueante**.
    *   Procesa la entrada para determinar el comando y sus argumentos.
    *   Ejecuta la acción correspondiente:
        *   Modifica el estado global (`events`, `global_threads_config`).
        *   Interactúa con los clientes (en `trigger`, `set_threads`, `exit`) llamando a `send_to_client`.
        *   Muestra información (`list`).
    *   El comando `exit` es crucial: notifica a todos los clientes, los desconecta limpiamente (llamando a `handle_disconnect`) y cierra el socket principal antes de terminar el proceso. `os._exit(0)` es una forma directa de terminar; en aplicaciones más complejas, se preferirían mecanismos más suaves para que los hilos terminen por sí mismos.

### 6. Bucle Principal de Aceptación y Arranque de Hilos

```python
# Iniciar hilo para comandos de servidor
command_thread = threading.Thread(target=server_commands, daemon=True)
command_thread.start()

# Bucle principal para aceptar clientes
try:
    while True:
        # Espera bloqueante hasta que un nuevo cliente se conecte
        client_sock, client_addr = server_socket.accept()
        # Crea un NUEVO hilo para manejar a este cliente específico
        client_handler = threading.Thread(target=handle_client, args=(client_sock, client_addr), daemon=True)
        client_handler.start() # Inicia la ejecución del hilo (llama a handle_client)
except KeyboardInterrupt: # Si se presiona Ctrl+C
    # Lógica de cierre similar a 'exit'
except Exception as e:
finally:
    # Asegura que el socket principal se cierre si salimos del bucle
    if not server_socket._closed:
         server_socket.close()
```

*   Primero, crea e inicia el hilo para los comandos del servidor (`server_commands`). `daemon=True` significa que este hilo no impedirá que el programa principal termine si es el único hilo que queda (además del principal).
*   Luego, entra en el bucle principal del servidor:
    *   `server_socket.accept()` es **bloqueante**: el hilo principal espera aquí hasta que llegue una nueva conexión.
    *   Cuando llega una conexión, `accept()` devuelve un nuevo objeto `socket` para *esa conexión específica* (`client_sock`) y la dirección del cliente (`client_addr`).
    *   Se crea un **nuevo hilo** (`client_handler`) que ejecutará la función `handle_client`, pasándole el socket y la dirección del nuevo cliente.
    *   `client_handler.start()` inicia el nuevo hilo. El bucle principal *inmediatamente* vuelve a llamar a `accept()`, listo para la siguiente conexión, mientras el hilo recién creado empieza a gestionar al cliente conectado.
    *   Usar `daemon=True` para los hilos de cliente también es común en servidores simples.
*   El bloque `try...except KeyboardInterrupt...finally` maneja la interrupción por Ctrl+C y otros errores, intentando cerrar el servidor de forma ordenada.

## Protocolo de Comunicación

La comunicación entre cliente y servidor se basa en mensajes **JSON**. Cada mensaje es un diccionario Python con al menos una clave `"type"` que indica el tipo de mensaje/comando. Opcionalmente, puede tener una clave `"payload"` con los datos asociados.

**Ejemplos:**

*   Cliente a Servidor: `{"type": "SUB", "payload": "data_ready"}`
*   Servidor a Cliente: `{"type": "TRIGGER", "payload": "data_ready"}`
*   Servidor a Cliente: `{"type": "CONFIG", "payload": {"threads": 4}}`

## Conclusión

El servidor utiliza un modelo basado en hilos para manejar concurrencia: un hilo principal escucha conexiones, un hilo maneja los comandos de la terminal, y se crea un hilo adicional por cada cliente conectado para gestionar su comunicación individual. El estado compartido (eventos, clientes, configuración) se mantiene en variables globales, y la comunicación se realiza mediante mensajes JSON sobre sockets TCP.
```

---
