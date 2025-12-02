# utils.py - Funciones auxiliares y helpers
# Sistema Proxy Microbit-ClassQuiz

"""
Funciones auxiliares y utilidades compartidas.
"""

import os
import csv
from datetime import datetime


def crear_directorio_data():
    """Crea directorio data/ si no existe"""
    os.makedirs('data', exist_ok=True)


def validar_url(url):
    """
    Valida formato de URL.
    
    Args:
        url (str): URL a validar
    
    Returns:
        bool: True si URL válida
    """
    if not url:
        return False
    
    return url.startswith('http://') or url.startswith('https://')


def validar_pin(pin):
    """
    Valida que PIN sea numérico y tenga longitud adecuada.
    
    Args:
        pin (str): PIN a validar
    
    Returns:
        bool: True si PIN válido
    """
    if not pin:
        return False
    
    return pin.isdigit() and len(pin) >= 4


def timestamp():
    """
    Retorna timestamp actual en formato HH:MM:SS.
    
    Returns:
        str: Timestamp formateado
    """
    return datetime.now().strftime('%H:%M:%S')


def timestamp_completo():
    """
    Retorna timestamp completo en formato YYYY-MM-DD HH:MM:SS.
    
    Returns:
        str: Timestamp completo
    """
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def exportar_logs(logs, filename=None):
    """
    Exporta lista de logs a archivo .txt.
    
    Args:
        logs (list): Lista de diccionarios con logs
        filename (str): Nombre del archivo (opcional)
    
    Returns:
        str: Nombre del archivo generado
    """
    if not filename:
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"log_{fecha}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("LOG EXPORTADO - Sistema Proxy Microbit-ClassQuiz\n")
            f.write(f"Fecha: {timestamp_completo()}\n")
            f.write("=" * 80 + "\n\n")
            
            for log in logs:
                linea = f"{log.get('timestamp', '')} [{log.get('nivel', 'INFO')}] {log.get('msg', '')}\n"
                f.write(linea)
        
        return filename
        
    except Exception as e:
        print(f"[Utils] Error exportando logs: {e}")
        return None


def leer_csv_config():
    """
    Lee config.csv y retorna diccionario.
    
    Returns:
        dict: Configuración o None si no existe
    """
    try:
        with open('data/config.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return next(reader)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[Utils] Error leyendo config.csv: {e}")
        return None


def leer_csv_alumnos():
    """
    Lee alumnos.csv y retorna lista de diccionarios.
    
    Returns:
        list: Lista de alumnos o lista vacía
    """
    try:
        with open('data/alumnos.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"[Utils] Error leyendo alumnos.csv: {e}")
        return []


def formatear_device_id(device_id):
    """
    Formatea un device_id para mostrar (primeros 8 caracteres).
    
    Args:
        device_id (str): ID completo del dispositivo
    
    Returns:
        str: ID formateado
    """
    if not device_id:
        return "(vacío)"
    
    if len(device_id) > 8:
        return device_id[:8] + "..."
    
    return device_id


def sanitizar_nombre(nombre):
    """
    Sanitiza un nombre de alumno (elimina caracteres problemáticos).
    
    Args:
        nombre (str): Nombre original
    
    Returns:
        str: Nombre sanitizado
    """
    if not nombre:
        return "Sin_Nombre"
    
    # Reemplazar espacios por guiones bajos
    nombre = nombre.replace(' ', '_')
    
    # Eliminar caracteres especiales problemáticos
    caracteres_permitidos = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    nombre_limpio = ''.join(c for c in nombre if c in caracteres_permitidos)
    
    if not nombre_limpio:
        return "Sin_Nombre"
    
    return nombre_limpio


def generar_nombre_temporal(device_id):
    """
    Genera un nombre temporal basado en el device_id.
    
    Args:
        device_id (str): ID del dispositivo
    
    Returns:
        str: Nombre temporal
    """
    if not device_id:
        return "Alumno_Temp"
    
    # Usar últimos 4 caracteres del ID
    sufijo = device_id[-4:] if len(device_id) >= 4 else device_id
    
    return f"Alumno_{sufijo}"


def validar_timeout(timeout):
    """
    Valida que el timeout esté en rango válido.
    
    Args:
        timeout (int): Timeout en segundos
    
    Returns:
        int: Timeout validado (dentro de rango permitido)
    """
    from config import TIMEOUT_VOTACION_MIN, TIMEOUT_VOTACION_MAX
    
    if timeout < TIMEOUT_VOTACION_MIN:
        return TIMEOUT_VOTACION_MIN
    
    if timeout > TIMEOUT_VOTACION_MAX:
        return TIMEOUT_VOTACION_MAX
    
    return timeout