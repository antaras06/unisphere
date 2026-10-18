(function () {
  const root = document.getElementById('chatRoot');
  if (!root) return;
  const conversationId = parseInt(root.dataset.conversationId, 10);
  const currentUserId = parseInt(root.dataset.userId, 10);
  const pollInterval = parseInt(root.dataset.pollInterval || '8000', 10);
  const apiUrl = root.dataset.apiUrl;
  const list = document.getElementById('messageList');
  const form = document.getElementById('messageForm');
  const textarea = form.querySelector('textarea');
  const sendBtn = form.querySelector('button[type="submit"]');
  const typingEl = document.getElementById('typingIndicator');
  const statusEl = document.getElementById('connStatus');
  const esc = window.UniSphere.escapeHtml;
  let lastId = parseInt(root.dataset.lastId || '0', 10);
  const seen = new Set(Array.from(list.querySelectorAll('[data-id]')).map(el => parseInt(el.dataset.id, 10)));
  let socketReady = false;

  document.body.dataset.activeConversation = conversationId;

  function fmtTime(iso) {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  function dayKey(iso) { const d = new Date(iso); return d.toDateString(); }
  function dayLabel(iso) {
    const d = new Date(iso); const today = new Date(); const y = new Date(); y.setDate(today.getDate() - 1);
    if (d.toDateString() === today.toDateString()) return 'Today';
    if (d.toDateString() === y.toDateString()) return 'Yesterday';
    return d.toLocaleDateString([], { day: 'numeric', month: 'short', year: 'numeric' });
  }

  function scrollBottom() { list.scrollTop = list.scrollHeight; }

  function appendMessage(m) {
    if (seen.has(m.id)) return;
    seen.add(m.id);
    const lastDivider = list.querySelector('.us-day-divider:last-of-type');
    const lastMsg = list.querySelector('.us-msg:last-of-type');
    const lastDay = lastMsg ? lastMsg.dataset.day : null;
    if (dayKey(m.created_at) !== lastDay) {
      const div = document.createElement('div');
      div.className = 'us-day-divider';
      div.textContent = dayLabel(m.created_at);
      list.appendChild(div);
    }
    const empty = document.getElementById('emptyChat');
    if (empty) empty.remove();
    const mine = m.sender_id === currentUserId;
    const el = document.createElement('div');
    el.className = 'us-msg ' + (mine ? 'mine' : 'theirs');
    el.dataset.id = m.id;
    el.dataset.day = dayKey(m.created_at);
    el.innerHTML = `${esc(m.body)}<div class="us-msg-meta">${mine ? 'You' : esc(m.sender_name)} · ${fmtTime(m.created_at)}</div>`;
    list.appendChild(el);
    if (m.id > lastId) lastId = m.id;
    scrollBottom();
  }

  // Localise timestamps rendered server-side
  list.querySelectorAll('[data-ts]').forEach(el => { el.textContent = fmtTime(el.dataset.ts); });
  list.querySelectorAll('.us-day-divider[data-ts]').forEach(el => { el.textContent = dayLabel(el.dataset.ts); });
  scrollBottom();

  async function poll() {
    try {
      const res = await fetch(`${apiUrl}?after=${lastId}`, { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' });
      if (!res.ok) return;
      const data = await res.json();
      (data.messages || []).forEach(appendMessage);
    } catch (_) {}
  }
  setInterval(poll, pollInterval);

  const socket = window.UniSphere.socket;
  if (socket) {
    socket.on('connect', () => { socket.emit('join_conversation', { conversation_id: conversationId }); });
    if (socket.connected) socket.emit('join_conversation', { conversation_id: conversationId });
    socket.on('joined', () => { socketReady = true; if (statusEl) { statusEl.textContent = 'Live'; statusEl.className = 'badge rounded-pill text-bg-success'; } });
    socket.on('disconnect', () => { socketReady = false; if (statusEl) { statusEl.textContent = 'Reconnecting…'; statusEl.className = 'badge rounded-pill text-bg-secondary'; } });
    socket.on('new_message', m => { if (m.conversation_id === conversationId) { appendMessage(m); if (m.sender_id !== currentUserId) poll(); } });
    socket.on('error', e => { if (e && e.error) window.UniSphere.toast(e.error, 'danger'); });
    let typingTimer;
    socket.on('typing', d => {
      if (d.conversation_id !== conversationId || d.user_id === currentUserId) return;
      typingEl.textContent = `${d.name} is typing…`;
      clearTimeout(typingTimer);
      typingTimer = setTimeout(() => { typingEl.textContent = ''; }, 2500);
    });
    let lastTyping = 0;
    textarea.addEventListener('input', () => {
      const now = Date.now();
      if (socketReady && now - lastTyping > 1500) { lastTyping = now; socket.emit('typing', { conversation_id: conversationId }); }
    });
  }

  async function send(body) {
    sendBtn.disabled = true;
    try {
      const res = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.UniSphere.csrf, 'Accept': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ body }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) { window.UniSphere.toast(data.error || 'Could not send message.', 'danger'); return false; }
      appendMessage(data.message);
      return true;
    } catch (_) {
      window.UniSphere.toast('Network error. Please try again.', 'danger');
      return false;
    } finally {
      sendBtn.disabled = false;
    }
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const body = textarea.value.trim();
    if (!body) return;
    const ok = await send(body);
    if (ok) { textarea.value = ''; textarea.style.height = ''; textarea.focus(); }
  });
  textarea.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 140) + 'px';
  });

  const toggleSidebar = document.getElementById('toggleSidebar');
  if (toggleSidebar) toggleSidebar.addEventListener('click', () => root.classList.toggle('show-sidebar'));
})();
