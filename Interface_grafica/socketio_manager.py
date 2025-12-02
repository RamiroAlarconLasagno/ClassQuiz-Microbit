# socketio_manager.py - Cliente Socket.IO hacia ClassQuiz
# Sistema Proxy Microbit-ClassQuiz

import socketio
import time
from threading import Lock, Thread

# Diccionario de clientes Socket.IO {device_id: client}
clientes = {}
clientes_lock = Lock()


def crear_cliente(device_id, nombre, url_classquiz, game_pin, estado_global):
    """
    Crea y conecta un cliente Socket.IO para un dispositivo.
    
    Args:
        device_id (str): ID único del dispositivo
        nombre (str): Nombre del alumno
        url_classquiz (str): URL del servidor ClassQuiz
        game_pin (str): PIN del juego
        estado_global (dict): Referencia al estado compartido
    """
    with clientes_lock:
        if device_id in clientes:
            print(f"[Socket.IO] Cliente {nombre} ya existe")
            return
        
        # Crear nuevo cliente
        cliente = socketio.Client(
            reconnection=True,
            reconnection_attempts=5,
            reconnection_delay=1,
            reconnection_delay_max=5
        )
        
        # ===== CONFIGURAR EVENTOS =====
        
        @cliente.event
        def connect():
            print(f"[Socket.IO] {nombre} conectado - enviando join_game...")
            
            cliente.emit('join_game', {
                'username': nombre,
                'game_pin': game_pin,
                'captcha': None,
                'custom_field': None
            })
        
        @cliente.event
        def disconnect():
            print(f"[Socket.IO] {nombre} desconectado")
            
            if device_id in estado_global['dispositivos']:
                estado_global['dispositivos'][device_id]['estado'] = 'desconectado'
        
        @cliente.on('joined_game')
        def on_joined_game(data):
            print(f"[Socket.IO] {nombre} unido al juego ✓")
            
            if device_id in estado_global['dispositivos']:
                estado_global['dispositivos'][device_id]['estado'] = 'online'
        
        @cliente.on('start_game')
        def on_start_game(data):
            print(f"[Socket.IO] Juego iniciado (detectado por {nombre})")
        
        @cliente.on('time_sync')
        def on_time_sync(data):
            """Responder a sincronización de tiempo"""
            try:
                cliente.emit('echo_time_sync', data)
            except:
                pass
        
        @cliente.on('set_question_number')
        def on_set_question(data):
            """Procesar pregunta recibida de ClassQuiz"""
            
            # Solo procesar una vez (primer dispositivo)
            with clientes_lock:
                primer_dispositivo = list(clientes.keys())[0] if clientes else None
            
            if primer_dispositivo == device_id:
                print(f"[Socket.IO] Pregunta recibida por {nombre}")
                procesar_pregunta_classquiz(data, estado_global)
        
        @cliente.on('question_results')
        def on_results(data):
            """Resultados de pregunta"""
            print(f"[Socket.IO] Resultados recibidos")
        
        @cliente.on('final_results')
        def on_final(data):
            """Resultados finales del juego"""
            print(f"[Socket.IO] Juego finalizado")
        
        @cliente.on('error')
        def on_error(data):
            print(f"[Socket.IO] Error {nombre}: {data}")
        
        @cliente.on('username_already_exists')
        def on_username_exists():
            print(f"[Socket.IO] ADVERTENCIA: Username '{nombre}' ya existe")
        
        @cliente.on('game_not_found')
        def on_game_not_found():
            print(f"[Socket.IO] ERROR: Juego {game_pin} no encontrado")
        
        # ===== CONECTAR =====
        
        try:
            print(f"[Socket.IO] Conectando {nombre} a {url_classquiz}...")
            
            cliente.connect(
                url_classquiz,
                transports=['websocket', 'polling']
            )
            
            # Guardar cliente
            clientes[device_id] = cliente
            
            # Actualizar estado
            if device_id in estado_global['dispositivos']:
                estado_global['dispositivos'][device_id]['socket'] = True
            
            print(f"[Socket.IO] Cliente {nombre} creado exitosamente")
        
        except Exception as e:
            print(f"[Socket.IO] Error conectando {nombre}: {e}")


