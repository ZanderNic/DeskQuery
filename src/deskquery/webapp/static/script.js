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
  const selectedModelDisplay = document.getElementById('selected-model');

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
    // update the display
    const modelLabel = modelSelectorOptions.querySelector(`.model-option.selected`).textContent;
    selectedModelDisplay.textContent = modelLabel;
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

    sendBtn.disabled = true;                          // disable the send button (keep label)
    sendBtn.style.backgroundColor = "#555";           // set color of send button to gray

    appendMessage(text, 'user');                 
    userInput.value = '';
    charCount.textContent = '0 / 500';

    // Add spinner + "Thinking..." message
    const thinkingMsg = document.createElement('div');
    thinkingMsg.className = 'message thinking';

    const spinner = document.createElement('span');
    spinner.className = 'spinner';

    const textNode = document.createElement('span');
    textNode.textContent = 'Thinking ...';

    thinkingMsg.appendChild(spinner);
    thinkingMsg.appendChild(textNode);
    chatContainer.appendChild(thinkingMsg);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, chat_id: currentChatId })
      });

      const data = await response.json();
      console.log("response.data:", data);
      currentChatId = data.chat_id;

      thinkingMsg.remove();

      data.messages.slice(-1).forEach(m => {
        if (m.role === 'assistant') {
          appendMessage(m.content, 'bot');
        }
      });

      loadChatList();
    } catch (error) {
      thinkingMsg.remove();
      appendMessage("Error while sending message.", 'bot');
      console.error(error);
    } finally {
      sendBtn.disabled = false;                   // Re-enable the send button
      sendBtn.style.backgroundColor = "";         // reset sedn button color
      userInput.focus();                          // set cursor in text input field 
    }
  }

  sendBtn.addEventListener('click', sendMessage);
  userInput.addEventListener('keypress', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  
  function groupChatsByDate(chats) {
    const groups = {
      "Heute": [],
      "Gestern": [],
      "Letzte 7 Tage": [],
      "Älter": []
    };
    const now = new Date();
    chats.forEach(c => {
      const date = new Date(c.timestamp);
      const diffTime = now - date;
      const diffDays = diffTime / (1000 * 60 * 60 * 24);

      if (date.toDateString() === now.toDateString()) {
        groups["Heute"].push(c);
      } else if (diffDays < 2) {
        groups["Gestern"].push(c);
      } else if (diffDays < 7) {
        groups["Letzte 7 Tage"].push(c);
      } else {
        groups["Älter"].push(c);
      }
    });
    return groups;
  }


  async function loadChatList() {
    const res = await fetch('/chats');
    const chats = await res.json();
    chatList.innerHTML = '';

    const grouped = groupChatsByDate(chats);

    for (const section in grouped) {
      if (grouped[section].length === 0) continue;

      const header = document.createElement('div');
      header.textContent = section;
      header.style.padding = '10px 15px';
      header.style.color = '#888';
      header.style.fontSize = '14px';
      header.style.fontWeight = '600';
      header.style.borderBottom = '1px solid #333';
      chatList.appendChild(header);

      grouped[section].forEach(c => {
        const entry = document.createElement('div');
        entry.className = 'chat-entry';

        const title = document.createElement('span');
        title.className = 'chat-title';
        title.textContent = c.title || c.chat_id;
        title.setAttribute('data-id', c.chat_id);
        title.contentEditable = false;

        let isEditing = false;

        const editBtn = document.createElement('button');
        editBtn.textContent = '🖉';
        editBtn.onclick = (e) => {
          e.stopPropagation();
          if (isEditing) return;
          isEditing = true;

          const original = title.textContent;
          title.contentEditable = true;
          title.focus();

          const finishEdit = async (save) => {
            isEditing = false;
            title.contentEditable = false;
            title.removeEventListener('blur', blurHandler);
            title.removeEventListener('keydown', keyHandler);

            const newTitle = title.textContent.trim();
            if (save && newTitle && newTitle !== original) {
              await fetch(`/chats/${c.chat_id}/rename`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
              });
            } else {
              title.textContent = original;
            }
            loadChatList();
          };

          const keyHandler = async (ev) => {
            if (ev.key === 'Enter') {
              ev.preventDefault();
              await finishEdit(true);
            } else if (ev.key === 'Escape') {
              ev.preventDefault();
              await finishEdit(false);
            }
          };

          const blurHandler = () => finishEdit(true);

          title.addEventListener('keydown', keyHandler);
          title.addEventListener('blur', blurHandler);
        };

        const delBtn = document.createElement('button');
        delBtn.textContent = '🗑';
        delBtn.onclick = async (e) => {
          e.stopPropagation();
          if (confirm('Delete this chat?')) {
            await fetch(`/chats/delete/${c.chat_id}`, { method: 'DELETE' });
            if (currentChatId === c.chat_id) {
              chatContainer.innerHTML = '';
              currentChatId = null;
            }
            loadChatList();
          }
        };

        entry.onclick = () => {
          if (!isEditing) loadChat(c.chat_id);
        };

        entry.appendChild(title);
        entry.appendChild(editBtn);
        entry.appendChild(delBtn);
        chatList.appendChild(entry);
      });
    }
  }

  
  async function loadChat(chatId) {
    const res = await fetch(`/chats/${chatId}`);
    const chat = await res.json();
    chatContainer.innerHTML = '';
    currentChatId = chat.chat_id;
    chat.messages.forEach(m => appendMessage(m.content, m.role === 'user' ? 'user' : 'bot'));
  }

  document.getElementById('new-chat-btn').onclick = async () => {
    const res = await fetch('/chats/new', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await res.json();
    currentChatId = data.chat_id;
    chatContainer.innerHTML = '';
    loadChatList();
  };

  // initialize setup
  loadChatList();
  loadModels();
});