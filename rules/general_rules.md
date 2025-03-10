# Reglas Generales de Arquitectura

1. El componente "Dominio" no debe llamar directamente a los Adaptadores Salientes (DB, API, Notificaciones).
2. La capa "Aplicación" orquesta la ejecución y es la única que invoca el "Dominio" y las interfaces de infraestructura.
3. Si un elemento o interfaz empieza con "I", pertenece a la capa de Infraestructura (por ejemplo, "IEnviarDinero").
4. "Dominio" concentra la lógica de negocio y no depende de implementaciones externas.
5. Cualquier integración con servicios externos (APIs de pago, notificaciones, base de datos) debe encapsularse en Adaptadores Salientes.
