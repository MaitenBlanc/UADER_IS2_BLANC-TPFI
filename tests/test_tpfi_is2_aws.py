"""Tests unitarios (Mock) para verificar los patrones y lógica interna del sistema."""

from unittest.mock import MagicMock, mock_open, patch

import pytest

from tpfi_is2_aws.observerclient import ObserverClient, conectar_y_escuchar
from tpfi_is2_aws.observerclient import main as observer_main
from tpfi_is2_aws.singletonclient import SingletonClient
from tpfi_is2_aws.singletonclient import main as client_main
from tpfi_is2_aws.singletonproxyobserver import (
    CORPORATE_DATA_FIELDS,
    CorporateDataProxy,
    CorporateDataSingleton,
    CorporateLogSingleton,
    DatabaseSingleton,
    ObserverManager,
    SingletonProxyObserverServer,
    client_handler,
)
from tpfi_is2_aws.singletonproxyobserver import main as main_server


@pytest.fixture
def mock_boto3():
    """Fixture que simula el recurso DynamoDB de boto3."""
    CorporateDataSingleton._instancia = None
    CorporateLogSingleton._instancia = None
    DatabaseSingleton._instancia = None
    with patch("tpfi_is2_aws.singletonproxyobserver.boto3.resource") as mock_resource:
        mock_db = MagicMock()
        mock_resource.return_value = mock_db
        yield mock_db


def test_patron_singleton_tablas_separadas(mock_boto3):
    """Verifica que CorporateDataSingleton, CorporateLogSingleton y DatabaseSingleton sean Singletons."""
    data1 = CorporateDataSingleton()
    data2 = CorporateDataSingleton()
    assert data1 is data2

    log1 = CorporateLogSingleton()
    log2 = CorporateLogSingleton()
    assert log1 is log2

    db1 = DatabaseSingleton()
    db2 = DatabaseSingleton()
    assert db1 is db2


def test_corporate_log_datos_cpu(mock_boto3):
    """Verifica que CorporateLogSingleton incorpore datos de CPU desde platform y uuid."""
    log_singleton = CorporateLogSingleton()
    log_singleton.table_log.put_item = MagicMock()

    resultado = log_singleton.log_action(
        {"id": "1", "UUID": "123", "accion": "get", "sesion": "s1", "timestamp": "t1"}
    )

    assert "CPU_UUID" in resultado
    assert "sistema" in resultado
    assert "nodo" in resultado
    assert "arquitectura" in resultado
    assert "procesador" in resultado
    log_singleton.table_log.put_item.assert_called_once()


def test_corporate_data_set_nuevo_y_existente(mock_boto3):
    """Verifica que set_record cree campos en blanco si no existe o actualice parcialmente si existe."""
    data_singleton = CorporateDataSingleton()
    data_singleton.table_data.put_item = MagicMock()

    # Caso 1: Registro nuevo (no existe previamente)
    data_singleton.table_data.get_item.return_value = {}
    nuevo = data_singleton.set_record({"id": "UADER-NEW", "cp": "3260"})
    assert nuevo["id"] == "UADER-NEW"
    assert nuevo["cp"] == "3260"
    for campo in CORPORATE_DATA_FIELDS:
        if campo != "cp":
            assert nuevo[campo] == ""

    # Caso 2: Registro existente (conserva campos previos no informados)
    data_singleton.table_data.get_item.return_value = {
        "Item": {"id": "UADER-NEW", "cp": "3260", "sede": "FCyT", "localidad": "CDU"}
    }
    actualizado = data_singleton.set_record({"id": "UADER-NEW", "cp": "3261"})
    assert actualizado["cp"] == "3261"
    assert actualizado["sede"] == "FCyT"
    assert actualizado["localidad"] == "CDU"


