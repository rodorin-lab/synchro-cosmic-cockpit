(() => {
  const state = {
    adapter: null,
    mode: 'local-demo',
    connected: false,
    sessionId: crypto?.randomUUID?.() || `rei-${Date.now()}`
  };

  const emit = (type, detail = {}) => {
    window.dispatchEvent(new CustomEvent('rei-room-event', {
      detail: { type, at: new Date().toISOString(), sessionId: state.sessionId, ...detail }
    }));
  };

  const bridge = {
    get mode() { return state.mode; },
    get connected() { return state.connected; },
    get sessionId() { return state.sessionId; },

    connect(adapter, mode = 'custom') {
      state.adapter = adapter || null;
      state.connected = !!adapter;
      state.mode = state.connected ? mode : 'local-demo';
      emit('bridge_status', { connected: state.connected, mode: state.mode });
      return state.connected;
    },

    disconnect() {
      state.adapter = null;
      state.connected = false;
      state.mode = 'local-demo';
      emit('bridge_status', { connected: false, mode: state.mode });
    },

    async chat(payload) {
      emit('user_message', payload);
      if (!state.adapter?.chat) return null;
      try {
        const result = await state.adapter.chat({ sessionId: state.sessionId, ...payload });
        emit('assistant_message', result || {});
        return result || null;
      } catch (error) {
        console.warn('[REI bridge] chat failed:', error);
        emit('bridge_error', { phase: 'chat', message: String(error?.message || error) });
        return null;
      }
    },

    async startCall(payload = {}) {
      emit('call_start', payload);
      if (!state.adapter?.startCall) return null;
      return state.adapter.startCall({ sessionId: state.sessionId, ...payload });
    },

    async stopCall(payload = {}) {
      emit('call_stop', payload);
      if (!state.adapter?.stopCall) return null;
      return state.adapter.stopCall({ sessionId: state.sessionId, ...payload });
    },

    async pushAudio(payload = {}) {
      if (!state.adapter?.pushAudio) return null;
      return state.adapter.pushAudio({ sessionId: state.sessionId, ...payload });
    },

    emit
  };

  // Handy HTTP adapter for Gram/Hermes or another local backend.
  // Example:
  // REI_ROOM_BRIDGE.connect(REI_ROOM_BRIDGE.createHttpAdapter({chatUrl:'http://127.0.0.1:8642/rei/chat'}),'gram-http')
  bridge.createHttpAdapter = ({ chatUrl, headers = {}, credentials = 'omit' } = {}) => ({
    async chat(payload) {
      if (!chatUrl) throw new Error('chatUrl is required');
      const res = await fetch(chatUrl, {
        method: 'POST',
        headers: { 'content-type': 'application/json', ...headers },
        credentials,
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    }
  });

  window.REI_ROOM_BRIDGE = bridge;
})();
