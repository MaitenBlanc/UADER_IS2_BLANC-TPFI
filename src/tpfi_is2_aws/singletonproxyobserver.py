"""Módulo del servidor SingletonProxyObserver para el Trabajo Práctico Final IS2.

Implementa un servidor TCP que gestiona el acceso a AWS DynamoDB utilizando
los patrones Singleton (para CorporateData y CorporateLog), Proxy y Observer,
incluyendo un registro de pista de auditoría con datos de CPU.
"""

import argparse
import json
import logging
import platform
import socket
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3  # type: ignore[import-untyped]

CORPORATE_DATA_FIELDS: tuple[str, ...] = (
    "cp",
    "CUIT",
    "domicilio",
    "idreq",
    "idSeq",
    "localidad",
    "provincia",
    "sede",
    "seqID",
    "telefono",
    "web",
)


# PATRÓN SINGLETON - ACCESO FÍSICO A TABLAS DYNAMODB
class CorporateDataSingleton:
    """Singleton para el acceso físico único y thread-safe a la tabla CorporateData."""

    _instancia: "CorporateDataSingleton | None" = None
    _lock: threading.Lock = threading.Lock()
    _inicializado: bool

    def __new__(cls, *args: Any, **kwargs: Any) -> "CorporateDataSingleton":
        """Garantiza que exista una única instancia de CorporateDataSingleton."""
        if cls._instancia is None:
            with cls._lock:
                if cls._instancia is None:
                    cls._instancia = super().__new__(cls)
        return cls._instancia

    def __init__(self) -> None:
        """Inicializa la conexión a la tabla CorporateData en DynamoDB solo una vez."""
        if not hasattr(self, "_inicializado"):
            logging.info("Inicializando Singleton para tabla CorporateData...")
            self.dynamodb: Any = boto3.resource("dynamodb")
            self.table_data: Any = self.dynamodb.Table("CorporateData")
            self._inicializado = True

    def get_record(self, record_id: str) -> dict[str, Any]:
        """Recupera un registro de CorporateData por su identificador.

        Args:
            record_id: Identificador del registro solicitado.

        Returns:
            Diccionario con los datos del tuple o diccionario vacío si no existe.
        """
        response = self.table_data.get_item(Key={"id": record_id})
        item: dict[str, Any] = response.get("Item", {})
        return item

    def list_records(self) -> list[dict[str, Any]]:
        """Recupera todos los registros almacenados en la tabla CorporateData.

        Returns:
            Lista de diccionarios con todos los tuples de CorporateData.
        """
        response = self.table_data.scan()
        items: list[dict[str, Any]] = response.get("Items", [])
        return items

    def set_record(self, data: dict[str, Any]) -> dict[str, Any]:
        """Crea o actualiza un registro en la tabla CorporateData.

        Si el registro ya existe, conserva los campos no informados.
        Si no existe, inicializa en blanco los campos de CorporateData no informados.

        Args:
            data: Diccionario con el identificador 'id' y los campos a establecer.

        Returns:
            Diccionario completo que fue persistido en CorporateData.
        """
        record_id = str(data.get("id", ""))
        existente = self.get_record(record_id) if record_id else {}

        if existente:
            registro_final: dict[str, Any] = dict(existente)
            for clave, valor in data.items():
                if valor is not None:
                    registro_final[clave] = valor
        else:
            registro_final = {"id": record_id}
            for campo in CORPORATE_DATA_FIELDS:
                registro_final[campo] = ""
            for clave, valor in data.items():
                if valor is not None:
                    registro_final[clave] = valor

        self.table_data.put_item(Item=registro_final)
        return registro_final


class CorporateLogSingleton:
    """Singleton para el acceso físico único y thread-safe a la tabla CorporateLog."""

    _instancia: "CorporateLogSingleton | None" = None
    _lock: threading.Lock = threading.Lock()
    _inicializado: bool

    def __new__(cls, *args: Any, **kwargs: Any) -> "CorporateLogSingleton":
        """Garantiza que exista una única instancia de CorporateLogSingleton."""
        if cls._instancia is None:
            with cls._lock:
                if cls._instancia is None:
                    cls._instancia = super().__new__(cls)
        return cls._instancia

    def __init__(self) -> None:
        """Inicializa la conexión a la tabla CorporateLog en DynamoDB solo una vez."""
        if not hasattr(self, "_inicializado"):
            logging.info("Inicializando Singleton para tabla CorporateLog...")
            self.dynamodb: Any = boto3.resource("dynamodb")
            self.table_log: Any = self.dynamodb.Table("CorporateLog")
            self._inicializado = True

    @staticmethod
    def obtener_datos_cpu() -> dict[str, str]:
        """Obtiene los metadatos de CPU y sistema operativo usando platform y uuid.

        Returns:
            Diccionario con UUID de CPU y metadatos de plataforma.
        """
        return {
            "CPU_UUID": str(uuid.getnode()),
            "sistema": platform.system(),
            "nodo": platform.node(),
            "arquitectura": platform.machine(),
            "procesador": platform.processor() or platform.machine(),
        }

    def log_action(self, log_data: dict[str, Any]) -> dict[str, Any]:
        """Registra una entrada de auditoría en la tabla CorporateLog.

        Args:
            log_data: Datos de la acción a registrar.

        Returns:
            Diccionario completo registrado en CorporateLog.
        """
        entrada = dict(log_data)
        datos_cpu = self.obtener_datos_cpu()
        for clave, valor in datos_cpu.items():
            entrada.setdefault(clave, valor)
        self.table_log.put_item(Item=entrada)
        return entrada


