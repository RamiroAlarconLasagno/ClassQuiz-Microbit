# proxy.py - Proxy USB-Concentrador <-> ClassQuiz Socket.IO
# Ejecutar: python proxy.py

import serial
import socketio
import json
import time
import threading
import sys
from random import choice

# ============================================================================
# CONFIGURACION
# ============================================================================
PUERTO_SERIE = 'COM4'  # Cambiar segun sistema (COM3 Windows, /dev/ttyACM0 Linux)
BAUDRATE = 115200
SERVIDOR_CLASSQUIZ = 'http://localhost:8000'
GAME_PIN = '307726'

NOMBRES_RANDOM = [
    "Luna", "Sol", "Estrella", "Cometa", "Nebulosa",
    "Galaxia", "Pulsar", "Quasar", "Asteroid", "Meteor",
    "Planeta", "Satelite", "Orbita", "Eclipse", "Aurora",
    "Cosmo", "Universo", "Vortex", "Quantum", "Photon"
]

# ============================================================================
# ESTADO GLOBAL
# ============================================================================
dispositivos = {}  # {device_id: {"nombre": str, "cliente": socketio.Client}}
pregunta_actual = None
tipo_pregunta_actual = None
num_opciones_actual = 4

puerto_serial = None
lock_serial = threading.Lock()

# ============================================================================
# FUNCIONES USB
# ============================================================================

def conectar_serial():
    """Conecta al puerto serie del concentrador"""
    global puerto_serial
    try:
        puerto_serial = serial.Serial(PUERTO_SERIE, BAUDRATE, timeout=1)
        print(f"[USB] Conectado a {PUERTO_SERIE}")
        return True
    except Exception as e:
        print(f"[USB] Error conectando: {e}")
        return False


def enviar_usb(data):
    """Envia JSON por USB al concentrador"""
    with lock_serial:
        try:
            mensaje = json.dumps(data) + '\n'
            puerto_serial.write(mensaje.encode('utf-8'))
            print(f"[USB→Conc] {data}")
        except Exception as e:
            print(f"[USB] Error enviando: {e}")


def leer_usb_loop():
    """Loop que lee mensajes JSON desde USB"""
    print("[USB] Thread de lectura iniciado")
    
    while True:
        try:
            if puerto_serial and puerto_serial.in_waiting:
                linea = puerto_serial.readline().decode('utf-8').strip()
                if linea:
                    procesar_mensaje_usb(linea)
        except Exception as e:
            print(f"[USB] Error leyendo: {e}")
            time.sleep(1)
        
        time.sleep(0.05)


def procesar_mensaje_usb(linea):
    """Procesa mensajes JSON desde el concentrador"""
    try:
        data = json.loads(linea)
        tipo = data.get('type')
        
        if tipo == 'discovery_start':
            print("\n[Descubrimiento] Iniciando...")
        
        elif tipo == 'debug':
            print(f"[Debug] {data.get('msg')}")
        
        elif tipo == 'new_device':
            print(f"[Descubrimiento] Nuevo: {data['device_id'][:8]}")
        
        elif tipo == 'device_list':
            registrar_dispositivos(data['devices'])
        
        elif tipo == 'discovery_end':
            print(f"[Descubrimiento] Completo: {data['total']} dispositivos\n")
        
        elif tipo == 'answer':
            procesar_respuesta(data['device_id'], data['answer'])
        
        elif tipo == 'polling_complete':
            print("[Polling] Completo\n")
        
        elif tipo == 'ping_result':
            device_id = data['device_id']
            status = data['status']
            nombre = dispositivos.get(device_id, {}).get('nombre', device_id[:8])
            print(f"[Ping] {nombre}: {status}")
        
        else:
            print(f"[USB←Conc] {data}")
    
    except json.JSONDecodeError:
        print(f"[USB] JSON invalido: {linea}")
    except Exception as e:
        print(f"[USB] Error procesando: {e}")


# ============================================================================
# GESTION DE DISPOSITIVOS
# ============================================================================

def registrar_dispositivos(lista_ids):
    """Crea clientes Socket.IO para cada dispositivo"""
    global dispositivos
    
    print(f"\n[Registro] {len(lista_ids)} dispositivos detectados")
    
    for device_id in lista_ids:
        if device_id not in dispositivos:
            # Generar nombre random
            nombre = f"{choice(NOMBRES_RANDOM)}_{device_id[-4:]}"
            
            # Crear cliente Socket.IO
            cliente = socketio.Client()
            configurar_cliente_socketio(cliente, nombre, device_id)
            
            # Guardar en diccionario
            dispositivos[device_id] = {
                "nombre": nombre,
                "cliente": cliente,
                "conectado": False
            }
            
            # Conectar en thread separado
            threading.Thread(
                target=conectar_cliente,
                args=(device_id,),
                daemon=True
            ).start()
    
    print(f"[Registro] Total: {len(dispositivos)} estudiantes")


def conectar_cliente(device_id):
    """Conecta un cliente Socket.IO individual"""
    info = dispositivos[device_id]
    cliente = info['cliente']
    nombre = info['nombre']
    
    try:
        print(f"[Conectando] {nombre}...")
        cliente.connect(SERVIDOR_CLASSQUIZ)
        # El handler connect() ejecutará join_game automáticamente
        time.sleep(0.3)  # Pequeña pausa entre conexiones
    
    except Exception as e:
        print(f"[Socket.IO] Error conectando {nombre}: {e}")


