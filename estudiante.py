# estudiante.py - Micro:bit Estudiante (DEBUG MODE)

from microbit import *
import radio
import machine
from random import randint

# === CONFIGURACION RADIO ===
radio.config(channel=7, power=6, length=64, queue=10)
radio.on()

# === ID UNICO ===
device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])

# === VARIABLES DE ESTADO ===
registrado = False
tipo_pregunta = "unica"
num_opciones = 4
opcion_actual = 0
opcion_confirmada = None
CONFIG_FILE = 'vote.cfg'

LETRAS = ['A', 'B', 'C', 'D']


def log(msg):
    """Log por puerto serie"""
    print("[{}ms] {}".format(running_time(), msg))


def enviar_mensaje(msg):
    """Envia mensaje por radio"""
    radio.send(msg)
    log("TX_RADIO: '{}'".format(msg))


def mostrar_opcion_actual():
    """Muestra la opcion actual en el display"""
    if opcion_actual < num_opciones:
        display.show(LETRAS[opcion_actual])
        log("Display: {}".format(LETRAS[opcion_actual]))
    else:
        display.show('?')
        log("Display: ?")


def mostrar_sin_voto():
    """Muestra X indicando que no hay voto"""
    log("Mostrando: SIN_VOTO")
    display.show(Image.NO)
    sleep(800)
    display.clear()


def mostrar_confirmado():
    """Muestra checkmark indicando voto confirmado"""
    log("Mostrando: VOTO_CONFIRMADO")
    display.show(Image.YES)
    sleep(1000)
    display.clear()


def cargar_voto_guardado():
    """Carga voto previo desde archivo"""
    global opcion_confirmada, opcion_actual
    try:
        with open(CONFIG_FILE, 'r') as f:
            data = eval(f.read())
            opcion_confirmada = data.get('confirmada', None)
            if opcion_confirmada:
                try:
                    opcion_actual = LETRAS.index(opcion_confirmada)
                except:
                    opcion_actual = 0
                log("Voto_cargado: {}".format(opcion_confirmada))
                mostrar_confirmado()
                return True
    except:
        log("Sin_voto_previo_guardado")
    return False


def guardar_voto():
    """Guarda voto confirmado en archivo"""
    try:
        data = {'confirmada': opcion_confirmada}
        with open(CONFIG_FILE, 'w') as f:
            f.write(repr(data))
        log("Voto_guardado_OK: {}".format(opcion_confirmada))
    except Exception as e:
        log("Error_guardando: {}".format(e))


def resetear_voto():
    """Limpia voto para nueva pregunta"""
    global opcion_confirmada, opcion_actual
    log("=== RESET_VOTO ===")
    opcion_confirmada = None
    opcion_actual = 0
    log("Voto_reseteado")
    mostrar_sin_voto()


def mover_derecha():
    """Mueve seleccion a la derecha (circular)"""
    global opcion_actual
    opcion_actual = (opcion_actual + 1) % num_opciones
    log("Navegacion_DERECHA: {}".format(LETRAS[opcion_actual]))
    mostrar_opcion_actual()
    sleep(300)


def mover_izquierda():
    """Mueve seleccion a la izquierda (circular)"""
    global opcion_actual
    opcion_actual = (opcion_actual - 1) % num_opciones
    log("Navegacion_IZQUIERDA: {}".format(LETRAS[opcion_actual]))
    mostrar_opcion_actual()
    sleep(300)


def confirmar_voto():
    """Confirma la opcion actual como voto final"""
    global opcion_confirmada
    
    log("=== CONFIRMAR_VOTO ===")
    
    if opcion_actual >= num_opciones:
        log("ERROR: indice_fuera_de_rango")
        display.show(Image.CONFUSED)
        sleep(500)
        display.clear()
        return
    
    opcion_confirmada = LETRAS[opcion_actual]
    guardar_voto()
    log("VOTO_CONFIRMADO: {}".format(opcion_confirmada))
    mostrar_confirmado()


