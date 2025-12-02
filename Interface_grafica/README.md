# Sistema Proxy Microbit-ClassQuiz v1.0

Sistema de integración entre dispositivos BBC micro:bit y la plataforma educativa ClassQuiz, desarrollado para la Fundación Dr. Manuel Sadosky - Proyecto CDIA.

## 📋 Descripción

Permite que estudiantes participen en quizzes de ClassQuiz usando micro:bits físicos en lugar de navegadores web. El sistema incluye:

- Aplicación ejecutable con GUI Tkinter para gestión del puerto USB
- Servidor Flask con interface web completa
- Comunicación USB con concentrador micro:bit (hasta 30 dispositivos)
- Múltiples conexiones Socket.IO hacia ClassQuiz (una por estudiante)

## 🚀 Instalación

### Requisitos

- Python 3.9 o superior
- 1 puerto USB disponible
- Navegador web moderno (Chrome, Firefox, Edge)
- ClassQuiz instalado y funcionando

### Instalación para desarrollo
```bash
# Clonar o descomprimir el proyecto
cd microbit_proxy

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python main.py
```

### Compilar ejecutable (opcional)
```bash
# Instalar PyInstaller
pip install pyinstaller

# Compilar
pyinstaller --onefile --windowed \
    --add-data "templates;templates" \
    --add-data "static;static" \
    --add-data "data;data" \
    --icon=icon.ico \
    --name microbit_proxy \
    main.py

# El ejecutable estará en: dist/microbit_proxy.exe
```

## 📖 Uso

### Primera configuración

1. Ejecutar `microbit_proxy.exe` (o `python main.py`)
2. En la ventana Tkinter:
   - Seleccionar puerto COM del concentrador
   - Click en "Conectar" (indicador cambia de 🔴 a 🟢)
   - Click en "Abrir Interface Web"

3. En el navegador (http://localhost:5000):
   - **Tab Configuración:**
     - Ingresar URL de ClassQuiz (ej: `http://localhost:8000`)
     - Ingresar PIN del juego (ej: `149206`)
     - Configurar timeout (default: 30 segundos)
     - Click "Guardar Configuración"
   
   - **Tab Dispositivos:**
     - Click "Descubrir" para detectar micro:bits
     - Asignar nombres a cada device_id
     - Click "Guardar" para persistir en CSV

### Uso diario

1. Ejecutar aplicación → Conectar puerto COM
2. Abrir interface web → Click "Cargar Config"
3. Verificar estados de dispositivos (🟢 conectados)
4. Iniciar quiz en ClassQuiz
5. Estudiantes responden con micro:bits:
   - **Botón A:** Navegar entre opciones (A → B → C → D)
   - **A + B:** Confirmar respuesta
6. Sistema envía respuestas automáticamente al finalizar timeout

## 📁 Estructura del proyecto
```
microbit_proxy/
├── main.py                 # Aplicación principal + GUI
├── flask_server.py         # Servidor Flask
├── serial_manager.py       # Gestión puerto USB
├── socketio_manager.py     # Cliente Socket.IO
├── config.py               # Configuración global
├── utils.py                # Funciones auxiliares
├── requirements.txt        # Dependencias Python
├── README.md               # Este archivo
├── templates/
│   └── index.html          # Interface web
├── static/
│   ├── css/style.css       # Estilos
│   └── js/app.js           # Lógica frontend
└── data/ (generado en runtime)
    ├── config.csv          # URL, PIN, timeout
    └── alumnos.csv         # Device IDs y nombres
```

## 🔧 Configuración avanzada

### Cambiar puerto Flask

Editar `config.py`:
```python
FLASK_PORT = 5000  # Cambiar a otro puerto si 5000 está ocupado
```

### Aumentar límite de dispositivos

Editar `config.py`:
```python
MAX_DISPOSITIVOS = 30  # Aumentar si tienes más micro:bits
```

### Timeout de votación

- **Mínimo:** 5 segundos
- **Máximo:** 300 segundos (5 minutos)
- **Recomendado:** 30-60 segundos

## 🐛 Troubleshooting

### Puerto COM no detectado
- Verificar que drivers de micro:bit estén instalados
- Windows descarga drivers automáticamente en primera conexión
- Desconectar y reconectar el USB

### Estudiante no aparece después de "Descubrir"
- Verificar que micro:bit tenga firmware estudiante.hex flasheado
- Presionar botón A del concentrador para reenviar descubrimiento
- Esperar 10 segundos completos

### Votación no inicia automáticamente
- Verificar que URL y PIN sean correctos en tab Configuración
- ClassQuiz debe mostrar la pregunta antes
- Aumentar timeout en configuración de ClassQuiz a 60s

### Respuestas no llegan a ClassQuiz
- Verificar logs en tab Historial
- Buscar mensajes `[Socket.IO]` con errores
- Reiniciar conexiones: cerrar navegador y volver a abrir

## 📊 Logs y diagnóstico

Los logs se muestran en el tab "Historial" con colores por nivel:

- **🔵 INFO:** Operaciones normales
- **⚪ DEBUG:** Información detallada (opcional)
- **🟡 WARNING:** Advertencias no críticas
- **🔴 ERROR:** Errores que requieren atención

### Exportar logs

Click en botón "📄 Exportar" para guardar logs en archivo .txt

### Pausar auto-scroll

Click en panel de logs para pausar auto-scroll por 5 segundos

## 🔐 Seguridad

- El sistema escucha solo en `localhost` (127.0.0.1)
- No expone puertos al exterior por defecto
- Datos almacenados localmente en CSV sin encriptar
- Para uso en red local, modificar `FLASK_HOST` en config.py

## 📜 Licencias

Todas las dependencias son open source:
- Flask (BSD-3-Clause)
- Flask-SocketIO (MIT)
- python-socketio (MIT)
- pyserial (BSD-3-Clause)
- Socket.IO Client JS (MIT)
- Bootstrap 5 (MIT)

## 👥 Créditos

**Autor del proyecto:** Leandro Batlle  
**Organización:** Fundación Dr. Manuel Sadosky  
**Programa:** CDIA (Centro de Desarrollo e Innovación en IA)  
**Año:** 2025

## 📞 Soporte

Para reportar bugs o solicitar ayuda:
1. Exportar logs desde el tab Historial
2. Capturar pantalla del error
3. Contactar al equipo técnico de Fundación Sadosky

## 🔄 Actualizaciones

**v1.0.0** (Enero 2025)
- Lanzamiento inicial
- Soporte hasta 30 micro:bits
- Interface web completa
- Persistencia en CSV
- Logs en tiempo real

---

**Fundación Dr. Manuel Sadosky**  
Proyecto CDIA - Centro de Desarrollo e Innovación en IA  
https://www.fundacionsadosky.org.ar