package main

import (
	"fmt"
	"log"
	"bufio"
	"net"
	"strings"
	"os"
	"os/signal"
	"sync"

	"github.com/expr-lang/expr"
)

var (
	mu       sync.Mutex
	clients = map[net.Conn]string{}
	port    = ":8080"
)

func main() {
	listener, err := net.Listen("tcp", port)
	if (err != nil) {
		log.Fatal("Error al crear el servidor: ", err)
	}
	fmt.Printf("Listening on %v\n", port)

	go safeExit(listener)

	for {
		conn, err := listener.Accept()
		if (err != nil) {
			log.Println("Error al conectar: ", err)
		}
		go handleConnection(conn)
	}
}

func handleConnection(conn net.Conn) {
	defer conn.Close()

	scanner := bufio.NewScanner(conn)

	for scanner.Scan() {
		expression := strings.TrimSpace(scanner.Text())
		if expression == "exit" {
			break
		}

		result, err := expr.Eval(expression, nil)
		if (err != nil) {
			fmt.Fprintln(conn, err)
			log.Println("Error al evaluar la expresion: ", err)
			continue
		}

		fmt.Fprintln(conn, result)
	}

	mu.Lock()
	delete(clients, conn)
	mu.Unlock()
}

func safeExit(listener net.Listener) {
	sign := make(chan os.Signal, 1)
	signal.Notify(sign, os.Interrupt)
	<-sign

	mu.Lock()
	for conn, _ := range clients {
		conn.Close()
	}
	mu.Unlock()

	listener.Close()
	os.Exit(0)
}
