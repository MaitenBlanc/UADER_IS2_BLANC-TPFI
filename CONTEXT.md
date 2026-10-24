# Registro de Prompts y Contexto de IA (CONTEXT.md)

De acuerdo con los requerimientos del Trabajo Práctico Final Integrador de **Ingeniería de Software II (UADER - FCyT)**, en este archivo se documentan las consultas y prompts utilizados con herramientas de Inteligencia Artificial durante el desarrollo, validación y verificación del proyecto.

---

## 1. Diseño de Arquitectura y Patrones (Singleton, Proxy y Observer)

### Prompt 1: Modelado de diagramas UML en Mermaid
> *"Necesito generar dos diagramas UML en sintaxis Mermaid para el README.md de un trabajo práctico de Ingeniería de Software II:*
> *1. Un diagrama de actividad UML para la gestión de las acciones `list`, `get` y `set` en un servidor de aplicaciones que implementa el patrón Proxy sobre AWS DynamoDB (registrando auditoría en `CorporateLog` y accediendo a `CorporateData` mediante un Singleton).*
> *2. Un diagrama de estado UML para la gestión del patrón Observer en el servidor ante la acción `subscribe`, manteniendo sockets TCP abiertos y notificando cambios cuando ocurre un `set`."*

### Prompt 2: Implementación del servidor TCP con patrones de diseño
> *"Desarrollar en Python un servidor TCP multihilo (`singletonproxyobserver.py`) que escuche por defecto en el puerto 8080 (`-p`) y soporte flag `-v` con el paquete `logging`. Debe implementar:*
> *- Sendos patrones Singleton thread-safe para el acceso físico a las tablas `CorporateData` y `CorporateLog` en AWS DynamoDB usando `boto3`.*
> *- Un patrón Observer (`ObserverManager`) que registre los sockets de clientes suscritos con acción `subscribe` y les retransmita en formato JSON cada modificación realizada con `set`.*
> *- Un patrón Proxy (`CorporateDataProxy`) que intercepte las acciones `get`, `set`, `list` y `subscribe`, genere un identificador de sesión con `uuid.uuid4()`, obtenga datos de CPU con `platform` y `uuid.getnode()`, registre la pista de auditoría en `CorporateLog` y ejecute la acción correspondiente."*

---

## 2. Desarrollo de Clientes TCP (`singletonclient.py` y `observerclient.py`)

### Prompt 3: Cliente transaccional `SingletonClient`
> *"Implementar el programa `singletonclient.py` en Python orientado a objetos que reciba `-i=input.json`, opcionalmente `-o=output.json` y `-v` para activar mensajes de trace con `logging`. Debe leer el JSON de entrada, conectarse por socket TCP al servidor (por defecto `localhost:8080`), enviar el requerimiento (`get`, `set` o `list`), recibir la respuesta JSON e imprimirla por salida estándar o guardarla en el archivo indicado en `-o`."*

### Prompt 4: Cliente suscriptor `ObserverClient`
> *"Implementar el programa `observerclient.py` en Python que reciba `-s=hostname` (default `localhost`), `-p=port` (default `8080`), `-o=output.json` (opcional) y `-v`. Debe generar un JSON con el `UUID` de la CPU (`uuid.getnode()`) y `"ACTION": "subscribe"`, mantener el socket TCP abierto para recibir múltiples notificaciones de cambios en `CorporateData`, mostrarlas por pantalla y agregarlas a `output.json` si fue indicado. Si la conexión TCP se interrumpe, debe manejar la excepción y reintentar la conexión cada 30 segundos (parametrizable)."*

---

## 3. Validación, Verificación y Calidad de Código (CI/CD)

### Prompt 5: Pruebas unitarias con mocks y cobertura > 85%
> *"Crear una suite de tests unitarios con `pytest` y `unittest.mock` en `tests/test_tpfi_is2_aws.py` que verifique que las clases `CorporateDataSingleton` y `CorporateLogSingleton` devuelvan siempre la misma instancia, que `ObserverManager` gestione `attach`, `detach` y `notify`, y que `CorporateDataProxy` procese `get`, `set`, `list` y `subscribe` registrando siempre en `CorporateLog`. Asegurar una cobertura de código superior al 85% sin requerir conexión activa a AWS durante los tests unitarios."*

### Prompt 6: Test de aceptación e integración con AWS DynamoDB
> *"Crear el script automatizado `test_aceptacion.py` para validar los casos de prueba de aceptación exigidos por la cátedra:*
> *- Camino feliz de cada una de las acciones (`set`, `get`, `list`, `subscribe`), comprobando el impacto real en las tablas `CorporateData` y `CorporateLog` de DynamoDB.*
> *- Intento de invocar cada uno de los tres programas con argumentos malformados.*
> *- Requerimientos sin datos mínimos necesarios.*
> *- Manejo en los clientes cuando el servidor de aplicaciones está caído.*
> *- Intento de levantar dos veces el servidor de aplicaciones en el mismo puerto."*

### Prompt 7: Configuración de Linters, Tipado, Seguridad y CI/CD
> *"Configurar `pyproject.toml`, `REQUIREMENTS.txt` y el workflow de GitHub Actions `.github/workflows/ci.yml` para validar automáticamente el código con `ruff` (reglas PEP8 y docstrings PEP257), `black`, `mypy`, `pyright`, `bandit`, `pytest` (con `--cov-fail-under=85`) y generación de documentación automática con `pdoc`."*

### Prompt 8: Revisión de completitud contra la consigna oficial
> *"Actuá como un ingeniero de software senior y revisor de código.*
> *Necesito que audites el estado actual de este proyecto comparándolo minuciosamente contra las instrucciones que están en el archivo que te adjunto.*
> *Por favor, analizá todo el workspace y generá un reporte en tu respuesta con la siguiente estructura:*
> *1. Checklist de Cumplimiento: Una lista Markdown indicando qué requerimientos de la consigna ya están implementados y cuáles no.*
> *2. Puntos Faltantes y Errores: Detallá qué archivos, funciones, rutas o lógicas faltan desarrollar o están incompletas según el documento de requerimientos.*
> *3. Código de Corrección: Para los puntos faltantes más críticos, generá los snippets de código listos para implementar o indicame exactamente en qué líneas de qué archivos debo hacer los cambios."*

