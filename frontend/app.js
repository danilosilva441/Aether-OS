const state = {
  projects: [],
  currentProjectId: null,
  conversations: [],
  currentConversationId: null,
  agents: [],
};

const el = {
  projectSelect: document.getElementById('projectSelect'),
  newProjectBtn: document.getElementById('newProjectBtn'),
  conversationList: document.getElementById('conversationList'),
  newConversationBtn: document.getElementById('newConversationBtn'),
  knowledgeList: document.getElementById('knowledgeList'),
  chatArea: document.getElementById('chatArea'),
  conversationTitle: document.getElementById('conversationTitle'),
  statusLine: document.getElementById('statusLine'),
  backendBadge: document.getElementById('backendBadge'),
  modeSelect: document.getElementById('modeSelect'),
  agentSelect: document.getElementById('agentSelect'),
  messageInput: document.getElementById('messageInput'),
  sendBtn: document.getElementById('sendBtn'),
  debateBtn: document.getElementById('debateBtn'),
  uploadInput: document.getElementById('uploadInput'),
};

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleString('pt-BR');
  } catch {
    return iso;
  }
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || 'Erro inesperado na API.');
  }
  return data;
}

function renderProjects() {
  el.projectSelect.innerHTML = '';
  state.projects.forEach((p) => {
    const opt = document.createElement('option');
    opt.value = String(p.id);
    opt.textContent = `${p.nome}${p.dominio ? ` (${p.dominio})` : ''}`;
    el.projectSelect.appendChild(opt);
  });

  if (state.currentProjectId) {
    el.projectSelect.value = String(state.currentProjectId);
  }
}

function renderConversations() {
  el.conversationList.innerHTML = '';
  state.conversations.forEach((c) => {
    const li = document.createElement('li');
    li.innerHTML = `<strong>${c.titulo}</strong><small>${fmtDate(c.created_at)}</small>`;
    li.onclick = async () => {
      state.currentConversationId = c.id;
      await loadMessages();
    };
    el.conversationList.appendChild(li);
  });
}

function addMessage(role, content, agentName = 'Usuário', timestamp = new Date().toISOString()) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.innerHTML = `<div class="meta">${agentName} • ${fmtDate(timestamp)}</div><div class="body"></div>`;
  div.querySelector('.body').textContent = content;
  el.chatArea.appendChild(div);
  el.chatArea.scrollTop = el.chatArea.scrollHeight;
  return div;
}

async function loadHealth() {
  const health = await api('/api/health');
  state.agents = health.agentes || [];
  el.backendBadge.textContent = `backend: ${health.llm_backend} | modelo: ${health.model}`;
  el.agentSelect.innerHTML = '';
  state.agents
    .filter((a) => !['core', 'conselho', 'memoria', 'plataforma_evolucao'].includes(a.id))
    .forEach((a) => {
      const opt = document.createElement('option');
      opt.value = a.id;
      opt.textContent = `${a.emoji} ${a.nome}`;
      el.agentSelect.appendChild(opt);
    });
}

async function loadProjects() {
  state.projects = await api('/api/projects');
  if (!state.projects.length) {
    const created = await api('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nome: 'Projeto Inicial Aether',
        dominio: 'engenharia de software',
        descricao: 'Projeto padrão criado automaticamente.',
      }),
    });
    state.projects = [created];
  }
  state.currentProjectId = state.projects[0].id;
  renderProjects();
  await loadConversations();
  await loadKnowledge();
}

async function loadConversations() {
  if (!state.currentProjectId) return;
  state.conversations = await api(`/api/conversations?project_id=${state.currentProjectId}`);
  renderConversations();
  if (state.conversations.length && !state.currentConversationId) {
    state.currentConversationId = state.conversations[0].id;
    await loadMessages();
  }
}

async function loadMessages() {
  if (!state.currentConversationId) return;
  const msgs = await api(`/api/conversations/${state.currentConversationId}/messages`);
  el.chatArea.innerHTML = '';
  msgs.forEach((m) => {
    const role = m.role === 'user' ? 'user' : 'assistant';
    const agentInfo = state.agents.find((a) => a.id === m.agent_id);
    const label = role === 'user' ? 'Você' : (agentInfo ? `${agentInfo.emoji} ${agentInfo.nome}` : 'Agente');
    addMessage(role, m.content, label, m.created_at);
  });

  const conv = state.conversations.find((c) => c.id === state.currentConversationId);
  if (conv) {
    el.conversationTitle.textContent = conv.titulo;
  }
}

async function loadKnowledge() {
  if (!state.currentProjectId) return;
  const items = await api(`/api/knowledge?project_id=${state.currentProjectId}`);
  el.knowledgeList.innerHTML = '';
  items.slice(0, 20).forEach((k) => {
    const li = document.createElement('li');
    li.innerHTML = `<strong>${k.titulo}</strong><small>${k.tags}</small>`;
    el.knowledgeList.appendChild(li);
  });
}

