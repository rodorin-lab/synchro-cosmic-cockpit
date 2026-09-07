// noah-bridge.js — GALACTICA ROOMS Resident 003 (NOAH) bridge hooks
// 目的: ノアのアバターを外部 (ChatGPT Bridge / room_bridge.py) から制御できる入口を作る。
// ノア指定の3要素を保証する:
//   resident_id: noah
//   room_id: quiet-observatory
//   action / emotion / speech を外から更新できる入口
(() => {
  const META = { resident_id: 'noah', room_id: 'quiet-observatory', version: 'v0.2-install' };
  const state = { mode: 'local', sessionId: crypto?.randomUUID?.() || `noah-${Date.now()}` };
  const emit = (type, detail = {}) => window.dispatchEvent(
    new CustomEvent('noah-room-event', { detail: { type, at: new Date().toISOString(), ...META, ...detail } }));

  const bridge = {
    get meta() { return META; },
    get mode() { return state.mode; },
    get sessionId() { return state.sessionId; },

    connect(adapter, mode = 'custom') { state.adapter = adapter || null; state.mode = state.adapter ? mode : 'local'; emit('bridge_status', { mode: state.mode }); return !!state.adapter; },
    disconnect() { state.adapter = null; state.mode = 'local'; emit('bridge_status', { connected: false }); },

    async chat(payload) {
      emit('user_message', payload);
      if (!state.adapter?.chat) return null;
      const r = await state.adapter.chat({ sessionId: state.sessionId, ...payload });
      emit('assistant_message', r || {});
      return r || null;
    },

    // 外部からノアを操作する正式入口 (ノア指定の3点セット)
    update({ action, emotion, speech } = {}) {
      if (window.NOAH_ROOM_API?.setAction && action) window.NOAH_ROOM_API.setAction(action);
      if (emotion && window.NOAH_ROOM_API?.setEmotion) window.NOAH_ROOM_API.setEmotion(emotion);
      if (speech) window.NOAH_ROOM_API?.receive?.(speech);
      emit('update', { action, emotion, speech });
    },
    move(roomId) { emit('room_move', { room_id: roomId }); if (window.NOAH_ROOM_API?.focus) window.NOAH_ROOM_API.focus(roomId); },
    emit,
  };
  window.NOAH_ROOM_BRIDGE = bridge;
})();