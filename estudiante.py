# estudiante.py - Micro:bit Estudiante con confirmacion visual

from microbit import *
import machine
import radio
from random import randint

# === CONFIGURACION RADIO ===
radio.config(channel=7, power=6, length=64, queue=10)
radio.on()

# === ID UNICO ===
mi_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])

# === ESTADOS ===
IDLE = 0
VOTING = 1
ANSWERED = 2

estado_actual = IDLE
ack_recibido = False

# === PARAMETROS PREGUNTA ===
tipo_pregunta = None
num_opciones = 4
opciones_validas = ['A', 'B', 'C', 'D']

# === RESPUESTAS GUARDADAS ===
letra_actual = 'A'
respuesta_unica = None
respuestas_multiple = set()

# === ARCHIVO PERSISTENCIA ===
CONFIG_FILE = 'voto.cfg'


def cargar_voto():
    """Carga respuestas guardadas desde archivo"""
    global respuesta_unica, respuestas_multiple
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = eval(f.read())
        respuesta_unica = config.get('respuesta_unica')
        respuestas_multiple = set(config.get('respuestas_multiple', []))
    except:
        respuesta_unica = None
        respuestas_multiple = set()


def guardar_voto():
    """Guarda respuestas actuales en archivo"""
    try:
        config = {
            'tipo': tipo_pregunta,
            'respuesta_unica': respuesta_unica,
            'respuestas_multiple': list(respuestas_multiple)
        }
        with open(CONFIG_FILE, 'w') as f:
            f.write(repr(config))
    except Exception as e:
        print("Error guardando voto:", e)


def resetear_respuestas():
    """Limpia todas las respuestas guardadas"""
    global respuesta_unica, respuestas_multiple, letra_actual
    respuesta_unica = None
    respuestas_multiple = set()
    letra_actual = 'A'
    try:
        import os
        os.remove(CONFIG_FILE)
    except:
        pass


def actualizar_display():
    """Actualiza display segun estado"""
    if estado_actual == IDLE:
        if ack_recibido:
            display.show(Image.YES)
        else:
            display.show(Image.NO)
    
    elif estado_actual == VOTING:
        # Mostrar letra actual
        display.show(letra_actual)
        
        # LED indicador si hay respuesta guardada
        if tipo_pregunta == "unica" and respuesta_unica:
            display.set_pixel(4, 0, 9)
        elif tipo_pregunta == "multiple" and len(respuestas_multiple) > 0:
            display.set_pixel(4, 0, 9)
    
    elif estado_actual == ANSWERED:
        display.show(Image.HAPPY)


def procesar_mensaje_radio(msg):
    """Procesa mensajes recibidos por radio"""
    global estado_actual, ack_recibido, tipo_pregunta, num_opciones, letra_actual
    
    if msg == "REPORT":
        if not ack_recibido:
            delay_ms = randint(0, 2000)
            sleep(delay_ms)
            radio.send("ID:" + mi_id)
            display.show(Image.ARROW_E)
            sleep(200)
            actualizar_display()
    
    elif msg.startswith("ACK:"):
        ack_id = msg[4:]
        if ack_id == mi_id:
            ack_recibido = True
            display.show(Image.HAPPY)
            sleep(1000)
            actualizar_display()
    
    elif msg.startswith("QPARAMS:"):
        partes = msg.split(':')
        if len(partes) == 3:
            tipo_pregunta = partes[1]
            num_opciones = int(partes[2])
            
            resetear_respuestas()
            estado_actual = VOTING
            
            # === CONFIRMACION VISUAL DE PREGUNTA NUEVA ===
            # Animacion breve para indicar llegada de pregunta
            display.show(Image.ARROW_S)
            sleep(300)
            display.show(Image.YES)
            sleep(600)
            display.show(Image.ARROW_S)
            sleep(300)
            
            # Mostrar tipo de pregunta
            if tipo_pregunta == "unica":
                display.show(Image.HEART_SMALL)
            else:
                display.show(Image.SQUARE)
            sleep(1000)
            
            # Mostrar primera opcion
            actualizar_display()
    
    elif msg.startswith("POLL:"):
        poll_id = msg[5:]
        if poll_id == mi_id:
            enviar_respuesta()
            estado_actual = ANSWERED
            actualizar_display()
    
    elif msg.startswith("PING:"):
        ping_id = msg[5:]
        if ping_id == mi_id:
            radio.send("PONG:" + mi_id)


def enviar_respuesta():
    """Envia respuesta guardada al concentrador"""
    respuesta_str = ""
    
    if tipo_pregunta == "unica":
        if respuesta_unica:
            respuesta_str = respuesta_unica
    else:
        if respuestas_multiple:
            respuesta_str = ','.join(sorted(respuestas_multiple))
    
    mensaje = "ANSWER:{}:{}".format(mi_id, respuesta_str)
    radio.send(mensaje)


def manejar_boton_a():
    """Boton A: cicla entre opciones disponibles"""
    global letra_actual
    
    if estado_actual == VOTING:
        opciones = opciones_validas[:num_opciones]
        idx_actual = opciones.index(letra_actual)
        idx_siguiente = (idx_actual + 1) % len(opciones)
        letra_actual = opciones[idx_siguiente]
        actualizar_display()


def manejar_boton_b():
    """Boton B: guarda/desguarda respuesta"""
    global respuesta_unica
    
    if estado_actual == VOTING:
        if tipo_pregunta == "unica":
            respuesta_unica = letra_actual
            display.set_pixel(4, 0, 9)
            sleep(200)
            actualizar_display()
        
        else:
            # Toggle multiple
            if letra_actual in respuestas_multiple:
                respuestas_multiple.remove(letra_actual)
            else:
                respuestas_multiple.add(letra_actual)
            
            # Flash confirmacion
            display.set_pixel(4, 0, 9)
            sleep(150)
            actualizar_display()
        
        guardar_voto()


# === INICIO ===
display.scroll(mi_id[-4:], delay=60)
sleep(500)
cargar_voto()
actualizar_display()

# === LOOP PRINCIPAL ===
while True:
    # Botones
    if button_a.was_pressed():
        manejar_boton_a()
    
    if button_b.was_pressed():
        manejar_boton_b()
    
    # Radio
    mensaje = radio.receive()
    if mensaje:
        procesar_mensaje_radio(mensaje)
    
    sleep(50)