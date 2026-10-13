""" Test de Aceptación Automatizado (Integración Real con AWS) """
import subprocess
import time
import json
import boto3
import uuid
import os

def ejecutar_comando(comando):
    """Ejecuta un comando en la terminal y devuelve el código de salida y el texto."""
    resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
    return resultado.returncode, resultado.stdout, resultado.stderr

def test_servidor_caido():
    """Evalúa el manejo en clientes de server aplicativo caído."""
    print("\n--- TEST: Servidor Caído ---")
    # Intentar ejecutar el cliente sin haber levantado el servidor TCP
    codigo, stdout, stderr = ejecutar_comando("python src/tpfi_is2_aws/singletonclient.py -i data/input_list.json")
    if "Error de red" in stderr or "Connection refused" in stderr or codigo != 0:
        print("ÉXITO: El cliente manejó correctamente la caída del servidor.")
    else:
        print("FALLO: El cliente no detectó que el servidor estaba caído.")

def test_argumentos_malformados():
    """Intento de llamar los programas con argumentos malformados."""
    print("\n--- TEST: Argumentos Malformados ---")
    # Llamar al cliente sin el argumento obligatorio -i
    codigo, stdout, stderr = ejecutar_comando("python src/tpfi_is2_aws/singletonclient.py --argumento-falso")
    if codigo != 0:
        print("ÉXITO: El programa rechazó los argumentos malformados correctamente.")
    else:
        print("FALLO: El programa aceptó argumentos inválidos.")

def test_doble_servidor():
    """Intento de levantar dos veces el servidor de aplicaciones."""
    print("\n--- TEST: Levantar servidor dos veces ---")
    # Levantar el primer servidor en segundo plano
    servidor1 = subprocess.Popen(["python", "src/tpfi_is2_aws/singletonproxyobserver.py", "-p", "8080"])
    time.sleep(2) # Dar tiempo a que abra el puerto
    
    # Intentar levantar el segundo en el mismo puerto
    resultado = subprocess.run(["python", "src/tpfi_is2_aws/singletonproxyobserver.py", "-p", "8080"], capture_output=True, text=True)
    
    if "Address already in use" in resultado.stderr or resultado.returncode != 0:
        print("ÉXITO: El sistema impidió levantar dos servidores en el mismo puerto.")
    else:
        print("FALLO: Se permitió levantar un segundo servidor.")
        
    servidor1.terminate()
    servidor1.wait()

def test_camino_feliz_y_datos_minimos():
    """
    Camino feliz de acciones, intento sin datos mínimos, y validación en DynamoDB.
    """
    print("\n--- TEST: Camino Feliz, Datos Mínimos y DynamoDB ---")
    
    # Preparar archivo sin datos mínimos (sin ACTION)
    input_malo = "data/input_malo.json"
    with open(input_malo, "w") as f:
        json.dump({"UUID": "test-uuid-fallo"}, f)
        
    # Levantar el servidor
    servidor = subprocess.Popen(["python", "src/tpfi_is2_aws/singletonproxyobserver.py", "-p", "8080"])
    time.sleep(2)
    
    try:
        # A. Test de requerimiento sin datos mínimos
        print("Probando requerimiento sin datos mínimos...")
        codigo, stdout, stderr = ejecutar_comando(f"python src/tpfi_is2_aws/singletonclient.py -i {input_malo}")
        if "Acción no reconocida" in stdout or "Error" in stdout:
            print("ÉXITO: Se rechazó la petición sin datos mínimos.")
            
        # B. Test de Camino Feliz (SET)
        print("Ejecutando acción SET (Camino Feliz)...")
        ejecutar_comando("python src/tpfi_is2_aws/singletonclient.py -i data/input_set.json")
        time.sleep(2) # Dar tiempo a AWS para registrar
        
        # C. Verificación directa en DynamoDB usando boto3
        print("Verificando impacto en tablas CorporateData y CorporateLog...")
        dynamodb = boto3.resource('dynamodb')
        table_data = dynamodb.Table('CorporateData')
        table_log = dynamodb.Table('CorporateLog')
        
        # Verificar CorporateData
        data_resp = table_data.get_item(Key={'id': 'UADER-FCYT-IS2'})
        if 'Item' in data_resp and data_resp['Item'].get('sede') == 'FCyT':
            print("ÉXITO: Los datos impactaron correctamente en CorporateData.")
        else:
            print("FALLO: Los datos no se guardaron en CorporateData.")
            
        # Verificar CorporateLog (buscar un log reciente)
        # Hacer un scan rápido buscando la IP/UUID para confirmar auditoría
        log_resp = table_log.scan()
        logs_encontrados = [item for item in log_resp.get('Items', []) if item.get('accion') == 'set']
        
        if len(logs_encontrados) > 0:
            print("ÉXITO: La actividad impactó correctamente en CorporateLog.")
        else:
            print("FALLO: No se registró la auditoría en CorporateLog.")
            
    finally:
        # Limpieza
        servidor.terminate()
        servidor.wait()
        if os.path.exists(input_malo):
            os.remove(input_malo)

if __name__ == "__main__":
    test_servidor_caido()
    test_argumentos_malformados()
    test_doble_servidor()
    test_camino_feliz_y_datos_minimos()
    print("\n--- TODOS LOS TESTS DE ACEPTACIÓN FINALIZADOS ---")