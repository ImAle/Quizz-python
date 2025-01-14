import socket
import threading
import time
import sys
import csv
from datetime import datetime
from colorama import Fore, Style
import usuarios
import preguntas

# Variables globales
MAX_JUGADORES = 2
NUM_PREGUNTAS = 5
HISTORIAL_PARTIDAS = "historial_partidas.csv"

usuarios_registrados = usuarios.cargar_usuarios()
preguntas_quizz = preguntas.cargar_preguntas()
clientes_conectados = []
preguntas_partida = preguntas.seleccionar_preguntas(preguntas_quizz, NUM_PREGUNTAS)

# Contador global para conocer cuantos jugadores han respondido a la preugnta 
contador_respuestas = 0
lock_respuestas = threading.Lock()

# Evento global para sincronizar el inicio del juego
evento_inicio = threading.Event()

# Evento global para sincronizar el envío de la pregunta
evento_pregunta = threading.Event()

# Evento global para el envío de ranking y mensajes personalizados
evento_ranking = threading.Event()

# Evento para sincronizar las respuestas
evento_todos_respondieron = threading.Event()

# Inicio del servidor
def iniciar_servidor():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind(("0.0.0.0", 12345))
    servidor.listen(MAX_JUGADORES)
    print("Servidor iniciado. Esperando conexiones...")

    while True:
        cliente_socket, direccion = servidor.accept()
        hilo = threading.Thread(target=manejar_cliente, args=(cliente_socket, direccion))
        hilo.start()

# Función para mostrar el estado actual de conexiones
def mostrar_estado_conexiones():
    sys.stdout.write("\033[H\033[J")  # Limpiar la pantalla antes de imprimir el estado
    sys.stdout.flush()

    print(f"Servidor iniciado. Esperando conexiones... ({len(clientes_conectados)}/{MAX_JUGADORES})\n")

    for cliente in clientes_conectados:
        if 'nick' in cliente:
            print(f"Cliente conectado desde {cliente['direccion']} ({cliente['nick']})")
        else:
            print(f"Cliente conectado desde {cliente['direccion']}, esperando nickname...")
            

# Guardar historial de partidas
def guardar_historial():
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    jugadores = [cliente["nick"] for cliente in clientes_conectados]
    puntos = [cliente["puntos"] for cliente in clientes_conectados]
    
    with open(HISTORIAL_PARTIDAS, mode='a', newline='') as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow([fecha_actual, jugadores, puntos])

# Mostrar historial de partidas
def mostrar_historial():
    try:
        with open(HISTORIAL_PARTIDAS, mode='r') as archivo:
            lector = csv.reader(archivo)
            next(lector) # Salta la primera linea
            historial = list(lector)
            historial.sort(reverse=True)
            print("\nHistorial de Partidas:")
            for registro in historial:
                print(f"Fecha: {registro[0]} | Jugadores: {registro[1]} | Puntos: {registro[2]}")
    except FileNotFoundError:
        print("No hay historial de partidas registrado.")


# Hace el ranking y lo envía
def enviar_ranking(clientes_conectados):
    # Ordenamos los jugadores de mayor a menor según sus puntos
    clientes_conectados.sort(key=lambda c: c['puntos'], reverse=True)

    # Formatear el ranking con el puntaje entre paréntesis
    puntajes = "\n".join([f"{i+1}. {c['nick']} -> ({c['puntos']} puntos)" for i, c in enumerate(clientes_conectados)])
    print(f"Ranking final:\n{puntajes}")

    # Enviar el ranking a todos los clientes
    for cliente in clientes_conectados:
        cliente["socket"].sendall(f"\nRanking final:\n{puntajes}\n".encode("utf-8"))

    # Calcular posiciones teniendo en cuenta empates
    posiciones = {}
    puesto_actual = 1

    for i, cliente in enumerate(clientes_conectados):
        puntos = cliente["puntos"]
        if puntos not in posiciones:
            posiciones[puntos] = puesto_actual
        puesto_actual += 1

    # Enviar mensajes personalizados
    for cliente in clientes_conectados:
        puesto = posiciones[cliente["puntos"]]
        jugadores_mismo_puesto = [c for c in clientes_conectados if c["puntos"] == cliente["puntos"]]

        if len(jugadores_mismo_puesto) > 1:
            mensaje = f"Empate! Compartes el puesto {puesto}"
        elif puesto == 1:
            mensaje = "¡Enhorabuena! Has ganado el quizz"
        else:
            mensaje = f"¡Enhorabuena! Has quedado en el puesto {puesto}"

        cliente["socket"].sendall(f"{mensaje}\n".encode("utf-8"))


