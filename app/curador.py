from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Dict, List, Tuple

import fitz

from app.llm import LLMClient

TAG_AGENT_MAP = {
    "#backend": ["backend", "arquiteto", "qualidade", "seguranca"],
    "#frontend": ["frontend", "arquiteto", "qualidade"],
    "#arquitetura": ["arquiteto", "backend", "infra"],
    "#seguranca": ["seguranca", "backend", "infra"],
    "#qualidade": ["qualidade", "engenheiro", "backend", "frontend"],
    "#infra": ["infra", "backend", "seguranca"],
    "#gestao": ["engenheiro", "gestao_projetos"],
}


class CuradorConhecimento:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def extrair_texto(self, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            return self._extrair_pdf(content)
        if suffix in {".txt", ".md"}:
            return content.decode("utf-8", errors="ignore")
        raise ValueError("Formato não suportado. Envie PDF, TXT ou MD.")

    def _extrair_pdf(self, content: bytes) -> str:
        doc = fitz.open(stream=content, filetype="pdf")
        partes: List[str] = []
        for page in doc:
            partes.append(page.get_text("text"))
        return "\n".join(partes)

    async def resumir_e_taguear(self, texto: str) -> Tuple[str, List[str]]:
        texto_base = texto[:3500]
        prompt = (
            "Você é Curador do Conhecimento. Gere resposta em JSON com campos 'resumo' e 'tags'. "
            "As tags devem ser lista com #backend, #frontend, #arquitetura, #seguranca, #qualidade, #infra, #gestao quando aplicável. "
            "Texto:\n"
            f"{texto_base}"
        )
        resp = await self.llm.complete_chat(messages=[{"role": "user", "content": prompt}])

        resumo = self._extrair_resumo(resp)
        tags = self._extrair_tags(resp, texto_base)
        return resumo, tags

    def _extrair_resumo(self, resposta: str) -> str:
        if "resumo" in resposta.lower():
            m = re.search(r"resumo[^:]*:\s*(.+)", resposta, flags=re.IGNORECASE | re.DOTALL)
            if m:
                return m.group(1).strip()[:900]
        return (resposta.strip() or "Resumo não disponível.")[:900]

    def _extrair_tags(self, resposta: str, texto: str) -> List[str]:
        tags = sorted(set(re.findall(r"#\w+", resposta.lower())))
        if tags:
            return tags

        base = texto.lower()
        heuristicas = []
        if any(t in base for t in ["api", "banco", "sql", "backend", "c#", "java"]):
            heuristicas.append("#backend")
        if any(t in base for t in ["css", "html", "frontend", "ux", "ui", "vue"]):
            heuristicas.append("#frontend")
        if any(t in base for t in ["arquitetura", "ddd", "clean", "hexagonal", "cqrs"]):
            heuristicas.append("#arquitetura")
        if any(t in base for t in ["segurança", "seguranca", "owasp", "jwt", "oauth"]):
            heuristicas.append("#seguranca")
        if any(t in base for t in ["teste", "qa", "qualidade", "tdd"]):
            heuristicas.append("#qualidade")
        if any(t in base for t in ["docker", "kubernetes", "deploy", "linux", "nginx"]):
            heuristicas.append("#infra")
        if any(t in base for t in ["scrum", "kanban", "requisito", "backlog", "história"]):
            heuristicas.append("#gestao")

        return heuristicas or ["#gestao"]

    def distribuir_agentes(self, tags: List[str]) -> List[str]:
        agentes: List[str] = []
        for tag in tags:
            agentes.extend(TAG_AGENT_MAP.get(tag, []))
        return sorted(set(agentes))
