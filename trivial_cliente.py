import socket
import sys

def iniciar_cliente():
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cliente.connect(("127.0.0.1", 12345))

    try:
        while True:
            mensaje = cliente.recv(1024).decode("utf-8")
            if not mensaje:
                print("El servidor cerró la conexión.")
                break

            # Detección de mensajes de jugadores conectados
            if mensaje.startswith("Jugadores conectados"):
                sys.stdout.write("\r" + " " * 80 + "\r")  # Limpiar la línea actual
                sys.stdout.flush()
                sys.stdout.write(mensaje.strip())
                sys.stdout.flush()
            else:
                print(mensaje, end="")  # Mostrar mensaje del servidor normalmente

            # Si el servidor espera entrada del usuario
            if mensaje.strip().endswith(":") or "Seleccione" in mensaje:
                entrada = input("")  # Leer entrada del usuario
                cliente.sendall(entrada.encode("utf-8"))

    except KeyboardInterrupt:
        print("\nCerrando conexión...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cliente.close()

if __name__ == "__main__":
    iniciar_cliente()
