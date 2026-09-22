from tkinter import *
import tkinter as tk
import socket

def get_input(event):
    expr = input.get().strip()
    if expr == "exit":
        root.destroy()
    conn.send(expr.encode())
    data = conn.recv(1024)
    output_text = f"""{data.decode("utf-8").strip()}"""
    output.delete("1.0", "end")
    output.insert(tk.END, output_text)

# Ventana principal
root = Tk()
root.geometry("800x600")
root.title("Calculadora cliente")
root.columnconfigure(0, weight=1)

# Input
input = tk.Entry(root, font=("Arial", 24))
input.bind("<Return>", get_input)
input.focus_set()
input.grid(row=0, column=0, sticky="ew")

# Output
output = Text(root, font=("Arial", 24), background="lightgray")
output.grid(row=1, column=0, sticky="ew")

# Net vars
ip, port    = '127.0.0.1', 8080
addr        = (ip, port)
output_text = ""

with socket.create_connection(addr) as conn:
    root.mainloop()
