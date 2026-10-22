# Aether OS v0.1 (Local)

Aether OS é um sistema **multi-agente de engenharia de software** para rodar localmente, com foco em colaboração entre especialistas de IA e decisão humana.

> **Regra de ouro:** *"Um agente, uma responsabilidade. O conhecimento flui pelo Curador, a decisão pelo Core, e a execução pelo Especialista."*

Este v0.1 é um **Walking Skeleton funcional** para notebook caseiro (i3-6006U, 16GB RAM), com backend FastAPI, frontend web estático, memória vetorial local e modo debate.

---

### O que o v0.1 cobre

- Core (orquestrador) com roteamento por intenção e menção de agente.
- Curador do Conhecimento com upload de PDF/TXT/MD.
- Memória vetorial local (ChromaDB persistente).
- Gestão de projetos e conversas (SQLite).
- Chat web com streaming token a token (SSE).
- Modo especialista e Modo Debate (Conselho Técnico mínimo).
- Backend de LLM com `ollama` + `mock` (fallback automático para mock se Ollama estiver offline).

---

### Arquitetura conceitual (ASCII)

```text
Usuário
  |
  v
Core (Orquestrador) 🧠
  |------------------------------|
  |                              |
  v                              v
Curador 📚                   Gestão de Projetos 📂
  |                              |
  v                              v
Engenheiro 👷  <-->  Arquiteto 🏛
  |                    |
  |                    |-----------------------------|
  v                    v                             v
Backend ⚙          Frontend 🎨                   Infra 🚀
  |                    |                             |
  |--------------------|-------------|---------------|
                                   v
                              Segurança 🔒
                                   |
                                   v
                              Qualidade 🧪
                                   |
                                   v
                              Professor 👨🏫
                                   |
                                   v
                               Memória 🧠
                                   |
                                   v
                             Pesquisador 🔍

Modo Debate: Conselho Técnico 🤝 (Arquiteto + Engenheiro + Backend + Segurança)
```

---

### Lista de agentes registrados (14)

0. Core (Orquestrador) 🧠
1. Curador do Conhecimento 📚
2. Engenheiro de Software 👷
3. Arquiteto 🏛
4. Desenvolvedor Backend ⚙
5. Desenvolvedor Frontend 🎨
6. Especialista em Segurança 🔒
7. Especialista em Infraestrutura 🚀
8. Especialista em Qualidade 🧪
9. Professor 👨🏫
10. Memória 🧠
11. Pesquisador 🔍
12. Conselho Técnico (Modo Debate) 🤝
13. Gestão de Projetos 📂
14. Plataforma de Evolução 🌱

Os prompts de sistema estão em `app/agents.py` (PT-BR, com missão, responsabilidades e limites).

---

### Roadmap em 3 fases

#### Fase 1 — Fundação (Walking Skeleton)
- Core + Curador + Memória + Gestão de Projetos
- Chat + streaming SSE
- Backend mock/ollama
- Debate mínimo

✅ **Coberto pelo v0.1**

#### Fase 2 — Expansão Técnica
- Melhor roteamento por intenção
- Mais ferramentas por especialista
- Melhor recuperação semântica por projeto
- Observabilidade e métricas de custo/latência

#### Fase 3 — Evolução da Plataforma
- Registro de novos agentes plugáveis por eventos
- Fluxos avançados multiagente
- Assistência contínua por projeto com políticas

---

### Stack técnica

- **Backend:** Python 3.10+, FastAPI, Uvicorn
- **LLM:** Ollama (produção local) ou Mock (teste/demonstração)
- **Memória vetorial:** ChromaDB local (`data/chroma`)
- **Persistência de domínio:** SQLite (`data/aether.db`)
- **UI:** HTML/CSS/JS vanilla (sem build, sem CDN)

---

### Estrutura do projeto

```text
aether_os/
├── app/
│   ├── agents.py          # Registro de agentes + prompts
│   ├── core.py            # Orquestrador e roteamento
│   ├── llm.py             # Cliente Ollama + mock + fallback
│   ├── memoria.py         # ChromaDB persistente + busca semântica
│   ├── curador.py         # Pipeline de upload/resumo/tags/distribuição
│   └── projetos.py        # SQLite: projects, conversations, messages, knowledge
├── frontend/
│   ├── index.html         # Layout geral
│   ├── styles.css         # Tema dark responsivo
│   └── app.js             # Lógica do chat, SSE, upload e debate
├── scripts/
│   └── smoke_test.py      # Teste automatizado de APIs e fluxo principal
├── data/                  # SQLite + Chroma persistidos localmente
├── main.py                # App FastAPI (API + estáticos)
├── requirements.txt
├── .env.example
├── run.sh
└── run.bat
```

