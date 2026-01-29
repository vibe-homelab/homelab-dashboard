"""Service Registry for managing monitored services."""
from .config import ServiceConfig, get_config


class ServiceRegistry:
    """Registry for managing service configurations."""

    def __init__(self):
        self._config = get_config()

    def get_service(self, service_id: str) -> ServiceConfig | None:
        """Get a service by ID."""
        return self._config.services.get(service_id)

    def list_services(self) -> list[ServiceConfig]:
        """List all registered services."""
        return list(self._config.services.values())

    def get_service_ids(self) -> list[str]:
        """Get all service IDs."""
        return list(self._config.services.keys())

    def get_gateway_url(self, service_id: str) -> str | None:
        """Get the gateway URL for a service."""
        service = self.get_service(service_id)
        return service.gateway.url if service else None

    def get_worker_manager_url(self, service_id: str) -> str | None:
        """Get the worker manager URL for a service."""
        service = self.get_service(service_id)
        return service.worker_manager.url if service else None
