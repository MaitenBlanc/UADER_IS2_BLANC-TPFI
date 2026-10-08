"""
Módulo cliente para enviar requerimientos sobre CorporateData.
"""
import socket
import json
import argparse
import logging

def main():
    parser = argparse.ArgumentParser(description='Cliente Singleton')
    parser.add_argument('-i', '--input', type=str, required=True, help='Archivo JSON de entrada')
    parser.add_argument('-o', '--output', type=str, help='Archivo JSON de salida (opcional)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Activar trace')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Leer el archivo de entrada
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            peticion = json.load(f)
    except Exception as e:
        logging.error(f"Error leyendo {args.input}: {e}")
        return

    # Conectar al servidor TCP
    try:
        logging.info("Conectando al servidor localhost:8080...")
        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.connect(('localhost', 8080))
        
        # Enviar petición
        logging.info("Enviando petición...")
        cliente.send(json.dumps(peticion).encode('utf-8'))
        
        # Recibir respuesta
        respuesta_raw = cliente.recv(4096).decode('utf-8')
        respuesta = json.loads(respuesta_raw)
        
        # Mostrar o guardar salida
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(respuesta, f, indent=4)
            logging.info(f"Respuesta guardada en {args.output}")
        else:
            print(json.dumps(respuesta, indent=4))
            
    except Exception as e:
        logging.error(f"Error de red: {e}")
    finally:
        cliente.close()

if __name__ == "__main__":
    main()