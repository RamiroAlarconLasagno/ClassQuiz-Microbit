# README.md - Sistema de Votación ClassQuiz con Micro:bit

## Descripción del Proyecto

Sistema de votación distribuida para educación que integra dispositivos **BBC micro:bit** con la plataforma web **ClassQuiz**. Permite a estudiantes participar en quizzes interactivos usando hardware físico en lugar de navegadores web.

---

## Arquitectura del Sistema

```
┌─────────────┐     Radio      ┌──────────────┐
│ Micro:bit   │ ◄────────────► │ Micro:bit    │
│ Estudiante  │     2.4GHz     │ Concentrador │
└─────────────┘                └──────┬───────┘
                                      │ USB-UART
                                      ▼
                               ┌──────────────┐
                               │ Proxy Python │
                               │ (PC/Netbook) │
                               └──────┬───────┘
                                      │ Socket.IO
                                      ▼
                               ┌──────────────┐
                               │  ClassQuiz   │
                               │   Backend    │
                               └──────────────┘
```

### Componentes

**1. Estudiante (estudiante.py)**
- Ejecuta en micro:bit de cada alumno
- Navegación de opciones con botones A/B
- Confirmación de voto con A+B simultáneo
- Display muestra opción actual (A/B/C/D)
- Comunicación por radio con concentrador

**2. Concentrador (concentrador.py)**
- Ejecuta en micro:bit USB conectado a PC
- Coordina hasta 30+ dispositivos estudiante
- Protocolo discovery para registro automático
- Polling secuencial para evitar colisiones
- Bridge USB-UART ↔ Radio

**3. Proxy (proxy.py)**
- Ejecuta en PC/netbook del docente
- Cliente Socket.IO multi-instancia
- Mapeo device_id → username ClassQuiz
- Traducción de protocolos micro:bit ↔ ClassQuiz

---

## Protocolo de Comunicación

### Radio (Micro:bit ↔ Micro:bit)

**Formato CSV:** `COMANDO:parametro1:parametro2`

| Comando | Dirección | Payload | Propósito |
|---------|-----------|---------|-----------|
| `REPORT` | Conc → Est | - | Solicitar registro |
| `ACK:device_id` | Est → Conc | device_id | Respuesta registro |
| `QPARAMS:tipo:num` | Conc → Est | tipo, opciones | Configurar pregunta |
| `POLL:device_id` | Conc → Est | device_id | Solicitar voto |
| `ANSWER:id:opcion` | Est → Conc | device_id, voto | Enviar respuesta |

### USB-UART (Micro:bit ↔ PC)

**Formato JSON** (tolerante a espacios):

```json
{
  "type": "question_params",
  "q_type": "unica",
  "num_options": 4
}
```

```json
{
  "type": "answer",
  "device_id": "1d4a339694f35219",
  "answer": "C"
}
```

### Socket.IO (Proxy ↔ ClassQuiz)

Eventos estándar ClassQuiz:
- `join_game` - Registro con username único
- `set_question_number` - Recepción de pregunta
- `submit_answer` - Envío de respuesta
- `question_results` - Feedback de resultado

---

## Flujo de Votación

```
1. DOCENTE inicia quiz en ClassQuiz web
   ↓
2. PROXY recibe evento "set_question_number"
   ↓
3. PROXY envía por USB: question_params
   ↓
4. CONCENTRADOR broadcast radio: QPARAMS:unica:4
   ↓
5. ESTUDIANTE resetea voto, habilita botones A/B
   ↓
6. ALUMNO navega opciones (A→B→C→D) y confirma (A+B)
   ↓
7. PROXY envía por USB: start_poll
   ↓
8. CONCENTRADOR hace polling: POLL:device_id_1, POLL:device_id_2...
   ↓
9. ESTUDIANTE responde: ANSWER:1d4a339694f35219:C
   ↓
10. CONCENTRADOR reenvía USB: {"type":"answer"...}
    ↓
11. PROXY mapea device_id → username y envía Socket.IO
    ↓
12. CLASSQUIZ procesa voto y muestra resultado
```

---

## Instalación y Uso

### Requisitos

**Hardware:**
- 1 micro:bit v2 (concentrador)
- N micro:bits v2 (estudiantes, máx ~30)
- Cable USB micro:bit ↔ PC
- PC/Netbook con Python 3.8+

**Software:**
- Python 3.8+
- Librerías: `pyserial`, `python-socketio[client]`, `requests`
- Editor Mu o MakeCode para flashear micro:bits

