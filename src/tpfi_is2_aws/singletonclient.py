"""Módulo cliente para enviar requerimientos sobre CorporateData.

Implementa la clase SingletonClient que permite ejecutar las acciones
'get', 'set' y 'list' contra el servidor SingletonProxyObserverTPFI.
"""

import argparse
import json
import logging
import socket
import uuid
from typing import Any


class SingletonClient:
    """Cliente TCP para consultar o actualizar registros en CorporateData."""

    def __init__(self, host: str = "localhost", port: int = 8080) -> None:
        """Inicializa el cliente con la dirección y puerto del servidor.

        Args:
            host: Nombre de host o IP del servidor.
            port: Puerto TCP del servidor.
        """
        self.host = host
        self.port = port

    @staticmethod
    def cargar_peticion(input_path: str) -> dict[str, Any]:
        """Lee el archivo JSON de entrada y asegura la presencia del UUID de CPU.

        Args:
            input_path: Ruta al archivo JSON de entrada.

        Returns:
            Diccionario con la petición lista para enviar.
        """
        with open(input_path, encoding="utf-8") as f:
            peticion: dict[str, Any] = json.load(f)
        if "UUID" not in peticion or not peticion["UUID"]:
            peticion["UUID"] = str(uuid.getnode())
        return peticion

    def enviar_peticion(self, peticion: dict[str, Any]) -> dict[str, Any]:
        """Envía una petición JSON al servidor TCP y retorna la respuesta.

        Args:
            peticion: Diccionario con los datos del requerimiento.

        Returns:
            Diccionario JSON devuelto por el servidor.
        """
        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            logging.info(f"Conectando al servidor {self.host}:{self.port}...")
            cliente.connect((self.host, self.port))

            logging.info("Enviando petición...")
            cliente.send(json.dumps(peticion).encode("utf-8"))

            respuesta_raw = cliente.recv(4096).decode("utf-8")
            respuesta: dict[str, Any] = json.loads(respuesta_raw)
            return respuesta
        finally:
            cliente.close()

    def ejecutar(self, input_path: str, output_path: str | None = None) -> None:
        """Ejecuta el flujo completo de lectura, envío y presentación de resultados.

        Args:
            input_path: Ruta del archivo JSON de entrada.
            output_path: Ruta opcional del archivo JSON de salida.
        """
        try:
            peticion = self.cargar_peticion(input_path)
        except Exception as e:
            logging.error(f"Error leyendo {input_path}: {e}")
            return

        try:
            respuesta = self.enviar_peticion(peticion)
            if output_path:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(respuesta, f, indent=4)
                logging.info(f"Respuesta guardada en {output_path}")
            else:
                print(json.dumps(respuesta, indent=4))
        except Exception as e:
            logging.error(f"Error de red: {e}")


def main() -> None:
    """Punto de entrada de línea de comandos para SingletonClient."""
    parser = argparse.ArgumentParser(description="Cliente Singleton")
    parser.add_argument(
        "-i", "--input", type=str, required=True, help="Archivo JSON de entrada"
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Archivo JSON de salida (opcional)"
    )
    parser.add_argument(
        "-s", "--server", type=str, default="localhost", help="Hostname del servidor"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=8080, help="Puerto del servidor"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Activar trace")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    cliente = SingletonClient(host=args.server, port=args.port)
    cliente.ejecutar(input_path=args.input, output_path=args.output)


if __name__ == "__main__":
    main()
