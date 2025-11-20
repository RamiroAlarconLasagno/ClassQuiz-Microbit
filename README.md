# Sistema Micro:bit + ClassQuiz

Sistema completo de votación con BBC micro:bit v2 integrado a ClassQuiz.

## Archivos

- `estudiante.py` - Programa para micro:bit de estudiantes
- `concentrador.py` - Programa para micro:bit concentrador (conectado a PC)
- `proxy.py` - Programa Python para PC (puente USB-ClassQuiz)

---

## Requisitos

### Hardware
- 1 micro:bit v2 (concentrador) + cable USB
- N micro:bits v2 (estudiantes)
- Todos configurados en **canal de radio 7**

### Software PC
```bash
pip install pyserial python-socketio[client] requests websocket-client
```

O si prefieres un archivo requirements.txt:
```bash
pip install -r requirements.txt
```

---

## Instalación

### 1. Instalar dependencias Python

**Crear entorno virtual (recomendado):**
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate
```

**Instalar paquetes:**
```bash
pip install -r requirements.txt
```

### 2. Programar micro:bits

**Concentrador:**
- Cargar `concentrador.py` en el micro:bit que estará conectado a PC por USB
- Este actúa como hub entre estudiantes y computadora

**Estudiantes:**
- Cargar `estudiante.py` en todos los micro:bits de estudiantes  
- Pueden funcionar con baterías (no necesitan USB)

**Nota:** Usar editor online (python.microbit.org) o Mu Editor para cargar los programas.

### 3. Configurar proxy.py

Editar estas líneas según tu sistema:

```python
PUERTO_SERIE = 'COM3'  # Windows: COM3, Linux: /dev/ttyACM0, Mac: /dev/tty.usbmodem*
SERVIDOR_CLASSQUIZ = 'http://localhost:8000'
GAME_PIN = '641568'  # PIN del juego ClassQuiz
```

---

## Uso

### Paso 0: Instalar dependencias Python
```bash
# Opción A: Instalación directa
pip install pyserial python-socketio[client] requests websocket-client

# Opción B: Usar requirements.txt (recomendado)
pip install -r requirements.txt
```

### Paso 1: Iniciar ClassQuiz
Crear un juego y obtener el PIN.

### Paso 2: Descubrir dispositivos
```bash
python proxy.py
```

Presionar **Botón A** en el concentrador:
- Envía señal REPORT durante 12 segundos
- Micro:bits estudiantes responden con su ID
- El proxy crea un cliente Socket.IO por cada estudiante
- Todos se unen automáticamente al juego

**Confirmación:** Display del concentrador muestra cantidad detectada.

### Paso 3: Iniciar juego en ClassQuiz
Los estudiantes aparecen como "Luna_abc1", "Estrella_def2", etc.

### Paso 4: Durante preguntas

**Automático:**
1. ClassQuiz envía pregunta → proxy detecta evento
2. Proxy envía parámetros al concentrador por USB
3. Concentrador hace broadcast radio → todos los estudiantes
4. Estudiantes ven ícono (❤ única, ▢ múltiple)

**Estudiante vota (10 segundos):**
- **Botón A:** Cicla opciones A → B → C → D
- **Botón B:** Guarda respuesta
  - Única: reemplaza anterior
  - Múltiple: toggle (agrega/quita)

**Recolección:**
5. Tras 10s, proxy envía comando `start_poll`
6. Concentrador pregunta uno por uno (POLL)
7. Cada estudiante responde cuando escucha su ID
8. Concentrador envía respuestas por USB
9. Proxy traduce a ClassQuiz vía Socket.IO

---

## Protocolo Radio

| Mensaje | Origen | Destino | Descripción |
|---------|--------|---------|-------------|
| `REPORT` | Concentrador | Broadcast | Inicia descubrimiento |
| `ID:abc123` | Estudiante | Concentrador | Responde con ID único |
| `ACK:abc123` | Concentrador | Estudiante | Confirma registro |
| `QPARAMS:multiple:3` | Concentrador | Broadcast | Tipo y opciones de pregunta |
| `POLL:abc123` | Concentrador | Estudiante | Solicita respuesta |
| `ANSWER:abc123:A,C` | Estudiante | Concentrador | Envía respuesta |
| `PING:abc123` | Concentrador | Estudiante | Verifica estado |
| `PONG:abc123` | Estudiante | Concentrador | Confirma online |

---

## Protocolo USB (JSON)

**PC → Concentrador:**
```json
{"type":"question_params", "q_type":"multiple", "num_options":3}
{"type":"start_poll"}
```

**Concentrador → PC:**
```json
{"type":"discovery_start"}
{"type":"debug", "msg":"REPORT_ENVIADO:ronda_1"}
{"type":"new_device", "device_id":"abc123"}
{"type":"device_list", "devices":["abc123","def456"]}
{"type":"discovery_end", "total":2}
{"type":"answer", "device_id":"abc123", "answer":"B"}
{"type":"polling_complete"}
{"type":"ping_result", "device_id":"abc123", "status":"online"}
```

---

## Troubleshooting

**Problema:** Puerto serie no detectado
```bash
# Linux: verificar permisos
sudo usermod -a -G dialout $USER
# Reiniciar sesión

# Windows: verificar en Device Manager
# Mac: ls /dev/tty.usb*
```

**Problema:** Estudiantes no responden
- Verificar mismo canal de radio (7)
- Hacer descubrimiento nuevamente (Botón A)
- Revisar baterías de estudiantes

**Problema:** Respuestas no llegan a ClassQuiz
- Verificar GAME_PIN en proxy.py
- Ver logs del proxy (debería mostrar "unido al juego ✓")
- Confirmar que estudiantes estén en "joined_game"
- **Crítico**: El proxy debe responder a `time_sync` con `echo_time_sync` (ya implementado)
- Revisar consola de ClassQuiz para ver si aparecen los estudiantes

**Problema:** Timeout en polling
- Normal si dispositivo está apagado/lejos
- Se envía respuesta vacía automáticamente
- ClassQuiz lo marca como "sin respuesta"

---

## Timing

- **Descubrimiento:** ~14 segundos
- **Votación:** 10 segundos (configurable en proxy.py)
- **Polling:** ~500ms × N estudiantes + reintentos
- **Total por pregunta:** ~40s para 30 estudiantes

---

## Persistencia

**Estudiantes:**
- Guardan voto en `voto.cfg` tras cada Botón B
- Sobrevive a resets durante votación
- Se borra al recibir nueva pregunta

**Concentrador:**
- Guarda IDs en `devices.cfg`
- No necesita descubrimiento en cada reinicio
- Botón A para forzar redescubrimiento

---

## Extensiones Futuras

- [ ] Validación de respuestas en proxy
- [ ] Dashboard web con estado en tiempo real
- [ ] Timeout configurable por pregunta
- [ ] Modo offline (sin ClassQuiz)
- [ ] Feedback visual cuando respuesta es recolectada
- [ ] Detección automática de puerto serie
- [ ] Configuración vía archivo JSON

---

## Licencia

GPL v3 - Ver LICENSE

## Créditos

Basado en el ecosistema BBC micro:bit y ClassQuiz.