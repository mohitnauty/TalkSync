(function () {
  if (window.__talksyncMeetOverlayLoaded) {
    return;
  }
  window.__talksyncMeetOverlayLoaded = true;

  const PLATFORM_CONFIG = {
    google_meet: {
      label: "Google Meet",
      channel: "google_meet",
      captionSelectors: [
        '[data-panel-container-id="captions"]',
        '[jsname="dsyhDe"]',
        '[aria-live="polite"]',
        '[aria-live="assertive"]',
      ],
      captionHint: "Turn on Google Meet captions, then use caption mode for the fastest translation path.",
    },
    microsoft_teams: {
      label: "Microsoft Teams",
      channel: "microsoft_teams",
      captionSelectors: [
        '[data-tid="closed-captions-renderer"]',
        '[data-tid="caption-text"]',
        '[data-tid="live-caption"]',
        '[aria-live="polite"]',
        '[aria-live="assertive"]',
      ],
      captionHint: "Turn on Teams live captions, then use caption mode for the fastest translation path.",
    },
    web: {
      label: "Meeting",
      channel: "web",
      captionSelectors: [
        '[aria-live="polite"]',
        '[aria-live="assertive"]',
      ],
      captionHint: "Turn on platform captions if available, otherwise use audio capture.",
    },
    zoho_meeting: {
      label: "Zoho Meeting",
      channel: "zoho_meeting",
      captionSelectors: [
        '[aria-live="polite"]',
        '[aria-live="assertive"]',
        '.caption-message',
        '.captions-container',
      ],
      captionHint: "Turn on Zoho captions if available. Otherwise use audio capture.",
    },
  };

  function detectPlatform() {
    const host = window.location.hostname;
    const path = window.location.pathname;
    if (host.includes("meet.google.com")) {
      return "google_meet";
    }
    if (host.includes("teams.microsoft.com")) {
      return "microsoft_teams";
    }
    if (host.includes("zoho.com") || host.includes("meeting.zoho.com") || path.includes("/meeting/")) {
      return "zoho_meeting";
    }
    return "web";
  }

  const platformKey = detectPlatform();
  const platform = PLATFORM_CONFIG[platformKey];

  const state = {
    socket: null,
    stream: null,
    audioContext: null,
    mediaSource: null,
    processor: null,
    pcmFrames: [],
    audioRequestInFlight: false,
    pendingAudioPayload: null,
    speechActive: false,
    silenceFrames: 0,
    utteranceFrameCount: 0,
    isCapturing: false,
    captionObserver: null,
    captionPollId: null,
    seenCaptionText: "",
    isConnected: false,
    hasJoined: false,
    sessionId: null,
    dragPointerId: null,
    dragOffsetX: 0,
    dragOffsetY: 0,
  };

  const root = document.createElement("div");
  root.id = "talksync-root";
  root.innerHTML = `
    <div class="talksync-panel">
      <div class="talksync-header">
        <h2>TalkSync ${platform.label}</h2>
        <div class="talksync-status"><span class="talksync-status-dot" id="ts-dot"></span><span id="ts-status">Disconnected</span></div>
      </div>
      <div class="talksync-body">
        <div class="talksync-grid">
          <div class="talksync-field">
            <label>Target Language</label>
            <select id="ts-target">
              <option value="hi">Hindi</option>
              <option value="pa">Punjabi</option>
              <option value="en">English</option>
            </select>
          </div>
          <div class="talksync-field">
            <label>AI Tier</label>
            <select id="ts-tier">
              <option value="free">Free</option>
              <option value="paid">Paid</option>
            </select>
          </div>
        </div>
        <div class="talksync-actions">
          <button class="talksync-primary" id="ts-connect">Connect</button>
          <button class="talksync-secondary" id="ts-join" disabled>Join</button>
          <button class="talksync-primary" id="ts-capture" disabled>Capture ${platform.label} Audio</button>
          <button class="talksync-secondary" id="ts-captions" disabled>Use ${platform.label} Captions</button>
          <button class="talksync-secondary" id="ts-stop" disabled>Stop</button>
        </div>
        <div class="talksync-card">
          <h3>Caption</h3>
          <p class="talksync-live" id="ts-caption">Waiting for speech from ${platform.label}.</p>
        </div>
        <div class="talksync-card">
          <h3>Translation</h3>
          <p class="talksync-live" id="ts-translation">Translated output will appear here.</p>
        </div>
        <div class="talksync-card">
          <h3>Events</h3>
          <pre class="talksync-log" id="ts-log"></pre>
        </div>
      </div>
    </div>
  `;
  document.documentElement.appendChild(root);

  const els = {
    panel: root,
    header: root.querySelector(".talksync-header"),
    dot: root.querySelector("#ts-dot"),
    status: root.querySelector("#ts-status"),
    target: root.querySelector("#ts-target"),
    tier: root.querySelector("#ts-tier"),
    connect: root.querySelector("#ts-connect"),
    join: root.querySelector("#ts-join"),
    capture: root.querySelector("#ts-capture"),
    captions: root.querySelector("#ts-captions"),
    stop: root.querySelector("#ts-stop"),
    caption: root.querySelector("#ts-caption"),
    translation: root.querySelector("#ts-translation"),
    log: root.querySelector("#ts-log"),
  };

  function wsUrl() {
    return "ws://127.0.0.1:8000/ws/realtime";
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function setPanelPosition(left, top) {
    const maxLeft = Math.max(0, window.innerWidth - root.offsetWidth - 8);
    const maxTop = Math.max(0, window.innerHeight - root.offsetHeight - 8);
    root.style.left = `${clamp(left, 8, maxLeft)}px`;
    root.style.top = `${clamp(top, 8, maxTop)}px`;
    root.style.right = "auto";
  }

  function startDrag(event) {
    if (event.target.closest("button, select, input, audio")) {
      return;
    }

    state.dragPointerId = event.pointerId;
    const rect = root.getBoundingClientRect();
    state.dragOffsetX = event.clientX - rect.left;
    state.dragOffsetY = event.clientY - rect.top;
    els.header.setPointerCapture(event.pointerId);
  }

  function moveDrag(event) {
    if (state.dragPointerId !== event.pointerId) {
      return;
    }
    setPanelPosition(event.clientX - state.dragOffsetX, event.clientY - state.dragOffsetY);
  }

  function endDrag(event) {
    if (state.dragPointerId !== event.pointerId) {
      return;
    }
    try {
      els.header.releasePointerCapture(event.pointerId);
    } catch (_) {
      // Ignore pointer release issues from browser-specific edge cases.
    }
    state.dragPointerId = null;
  }

  function log(label, payload) {
    const line = `[${new Date().toLocaleTimeString()}] ${label}\n${JSON.stringify(payload, null, 2)}\n`;
    els.log.textContent = `${line}\n${els.log.textContent}`.trim();
  }

  function setStatus(connected, label) {
    state.isConnected = connected;
    els.status.textContent = label;
    els.dot.classList.toggle("live", connected);
    els.join.disabled = !connected;
    els.capture.disabled = !connected || !state.hasJoined;
    els.captions.disabled = !connected || !state.hasJoined;
    els.stop.disabled = !state.isCapturing && !state.captionObserver;
  }

  function updateButtons() {
    els.join.disabled = !state.isConnected;
    els.capture.disabled = !state.isConnected || !state.hasJoined || state.isCapturing;
    els.captions.disabled = !state.isConnected || !state.hasJoined || Boolean(state.captionObserver);
    els.stop.disabled = !state.isCapturing && !state.captionObserver;
  }

  function send(payload) {
    if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
      throw new Error("TalkSync socket is not connected.");
    }
    state.socket.send(JSON.stringify(payload));
    log("client_sent", payload);
  }

  function joinPayload() {
    return {
      event: "join_session",
      participant_id: `${platformKey}-listener`,
      participant_name: `${platform.label} Listener`,
      role: "listener",
      preferred_language: els.target.value,
      receive_audio: false,
      receive_transcript: true,
      session_config: {
        source_language: "en",
        target_language: els.target.value,
        detected_language: "en",
        auto_detect_language: true,
        translation_enabled: true,
        transcript_enabled: true,
        audio_output_enabled: false,
        ai_tier: els.tier.value,
        channel: platform.channel,
      },
    };
  }

  function handleServerEvent(event) {
    log("server_received", event);
    switch (event.event) {
      case "session_started":
        state.sessionId = event.session_id;
        break;
      case "participant_joined":
        state.hasJoined = true;
        updateButtons();
        break;
      case "caption":
        els.caption.textContent = event.text;
        break;
      case "translation":
        state.audioRequestInFlight = false;
        els.translation.textContent = event.text;
        flushPendingPayload();
        break;
      case "error":
        state.audioRequestInFlight = false;
        els.translation.textContent = `Error: ${event.message}`;
        flushPendingPayload();
        break;
    }
  }

  async function connect() {
    if (state.socket && state.socket.readyState === WebSocket.OPEN) {
      return;
    }
    state.socket = new WebSocket(wsUrl());
    setStatus(false, "Connecting...");

    state.socket.addEventListener("open", () => {
      setStatus(true, "Connected");
      updateButtons();
    });
    state.socket.addEventListener("message", (message) => {
      handleServerEvent(JSON.parse(message.data));
    });
    state.socket.addEventListener("close", () => {
      state.hasJoined = false;
      state.audioRequestInFlight = false;
      state.pendingAudioPayload = null;
      setStatus(false, "Disconnected");
      updateButtons();
    });
    state.socket.addEventListener("error", () => {
      setStatus(false, "Socket error");
    });
  }

  async function startCapture() {
    if (!state.hasJoined) {
      alert("Join the TalkSync session first.");
      return;
    }

    state.stream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
      },
    });

    state.audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 16000,
    });
    state.mediaSource = state.audioContext.createMediaStreamSource(state.stream);
    state.processor = state.audioContext.createScriptProcessor(4096, 1, 1);
    state.isCapturing = true;
    state.pcmFrames = [];
    state.speechActive = false;
    state.silenceFrames = 0;
    state.utteranceFrameCount = 0;

    state.processor.onaudioprocess = (audioEvent) => {
      const frame = new Float32Array(audioEvent.inputBuffer.getChannelData(0));
      const rms = calculateRms(frame);
      const isSpeech = rms > 0.01;

      if (isSpeech) {
        state.speechActive = true;
        state.silenceFrames = 0;
        state.pcmFrames.push(frame);
        state.utteranceFrameCount += 1;
        return;
      }

      if (state.speechActive) {
        state.pcmFrames.push(frame);
        state.silenceFrames += 1;
        state.utteranceFrameCount += 1;
        if (state.silenceFrames >= 2 || state.utteranceFrameCount >= 18) {
          flushAudioChunk();
        }
      }
    };

    state.mediaSource.connect(state.processor);
    state.processor.connect(state.audioContext.destination);

    const [videoTrack] = state.stream.getVideoTracks();
    if (videoTrack) {
      videoTrack.addEventListener("ended", stopCapture);
    }

    updateButtons();
  }

  function startCaptionMode() {
    if (!state.hasJoined) {
      alert("Join the TalkSync session first.");
      return;
    }

    stopCapture();
    state.seenCaptionText = "";
    els.translation.textContent = platform.captionHint;

    const scanCaptions = () => {
      const text = readMeetCaptionsText();
      if (!text || text === state.seenCaptionText) {
        return;
      }
      state.seenCaptionText = text;
      els.caption.textContent = text;
      sendTextChunk(text);
    };

    state.captionObserver = new MutationObserver(scanCaptions);
    state.captionObserver.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
    });
    state.captionPollId = window.setInterval(scanCaptions, 700);
    scanCaptions();
    updateButtons();
  }

  function stopCapture() {
    flushAudioChunk();
    if (state.processor) {
      state.processor.disconnect();
      state.processor.onaudioprocess = null;
      state.processor = null;
    }
    if (state.mediaSource) {
      state.mediaSource.disconnect();
      state.mediaSource = null;
    }
    if (state.audioContext) {
      state.audioContext.close();
      state.audioContext = null;
    }
    if (state.stream) {
      state.stream.getTracks().forEach((track) => track.stop());
      state.stream = null;
    }
    state.isCapturing = false;
    state.speechActive = false;
    state.silenceFrames = 0;
    state.utteranceFrameCount = 0;
    state.pcmFrames = [];
    if (state.captionObserver) {
      state.captionObserver.disconnect();
      state.captionObserver = null;
    }
    if (state.captionPollId) {
      window.clearInterval(state.captionPollId);
      state.captionPollId = null;
    }
    updateButtons();
  }

  async function flushAudioChunk() {
    if (!state.pcmFrames.length || !state.isConnected || !state.hasJoined) {
      return;
    }

    const wavBuffer = encodeWav(state.pcmFrames, state.audioContext?.sampleRate || 16000);
    const payload = {
      event: "audio_chunk",
      participant_id: `${platformKey}-listener`,
      chunk: await arrayBufferToBase64(wavBuffer),
      content_type: "audio/wav",
      source_language: "en",
      target_language: els.target.value,
    };

    state.pcmFrames = [];
    state.speechActive = false;
    state.silenceFrames = 0;
    state.utteranceFrameCount = 0;

    if (state.audioRequestInFlight) {
      state.pendingAudioPayload = payload;
      return;
    }

    state.audioRequestInFlight = true;
    send(payload);
  }

  function flushPendingPayload() {
    if (!state.pendingAudioPayload || state.audioRequestInFlight) {
      return;
    }
    const payload = state.pendingAudioPayload;
    state.pendingAudioPayload = null;
    state.audioRequestInFlight = true;
    send(payload);
  }

  function sendTextChunk(text) {
    if (state.audioRequestInFlight) {
      state.pendingAudioPayload = {
        event: "text_chunk",
        participant_id: `${platformKey}-listener`,
        text,
        source_language: "en",
        target_language: els.target.value,
      };
      return;
    }
    state.audioRequestInFlight = true;
    send({
      event: "text_chunk",
      participant_id: `${platformKey}-listener`,
      text,
      source_language: "en",
      target_language: els.target.value,
    });
  }

  function readMeetCaptionsText() {
    const parts = [];
    for (const selector of platform.captionSelectors) {
      document.querySelectorAll(selector).forEach((node) => {
        const text = node.textContent?.trim();
        if (text) {
          parts.push(text);
        }
      });
    }

    const unique = [...new Set(parts.map((item) => item.replace(/\s+/g, " ").trim()))];
    return unique.join(" ").trim();
  }

  async function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    const chunkSize = 0x8000;
    for (let i = 0; i < bytes.length; i += chunkSize) {
      binary += String.fromCharCode(...bytes.slice(i, i + chunkSize));
    }
    return btoa(binary);
  }

  function encodeWav(frames, sampleRate) {
    const merged = mergeFrames(frames);
    const pcm16 = floatTo16BitPCM(merged);
    const buffer = new ArrayBuffer(44 + pcm16.length * 2);
    const view = new DataView(buffer);

    writeAscii(view, 0, "RIFF");
    view.setUint32(4, 36 + pcm16.length * 2, true);
    writeAscii(view, 8, "WAVE");
    writeAscii(view, 12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeAscii(view, 36, "data");
    view.setUint32(40, pcm16.length * 2, true);

    let offset = 44;
    for (const sample of pcm16) {
      view.setInt16(offset, sample, true);
      offset += 2;
    }
    return buffer;
  }

  function mergeFrames(frames) {
    const total = frames.reduce((sum, frame) => sum + frame.length, 0);
    const merged = new Float32Array(total);
    let offset = 0;
    for (const frame of frames) {
      merged.set(frame, offset);
      offset += frame.length;
    }
    return merged;
  }

  function floatTo16BitPCM(float32Array) {
    const pcm16 = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i += 1) {
      const sample = Math.max(-1, Math.min(1, float32Array[i]));
      pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }
    return pcm16;
  }

  function writeAscii(view, offset, text) {
    for (let i = 0; i < text.length; i += 1) {
      view.setUint8(offset + i, text.charCodeAt(i));
    }
  }

  function calculateRms(frame) {
    let sum = 0;
    for (let i = 0; i < frame.length; i += 1) {
      sum += frame[i] * frame[i];
    }
    return Math.sqrt(sum / frame.length);
  }

  els.connect.addEventListener("click", () => {
    connect().catch((error) => {
      log("connect_error", { message: error.message });
    });
  });

  els.join.addEventListener("click", () => {
    try {
      send(joinPayload());
    } catch (error) {
      log("join_error", { message: error.message });
    }
  });

  els.capture.addEventListener("click", () => {
    startCapture().catch((error) => {
      log("capture_error", { message: error.message });
      els.translation.textContent = `Capture error: ${error.message}`;
    });
  });

  els.captions.addEventListener("click", () => {
    try {
      startCaptionMode();
    } catch (error) {
      log("caption_mode_error", { message: error.message });
      els.translation.textContent = `Caption mode error: ${error.message}`;
    }
  });

  els.stop.addEventListener("click", stopCapture);
  els.header.addEventListener("pointerdown", startDrag);
  els.header.addEventListener("pointermove", moveDrag);
  els.header.addEventListener("pointerup", endDrag);
  els.header.addEventListener("pointercancel", endDrag);
  window.addEventListener("resize", () => {
    const rect = root.getBoundingClientRect();
    setPanelPosition(rect.left, rect.top);
  });

  setStatus(false, "Disconnected");
  updateButtons();
})();
