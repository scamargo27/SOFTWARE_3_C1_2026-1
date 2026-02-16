import socket
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os

LOG_FILE = "registros.txt"

print("Se esta ejecutando desde:", os.getcwd())
print("Ruta completa del log:", os.path.abspath(LOG_FILE))

HOST = "0.0.0.0"
PORT = 5050
BUFFER_SIZE = 4096

log_lock = threading.Lock()

# Patron para validar solo letras y espacios 
VALID_LINE_RE = re.compile(r"^[A-Za-z ]+$")

# Modo de respuesta al cliente
RESPONSE_MODE = "teacher"  

# Funcion para determinar si el conteo es primo
def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True

# Funcion para escribir en el archivo de texto (registro)
def write_log(text_line: str, count: int, si_no: str) -> None:
    # Guardar en formato CSV 
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f'{timestamp},"{text_line}",{count},{si_no}\n'

    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)

#Funcion para leer los datos enviados por el cliente
def receive_all(conn: socket.socket) -> str:
    # Leer todo el mensaje del cliente
    conn.settimeout(1.0)
    chunks = []

    while True:
        try:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            chunks.append(data)
        except socket.timeout:
            break

    raw = b"".join(chunks)
    return raw.decode("utf-8", errors="replace")

# Funcion de validacion de lineas: check, conteo y primo
def process_line(line: str) -> str:
    original = line
    trimmed = line.strip()

    # Validar linea vacia
    if trimmed == "":
        return "ERROR: linea vacia"
    
    # Validar formato
    if not VALID_LINE_RE.fullmatch(trimmed):
        return "ERROR: solo letras y espacios"

    # Conteo ultimo caracter
    last_char = trimmed[-1]
    count = trimmed.count(last_char)
    si_no = "SI" if is_prime(count) else "NO"

    # Guardar 
    write_log(trimmed, count, si_no)

    # Respuesta
    if RESPONSE_MODE == "teacher":
        return f"{trimmed}, {count}, {si_no}"
    else:
        prime_label = "primo" if si_no == "SI" else "no primo"
        return f"{trimmed} -> '{last_char}' aparece {count} veces -> {prime_label}"

# Funcion que maneja la conexion de un cliente
def handle_client(conn: socket.socket, addr):
    try:
        # Recibir datos del cliente
        text = receive_all(conn)
        lines = text.splitlines()

        # Procesar lineas
        if not lines:
            response = "ERROR: entrada vacia\n"
        else:
            responses = [process_line(line) for line in lines]
            response = "\n".join(responses) + "\n"

        # Enviar respuesta 
        conn.sendall(response.encode("ascii", errors="replace"))

    except Exception as e:
        msg = f"ERROR: {type(e).__name__}\n"
        conn.sendall(msg.encode("ascii", errors="replace"))
    finally:
        # Cerrar conexion
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        conn.close()

# Funcion que arranca el servidor TCP y maneja las conexiones
def main():
    # Configurar socket del servidor
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(200)
    print(f"Servidor TCP escuchando en {HOST}:{PORT}")

    # Threadpool para manejar clientes
    with ThreadPoolExecutor(max_workers=50) as executor:
        while True:
            conn, addr = server.accept()
            executor.submit(handle_client, conn, addr)


if __name__ == "__main__":
    main()
