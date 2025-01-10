import csv
from email_validator import validate_email, EmailNotValidError

# Archivos CSV
ARCHIVO_USUARIOS = 'usuarios.csv'

# Guardar usuarios en el archivo CSV
def guardar_usuario(email, clave):
    with open(ARCHIVO_USUARIOS, mode='a', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([email, clave])

# Cargar usuarios desde el archivo CSV
def cargar_usuarios():
    usuarios = {}
    try:
        with open(ARCHIVO_USUARIOS, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                usuarios[row[0]] = row[1]
    except FileNotFoundError:
        pass  # Si el archivo no existe, asumimos que no hay usuarios
    return usuarios

# Registro del cliente
def registro_cliente(cliente_socket, usuarios_registrados):
    exito = False
    cliente_socket.sendall(b"Ingrese su email: ")
    email = cliente_socket.recv(1024).decode("utf-8").strip()
    try:
        validate_email(email)
        if email in usuarios_registrados:
            cliente_socket.sendall(b"Email ya registrado.\n")
        else:
            cliente_socket.sendall(b"Ingrese su clave: ")
            clave = cliente_socket.recv(1024).decode("utf-8").strip()
            usuarios_registrados[email] = clave
            guardar_usuario(email, clave)
            cliente_socket.sendall(b"Registro exitoso.\n")
            exito = True
    except EmailNotValidError:
        cliente_socket.sendall(b"Email no valido.\n")
    return exito

# Inicio de sesión para el cliente
def inicio_sesion_cliente(cliente_socket, usuarios_registrados):
    exito = False
    cliente_socket.sendall(b"Ingrese su email: ")
    email = cliente_socket.recv(1024).decode("utf-8").strip()
    cliente_socket.sendall(b"Ingrese su clave: ")
    clave = cliente_socket.recv(1024).decode("utf-8").strip()

    if usuarios_registrados.get(email) == clave:
        cliente_socket.sendall(b"Inicio de sesion exitoso.\n")
        exito = True
    else:
        cliente_socket.sendall(b"Credenciales incorrectas.\n")

    return exito