async function createConversation() {
  if (!state.currentProjectId) return;
  const conv = await api('/api/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: state.currentProjectId, titulo: 'Nova conversa' }),
  });
  state.currentConversationId = conv.id;
  await loadConversations();
  await loadMessages();
}

async function sendMessage() {
  const text = el.messageInput.value.trim();
  if (!text) return;
  if (!state.currentConversationId) {
    await createConversation();
  }

  addMessage('user', text, 'Você');
  el.messageInput.value = '';
  el.statusLine.textContent = 'Aether está processando sua mensagem...';

  const assistantDiv = addMessage('assistant', '', 'Aether');
  const body = assistantDiv.querySelector('.body');
  const meta = assistantDiv.querySelector('.meta');

  const payload = {
    conversation_id: state.currentConversationId,
    message: text,
    mode: el.modeSelect.value,
    agent_id: el.modeSelect.value === 'expert' ? el.agentSelect.value : null,
  };

  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok || !response.body) {
    const err = await response.json().catch(() => ({}));
    body.textContent = err.error || 'Falha ao enviar mensagem.';
    el.statusLine.textContent = 'Erro ao processar mensagem.';
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() || '';

    for (const rawEvent of events) {
      let eventType = 'message';
      let dataText = '{}';
      const lines = rawEvent.split('\n');
      for (const ln of lines) {
        if (ln.startsWith('event:')) eventType = ln.replace('event:', '').trim();
        if (ln.startsWith('data:')) dataText = ln.replace('data:', '').trim();
      }
      const data = JSON.parse(dataText || '{}');

      if (eventType === 'meta') {
        meta.textContent = `${data.agente.emoji} ${data.agente.nome} • ${fmtDate(data.timestamp)}`;
        el.statusLine.textContent = data.roteamento;
      } else if (eventType === 'token') {
        body.textContent += data.text || '';
        el.chatArea.scrollTop = el.chatArea.scrollHeight;
      } else if (eventType === 'done') {
        el.statusLine.textContent = 'Resposta concluída.';
      }
    }
  }

  await loadConversations();
}

async function sendDebate() {
  if (!state.currentConversationId) {
    await createConversation();
  }
  const question = el.messageInput.value.trim();
  if (!question) {
    alert('Digite a pergunta para o debate técnico.');
    return;
  }
  el.statusLine.textContent = 'Conselho Técnico em andamento...';

  try {
    const resp = await api('/api/debate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_id: state.currentConversationId,
        question,
      }),
    });
    addMessage('user', `[DEBATE] ${question}`, 'Você');
    addMessage('assistant', resp.dossie, '🤝 Conselho Técnico');
    el.messageInput.value = '';
    el.statusLine.textContent = 'Debate concluído.';
    await loadConversations();
  } catch (err) {
    el.statusLine.textContent = `Falha no debate: ${err.message}`;
  }
}

async function uploadKnowledge(file) {
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  if (state.currentProjectId) {
    formData.append('project_id', String(state.currentProjectId));
  }

  el.statusLine.textContent = 'Processando conhecimento com o Curador...';
  try {
    const resp = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Falha ao processar arquivo.');
    el.statusLine.textContent = `Conhecimento adicionado com tags: ${data.tags.join(', ')}`;
    await loadKnowledge();
  } catch (err) {
    el.statusLine.textContent = `Erro no upload: ${err.message}`;
  }
}

async function createProject() {
  const nome = prompt('Nome do projeto:');
  if (!nome) return;
  const dominio = prompt('Domínio do projeto (opcional):') || '';
  const descricao = prompt('Descrição (opcional):') || '';
  const p = await api('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nome, dominio, descricao }),
  });
  state.currentProjectId = p.id;
  state.currentConversationId = null;
  await loadProjects();
}

function bindEvents() {
  el.projectSelect.addEventListener('change', async (e) => {
    state.currentProjectId = Number(e.target.value);
    state.currentConversationId = null;
    await loadConversations();
    await loadKnowledge();
  });

  el.newConversationBtn.addEventListener('click', createConversation);
  el.newProjectBtn.addEventListener('click', createProject);
  el.sendBtn.addEventListener('click', sendMessage);
  el.debateBtn.addEventListener('click', sendDebate);

  el.messageInput.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter' && !ev.shiftKey) {
      ev.preventDefault();
      sendMessage();
    }
  });

  el.uploadInput.addEventListener('change', (e) => {
    uploadKnowledge(e.target.files?.[0]);
    e.target.value = '';
  });

  el.modeSelect.addEventListener('change', () => {
    const expert = el.modeSelect.value === 'expert';
    el.agentSelect.disabled = !expert;
  });
}

async function bootstrap() {
  try {
    await loadHealth();
    await loadProjects();
    bindEvents();
    el.modeSelect.dispatchEvent(new Event('change'));
  } catch (err) {
    el.statusLine.textContent = `Erro ao inicializar: ${err.message}`;
  }
}

bootstrap();
