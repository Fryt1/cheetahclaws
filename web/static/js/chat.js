/* ChatApp — core class, constructor, send/WS/streaming/event dispatch.
 *
 * Other /static/js modules extend ChatApp.prototype via Object.assign, so
 * this file must load FIRST (after marked.min.js). The global `app` instance
 * is created in init.js once all mixins have registered their methods.
 */

class ChatApp {
  constructor() {
    this.sessionId = null;
    this.ws = null;
    this.streaming = false;
    this._textBuf = '';
    this._curMsgEl = null;
    this._thinkEl = null;
    this._toolCards = {};
    this._toolCounter = 0;
    this._approvalEl = null;
    this._activityEl = null;
    this._pendingApproval = false;
    this._authed = false;
    this._authMode = 'login';   // or 'register'
    this._sessions = [];        // last fetched list (for search filter)
    this._user = null;
    this._richUserId = null;
    try {
      const params = new URLSearchParams(window.location.search);
      this._richUserId = params.get('rich_user_id') || params.get('richUserId') || null;
    } catch(e) { /* ignore */ }
    this._pendingAttachments = [];

    // Listen for RICH user context from parent window (embedded mode)
    window.addEventListener('message', (e) => {
      const data = e.data;
      if (data && data.type === 'rich_user_context' && data.userId) {
        this._richUserId = data.userId;
      }
    });
  }

  // ── Attachments ─────────────────────────────────────────────────

  pickAttachment() {
    const input = document.getElementById('attachment-input');
    if (input) input.click();
  }

  async addAttachments(fileList) {
    const files = Array.from(fileList || []);
    for (const file of files) {
      if (file.size > 20 * 1024 * 1024) {
        this._addError(`${file.name} is larger than 20MB`);
        continue;
      }
      try {
        const data = await this._fileToBase64(file);
        this._pendingAttachments.push({
          name: file.name,
          mime: file.type || 'application/octet-stream',
          size: file.size,
          data,
        });
      } catch(e) {
        this._addError(`Failed to read ${file.name}: ${e.message}`);
      }
    }
    this._renderAttachments();
  }

  removeAttachment(index) {
    this._pendingAttachments.splice(index, 1);
    this._renderAttachments();
  }