# Manejo de clientes
def manejar_cliente(cliente_socket, direccion):
    global clientes_conectados, contador_respuestas # Hacer saber al método que dichas variables son globales

    if len(clientes_conectados) >= MAX_JUGADORES:
        cliente_socket.sendall((Fore.RED + "Servidor lleno. No se permiten mas conexiones en esta partida.\n" + Style.RESET_ALL).encode('utf-8'))
        cliente_socket.close()
        return

    clientes_conectados.append({"socket": cliente_socket, "direccion": direccion, "puntos": 0})

    # Imprimir conexión inicial
    mostrar_estado_conexiones()
    cliente_socket.sendall((Fore.GREEN + "Bienvenido al servidor de Trivial.\n" + Style.RESET_ALL).encode('utf-8'))

    # Inicio de sesión y registro
    while True:
        cliente_socket.sendall(b"Seleccione: 1. Registrarse 2. Iniciar sesion\n")
        opcion = cliente_socket.recv(1024).decode("utf-8").strip()

        if opcion == "1":
            usuarios.registro_cliente(cliente_socket,usuarios_registrados)

        elif opcion == "2":
            if usuarios.inicio_sesion_cliente(cliente_socket, usuarios_registrados): break


    cliente_socket.sendall(b"Ingrese su Nick para la partida: ")
    nick = cliente_socket.recv(1024).decode("utf-8").strip()

    # Buscar el cliente correspondiente y asignar el nickname usando next() con una expresión lambda
    cliente = next(cliente for cliente in clientes_conectados if cliente["socket"] == cliente_socket)
    cliente["nick"] = nick  # Asignar el nickname al cliente encontrado

    # Actualizar las líneas con nickname
    mostrar_estado_conexiones()

    cliente_socket.sendall(b"Esperando a que se conecten los demas jugadores...\n")

    # Sincronización para asegurarse de que todos los jugadores asignaron su nickname
    while len([c for c in clientes_conectados if 'nick' in c]) < MAX_JUGADORES:
        cliente_socket.sendall(
            f"Jugadores conectados ({sum([1 for c in clientes_conectados if 'nick' in c])}/{MAX_JUGADORES}): {', '.join([c['nick'] for c in clientes_conectados if 'nick' in c])}\n".encode(
                "utf-8"))
        time.sleep(1)

    cliente_socket.sendall(
        f"Jugadores conectados: {', '.join([c['nick'] for c in clientes_conectados])}\n".encode("utf-8"))
    cliente_socket.sendall((Fore.GREEN + "\nTodos los jugadores estan listos. La partida comenzara.\n" + Style.RESET_ALL).encode('utf-8'))

    ronda_preguntas = 1

    # Bucle para todas las preguntas
    for pregunta in preguntas_partida:
        
        # Imprime la ronda por la que van
        if cliente_socket == clientes_conectados[0]["socket"]:
            sys.stdout.write("\r" + " " * 30 + "\r")  # Limpia la línea
            sys.stdout.flush()
            print(f"Los jugadores van por la ronda {ronda_preguntas}/{NUM_PREGUNTAS}")

        # Hacer presente en la terminal del cliente su nickname
        cliente_socket.sendall(
            (Fore.YELLOW + f"Jugador: {nick}\n" + Style.RESET_ALL).encode('utf-8'))

        # Sincronización de la pregunta (envío a todos los clientes)
        if cliente_socket == clientes_conectados[0]["socket"]:  # Solo un hilo activará el evento
            evento_pregunta.set()  # Esto activa el evento para que todos los hilos reciban la pregunta al mismo tiempo

        evento_pregunta.wait()  # Espera hasta que el evento sea activado
        cliente_socket.sendall(f"Pregunta: {pregunta['pregunta']}\n".encode("utf-8"))

        for i, opcion in enumerate(pregunta['opciones']):
            cliente_socket.sendall(f"{i + 1}. {opcion}\n".encode("utf-8"))

        cliente_socket.sendall(b"Seleccione una opcion: ")

        respuesta = cliente_socket.recv(1024).decode("utf-8").strip()
        
        # Procesar respuesta
        for cliente in clientes_conectados:
            if cliente["socket"] == cliente_socket:
                with lock_respuestas:
                    if respuesta.isdigit() and 1 <= int(respuesta) <= len(pregunta['opciones']):
                        if pregunta['opciones'][int(respuesta) - 1] == pregunta['respuesta']:
                            cliente_socket.sendall((Fore.GREEN + "Correcto!\n" + Style.RESET_ALL).encode('utf-8'))
                            cliente["puntos"] += 1
                        else:
                            cliente_socket.sendall((Fore.RED + "Incorrecto!\n" + Style.RESET_ALL).encode('utf-8'))
                    else:
                        cliente_socket.sendall((Fore.RED + "Opcion no valida.\n" + Style.RESET_ALL).encode('utf-8'))
                    
                    # Marcamos que el jugador respondió
                    contador_respuestas += 1
                    print(f"{cliente['nick']} ha respondido. Total respuestas: {contador_respuestas}")
                    if contador_respuestas == MAX_JUGADORES:
                        print("Todos los jugadores han respondido.")
                        evento_todos_respondieron.set()
                        
                break

        cliente_socket.sendall(b"Esperando la siguiente pregunta...\n")

        # Esperamos a que todos respondan
        evento_todos_respondieron.wait()
        
        if(cliente_socket == clientes_conectados[0]["socket"]):
            with lock_respuestas:
                print("Continuando a la siguiente pregunta...")
                contador_respuestas = 0
                evento_todos_respondieron.clear()

        ronda_preguntas += 1

    # Finalizar la partida
    cliente_socket.sendall(b"Partida finalizada.\n")

    # Solo el primer cliente conectado ejecuta el ranking
    if cliente_socket == clientes_conectados[0]["socket"]:
        enviar_ranking(clientes_conectados)
        guardar_historial()
        mostrar_historial()
        evento_ranking.set()  # Activa el evento para informar a otros clientes

    # Espera hasta que el evento de ranking se complete
    evento_ranking.wait()

    cliente_socket.close()

if __name__ == "__main__":
    iniciar_servidor()
