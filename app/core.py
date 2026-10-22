from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from app.agents import AGENTES_MAP, Agent, buscar_agente_por_mencao


@dataclass
class Roteamento:
    agente: Agent
    motivo: str
    modo: str


class CoreOrquestrador:
    def __init__(self) -> None:
        self.agentes_default = {
            "cumprimento": AGENTES_MAP["engenheiro"],
            "geral": AGENTES_MAP["engenheiro"],
        }

    def classificar(self, message: str, mode: str = "auto", agent_id: str | None = None) -> Roteamento:
        texto = message.strip()
        texto_lower = texto.lower()

        if mode == "expert" and agent_id and agent_id in AGENTES_MAP:
            agente = AGENTES_MAP[agent_id]
            return Roteamento(agente=agente, motivo="modo especialista selecionado manualmente", modo=mode)

        if texto_lower.startswith("/debate"):
            agente = AGENTES_MAP["conselho"]
            return Roteamento(agente=agente, motivo="comando explícito de debate detectado", modo="debate")

        mencionado = buscar_agente_por_mencao(texto)
        if mencionado and mencionado.id != "core":
            return Roteamento(
                agente=mencionado,
                motivo=f"menção direta ao agente {mencionado.nome}",
                modo="auto",
            )

        if any(s in texto_lower for s in ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"]):
            agente = self.agentes_default["cumprimento"]
            return Roteamento(agente=agente, motivo="cumprimento inicial, roteando para diagnóstico de contexto", modo="auto")

        if any(s in texto_lower for s in ["arquitetura", "ddd", "clean architecture", "hexagonal", "cqrs"]):
            agente = AGENTES_MAP["arquiteto"]
            return Roteamento(agente=agente, motivo="tema arquitetural identificado", modo="auto")

        if any(s in texto_lower for s in ["api", "banco", "sql", "postgres", "backend"]):
            agente = AGENTES_MAP["backend"]
            return Roteamento(agente=agente, motivo="tema de backend identificado", modo="auto")

        if any(s in texto_lower for s in ["segurança", "seguranca", "jwt", "oauth", "owasp"]):
            agente = AGENTES_MAP["seguranca"]
            return Roteamento(agente=agente, motivo="tema de segurança identificado", modo="auto")

        if any(s in texto_lower for s in ["teste", "qualidade", "cobertura", "tdd"]):
            agente = AGENTES_MAP["qualidade"]
            return Roteamento(agente=agente, motivo="tema de qualidade identificado", modo="auto")

        agente = self.agentes_default["geral"]
        return Roteamento(agente=agente, motivo="pergunta geral sem especialista explícito", modo="auto")

    def montar_contexto_memoria(self, resultados: List[Dict]) -> str:
        if not resultados:
            return "Sem contexto adicional de memória para esta mensagem."

        linhas = ["Contexto de memória recuperado:"]
        for item in resultados:
            metadata = item.get("metadata", {})
            tags = metadata.get("tags", "")
            titulo = metadata.get("titulo", "Conhecimento")
            texto = item.get("texto", "")[:400]
            linhas.append(f"- {titulo} | tags: {tags} | trecho: {texto}")
        return "\n".join(linhas)
