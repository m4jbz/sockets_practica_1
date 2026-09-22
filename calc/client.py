import socket
import tkinter as tk
from tkinter import ttk

HOST, PORT   = '127.0.0.1', 8000
TIMEOUT      = 5.0
OPERATORS    = '+-*/'

conn         = None
recv_buffer  = b''


def set_status(message, ok=False):
    status.configure(text=message, foreground='#1a7f37' if ok else '#b00020')


def update_indicator():
    connected = conn is not None
    canvas.itemconfigure(led, fill='#1a7f37' if connected else '#b00020')
    indicator.configure(text='Conectado' if connected else 'Sin conexión')
    connect_button.configure(text='Desconectar' if connected else 'Conectar')


def connect():
    global conn, recv_buffer
    if conn is not None:
        return
    host = host_entry.get().strip() or HOST
    try:
        port = int(port_entry.get().strip())
    except ValueError:
        set_status('El puerto debe ser un número entero.')
        return
    try:
        conn = socket.create_connection((host, port), timeout=TIMEOUT)
    except OSError as e:
        conn = None
        set_status(f'No fue posible conectar con el servidor {host}:{port} ({e}).')
    else:
        recv_buffer = b''
        set_status(f'Conexión establecida con {host}:{port}.', ok=True)
    update_indicator()


def disconnect(message='Desconectado del servidor.'):
    global conn, recv_buffer
    if conn is not None:
        try:
            conn.sendall(b'exit\n')
        except OSError:
            pass
        conn.close()
    conn = None
    recv_buffer = b''
    set_status(message)
    update_indicator()


def toggle_connection():
    if conn is None:
        connect()
    else:
        disconnect()


def receive_line():
    """Lee hasta el salto de línea que delimita cada respuesta del servidor."""
    global recv_buffer
    while b'\n' not in recv_buffer:
        data = conn.recv(1024)
        if not data:
            return None
        recv_buffer += data
    line, recv_buffer = recv_buffer.split(b'\n', 1)
    return line.decode('utf-8', 'replace').strip()


def show_result(text, error=False):
    result.configure(state='normal')
    result.delete('1.0', 'end')
    result.insert('1.0', text)
    result.configure(state='disabled', foreground='#b00020' if error else '#101010')


def add_history(expr, response):
    history.insert('end', f'{expr}  =>  {response}')
    history.see('end')


def send_expression(event=None):
    expr = display.get().strip()
    if not expr:
        set_status('Escriba una expresión antes de evaluarla.')
        show_result('Error: la expresión está vacía.', error=True)
        return
    if not any(ch in OPERATORS for ch in expr):
        set_status('La expresión no contiene ningún operador: no se envió al servidor.')
        show_result('Error: la expresión está incompleta: no contiene ningún operador.', error=True)
        return
    if conn is None:
        set_status('No hay conexión con el servidor. Pulse Conectar.')
        show_result('Error: no hay conexión con el servidor.', error=True)
        return
    try:
        conn.sendall((expr + '\n').encode('utf-8'))
        response = receive_line()
    except socket.timeout:
        set_status('Tiempo de espera agotado: el servidor no respondió.')
        show_result('Error: tiempo de espera agotado.', error=True)
        return
    except OSError as e:
        show_result('Error: se perdió la conexión con el servidor.', error=True)
        add_history(expr, 'sin respuesta')
        disconnect(f'Se perdió la conexión con el servidor ({e}).')
        return

    if response is None:
        show_result('Error: el servidor cerró la conexión.', error=True)
        add_history(expr, 'sin respuesta')
        disconnect('El servidor cerró la conexión.')
        return

    error = response.startswith('Error')
    show_result(response, error=error)
    set_status('El servidor reportó un error.' if error else 'Respuesta recibida.', ok=not error)
    add_history(expr, response)


def append(text):
    display.insert('end', text)
    display.icursor('end')
    display.focus_set()


def backspace():
    current = display.get()
    display.delete(0, 'end')
    display.insert(0, current[:-1])
    display.focus_set()


def clear_all():
    display.delete(0, 'end')
    show_result('')
    set_status('Expresión y resultado limpiados.', ok=True)
    display.focus_set()


