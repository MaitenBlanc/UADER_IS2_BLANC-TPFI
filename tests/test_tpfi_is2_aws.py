"""Tests unitarios (Mock) para verificar los patrones y lógica interna del servidor."""

from unittest.mock import MagicMock, mock_open, patch

import pytest

from tpfi_is2_aws.observerclient import conectar_y_escuchar
from tpfi_is2_aws.observerclient import main as observer_main
from tpfi_is2_aws.singletonclient import main as client_main
from tpfi_is2_aws.singletonproxyobserver import (
    CorporateDataProxy,
    DatabaseSingleton,
    ObserverManager,
    client_handler,
)
from tpfi_is2_aws.singletonproxyobserver import main as main_server


@pytest.fixture
def mock_boto3():
    with patch("tpfi_is2_aws.singletonproxyobserver.boto3.resource") as mock_resource:
        mock_db = MagicMock()
        mock_resource.return_value = mock_db
        yield mock_db


def test_patron_singleton(mock_boto3):
    """Verifica que el patrón Singleton devuelva siempre la misma instancia."""
    DatabaseSingleton._instancia = None  # Reset para el test
    db1 = DatabaseSingleton()
    db2 = DatabaseSingleton()
    assert db1 is db2


def test_patron_observer():
    """Verifica el patrón Observer: attach, detach y notify."""
    manager = ObserverManager()
    mock_socket = MagicMock()

    manager.attach(mock_socket)
    assert mock_socket in manager._observers

    manager.notify({"change": "data"})
    mock_socket.send.assert_called_once()

    manager.detach(mock_socket)
    assert mock_socket not in manager._observers


def test_patron_proxy_happy_path(mock_boto3):
    """Verifica el patrón Proxy para peticiones válidas."""
    DatabaseSingleton._instancia = None
    manager = ObserverManager()
    proxy = CorporateDataProxy(manager)

    proxy.db.get_record = MagicMock(return_value={"id": "UADER"})
    proxy.db.log_action = MagicMock()

    peticion = {"UUID": "123", "ACTION": "get", "ID": "UADER"}
    respuesta = proxy.procesar_peticion(peticion, MagicMock())

    assert respuesta == {"get": {"id": "UADER"}}
    proxy.db.log_action.assert_called_once()
    assert proxy.db.log_action.call_args[0][0]["accion"] == "get"


def test_proxy_faltan_datos(mock_boto3):
    """Verifica el Proxy cuando el requerimiento no indica datos mínimos."""
    DatabaseSingleton._instancia = None
    proxy = CorporateDataProxy(ObserverManager())
    proxy.db.log_action = MagicMock()

    # Petición sin ACTION
    peticion_incompleta = {"UUID": "123", "ID": "UADER"}
    respuesta = proxy.procesar_peticion(peticion_incompleta, MagicMock())

    assert "Error" in respuesta
    assert respuesta["Error"] == "Acción no reconocida"


def test_proxy_accion_list(mock_boto3):
    """Verifica que el Proxy enrute correctamente la acción list."""
    DatabaseSingleton._instancia = None
    proxy = CorporateDataProxy(ObserverManager())
    proxy.db.list_records = MagicMock(return_value=[{"id": "UADER"}])
    proxy.db.log_action = MagicMock()

    respuesta = proxy.procesar_peticion({"ACTION": "list"}, MagicMock())
    assert respuesta == {"list": [{"id": "UADER"}]}
    proxy.db.log_action.assert_called_once()


def test_proxy_accion_set(mock_boto3):
    """Verifica que el Proxy actualice y notifique a los observadores en set."""
    DatabaseSingleton._instancia = None
    manager = ObserverManager()
    manager.notify = MagicMock()
    proxy = CorporateDataProxy(manager)
    proxy.db.set_record = MagicMock()
    proxy.db.log_action = MagicMock()

    peticion = {"ACTION": "set", "ID": "UADER", "data": {"cp": "3260"}}
    respuesta = proxy.procesar_peticion(peticion, MagicMock())

    assert respuesta == {"set": {"cp": "3260", "id": "UADER"}}
    manager.notify.assert_called_once()


def test_proxy_accion_subscribe(mock_boto3):
    """Verifica que el Proxy enrute la suscripción guardando el socket."""
    DatabaseSingleton._instancia = None
    manager = ObserverManager()
    manager.attach = MagicMock()
    proxy = CorporateDataProxy(manager)
    proxy.db.log_action = MagicMock()
    mock_socket = MagicMock()

    respuesta = proxy.procesar_peticion({"ACTION": "subscribe"}, mock_socket)

    assert respuesta["status"] == "OK"
    manager.attach.assert_called_once_with(mock_socket)


