(function () {
  const input = document.getElementById('images');
  const dropzone = document.getElementById('dropzone');
  const grid = document.getElementById('previewGrid');
  const maxImages = parseInt(dropzone?.dataset.max || '5', 10);
  const maxMb = parseInt(dropzone?.dataset.maxMb || '5', 10);
  if (!input || !dropzone || !grid) return;

  let files = [];

  function existingCount() {
    return grid.querySelectorAll('.us-preview[data-existing]:not(.is-removed)').length;
  }

  function syncInput() {
    const dt = new DataTransfer();
    files.forEach(f => dt.items.add(f));
    input.files = dt.files;
  }

  function render() {
    grid.querySelectorAll('.us-preview[data-new]').forEach(el => el.remove());
    files.forEach((file, idx) => {
      const el = document.createElement('div');
      el.className = 'us-preview';
      el.dataset.new = '1';
      const img = document.createElement('img');
      img.alt = file.name;
      img.src = URL.createObjectURL(file);
      img.onload = () => URL.revokeObjectURL(img.src);
      const rm = document.createElement('button');
      rm.type = 'button';
      rm.className = 'us-preview-remove';
      rm.setAttribute('aria-label', 'Remove image');
      rm.innerHTML = '<i class="bi bi-x-lg"></i>';
      rm.addEventListener('click', () => { files.splice(idx, 1); syncInput(); render(); });
      const label = document.createElement('span');
      label.className = 'us-preview-label';
      label.textContent = (file.size / 1024 / 1024).toFixed(1) + ' MB';
      el.append(img, rm, label);
      grid.appendChild(el);
    });
    const count = existingCount() + files.length;
    const counter = document.getElementById('imageCount');
    if (counter) counter.textContent = `${count}/${maxImages} images`;
  }

  function addFiles(list) {
    const errors = [];
    for (const f of Array.from(list)) {
      if (existingCount() + files.length >= maxImages) { errors.push(`You can add at most ${maxImages} images.`); break; }
      if (!/^image\/(jpeg|png|webp)$/.test(f.type)) { errors.push(`${f.name}: only JPG, PNG or WEBP allowed.`); continue; }
      if (f.size > maxMb * 1024 * 1024) { errors.push(`${f.name}: larger than ${maxMb} MB.`); continue; }
      files.push(f);
    }
    syncInput();
    render();
    const errBox = document.getElementById('imageErrors');
    if (errBox) { errBox.textContent = errors.join(' '); errBox.classList.toggle('d-none', errors.length === 0); }
  }

  dropzone.addEventListener('click', () => input.click());
  dropzone.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
  input.addEventListener('change', () => { addFiles(input.files); });
  ['dragenter', 'dragover'].forEach(ev => dropzone.addEventListener(ev, e => { e.preventDefault(); dropzone.classList.add('dragover'); }));
  ['dragleave', 'drop'].forEach(ev => dropzone.addEventListener(ev, e => { e.preventDefault(); dropzone.classList.remove('dragover'); }));
  dropzone.addEventListener('drop', e => addFiles(e.dataTransfer.files));

  grid.addEventListener('click', e => {
    const btn = e.target.closest('[data-toggle-remove]');
    if (!btn) return;
    const wrap = btn.closest('.us-preview');
    const cb = wrap.querySelector('input[type="checkbox"]');
    cb.checked = !cb.checked;
    wrap.classList.toggle('is-removed', cb.checked);
    btn.innerHTML = cb.checked ? '<i class="bi bi-arrow-counterclockwise"></i>' : '<i class="bi bi-x-lg"></i>';
    render();
  });

  render();
})();
