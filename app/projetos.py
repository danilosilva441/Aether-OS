from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional


class ProjetoStore:
    def __init__(self, db_path: str = "data/aether.db") -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    dominio TEXT DEFAULT '',
                    descricao TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    titulo TEXT DEFAULT 'Nova conversa',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    agent_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    titulo TEXT NOT NULL,
                    fonte TEXT NOT NULL,
                    resumo TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    agentes_destino TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )
                """
            )

    def listar_projetos(self) -> List[Dict[str, Any]]:
        with self.conn() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

    def criar_projeto(self, nome: str, dominio: str = "", descricao: str = "") -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        with self.conn() as conn:
            cur = conn.execute(
                "INSERT INTO projects (nome, dominio, descricao, created_at) VALUES (?, ?, ?, ?)",
                (nome, dominio, descricao, now),
            )
            project_id = cur.lastrowid
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row)

    def get_projeto(self, project_id: int) -> Optional[Dict[str, Any]]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row) if row else None

    def listar_conversas(self, project_id: int) -> List[Dict[str, Any]]:
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE project_id = ? ORDER BY id DESC", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def criar_conversa(self, project_id: int, titulo: str = "Nova conversa") -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        with self.conn() as conn:
            cur = conn.execute(
                "INSERT INTO conversations (project_id, titulo, created_at) VALUES (?, ?, ?)",
                (project_id, titulo, now),
            )
            cid = cur.lastrowid
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (cid,)).fetchone()
        return dict(row)

    def get_conversa(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        return dict(row) if row else None

    def atualizar_titulo_conversa(self, conversation_id: int, titulo: str) -> None:
        with self.conn() as conn:
            conn.execute("UPDATE conversations SET titulo = ? WHERE id = ?", (titulo[:80], conversation_id))

    def listar_mensagens(self, conversation_id: int) -> List[Dict[str, Any]]:
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC", (conversation_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def salvar_mensagem(
        self,
        conversation_id: int,
        role: str,
        content: str,
        agent_id: str | None = None,
    ) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        with self.conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, agent_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, agent_id, now),
            )
            mid = cur.lastrowid
            row = conn.execute("SELECT * FROM messages WHERE id = ?", (mid,)).fetchone()
        return dict(row)

    def salvar_knowledge(
        self,
        titulo: str,
        fonte: str,
        resumo: str,
        tags: List[str],
        agentes_destino: List[str],
        project_id: int | None = None,
    ) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        tags_str = ",".join(tags)
        agentes_str = ",".join(agentes_destino)
        with self.conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO knowledge (project_id, titulo, fonte, resumo, tags, agentes_destino, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, titulo, fonte, resumo, tags_str, agentes_str, now),
            )
            kid = cur.lastrowid
            row = conn.execute("SELECT * FROM knowledge WHERE id = ?", (kid,)).fetchone()
        return dict(row)

    def listar_knowledge(self, project_id: int | None = None) -> List[Dict[str, Any]]:
        with self.conn() as conn:
            if project_id is None:
                rows = conn.execute("SELECT * FROM knowledge ORDER BY id DESC").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM knowledge WHERE project_id = ? OR project_id IS NULL ORDER BY id DESC",
                    (project_id,),
                ).fetchall()
        return [dict(row) for row in rows]
