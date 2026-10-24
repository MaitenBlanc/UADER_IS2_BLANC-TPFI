"""Módulo cliente subscrito al patrón Observer del servidor.

Implementa la clase ObserverClient que se suscribe al servidor
SingletonProxyObserverTPFI y recibe notificaciones en tiempo real
ante cada cambio en la tabla CorporateData.
"""

import argparse
import json
import logging
import socket
import time
import uuid


class ObserverClient:
    """Cliente TCP observador que mantiene una suscripción activa al servidor."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        output_file: str | None = None,
        retry_interval: int = 30,
    ) -> None:
        """Inicializa el cliente observador con parámetros de conexión y reintento.

        Args:
            host: Nombre de host o IP del servidor.
            port: Puerto TCP del servidor.
            output_file: Archivo opcional donde guardar las notificaciones recibidas.
            retry_interval: Tiempo en segundos entre reintentos de reconexión.
        """
        self.host = host
        self.port = port
        self.output_file = output_file
        self.retry_interval = retry_interval

    def escuchar_eventos(self) -> None:
        """Conecta al servidor, envía la suscripción y procesa eventos entrantes."""
        conectar_y_escuchar(self.host, self.port, self.output_file)

    def iniciar(self) -> None:
        """Ejecuta el bucle continuo de suscripción y reconexión automática."""
        while True:
            self.escuchar_eventos()
            logging.info(f"Reintentando conexión en {self.retry_interval} segundos...")
            time.sleep(self.retry_interval)


def conectar_y_escuchar(host: str, port: int, output_file: str | None = None) -> None:
    """Establece la conexión TCP de suscripción y procesa los mensajes del servidor.

    Args:
        host: Nombre de host o IP del servidor.
        port: Puerto TCP del servidor.
        output_file: Ruta opcional al archivo JSON de salida.
    """
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        logging.info(f"Intentando conectar a {host}:{port}...")
        cliente.connect((host, port))

        peticion = {"UUID": str(uuid.getnode()), "ACTION": "subscribe"}
        cliente.send(json.dumps(peticion).encode("utf-8"))
        logging.info("Suscripción enviada. Esperando notificaciones...")

        while True:
            datos = cliente.recv(4096).decode("utf-8")
            if not datos:
                logging.warning("Conexión cerrada por el servidor.")
                break

            for linea in datos.strip().split("\n"):
                if linea:
                    respuesta = json.loads(linea)
                    print(">>> EVENTO RECIBIDO:", json.dumps(respuesta, indent=4))

                    if output_file:
                        with open(output_file, "a", encoding="utf-8") as f:
                            json.dump(respuesta, f)
                            f.write("\n")

    except Exception as e:
        logging.error(f"Conexión interrumpida: {e}")
    finally:
        cliente.close()


def main() -> None:
    """Punto de entrada de línea de comandos para ObserverClient."""
    parser = argparse.ArgumentParser(description="Cliente Observer")
    parser.add_argument(
        "-s", "--server", type=str, default="localhost", help="Hostname del servidor"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=8080, help="Puerto del servidor"
    )
    parser.add_argument("-o", "--output", type=str, help="Archivo JSON de salida")
    parser.add_argument(
        "-r",
        "--retry",
        type=int,
        default=30,
        help="Segundos de espera antes de reintentar conexión (default: 30)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Activar trace")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    cliente = ObserverClient(
        host=args.server,
        port=args.port,
        output_file=args.output,
        retry_interval=args.retry,
    )
    cliente.iniciar()


if __name__ == "__main__":
    main()
