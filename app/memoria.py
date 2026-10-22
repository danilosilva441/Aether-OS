from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, List

import chromadb

logger = logging.getLogger(__name__)


class MemoriaVetorial:
    def __init__(self, persist_dir: str = "data/chroma") -> None:
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        os.environ.setdefault("ANONYMIZED_TELEMETRY", "FALSE")
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(name="conhecimento")

    def armazenar(
        self,
        texto: str,
        metadata: Dict[str, Any],
        documento_id: str | None = None,
    ) -> str:
        did = documento_id or str(uuid.uuid4())
        self.collection.add(
            ids=[did],
            documents=[texto],
            metadatas=[metadata],
        )
        return did

    def buscar(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        if not query.strip():
            return []

        try:
            result = self.collection.query(query_texts=[query], n_results=top_k)
        except Exception as exc:
            logger.warning("Falha na busca semântica: %s", exc)
            return []

        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0] if "distances" in result else [None] * len(docs)

        itens: List[Dict[str, Any]] = []
        for idx, doc in enumerate(docs):
            itens.append(
                {
                    "texto": doc,
                    "metadata": metas[idx] if idx < len(metas) else {},
                    "distancia": dists[idx] if idx < len(dists) else None,
                }
            )
        return itens
