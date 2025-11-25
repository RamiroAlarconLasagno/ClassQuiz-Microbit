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
PUERTO_SERIE = 'COM4'
BAUDRATE = 115200
SERVIDOR_CLASSQUIZ = 'http://localhost:8000'
GAME_PIN = '545191'

NOMBRES_RANDOM = [
    "Luna", "Sol", "Estrella", "Cometa", "Nebulosa",
    "Galaxia", "Pulsar", "Quasar", "Asteroid", "Meteor",
    "Planeta", "Satelite", "Orbita", "Eclipse", "Aurora",
    "Cosmo", "Universo", "Vortex", "Quantum", "Photon"
]

# ============================================================================
# ESTADO GLOBAL
# ============================================================================
dispositivos = {}
pregunta_actual = None
tipo_pregunta_actual = None
num_opciones_actual = 4
opciones_actuales = []

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
            print(f"[USB→Conc] ENVIADO: {data}")
        except Exception as e:
            print(f"[USB] Error enviando: {e}")


def leer_usb_loop():
    """Loop que lee mensajes JSON desde USB"""
    print("[USB] Thread de lectura iniciado")
    
    while True:
        try:
            if puerto_serial and puerto_serial.in_waiting:
                bytes_disponibles = puerto_serial.in_waiting
                print(f"[USB] {bytes_disponibles} bytes disponibles")
                
                linea = puerto_serial.readline().decode('utf-8').strip()
                
                if linea:
                    print(f"[USB←Conc] RAW: {linea}")
                    procesar_mensaje_usb(linea)
                else:
                    print(f"[USB] Línea vacía")
        except Exception as e:
            print(f"[USB] Error leyendo: {e}")
            time.sleep(1)
        
        time.sleep(0.05)


def procesar_mensaje_usb(linea):
    """Procesa mensajes JSON desde el concentrador"""
    try:
        print(f"[USB] Parseando JSON...")
        data = json.loads(linea)
        tipo = data.get('type')
        
        print(f"[USB] Tipo detectado: '{tipo}'")
        print(f"[USB] Data completa: {data}")
        
        if tipo == 'discovery_start':
            print("\n[Descubrimiento] Iniciando...")
        
        elif tipo == 'debug':
            print(f"[Debug-Concentrador] {data.get('msg')}")
        
        elif tipo == 'new_device':
            print(f"[Descubrimiento] Nuevo: {data['device_id'][:8]}")
        
        elif tipo == 'device_list':
            registrar_dispositivos(data['devices'])
        
        elif tipo == 'discovery_end':
            print(f"[Descubrimiento] Completo: {data['total']} dispositivos\n")
        
        elif tipo == 'qparams_sent':
            print(f"[QPARAMS] Concentrador envió: tipo={data.get('q_type')}, opciones={data.get('num_options')}")
        
        elif tipo == 'answer':
            device_id = data.get('device_id')
            answer = data.get('answer')
            print(f"[ANSWER] Recibido de {device_id[:8]}: '{answer}'")
            procesar_respuesta(device_id, answer)
        
        elif tipo == 'polling_complete':
            print("[Polling] Completo\n")
        
        elif tipo == 'ping_result':
            device_id = data['device_id']
            status = data['status']
            nombre = dispositivos.get(device_id, {}).get('nombre', device_id[:8])
            print(f"[Ping] {nombre}: {status}")
        
        else:
            print(f"[USB] Mensaje no reconocido: {data}")
    
    except json.JSONDecodeError as e:
        print(f"[USB] JSON INVÁLIDO: {linea}")
        print(f"[USB] Error: {e}")
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
            nombre = f"{choice(NOMBRES_RANDOM)}_{device_id[-4:]}"
            
            cliente = socketio.Client()
            configurar_cliente_socketio(cliente, nombre, device_id)
            
            dispositivos[device_id] = {
                "nombre": nombre,
                "cliente": cliente,
                "conectado": False
            }
            
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
        print(f"[Socket.IO] Conectando {nombre}...")
        cliente.connect(SERVIDOR_CLASSQUIZ)
        
        time.sleep(2.0)
        
        if not info.get('conectado'):
            print(f"[⚠️] {nombre} - No recibió confirmación joined_game")
    
    except Exception as e:
        print(f"[Socket.IO] Error conectando {nombre}: {e}")


