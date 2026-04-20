// main.js  — Autocomplete for search inputs

function initAutocomplete(inputId, listId, endpoint) {
  const input = document.getElementById(inputId);
  const list  = document.getElementById(listId);
  if (!input || !list) return;

  let activeIndex = -1;
  let debounceTimer;

  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();

    if (q.length < 2) { closeList(); return; }

    debounceTimer = setTimeout(async () => {
      const res   = await fetch(`${endpoint}?query=${encodeURIComponent(q)}`);
      const names = await res.json();

      list.innerHTML = '';
      activeIndex = -1;

      if (!names.length) { closeList(); return; }

      names.forEach((name, i) => {
        const item = document.createElement('div');
        item.className = 'autocomplete-item';
        item.textContent = name;
        item.addEventListener('mousedown', () => {
          input.value = name;
          closeList();
          input.form.submit();
        });
        list.appendChild(item);
      });

      list.classList.add('open');
    }, 200);
  });

  // Keyboard navigation
  input.addEventListener('keydown', (e) => {
    const items = list.querySelectorAll('.autocomplete-item');
    if (!items.length) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, items.length - 1);
      updateActive(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, -1);
      updateActive(items);
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      input.value = items[activeIndex].textContent;
      closeList();
      input.form.submit();
    } else if (e.key === 'Escape') {
      closeList();
    }
  });

  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !list.contains(e.target)) closeList();
  });

  function updateActive(items) {
    items.forEach((item, i) => {
      item.classList.toggle('active', i === activeIndex);
    });
  }

  function closeList() {
    list.classList.remove('open');
    list.innerHTML = '';
    activeIndex = -1;
  }
}