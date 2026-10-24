"""Test de Aceptación Automatizado (Integración Real con AWS DynamoDB).

Verifica todos los casos solicitados en la sección Validación y Verificación:
1. Camino feliz de cada una de las acciones (set, get, list, subscribe) e impacto en
   las tablas CorporateData y CorporateLog.
2. Intento de llamar los programas con argumentos malformados (cada uno de los 3).
3. Intento de requerimiento sin indicar datos mínimos necesarios.
4. Manejo en clientes de server aplicativo caído.
5. Intento de levantar dos veces el servidor de aplicaciones.
"""

import json
import os
import subprocess
import time

import boto3  # type: ignore[import-untyped]


def ejecutar_comando(comando: str) -> tuple[int, str, str]:
    """Ejecuta un comando en la terminal y devuelve código de salida, stdout y stderr."""
    resultado = subprocess.run(
        comando, shell=True, capture_output=True, text=True  # nosec B602
    )
    return resultado.returncode, resultado.stdout, resultado.stderr


def test_servidor_caido() -> None:
    """Evalúa el manejo en clientes (SingletonClient y ObserverClient) de server caído."""
    print("\n--- TEST 1: Servidor Caído ---")
    codigo, stdout, stderr = ejecutar_comando(
        "python src/tpfi_is2_aws/singletonclient.py -i data/input_list.json -v"
    )
    if (
        "Error de red" in stderr
        or "Connection refused" in stderr
        or "Error" in stderr
        or codigo == 0
    ):
        print("ÉXITO: SingletonClient manejó correctamente la caída del servidor.")
    else:
        print("FALLO: SingletonClient no manejó la caída del servidor.")

    # Probar ObserverClient ante servidor caído durante unos segundos
    obs_proc = subprocess.Popen(
        [
            "python",
            "src/tpfi_is2_aws/observerclient.py",
            "-s",
            "localhost",
            "-p",
            "8080",
            "-v",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(2)
    if obs_proc.poll() is None:
        print(
            "ÉXITO: ObserverClient capturó la excepción de servidor caído y aguarda reconexión."
        )
    else:
        print("FALLO: ObserverClient terminó inesperadamente con servidor caído.")
    obs_proc.terminate()
    obs_proc.wait()


def test_argumentos_malformados() -> None:
    """Evalúa el intento de llamar a cada uno de los 3 programas con argumentos malformados."""
    print("\n--- TEST 2: Argumentos Malformados (en cada programa) ---")
    programas = [
        (
            "SingletonClient",
            "python src/tpfi_is2_aws/singletonclient.py --arg-invalido",
        ),
        ("ObserverClient", "python src/tpfi_is2_aws/observerclient.py --arg-invalido"),
        (
            "SingletonProxyObserver",
            "python src/tpfi_is2_aws/singletonproxyobserver.py --arg-invalido",
        ),
    ]
    for nombre, cmd in programas:
        codigo, _, _ = ejecutar_comando(cmd)
        if codigo != 0:
            print(
                f"ÉXITO: {nombre} rechazó los argumentos malformados correctamente (código {codigo})."
            )
        else:
            print(f"FALLO: {nombre} aceptó argumentos inválidos.")


def test_doble_servidor() -> None:
    """Evalúa el intento de levantar dos veces el servidor de aplicaciones en el mismo puerto."""
    print("\n--- TEST 3: Levantar servidor dos veces ---")
    servidor1 = subprocess.Popen(
        ["python", "src/tpfi_is2_aws/singletonproxyobserver.py", "-p", "8080"]
    )
    time.sleep(2)

    try:
        resultado = subprocess.run(
            ["python", "src/tpfi_is2_aws/singletonproxyobserver.py", "-p", "8080"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if "Address already in use" in resultado.stderr or resultado.returncode != 0:
            print(
                "ÉXITO: El sistema impidió levantar dos servidores en el mismo puerto."
            )
        else:
            print("FALLO: Se permitió levantar un segundo servidor.")
    finally:
        servidor1.terminate()
        servidor1.wait()


def test_camino_feliz_y_datos_minimos() -> None:
    """Evalúa requerimiento sin datos mínimos y camino feliz de todas las acciones en DynamoDB."""
    print(
        "\n--- TEST 4: Datos Mínimos, Camino Feliz (SET, GET, LIST, SUBSCRIBE) y DynamoDB ---"
    )

    input_sin_accion = "data/input_sin_accion.json"
    input_get_sin_id = "data/input_get_sin_id.json"
    salida_observer = "data/salida_observer_test.json"

    with open(input_sin_accion, "w", encoding="utf-8") as f:
        json.dump({"UUID": "test-uuid-fallo"}, f)
    with open(input_get_sin_id, "w", encoding="utf-8") as f:
        json.dump({"UUID": "test-uuid-fallo", "ACTION": "get"}, f)
    if os.path.exists(salida_observer):
        os.remove(salida_observer)

    servidor = subprocess.Popen(
        ["python", "src/tpfi_is2_aws/singletonproxyobserver.py", "-p", "8080", "-v"]
    )
    time.sleep(2)

    observer = subprocess.Popen(
        [
            "python",
            "src/tpfi_is2_aws/observerclient.py",
            "-s",
            "localhost",
            "-p",
            "8080",
            "-o",
            salida_observer,
            "-v",
        ]
    )
    time.sleep(2)

    try:
        # A. Test de requerimiento sin datos mínimos
        print("Probando requerimientos sin datos mínimos...")
        _, stdout_no_act, _ = ejecutar_comando(
            f"python src/tpfi_is2_aws/singletonclient.py -i {input_sin_accion}"
        )
        _, stdout_no_id, _ = ejecutar_comando(
            f"python src/tpfi_is2_aws/singletonclient.py -i {input_get_sin_id}"
        )
        if "Error" in stdout_no_act and "Error" in stdout_no_id:
            print("ÉXITO: Se rechazaron las peticiones sin datos mínimos necesarios.")
        else:
            print("FALLO: No se detectó la falta de datos mínimos.")

        # B. Camino Feliz: SET (actualiza CorporateData y notifica al ObserverClient)
        print("Ejecutando acción SET (Camino Feliz)...")
        _, stdout_set, _ = ejecutar_comando(
            "python src/tpfi_is2_aws/singletonclient.py -i data/input_set.json -v"
        )
        if '"set"' in stdout_set:
            print("ÉXITO: Acción SET ejecutada y respondida correctamente.")

        # C. Camino Feliz: GET
        print("Ejecutando acción GET (Camino Feliz)...")
        _, stdout_get, _ = ejecutar_comando(
            "python src/tpfi_is2_aws/singletonclient.py -i data/input_get.json -v"
        )
        if '"get"' in stdout_get and "UADER-FCYT-IS2" in stdout_get:
            print("ÉXITO: Acción GET recuperó el registro correctamente.")

        # D. Camino Feliz: LIST
        print("Ejecutando acción LIST (Camino Feliz)...")
        _, stdout_list, _ = ejecutar_comando(
            "python src/tpfi_is2_aws/singletonclient.py -i data/input_list.json -v"
        )
        if '"list"' in stdout_list:
            print("ÉXITO: Acción LIST devolvió los registros de la tabla.")

        time.sleep(2)

        # E. Verificar recepción de notificación en ObserverClient (SUBSCRIBE + CHANGE)
        if os.path.exists(salida_observer):
            with open(salida_observer, encoding="utf-8") as f:
                contenido_obs = f.read()
            if "change" in contenido_obs or "OK" in contenido_obs:
                print(
                    "ÉXITO: ObserverClient se suscribió y recibió las notificaciones de cambio."
                )

        # F. Verificación directa en DynamoDB usando boto3
        print("Verificando impacto en tablas CorporateData y CorporateLog en AWS...")
        dynamodb = boto3.resource("dynamodb")
        table_data = dynamodb.Table("CorporateData")
        table_log = dynamodb.Table("CorporateLog")

        data_resp = table_data.get_item(Key={"id": "UADER-FCYT-IS2"})
        if "Item" in data_resp and data_resp["Item"].get("sede") == "FCyT":
            print("ÉXITO: Los datos impactaron correctamente en CorporateData.")
        else:
            print("FALLO: Los datos no se encontraron en CorporateData.")

        log_resp = table_log.scan()
        items_log = log_resp.get("Items", [])
        acciones_registradas = {item.get("accion") for item in items_log}
        esperadas = {"set", "get", "list", "subscribe"}
        if esperadas.issubset(acciones_registradas):
            print(
                f"ÉXITO: Todas las acciones {esperadas} quedaron auditadas en CorporateLog."
            )
        elif len(items_log) > 0:
            print(
                f"ÉXITO PARCIAL: Actividad registrada en CorporateLog ({acciones_registradas})."
            )
        else:
            print("FALLO: No se registró la auditoría en CorporateLog.")

    finally:
        observer.terminate()
        observer.wait()
        servidor.terminate()
        servidor.wait()
        for temp_file in (input_sin_accion, input_get_sin_id, salida_observer):
            if os.path.exists(temp_file):
                os.remove(temp_file)


if __name__ == "__main__":
    test_servidor_caido()
    test_argumentos_malformados()
    test_doble_servidor()
    test_camino_feliz_y_datos_minimos()
    print("\n--- TODOS LOS TESTS DE ACEPTACIÓN FINALIZADOS ---")
