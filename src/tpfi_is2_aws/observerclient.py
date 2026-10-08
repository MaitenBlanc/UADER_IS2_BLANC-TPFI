"""
Módulo cliente subscrito al patrón Observer del servidor.
"""
import socket
import json
import argparse
import logging
import uuid
import time

def conectar_y_escuchar(host: str, port: int, output_file: str):
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        logging.info(f"Intentando conectar a {host}:{port}...")
        cliente.connect((host, port))
        
        # Generar JSON de subscripción
        peticion = {
            "UUID": str(uuid.getnode()),
            "ACTION": "subscribe"
        }
        cliente.send(json.dumps(peticion).encode('utf-8'))
        logging.info("Suscripción enviada. Esperando notificaciones...")
        
        while True:
            # Mantener puerto abierto recibiendo datos
            datos = cliente.recv(4096).decode('utf-8')
            if not datos:
                logging.warning("Conexión cerrada por el servidor.")
                break
                
            for linea in datos.strip().split('\n'):
                if linea:
                    respuesta = json.loads(linea)
                    print(">>> EVENTO RECIBIDO:", json.dumps(respuesta, indent=4))
                    
                    if output_file:
                        with open(output_file, 'a', encoding='utf-8') as f:
                            json.dump(respuesta, f)
                            f.write("\n")
                            
    except Exception as e:
        logging.error(f"Conexión interrumpida: {e}")
    finally:
        cliente.close()

def main():
    parser = argparse.ArgumentParser(description='Cliente Observer')
    parser.add_argument('-s', '--server', type=str, default='localhost', help='Hostname del servidor')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Puerto del servidor')
    parser.add_argument('-o', '--output', type=str, help='Archivo JSON de salida')
    parser.add_argument('-v', '--verbose', action='store_true', help='Activar trace')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Reintento en caso de caída (cada 30 segundos)
    while True:
        conectar_y_escuchar(args.server, args.port, args.output)
        logging.info("Reintentando conexión en 30 segundos...")
        time.sleep(30)

if __name__ == "__main__":
    main()