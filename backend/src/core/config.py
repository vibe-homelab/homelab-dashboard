"""Configuration loader for Homelab Dashboard."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DashboardSettings:
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass
class GatewayConfig:
    host: str
    port: int

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class WorkerManagerConfig:
    host: str
    port: int

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class EndpointsConfig:
    health: str = "/healthz"
    status: str = "/v1/system/status"
    models: str = "/v1/models"
    evict: str = "/v1/system/evict/{alias}"


@dataclass
class WorkerConfig:
    alias: str
    name: str
    type: str


@dataclass
class ServiceConfig:
    id: str
    name: str
    description: str
    icon: str
    gateway: GatewayConfig
    worker_manager: WorkerManagerConfig
    endpoints: EndpointsConfig
    workers: list[WorkerConfig] = field(default_factory=list)


@dataclass
class PollingConfig:
    health_interval_seconds: int = 10
    status_interval_seconds: int = 5


@dataclass
class WebSocketConfig:
    heartbeat_interval_seconds: int = 30


@dataclass
class DashboardConfig:
    dashboard: DashboardSettings
    services: dict[str, ServiceConfig]
    polling: PollingConfig
    websocket: WebSocketConfig


_config: DashboardConfig | None = None


def load_config(config_path: str | Path) -> DashboardConfig:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    # Parse dashboard settings
    dashboard_raw = raw.get("dashboard", {})
    dashboard = DashboardSettings(
        host=dashboard_raw.get("host", "0.0.0.0"),
        port=dashboard_raw.get("port", 8080),
    )

    # Parse services
    services: dict[str, ServiceConfig] = {}
    for service_id, svc_raw in raw.get("services", {}).items():
        gateway_raw = svc_raw.get("gateway", {})
        wm_raw = svc_raw.get("worker_manager", {})
        endpoints_raw = svc_raw.get("endpoints", {})

        workers = [
            WorkerConfig(
                alias=w.get("alias", ""),
                name=w.get("name", ""),
                type=w.get("type", ""),
            )
            for w in svc_raw.get("workers", [])
        ]

        services[service_id] = ServiceConfig(
            id=service_id,
            name=svc_raw.get("name", service_id),
            description=svc_raw.get("description", ""),
            icon=svc_raw.get("icon", "server"),
            gateway=GatewayConfig(
                host=gateway_raw.get("host", "localhost"),
                port=gateway_raw.get("port", 8000),
            ),
            worker_manager=WorkerManagerConfig(
                host=wm_raw.get("host", "localhost"),
                port=wm_raw.get("port", 8100),
            ),
            endpoints=EndpointsConfig(
                health=endpoints_raw.get("health", "/healthz"),
                status=endpoints_raw.get("status", "/v1/system/status"),
                models=endpoints_raw.get("models", "/v1/models"),
                evict=endpoints_raw.get("evict", "/v1/system/evict/{alias}"),
            ),
            workers=workers,
        )

    # Parse polling settings
    polling_raw = raw.get("polling", {})
    polling = PollingConfig(
        health_interval_seconds=polling_raw.get("health_interval_seconds", 10),
        status_interval_seconds=polling_raw.get("status_interval_seconds", 5),
    )

    # Parse websocket settings
    ws_raw = raw.get("websocket", {})
    websocket = WebSocketConfig(
        heartbeat_interval_seconds=ws_raw.get("heartbeat_interval_seconds", 30),
    )

    return DashboardConfig(
        dashboard=dashboard,
        services=services,
        polling=polling,
        websocket=websocket,
    )


def get_config() -> DashboardConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        # Default config path
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        _config = load_config(config_path)
    return _config


def set_config(config: DashboardConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
