# Cliente de chat con sockets TCP.
# Pide la dirección IP y el puerto del servidor, envía los mensajes que escribe
# el usuario y muestra en pantalla los que llegan de los demás clientes.
import os
import socket
import sys
import threading


def main():
    ip = input("Dirección IP del servidor: ").strip()
    puerto = input("Puerto: ").strip()
    usuario = input("Nombre de usuario: ").strip()

    try:
        conn = socket.create_connection((ip, int(puerto)))
    except (OSError, ValueError) as err:
        print("No se pudo conectar con el servidor:", err)
        return

    # Los archivos con newline="\n" evitan que Windows traduzca los saltos de
    # línea, que son el único separador que entiende el servidor.
    entrada = conn.makefile("r", encoding="utf-8", newline="\n")
    salida = conn.makefile("w", encoding="utf-8", newline="\n")

    # El nombre de usuario es la primera línea que espera el servidor.
    salida.write(usuario + "\n")
    salida.flush()
    print("Conectado al chat. Escribe exit para salir.")

    # La recepción corre en su propio hilo para poder escribir y recibir
    # mensajes al mismo tiempo.
    threading.Thread(target=recibir, args=(entrada,), daemon=True).start()

    while True:
        try:
            texto = input().strip()
        except EOFError:
            break
        salida.write(texto + "\n")
        salida.flush()
        if texto == "exit":
            print("Has salido del chat")
            break
        # El mensaje enviado se muestra con la misma estructura que los recibidos.
        print('[%s]: "%s"' % ("Tú", texto))

    conn.close()


def recibir(entrada):
    # Muestra en pantalla todo lo que envía el servidor.
    try:
        for linea in entrada:
            print(linea.rstrip("\n"))
    except OSError:
        pass
    print("Se perdió la conexión con el servidor")
    # os._exit termina el proceso completo desde el hilo, igual que os.Exit en Go.
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
