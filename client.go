// Cliente de chat con sockets TCP.
// Pide la dirección IP y el puerto del servidor, envía los mensajes que escribe
// el usuario y muestra en pantalla los que llegan de los demás clientes.
package main

import (
	"bufio"
	"fmt"
	"net"
	"os"
	"strings"
)

func main() {
	teclado := bufio.NewScanner(os.Stdin)

	fmt.Print("Dirección IP del servidor: ")
	teclado.Scan()
	ip := strings.TrimSpace(teclado.Text())

	fmt.Print("Puerto: ")
	teclado.Scan()
	puerto := strings.TrimSpace(teclado.Text())

	fmt.Print("Nombre de usuario: ")
	teclado.Scan()
	usuario := strings.TrimSpace(teclado.Text())

	conn, err := net.Dial("tcp", net.JoinHostPort(ip, puerto))
	if err != nil {
		fmt.Println("No se pudo conectar con el servidor:", err)
		return
	}
	defer conn.Close()

	// El nombre de usuario es la primera línea que espera el servidor.
	fmt.Fprintln(conn, usuario)
	fmt.Println("Conectado al chat. Escribe exit para salir.")

	// La recepción corre en su propia goroutine para poder escribir y recibir
	// mensajes al mismo tiempo.
	go recibir(conn)

	for teclado.Scan() {
		texto := strings.TrimSpace(teclado.Text())
		fmt.Fprintln(conn, texto)
		if texto == "exit" {
			fmt.Println("Has salido del chat")
			return
		}
		// El mensaje enviado se muestra con la misma estructura que los recibidos.
		fmt.Printf("[%s]: \"%s\"\n", "Tú", texto)
	}
}

// recibir muestra en pantalla todo lo que envía el servidor.
func recibir(conn net.Conn) {
	lector := bufio.NewScanner(conn)
	for lector.Scan() {
		fmt.Println(lector.Text())
	}
	fmt.Println("Se perdió la conexión con el servidor")
	os.Exit(0)
}
