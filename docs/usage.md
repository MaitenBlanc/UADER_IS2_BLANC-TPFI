# Guía de Uso

El sistema está compuesto por tres aplicativos en lenguaje Python dentro de `src/tpfi_is2_aws/`:

## 1. Servidor (`singletonproxyobserver.py`)

Inicia el servidor TCP (por defecto en el puerto `8080`):

```bash
python src/tpfi_is2_aws/singletonproxyobserver.py -p 8080 -v
```

## 2. Cliente Observador (`observerclient.py`)

Se suscribe al servidor mediante la acción `subscribe` y permanece a la escucha de actualizaciones en `CorporateData`. Si el servidor cae, reintenta la conexión automáticamente cada 30 segundos (parametrizable con `-r`):

```bash
python src/tpfi_is2_aws/observerclient.py -s localhost -p 8080 -o data/salida_observer.json -v
```

## 3. Cliente Transaccional (`singletonclient.py`)

Permite consultar un registro (`get`), listar toda la tabla (`list`) o insertar/modificar un registro (`set`):

```bash
# Listar todos los registros
python src/tpfi_is2_aws/singletonclient.py -i data/input_list.json -v

# Consultar un registro por ID
python src/tpfi_is2_aws/singletonclient.py -i data/input_get.json -v

# Crear o modificar un registro (notifica a los clientes Observer suscritos)
python src/tpfi_is2_aws/singletonclient.py -i data/input_set.json -o data/salida_set.json -v
```
