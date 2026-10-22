from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import fitz
import httpx

BASE_URL = os.getenv("AETHER_BASE_URL", "http://127.0.0.1:8000")


def assert_ok(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Aether OS - Documento de teste\nArquitetura backend com requisitos de segurança, qualidade e deploy local.",
    )
    doc.save(path)
    doc.close()


def parse_sse_events(response: httpx.Response) -> tuple[dict, str]:
    meta = {}
    final_msg = ""
    current_event = None
    for line in response.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="ignore")
        if line.startswith("event:"):
            current_event = line.replace("event:", "").strip()
        elif line.startswith("data:"):
            payload = json.loads(line.replace("data:", "").strip())
            if current_event == "meta":
                meta = payload
            elif current_event == "done":
                final_msg = payload.get("message", "")
    return meta, final_msg


def main() -> int:
    print(f"[smoke] Base URL: {BASE_URL}")
    with httpx.Client(timeout=60.0) as client:
        # health
        health = client.get(f"{BASE_URL}/api/health")
        assert_ok(health.status_code == 200, "health falhou")
        health_json = health.json()
        print("[ok] /api/health", health_json.get("llm_backend"), health_json.get("model"))

        # criar projeto
        p = client.post(
            f"{BASE_URL}/api/projects",
            json={
                "nome": "Projeto Smoke Test",
                "dominio": "chat multiagente",
                "descricao": "Validação automática local",
            },
        )
        assert_ok(p.status_code == 200, "criação de projeto falhou")
        projeto = p.json()
        print("[ok] /api/projects POST", projeto["id"])

        # criar conversa
        c = client.post(
            f"{BASE_URL}/api/conversations",
            json={"project_id": projeto["id"], "titulo": "Conversa de teste"},
        )
        assert_ok(c.status_code == 200, "criação de conversa falhou")
        conversa = c.json()
        print("[ok] /api/conversations POST", conversa["id"])

        # chat com streaming SSE
        with client.stream(
            "POST",
            f"{BASE_URL}/api/chat",
            json={
                "conversation_id": conversa["id"],
                "message": "Quais os próximos passos para estruturar o backend desse projeto?",
                "mode": "auto",
            },
        ) as resp:
            assert_ok(resp.status_code == 200, "chat SSE falhou")
            meta, final_msg = parse_sse_events(resp)
            assert_ok(bool(meta), "evento meta não recebido")
            assert_ok(len(final_msg) > 10, "mensagem final SSE vazia")
            print("[ok] /api/chat SSE", meta.get("agente", {}).get("nome", "sem agente"))

        # gerar e subir PDF
        with tempfile.TemporaryDirectory() as td:
            pdf_path = Path(td) / "conhecimento.pdf"
            make_pdf(pdf_path)
            with open(pdf_path, "rb") as f:
                up = client.post(
                    f"{BASE_URL}/api/upload",
                    files={"file": ("conhecimento.pdf", f, "application/pdf")},
                    data={"project_id": str(projeto["id"])},
                )
            assert_ok(up.status_code == 200, f"upload falhou: {up.text}")
            up_json = up.json()
            assert_ok("tags" in up_json and len(up_json["tags"]) > 0, "upload sem tags")
            print("[ok] /api/upload", up_json["tags"])

        # knowledge
        k = client.get(f"{BASE_URL}/api/knowledge", params={"project_id": projeto["id"]})
        assert_ok(k.status_code == 200, "list knowledge falhou")
        k_json = k.json()
        assert_ok(len(k_json) >= 1, "knowledge vazio")
        print("[ok] /api/knowledge", len(k_json))

        # debate
        d = client.post(
            f"{BASE_URL}/api/debate",
            json={
                "conversation_id": conversa["id"],
                "question": "Vale manter monólito modular ou ir para microserviços neste estágio inicial?",
            },
        )
        assert_ok(d.status_code == 200, f"debate falhou: {d.text}")
        d_json = d.json()
        assert_ok(len(d_json.get("especialistas", [])) == 4, "debate não retornou 4 especialistas")
        assert_ok(len(d_json.get("dossie", "")) > 30, "dossiê vazio")
        print("[ok] /api/debate especialistas=4")

    print("\n✅ Smoke test concluído com sucesso.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\n❌ Smoke test falhou: {exc}", file=sys.stderr)
        raise
