# microbitml.py - Protocolo simple de comunicacion radio para micro:bit

__all__ = ["RadioProtocol"]

class RadioProtocol:
    """
    Protocolo basico para comunicacion entre microbits
    Sin dependencias externas para evitar imports circulares
    """
    
    def __init__(self, device_id=None):
        """
        Inicializa el protocolo
        device_id: ID opcional del dispositivo (para estudiantes)
        """
        self.device_id = device_id
        self.registered = False
    
    # === COMANDOS BROADCAST ===
    
    @staticmethod
    def crear_report():
        """Crea mensaje REPORT para descubrimiento"""
        return "REPORT"
    
    @staticmethod
    def crear_question(question_data):
        """Crea mensaje QUESTION con datos de pregunta"""
        return f"QUESTION:{question_data}"
    
    @staticmethod
    def crear_ping(device_id):
        """Crea mensaje PING para dispositivo especifico"""
        return f"PING:{device_id}"
    
    # === RESPUESTAS INDIVIDUALES ===
    
    def crear_id_response(self):
        """Crea respuesta ID con device_id propio"""
        if not self.device_id:
            raise ValueError("device_id no configurado")
        return f"ID:{self.device_id}"
    
    @staticmethod
    def crear_ack(device_id):
        """Crea ACK para device_id especifico"""
        return f"ACK:{device_id}"
    
    @staticmethod
    def crear_pong(device_id):
        """Crea respuesta PONG"""
        return f"PONG:{device_id}"
    
    def crear_answer(self, opciones):
        """
        Crea respuesta con opciones guardadas
        opciones: lista de strings, ej: ['A', 'B', 'C']
        """
        if not self.device_id:
            raise ValueError("device_id no configurado")
        opciones_str = ','.join(opciones)
        return f"ANSWER:{self.device_id}:{opciones_str}"
    
    # === DECODIFICACION ===
    
    @staticmethod
    def decodificar(mensaje):
        """
        Decodifica mensaje recibido
        Retorna: (tipo, datos)
        Tipos: REPORT, QUESTION, PING, ID, ACK, PONG, ANSWER
        """
        if not mensaje:
            return (None, None)
        
        # Mensajes sin payload
        if mensaje == "REPORT":
            return ("REPORT", None)
        
        # Mensajes con payload
        if ':' in mensaje:
            partes = mensaje.split(':', 1)
            tipo = partes[0]
            datos = partes[1] if len(partes) > 1 else None
            return (tipo, datos)
        
        return (None, None)
    
    @staticmethod
    def extraer_device_id(mensaje):
        """
        Extrae device_id de mensajes tipo ID:xxx, ACK:xxx, PING:xxx
        Retorna: device_id o None
        """
        tipo, datos = RadioProtocol.decodificar(mensaje)
        if tipo in ["ID", "ACK", "PING", "PONG"]:
            return datos
        return None
    
    @staticmethod
    def extraer_answer(mensaje):
        """
        Extrae respuesta de mensaje ANSWER:device_id:A,B,C
        Retorna: (device_id, [opciones]) o (None, None)
        """
        tipo, datos = RadioProtocol.decodificar(mensaje)
        if tipo == "ANSWER" and datos:
            partes = datos.split(':', 1)
            if len(partes) == 2:
                device_id = partes[0]
                opciones = partes[1].split(',')
                return (device_id, opciones)
        return (None, None)
    
    # === VALIDACION ===
    
    def validar_ack(self, mensaje):
        """Verifica si el ACK es para este dispositivo"""
        device_id = self.extraer_device_id(mensaje)
        return device_id == self.device_id
    
    def validar_ping(self, mensaje):
        """Verifica si el PING es para este dispositivo"""
        device_id = self.extraer_device_id(mensaje)
        return device_id == self.device_id
    
    # === ESTADO ===
    
    def marcar_registrado(self):
        """Marca dispositivo como registrado"""
        self.registered = True
    
    def resetear_registro(self):
        """Resetea estado de registro"""
        self.registered = False
    
    def esta_registrado(self):
        """Retorna si el dispositivo esta registrado"""
        return self.registered


# === FUNCIONES DE UTILIDAD ===

def test_protocol():
    """Test basico del protocolo"""
    print("=== Test RadioProtocol ===")
    
    # Crear protocolo
    proto = RadioProtocol(device_id="aabbccdd")
    
    # Test mensajes broadcast
    assert proto.crear_report() == "REPORT"
    assert proto.crear_ping("1234") == "PING:1234"
    
    # Test respuestas
    assert proto.crear_id_response() == "ID:aabbccdd"
    assert proto.crear_ack("1234") == "ACK:1234"
    assert proto.crear_answer(['A', 'C']) == "ANSWER:aabbccdd:A,C"
    
    # Test decodificacion
    assert proto.decodificar("REPORT") == ("REPORT", None)
    assert proto.decodificar("ID:1234") == ("ID", "1234")
    assert proto.decodificar("ACK:aabbccdd") == ("ACK", "aabbccdd")
    
    # Test extraccion
    assert proto.extraer_device_id("ID:1234") == "1234"
    assert proto.extraer_answer("ANSWER:dev1:A,B") == ("dev1", ["A", "B"])
    
    # Test validacion
    assert proto.validar_ack("ACK:aabbccdd") == True
    assert proto.validar_ack("ACK:1234") == False
    
    print("Todos los tests pasaron!")


if __name__ == "__main__":
    test_protocol()