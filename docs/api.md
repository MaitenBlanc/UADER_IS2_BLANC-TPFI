# Referencia de API

Documentación de los módulos que componen el paquete `tpfi_is2_aws`:

- **`tpfi_is2_aws.singletonproxyobserver`**:
  - `CorporateDataSingleton`: Patrón Singleton para acceso físico a la tabla `CorporateData`.
  - `CorporateLogSingleton`: Patrón Singleton para acceso físico a la tabla `CorporateLog`, incluyendo recolección de datos de CPU mediante `platform` y `uuid.getnode()`.
  - `DatabaseSingleton`: Fachada Singleton que unifica el acceso a `CorporateDataSingleton` y `CorporateLogSingleton`.
  - `ObserverManager`: Patrón Observer que administra la suscripción de sockets TCP (`attach`, `detach`, `notify`).
  - `CorporateDataProxy`: Patrón Proxy que audita todas las peticiones en `CorporateLog` con `uuid.uuid4()` y delega la operación a los Singletons y al Observer.
  - `SingletonProxyObserverServer`: Servidor de aplicaciones TCP multihilo.
- **`tpfi_is2_aws.singletonclient`**:
  - `SingletonClient`: Cliente TCP orientado a objetos para enviar requerimientos `get`, `set` y `list`.
- **`tpfi_is2_aws.observerclient`**:
  - `ObserverClient`: Cliente TCP orientado a objetos para suscripción continua (`subscribe`) y reconexión automática.

::: tpfi_is2_aws
    options:
      show_submodules: true