def test_client_handler_cierra_socket():
    """Verifica que el handler procesa la petición y cierra el socket transaccional."""
    mock_conn = MagicMock()
    mock_conn.recv.return_value = b'{"ACTION": "get"}'
    mock_proxy = MagicMock()
    mock_proxy.procesar_peticion.return_value = {"get": "data"}

    client_handler(mock_conn, ("127.0.0.1", 1234), mock_proxy)

    mock_conn.send.assert_called_once()
    mock_conn.close.assert_called_once()


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
    test_json = '{"UUID": "123", "ACTION": "list"}'
    mock_response = '{"list": [{"id": "UADER"}]}'

    # Simular los argumentos de consola, el archivo de lectura y el socket TCP
    with (
        patch("sys.argv", ["singletonclient.py", "-i", "data/dummy.json"]),
        patch("builtins.open", mock_open(read_data=test_json)),
        patch("socket.socket") as mock_socket,
    ):

        mock_conn = MagicMock()
        mock_conn.recv.return_value = mock_response.encode("utf-8")
        mock_socket.return_value = mock_conn

        client_main()

        # Verificar que el cliente intentó conectarse y envió los datos
        mock_conn.connect.assert_called_once_with(("localhost", 8080))
        mock_conn.send.assert_called_once()


def test_observerclient_escucha():
    """Verifica que el observador envíe su suscripción y escuche eventos."""
    with patch("socket.socket") as mock_socket:
        mock_conn = MagicMock()
        # El primer recv devuelve un evento, el segundo devuelve vacío para romper el bucle while
        mock_conn.recv.side_effect = [b'{"change": "data"}\n', b""]
        mock_socket.return_value = mock_conn

        conectar_y_escuchar("localhost", 8080, None)

        mock_conn.connect.assert_called_once_with(("localhost", 8080))
        mock_conn.send.assert_called_once()  # Garantiza que envió el 'subscribe'


def test_servidor_main_bucle():
    """Verifica el arranque del servidor TCP y su apagado correcto."""
    with (
        patch("sys.argv", ["singletonproxyobserver.py", "-p", "8080"]),
        patch("socket.socket") as mock_socket,
        patch("threading.Thread"),
    ):

        mock_server = MagicMock()
        # Simular un Ctrl+C (KeyboardInterrupt) para salir del 'while True' inmediatamente
        mock_server.accept.side_effect = KeyboardInterrupt
        mock_socket.return_value = mock_server

        main_server()

        # Verificar la secuencia completa de vida del socket
        mock_server.bind.assert_called_once_with(("0.0.0.0", 8080))
        mock_server.listen.assert_called_once()
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
        # Verificar que intentó abrir el archivo de salida para escribir
        mock_file.assert_called_with("out.json", "w", encoding="utf-8")


def test_singletonclient_file_error():
    """Cubre la excepción en SingletonClient al leer un archivo que no existe."""
    with (
        patch("sys.argv", ["singletonclient.py", "-i", "no_existe.json"]),
        patch("builtins.open", side_effect=FileNotFoundError("No existe")),
    ):
        client_main()  # Debería atrapar la excepción internamente y no crashear


def test_observerclient_main_loop():
    """Cubre el parseo de argumentos de ObserverClient y su bucle infinito."""
    with (
        patch("sys.argv", ["observerclient.py", "-p", "8080", "-o", "out.json", "-v"]),
        patch("tpfi_is2_aws.observerclient.conectar_y_escuchar"),
        patch("time.sleep", side_effect=KeyboardInterrupt),
    ):  # Simula Ctrl+C para salir del while True

        try:
            observer_main()
        except KeyboardInterrupt:
            pass  # El test pasa si se interrumpe correctamente


def test_singletonclient_network_error():
    """Cubre el bloque de excepción de red en SingletonClient."""
    with (
        patch("sys.argv", ["singletonclient.py", "-i", "in.json"]),
        patch("builtins.open", mock_open(read_data='{"ACTION": "get"}')),
        patch("socket.socket") as mock_socket,
    ):

        # Simular que la conexión TCP es rechazada
        mock_socket.return_value.connect.side_effect = ConnectionError("Fallo simulado")
        client_main()  # El programa debe capturar el error en el except y terminar limpiamente
