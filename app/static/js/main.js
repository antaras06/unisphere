(function () {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
  window.UniSphere = window.UniSphere || {};
  window.UniSphere.csrf = csrf;

  window.UniSphere.toast = function (message, variant) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const el = document.createElement('div');
    el.className = `toast align-items-center text-bg-${variant || 'dark'} border-0 shadow`;
    el.setAttribute('role', 'status');
    el.innerHTML = `<div class="d-flex"><div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`;
    container.appendChild(el);
    const t = new bootstrap.Toast(el, { delay: 2500 });
    t.show();
    el.addEventListener('hidden.bs.toast', () => el.remove());
  };

  // Favourite toggles (AJAX with form fallback)
  document.addEventListener('submit', async function (e) {
    const form = e.target;
    if (!form.matches('form.js-fav-form')) return;
    e.preventDefault();
    const btn = form.querySelector('button');
    btn.disabled = true;
    try {
      const res = await fetch(form.action, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'fetch', 'Accept': 'application/json' },
      });
      if (res.status === 401 || res.redirected) { window.location.href = form.dataset.loginUrl || '/login'; return; }
      const data = await res.json();
      btn.classList.toggle('active', data.saved);
      btn.setAttribute('aria-pressed', data.saved ? 'true' : 'false');
      const label = btn.querySelector('.fav-label');
      if (label) label.textContent = data.saved ? 'Saved' : 'Save';
      if (form.dataset.removeOnUnsave === '1' && !data.saved) {
        const card = form.closest('[data-fav-card]');
        if (card) {
          card.remove();
          const grid = document.getElementById('favGrid');
          if (grid && !grid.querySelector('[data-fav-card]')) window.location.reload();
        }
      }
      window.UniSphere.toast(data.message, data.saved ? 'primary' : 'dark');
    } catch (err) {
      form.submit();
    } finally {
      btn.disabled = false;
    }
  });

  // Loading state for forms
  document.addEventListener('submit', function (e) {
    const form = e.target;
    if (form.matches('form.js-fav-form') || form.dataset.noLoading !== undefined) return;
    const btn = form.querySelector('button[type="submit"][data-loading]');
    if (btn) {
      btn.classList.add('is-loading');
      btn.disabled = true;
      setTimeout(() => { btn.disabled = false; btn.classList.remove('is-loading'); }, 15000);
    }
  });

  // Auto-dismiss flashes
  setTimeout(() => {
    document.querySelectorAll('#flashContainer .alert').forEach(el => {
      try { bootstrap.Alert.getOrCreateInstance(el).close(); } catch (_) {}
    });
  }, 6000);

  // Global socket: unread badge updates
  if (window.io && document.body.dataset.noSocket === undefined) {
    try {
      const socket = io({ withCredentials: true });
      window.UniSphere.socket = socket;
      socket.on('inbox_update', function (data) {
        const active = document.body.dataset.activeConversation;
        if (active && String(active) === String(data.conversation_id)) return;
        const badge = document.getElementById('unreadBadge');
        if (badge) {
          const n = parseInt(badge.textContent || '0', 10) + 1;
          badge.textContent = n;
          badge.classList.remove('d-none');
        }
        window.UniSphere.toast(`New message from ${data.sender_name}: ${escapeHtml(data.preview)}`, 'primary');
      });
    } catch (_) {}
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  window.UniSphere.escapeHtml = escapeHtml;
})();