### Instalación

1. **Instalar dependencias Python:**
```bash
pip install pyserial python-socketio requests websocket-client
```

2. **Flashear micro:bits:**
   - `estudiante.py` → Todos los micro:bits de alumnos
   - `concentrador.py` → Micro:bit conectado a USB

3. **Configurar proxy:**
```python
# En proxy.py
SERIAL_PORT = "COM3"  # o /dev/ttyACM0 en Linux
GAME_PIN = "123456"
CLASSQUIZ_URL = "https://classquiz.example.com"
```

4. **Ejecutar sistema:**
```bash
python proxy.py
```

### Uso en Clase

1. Docente crea quiz en ClassQuiz web
2. Inicia juego y obtiene PIN
3. Configura PIN en proxy.py
4. Ejecuta `python proxy.py`
5. Proxy registra automáticamente todos los micro:bits
6. Docente inicia pregunta
7. Alumnos votan con botones
8. Resultados se muestran en ClassQuiz

---

## Características Técnicas

### Gestión de Colisiones Radio

Sistema de dos fases para evitar colisiones entre 30+ dispositivos:

**Fase 1: Discovery (aleatorio con ACK)**
- Concentrador broadcast `REPORT` cada 100ms
- Estudiantes responden con delay aleatorio 0-2000ms
- Concentrador envía ACK confirmando registro
- Estudiante solo se registra tras recibir ACK

**Fase 2: Polling (secuencial)**
- Concentrador itera device_ids registrados
- Envía `POLL:device_id` específico
- Solo el estudiante con ese ID responde
- 0% colisiones garantizadas

### Optimizaciones de Memoria

Micro:bit v2 tiene **128KB RAM**, pero MicroPython consume ~100KB:

- Mensajes radio máx 32 bytes (default) o 64 (config)
- CSV en lugar de JSON: `"A,B,C"` vs `{"a":"A","b":"B"}`
- Sin f-strings: usar `.format()` o concatenación
- Device ID hexadecimal: `''.join(['{:02x}'.format(b) for b in machine.unique_id()])`

### Tolerancia a Reseteos

Estudiantes pierden estado al presionar botón reset:
- Device ID se recalcula (machine.unique_id() = hardware ID)
- Responden a siguiente `REPORT` broadcast
- Proxy mantiene mapeo persistente device_id → username

---

## Archivos del Proyecto

```
/
├── estudiante.py          # Firmware micro:bit alumno
├── concentrador.py        # Firmware micro:bit USB
├── proxy.py               # Servicio Python PC
├── README.md              # Este archivo
├── informe_errores_microbit_uart.md  # Debugging guide
└── arquitectura-completa-microbit-classquiz.mermaid
```

---

## Limitaciones Conocidas

- **Máx ~30 dispositivos:** Limitado por RAM y tiempo de polling
- **Radio 2.4GHz:** Interferencia con WiFi en mismo canal
- **Sin encriptación:** Protocolo radio en texto plano
- **MicroPython:** Sin JSON parsing nativo, parser manual requerido
- **Display 5×5:** Solo 4 opciones visualizables (A/B/C/D)

---

## Solución de Problemas

### Estudiante no registra

1. Verificar radio habilitada: `radio.on()`
2. Mismo canal radio: `radio.config(channel=7)`
3. Revisar logs: display muestra "?" hasta ACK

### Concentrador no recibe comandos USB

1. Puerto correcto: `ls /dev/ttyACM*` (Linux) o Device Manager (Windows)
2. Baudrate: 115200 default
3. Revisar parser: buscar keywords, no formato JSON exacto

### Proxy no conecta Socket.IO

1. URL ClassQuiz correcta
2. PIN válido y juego activo
3. Redis funcional en ClassQuiz backend

---

## Créditos y Licencia

**Autor del proyecto:** Leandro Batlle (Colegio Nacional de Buenos Aires)  
**Framework base:** microbitML (Enseñanza ML con micro:bits)  
**Integración ClassQuiz:** Desarrollo contractual CDIA/Fundación Sadosky  

**Licencia:** Por definir

---

## Soporte

Para reportar bugs o solicitar features, contactar al equipo de desarrollo del proyecto microbitML/ClassQuiz.

**Documentación adicional:**
- `informe_errores_microbit_uart.md` - Guía de debugging USB/UART
- `guia_documentacion_microbitml.md` - Estándares de código
- `MICROBIT_INCOMPATIBILIDADES.md` - Limitaciones MicroPython