"""Docker-based service launcher for vLLM LLM service."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..core.config import ServiceConfig
from .base import ServiceLauncher

logger = logging.getLogger(__name__)

MODEL_PRESETS = {
    "glm-4.7-awq": "/models/GLM-4.7-AWQ",
    "qwen3-235b-awq": "/models/Qwen3-235B-A22B-Instruct-2507-AWQ",
    "qwen3-235b-fp4": "/models/Qwen3-235B-A22B-Instruct-2507-FP4",
    "gpt-oss-120b": "/models/gpt-oss-120b",
}


class DockerLauncher(ServiceLauncher):
    """Launch vLLM as a Docker container."""

    def __init__(self, config: ServiceConfig) -> None:
        self._config = config
        self._container_name = config.launch.container_name or f"orchestrator-{config.id}"
        self._container_id: str | None = None

    async def start(self, gpu_ids: list[int], port: int) -> dict[str, Any]:
        lc = self._config.launch
        cuda_devices = ",".join(str(g) for g in gpu_ids)
        tp_size = len(gpu_ids)

        preset = lc.model_preset or "gpt-oss-120b"
        model_path = MODEL_PRESETS.get(preset, f"/models/{preset}")

        cmd = [
            "docker", "run", "-d",
            "--name", self._container_name,
            "--gpus", "all",
            "--ipc=host",
            "-v", f"{lc.models_dir}:/models",
            "-p", f"{port}:8000",
            "-e", f"CUDA_VISIBLE_DEVICES={cuda_devices}",
        ]

        for key, val in lc.env.items():
            cmd.extend(["-e", f"{key}={val}"])

        cmd.extend([lc.image or "vllm/vllm-openai:latest"])
        cmd.extend([
            "--host", "0.0.0.0",
            "--port", "8000",
            "--model", model_path,
            "--tensor-parallel-size", str(tp_size),
        ])

        if lc.extra_args:
            cmd.extend(lc.extra_args.split())

        # Remove existing container if present
        await self._run_cmd(["docker", "rm", "-f", self._container_name])

        logger.info("Starting LLM container: %s", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"Docker run failed (rc={proc.returncode}): {stderr.decode().strip()}"
            )

        self._container_id = stdout.decode().strip()[:12]
        return {"container_id": self._container_id}

    async def stop(self) -> None:
        logger.info("Stopping container %s", self._container_name)
        await self._run_cmd(["docker", "stop", "-t", "30", self._container_name])
        await self._run_cmd(["docker", "rm", "-f", self._container_name])
        self._container_id = None

    async def is_alive(self) -> bool:
        proc = await asyncio.create_subprocess_exec(
            "docker", "inspect", "-f", "{{.State.Running}}", self._container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip() == "true"

    async def _run_cmd(self, cmd: list[str]) -> None:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