class DatabaseSingleton:
    """Fachada Singleton compatible que agrupa CorporateDataSingleton y CorporateLogSingleton."""

    _instancia: "DatabaseSingleton | None" = None
    _lock: threading.Lock = threading.Lock()
    _inicializado: bool

    def __new__(cls, *args: Any, **kwargs: Any) -> "DatabaseSingleton":
        """Garantiza que exista una única instancia de DatabaseSingleton."""
        if cls._instancia is None:
            with cls._lock:
                if cls._instancia is None:
                    cls._instancia = super().__new__(cls)
        return cls._instancia

    def __init__(self) -> None:
        """Inicializa las referencias a los Singletons de datos y auditoría."""
        if not hasattr(self, "_inicializado"):
            CorporateDataSingleton._instancia = None
            CorporateLogSingleton._instancia = None
            self.data_singleton = CorporateDataSingleton()
            self.log_singleton = CorporateLogSingleton()
            self.table_data = self.data_singleton.table_data
            self.table_log = self.log_singleton.table_log
            self._inicializado = True

    def get_record(self, record_id: str) -> dict[str, Any]:
        """Delega la obtención de un registro a CorporateDataSingleton."""
        return self.data_singleton.get_record(record_id)

    def list_records(self) -> list[dict[str, Any]]:
        """Delega el listado de registros a CorporateDataSingleton."""
        return self.data_singleton.list_records()

    def set_record(self, data: dict[str, Any]) -> dict[str, Any]:
        """Delega la actualización o creación de un registro a CorporateDataSingleton."""
        return self.data_singleton.set_record(data)

    def log_action(self, log_data: dict[str, Any]) -> dict[str, Any]:
        """Delega el registro de auditoría a CorporateLogSingleton."""
        return self.log_singleton.log_action(log_data)


# PATRÓN OBSERVER
class ObserverManager:
    """Gestiona las subscripciones de clientes y notifica cambios en CorporateData."""

    def __init__(self) -> None:
        """Inicializa la lista de sockets observadores y su cerrojo de concurrencia."""
        self._observers: list[socket.socket] = []
        self._lock = threading.Lock()

    def attach(self, observer_socket: socket.socket) -> None:
        """Agrega un socket de cliente a la lista de observadores activos.

        Args:
            observer_socket: Socket TCP del cliente suscriptor.
        """
        with self._lock:
            if observer_socket not in self._observers:
                self._observers.append(observer_socket)
                logging.info(
                    f"Nuevo suscriptor agregado. Total: {len(self._observers)}"
                )

    def detach(self, observer_socket: socket.socket) -> None:
        """Remueve un socket de la lista de observadores activos.

        Args:
            observer_socket: Socket TCP a remover.
        """
        with self._lock:
            try:
                self._observers.remove(observer_socket)
                logging.info(f"Suscriptor removido. Total: {len(self._observers)}")
            except ValueError:
                pass

    def notify(self, data: dict[str, Any]) -> None:
        """Notifica a todos los observadores registrados sobre un cambio en CorporateData.

        Args:
            data: Diccionario con los datos actualizados a enviar como JSON.
        """
        logging.info("Notificando a suscriptores sobre actualización...")
        mensaje = json.dumps(data, default=str) + "\n"
        with self._lock:
            for obs in list(self._observers):
                try:
                    obs.send(mensaje.encode("utf-8"))
                except Exception as e:
                    logging.warning(f"Error notificando a un socket, se remueve: {e}")
                    try:
                        self._observers.remove(obs)
                    except ValueError:
                        pass


