"""Configuration loader for Homelab GPU Orchestrator."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


# --- GPU Configuration ---

@dataclass
class GpuPoolConfig:
    total_gpus: int = 4
    gpu_ids: list[int] = field(default_factory=lambda: [0, 1, 2, 3])


@dataclass
class GpuRequirement:
    min_gpus: int = 1
    max_gpus: int = 1
    exclusive: bool = False


# --- Launch Configuration ---

@dataclass
class LaunchConfig:
    type: str  # "docker" or "process"
    port: int = 8000
    working_dir: Optional[str] = None
    command: Optional[list[str]] = None
    image: Optional[str] = None
    container_name: Optional[str] = None
    models_dir: Optional[str] = None
    model_preset: Optional[str] = None
    env: dict[str, str] = field(default_factory=dict)
    extra_args: Optional[str] = None


@dataclass
class HealthCheckConfig:
    endpoint: str = "/health"
    interval_sec: int = 5
    timeout_sec: int = 3
    startup_timeout_sec: int = 300


@dataclass
class ApiConfig:
    base_path: str = ""
    proxy_endpoints: list[str] = field(default_factory=list)


# --- Service Configuration ---

@dataclass
class ServiceConfig:
    id: str
    display_name: str
    description: str = ""
    icon: str = "server"
    gpu_requirement: GpuRequirement = field(default_factory=GpuRequirement)
    launch: LaunchConfig = field(default_factory=lambda: LaunchConfig(type="process"))
    health_check: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    idle_timeout_sec: int = 300
    api: ApiConfig = field(default_factory=ApiConfig)


# --- Queue Configuration ---

@dataclass
class QueueConfig:
    max_size: int = 100
    request_timeout_sec: int = 1800


# --- Dashboard & Global Settings ---

@dataclass
class DashboardSettings:
    host: str = "0.0.0.0"
    port: int = 4010


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
    gpu_pool: GpuPoolConfig
    services: dict[str, ServiceConfig]
    queue: QueueConfig
    polling: PollingConfig
    websocket: WebSocketConfig


# --- Config Loader ---

_config: DashboardConfig | None = None


def _parse_gpu_requirement(raw: dict[str, Any]) -> GpuRequirement:
    return GpuRequirement(
        min_gpus=raw.get("min_gpus", 1),
        max_gpus=raw.get("max_gpus", 1),
        exclusive=raw.get("exclusive", False),
    )


def _parse_launch_config(raw: dict[str, Any]) -> LaunchConfig:
    return LaunchConfig(
        type=raw.get("type", "process"),
        port=raw.get("port", 8000),
        working_dir=raw.get("working_dir"),
        command=raw.get("command"),
        image=raw.get("image"),
        container_name=raw.get("container_name"),
        models_dir=raw.get("models_dir"),
        model_preset=raw.get("model_preset"),
        env=raw.get("env", {}),
        extra_args=raw.get("extra_args"),
    )


def _parse_health_check(raw: dict[str, Any]) -> HealthCheckConfig:
    return HealthCheckConfig(
        endpoint=raw.get("endpoint", "/health"),
        interval_sec=raw.get("interval_sec", 5),
        timeout_sec=raw.get("timeout_sec", 3),
        startup_timeout_sec=raw.get("startup_timeout_sec", 300),
    )


def _parse_api_config(raw: dict[str, Any]) -> ApiConfig:
    return ApiConfig(
        base_path=raw.get("base_path", ""),
        proxy_endpoints=raw.get("proxy_endpoints", []),
    )


def load_config(config_path: str | Path) -> DashboardConfig:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    # Dashboard settings
    dashboard_raw = raw.get("dashboard", {})
    dashboard = DashboardSettings(
        host=dashboard_raw.get("host", "0.0.0.0"),
        port=dashboard_raw.get("port", 4010),
    )

    # GPU pool
    gpu_raw = raw.get("gpu_pool", {})
    gpu_pool = GpuPoolConfig(
        total_gpus=gpu_raw.get("total_gpus", 4),
        gpu_ids=gpu_raw.get("gpu_ids", [0, 1, 2, 3]),
    )

    # Services
    services: dict[str, ServiceConfig] = {}
    for service_id, svc_raw in raw.get("services", {}).items():
        gpu_req_raw = svc_raw.get("gpu_requirement", {})
        launch_raw = svc_raw.get("launch", {})
        hc_raw = svc_raw.get("health_check", {})
        api_raw = svc_raw.get("api", {})

        services[service_id] = ServiceConfig(
            id=service_id,
            display_name=svc_raw.get("display_name", service_id),
            description=svc_raw.get("description", ""),
            icon=svc_raw.get("icon", "server"),
            gpu_requirement=_parse_gpu_requirement(gpu_req_raw),
            launch=_parse_launch_config(launch_raw),
            health_check=_parse_health_check(hc_raw),
            idle_timeout_sec=svc_raw.get("idle_timeout_sec", 300),
            api=_parse_api_config(api_raw),
        )

    # Queue
    queue_raw = raw.get("queue", {})
    queue = QueueConfig(
        max_size=queue_raw.get("max_size", 100),
        request_timeout_sec=queue_raw.get("request_timeout_sec", 1800),
    )

    # Polling
    polling_raw = raw.get("polling", {})
    polling = PollingConfig(
        health_interval_seconds=polling_raw.get("health_interval_seconds", 10),
        status_interval_seconds=polling_raw.get("status_interval_seconds", 5),
    )

    # WebSocket
    ws_raw = raw.get("websocket", {})
    websocket = WebSocketConfig(
        heartbeat_interval_seconds=ws_raw.get("heartbeat_interval_seconds", 30),
    )

    return DashboardConfig(
        dashboard=dashboard,
        gpu_pool=gpu_pool,
        services=services,
        queue=queue,
        polling=polling,
        websocket=websocket,
    )


def get_config() -> DashboardConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        _config = load_config(config_path)
    return _config


def set_config(config: DashboardConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