def procesar_pregunta_classquiz(data, estado):
    """
    Procesa pregunta recibida de ClassQuiz.
    
    Args:
        data (dict): Datos de la pregunta
        estado (dict): Estado global compartido
    """
    try:
        pregunta_idx = data.get('question_index', 0)
        question = data.get('question', {})
        
        # Determinar tipo de pregunta
        question_type = question.get('type', 'ABCD')
        tipo = "unica" if question_type == 'ABCD' else "multiple"
        
        # Extraer opciones
        answers = question.get('answers', [])
        opciones_texto = [ans.get('answer', '') for ans in answers]
        num_opciones = len(opciones_texto)
        
        # Validar número de opciones
        if num_opciones < 2:
            num_opciones = 4
            opciones_texto = ['Opción A', 'Opción B', 'Opción C', 'Opción D']
        
        # Guardar en estado global
        estado['pregunta_actual'] = {
            'index': pregunta_idx,
            'tipo': tipo,
            'num_opciones': num_opciones,
            'opciones': opciones_texto
        }
        
        print(f"[ClassQuiz] Pregunta #{pregunta_idx}: {tipo}, {num_opciones} opciones")
        print(f"[ClassQuiz] Opciones: {opciones_texto}")
        
        # Enviar parámetros al concentrador
        import serial_manager
        
        serial_manager.enviar({
            'type': 'question_params',
            'q_type': tipo,
            'num_options': num_opciones
        })
        
    except Exception as e:
        print(f"[Socket.IO] Error procesando pregunta: {e}")


def enviar_respuesta(device_id, respuesta_letra, estado):
    """
    Envía respuesta de estudiante a ClassQuiz.
    
    Args:
        device_id (str): ID del dispositivo
        respuesta_letra (str): Letra de respuesta (A/B/C/D)
        estado (dict): Estado global compartido
    """
    with clientes_lock:
        if device_id not in clientes:
            print(f"[Socket.IO] Cliente {device_id[:8]} no existe")
            return
        
        cliente = clientes[device_id]
    
    pregunta = estado.get('pregunta_actual')
    
    if not pregunta:
        print("[Socket.IO] No hay pregunta activa")
        return
    
    # Mapear letra a texto completo
    if respuesta_letra and respuesta_letra in ['A', 'B', 'C', 'D']:
        indice = ord(respuesta_letra) - ord('A')
        opciones = pregunta['opciones']
        
        if 0 <= indice < len(opciones):
            respuesta_texto = opciones[indice]
        else:
            print(f"[Socket.IO] Índice {indice} fuera de rango")
            return
    
    elif respuesta_letra == "":
        respuesta_texto = ""
    
    else:
        respuesta_texto = respuesta_letra
    
    # Enviar a ClassQuiz
    try:
        cliente.emit('submit_answer', {
            'question_index': pregunta['index'],
            'answer': respuesta_texto
        })
        
        nombre = estado['dispositivos'].get(device_id, {}).get('nombre', device_id[:8])
        print(f"[Socket.IO] Respuesta enviada: {nombre} → '{respuesta_texto}'")
        
    except Exception as e:
        print(f"[Socket.IO] Error enviando respuesta: {e}")


def conectar_todos(estado):
    """
    Conecta todos los dispositivos registrados a ClassQuiz.
    
    Args:
        estado (dict): Estado global compartido
    """
    dispositivos_a_conectar = []
    
    # Obtener lista de dispositivos
    for device_id, info in estado['dispositivos'].items():
        with clientes_lock:
            if device_id not in clientes:
                dispositivos_a_conectar.append((device_id, info))
    
    # Conectar cada dispositivo en thread separado
    for device_id, info in dispositivos_a_conectar:
        thread = Thread(
            target=crear_cliente,
            args=(
                device_id,
                info['nombre'],
                estado['url_classquiz'],
                estado['game_pin'],
                estado
            ),
            daemon=True
        )
        thread.start()
        
        # Pequeña pausa entre conexiones
        time.sleep(0.5)


def desconectar_todos():
    """Desconecta todos los clientes Socket.IO"""
    with clientes_lock:
        for device_id, cliente in list(clientes.items()):
            try:
                cliente.disconnect()
                print(f"[Socket.IO] Cliente {device_id[:8]} desconectado")
            except:
                pass
        
        clientes.clear()
    
    print("[Socket.IO] Todos los clientes desconectados")


def obtener_estado_clientes():
    """
    Obtiene estado de todos los clientes.
    
    Returns:
        dict: {device_id: {'conectado': bool, 'transporte': str}}
    """
    resultado = {}
    
    with clientes_lock:
        for device_id, cliente in clientes.items():
            try:
                resultado[device_id] = {
                    'conectado': cliente.connected,
                    'transporte': cliente.transport() if hasattr(cliente, 'transport') else 'unknown'
                }
            except:
                resultado[device_id] = {
                    'conectado': False,
                    'transporte': 'error'
                }
    
    return resultado