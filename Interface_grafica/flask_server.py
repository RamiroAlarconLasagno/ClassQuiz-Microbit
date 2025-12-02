# flask_server.py - Servidor Flask con API REST y WebSocket
# Sistema Proxy Microbit-ClassQuiz

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
import csv
import os
import time
from threading import Thread, Lock

import serial_manager
import socketio_manager
import config
import utils

# Crear aplicación Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

# Inicializar Socket.IO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading'
)

# Estado global compartido
estado = {
    'puerto_conectado': False,
    'puerto_nombre': None,
    'url_classquiz': config.DEFAULT_URL_CLASSQUIZ,
    'game_pin': config.DEFAULT_GAME_PIN,
    'timeout_votacion': config.DEFAULT_TIMEOUT,
    'dispositivos': {},  # {device_id: {nombre, estado, socket}}
    'pregunta_actual': None,
    'alumnos': [],
    'votacion_activa': False
}

# Lock para acceso seguro al estado
estado_lock = Lock()

# ============================================================================
# RUTAS HTTP
# ============================================================================

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Obtener configuración actual"""
    with estado_lock:
        return jsonify({
            'url': estado['url_classquiz'],
            'pin': estado['game_pin'],
            'puerto': estado['puerto_nombre'],
            'timeout': estado['timeout_votacion'],
            'conectado': estado['puerto_conectado']
        })


@app.route('/api/config', methods=['POST'])
def set_config():
    """Actualizar configuración y guardar en CSV"""
    try:
        data = request.json
        
        with estado_lock:
            # Validar datos
            url = data.get('url', estado['url_classquiz'])
            if not utils.validar_url(url):
                return jsonify({'error': 'URL inválida'}), 400
            
            pin = data.get('pin', estado['game_pin'])
            if not utils.validar_pin(pin):
                return jsonify({'error': 'PIN inválido'}), 400
            
            timeout = int(data.get('timeout', estado['timeout_votacion']))
            if timeout < 5 or timeout > 300:
                return jsonify({'error': 'Timeout debe estar entre 5 y 300 segundos'}), 400
            
            # Actualizar estado
            estado['url_classquiz'] = url
            estado['game_pin'] = pin
            estado['timeout_votacion'] = timeout
        
        # Guardar en archivo
        guardar_config()
        
        # Notificar a clientes web
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': 'Configuración actualizada correctamente',
            'timestamp': utils.timestamp()
        })
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/puertos', methods=['GET'])
def listar_puertos():
    """Detectar puertos COM disponibles"""
    try:
        puertos = serial_manager.detectar_puertos()
        return jsonify({'puertos': puertos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/descubrir', methods=['POST'])
def descubrir_dispositivos():
    """Iniciar descubrimiento de micro:bits"""
    if not estado['puerto_conectado']:
        return jsonify({'error': 'Puerto no conectado'}), 400
    
    try:
        serial_manager.enviar({'type': 'start_discovery'})
        
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': 'Descubrimiento de dispositivos iniciado',
            'timestamp': utils.timestamp()
        })
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alumnos', methods=['GET'])
def get_alumnos():
    """Obtener lista de alumnos"""
    with estado_lock:
        return jsonify({'alumnos': estado['alumnos']})


@app.route('/api/alumnos', methods=['POST'])
def guardar_alumnos():
    """Guardar lista de alumnos en CSV"""
    try:
        data = request.json
        
        with estado_lock:
            estado['alumnos'] = data.get('alumnos', [])
        
        # Guardar en archivo
        utils.crear_directorio_data()
        
        with open(config.ALUMNOS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['device_id', 'nombre_alumno'])
            writer.writeheader()
            
            for alumno in estado['alumnos']:
                writer.writerow({
                    'device_id': alumno.get('id', ''),
                    'nombre_alumno': alumno.get('nombre', '')
                })
        
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': f"Lista de alumnos guardada ({len(estado['alumnos'])} registros)",
            'timestamp': utils.timestamp()
        })
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cargar_config', methods=['POST'])
def cargar_configuracion():
    """Cargar config.csv y alumnos.csv"""
    try:
        config_cargada = {}
        alumnos_cargados = []
        
        # Cargar configuración
        config_data = utils.leer_csv_config()
        if config_data:
            with estado_lock:
                estado['url_classquiz'] = config_data.get('url', estado['url_classquiz'])
                estado['game_pin'] = config_data.get('game_pin', estado['game_pin'])
                estado['timeout_votacion'] = int(config_data.get('timeout_votacion', estado['timeout_votacion']))
            
            config_cargada = {
                'url': estado['url_classquiz'],
                'pin': estado['game_pin'],
                'timeout': estado['timeout_votacion']
            }
        
        # Cargar alumnos
        alumnos_data = utils.leer_csv_alumnos()
        if alumnos_data:
            alumnos_cargados = [
                {
                    'id': a.get('device_id', ''),
                    'nombre': a.get('nombre_alumno', ''),
                    'estado': 'offline'
                }
                for a in alumnos_data
            ]
            
            with estado_lock:
                estado['alumnos'] = alumnos_cargados
                
                # Actualizar dispositivos conocidos
                for alumno in alumnos_cargados:
                    if alumno['id']:
                        if alumno['id'] not in estado['dispositivos']:
                            estado['dispositivos'][alumno['id']] = {
                                'id': alumno['id'],
                                'nombre': alumno['nombre'],
                                'estado': 'registrado'
                            }
        
        # Emitir evento de carga completa
        socketio.emit('config_cargada', {
            'config': config_cargada,
            'alumnos': alumnos_cargados
        })
        
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': f"Configuración cargada: {len(alumnos_cargados)} alumnos",
            'timestamp': utils.timestamp()
        })
        
        return jsonify({'success': True})
        
    except FileNotFoundError:
        return jsonify({'error': 'Archivos de configuración no encontrados'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# WEBSOCKET EVENTS (Flask-SocketIO)
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Cliente web conectado"""
    emit('log', {
        'nivel': 'INFO',
        'msg': 'Conectado al servidor proxy',
        'timestamp': utils.timestamp()
    })
    
    # Enviar estado actual
    with estado_lock:
        emit('dispositivos_actualizados', {
            'dispositivos': list(estado['dispositivos'].values())
        })


