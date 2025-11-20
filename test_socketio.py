# test_socketio.py - Prueba de conexión Socket.IO sin micro:bits
# Ejecutar: python test_socketio.py

import socketio
import time
from random import choice

# ============================================================================
# CONFIGURACION
# ============================================================================
SERVIDOR_CLASSQUIZ = 'http://localhost:8000'
GAME_PIN = '951248'  # Cambiar según tu juego

NOMBRES_TEST = ["TestLuna", "TestSol", "TestEstrella"]

# ============================================================================
# PRUEBA
# ============================================================================

def test_connection():
    print("=" * 80)
    print("TEST SOCKET.IO - CLASSQUIZ")
    print("=" * 80)
    print(f"Servidor: {SERVIDOR_CLASSQUIZ}")
    print(f"Game PIN: {GAME_PIN}")
    print("=" * 80)
    
    clientes = []
    
    # Crear clientes
    for nombre in NOMBRES_TEST:
        cliente = socketio.Client()
        
        @cliente.event
        def connect():
            print(f"[✓] {nombre} conectado")
            cliente.emit('join_game', {
                'username': nombre,
                'game_pin': GAME_PIN,
                'captcha': None,
                'custom_field': None
            })
        
        @cliente.event
        def disconnect():
            print(f"[✗] {nombre} desconectado")
        
        @cliente.on('joined_game')
        def on_joined(data):
            print(f"[✓✓] {nombre} UNIDO AL JUEGO")
        
        @cliente.on('time_sync')
        def on_time_sync(data):
            cliente.emit('echo_time_sync', data)
        
        @cliente.on('error')
        def on_error(data):
            print(f"[ERROR] {nombre}: {data}")
        
        @cliente.on('game_not_found')
        def on_not_found():
            print(f"[ERROR] Juego {GAME_PIN} no encontrado")
        
        @cliente.on('username_already_exists')
        def on_exists():
            print(f"[ERROR] {nombre} ya existe")
        
        clientes.append({'cliente': cliente, 'nombre': nombre})
    
    # Conectar todos
    print("\n[Conectando]...")
    for item in clientes:
        try:
            item['cliente'].connect(SERVIDOR_CLASSQUIZ)
            time.sleep(0.3)
        except Exception as e:
            print(f"[ERROR] {item['nombre']}: {e}")
    
    # Esperar
    print("\n[Esperando 10 segundos...]")
    print("Revisa ClassQuiz - deberían aparecer los 3 estudiantes")
    time.sleep(10)
    
    # Desconectar
    print("\n[Desconectando]...")
    for item in clientes:
        try:
            item['cliente'].disconnect()
        except:
            pass
    
    print("\n[OK] Test completo")


if __name__ == '__main__':
    test_connection()