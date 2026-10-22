from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agents import AGENTES_MAP, listar_agentes_publico
from app.core import CoreOrquestrador
from app.curador import CuradorConhecimento
from app.llm import LLMClient
from app.memoria import MemoriaVetorial
from app.projetos import ProjetoStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aether")

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Aether OS v0.1", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = LLMClient()
memoria = MemoriaVetorial(persist_dir=str(BASE_DIR / "data" / "chroma"))
projetos = ProjetoStore(db_path=str(BASE_DIR / "data" / "aether.db"))
core = CoreOrquestrador()
curador = CuradorConhecimento(llm=llm)


class ProjectCreate(BaseModel):
    nome: str
    dominio: str = ""
    descricao: str = ""


class ConversationCreate(BaseModel):
    project_id: int
    titulo: str = "Nova conversa"


class ChatPayload(BaseModel):
    conversation_id: int
    message: str = Field(min_length=1)
    mode: Literal["auto", "expert"] = "auto"
    agent_id: Optional[str] = None


class DebatePayload(BaseModel):
    conversation_id: int
    question: str = Field(min_length=1)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "llm_backend": await llm.backend_ativo(),
        "model": llm.model,
        "agentes": listar_agentes_publico(),
    }


@app.get("/api/projects")
def list_projects() -> list[dict]:
    return projetos.listar_projetos()


@app.post("/api/projects")
def create_project(payload: ProjectCreate) -> dict:
    return projetos.criar_projeto(nome=payload.nome, dominio=payload.dominio, descricao=payload.descricao)


@app.get("/api/conversations")
def list_conversations(project_id: int) -> list[dict]:
    if not projetos.get_projeto(project_id):
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    return projetos.listar_conversas(project_id)


@app.post("/api/conversations")
def create_conversation(payload: ConversationCreate) -> dict:
    if not projetos.get_projeto(payload.project_id):
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    return projetos.criar_conversa(project_id=payload.project_id, titulo=payload.titulo)


@app.get("/api/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int) -> list[dict]:
    if not projetos.get_conversa(conversation_id):
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return projetos.listar_mensagens(conversation_id)


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/chat")
async def chat(payload: ChatPayload) -> StreamingResponse:
    conversa = projetos.get_conversa(payload.conversation_id)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")

    projeto = projetos.get_projeto(conversa["project_id"])
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto vinculado não encontrado.")

    route = core.classificar(payload.message, mode=payload.mode, agent_id=payload.agent_id)

    projetos.salvar_mensagem(
        conversation_id=payload.conversation_id,
        role="user",
        content=payload.message,
        agent_id=None,
    )

    historico = projetos.listar_mensagens(payload.conversation_id)
    mem_hits = memoria.buscar(payload.message, top_k=4)
    contexto_memoria = core.montar_contexto_memoria(mem_hits)

    if len(historico) == 1:
        projetos.atualizar_titulo_conversa(payload.conversation_id, payload.message.strip()[:60])

    prompt_sistema = (
        f"{route.agente.system_prompt}\n\n"
        "Contexto do projeto ativo:\n"
        f"- Nome: {projeto['nome']}\n"
        f"- Domínio: {projeto['dominio']}\n"
        f"- Descrição: {projeto['descricao']}\n\n"
        f"{contexto_memoria}\n\n"
        "Responda em português do Brasil, de forma prática e objetiva."
    )

    mensagens_llm = [
        {"role": "user", "content": payload.message},
    ]

    async def event_generator() -> AsyncGenerator[str, None]:
        meta = {
            "agente": {
                "id": route.agente.id,
                "nome": route.agente.nome,
                "emoji": route.agente.emoji,
            },
            "roteamento": f"roteado para: {route.agente.nome} — motivo: {route.motivo}",
            "timestamp": datetime.utcnow().isoformat(),
        }
        yield sse_event("meta", meta)

        partes: list[str] = []
        async for chunk in llm.stream_chat(messages=mensagens_llm, system_prompt=prompt_sistema):
            partes.append(chunk)
            yield sse_event("token", {"text": chunk})

        final_text = "".join(partes).strip()
        if not final_text:
            final_text = "Não consegui gerar uma resposta agora. Tente novamente em instantes."

        projetos.salvar_mensagem(
            conversation_id=payload.conversation_id,
            role="assistant",
            content=final_text,
            agent_id=route.agente.id,
        )

        yield sse_event("done", {"message": final_text})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    project_id: Optional[int] = Form(default=None),
) -> dict:
    if project_id is not None and not projetos.get_projeto(project_id):
        raise HTTPException(status_code=404, detail="Projeto não encontrado para vincular o conhecimento.")

    try:
        content = await file.read()
        texto = curador.extrair_texto(file.filename or "arquivo", content)
        if not texto.strip():
            raise ValueError("Não foi possível extrair conteúdo de texto do arquivo.")

        resumo, tags = await curador.resumir_e_taguear(texto)
        agentes_destino = curador.distribuir_agentes(tags)

        row = projetos.salvar_knowledge(
            titulo=file.filename or "documento",
            fonte=file.filename or "upload",
            resumo=resumo,
            tags=tags,
            agentes_destino=agentes_destino,
            project_id=project_id,
        )

        memoria.armazenar(
            texto=texto[:8000],
            metadata={
                "titulo": row["titulo"],
                "tags": row["tags"],
                "project_id": row["project_id"],
                "knowledge_id": row["id"],
            },
            documento_id=f"knowledge-{row['id']}",
        )

        return {
            "id": row["id"],
            "titulo": row["titulo"],
            "resumo": resumo,
            "tags": tags,
            "agentes_destino": agentes_destino,
            "mensagem": "Conhecimento processado e distribuído com sucesso.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Falha ao processar upload")
        raise HTTPException(
            status_code=500,
            detail="Falha ao processar upload. Verifique o formato do arquivo e tente novamente.",
        ) from exc


