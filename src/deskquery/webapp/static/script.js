document.addEventListener('DOMContentLoaded', () => {
  let currentChatId = null;
  const chatContainer = document.getElementById('chat-container');
  const userInput = document.getElementById('user-input');
  const sendBtn = document.getElementById('send-btn');
  const charCount = document.getElementById('char-count');
  const chatList = document.getElementById('chat-list');
  const sidebar = document.getElementById('sidebar');
  const toggleSidebarBtn = document.getElementById('toggle-sidebar');

  toggleSidebarBtn.addEventListener('click', () => {
    sidebar.classList.toggle('hidden');
  });

  userInput.addEventListener('input', () => {
    charCount.textContent = `${userInput.value.length} / 500`;
  });

  function appendMessage(content, sender) {
    const msg = document.createElement('div');
    msg.className = `message ${sender}`;
    msg.textContent = content;
    chatContainer.appendChild(msg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    appendMessage(text, 'user');
    userInput.value = '';
    charCount.textContent = '0 / 500';

    const response = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, chat_id: currentChatId })
    });

    const data = await response.json();
    currentChatId = data.chat_id;

    data.messages.slice(-1).forEach(m => {
      if (m.role === 'assistant') {
        appendMessage(m.content, 'bot');
      }
    });

    loadChatList();
  }

  sendBtn.addEventListener('click', sendMessage);
  userInput.addEventListener('keypress', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  async function loadChatList() {
    const res = await fetch('/chats');
    const chats = await res.json();
    chatList.innerHTML = '';
    chats.forEach(c => {
      const entry = document.createElement('div');
      entry.className = 'chat-entry';
      entry.textContent = c.title || c.chat_id;
      entry.onclick = () => loadChat(c.chat_id);
      chatList.appendChild(entry);
    });
  }

  async function loadChat(chatId) {
    const res = await fetch(`/chats/${chatId}`);
    const chat = await res.json();
    chatContainer.innerHTML = '';
    currentChatId = chat.chat_id;
    chat.messages.forEach(m => appendMessage(m.content, m.role === 'user' ? 'user' : 'bot'));
  }

  document.getElementById('new-chat-btn').onclick = () => {
    currentChatId = null;
    chatContainer.innerHTML = '';
  };

  loadChatList();
});