# ============================================================================
# SOCKET.IO - EVENTOS CLASSQUIZ
# ============================================================================

def configurar_cliente_socketio(cliente, nombre, device_id):
    """Configura handlers de eventos para un cliente"""
    
    @cliente.event
    def connect():
        print(f"[Socket.IO] {nombre} conectado - enviando join_game...")
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
        cliente.emit('echo_time_sync', data)
    
    @cliente.on('set_question_number')
    def on_set_question(data):
        if list(dispositivos.keys())[0] == device_id:
            print(f"[ClassQuiz] Pregunta recibida por {nombre}")
            procesar_nueva_pregunta(data)
    
    @cliente.on('question_results')
    def on_results(data):
        pass
    
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
    global pregunta_actual, tipo_pregunta_actual, num_opciones_actual, opciones_actuales
    
    pregunta_actual = data.get('question_index', 0)
    question = data.get('question', {})
    
    question_type = question.get('type', 'ABCD')
    if question_type == 'ABCD':
        tipo_pregunta_actual = "unica"
    else:
        tipo_pregunta_actual = "multiple"
    
    answers = question.get('answers', [])
    opciones_actuales = [ans.get('answer', '') for ans in answers]
    num_opciones_actual = len(opciones_actuales)
    
    if num_opciones_actual < 2:
        num_opciones_actual = 4
        opciones_actuales = ['Opcion A', 'Opcion B', 'Opcion C', 'Opcion D']
    
    print(f"\n[ClassQuiz] Pregunta {pregunta_actual}: {tipo_pregunta_actual}, {num_opciones_actual} opciones")
    print(f"[ClassQuiz] Opciones: {opciones_actuales}")
    
    # Enviar parametros al concentrador
    msg = {
        "type": "question_params",
        "q_type": tipo_pregunta_actual,
        "num_options": num_opciones_actual
    }
    print(f"[PROXY→USB] Enviando: {msg}")
    enviar_usb(msg)
    
    # Esperar 10 segundos
    print("[Votacion] Esperando 10 segundos...")
    for i in range(10, 0, -1):
        print(f"[Votacion] {i}...")
        time.sleep(1)
    
    # Iniciar polling
    msg_poll = {"type": "start_poll"}
    print(f"[PROXY→USB] Enviando: {msg_poll}")
    enviar_usb(msg_poll)


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
    
    # Convertir letra a texto completo
    if answer in ['A', 'B', 'C', 'D']:
        indice = ord(answer) - ord('A')
        
        if 0 <= indice < len(opciones_actuales):
            answer_text = opciones_actuales[indice]
            print(f"[Mapeo] {nombre}: {answer} → '{answer_text}'")
        else:
            print(f"[Error] {nombre}: Índice {indice} fuera de rango")
            return
    
    elif answer == "":
        answer_text = ""
        print(f"[Respuesta] {nombre}: (sin respuesta)")
    
    else:
        answer_text = answer
        print(f"[Respuesta] {nombre}: {answer_text}")
    
    try:
        cliente.emit('submit_answer', {
            'question_index': pregunta_actual,
            'answer': answer_text
        })
        print(f"[→ClassQuiz] {nombre}: Enviado ✓")
    
    except Exception as e:
        print(f"[Error] {nombre}: {e}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("PROXY MICROBIT-CLASSQUIZ (DEBUG MODE)")
    print("=" * 80)
    print(f"Servidor: {SERVIDOR_CLASSQUIZ}")
    print(f"Game PIN: {GAME_PIN}")
    print(f"Puerto: {PUERTO_SERIE}")
    print("=" * 80)
    
    if not conectar_serial():
        print("[Error] No se pudo conectar al concentrador")
        sys.exit(1)
    
    thread_usb = threading.Thread(target=leer_usb_loop, daemon=True)
    thread_usb.start()
    
    print("\n[Esperando] Presiona Boton A en el concentrador para descubrir dispositivos")
    print("[Ctrl+C para salir]\n")
    
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