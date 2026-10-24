# Instalación y Configuración

## 1. Crear y activar el entorno virtual (`venv`)

Desde la raíz del proyecto, crear y activar el ambiente virtual de Python:

```bash
python3 -m venv TPF
source TPF/bin/activate
```

## 2. Instalar dependencias y el paquete

Instalar todas las librerías listadas en `REQUIREMENTS.txt` y registrar el paquete en modo editable:

```bash
pip install -r REQUIREMENTS.txt
pip install -e .
```

## 3. Configurar credenciales de AWS

Asegúrese de configurar las credenciales de acceso a AWS DynamoDB con permiso sobre las tablas `CorporateData` y `CorporateLog`:

```bash
aws configure
```

Ingrese su `AWS Access Key ID`, `AWS Secret Access Key` y la región correspondiente (por ejemplo `us-west-2` o `us-east-1`).
