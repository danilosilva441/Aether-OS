from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, List

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self) -> None:
        self.backend = os.getenv("AETHER_LLM_BACKEND", "ollama").strip().lower()
        self.model = os.getenv("AETHER_MODEL", "qwen2.5:3b")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")

    async def _ollama_disponivel(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.ollama_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def backend_ativo(self) -> str:
        if self.backend == "ollama":
            if await self._ollama_disponivel():
                return "ollama"
            logger.warning("Ollama indisponível. Fallback automático para backend mock.")
            return "mock"
        return "mock"

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        backend = await self.backend_ativo()
        if backend == "ollama":
            async for chunk in self._stream_ollama(messages, system_prompt, temperature):
                yield chunk
            return

        async for chunk in self._stream_mock(messages, system_prompt):
            yield chunk

    async def complete_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str | None = None,
    ) -> str:
        partes: List[str] = []
        async for chunk in self.stream_chat(messages=messages, system_prompt=system_prompt):
            partes.append(chunk)
        return "".join(partes).strip()

    async def _stream_ollama(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str | None,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        payload_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "stream": True,
            "options": {"temperature": temperature},
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{self.ollama_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    msg = data.get("message", {}).get("content", "")
                    if msg:
                        yield msg

    async def _stream_mock(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str | None,
    ) -> AsyncGenerator[str, None]:
        user_text = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_text = msg.get("content", "")
                break

        contexto = ""
        if system_prompt:
            if "Arquiteto" in system_prompt or "arquiteto" in system_prompt:
                contexto = "Como Arquiteto, "
            elif "Segurança" in system_prompt or "segurança" in system_prompt.lower():
                contexto = "Sob a ótica de Segurança, "
            elif "Engenheiro" in system_prompt:
                contexto = "Como Engenheiro, "
            elif "Backend" in system_prompt:
                contexto = "Como Backend, "

        resposta = (
            f"{contexto}estou em modo de demonstração local (mock). "
            f"Recebi sua mensagem: '{user_text[:220]}'. "
            "Sugestão inicial: validar requisitos, dividir em incrementos pequenos e registrar decisões no projeto."
        )

        for token in resposta.split(" "):
            await asyncio.sleep(0.02)
            yield token + " "
