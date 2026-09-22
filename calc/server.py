import math
import re
import socket
import signal
import threading

IP, PORT     = '', 8000
addr         = (IP, PORT)
clients      = {}
clients_lock = threading.Lock()
log_lock     = threading.Lock()

NUMBER_RE = re.compile(r'\d+(?:\.\d+)?|\.\d+')


class ExpressionError(Exception):
    pass


class DivisionByZero(ExpressionError):
    def __init__(self):
        super().__init__('no es posible realizar una división entre cero.')


def tokenize(expr):
    tokens = []
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch.isspace():
            i += 1
            continue
        match = NUMBER_RE.match(expr, i)
        if match:
            tokens.append(('num', float(match.group())))
            i = match.end()
            continue
        if ch in '+-*/()':
            tokens.append((ch, ch))
            i += 1
            continue
        raise ExpressionError(f'la expresión contiene un carácter no permitido: "{ch}".')
    return tokens


class Parser:
    """Descenso recursivo: la precedencia queda dada por la jerarquía de reglas."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos][0]
        return None

    def advance(self):
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def parse(self):
        value = self.expression()
        remaining = self.peek()
        if remaining is not None:
            if remaining == ')':
                raise ExpressionError('paréntesis no balanceados: sobra un ")".')
            raise ExpressionError(f'operador colocado incorrectamente cerca de "{remaining}".')
        return value

    def expression(self):
        value = self.term()
        while self.peek() in ('+', '-'):
            op = self.advance()[0]
            right = self.term()
            value = value + right if op == '+' else value - right
        return value

    def term(self):
        value = self.factor()
        while self.peek() in ('*', '/'):
            op = self.advance()[0]
            right = self.factor()
            if op == '*':
                value = value * right
            else:
                if right == 0:
                    raise DivisionByZero()
                value = value / right
        return value

    def factor(self):
        sign = self.peek()
        if sign in ('+', '-'):
            self.advance()
            value = self.factor()
            return value if sign == '+' else -value
        return self.primary()

    def primary(self):
        kind = self.peek()
        if kind is None:
            raise ExpressionError('la expresión está incompleta: falta un número.')
        kind, value = self.advance()
        if kind == 'num':
            return value
        if kind == '(':
            inner = self.expression()
            if self.peek() != ')':
                raise ExpressionError('paréntesis no balanceados: falta un ")".')
            self.advance()
            return inner
        if kind == ')':
            raise ExpressionError('paréntesis no balanceados: hay un ")" sin apertura.')
        raise ExpressionError(f'operador colocado incorrectamente: "{value}".')


def format_number(value):
    if not math.isfinite(value):
        raise ExpressionError('el resultado excede el rango numérico representable.')
    if float(value).is_integer():
        return str(int(value))
    return f'{value:.10g}'


def evaluate(expr):
    if not expr.strip():
        raise ExpressionError('la expresión está vacía.')
    return format_number(Parser(tokenize(expr)).parse())


def log(message):
    with log_lock:
        print(message, flush=True)


def process(expr):
    try:
        return 'Resultado: ' + evaluate(expr)
    except ExpressionError as e:
        return 'Error: ' + str(e)
    except Exception as e:
        return f'Error: no fue posible evaluar la expresión ({e}).'


def handle_client(conn, peer):
    log(f'[+] Cliente conectado: {peer[0]}:{peer[1]}')
    buffer = b''
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                expr = line.decode('utf-8', 'replace').strip()
                if expr == 'exit':
                    return
                log(f'[>] {peer[0]}:{peer[1]} solicita: {expr!r}')
                response = process(expr)
                log(f'[<] {peer[0]}:{peer[1]} recibe: {response}')
                conn.sendall((response + '\n').encode('utf-8'))
    except OSError:
        pass
    finally:
        with clients_lock:
            clients.pop(conn, None)
        conn.close()
        log(f'[-] Cliente desconectado: {peer[0]}:{peer[1]}')


def shutdown(*_):
    log('\nCerrando el servidor.')
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

    log('Servidor detenido.')


def accept_loop():
    while True:
        try:
            conn, peer = server.accept()
        except OSError:
            break
        t = threading.Thread(target=handle_client, args=(conn, peer), daemon=True)
        with clients_lock:
            clients[conn] = t
        t.start()


server = socket.create_server(addr)
log(f'Servidor de calculadora escuchando en el puerto {PORT}. Ctrl+C para detenerlo.')

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

accept_thread = threading.Thread(target=accept_loop, daemon=True)
accept_thread.start()

signal.pause()
