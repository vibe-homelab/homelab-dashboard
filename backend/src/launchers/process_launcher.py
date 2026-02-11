"""Process-based service launcher for Image, Voice STT, Voice TTS."""
from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import Any

from ..core.config import ServiceConfig
from .base import ServiceLauncher

logger = logging.getLogger(__name__)


class ProcessLauncher(ServiceLauncher):
    """Launch a service as a subprocess with CUDA_VISIBLE_DEVICES."""

    def __init__(self, config: ServiceConfig) -> None:
        self._config = config
        self._process: asyncio.subprocess.Process | None = None

    async def start(self, gpu_ids: list[int], port: int) -> dict[str, Any]:
        lc = self._config.launch
        cuda_devices = ",".join(str(g) for g in gpu_ids)

        env = os.environ.copy()
        env.update(lc.env)
        env["CUDA_VISIBLE_DEVICES"] = cuda_devices
        env["NUM_GPUS_TO_USE"] = str(len(gpu_ids))

        if not lc.command:
            raise ValueError(f"No command configured for service {self._config.id}")

        cmd = list(lc.command) + ["--port", str(port)]
        if lc.extra_args:
            cmd.extend(lc.extra_args.split())

        logger.info(
            "Starting %s: %s (CUDA=%s, port=%d)",
            self._config.id, " ".join(cmd), cuda_devices, port,
        )
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=lc.working_dir,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        return {"pid": self._process.pid}

    async def stop(self) -> None:
        if self._process and self._process.returncode is None:
            logger.info("Stopping %s (pid=%d)", self._config.id, self._process.pid)
            try:
                self._process.send_signal(signal.SIGTERM)
                await asyncio.wait_for(self._process.wait(), timeout=15)
            except asyncio.TimeoutError:
                logger.warning("SIGTERM timeout for %s, sending SIGKILL", self._config.id)
                self._process.kill()
                await self._process.wait()
        self._process = None

    async def is_alive(self) -> bool:
        return self._process is not None and self._process.returncode is None
