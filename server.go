// Servidor de chat con sockets TCP.
// Acepta varios clientes al mismo tiempo, cada uno atendido por una goroutine,
// y retransmite los mensajes recibidos a todos los clientes menos al que lo envió.
package main

import (
	"bufio"
	"fmt"
	"net"
	"os"
	"os/signal"
	"strings"
	"sync"
)

// clientes guarda la conexión de cada usuario en línea y su nombre.
// El mutex lo protege porque varias goroutines lo leen y lo modifican a la vez.
var (
	mu       sync.Mutex
	clientes = map[net.Conn]string{}
)

func main() {
	listener, err := net.Listen("tcp", ":8067")
	if err != nil {
		fmt.Println("No se pudo iniciar el servidor:", err)
		return
	}
	fmt.Println("Servidor escuchando en el puerto 8067")

	go cierreSeguro(listener)

	for {
		conn, err := listener.Accept()
		if err != nil {
			return
		}
		go atenderCliente(conn)
	}
}

// atenderCliente lee el nombre del usuario y después sus mensajes hasta que
// escribe exit o cierra el programa.
func atenderCliente(conn net.Conn) {
	defer conn.Close()

	lector := bufio.NewScanner(conn)
	if !lector.Scan() {
		return
	}
	usuario := strings.TrimSpace(lector.Text()) // quita espacios en blanco

	mu.Lock()
	clientes[conn] = usuario // enlaza la conexión con el nombre de usuario
	mu.Unlock()

	fmt.Printf("Se ha conectado el usuario %s desde %s\n", usuario, conn.RemoteAddr())
	retransmitir(conn, fmt.Sprintf("El usuario %s se ha unido al chat", usuario))

	// ciclo infinito que acaba hasta que el usuario escriba: "exit"
	for lector.Scan() {
		texto := strings.TrimSpace(lector.Text())
		if texto == "exit" {
			break
		}
		mensaje := fmt.Sprintf("[%s]: \"%s\"", usuario, texto)
		fmt.Println(mensaje)
		retransmitir(conn, mensaje)
	}

	mu.Lock()
	delete(clientes, conn)
	mu.Unlock()

	fmt.Printf("Se ha desconectado el usuario %s\n", usuario)
	retransmitir(conn, fmt.Sprintf("El usuario %s ha abandonado el chat", usuario))
}

// retransmitir envía el mensaje a todos los clientes conectados menos al emisor.
func retransmitir(emisor net.Conn, mensaje string) {
	mu.Lock()
	defer mu.Unlock()
	for conn := range clientes {
		if conn != emisor {
			fmt.Fprintln(conn, mensaje)
		}
	}
}

// cierreSeguro espera Ctrl+C para avisar a los usuarios antes de cerrar sus
// conexiones, de modo que ninguno se desconecte de forma inesperada.
func cierreSeguro(listener net.Listener) {
	senal := make(chan os.Signal, 1)
	signal.Notify(senal, os.Interrupt)
	<-senal

	fmt.Println("\nCerrando el servidor y desconectando a los usuarios")
	mu.Lock()
	for conn, usuario := range clientes {
		fmt.Fprintln(conn, "El servidor se ha cerrado, serás desconectado del chat")
		conn.Close()
		fmt.Printf("Se ha desconectado el usuario %s\n", usuario)
	}
	mu.Unlock()

	listener.Close()
	os.Exit(0)
}