def test_patron_observer():
    """Verifica el patrón Observer: attach, detach, notify y limpieza de socket caído."""
    manager = ObserverManager()
    mock_socket = MagicMock()

    manager.attach(mock_socket)
    assert mock_socket in manager._observers

    manager.notify({"change": "data"})
    mock_socket.send.assert_called_once()

    manager.detach(mock_socket)
    assert mock_socket not in manager._observers
    # Remover nuevamente no debe lanzar excepción
    manager.detach(mock_socket)

    # Si un socket falla al enviar, debe removerse automáticamente
    bad_socket = MagicMock()
    bad_socket.send.side_effect = OSError("Socket roto")
    manager.attach(bad_socket)
    manager.notify({"change": "data"})
    assert bad_socket not in manager._observers


def test_patron_proxy_happy_path(mock_boto3):
    """Verifica el patrón Proxy para peticiones get válidas e inexistentes."""
    manager = ObserverManager()
    proxy = CorporateDataProxy(manager)

    proxy.db.get_record = MagicMock(return_value={"id": "UADER"})
    proxy.db.log_action = MagicMock()

    peticion = {"UUID": "123", "ACTION": "get", "ID": "UADER"}
    respuesta = proxy.procesar_peticion(peticion, MagicMock())

    assert respuesta == {"get": {"id": "UADER"}}
    proxy.db.log_action.assert_called_once()
    assert proxy.db.log_action.call_args[0][0]["accion"] == "get"

    # Registro no encontrado
    proxy.db.get_record = MagicMock(return_value={})
    respuesta_no_encontrado = proxy.procesar_peticion(peticion, MagicMock())
    assert respuesta_no_encontrado == {"Error": "Registro no encontrado"}


def test_proxy_faltan_datos(mock_boto3):
    """Verifica el Proxy cuando el requerimiento no indica datos mínimos."""
    proxy = CorporateDataProxy(ObserverManager())
    proxy.db.log_action = MagicMock()

    # Petición sin ACTION
    peticion_incompleta = {"UUID": "123", "ID": "UADER"}
    respuesta = proxy.procesar_peticion(peticion_incompleta, MagicMock())
    assert "Error" in respuesta
    assert respuesta["Error"] == "Acción no reconocida"

    # Petición get sin ID
    respuesta_get_sin_id = proxy.procesar_peticion({"ACTION": "get"}, MagicMock())
    assert "Error" in respuesta_get_sin_id

    # Petición set sin ID
    respuesta_set_sin_id = proxy.procesar_peticion(
        {"ACTION": "set", "data": {"cp": "3260"}}, MagicMock()
    )
    assert "Error" in respuesta_set_sin_id


def test_proxy_accion_list(mock_boto3):
    """Verifica que el Proxy enrute correctamente la acción list."""
    proxy = CorporateDataProxy(ObserverManager())
    proxy.db.list_records = MagicMock(return_value=[{"id": "UADER"}])
    proxy.db.log_action = MagicMock()

    respuesta = proxy.procesar_peticion({"ACTION": "list"}, MagicMock())
    assert respuesta == {"list": [{"id": "UADER"}]}
    proxy.db.log_action.assert_called_once()


def test_proxy_accion_set(mock_boto3):
    """Verifica que el Proxy actualice y notifique a los observadores en set."""
    manager = ObserverManager()
    manager.notify = MagicMock()
    proxy = CorporateDataProxy(manager)
    proxy.db.set_record = MagicMock(return_value={"cp": "3260", "id": "UADER"})
    proxy.db.log_action = MagicMock()

    peticion = {
        "ACTION": "set",
        "ID": "UADER",
        "sede": "FCyT",
        "data": {"cp": "3260"},
    }
    respuesta = proxy.procesar_peticion(peticion, MagicMock())

    assert respuesta == {"set": {"cp": "3260", "id": "UADER"}}
    manager.notify.assert_called_once()


def test_proxy_accion_subscribe(mock_boto3):
    """Verifica que el Proxy enrute la suscripción guardando el socket."""
    manager = ObserverManager()
    manager.attach = MagicMock()
    proxy = CorporateDataProxy(manager)
    proxy.db.log_action = MagicMock()
    mock_socket = MagicMock()

    respuesta = proxy.procesar_peticion({"ACTION": "subscribe"}, mock_socket)

    assert respuesta["status"] == "OK"
    manager.attach.assert_called_once_with(mock_socket)


