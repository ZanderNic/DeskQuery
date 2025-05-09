const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const charCount = document.getElementById('char-count');

const modelDropdown = document.getElementById('header-model-dropdown');
const modelDropdownButton = document.getElementById('header-model-selection-button');

let isWaitingForResponse = false;

document.addEventListener('DOMContentLoaded', () => {

// Fetch the models from the external JSON file
fetch('../../llm/models.json')
  .then(response => {
    if (!response.ok) {
      throw new Error('Failed to load models.json');
    }
    return response.json();
  })
  .then(models => {
    // Populate the dropdown with options
    models.forEach(model => {
      const option = document.createElement('option');
      option.value = model.value;
      option.textContent = model.label;
      modelDropdown.appendChild(option);
    });
  })
  .catch(error => {
    console.error('Error loading models:', error);
  });
});

modelDropdown.addEventListener('change', function() {
  const selectedModel = this.options[this.selectedIndex].text;
  modelDropdownButton.textContent = selectedModel;
});

function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 200) + 'px';
}

userInput.addEventListener('input', () => {
  autoResizeTextarea(userInput);
  charCount.textContent = `${userInput.value.length} / 500`;
});

function appendMessage(content, sender, isHTML = false) {
  const msg = document.createElement('div');
  msg.className = `message ${sender}`;
  if (isHTML) {
    msg.innerHTML = content;
  } else {
    msg.textContent = content;
  }
  chatContainer.appendChild(msg);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function appendLoading() {
  const msg = document.createElement('div');
  msg.className = 'message bot loading';
  msg.id = 'loading-msg';
  msg.textContent = 'Thinking...';
  chatContainer.appendChild(msg);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeLoading() {
  const loadingMsg = document.getElementById('loading-msg');
  if (loadingMsg) loadingMsg.remove();
}

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text || isWaitingForResponse) return;

  isWaitingForResponse = true;
  appendMessage(text, 'user');
  userInput.value = '';
  autoResizeTextarea(userInput);
  charCount.textContent = '0 / 500';
  userInput.disabled = true;
  sendBtn.disabled = true;

  appendLoading();

  try {
  const response = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text })
  });

  const data = await response.json();
  console.log("RESPONSE:", data);

  removeLoading();

  if (data.type === 'text') {
    appendMessage(data.content, 'bot');

  } else if (data.type === 'image') {
    const html = `<img src="${data.content}" style="max-width:100%">`;
    appendMessage(html, 'bot', true);

  } else if (data.type === 'plot') {
    const plotDiv = document.createElement('div');
    plotDiv.className = 'message bot';
    const plotId = 'plot-' + Date.now();
    plotDiv.id = plotId;
    chatContainer.appendChild(plotDiv);
    Plotly.newPlot(plotId, data.data, data.layout);

  } else if (data.type === 'mixed') {
    let html = '';

    if (data.text) html += `<p>${data.text}</p>`;
    if (data.image) html += `<img src="${data.image}" style="max-width:100%">`;
    if (data.html) html += data.html;

    let plotId = null;
    if (data.plot) {
      plotId = 'plot-' + Date.now();
      html += `<div id="${plotId}" style="width:100%"></div>`;
    }

    appendMessage(html, 'bot', true);

    if (plotId) {
      Plotly.newPlot(plotId, data.plot.data, data.plot.layout);
    }

    } else if (data.type === 'html') {
      appendMessage(data.html, 'bot', true);

    } else {
      appendMessage('[Error: unknown response type]', 'bot');
    }





  } catch (err) {
    console.error('Error handling response:', err);
    removeLoading();
    appendMessage('[Error: could not understand response]', 'bot');
  } finally {
    isWaitingForResponse = false;
    userInput.disabled = false;
    sendBtn.disabled = false;
    userInput.focus();
    userInput.dispatchEvent(new Event('input'));
  }
}

sendBtn.addEventListener('click', sendMessage);

userInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});