@socketio.on('disconnect')
def handle_disconnect():
    """Cliente web desconectado"""
    print("[Flask] Cliente web desconectado")


@socketio.on('test_usb')
def handle_test_usb():
    """Test de conexión USB"""
    if not estado['puerto_conectado']:
        emit('log', {
            'nivel': 'ERROR',
            'msg': 'Puerto USB no conectado',
            'timestamp': utils.timestamp()
        })
        return
    
    try:
        serial_manager.enviar({'type': 'ping_all'})
        
        emit('log', {
            'nivel': 'INFO',
            'msg': 'Comando de test enviado al concentrador',
            'timestamp': utils.timestamp()
        })
    except Exception as e:
        emit('log', {
            'nivel': 'ERROR',
            'msg': f"Error en test USB: {str(e)}",
            'timestamp': utils.timestamp()
        })


@socketio.on('iniciar_votacion')
def handle_iniciar_votacion():
    """Iniciar proceso de votación con countdown"""
    
    with estado_lock:
        if not estado['pregunta_actual']:
            emit('log', {
                'nivel': 'ERROR',
                'msg': 'No hay pregunta activa',
                'timestamp': utils.timestamp()
            })
            return
        
        timeout = estado['timeout_votacion']
        estado['votacion_activa'] = True
    
    # Thread para countdown
    def countdown():
        for i in range(timeout, 0, -1):
            socketio.emit('countdown', {'segundos': i})
            time.sleep(1)
        
        # Finalizar polling
        serial_manager.enviar({'type': 'start_poll'})
        
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': 'Polling de respuestas iniciado',
            'timestamp': utils.timestamp()
        })
        
        with estado_lock:
            estado['votacion_activa'] = False
    
    Thread(target=countdown, daemon=True).start()


@socketio.on('finalizar_votacion')
def handle_finalizar_votacion():
    """Finalizar votación anticipadamente"""
    try:
        serial_manager.enviar({'type': 'start_poll'})
        
        with estado_lock:
            estado['votacion_activa'] = False
        
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': 'Votación finalizada manualmente',
            'timestamp': utils.timestamp()
        })
    except Exception as e:
        socketio.emit('log', {
            'nivel': 'ERROR',
            'msg': f"Error finalizando votación: {str(e)}",
            'timestamp': utils.timestamp()
        })


# ============================================================================
# PROCESAMIENTO MENSAJES USB
# ============================================================================

