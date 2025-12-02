# serial_manager.py - Gestión de puerto serie USB
# Sistema Proxy Microbit-ClassQuiz

import serial
import serial.tools.list_ports
import json
import time
from threading import Lock

import config

# Variable global del puerto serie
puerto_serial = None
puerto_lock = Lock()


def detectar_puertos():
    """
    Detecta puertos COM/ttyACM disponibles.
    
    Returns:
        list: Lista de diccionarios con 'port' y 'description'
    """
    puertos = serial.tools.list_ports.comports()
    
    resultado = []
    for p in puertos:
        resultado.append({
            'port': p.device,
            'description': p.description
        })
    
    print(f"[Serial] Detectados {len(resultado)} puerto(s)")
    return resultado


def conectar(puerto, baudrate=None):
    """
    Conecta al puerto serie.
    
    Args:
        puerto (str): Nombre del puerto (ej: 'COM4', '/dev/ttyACM0')
        baudrate (int): Velocidad de comunicación (default: de config)
    
    Returns:
        bool: True si conectó exitosamente
    """
    global puerto_serial
    
    if baudrate is None:
        baudrate = config.BAUDRATE
    
    try:
        with puerto_lock:
            # Cerrar puerto anterior si existe
            if puerto_serial and puerto_serial.is_open:
                puerto_serial.close()
            
            # Abrir nuevo puerto
            puerto_serial = serial.Serial(
                puerto,
                baudrate,
                timeout=config.SERIAL_TIMEOUT
            )
            
            # Esperar inicialización del micro:bit
            time.sleep(2)
        
        print(f"[Serial] Conectado a {puerto} @ {baudrate} baudios")
        return True
        
    except serial.SerialException as e:
        print(f"[Serial] Error conectando a {puerto}: {e}")
        return False
    except Exception as e:
        print(f"[Serial] Error inesperado: {e}")
        return False


def enviar(data):
    """
    Envía diccionario como JSON por puerto serie.
    
    Args:
        data (dict): Diccionario a enviar
    
    Returns:
        bool: True si envío exitoso
    """
    if not esta_conectado():
        print("[Serial] Error: Puerto no conectado")
        return False
    
    try:
        with puerto_lock:
            # Convertir a JSON y agregar newline
            mensaje = json.dumps(data) + '\n'
            
            # Enviar bytes
            puerto_serial.write(mensaje.encode('utf-8'))
            puerto_serial.flush()
        
        print(f"[Serial→USB] Enviado: {data}")
        return True
        
    except serial.SerialException as e:
        print(f"[Serial] Error enviando: {e}")
        return False
    except Exception as e:
        print(f"[Serial] Error inesperado enviando: {e}")
        return False


def leer():
    """
    Lee línea desde puerto serie (non-blocking).
    
    Returns:
        str: Línea leída o None si no hay datos
    """
    if not esta_conectado():
        return None
    
    try:
        with puerto_lock:
            # Verificar si hay datos disponibles
            if puerto_serial.in_waiting > 0:
                # Leer línea completa
                linea = puerto_serial.readline()
                
                # Decodificar y limpiar
                linea_str = linea.decode('utf-8', errors='ignore').strip()
                
                if linea_str:
                    return linea_str
        
        return None
        
    except serial.SerialException as e:
        print(f"[Serial] Error leyendo: {e}")
        return None
    except Exception as e:
        print(f"[Serial] Error inesperado leyendo: {e}")
        return None


def desconectar():
    """Cierra el puerto serie"""
    global puerto_serial
    
    try:
        with puerto_lock:
            if puerto_serial and puerto_serial.is_open:
                puerto_serial.close()
                print("[Serial] Puerto cerrado")
            
            puerto_serial = None
            
    except Exception as e:
        print(f"[Serial] Error desconectando: {e}")


def esta_conectado():
    """
    Verifica si el puerto está abierto y listo.
    
    Returns:
        bool: True si puerto abierto
    """
    try:
        with puerto_lock:
            return puerto_serial is not None and puerto_serial.is_open
    except:
        return False


def obtener_info_puerto():
    """
    Obtiene información del puerto actual.
    
    Returns:
        dict: Info del puerto o None
    """
    try:
        with puerto_lock:
            if puerto_serial and puerto_serial.is_open:
                return {
                    'port': puerto_serial.port,
                    'baudrate': puerto_serial.baudrate,
                    'timeout': puerto_serial.timeout,
                    'in_waiting': puerto_serial.in_waiting
                }
        return None
    except:
        return None