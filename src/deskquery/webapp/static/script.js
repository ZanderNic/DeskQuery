document.addEventListener('DOMContentLoaded', () => {
  let currentChatId = null;   // the currently selected chat
  let selectedModel = null;   // the currently selected model
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
  const overlay = document.getElementById('empty-chat-overlay');


  // ============================
  // === UI Utility Functions ===
  // ============================

  function appendMessage(content, sender, data = null, messageId = null) {
     
    console.log("DEBUG appendMessage()", { sender, content, data });  

    const wrapper = document.createElement('div');
    wrapper.className = `message ${sender}`;

    // Append text content if present
    if (content) {
      const text = document.createElement('div');
      text.className = 'message-text';
      text.textContent = content;
      wrapper.appendChild(text);
    }

    switch (data?.type) {
      case 'plot':
        wrapper.appendChild(renderPlot(data.plotly, messageId));
        break;
      case 'table':
        wrapper.appendChild(renderTable(data.df));
        break;
    }

    chatContainer.appendChild(wrapper);
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  function createThinkingMessage() {
    const msg = document.createElement('div');
    msg.className = 'message thinking';
    const spinner = document.createElement('span');
    spinner.className = 'spinner';
    const text = document.createElement('span');
    text.textContent = 'Thinking ...';
    msg.append(spinner, text);
    return msg;
  }

  function showError(message, error = null) {
    appendMessage(message, 'bot');
    if (error) console.error(error);
  }

  function updateOverlayVisibility() {
    requestAnimationFrame(() => {
      const hasMessages = chatContainer.querySelector('.message');
      if (!currentChatId || !hasMessages) {
        overlay.classList.remove('hidden');
      } else {
        overlay.classList.add('hidden');
      }
    });
  }

  function setActiveChatInSidebar(chatId) {
    chatList.querySelectorAll('.chat-entry').forEach(entry => {
      const span = entry.querySelector('.chat-title');
      if (span && span.getAttribute('data-id') === chatId) {
        entry.classList.add('active');
      } else {
        entry.classList.remove('active');
      }
    });
  }


  // ======================
  // === Model Handling ===
  // ======================

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
  
  // ======================
  // === Chat Functions ===
  // ======================

  async function loadChatList() {
    const res = await fetch('/chats');
    if (!res.ok) throw new Error("Failed to load chats");

    const chats = await res.json();
    chatList.innerHTML = '';

    const grouped = groupChatsByDate(chats);

    for (const section in grouped) {
      if (grouped[section].length === 0) continue;

      const groupHeader = document.createElement('div');
      groupHeader.className = 'chat-list-group-label';
      groupHeader.textContent = section;
      chatList.appendChild(groupHeader);

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

          editBtn.textContent = '✔';

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
            editBtn.textContent = '🖉';
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
            
            // if current chat is deleted chat clear chat container
            if (currentChatId === c.chat_id) {
              chatContainer.innerHTML = '';
              currentChatId = null;
            }
            
            document.querySelectorAll('.chat-entry.active').forEach(entry => {
              entry.classList.remove('active');
            });
            
            await loadChatList();
            updateOverlayVisibility();
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

  async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    sendBtn.disabled = true;                          // disable the send button (keep label)
    sendBtn.style.backgroundColor = "#555";           // set color of send button to gray

    if (!currentChatId) {
      const res = await fetch('/chats/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      const data = await res.json();
      currentChatId = data.chat_id;
      await loadChatList();                   // refresh sidebar to include the new chat
      setActiveChatInSidebar(currentChatId);  // select chat as active chat in sidebar
    }

    appendMessage(text, 'user');    
    userInput.value = '';
    charCount.textContent = '0 / 500';
    updateOverlayVisibility();

    const thinkingMsg = createThinkingMessage();  // Add spinner + "Thinking..." message
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

      data.messages.forEach(m => {
        if (m.role === 'assistant') {
          renderAssistantMessage(m)
        }
      });

      loadChatList();

    } catch (error) {
      thinkingMsg.remove();
      showError("Error while sending message.", error);
    } finally {
      sendBtn.disabled = false;                   // Re-enable the send button
      sendBtn.style.backgroundColor = "";         // reset send button color
      userInput.focus();                          // set cursor in text input field 
    }
  }

  async function loadChat(chatId) {
    const res = await fetch(`/chats/${chatId}`);
    const chat = await res.json();
    chatContainer.innerHTML = '';
    currentChatId = chat.chat_id;
    chat.messages.forEach(m => {
      if (m.role === 'assistant') {
        renderAssistantMessage(m);  
      
      } else {
        let parsedData = null;
        try {
          parsedData = typeof m.data === 'string' ? JSON.parse(m.data) : m.data;
        } catch (e) {
          console.warn('Error while parsing:', m.data, e);
        }
        appendMessage(m.content, 'user', parsedData, m.id);
      }
    });
    
    setActiveChatInSidebar(currentChatId)    // set active chat in history to indicate which one is active
    updateOverlayVisibility();  // if empty chat show empty Overlay
  }
  
  // =======================
  // === Utility Helpers ===
  // =======================

  function groupChatsByDate(chats) {
    const groups = {
      "Today": [],
      "Yesterday": [],
      "Last 7 days": [],
      "Older": []
    };
    const now = new Date();
    chats.forEach(c => {
      const date = new Date(c.last_updated);
      const diffTime = now - date;
      const diffDays = diffTime / (1000 * 60 * 60 * 24);

      if (date.toDateString() === now.toDateString()) {
        groups["Today"].push(c);
      } else if (diffDays < 2) {
        groups["Yesterday"].push(c);
      } else if (diffDays < 7) {
        groups["Last 7 days"].push(c);
      } else {
        groups["Older"].push(c);
      }
    });
    return groups;
  }

  function renderAssistantMessage(m) {
    const content = m.content || '';
    const data = m.data || null;
    const type = data?.type || null;
    const to_plot = data?.plotted || null;

    if (type === 'mixed' && to_plot && data.plotly) {
      appendMessage(content, 'bot', null, m.id);
      appendMessage('', 'bot', { type: 'plot', plotly: data.plotly }, m.id + '-plot');
    } else {
      appendMessage(content, 'bot', data, m.id);
    }
  }

  function renderPlot(plotData, messageId) {
    const plotDiv = document.createElement('div');
    plotDiv.id = `plot-${messageId || Math.random().toString(36).slice(2)}`;
    plotDiv.className = 'plot-container';

    const render = () => {
      if (!plotDiv.offsetParent) {
        requestAnimationFrame(render);
        return;
      }

      try {
        const parentWidth = plotDiv.parentElement?.offsetWidth || 600;

        Plotly.newPlot(
          plotDiv,
          plotData.data,
          {
            ...plotData.layout,
             autosize: true,
            height: 450,
            margin: { l: 30, r: 30, t: 30, b: 30 }
          },
          { responsive: true }
        );
      } catch (e) {
        console.warn("Plotly render error", e);
      }
    };

    requestAnimationFrame(render);

    return plotDiv;
  }

  function renderTable(df) {
    const table = document.createElement('table');
    table.className = 'dataframe';
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    df.columns.forEach(col => {
      const th = document.createElement('th');
      th.textContent = col;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    df.rows.forEach(row => {
      const tr = document.createElement('tr');
      row.forEach(cell => {
        const td = document.createElement('td');
        td.textContent = cell;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    return table;
  }

  // =======================
  // === Event Listeners ===
  // =======================

  sendBtn.addEventListener('click', sendMessage);
  userInput.addEventListener('keypress', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

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

  document.getElementById('new-chat-btn').onclick = async () => {
    const res = await fetch('/chats/new', {                // get a new chat from the chats/new endpoint
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await res.json();
    currentChatId = data.chat_id;
    chatContainer.innerHTML = '';         // reset chat container to contain nothing in new chat
    
    await loadChatList();                 // load the chat list with the new chat added
    await loadChat(currentChatId);        // select the new chat
    updateOverlayVisibility();            // update layout
  };


  // ========================
  // === Initialize Setup ===
  // ========================
  
  loadChatList();
  loadModels();
  updateOverlayVisibility();
});