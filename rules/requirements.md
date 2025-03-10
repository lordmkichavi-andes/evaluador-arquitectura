# Requerimientos Específicos

- Debe existir un adaptador entrante (REST) que reciba solicitudes del "Cliente".
- La capa "Aplicación" debe exponer la interfaz "IEnviarDinero" para gestionar la operación de pagos.
- "Adaptador Saliente (API Pagos)" integra el servicio de pagos externo y lo inyecta en "Aplicación" mediante la interfaz.
- "Adaptador Saliente (Notificaciones)" envía notificaciones después de completar la transacción.
- "Adaptador Saliente (DB)" administra el acceso a datos, sin exponer detalles de infraestructura al "Dominio".