def clear_history():
    history.delete(0, 'end')


def on_close():
    disconnect()
    root.destroy()


# Ventana principal
root = tk.Tk()
root.title('Calculadora cliente')
root.geometry('820x620')
root.minsize(720, 560)
root.columnconfigure(0, weight=1)
root.rowconfigure(3, weight=1)

# Barra de conexión
top = ttk.Frame(root, padding=8)
top.grid(row=0, column=0, sticky='ew')

ttk.Label(top, text='Servidor:').pack(side='left')
host_entry = ttk.Entry(top, width=14)
host_entry.insert(0, HOST)
host_entry.pack(side='left', padx=4)

ttk.Label(top, text='Puerto:').pack(side='left')
port_entry = ttk.Entry(top, width=7)
port_entry.insert(0, str(PORT))
port_entry.pack(side='left', padx=4)

connect_button = ttk.Button(top, text='Conectar', command=toggle_connection)
connect_button.pack(side='left', padx=8)

indicator = ttk.Label(top, text='Sin conexión')
indicator.pack(side='right')
canvas = tk.Canvas(top, width=16, height=16, highlightthickness=0)
led = canvas.create_oval(2, 2, 14, 14, fill='#b00020', outline='')
canvas.pack(side='right', padx=6)

# Campo de la expresión
display = tk.Entry(root, font=('Arial', 24))
display.grid(row=1, column=0, sticky='ew', padx=8)
display.bind('<Return>', send_expression)
display.focus_set()

# Área de resultado
result = tk.Text(root, font=('Arial', 20), height=2, background='#e9e9e9',
                 state='disabled', wrap='word')
result.grid(row=2, column=0, sticky='ew', padx=8, pady=6)

# Cuerpo: teclado e historial
body = ttk.Frame(root, padding=8)
body.grid(row=3, column=0, sticky='nsew')
body.columnconfigure(0, weight=3)
body.columnconfigure(1, weight=2)
body.rowconfigure(0, weight=1)

keypad = ttk.Frame(body)
keypad.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
for c in range(4):
    keypad.columnconfigure(c, weight=1)
for r in range(5):
    keypad.rowconfigure(r, weight=1)

keys = [
    [('(', lambda: append('(')), (')', lambda: append(')')),
     ('Borrar', backspace), ('Limpiar', clear_all)],
    [('7', lambda: append('7')), ('8', lambda: append('8')),
     ('9', lambda: append('9')), ('/', lambda: append(' / '))],
    [('4', lambda: append('4')), ('5', lambda: append('5')),
     ('6', lambda: append('6')), ('*', lambda: append(' * '))],
    [('1', lambda: append('1')), ('2', lambda: append('2')),
     ('3', lambda: append('3')), ('-', lambda: append(' - '))],
    [('0', lambda: append('0')), ('.', lambda: append('.')),
     ('+', lambda: append(' + ')), ('=', send_expression)],
]
for r, row in enumerate(keys):
    for c, (label, action) in enumerate(row):
        ttk.Button(keypad, text=label, command=action).grid(
            row=r, column=c, sticky='nsew', padx=2, pady=2)

side = ttk.Frame(body)
side.grid(row=0, column=1, sticky='nsew')
side.columnconfigure(0, weight=1)
side.rowconfigure(1, weight=1)

ttk.Label(side, text='Historial de operaciones').grid(row=0, column=0, sticky='w')
history = tk.Listbox(side, font=('Arial', 11))
history.grid(row=1, column=0, sticky='nsew')
scroll = ttk.Scrollbar(side, orient='vertical', command=history.yview)
scroll.grid(row=1, column=1, sticky='ns')
history.configure(yscrollcommand=scroll.set)
ttk.Button(side, text='Limpiar historial', command=clear_history).grid(
    row=2, column=0, sticky='ew', pady=4)

# Barra de estado
status = ttk.Label(root, text='Sin conexión con el servidor.', foreground='#b00020',
                   padding=6, anchor='w')
status.grid(row=4, column=0, sticky='ew')

root.protocol('WM_DELETE_WINDOW', on_close)
connect()
root.mainloop()