def procesar_mensaje_usb(mensaje):
    """
    Callback desde main.py cuando llega mensaje USB.
    Esta función procesa los mensajes JSON del concentrador.
    """
    try:
        # Intentar parsear como JSON
        data = json.loads(mensaje)
        tipo = data.get('type')
        
        # Log de depuración
        socketio.emit('log', {
            'nivel': 'DEBUG',
            'msg': f"USB←Conc: {mensaje[:100]}",
            'timestamp': utils.timestamp()
        })
        
        # Procesar según tipo de mensaje
        if tipo == 'device_list':
            procesar_device_list(data)
        
        elif tipo == 'answer':
            procesar_answer(data)
        
        elif tipo == 'debug':
            socketio.emit('log', {
                'nivel': 'DEBUG',
                'msg': f"[Concentrador] {data.get('msg', '')}",
                'timestamp': utils.timestamp()
            })
        
        elif tipo == 'qparams_sent':
            socketio.emit('log', {
                'nivel': 'INFO',
                'msg': f"Parámetros enviados: {data.get('q_type')} - {data.get('num_options')} opciones",
                'timestamp': utils.timestamp()
            })
        
        elif tipo == 'ping_result':
            device_id = data.get('device_id', '')
            status = data.get('status', '')
            nombre = estado['dispositivos'].get(device_id, {}).get('nombre', device_id[:8])
            
            socketio.emit('log', {
                'nivel': 'INFO',
                'msg': f"Ping {nombre}: {status}",
                'timestamp': utils.timestamp()
            })
    
    except json.JSONDecodeError:
        socketio.emit('log', {
            'nivel': 'ERROR',
            'msg': f"JSON inválido del concentrador: {mensaje[:50]}...",
            'timestamp': utils.timestamp()
        })
    
    except Exception as e:
        socketio.emit('log', {
            'nivel': 'ERROR',
            'msg': f"Error procesando mensaje USB: {str(e)}",
            'timestamp': utils.timestamp()
        })


def procesar_device_list(data):
    """Procesa lista de dispositivos detectados"""
    devices = data.get('devices', [])
    
    print(f"[Flask] Dispositivos detectados: {len(devices)}")
    
    with estado_lock:
        for dev_id in devices:
            if dev_id not in estado['dispositivos']:
                # Buscar nombre en alumnos cargados
                nombre = None
                for a in estado['alumnos']:
                    if a.get('id') == dev_id:
                        nombre = a.get('nombre')
                        break
                
                if not nombre:
                    nombre = f"Alumno_{dev_id[-4:]}"
                
                estado['dispositivos'][dev_id] = {
                    'id': dev_id,
                    'nombre': nombre,
                    'estado': 'registrado'
                }
                
                print(f"[Flask] Nuevo dispositivo: {dev_id[:8]} → {nombre}")
    
    # Emitir actualización
    socketio.emit('dispositivos_actualizados', {
        'dispositivos': list(estado['dispositivos'].values())
    })
    
    socketio.emit('log', {
        'nivel': 'INFO',
        'msg': f"Descubrimiento completo: {len(devices)} dispositivo(s)",
        'timestamp': utils.timestamp()
    })
    
    # Conectar dispositivos a ClassQuiz
    socketio_manager.conectar_todos(estado)


def procesar_answer(data):
    """Procesa respuesta de estudiante"""
    device_id = data.get('device_id')
    respuesta = data.get('answer')
    
    with estado_lock:
        nombre = estado['dispositivos'].get(device_id, {}).get('nombre', device_id[:8])
    
    print(f"[Flask] Respuesta recibida: {nombre} → {respuesta}")
    
    # Emitir a frontend
    socketio.emit('respuesta_recibida', {
        'device_id': device_id,
        'nombre': nombre,
        'respuesta': respuesta
    })
    
    # Enviar a ClassQuiz
    socketio_manager.enviar_respuesta(device_id, respuesta, estado)


# ============================================================================
# HELPERS
# ============================================================================

def guardar_config():
    """Guardar configuración en CSV"""
    utils.crear_directorio_data()
    
    try:
        with open(config.CONFIG_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'url', 'game_pin', 'puerto_serie', 'timeout_votacion'
            ])
            writer.writeheader()
            
            with estado_lock:
                writer.writerow({
                    'url': estado['url_classquiz'],
                    'game_pin': estado['game_pin'],
                    'puerto_serie': estado['puerto_nombre'] or '',
                    'timeout_votacion': estado['timeout_votacion']
                })
        
        print("[Flask] Configuración guardada correctamente")
        
    except Exception as e:
        print(f"[Flask] Error guardando configuración: {e}")


def run_server():
    """
    Ejecutar servidor Flask.
    Llamado desde main.py en thread separado.
    """
    print(f"[Flask] Iniciando servidor en http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    
    socketio.run(
        app,
        debug=False,
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        use_reloader=False,  # Crítico para threads
        log_output=False
    )