---

### Épicos → arquivos

- **Core e roteamento** → `app/core.py`, `main.py` (`/api/chat`)
- **Curadoria e ingestão** → `app/curador.py`, `main.py` (`/api/upload`)
- **Memória vetorial** → `app/memoria.py`
- **Gestão de projetos e conversas** → `app/projetos.py`, `main.py` (`/api/projects`, `/api/conversations`)
- **Conselho técnico** → `main.py` (`/api/debate`)
- **UX web local** → `frontend/*`

---

### Instalação (Linux)

1. Instale Python 3.10+
2. (Opcional produção) Instale Ollama: https://ollama.com
3. Faça pull do modelo recomendado:
   ```bash
   ollama pull qwen2.5:3b
   ```
4. Crie e ative venv:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
5. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
6. Configure ambiente:
   ```bash
   cp .env.example .env
   ```
7. Rode:
   ```bash
   ./run.sh
   ```

---

### Instalação (Windows)

1. Instale Python 3.10+
2. (Opcional produção) Instale Ollama: https://ollama.com
3. Pull do modelo:
   ```bat
   ollama pull qwen2.5:3b
   ```
4. Ambiente virtual:
   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   ```
5. Dependências:
   ```bat
   pip install -r requirements.txt
   ```
6. Configure `.env` com base em `.env.example`
7. Rode:
   ```bat
   run.bat
   ```

---

### Configuração (.env)

```env
AETHER_LLM_BACKEND=mock
AETHER_MODEL=qwen2.5:3b
OLLAMA_URL=http://localhost:11434
AETHER_HOST=0.0.0.0
AETHER_PORT=8000
```

- `AETHER_LLM_BACKEND=ollama` para produção local com modelo real.
- Se `ollama` estiver inacessível, o sistema faz fallback automático para `mock` com aviso em log.

---

### Acesso pela rede local (LAN)

O servidor escuta em `0.0.0.0:8000`.

- No notebook-servidor: inicie o app.
- Em outro dispositivo na mesma rede: acesse `http://IP_do_notebook:8000`.

Descobrir IP (Linux):
```bash
hostname -I
```

Descobrir IP (Windows):
```bat
ipconfig
```

#### Firewall
- **Windows Firewall:** liberar porta TCP 8000 para rede privada.
- **Linux (ufw):**
  ```bash
  sudo ufw allow 8000/tcp
  ```

Dica: configurar reserva DHCP/IP fixo no roteador para não mudar o endereço.

---

### Notas honestas de hardware (i3-6006U / 16GB)

- Recomendado: modelos **1.5B a 4B** quantizados.
- Padrão sugerido: **qwen2.5:3b** (bom para PT-BR).
- Modelos 7B+ em CPU antiga podem cair para ~1–2 tokens/s.
- RAM estimada:
  - Modelo: ~2–4 GB
  - Aplicação + banco + memória vetorial: ~1–2 GB
  - Sistema operacional + margem: restante
- Para melhor fluidez: feche apps pesados e evite múltiplas inferências paralelas.

---

### API principal

- `GET /api/health`
- `GET/POST /api/projects`
- `GET/POST /api/conversations`
- `GET /api/conversations/{id}/messages`
- `POST /api/chat` (SSE)
- `POST /api/upload` (PDF/TXT/MD)
- `GET /api/knowledge`
- `POST /api/debate`

---

### Plataforma de Evolução (como adicionar novos agentes)

1. Adicione o agente em `app/agents.py` (id, nome, emoji, papel e prompt).
2. Atualize aliases/roteamento em `buscar_agente_por_mencao` e `app/core.py`.
3. (Evolução futura) registrar eventos:
   - `AgentRegistrationSigned`
   - `AgentRegistrationPublished`
4. Opcional: incluir tags de distribuição no Curador (`app/curador.py`).

---

### Script de smoke test

Com o servidor rodando em `http://127.0.0.1:8000`:

```bash
python scripts/smoke_test.py
```

O script valida:
- Health
- Criação de projeto e conversa
- Chat com streaming SSE
- Upload de PDF gerado em tempo de execução
- Listagem de conhecimentos
- Debate com 4 especialistas

---

### Limitações conhecidas do v0.1

- Roteamento ainda heurístico (palavras-chave + menções diretas).
- Sem autenticação de usuários (foco LAN local).
- Curadoria de tags usa LLM + heurística, pode precisar ajustes finos.
- Debates em backend mock são simulados (úteis para teste de fluxo/UI).