def test_database_singleton_delegacion(mock_boto3):
    """Verifica que DatabaseSingleton delegue correctamente a los dos Singletons."""
    db = DatabaseSingleton()
    db.data_singleton.table_data.get_item.return_value = {"Item": {"id": "UADER"}}
    db.data_singleton.table_data.scan.return_value = {"Items": [{"id": "UADER"}]}

    assert db.get_record("UADER") == {"id": "UADER"}
    assert db.list_records() == [{"id": "UADER"}]
    res_set = db.set_record({"id": "UADER", "cp": "3260"})
    assert res_set["cp"] == "3260"
    res_log = db.log_action({"id": "log1", "accion": "get"})
    assert res_log["accion"] == "get"


def test_client_handler_cierra_socket():
    """Verifica que el handler procesa la petición y cierra el socket transaccional."""
    mock_conn = MagicMock()
    mock_conn.recv.return_value = b'{"ACTION": "get"}'
    mock_proxy = MagicMock()
    mock_proxy.procesar_peticion.return_value = {"get": "data"}

    client_handler(mock_conn, ("127.0.0.1", 1234), mock_proxy)

    mock_conn.send.assert_called_once()
    mock_conn.close.assert_called_once()


def test_client_handler_vacio_y_excepcion():
    """Verifica manejo de payload vacío y excepción en client_handler."""
    mock_conn_vacio = MagicMock()
    mock_conn_vacio.recv.return_value = b""
    client_handler(mock_conn_vacio, ("127.0.0.1", 1234), MagicMock())
    mock_conn_vacio.close.assert_called_once()

    mock_conn_err = MagicMock()
    mock_conn_err.recv.return_value = b"json-invalido"
    client_handler(mock_conn_err, ("127.0.0.1", 1234), MagicMock())
    mock_conn_err.close.assert_called_once()


def test_client_handler_mantiene_abierto_subscribe():
    """Verifica que el handler NO cierra el socket si la acción es de suscripción."""
    mock_conn = MagicMock()
    mock_conn.recv.return_value = b'{"ACTION": "subscribe"}'
    mock_proxy = MagicMock()
    mock_proxy.procesar_peticion.return_value = {"status": "OK"}

    client_handler(mock_conn, ("127.0.0.1", 1234), mock_proxy)

    mock_conn.send.assert_called_once()
    mock_conn.close.assert_not_called()


def test_singletonclient_exito():
    """Verifica la ejecución del cliente transaccional interceptando la lectura del JSON."""
    test_json = '{"ACTION": "list"}'
    mock_response = '{"list": [{"id": "UADER"}]}'

    with (
        patch("sys.argv", ["singletonclient.py", "-i", "data/dummy.json"]),
        patch("builtins.open", mock_open(read_data=test_json)),
        patch("socket.socket") as mock_socket,
    ):
        mock_conn = MagicMock()
        mock_conn.recv.return_value = mock_response.encode("utf-8")
        mock_socket.return_value = mock_conn

        client_main()

        mock_conn.connect.assert_called_once_with(("localhost", 8080))
        mock_conn.send.assert_called_once()


def test_observerclient_escucha():
    """Verifica que el observador envíe su suscripción, escuche eventos y guarde salida."""
    with (
        patch("socket.socket") as mock_socket,
        patch("builtins.open", mock_open()) as m_open,
    ):
        mock_conn = MagicMock()
        mock_conn.recv.side_effect = [b'{"change": "data"}\n', b""]
        mock_socket.return_value = mock_conn

        conectar_y_escuchar("localhost", 8080, "out_obs.json")

        mock_conn.connect.assert_called_once_with(("localhost", 8080))
        mock_conn.send.assert_called_once()
        m_open.assert_called_once_with("out_obs.json", "a", encoding="utf-8")


