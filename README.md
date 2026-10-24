# TPFI IS2 AWS - Patrones Singleton, Proxy y Observer con DynamoDB

Trabajo Práctico Final Integrador (TPFI) de **Ingeniería de Software II (UADER - FCyT)**.
Implementación de una arquitectura cliente-servidor TCP en Python que gestiona el acceso a **AWS DynamoDB** (`CorporateData` y `CorporateLog`) utilizando los patrones de diseño **Singleton**, **Proxy** y **Observer**.

* **Autora:** [Maiten Blanc](https://github.com/MaitenBlanc)
* **Versión:** `1.0.0` | **Build:** `001`
* **Licencia:** MIT License

---

## Características Principales

* **Patrones Singleton (`CorporateDataSingleton` y `CorporateLogSingleton`):** Sendos Singletons *thread-safe* para el acceso físico independiente a las tablas `CorporateData` y `CorporateLog` en AWS DynamoDB mediante `boto3`, incluyendo recolección de metadatos de CPU con `platform` y `uuid.getnode()`.
* **Patrón Proxy (`CorporateDataProxy`):** Intermediario que intercepta todas las peticiones (`get`, `list`, `set`, `subscribe`), registra obligatoriamente una pista de auditoría en `CorporateLog` (`UUID`, `sesion` vía `uuid.uuid4()`, `accion`, `timestamp` y datos de CPU) y delega la operación al Singleton correspondiente.
* **Patrón Observer (`ObserverManager`):** Gestión de clientes suscriptos mediante sockets TCP abiertos y notificación automática en tiempo real ante cada actualización (`set`) en la base de datos.
* **Calidad y CI/CD:** Validación continua con `black`, `ruff` (PEP8 y PEP257), `mypy`, `pyright`, `bandit`, `pytest` (cobertura > 85%) y generación de documentación automática con `pdoc` mediante GitHub Actions.

---

## Diseño de Arquitectura (Diagramas UML)

### 1. Diagrama de Actividad UML (Gestión Proxy)
Modela cómo se gestionan internamente las acciones `list`, `get` y `set` dentro del servidor de aplicaciones:

```mermaid
flowchart TD
    A([Inicio: Cliente conecta por TCP]) --> B[Recibir JSON con petición]
    B --> C{¿Qué acción solicita?}
    
    C -->|get| D[Auditoría: Registrar 'get' en CorporateLog vía CorporateLogSingleton]
    C -->|list| E[Auditoría: Registrar 'list' en CorporateLog vía CorporateLogSingleton]
    C -->|set| F[Auditoría: Registrar 'set' en CorporateLog vía CorporateLogSingleton]
    
    D --> G[Proxy: Recuperar tuple de CorporateData vía CorporateDataSingleton]
    E --> H[Proxy: Recuperar toda la tabla vía CorporateDataSingleton]
    F --> I[Proxy: Actualizar o crear tuple en CorporateData vía CorporateDataSingleton]
    
    G --> J[Formatear respuesta JSON]
    H --> J
    I --> J
    
    J --> K[Enviar JSON al cliente]
    K --> L([Fin: Cerrar conexión del cliente solicitante])
    
    I --> M[Disparar evento al Observer]
```

### 2. Diagrama de Estado UML (Gestión Observer)
Representa la gestión de las suscripciones usando el patrón Observer en el servidor:

```mermaid
stateDiagram-v2
    [*] --> EscuchandoPuerto
    
    EscuchandoPuerto --> ProcesandoSuscripcion : Recibe acción 'subscribe'
    ProcesandoSuscripcion --> RegistrandoAuditoria : Log en CorporateLog
    RegistrandoAuditoria --> SuscriptorRegistrado : Guardar socket en lista activa
    SuscriptorRegistrado --> EscuchandoPuerto : Mantiene conexión abierta
    
    EscuchandoPuerto --> NotificandoCambios : Se detecta evento 'set' en DB
    NotificandoCambios --> IterandoSockets
    IterandoSockets --> EnviandoJSON : Por cada suscriptor
    EnviandoJSON --> IterandoSockets
    IterandoSockets --> EscuchandoPuerto : Fin de iteración
    
    EscuchandoPuerto --> LimpiandoSuscriptores : Detecta socket desconectado
    LimpiandoSuscriptores --> EscuchandoPuerto
```

---

## Instalación y Configuración

1. **Crear y activar el entorno virtual:**
   ```bash
   python3 -m venv TPF
   source TPF/bin/activate
   ```

2. **Instalar dependencias y el paquete en modo editable:**
   ```bash
   pip install -r REQUIREMENTS.txt
   pip install -e .
   ```

3. **Configurar credenciales de AWS CLI:**
   ```bash
   aws configure
   ```
   *(Ingresar `AWS Access Key ID`, `AWS Secret Access Key` y región `us-west-2`).*

---

## Guía de Uso y Pruebas Manuales

Abrir **tres terminales** con el entorno virtual activado desde la raíz del proyecto:

### Terminal 1: Servidor (`singletonproxyobserver.py`)
```bash
python src/tpfi_is2_aws/singletonproxyobserver.py -p 8080 -v
```

### Terminal 2: Cliente Observador (`observerclient.py`)
```bash
python src/tpfi_is2_aws/observerclient.py -s localhost -p 8080 -o data/salida_observer.json -v
```

### Terminal 3: Cliente Transaccional (`singletonclient.py`)
* **Listar registros (`list`):**
  ```bash
  python src/tpfi_is2_aws/singletonclient.py -i data/input_list.json -v
  ```
* **Consultar un registro (`get`):**
  ```bash
  python src/tpfi_is2_aws/singletonclient.py -i data/input_get.json -v
  ```
* **Actualizar un registro y disparar notificación al Observer (`set`):**
  ```bash
  python src/tpfi_is2_aws/singletonclient.py -i data/input_set.json -v
  ```

---

## Testing, Calidad y Cobertura

### 1. Tests Unitarios (con Mocks) y Cobertura (> 85%)
```bash
pytest --cov=src/tpfi_is2_aws tests/test_tpfi_is2_aws.py --cov-fail-under=85
```

### 2. Tests de Aceptación (Integración Real con AWS DynamoDB)
Evalúa servidor caído, argumentos malformados en cada programa, doble apertura de puerto, datos mínimos y el camino feliz de todas las acciones (`set`, `get`, `list`, `subscribe`) con impacto real en `CorporateData` y `CorporateLog`:
```bash
python3 test_aceptacion.py
```

### 3. Validaciones de Formato (PEP8 / PEP257), Tipado, Seguridad y Documentación
```bash
black --check src/ tests/
ruff check src/ tests/
mypy src/
pyright src/
bandit -r src/ -ll
pdoc src/tpfi_is2_aws -o docs_output
```

```