# ============================================================================
# SOCKET.IO - EVENTOS CLASSQUIZ
# ============================================================================

def configurar_cliente_socketio(cliente, nombre, device_id):
    """Configura handlers de eventos para un cliente"""
    
    @cliente.event
    def connect():
        print(f"[Socket.IO] {nombre} conectado")
        # Join game inmediatamente al conectar
        cliente.emit('join_game', {
            'username': nombre,
            'game_pin': GAME_PIN,
            'captcha': None,
            'custom_field': None
        })
    
    @cliente.event
    def disconnect():
        print(f"[Socket.IO] {nombre} desconectado")
        dispositivos[device_id]['conectado'] = False
    
    @cliente.on('joined_game')
    def on_joined_game(data):
        print(f"[ClassQuiz] {nombre} unido al juego ✓")
        dispositivos[device_id]['conectado'] = True
    
    @cliente.on('start_game')
    def on_start_game():
        print(f"[ClassQuiz] Juego iniciado")
    
    @cliente.on('time_sync')
    def on_time_sync(data):
        # CRITICO: Responder time_sync para validacion JWT
        cliente.emit('echo_time_sync', data)
    
    @cliente.on('set_question_number')
    def on_set_question(data):
        # Solo el primer cliente procesa (evitar duplicados)
        if list(dispositivos.keys())[0] == device_id:
            procesar_nueva_pregunta(data)
    
    @cliente.on('question_results')
    def on_results(data):
        pass  # Silencioso
    
    @cliente.on('final_results')
    def on_final(data):
        print(f"[ClassQuiz] Juego finalizado")
    
    @cliente.on('error')
    def on_error(data):
        print(f"[Socket.IO] Error {nombre}: {data}")
    
    @cliente.on('username_already_exists')
    def on_username_exists():
        print(f"[Socket.IO] WARN: Username {nombre} ya existe")
    
    @cliente.on('game_not_found')
    def on_game_not_found():
        print(f"[Socket.IO] ERROR: Juego {GAME_PIN} no encontrado")


def procesar_nueva_pregunta(data):
    """Procesa pregunta recibida de ClassQuiz"""
    global pregunta_actual, tipo_pregunta_actual, num_opciones_actual
    
    pregunta_actual = data.get('question_index', 0)
    question = data.get('question', {})
    
    # Detectar tipo
    question_type = question.get('type', 'ABCD')
    if question_type == 'ABCD':
        tipo_pregunta_actual = "unica"  # Asumimos unica por defecto
    else:
        tipo_pregunta_actual = "multiple"
    
    # Detectar numero de opciones
    answers = question.get('answers', [])
    num_opciones_actual = len(answers)
    if num_opciones_actual < 2:
        num_opciones_actual = 4
    
    print(f"\n[ClassQuiz] Pregunta {pregunta_actual}: {tipo_pregunta_actual}, {num_opciones_actual} opciones")
    
    # Enviar parametros al concentrador
    enviar_usb({
        "type": "question_params",
        "q_type": tipo_pregunta_actual,
        "num_options": num_opciones_actual
    })
    
    # Esperar 10 segundos para votacion
    print("[Votacion] Esperando 10 segundos...")
    time.sleep(10)
    
    # Iniciar polling
    print("[Polling] Iniciando recoleccion...")
    enviar_usb({"type": "start_poll"})


def procesar_respuesta(device_id, answer):
    """Envia respuesta de estudiante a ClassQuiz"""
    if device_id not in dispositivos:
        print(f"[Warning] Dispositivo desconocido: {device_id}")
        return
    
    info = dispositivos[device_id]
    cliente = info['cliente']
    nombre = info['nombre']
    
    if not info['conectado']:
        print(f"[Warning] {nombre} no conectado")
        return
    
    # Enviar a ClassQuiz
    try:
        cliente.emit('submit_answer', {
            'question_index': pregunta_actual,
            'answer': answer
        })
        
        if answer:
            print(f"[Respuesta] {nombre}: {answer}")
        else:
            print(f"[Respuesta] {nombre}: (vacio)")
    
    except Exception as e:
        print(f"[Error] Enviando respuesta {nombre}: {e}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("PROXY MICROBIT-CLASSQUIZ")
    print("=" * 80)
    print(f"Servidor: {SERVIDOR_CLASSQUIZ}")
    print(f"Game PIN: {GAME_PIN}")
    print(f"Puerto: {PUERTO_SERIE}")
    print("=" * 80)
    
    # Conectar USB
    if not conectar_serial():
        print("[Error] No se pudo conectar al concentrador")
        sys.exit(1)
    
    # Iniciar thread de lectura USB
    thread_usb = threading.Thread(target=leer_usb_loop, daemon=True)
    thread_usb.start()
    
    print("\n[Esperando] Presiona Boton A en el concentrador para descubrir dispositivos")
    print("[Ctrl+C para salir]\n")
    
    # Mantener vivo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Saliendo] Desconectando clientes...")
        for info in dispositivos.values():
            try:
                info['cliente'].disconnect()
            except:
                pass
        print("[OK] Salida limpia")


if __name__ == '__main__':
    main()