  _fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const value = String(reader.result || '');
        resolve(value.includes(',') ? value.split(',').pop() : value);
      };
      reader.onerror = () => reject(reader.error || new Error('read failed'));
      reader.readAsDataURL(file);
    });
  }

  _renderAttachments() {
    const el = document.getElementById('attachment-list');
    if (!el) return;
    const items = this._pendingAttachments || [];
    el.classList.toggle('has-items', items.length > 0);
    el.innerHTML = items.map((item, index) => `
      <div class="attachment-chip" title="${this._escapeHtml(item.name)}">
        <span>${this._escapeHtml(item.name)}</span>
        <small>${Math.ceil(item.size / 1024)}KB</small>
        <button onclick="app.removeAttachment(${index})" title="Remove">×</button>
      </div>
    `).join('');
  }

  // ── Send prompt ─────────────────────────────────────────────────

  async send() {
    const input = document.getElementById('prompt-input');
    const text = input.value.trim();
    const attachments = [...(this._pendingAttachments || [])];
    if (!text && attachments.length === 0) return;
    const promptText = text || '请分析我上传的附件。';
    input.value = '';
    input.style.height = 'auto';
    this._pendingAttachments = [];
    this._renderAttachments();

    try {
      if (!this.sessionId) {
        const body = {prompt: '', session_id: ''};
        if (this._richUserId) body.rich_user_id = this._richUserId;
        const r = await this._fetchAuth('/api/prompt', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify(body)
        });
        const data = await r.json();
        if (!r.ok) {
          input.value = text;
          this._pendingAttachments = attachments;
          this._renderAttachments();
          this._addError(data.error || `Server error (${r.status})`);
          return;
        }
        this.sessionId = data.session_id;
        // If user is "in" a folder, drop the auto-created session there.
        const fid = this._getActiveFolderId && this._getActiveFolderId();
        if (fid) {
          try {
            await this._fetchAuth(
              `/api/sessions/${data.session_id}/folder`, {
                method: 'PATCH',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({folder_id: fid}),
              });
          } catch(e) { /* non-fatal */ }
        }
        this._connectWS(this.sessionId);
        this.loadSessions();
      }

      this._addUserBubble(promptText, attachments);
      this._showActivity('', 'Processing', 'connecting...');
      this._scrollBottom();

      // Slash commands
      if (promptText.startsWith('/') && attachments.length === 0) {
        const longRunning = ['/brainstorm','/worker','/plan','/agent'];
        const isLong = longRunning.some(c => promptText === c || promptText.startsWith(c + ' '));
        if (isLong) {
          this._showActivity('', 'Running', promptText.split(' ')[0] + '...');
          this._runSlashSSE(promptText);
        } else {
          this._showActivity('', 'Running', promptText.split(' ')[0] + '...');
          const slashBody = {prompt: promptText, session_id: this.sessionId};
          if (this._richUserId) slashBody.rich_user_id = this._richUserId;
          const r = await this._fetchAuth('/api/prompt', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(slashBody)
          });
          const data = await r.json();
          if (!r.ok) {
            this._removeActivity();
            this._addError(data.error || `Server error (${r.status})`);
            return;
          }
          this._removeActivity();
          (data.events || []).forEach(evt => this._handleEvent(evt));
          if (!this.sessionId) this.sessionId = data.session_id;
        }
        return;
      }

      // Regular prompts — prefer WS
      await this._ensureWS();
      const wsOK = this.ws && this.ws.readyState === 1;
      if (wsOK) {
        this._showActivity('', 'Processing', 'sending to agent...');
        const wsBody = {type: 'prompt', prompt: promptText, attachments, session_id: this.sessionId};
        if (this._richUserId) wsBody.rich_user_id = this._richUserId;
        this.ws.send(JSON.stringify(wsBody));
      } else {
        this._showActivity('', 'Processing', 'sending (http)...');
        const httpBody = {prompt: promptText, session_id: this.sessionId, attachments};
        if (this._richUserId) httpBody.rich_user_id = this._richUserId;
        const r = await this._fetchAuth('/api/prompt', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify(httpBody)
        });
        if (!r.ok) {
          const data = await r.json();
          this._addError(data.error || `Server error (${r.status})`);
          return;
        }
        this._pollForResult();
      }
    } catch(e) {
      input.value = text;
      this._pendingAttachments = attachments;
      this._renderAttachments();
      this._addError('Failed to send: ' + e.message);
    }
  }

  _pollForResult() {
    if (this._polling) return;
    this._polling = true;
    this._pollCount = 0;
    this.setStatus('running');
    this._showActivity('', 'Working', 'waiting for response...');
    const poll = async () => {
      this._pollCount++;
      try {
        const r = await fetch(`/api/sessions/${this.sessionId}`, {credentials:'same-origin'});
        if (!r.ok) { this._polling = false; this._removeActivity(); return; }
        const data = await r.json();
        const secs = this._pollCount * 2;
        this._showActivity('', 'Working',
          data.busy ? `running... (${secs}s)` : 'finishing...');
        if (!data.busy) {
          this._polling = false;
          this._removeActivity();
          this.setStatus('idle');
          const msgs = data.messages || [];
          const last = msgs[msgs.length - 1];
          if (last && last.role === 'assistant') {
            this._addAssistantBubble(last.content);
            if (last.tool_calls) last.tool_calls.forEach(tc => {
              this._addToolCard(tc.name, tc.inputs, tc.status, tc.result);
            });
          }
          this.loadSessions();
          if (this.sessionId && (!this.ws || this.ws.readyState !== 1)) {
            this._connectWS(this.sessionId);
          }
          return;
        }
      } catch(e) { /* ignore */ }
      if (this._polling) setTimeout(poll, 2000);
    };
    setTimeout(poll, 2000);
  }

  // ── WebSocket ────────────────────────────────────────────────────

  _connectWS(sid) {
    this._disconnectWS();
    this._wsRetries = (this._wsRetries || 0);
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${location.host}/api/events`;
    try {
      this.ws = new WebSocket(url);
    } catch(e) {
      console.warn('[chat] WebSocket constructor failed:', e);
      this.setStatus('no-ws');
      return;
    }
    this._wsSessionId = sid;

    this.ws.onopen = () => {
      this._wsRetries = 0;
      const hello = {session_id: sid};
      if (this._richUserId) hello.rich_user_id = this._richUserId;
      this.ws.send(JSON.stringify(hello));
      this.setStatus('connected');
      this._wsReady = true;
    };
    this.ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.error) {
          console.warn('[chat] WS server error:', data.error);
          return;
        }
        this._handleEvent(data);
      } catch(err) { console.error('[chat] ws parse:', err); }
    };
    this.ws.onclose = (ev) => {
      if (ev.code === 1000) {
        this.setStatus('idle');
        return;
      }
      if (this._wsSessionId && this.sessionId === this._wsSessionId) {
        const delay = Math.min(1000 * Math.pow(2, this._wsRetries), 10000);
        this._wsRetries++;
        this.setStatus(this._wsRetries <= 2 ? 'connecting...' : 'reconnecting...');
        setTimeout(() => {
          if (this.sessionId === this._wsSessionId) {
            this._connectWS(this._wsSessionId);
          }
        }, delay);
      } else {
        this.setStatus('idle');
      }
    };
    this.ws.onerror = () => {};
  }

  _disconnectWS() {
    if (this.ws) { try { this.ws.close(); } catch(e){} this.ws = null; }
    this._wsReady = false;
    this._wsSessionId = null;
  }

  _runSlashSSE(cmd) {
    const bodyObj = {prompt: cmd, session_id: this.sessionId || ''};
    if (this._richUserId) bodyObj.rich_user_id = this._richUserId;
    const body = JSON.stringify(bodyObj);
    fetch('/api/prompt', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'Accept': 'text/event-stream'},
      body,
    }).then(response => {
      if (!response.ok) {
        this._removeActivity();
        this._addError(`Server error (${response.status})`);
        return;
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      const processChunk = ({done, value}) => {
        if (done) {
          this._removeActivity();
          this.loadSessions();
          return;
        }
        buffer += decoder.decode(value, {stream: true});
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const evt = JSON.parse(line.slice(6));
              if (evt.type === 'session') {
                if (!this.sessionId) {
                  this.sessionId = evt.data.session_id;
                  this.loadSessions();
                }
              } else if (evt.type === 'done') {
                this._removeActivity();
                this.loadSessions();
              } else {
                this._handleEvent(evt);
              }
            } catch(e) { /* skip bad JSON */ }
          }
        }
        reader.read().then(processChunk);
      };
      reader.read().then(processChunk);
    }).catch(err => {
      this._removeActivity();
      this._addError('Connection error: ' + err.message);
    });
  }

  _ensureWS() {
    return new Promise(resolve => {
      if (this.ws && this.ws.readyState === 1 && this._wsReady) { resolve(); return; }
      if (!this.ws || this.ws.readyState >= 2) {
        if (this.sessionId) this._connectWS(this.sessionId);
      }
      let elapsed = 0;
      const iv = setInterval(() => {
        elapsed += 50;
        if (this.ws && this.ws.readyState === 1 && this._wsReady) {
          clearInterval(iv); resolve(); return;
        }
        if (elapsed >= 5000) { clearInterval(iv); resolve(); }
      }, 50);
    });
  }

  // ── Event dispatch ──────────────────────────────────────────────

  _handleEvent(evt) {
    switch (evt.type) {
      case 'text_chunk':
        this._removeActivity();
        if (!this._curMsgEl) this._startAssistantStream();
        this._textBuf += evt.data.text;
        this._renderStream();
        break;
      case 'thinking_chunk':
        this._showActivity('thinking', 'Thinking',
          evt.data.text ? evt.data.text.slice(0, 60) : '');
        break;
      case 'tool_start':
        this._removeActivity();
        this._addToolCard(evt.data.name, evt.data.inputs, 'running');
        this._showActivity('tool-running', `Running ${evt.data.name}`, '');
        break;
      case 'tool_end':
        this._removeActivity();
        this._completeToolCard(evt.data.name, evt.data.result, evt.data.permitted);
        // Forward navigation requests to RICH parent window
        if ((evt.data.name === 'navigate' || evt.data.name === 'open_symbol_chart') && window.parent !== window) {
          const match = (evt.data.result || '').match(/\[RICH_NAVIGATE\]\s+path=(\S+)\s+title=(.*)/);
          if (match) {
            window.parent.postMessage({
              type: 'navigate',
              path: match[1],
              title: match[2].trim(),
            }, '*');
          }
        }
        break;
      case 'permission_request':
        this._removeActivity();
        this._showApproval(evt.data.description);
        break;
      case 'permission_response':
        this._resolveApproval(evt.data.granted);
        break;
      case 'turn_done':
        this._removeActivity();
        this._finishTurn(evt.data.input_tokens, evt.data.output_tokens);
        break;
      case 'status':
        if (evt.data.state === 'running') {
          this.setStatus('running');
          this._showActivity('', 'Processing', '');
        } else if (evt.data.state === 'idle') {
          this._removeActivity();
          this.setStatus('connected');
          this.loadSessions();
        }
        break;
      case 'command_result':
        this._removeActivity();
        this._addCommandResult(evt.data.command, evt.data.output);
        break;
      case 'interactive_menu':
        this._removeActivity();
        this._addInteractiveMenu(evt.data);
        break;
      case 'input_request':
        this._removeActivity();
        this._addInputRequest(evt.data);
        break;
      case 'error':
        this._removeActivity();
        this._addError(evt.data.message);
        break;
    }
  }

  // ── Message rendering (bubbles + streaming) ────────────────────

  _clearChat() {
    const el = document.getElementById('messages');
    el.innerHTML = '<div style="flex:1"></div>';
    this._curMsgEl = null; this._thinkEl = null; this._activityEl = null;
    this._textBuf = ''; this._toolCards = {};
    this._toolCounter = 0; this._approvalEl = null;
    this._pendingApproval = false;
  }

  _addUserBubble(text, attachments = []) {
    const el = document.createElement('div');
    el.className = 'msg user';
    el.innerHTML = `<div class="role-tag">You</div><div class="bubble"></div>`;
    const bubble = el.querySelector('.bubble');
    bubble.textContent = text;
    if (attachments.length) {
      const list = document.createElement('div');
      list.style.marginTop = '8px';
      list.style.display = 'flex';
      list.style.gap = '6px';
      list.style.flexWrap = 'wrap';
      for (const item of attachments) {
        const chip = document.createElement('span');
        chip.style.fontSize = '11px';
        chip.style.opacity = '0.8';
        chip.textContent = `Attachment: ${item.name}`;
        list.appendChild(chip);
      }
      bubble.appendChild(list);
    }
    document.getElementById('messages').appendChild(el);
    this._scrollBottom();
  }

  _addAssistantBubble(content) {
    const el = document.createElement('div');
    el.className = 'msg assistant';
    el.innerHTML = `<div class="role-tag">Assistant</div><div class="bubble"></div>`;
    el.querySelector('.bubble').innerHTML = this._renderMd(content);
    document.getElementById('messages').appendChild(el);
    this._scrollBottom();
  }

  _startAssistantStream() {
    this._removeActivity();
    this._textBuf = '';
    const el = document.createElement('div');
    el.className = 'msg assistant';
    el.innerHTML = `<div class="role-tag">Assistant</div><div class="bubble"></div>`;
    document.getElementById('messages').appendChild(el);
    this._curMsgEl = el.querySelector('.bubble');
    this.streaming = true;
  }

  _renderStream() {
    if (!this._curMsgEl) return;
    if (!this._rafPending) {
      this._rafPending = true;
      requestAnimationFrame(() => {
        this._rafPending = false;
        if (this._curMsgEl) {
          this._curMsgEl.innerHTML = this._renderMd(this._textBuf);
          this._scrollBottom();
        }
      });
    }
  }

  _finishTurn(tokIn, tokOut) {
    this._removeActivity();
    this.streaming = false;
    this._curMsgEl = null;
    if (tokIn || tokOut) {
      const meta = document.createElement('div');
      meta.className = 'turn-meta';
      meta.textContent = `${(tokIn||0).toLocaleString()} tokens in / ${(tokOut||0).toLocaleString()} tokens out`;
      document.getElementById('messages').appendChild(meta);
    }
    this._scrollBottom();
  }

  _addError(msg) {
    const el = document.createElement('div');
    el.style.cssText = 'color:var(--red);font-size:13px;padding:8px 12px;background:var(--red-dim);border-radius:var(--radius-sm);margin:8px 0;max-width:min(640px,90%)';
    el.textContent = msg;
    document.getElementById('messages').appendChild(el);
    this._scrollBottom();
  }

  setStatus(state) {
    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-text');
    dot.className = 'dot' + (state==='disconnected'?' off':'') + (state==='running'?' busy':'');
    txt.textContent = state;
  }
}
