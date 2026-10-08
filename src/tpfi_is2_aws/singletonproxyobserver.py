"""
Módulo del servidor SingletonProxyObserver para el Trabajo Práctico Final IS2.

Implementa un servidor TCP que gestiona el acceso a AWS DynamoDB utilizando
los patrones Singleton, Proxy y Observer, incluyendo un registro de auditoría.
"""

import socket
import threading
import json
import argparse
import logging
import uuid
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
import boto3

# PATRÓN SINGLETON

class DatabaseSingleton:
    """
    Singleton para acceder a AWS DynamoDB de forma única y thread-safe.
    """
    _instancia = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instancia is None:
            with cls._lock:
                if cls._instancia is None:
                    cls._instancia = super().__new__(cls)
        return cls._instancia

    def __init__(self):
        """Inicializa la conexión a DynamoDB solo una vez."""
        if not hasattr(self, "_inicializado"):
            logging.info("Inicializando conexión a AWS DynamoDB (Singleton)...")
            self.dynamodb = boto3.resource('dynamodb')
            self.table_data = self.dynamodb.Table('CorporateData')
            self.table_log = self.dynamodb.Table('CorporateLog')
            self._inicializado = True

    def get_record(self, record_id: str) -> Dict[str, Any]:
        response = self.table_data.get_item(Key={'id': record_id})
        return response.get('Item', {})

    def list_records(self) -> List[Dict[str, Any]]:
        response = self.table_data.scan()
        return response.get('Items', [])

    def set_record(self, data: Dict[str, Any]) -> None:
        self.table_data.put_item(Item=data)

    def log_action(self, log_data: Dict[str, Any]) -> None:
        self.table_log.put_item(Item=log_data)


# PATRÓN OBSERVER 

class ObserverManager:
    """
    Gestiona las subscripciones y notifica a los clientes de cambios.
    """
    def __init__(self):
        self._observers: List[socket.socket] = []
        self._lock = threading.Lock()

    def attach(self, observer_socket: socket.socket) -> None:
        """Agrega un socket a la lista de observadores."""
        with self._lock:
            if observer_socket not in self._observers:
                self._observers.append(observer_socket)
                logging.info(f"Nuevo suscriptor agregado. Total: {len(self._observers)}")

    def detach(self, observer_socket: socket.socket) -> None:
        """Remueve un socket de la lista."""
        with self._lock:
            try:
                self._observers.remove(observer_socket)
                logging.info(f"Suscriptor removido. Total: {len(self._observers)}")
            except ValueError:
                pass

    def notify(self, data: Dict[str, Any]) -> None:
        """Notifica a todos los observadores registrados sobre un cambio."""
        logging.info("Notificando a suscriptores sobre actualización...")
        mensaje = json.dumps(data, default=str) + "\n"
        with self._lock:
            for obs in list(self._observers):
                try:
                    obs.send(mensaje.encode('utf-8'))
                except Exception as e:
                    logging.warning(f"Error notificando a un socket, se remueve: {e}")
                    self.detach(obs)


# PATRÓN PROXY 
class CorporateDataProxy:
    """
    Proxy que intercepta la petición, genera auditoría y accede a la base.
    """
    def __init__(self, observer_manager: ObserverManager):
        self.db = DatabaseSingleton()
        self.observer = observer_manager

    def procesar_peticion(self, peticion: Dict[str, Any], client_socket: socket.socket) -> Dict[str, Any]:
        accion = peticion.get("ACTION")
        cliente_uuid = peticion.get("UUID", str(uuid.getnode()))
        sesion_id = str(uuid.uuid4())
        record_id = peticion.get("ID", "")
        timestamp = datetime.now(timezone.utc).isoformat()

        # Registro de Auditoría
        log_entry = {
            "UUID": cliente_uuid,
            "sesion": sesion_id,
            "accion": accion,
            "timestamp": timestamp
        }
        if record_id:
            log_entry["ID_solicitado"] = record_id
            
        logging.info(f"[Proxy] Registrando auditoría: Acción '{accion}' de {cliente_uuid}")
        self.db.log_action(log_entry)

        # Enrutamiento de la acción
        if accion == "subscribe":
            self.observer.attach(client_socket)
            return {"status": "OK", "message": "Suscrito exitosamente."}

        elif accion == "get":
            data = self.db.get_record(record_id)
            return {"get": data} if data else {"Error": "Registro no encontrado"}

        elif accion == "list":
            data = self.db.list_records()
            return {"list": data}

        elif accion == "set":
            data = peticion.get("data", {})
            if "id" not in data and record_id:
                data["id"] = record_id
            self.db.set_record(data)
            # Notificar el cambio a los suscriptores
            self.observer.notify({"change": data})
            return {"set": data}

        return {"Error": "Acción no reconocida"}


# SERVIDOR TCP
def client_handler(conn: socket.socket, addr: tuple, proxy: CorporateDataProxy):
    """Maneja la conexión de un cliente en un hilo independiente."""
    logging.info(f"Conexión aceptada de {addr}")
    try:
        data_raw = conn.recv(4096).decode('utf-8')
        if not data_raw:
            return

        peticion = json.loads(data_raw)
        accion = peticion.get("ACTION")
        
        respuesta = proxy.procesar_peticion(peticion, conn)
        
        # Envío de la respuesta inicial
        conn.send((json.dumps(respuesta, default=str) + "\n").encode('utf-8'))
        
        # Si no es un suscriptor, se cierra la conexión luego de responder
        if accion != "subscribe":
            conn.close()
            logging.info(f"Conexión con {addr} cerrada.")
            
    except Exception as e:
        logging.error(f"Error manejando cliente {addr}: {e}")
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Servidor SingletonProxyObserver')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Puerto de escucha TCP')
    parser.add_argument('-v', '--verbose', action='store_true', help='Activar logs detallados')
    args = parser.parse_args()

    nivel_log = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=nivel_log, format='%(asctime)s - %(levelname)s - %(message)s')

    observer_manager = ObserverManager()
    proxy = CorporateDataProxy(observer_manager)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', args.port))
    server.listen(5)
    
    print(f"Servidor iniciado en puerto {args.port}...")
    
    try:
        while True:
            conn, addr = server.accept()
            # Creación de un hilo por cada cliente conectado
            hilo = threading.Thread(target=client_handler, args=(conn, addr, proxy))
            hilo.daemon = True
            hilo.start()
    except KeyboardInterrupt:
        print("\nServidor apagado manualmente.")
    finally:
        server.close()

if __name__ == "__main__":
    main()