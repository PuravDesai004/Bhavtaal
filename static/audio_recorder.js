/* Browser-native, in-memory mono PCM recorder. It never writes microphone data to disk. */
(function () {
  const TARGET_RATE = 16000;

  function wavFromFloat(samples, sampleRate) {
    if (!samples || samples.length === 0) throw new Error("No microphone audio was captured. Please try again.");
    if (!Number.isFinite(sampleRate) || sampleRate <= 0) throw new Error("The microphone returned an invalid sample rate.");
    const ratio = sampleRate / TARGET_RATE;
    const outputLength = Math.max(1, Math.round(samples.length / ratio));
    const pcm = new Int16Array(outputLength);
    for (let i = 0; i < outputLength; i += 1) {
      let value;
      if (sampleRate < TARGET_RATE) {
        const position = Math.min(samples.length - 1, i * ratio);
        const left = Math.floor(position);
        const right = Math.min(samples.length - 1, left + 1);
        const fraction = position - left;
        value = samples[left] * (1 - fraction) + samples[right] * fraction;
      } else {
        const start = i * ratio;
        const end = Math.min(samples.length, (i + 1) * ratio);
        let weighted = 0; let weightTotal = 0;
        for (let j = Math.floor(start); j < Math.ceil(end); j += 1) {
          const weight = Math.max(0, Math.min(end, j + 1) - Math.max(start, j));
          weighted += samples[j] * weight; weightTotal += weight;
        }
        value = weighted / Math.max(Number.EPSILON, weightTotal);
      }
      value = Math.max(-1, Math.min(1, value));
      pcm[i] = value < 0 ? value * 32768 : value * 32767;
    }

    const buffer = new ArrayBuffer(44 + pcm.length * 2);
    const view = new DataView(buffer);
    const write = (offset, text) => { for (let i = 0; i < text.length; i += 1) view.setUint8(offset + i, text.charCodeAt(i)); };
    write(0, "RIFF"); view.setUint32(4, 36 + pcm.length * 2, true); write(8, "WAVE");
    write(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
    view.setUint16(22, 1, true); view.setUint32(24, TARGET_RATE, true);
    view.setUint32(28, TARGET_RATE * 2, true); view.setUint16(32, 2, true);
    view.setUint16(34, 16, true); write(36, "data"); view.setUint32(40, pcm.length * 2, true);
    for (let i = 0; i < pcm.length; i += 1) view.setInt16(44 + i * 2, pcm[i], true);
    return new Uint8Array(buffer);
  }

  function toBase64(bytes) {
    let binary = "";
    const size = 0x8000;
    for (let offset = 0; offset < bytes.length; offset += size) {
      binary += String.fromCharCode.apply(null, bytes.subarray(offset, offset + size));
    }
    return btoa(binary);
  }

  class MolAudioRecorder {
    constructor(canvas, onTick) {
      this.canvas = canvas;
      this.onTick = onTick || function () {};
      this.context = null;
      this.stream = null;
      this.chunks = [];
      this.recording = false;
      this.starting = false;
      this.startedAt = 0;
      this.frame = null;
      this.timer = null;
      this._cleanupPromise = null;
    }

    async start() {
      if (this.recording || this.starting) return false;
      const getMedia = navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
      if (!getMedia) throw new Error("This browser does not support microphone capture.");
      this.starting = true;
      try {
        if (this._cleanupPromise) await this._cleanupPromise;
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) throw new Error("This browser does not support microphone audio processing.");
        this.context = new AudioContext();
        await this.context.resume();
        this.chunks = [];
        const source = this.context.createMediaStreamSource(this.stream);
        const processor = this.context.createScriptProcessor(2048, 1, 1);
        const silent = this.context.createGain(); silent.gain.value = 0;
        processor.onaudioprocess = (event) => {
          if (!this.recording) return;
          const input = event.inputBuffer.getChannelData(0);
          this.chunks.push(new Float32Array(input));
          this.draw(input);
        };
        source.connect(processor); processor.connect(silent); silent.connect(this.context.destination);
        this.processor = processor; this.source = source; this.silent = silent;
        this.recording = true; this.startedAt = performance.now();
        this.timer = window.setInterval(() => {
          const seconds = Math.min(10, (performance.now() - this.startedAt) / 1000);
          this.onTick(seconds);
          if (seconds >= 10) window.dispatchEvent(new Event("molbhaav-recording-limit"));
        }, 100);
        return true;
      } catch (error) {
        await this.cleanup();
        throw error;
      } finally {
        this.starting = false;
      }
    }

    draw(input) {
      const canvas = this.canvas;
      if (!canvas) return;
      const context = canvas.getContext("2d");
      const width = canvas.width; const height = canvas.height;
      context.clearRect(0, 0, width, height);
      const loudness = input ? Math.min(1, input.reduce((sum, value) => sum + Math.abs(value), 0) / input.length * 5) : .3;
      context.strokeStyle = "#dc2626"; context.lineWidth = 4;
      context.beginPath(); context.arc(width / 2, height / 2, 72 + loudness * 10, 0, Math.PI * 2); context.stroke();
      context.strokeStyle = "rgba(220,38,38,.24)"; context.lineWidth = 3;
      context.beginPath(); context.arc(width / 2, height / 2, 83 + loudness * 11, 0, Math.PI * 2); context.stroke();
    }

    async stop() {
      if (!this.recording) return null;
      const duration = (performance.now() - this.startedAt) / 1000;
      this.recording = false;
      let result = null;
      let captureError = null;
      try {
        if (duration < 1.5) return null;
        const sampleRate = this.context?.sampleRate;
        const total = this.chunks.reduce((sum, chunk) => sum + chunk.length, 0);
        if (total === 0) throw new Error("No microphone audio was captured. Please try again.");
        const joined = new Float32Array(total);
        let cursor = 0; let squareTotal = 0;
        for (const chunk of this.chunks) {
          joined.set(chunk, cursor); cursor += chunk.length;
          for (let i = 0; i < chunk.length; i += 1) squareTotal += chunk[i] * chunk[i];
        }
        const rms = Math.sqrt(squareTotal / total);
        if (rms < 0.001) throw new Error("We didn't hear any speech. Move closer to the mic and try again.");
        result = { audio_b64: toBase64(wavFromFloat(joined, sampleRate)), duration };
      } catch (error) {
        captureError = error;
      } finally {
        await this.cleanup();
      }
      if (captureError) throw captureError;
      return result;
    }

    cleanup() {
      this.recording = false;
      window.clearInterval(this.timer);
      if (this.frame) cancelAnimationFrame(this.frame);
      const nodes = [this.processor, this.source, this.silent];
      const stream = this.stream;
      const context = this.context;
      this.chunks = [];
      this.stream = this.context = this.processor = this.source = this.silent = this.timer = this.frame = null;
      for (const node of nodes) {
        try { node?.disconnect(); } catch (_) { /* already disconnected */ }
      }
      stream?.getTracks().forEach((track) => track.stop());
      if (this.canvas) this.canvas.getContext("2d").clearRect(0, 0, this.canvas.width, this.canvas.height);
      if (!context || context.state === "closed") return Promise.resolve();
      const closing = Promise.resolve()
        .then(() => context.close())
        .catch(() => { /* context shutdown is best effort */ })
        .finally(() => {
          if (this._cleanupPromise === closing) this._cleanupPromise = null;
        });
      this._cleanupPromise = closing;
      return closing;
    }
  }

  let muted = false;
  let audioContext = null;
  window.setBazaarMuted = (value) => { muted = Boolean(value); };
  window.playBazaarSound = async (kind) => {
    if (muted) return;
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      audioContext = audioContext || new AudioContext();
      await audioContext.resume();
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      oscillator.connect(gain); gain.connect(audioContext.destination);
      const now = audioContext.currentTime;
      const frequencies = kind === "lock" ? [740, 980] : kind === "buzzer" ? [180, 95] : [540, 820];
      oscillator.type = kind === "buzzer" ? "sawtooth" : "sine";
      oscillator.frequency.setValueAtTime(frequencies[0], now);
      oscillator.frequency.exponentialRampToValueAtTime(frequencies[1], now + .14);
      gain.gain.setValueAtTime(.0001, now); gain.gain.exponentialRampToValueAtTime(.11, now + .015);
      gain.gain.exponentialRampToValueAtTime(.0001, now + .2);
      oscillator.start(now); oscillator.stop(now + .22);
    } catch (_) { /* sound is optional */ }
  };
  MolAudioRecorder.encodePcm16Wav = wavFromFloat;
  window.MolAudioRecorder = MolAudioRecorder;
})();
