// Fallback audio player for old browsers (iOS 9 / Safari 9). Classic script,
// no ES modules / fetch / IntersectionObserver / wavesurfer. Uses a native
// <audio> element and a hand-drawn <canvas> waveform from the precomputed peaks.
// Speed control is omitted here (iOS 9 has no working <audio>.playbackRate);
// the modern player.js provides it via progressive enhancement.
(function () {
  'use strict';

  // Browsers that support ES modules run player.js instead; don't double-init.
  if ('noModule' in HTMLScriptElement.prototype) return;

  var registry = [];

  function ensurePlayer(el) {
    for (var i = 0; i < registry.length; i++) {
      if (registry[i].el === el) return registry[i].api;
    }
    var api = initPlayer(el);
    registry.push({ el: el, api: api });
    return api;
  }
  window.__ensurePlayer = ensurePlayer;

  function fmt(s) {
    if (!isFinite(s) || s < 0) s = 0;
    var m = Math.floor(s / 60), ss = Math.floor(s % 60);
    return m + ':' + (ss < 10 ? '0' + ss : ss);
  }

  function findWords(root) {
    var n = root.nextElementSibling;
    while (n && !(n.classList && n.classList.contains('source-text'))) n = n.nextElementSibling;
    if (!n) return [];
    return Array.prototype.slice.call(n.querySelectorAll('[data-t0]'));
  }

  function initPlayer(root) {
    var words = findWords(root);
    var peaks = null, duration = 0, segEnd = null, activeWord = null;

    var audio = document.createElement('audio');
    audio.preload = 'metadata';
    audio.src = root.getAttribute('data-audio');
    root.appendChild(audio);

    // Speed isn't available here; hide the control the markup ships with.
    var speedLabel = root.querySelector('.ap-speed-label');
    if (speedLabel) speedLabel.style.display = 'none';

    var waveBox = root.querySelector('.ap-wave');
    var canvas = document.createElement('canvas');
    canvas.className = 'ap-canvas';
    waveBox.appendChild(canvas);
    var ctx = canvas.getContext('2d');

    function sizeCanvas() {
      var dpr = window.devicePixelRatio || 1;
      var w = waveBox.clientWidth || 300, h = 48;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function draw() {
      if (!peaks) return;
      var w = canvas.width / (window.devicePixelRatio || 1);
      var h = canvas.height / (window.devicePixelRatio || 1);
      ctx.clearRect(0, 0, w, h);
      var n = peaks.length;
      var bw = w / n;
      var prog = duration ? audio.currentTime / duration : 0;
      for (var i = 0; i < n; i++) {
        var bh = Math.max(1, peaks[i] * h);
        ctx.fillStyle = (i / n) <= prog ? '#4a90e2' : '#9aa7b4';
        ctx.fillRect(i * bw, (h - bh) / 2, Math.max(1, bw - 1), bh);
      }
    }

    // Load peaks via XHR (no fetch on iOS 9).
    var durEl = root.querySelector('.ap-dur'), curEl = root.querySelector('.ap-cur');
    var xhr = new XMLHttpRequest();
    xhr.open('GET', root.getAttribute('data-peaks'), true);
    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4) return;
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          var pj = JSON.parse(xhr.responseText);
          peaks = pj.peaks;
          duration = pj.duration || 0;
          sizeCanvas();
          draw();
          if (durEl) durEl.textContent = fmt(duration);
        } catch (e) { /* leave waveform blank; audio still works */ }
      }
    };
    xhr.send();

    // Seek by clicking the waveform.
    canvas.addEventListener('click', function (e) {
      if (!duration) return;
      var r = canvas.getBoundingClientRect();
      audio.currentTime = Math.max(0, Math.min(duration, (e.clientX - r.left) / r.width * duration));
    });

    var playBtn = root.querySelector('.ap-play');
    audio.addEventListener('play',  function () { if (playBtn) playBtn.innerHTML = '⏸'; });
    audio.addEventListener('pause', function () { if (playBtn) playBtn.innerHTML = '▶'; });
    if (playBtn) playBtn.onclick = function () {
      segEnd = null;
      if (audio.paused) audio.play(); else audio.pause();
    };
    var back = root.querySelector('.ap-back'), fwd = root.querySelector('.ap-fwd');
    if (back) back.onclick = function () { audio.currentTime = Math.max(0, audio.currentTime - 5); };
    if (fwd)  fwd.onclick  = function () { audio.currentTime = Math.min(duration || audio.duration || 0, audio.currentTime + 5); };

    audio.addEventListener('loadedmetadata', function () {
      if (!duration && isFinite(audio.duration)) { duration = audio.duration; if (durEl) durEl.textContent = fmt(duration); }
    });

    audio.addEventListener('timeupdate', function () {
      var t = audio.currentTime;
      if (curEl) curEl.textContent = fmt(t);
      if (segEnd !== null && t >= segEnd) { audio.pause(); segEnd = null; }
      // Highlight current word.
      var next = null;
      for (var i = 0; i < words.length; i++) {
        if (t >= +words[i].getAttribute('data-t0') && t < +words[i].getAttribute('data-t1')) { next = words[i]; break; }
      }
      if (next !== activeWord) {
        if (activeWord) activeWord.className = activeWord.className.replace(/ ?ap-active/, '');
        if (next && next.className.indexOf('ap-active') === -1) next.className += ' ap-active';
        activeWord = next;
      }
      draw();
    });
    audio.addEventListener('ended', function () {
      if (activeWord) { activeWord.className = activeWord.className.replace(/ ?ap-active/, ''); activeWord = null; }
      draw();
    });

    var resizeTimer = null;
    window.addEventListener('resize', function () {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () { sizeCanvas(); draw(); }, 150);
    });

    return {
      playSegment: function (t0, t1) {
        segEnd = t1;
        audio.currentTime = t0;
        audio.play();
      }
    };
  }

  function initAll() {
    var players = document.querySelectorAll('.audio-player');
    for (var i = 0; i < players.length; i++) ensurePlayer(players[i]);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
}());