@app.get("/api/knowledge")
def list_knowledge(project_id: Optional[int] = None) -> list[dict]:
    return projetos.listar_knowledge(project_id=project_id)


@app.post("/api/debate")
async def debate(payload: DebatePayload) -> dict:
    conversa = projetos.get_conversa(payload.conversation_id)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")

    projeto = projetos.get_projeto(conversa["project_id"])
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    especialistas = ["arquiteto", "engenheiro", "backend", "seguranca"]
    respostas = []

    for agent_id in especialistas:
        agente = AGENTES_MAP[agent_id]
        prompt = (
            f"{agente.system_prompt}\n"
            f"Projeto: {projeto['nome']} ({projeto['dominio']})\n"
            "Responda em até 8 linhas, com foco em riscos e recomendações práticas."
        )
        texto = await llm.complete_chat(
            messages=[{"role": "user", "content": payload.question}],
            system_prompt=prompt,
        )
        respostas.append(
            {
                "agent_id": agente.id,
                "agente": f"{agente.emoji} {agente.nome}",
                "resposta": texto.strip(),
            }
        )

    sintese_prompt = (
        "Você é o Core do Conselho Técnico. Produza um dossiê em português com as seções:\n"
        "1) Concordâncias\n2) Divergências\n3) Riscos\n4) Trade-offs\n5) Recomendação Final\n"
        "Inclua ao final: 'A decisão final permanece com o usuário.'\n"
        f"Pergunta: {payload.question}\n"
        f"Contribuições: {json.dumps(respostas, ensure_ascii=False)}"
    )
    dossier = await llm.complete_chat(messages=[{"role": "user", "content": sintese_prompt}])

    projetos.salvar_mensagem(payload.conversation_id, "user", f"[DEBATE] {payload.question}")
    projetos.salvar_mensagem(payload.conversation_id, "assistant", dossier, "conselho")

    return {
        "question": payload.question,
        "especialistas": respostas,
        "dossie": dossier,
        "nota": "A decisão final permanece com o usuário.",
    }


app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR)), name="assets")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.exception_handler(HTTPException)
async def http_exc_handler(_, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("AETHER_HOST", "0.0.0.0")
    port = int(os.getenv("AETHER_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)