def procesar_mensaje(msg):
    """Procesa mensajes radio recibidos"""
    global registrado, tipo_pregunta, num_opciones
    
    log("RX_RADIO: '{}'".format(msg))
    
    if msg == "REPORT":
        log("CMD: REPORT_detectado")
        if not registrado:
            delay = randint(100, 2000)
            log("Delay_aleatorio: {}ms".format(delay))
            sleep(delay)
            enviar_mensaje("ID:{}".format(device_id))
        else:
            log("Ya_registrado,_ignorando_REPORT")
        return
    
    if msg.startswith("ACK:"):
        id_ack = msg[4:]
        log("CMD: ACK_recibido_para: {}".format(id_ack[:8]))
        if id_ack == device_id:
            registrado = True
            log("ACK_CONFIRMADO! Ahora_registrado")
            display.show(Image.HAPPY)
            sleep(1000)
            display.clear()
        else:
            log("ACK_no_es_para_mi")
        return
    
    if msg.startswith("QPARAMS:"):
        log("=== CMD: QPARAMS_recibido ===")
        try:
            partes = msg.split(':')
            log("Partes: {}".format(len(partes)))
            if len(partes) >= 3:
                tipo_pregunta = partes[1]
                num_opciones = int(partes[2])
                log("Nueva_pregunta: tipo={}, opciones={}".format(tipo_pregunta, num_opciones))
                
                resetear_voto()
                
                if tipo_pregunta == "unica":
                    display.show("1")
                else:
                    display.show("M")
                sleep(800)
                mostrar_sin_voto()
            else:
                log("QPARAMS_formato_invalido")
        except Exception as e:
            log("Error_parseando_QPARAMS: {}".format(e))
        return
    
    if msg.startswith("POLL:"):
        id_poll = msg[5:]
        log("CMD: POLL_recibido_para: {}".format(id_poll[:8]))
        if id_poll == device_id:
            log("POLL_ES_PARA_MI!")
            
            if opcion_confirmada:
                respuesta = "ANSWER:{}:{}".format(device_id, opcion_confirmada)
                log("Enviando_respuesta_con_voto: {}".format(opcion_confirmada))
                enviar_mensaje(respuesta)
                mostrar_confirmado()
            else:
                respuesta = "ANSWER:{}:".format(device_id)
                log("Enviando_respuesta_SIN_voto")
                enviar_mensaje(respuesta)
                mostrar_sin_voto()
        else:
            log("POLL_no_es_para_mi")
        return
    
    if msg.startswith("PING:"):
        id_ping = msg[5:]
        log("CMD: PING_recibido_para: {}".format(id_ping[:8]))
        if id_ping == device_id:
            log("PING_ES_PARA_MI! Enviando_PONG")
            enviar_mensaje("PONG:{}".format(device_id))
        else:
            log("PING_no_es_para_mi")
        return
    
    log("Mensaje_no_reconocido: {}".format(msg))


def mostrar_id_breve():
    """Muestra ultimos 4 caracteres del ID"""
    log("Mostrando_ID_en_display")
    display.scroll(device_id[-4:], delay=60)
    sleep(500)
    display.clear()


# === INICIO ===
log("=" * 40)
log("=== ESTUDIANTE_INICIADO ===")
log("=" * 40)
log("Radio_configurado: channel=7, power=6")
log("Mi_ID: {}".format(device_id))
log("ID_corto: {}".format(device_id[-8:]))
log("Estado_inicial: IDLE, registrado=False")

log("Mostrando_ID_inicial...")
mostrar_id_breve()

log("Intentando_cargar_voto_previo...")
cargar_voto_guardado()

log("=" * 40)
log("=== ENTRANDO_LOOP_PRINCIPAL ===")
log("=" * 40)

# === LOOP PRINCIPAL ===
tiempo_ultimo_boton = 0
DEBOUNCE_MS = 200

while True:
    msg = radio.receive()
    if msg:
        procesar_mensaje(msg)
    
    tiempo_actual = running_time()
    
    # Boton A: Navegar DERECHA
    if button_a.was_pressed() and not button_b.is_pressed():
        if tiempo_actual - tiempo_ultimo_boton > DEBOUNCE_MS:
            tiempo_ultimo_boton = tiempo_actual
            log("=== BTN_A_presionado ===")
            
            if not registrado:
                log("No_registrado, mostrando_ID")
                mostrar_id_breve()
            else:
                mover_derecha()
    
    # Boton B: Navegar IZQUIERDA
    if button_b.was_pressed() and not button_a.is_pressed():
        if tiempo_actual - tiempo_ultimo_boton > DEBOUNCE_MS:
            tiempo_ultimo_boton = tiempo_actual
            log("=== BTN_B_presionado ===")
            
            if not registrado:
                log("No_registrado, mostrando_ID")
                mostrar_id_breve()
            else:
                mover_izquierda()
    
    # A+B JUNTOS: CONFIRMAR
    if button_a.is_pressed() and button_b.is_pressed():
        if tiempo_actual - tiempo_ultimo_boton > DEBOUNCE_MS:
            tiempo_ultimo_boton = tiempo_actual
            log("=== BTN_A+B_presionados ===")
            
            if registrado:
                confirmar_voto()
            else:
                log("No_registrado, ignorando_confirmacion")
            
            while button_a.is_pressed() or button_b.is_pressed():
                sleep(50)
    
    # Logo: Mostrar estado actual
    if pin_logo.is_touched():
        log("=== LOGO_tocado ===")
        if registrado:
            if opcion_confirmada:
                log("Estado: Voto_confirmado={}".format(opcion_confirmada))
                display.show(opcion_confirmada)
                sleep(500)
                mostrar_confirmado()
            else:
                log("Estado: Navegando={}".format(LETRAS[opcion_actual]))
                mostrar_opcion_actual()
                sleep(500)
                mostrar_sin_voto()
        else:
            log("No_registrado, mostrando_ID")
            mostrar_id_breve()
        
        while pin_logo.is_touched():
            sleep(50)
    
    sleep(50)