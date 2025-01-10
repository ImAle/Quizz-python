import socket
import threading
import time
import sys
from colorama import Fore, Style
import usuarios
import preguntas

# Variables globales
MAX_JUGADORES = 2
NUM_PREGUNTAS = 5
DESCANSO_POR_PREGUNTA = 2

usuarios_registrados = usuarios.cargar_usuarios()
preguntas_quizz = preguntas.cargar_preguntas()
clientes_conectados = []
preguntas_partida = preguntas.seleccionar_preguntas(preguntas_quizz,NUM_PREGUNTAS)

# Evento global para sincronizar el inicio del juego
evento_inicio = threading.Event()

# Evento global para sincronizar el envío de la pregunta
evento_pregunta = threading.Event()

# Evento global para el envío de ranking y mensajes personalizados
evento_ranking = threading.Event()

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


# Hace el ranking y lo envía
def enviar_ranking(clientes_conectados):
    # Ordenamos los jugadores de mayor a menor según sus puntos
    clientes_conectados.sort(key=lambda c: c['puntos'], reverse=True)

    # Formatear el ranking con el puntaje entre paréntesis
    puntajes = "\n".join([f"{i+1}. {c['nick']} -> ({c['puntos']} puntos)" for i, c in enumerate(clientes_conectados)])

    # Mostrar el ranking completo en el servidor
    print(f"Ranking final:\n{puntajes}")

    # Enviar el ranking a todos los clientes
    for cliente in clientes_conectados:
        cliente["socket"].sendall(f"\nRanking final:\n{puntajes}\n".encode("utf-8"))

    # Enviar mensajes personalizados a los jugadores
    for cliente in clientes_conectados:
        if cliente["puntos"] == clientes_conectados[0]["puntos"]:
            mensaje = "Enhorabuena! Has ganado el quizz"
        else:
            puesto = clientes_conectados.index(cliente) + 1
            mensaje = f"Enhorabuena! Has quedado en el puesto {puesto}"

        # Mensaje personalizado
        cliente["socket"].sendall(f"{mensaje}\n".encode("utf-8"))

# Manejo de clientes
def manejar_cliente(cliente_socket, direccion):
    global clientes_conectados

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

        # Imprimir solo una vez
        if cliente_socket == clientes_conectados[0]["socket"]:
            sys.stdout.write("\r" + " " * 30 + "\r")  # Limpia la línea
            sys.stdout.flush()
            print(f"Los jugadores van por la ronda {ronda_preguntas}/{NUM_PREGUNTAS}")

        # Guardar el estado inicial de los puntos
        puntos_iniciales = {c["nick"]: c["puntos"] for c in clientes_conectados}

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

                if respuesta.isdigit() and 1 <= int(respuesta) <= len(pregunta['opciones']):
                    if pregunta['opciones'][int(respuesta) - 1] == pregunta['respuesta']:
                        cliente_socket.sendall((Fore.GREEN + "Correcto!\n" + Style.RESET_ALL).encode('utf-8'))
                        cliente["puntos"] += 1
                    else:
                        cliente_socket.sendall((Fore.RED + "Incorrecto!\n" + Style.RESET_ALL).encode('utf-8'))
                else:
                    cliente_socket.sendall((Fore.RED + "Opcion no valida.\n" + Style.RESET_ALL).encode('utf-8'))
                    
                break

        cliente_socket.sendall(b"Esperando la siguiente pregunta...\n")

        # Verificar si todos los jugadores han respondido
        while True:
            if all(c["puntos"] != puntos_iniciales[c["nick"]] for c in clientes_conectados): break

        ronda_preguntas += 1

        # Verificar si el cliente se ha desconectado
        if cliente_socket.fileno() == -1:
            clientes_conectados = [c for c in clientes_conectados if c["socket"].fileno() != -1]
            break
        
        time.sleep(DESCANSO_POR_PREGUNTA)

    # Finalizar la partida
    cliente_socket.sendall(b"Partida finalizada.\n")

    # Solo el primer cliente conectado ejecuta el ranking
    if cliente_socket == clientes_conectados[0]["socket"]:
        enviar_ranking(clientes_conectados)
        evento_ranking.set()  # Activa el evento para informar a otros clientes

    # Espera hasta que el evento de ranking se complete
    evento_ranking.wait()

    cliente_socket.close()

if __name__ == "__main__":
    iniciar_servidor()

# El servidor debe guardar un historico de partidas