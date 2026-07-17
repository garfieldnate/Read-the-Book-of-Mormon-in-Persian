// Modern audio player (browsers with ES modules). Uses wavesurfer.js for the
// waveform + playback, with a precomputed-peaks fast path. Old browsers get
// player-legacy.js instead (loaded via nomodule). Word taps are handled by the
// shared word-popup.js, which calls window.__ensurePlayer(playerEl).playSegment.

const players = document.querySelectorAll('.audio-player');

if (players.length) {
  const { default: WaveSurfer } = await import('./vendor/wavesurfer.esm.js');

  const fmt = (s) => {
    if (!isFinite(s) || s < 0) s = 0;
    const m = Math.floor(s / 60);
    return m + ':' + String(Math.floor(s % 60)).padStart(2, '0');
  };

  const findWords = (root) => {
    let n = root.nextElementSibling;
    while (n && !n.classList.contains('source-text')) n = n.nextElementSibling;
    return n ? [...n.querySelectorAll('[data-t0]')] : [];
  };

  const registry = new Map();

  // Cached, sync-returning handle so the popup can call playSegment immediately;
  // the actual wavesurfer instance is attached once its async init resolves.
  function ensurePlayer(el) {
    if (registry.has(el)) return registry.get(el);
    const api = { ws: null, segEnd: null };
    api.ready = initPlayer(el, api);
    api.playSegment = (t0, t1) => api.ready.then(() => {
      if (!api.ws) return;
      api.segEnd = t1;
      api.ws.setTime(t0);
      api.ws.play();
    });
    registry.set(el, api);
    return api;
  }
  window.__ensurePlayer = ensurePlayer;

  async function initPlayer(root, api) {
    const q = (sel) => root.querySelector(sel);
    const words = findWords(root);

    let peaks, duration;
    try {
      const pj = await (await fetch(root.dataset.peaks)).json();
      peaks = [pj.peaks];
      duration = pj.duration;
    } catch { /* fall back to client-side decode */ }

    const ws = WaveSurfer.create({
      container: q('.ap-wave'),
      height: 48,
      waveColor: '#9aa7b4',
      progressColor: '#4a90e2',
      cursorColor: '#e8a33d',
      barWidth: 2, barGap: 1, barRadius: 2,
      url: root.dataset.audio,
      peaks, duration,
    });
    api.ws = ws;

    const curEl = q('.ap-cur'), durEl = q('.ap-dur');
    if (duration) durEl.textContent = fmt(duration);
    ws.on('ready', () => { durEl.textContent = fmt(ws.getDuration()); });

    let activeWord = null;
    ws.on('timeupdate', (t) => {
      curEl.textContent = fmt(t);
      if (api.segEnd !== null && t >= api.segEnd) { ws.pause(); api.segEnd = null; }
      let next = null;
      for (const w of words) {
        if (t >= +w.dataset.t0 && t < +w.dataset.t1) { next = w; break; }
      }
      if (next !== activeWord) {
        if (activeWord) activeWord.classList.remove('ap-active');
        if (next) next.classList.add('ap-active');
        activeWord = next;
      }
    });
    ws.on('finish', () => { if (activeWord) { activeWord.classList.remove('ap-active'); activeWord = null; } });

    const play = q('.ap-play');
    ws.on('play',  () => { play.textContent = '⏸'; play.setAttribute('aria-label', 'Pause'); });
    ws.on('pause', () => { play.textContent = '▶'; play.setAttribute('aria-label', 'Play'); });
    play.onclick = () => { api.segEnd = null; ws.playPause(); };
    q('.ap-back').onclick   = () => ws.setTime(Math.max(0, ws.getCurrentTime() - 5));
    q('.ap-fwd').onclick    = () => ws.setTime(Math.min(ws.getDuration(), ws.getCurrentTime() + 5));
    q('.ap-speed').onchange = (e) => ws.setPlaybackRate(parseFloat(e.target.value), true);
  }

  // Draw each waveform as it nears the viewport.
  const io = new IntersectionObserver((entries) => {
    for (const en of entries) {
      if (en.isIntersecting) { io.unobserve(en.target); ensurePlayer(en.target); }
    }
  }, { rootMargin: '250px' });
  players.forEach((p) => io.observe(p));
}
