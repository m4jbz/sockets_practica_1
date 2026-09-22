import threading
import socket
import signal

IP, PORT     = '127.0.0.1', 8000
addr         = (IP, PORT)
clients      = {}
clients_lock = threading.Lock()

server       = socket.create_server(addr)
print(f'Listening on: {addr}')

def handle_client(conn, addr):
    try:
        while True:
            data = conn.recv(1024)
            if not data: break
            expr = data.decode('utf-8').strip()
            print(expr)
            try:
                result = 'R = ' + str(eval(expr)) + '\n'
                print(result.strip())
                conn.send(result.encode())
            except Exception as e:
                conn.send(str(e).encode())
                print(f'ERROR: {e}')
    except OSError:
        pass
    finally:
        with clients_lock:
            clients.pop(conn, None)
        conn.close()

def shutdown(*_):
    server.close()

    with clients_lock:
        items = list(clients.items())

    for conn, t in items:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conn.close()

    for conn, t in items:
        t.join(timeout=2)

def accept_loop():
    while True:
        try:
            conn, addr = server.accept()
        except OSError:
            break
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        with clients_lock:
            clients[conn] = t
        t.start()

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

accept_thread = threading.Thread(target=accept_loop, daemon=True)
accept_thread.start()

signal.pause() 
