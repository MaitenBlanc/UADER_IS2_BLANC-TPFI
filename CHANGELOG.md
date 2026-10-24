# Changelog

Todos los cambios notables en este proyecto son documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - Build 001 - 2026-10-24

### Agregado
- Implementación del servidor TCP [`singletonproxyobserver.py`](src/tpfi_is2_aws/singletonproxyobserver.py) integrando los patrones de diseño **Singleton**, **Proxy** y **Observer**.
- Separación del acceso físico a AWS DynamoDB en sendos patrones Singleton thread-safe: `CorporateDataSingleton` (tabla `CorporateData`) y `CorporateLogSingleton` (tabla `CorporateLog`).
- Registro de metadatos de CPU y plataforma en `CorporateLog` utilizando los paquetes `platform` y `uuid` (`uuid.getnode()` y `uuid.uuid4()`).
- Implementación orientada a objetos de [`singletonclient.py`](src/tpfi_is2_aws/singletonclient.py) (`SingletonClient`) para operaciones `get`, `set` y `list` con soporte de archivo de salida opcional (`-o`), trazas (`-v`) y configuración de host/puerto (`-s`, `-p`).
- Implementación orientada a objetos de [`observerclient.py`](src/tpfi_is2_aws/observerclient.py) (`ObserverClient`) para suscripción en tiempo real (`subscribe`) y reconexión automática parametrizable (cada 30 segundos por defecto).
- Lógica completa en acción `set`: actualización parcial preservando campos no informados si el registro existe, o creación con campos en blanco si la clave no existía previamente.
- Diagramas UML de Actividad (gestión Proxy `list`/`get`/`set`) y de Estado (gestión Observer `subscribe`) en `README.md`.
- Suite de pruebas unitarias automatizadas con `pytest` y `unittest.mock` en `tests/test_tpfi_is2_aws.py` superando el 85% de cobertura.
- Script de pruebas de aceptación e integración con AWS DynamoDB en `test_aceptacion.py` (camino feliz de todas las acciones, servidor caído, argumentos malformados en cada programa, datos mínimos y doble instancia de servidor).
- Pipeline de CI/CD en GitHub Actions (`.github/workflows/ci.yml`) ejecutando `black`, `ruff` (PEP8 y PEP257), `bandit`, `mypy`, `pyright`, `pytest --cov` y generación automática de documentación con `pdoc`.

