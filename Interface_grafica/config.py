# config.py - Configuración global del sistema
# Sistema Proxy Microbit-ClassQuiz

"""
Configuración global del sistema Proxy Microbit-ClassQuiz.
Define constantes y valores por defecto.
"""

# ============================================================================
# FLASK SERVER
# ============================================================================

FLASK_HOST = '127.0.0.1'
FLASK_PORT = 5000
SECRET_KEY = 'microbit-classquiz-2025-fundacion-sadosky'

# ============================================================================
# SERIAL (USB)
# ============================================================================

BAUDRATE = 115200
SERIAL_TIMEOUT = 1  # segundos
USB_READ_INTERVAL = 0.05  # segundos entre lecturas

# ============================================================================
# DEFAULTS
# ============================================================================

DEFAULT_URL_CLASSQUIZ = 'http://localhost:8000'
DEFAULT_GAME_PIN = '149206'
DEFAULT_TIMEOUT = 30  # segundos para votación

# ============================================================================
# ARCHIVOS
# ============================================================================

DATA_DIR = 'data'
CONFIG_FILE = 'data/config.csv'
ALUMNOS_FILE = 'data/alumnos.csv'

# ============================================================================
# LOGGING
# ============================================================================

LOG_FORMAT = '[%(asctime)s] [%(levelname)s] %(message)s'
LOG_DATE_FORMAT = '%H:%M:%S'

# ============================================================================
# MICRO:BIT
# ============================================================================

MAX_DISPOSITIVOS = 30
DEVICE_ID_LENGTH = 16  # caracteres hex del ID único

# ============================================================================
# SOCKET.IO
# ============================================================================

SOCKETIO_RECONNECTION_ATTEMPTS = 5
SOCKETIO_RECONNECTION_DELAY = 1  # segundos
SOCKETIO_RECONNECTION_DELAY_MAX = 5  # segundos

# ============================================================================
# TIMEOUTS
# ============================================================================

TIMEOUT_VOTACION_MIN = 5  # segundos mínimo
TIMEOUT_VOTACION_MAX = 300  # segundos máximo

# ============================================================================
# VERSIÓN
# ============================================================================

VERSION = '1.0.0'
AUTOR = 'Fundación Dr. Manuel Sadosky - Proyecto CDIA'