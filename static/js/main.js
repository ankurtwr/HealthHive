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

// ── Chatbot Logic ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const chatbotWidget = document.getElementById('chatbotWidget');
  const chatbotToggle = document.getElementById('chatbotToggle');
  const chatbotClose = document.getElementById('chatbotClose');
  const chatbotMessages = document.getElementById('chatbotMessages');
  const chatbotInput = document.getElementById('chatbotInput');
  const chatbotSend = document.getElementById('chatbotSend');

  if (!chatbotWidget) return;

  chatbotToggle.addEventListener('click', () => {
    chatbotWidget.classList.add('open');
    chatbotInput.focus();
  });

  chatbotClose.addEventListener('click', () => {
    chatbotWidget.classList.remove('open');
  });

  const appendMessage = (text, sender) => {
    const msg = document.createElement('div');
    msg.className = `chat-msg ${sender}`;
    msg.textContent = text;
    chatbotMessages.appendChild(msg);
    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
  };

  const sendMessage = async () => {
    const text = chatbotInput.value.trim();
    if (!text) return;

    appendMessage(text, 'user');
    chatbotInput.value = '';

    try {
      const response = await fetch('/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await response.json();
      appendMessage(data.response, 'bot');
    } catch (err) {
      appendMessage('Sorry, I am having trouble connecting.', 'bot');
    }
  };

  chatbotSend.addEventListener('click', sendMessage);
  chatbotInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
  });

  // ── Theme Toggle Logic ──
  const themeToggle = document.getElementById('theme-toggle-btn');
  if (themeToggle) {
    const updateToggleIcon = () => {
      if (document.documentElement.classList.contains('light-theme')) {
        themeToggle.textContent = '☀️';
      } else {
        themeToggle.textContent = '🌙';
      }
    };
    
    // Set initial icon
    updateToggleIcon();

    themeToggle.addEventListener('click', () => {
      if (document.documentElement.classList.contains('light-theme')) {
        document.documentElement.classList.remove('light-theme');
        localStorage.setItem('theme', 'dark');
      } else {
        document.documentElement.classList.add('light-theme');
        localStorage.setItem('theme', 'light');
      }
      updateToggleIcon();
    });
  }
});