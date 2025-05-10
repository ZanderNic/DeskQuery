document.addEventListener('DOMContentLoaded', () => {
  let currentChatId = null;
  const chatContainer = document.getElementById('chat-container');
  const userInput = document.getElementById('user-input');
  const sendBtn = document.getElementById('send-btn');
  const charCount = document.getElementById('char-count');
  const chatList = document.getElementById('chat-list');
  const sidebar = document.getElementById('sidebar');
  const newChatBtnWrapper = document.getElementById('new-chat-btn-wrapper');
  const toggleSidebarBtn = document.getElementById('toggle-sidebar');
  const modelSelectorBtn = document.getElementById('model-selector-btn');
  const modelSelectorOptions = document.getElementById('model-selector-options');

  // the currently selected model
  let selectedModel = null;

  async function loadModels() {
    // fetch the model list
    let response = await fetch('/get-models');
    response = await response.json();
    const models = response.models;

    // prepare the model selector ul
    modelSelectorOptions.innerHTML = '';
    let child_id = 0;

    // create the model selector option for each model
    models.forEach(model => {
      const option = document.createElement('li');
      option.className = 'model-option';
      option.setAttribute('data', `${model.provider}:${model.model}`);
      option.textContent = model.label;

      // add a click event listener for selection functionality
      option.addEventListener('click', () => {
        // update the selectedModel variable for setCurrentModel()
        selectedModel = option.getAttribute('data');

        // unselect the current model option
        const modelSelectorSelectedOption = document.getElementsByClassName(
          'model-option selected')[0];
        if (modelSelectorSelectedOption) {
          modelSelectorSelectedOption.classList.remove('selected');
        }

        // select the clicked model option
        option.classList.add("selected");
        // close the model selector
        modelSelectorOptions.classList.toggle('hidden');
        // apply the selection to the system
        setCurrentModel();
      });
      // select first model in the list by default
      if (child_id === 0) {
        option.classList.toggle("selected");
        selectedModel = option.getAttribute('data');
        child_id++;
      }
      modelSelectorOptions.appendChild(option);
    });
    // apply the default model
    setCurrentModel();
  }
  
  async function setCurrentModel() {
    console.log("selectedModel:", selectedModel);
    const [provider, model] = selectedModel.split(':');
    await fetch('/set-model', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        'provider': provider,
        'model': model,
      })
    });
  }
  
  modelSelectorBtn.addEventListener('click', () => {
    modelSelectorOptions.classList.toggle('hidden');
  });


  toggleSidebarBtn.addEventListener('click', () => {
    newChatBtnWrapper.classList.toggle('hidden');
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

  // initialize setup
  loadChatList();
  loadModels();
});