def test_observerclient_excepcion():
    """Verifica el manejo de excepción de conexión en conectar_y_escuchar."""
    with patch("socket.socket") as mock_socket:
        mock_conn = MagicMock()
        mock_conn.connect.side_effect = ConnectionError("Caído")
        mock_socket.return_value = mock_conn

        conectar_y_escuchar("localhost", 8080, None)
        mock_conn.close.assert_called_once()


def test_servidor_main_bucle(mock_boto3):
    """Verifica el arranque del servidor TCP y su apagado correcto."""
    with (
        patch("sys.argv", ["singletonproxyobserver.py", "-p", "8080", "-v"]),
        patch("socket.socket") as mock_socket,
        patch("threading.Thread") as mock_thread,
    ):
        mock_server = MagicMock()
        mock_client_conn = MagicMock()
        mock_server.accept.side_effect = [
            (mock_client_conn, ("127.0.0.1", 5000)),
            KeyboardInterrupt,
        ]
        mock_socket.return_value = mock_server

        main_server()

        mock_server.bind.assert_called_once_with(("0.0.0.0", 8080))
        mock_server.listen.assert_called_once()
        mock_thread.assert_called_once()
        mock_server.close.assert_called_once()


def test_singletonclient_args_output_and_exception():
    """Cubre el parseo de argumentos (-v, -o), guardado de archivo y ejecución completa."""
    test_json = '{"UUID": "123", "ACTION": "get"}'
    mock_response = '{"get": "data"}'

    with (
        patch(
            "sys.argv", ["singletonclient.py", "-i", "in.json", "-o", "out.json", "-v"]
        ),
        patch("builtins.open", mock_open(read_data=test_json)) as mock_file,
        patch("socket.socket") as mock_socket,
    ):
        mock_conn = MagicMock()
        mock_conn.recv.return_value = mock_response.encode("utf-8")
        mock_socket.return_value = mock_conn

        client_main()

        mock_conn.connect.assert_called_once()
        mock_file.assert_called_with("out.json", "w", encoding="utf-8")


def test_singletonclient_file_error():
    """Cubre la excepción en SingletonClient al leer un archivo que no existe."""
    with (
        patch("sys.argv", ["singletonclient.py", "-i", "no_existe.json"]),
        patch("builtins.open", side_effect=FileNotFoundError("No existe")),
    ):
        client_main()


def test_observerclient_main_loop():
    """Cubre el parseo de argumentos de ObserverClient y su bucle infinito."""
    with (
        patch("sys.argv", ["observerclient.py", "-p", "8080", "-o", "out.json", "-v"]),
        patch("tpfi_is2_aws.observerclient.conectar_y_escuchar"),
        patch("time.sleep", side_effect=KeyboardInterrupt),
    ):
        try:
            observer_main()
        except KeyboardInterrupt:
            pass


def test_singletonclient_network_error():
    """Cubre el bloque de excepción de red en SingletonClient."""
    with (
        patch("sys.argv", ["singletonclient.py", "-i", "in.json"]),
        patch("builtins.open", mock_open(read_data='{"ACTION": "get"}')),
        patch("socket.socket") as mock_socket,
    ):
        mock_socket.return_value.connect.side_effect = ConnectionError("Fallo simulado")
        client_main()


def test_clases_oop_clientes_y_servidor(mock_boto3):
    """Verifica la instanciación directa de las clases OOP de clientes y servidor."""
    sc = SingletonClient(host="127.0.0.1", port=9090)
    assert sc.host == "127.0.0.1"
    assert sc.port == 9090

    oc = ObserverClient(
        host="127.0.0.1", port=9090, output_file="out.json", retry_interval=15
    )
    assert oc.host == "127.0.0.1"
    assert oc.port == 9090
    assert oc.retry_interval == 15

    srv = SingletonProxyObserverServer(host="127.0.0.1", port=9090)
    assert srv.host == "127.0.0.1"
    assert srv.port == 9090
