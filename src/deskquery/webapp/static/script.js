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

    // Append text content if present
    if (content) {
      const text = document.createElement('div');
      text.className = 'message-text';
      text.textContent = content;
      wrapper.appendChild(text);
    }

    switch (data?.type) {
      case 'plot':
        wrapper.className = 'message plot';
        wrapper.appendChild(renderPlot(data.plotly, messageId));
        break;
      case 'table':
        wrapper.className = 'message table';
        const tableHeader = document.createElement('div');
        tableHeader.className = 'table-header';
        tableHeader.textContent = data.data.plotly.layout?.title?.text || '';
        wrapper.appendChild(tableHeader);
        wrapper.appendChild(renderTable(
          data.data,
          data.data.plotly.layout?.xaxis?.title?.text || ''
        ));
        break;
      default:
        wrapper.className = `message ${sender}`;
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
        // set edit button to pencil icon
        editBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" fill="currentColor" stroke="currentColor" stroke-width="0" viewBox="0 0 576 512"><path stroke="none" d="m402.3 344.9 32-32c5-5 13.7-1.5 13.7 5.7V464c0 26.5-21.5 48-48 48H48c-26.5 0-48-21.5-48-48V112c0-26.5 21.5-48 48-48h273.5c7.1 0 10.7 8.6 5.7 13.7l-32 32c-1.5 1.5-3.5 2.3-5.7 2.3H48v352h352V350.5c0-2.1.8-4.1 2.3-5.6zm156.6-201.8L296.3 405.7l-90.4 10c-26.2 2.9-48.5-19.2-45.6-45.6l10-90.4L432.9 17.1c22.9-22.9 59.9-22.9 82.7 0l43.2 43.2c22.9 22.9 22.9 60 .1 82.8zM460.1 174 402 115.9 216.2 301.8l-7.3 65.3 65.3-7.3L460.1 174zm64.8-79.7-43.2-43.2c-4.1-4.1-10.8-4.1-14.8 0L436 82l58.1 58.1 30.9-30.9c4-4.2 4-10.8-.1-14.9z"/></svg>';
        editBtn.onclick = (e) => {
          e.stopPropagation();
          if (isEditing) return;
          isEditing = true;

          // change edit button to checkmark icon
          editBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" fill="currentColor" stroke="currentColor" stroke-width="0" viewBox="0 0 448 512"><path stroke="none" d="M64 80c-8.8 0-16 7.2-16 16v320c0 8.8 7.2 16 16 16h320c8.8 0 16-7.2 16-16V96c0-8.8-7.2-16-16-16H64zM0 96c0-35.3 28.7-64 64-64h320c35.3 0 64 28.7 64 64v320c0 35.3-28.7 64-64 64H64c-35.3 0-64-28.7-64-64V96zm337 113L209 337c-9.4 9.4-24.6 9.4-33.9 0l-64-64c-9.4-9.4-9.4-24.6 0-33.9s24.6-9.4 33.9 0l47 47L303 175c9.4-9.4 24.6-9.4 33.9 0s9.4 24.6 0 33.9z"/></svg>';

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
            // reset edit button to pencil icon
            editBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" fill="currentColor" stroke="currentColor" stroke-width="0" viewBox="0 0 576 512"><path stroke="none" d="m402.3 344.9 32-32c5-5 13.7-1.5 13.7 5.7V464c0 26.5-21.5 48-48 48H48c-26.5 0-48-21.5-48-48V112c0-26.5 21.5-48 48-48h273.5c7.1 0 10.7 8.6 5.7 13.7l-32 32c-1.5 1.5-3.5 2.3-5.7 2.3H48v352h352V350.5c0-2.1.8-4.1 2.3-5.6zm156.6-201.8L296.3 405.7l-90.4 10c-26.2 2.9-48.5-19.2-45.6-45.6l10-90.4L432.9 17.1c22.9-22.9 59.9-22.9 82.7 0l43.2 43.2c22.9 22.9 22.9 60 .1 82.8zM460.1 174 402 115.9 216.2 301.8l-7.3 65.3 65.3-7.3L460.1 174zm64.8-79.7-43.2-43.2c-4.1-4.1-10.8-4.1-14.8 0L436 82l58.1 58.1 30.9-30.9c4-4.2 4-10.8-.1-14.9z"/></svg>';
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
        // set delete button to trash icon
        delBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 24 24"><path d="M3 6h18M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2M10 11v6M14 11v6"/></svg>';
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

      if (data.messages && data.messages.length > 0) {
        const lastAssistantMsg = [...data.messages].reverse().find(m => m.role === 'assistant');
        if (lastAssistantMsg) {
          renderAssistantDescriptor();
          renderAssistantMessage(lastAssistantMsg);
        }
      }

      loadChatList();

    } catch (error) {
      thinkingMsg.remove();
      showError("Error while sending message. Please try again.", error);
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
    let consecutive_assistant_msgs = 0;
    chat.messages.forEach(m => {
      if (m.role === 'assistant') {
        if (consecutive_assistant_msgs === 0) {
          renderAssistantDescriptor();
        }
        consecutive_assistant_msgs++;
        renderAssistantMessage(m);
      } else {
        let parsedData = null;
        try {
          parsedData = typeof m.data === 'string' ? JSON.parse(m.data) : m.data;
        } catch (e) {
          console.warn('Error while parsing:', m.data, e);
        }
        consecutive_assistant_msgs = 0;
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
      const date = new Date(c.last_timestamp);
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

  function renderAssistantDescriptor() {
    const descriptor = document.createElement('div');
    descriptor.className = 'assistant';

    // assistant icon
    const icon = document.createElement('div');
    icon.className = 'assistant-icon';
    icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 24 24"><path d="M18 4a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3h-5l-5 3v-3H6a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3h12zM9.5 9h.01M14.5 9h.01"/><path d="M9.5 13a3.5 3.5 0 0 0 5 0"/></svg>';
    descriptor.appendChild(icon);

    // assistant name
    const name = document.createElement('div');
    name.className = 'assistant-name';
    name.textContent = 'Desk Query Assistant';
    descriptor.appendChild(name);

    chatContainer.appendChild(descriptor);
    chatContainer.scrollTop = chatContainer.scrollHeight;  // scroll to bottom
  }

  function renderAssistantMessage(m) {
    const content = m.content || '';
    const data = m.data || null;
    const type = data?.type || null;
    const to_plot = data?.plotted || null;

    if (type === 'mixed' && to_plot && data.plotly) {
      appendMessage(content, 'bot', null, m.id);
      appendMessage('', 'bot', { type: 'plot', plotly: data.plotly }, m.id + '-plot');
    } else if (type === 'mixed' && !to_plot && data) {
      appendMessage(content, 'bot', null, m.id);
      appendMessage('', 'bot', { type: 'table', data: data }, m.id + '-table');
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
            width: parentWidth,
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

  function renderTable(data, indexLabel = '') {
    console.log("df in renderTable: ", data); // DEBUG: Log the DataFrame structure

    const table = document.createElement('table');
    table.className = 'dataframe';

    const thead = document.createElement('thead');

    const headerRow = document.createElement('tr');
    const th = document.createElement('th');
    th.textContent = indexLabel;
    headerRow.appendChild(th); // Empty header for row indices

    for (const col in data['function_data']) {
      const th = document.createElement('th');
      th.textContent = col;
      headerRow.appendChild(th);
    }
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    
    // const dfCols = Object.keys(df);
    // console.log("dfCols: ", dfCols); // DEBUG: Log the DataFrame columns
    // const rowIndices = Object.keys(df[dfCols[0]]);
    // console.log("rowIndices: ", rowIndices); // DEBUG: Log the DataFrame row indices
    
    // dfEntries = {};
    // for (const row_idx of rowIndices) {
    //   dfEntries[row_idx] = {};
    //   for (const col of dfCols) {
    //     dfEntries[row_idx][col] = df[col][row_idx];
    //   }
    // }

    // console.log("dfEntries: ", dfEntries); // DEBUG: Log the DataFrame entries

    // for (const row in dfEntries) {
    //   const tr = document.createElement('tr');
    //   // Create the first cell for the row index
    //   const td = document.createElement('td');
    //   td.textContent = row;
    //   tr.appendChild(td);
    //   for (const col in dfEntries[row]) {
    //     const td = document.createElement('td');
    //     td.textContent = dfEntries[row][col] !== null ? dfEntries[row][col] : '';
    //     tr.appendChild(td);
    //   }
    //   tbody.appendChild(tr);
    // }

    for (const row in data['df']) {
      const tr = document.createElement('tr');
      // Create the first cell for the row index
      const td = document.createElement('td');
      td.textContent = row;
      tr.appendChild(td);
      for (const col in data['df'][row]) {
        const td = document.createElement('td');
        td.textContent = data['df'][row][col] !== null ? data['df'][row][col] : '';
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }

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