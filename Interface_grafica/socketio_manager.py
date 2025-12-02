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
    print(f"[Socket.IO] crear_cliente llamado para {nombre}")
    print(f"[Socket.IO]   device_id: {device_id[:8]}")
    print(f"[Socket.IO]   url: {url_classquiz}")
    print(f"[Socket.IO]   pin: {game_pin}")

    # Verificar si ya existe (con lock)
    with clientes_lock:
        if device_id in clientes:
            print(f"[Socket.IO] Cliente {nombre} ya existe - abortando")
            return

    print(f"[Socket.IO] Creando nuevo cliente para {nombre}...")

    # Crear nuevo cliente (fuera del lock)
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

        join_data = {
            'username': nombre,
            'game_pin': game_pin,
            'captcha': None,
            'custom_field': None
        }

        print(f"[Socket.IO→ClassQuiz] join_game enviado:")
        print(f"[Socket.IO→ClassQuiz]   username: {nombre}")
        print(f"[Socket.IO→ClassQuiz]   game_pin: {game_pin}")
        print(f"[Socket.IO→ClassQuiz]   data completo: {join_data}")

        cliente.emit('join_game', join_data)

    @cliente.event
    def disconnect():
        print(f"[Socket.IO] {nombre} desconectado")

        if device_id in estado_global['dispositivos']:
            estado_global['dispositivos'][device_id]['estado'] = 'desconectado'

    @cliente.on('joined_game')
    def on_joined_game(data):
        print(f"[Socket.IO←ClassQuiz] ✅ joined_game recibido para {nombre}")
        print(f"[Socket.IO←ClassQuiz]   data: {data}")
        print(f"[Socket.IO] {nombre} unido al juego ✓")

        if device_id in estado_global['dispositivos']:
            estado_global['dispositivos'][device_id]['estado'] = 'online'
            print(f"[Socket.IO] Estado de {nombre} actualizado a 'online'")

    @cliente.on('start_game')
    def on_start_game(data):
        print(f"[Socket.IO] Juego iniciado (detectado por {nombre})")

    @cliente.on('time_sync')
    def on_time_sync(data):
        """Responder a sincronización de tiempo"""
        try:
            print(f"[Socket.IO←ClassQuiz] time_sync recibido de {nombre}: {data}")
            cliente.emit('echo_time_sync', data)
            print(f"[Socket.IO→ClassQuiz] echo_time_sync enviado de {nombre}")
        except Exception as e:
            print(f"[Socket.IO] Error en time_sync de {nombre}: {e}")

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
        print(f"[Socket.IO←ClassQuiz] ❌ ERROR recibido para {nombre}")
        print(f"[Socket.IO←ClassQuiz]   data: {data}")

    @cliente.on('username_already_exists')
    def on_username_exists():
        print(f"[Socket.IO←ClassQuiz] ⚠️ username_already_exists recibido")
        print(f"[Socket.IO←ClassQuiz]   Username: '{nombre}' ya existe en el juego")
        print(f"[Socket.IO] ADVERTENCIA: Username '{nombre}' ya existe - puede causar problemas")

    @cliente.on('game_not_found')
    def on_game_not_found():
        print(f"[Socket.IO←ClassQuiz] ❌ game_not_found recibido")
        print(f"[Socket.IO←ClassQuiz]   Game PIN: {game_pin}")
        print(f"[Socket.IO] ERROR CRÍTICO: Juego {game_pin} no encontrado - verificar PIN en ClassQuiz")

    # ===== CONECTAR =====

    print(f"[Socket.IO] Configurando conexión para {nombre}...")

    try:
        print(f"[Socket.IO] Conectando {nombre} a {url_classquiz}...")
        print(f"[Socket.IO] Transports: websocket, polling")

        cliente.connect(
            url_classquiz,
            transports=['websocket', 'polling']
        )

        print(f"[Socket.IO] ✓ Conexión establecida para {nombre}")

        # Guardar cliente (con lock)
        with clientes_lock:
            clientes[device_id] = cliente
            print(f"[Socket.IO] Cliente {nombre} guardado en diccionario")

        # Actualizar estado
        if device_id in estado_global['dispositivos']:
            estado_global['dispositivos'][device_id]['socket'] = True
            print(f"[Socket.IO] Estado actualizado para {nombre}")

        print(f"[Socket.IO] ✓✓ Cliente {nombre} completamente configurado")

    except Exception as e:
        print(f"[Socket.IO] ❌ Error conectando {nombre}: {e}")
        import traceback
        traceback.print_exc()


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
    print(f"[Socket.IO] enviar_respuesta llamado:")
    print(f"[Socket.IO]   device_id: {device_id[:8]}")
    print(f"[Socket.IO]   respuesta_letra: '{respuesta_letra}'")

    with clientes_lock:
        if device_id not in clientes:
            print(f"[Socket.IO] ❌ Cliente {device_id[:8]} no existe en diccionario")
            print(f"[Socket.IO] Clientes disponibles: {list(clientes.keys())}")
            return

        cliente = clientes[device_id]
        print(f"[Socket.IO] ✓ Cliente encontrado en diccionario")

    pregunta = estado.get('pregunta_actual')

    if not pregunta:
        print("[Socket.IO] ❌ No hay pregunta activa en estado")
        return

    print(f"[Socket.IO] Pregunta activa: #{pregunta.get('index')}")
    print(f"[Socket.IO] Opciones disponibles: {pregunta.get('opciones')}")

    # Mapear letra a texto completo
    if respuesta_letra and respuesta_letra in ['A', 'B', 'C', 'D']:
        indice = ord(respuesta_letra) - ord('A')
        opciones = pregunta['opciones']

        print(f"[Socket.IO] Mapeando letra '{respuesta_letra}' → índice {indice}")

        if 0 <= indice < len(opciones):
            respuesta_texto = opciones[indice]
            print(f"[Socket.IO] Mapeo exitoso: '{respuesta_letra}' → '{respuesta_texto}'")
        else:
            print(f"[Socket.IO] ❌ Índice {indice} fuera de rango (opciones: {len(opciones)})")
            return

    elif respuesta_letra == "":
        respuesta_texto = ""
        print(f"[Socket.IO] Respuesta vacía")

    else:
        respuesta_texto = respuesta_letra
        print(f"[Socket.IO] Respuesta texto directo: '{respuesta_texto}'")

    # Enviar a ClassQuiz
    try:
        answer_data = {
            'question_index': pregunta['index'],
            'answer': respuesta_texto
        }

        nombre = estado['dispositivos'].get(device_id, {}).get('nombre', device_id[:8])

        print(f"[Socket.IO→ClassQuiz] submit_answer enviado:")
        print(f"[Socket.IO→ClassQuiz]   alumno: {nombre}")
        print(f"[Socket.IO→ClassQuiz]   question_index: {pregunta['index']}")
        print(f"[Socket.IO→ClassQuiz]   answer: '{respuesta_texto}'")
        print(f"[Socket.IO→ClassQuiz]   data completo: {answer_data}")

        cliente.emit('submit_answer', answer_data)

        print(f"[Socket.IO] ✅ Respuesta enviada exitosamente: {nombre} → '{respuesta_texto}'")

    except Exception as e:
        print(f"[Socket.IO] ❌ Error enviando respuesta: {e}")
        import traceback
        traceback.print_exc()


def conectar_todos(estado):
    """
    Conecta todos los dispositivos registrados a ClassQuiz.

    Args:
        estado (dict): Estado global compartido
    """
    print("[Socket.IO] Iniciando conectar_todos...")
    dispositivos_a_conectar = []

    # Obtener lista de dispositivos
    for device_id, info in estado['dispositivos'].items():
        with clientes_lock:
            if device_id not in clientes:
                dispositivos_a_conectar.append((device_id, info))
                print(f"[Socket.IO] Agregado a lista: {info.get('nombre', device_id[:8])}")
            else:
                print(f"[Socket.IO] Ya conectado: {info.get('nombre', device_id[:8])}")

    print(f"[Socket.IO] Total a conectar: {len(dispositivos_a_conectar)}")

    # Conectar cada dispositivo en thread separado
    for idx, (device_id, info) in enumerate(dispositivos_a_conectar, 1):
        print(f"[Socket.IO] Iniciando thread {idx}/{len(dispositivos_a_conectar)}: {info.get('nombre', device_id[:8])}")

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

    print(f"[Socket.IO] Todos los threads iniciados ({len(dispositivos_a_conectar)} dispositivos)")


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