# PATRÓN PROXY
class CorporateDataProxy:
    """Proxy que intercepta las peticiones, registra auditoría y gestiona el acceso a DB."""

    def __init__(self, observer_manager: ObserverManager) -> None:
        """Inicializa el Proxy con los Singletons de datos, auditoría y el Observer.

        Args:
            observer_manager: Instancia de ObserverManager para gestionar suscripciones.
        """
        self.db = DatabaseSingleton()
        self.data_db = self.db.data_singleton
        self.log_db = self.db.log_singleton
        self.observer = observer_manager

    @staticmethod
    def _extraer_datos_set(peticion: dict[str, Any], record_id: str) -> dict[str, Any]:
        """Extrae los campos del tuple CorporateData desde la petición 'set'."""
        datos_sub = peticion.get("data", {})
        resultado: dict[str, Any] = (
            dict(datos_sub) if isinstance(datos_sub, dict) else {}
        )

        for campo in CORPORATE_DATA_FIELDS:
            if campo in peticion and campo not in resultado:
                resultado[campo] = peticion[campo]

        if "id" in peticion and "id" not in resultado:
            resultado["id"] = peticion["id"]
        if record_id and "id" not in resultado:
            resultado["id"] = record_id

        return resultado

    def procesar_peticion(
        self, peticion: dict[str, Any], client_socket: socket.socket
    ) -> dict[str, Any]:
        """Procesa un requerimiento JSON registrando auditoría y ejecutando la acción.

        Args:
            peticion: Diccionario JSON enviado por el cliente.
            client_socket: Socket TCP de la conexión entrante.

        Returns:
            Diccionario con la respuesta formateada o indicación de error.
        """
        accion = peticion.get("ACTION")
        cliente_uuid = str(peticion.get("UUID") or uuid.getnode())
        sesion_id = str(uuid.uuid4())
        record_id = str(peticion.get("ID") or peticion.get("id") or "")
        timestamp = datetime.now(UTC).isoformat()

        # Registro de pista de auditoría en CorporateLog
        log_entry: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "UUID": cliente_uuid,
            "sesion": sesion_id,
            "accion": str(accion) if accion else "desconocida",
            "timestamp": timestamp,
        }
        if record_id:
            log_entry["ID_solicitado"] = record_id

        logging.info(
            f"[Proxy] Registrando auditoría: Acción '{accion}' de {cliente_uuid}"
        )
        self.db.log_action(log_entry)

        if not accion or accion not in {"subscribe", "get", "list", "set"}:
            return {"Error": "Acción no reconocida"}

        if accion == "subscribe":
            self.observer.attach(client_socket)
            return {"status": "OK", "message": "Suscrito exitosamente."}

        if accion == "get":
            if not record_id:
                return {"Error": "Falta indicar ID para la acción get"}
            data = self.db.get_record(record_id)
            return {"get": data} if data else {"Error": "Registro no encontrado"}

        if accion == "list":
            datos_lista = self.db.list_records()
            return {"list": datos_lista}

        # Acción "set"
        datos_set = self._extraer_datos_set(peticion, record_id)
        if not datos_set.get("id"):
            return {"Error": "Falta indicar ID para la acción set"}

        registro_actualizado = self.db.set_record(datos_set)
        if registro_actualizado is None:
            registro_actualizado = datos_set

        self.observer.notify({"change": registro_actualizado})
        return {"set": registro_actualizado}


# SERVIDOR TCP
def client_handler(
    conn: socket.socket, addr: tuple[str, int], proxy: CorporateDataProxy
) -> None:
    """Maneja la conexión de un cliente TCP en un hilo de ejecución independiente.

    Args:
        conn: Socket de la conexión aceptada.
        addr: Tupla (host, puerto) del cliente remoto.
        proxy: Instancia de CorporateDataProxy para procesar la petición.
    """
    logging.info(f"Conexión aceptada de {addr}")
    accion: str | None = None
    try:
        data_raw = conn.recv(4096).decode("utf-8")
        if not data_raw:
            conn.close()
            return

        peticion = json.loads(data_raw)
        accion = peticion.get("ACTION")

        respuesta = proxy.procesar_peticion(peticion, conn)

        conn.send((json.dumps(respuesta, default=str) + "\n").encode("utf-8"))

        if accion != "subscribe" or "Error" in respuesta:
            conn.close()
            logging.info(f"Conexión con {addr} cerrada.")

    except Exception as e:
        logging.error(f"Error manejando cliente {addr}: {e}")
        conn.close()


class SingletonProxyObserverServer:
    """Servidor TCP orientado a objetos que integra Proxy, Singleton y Observer."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:  # nosec B104
        """Inicializa el servidor en el host y puerto indicados.

        Args:
            host: Dirección IP de escucha.
            port: Puerto TCP de escucha.
        """
        self.host = host
        self.port = port
        self.observer_manager = ObserverManager()
        self.proxy = CorporateDataProxy(self.observer_manager)

    def serve_forever(self) -> None:
        """Inicia el bucle principal de aceptación de conexiones TCP."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen(5)

        print(f"Servidor iniciado en puerto {self.port}...")

        try:
            while True:
                conn, addr = server.accept()
                hilo = threading.Thread(
                    target=client_handler, args=(conn, addr, self.proxy)
                )
                hilo.daemon = True
                hilo.start()
        except KeyboardInterrupt:
            print("\nServidor apagado manualmente.")
        finally:
            server.close()


def main() -> None:
    """Punto de entrada de línea de comandos para el servidor SingletonProxyObserver."""
    parser = argparse.ArgumentParser(description="Servidor SingletonProxyObserver")
    parser.add_argument(
        "-p", "--port", type=int, default=8080, help="Puerto de escucha TCP"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Activar logs detallados"
    )
    args = parser.parse_args()

    nivel_log = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=nivel_log, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    servidor = SingletonProxyObserverServer(port=args.port)
    servidor.serve_forever()


if __name__ == "__main__":
    main()
