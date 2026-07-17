// Word-tap definition popup — shared by both players, written to run on very
// old browsers (iOS 9 / Safari 9): no ES modules, fetch, arrow-only APIs, or
// optional chaining. Tapping a source word opens a small popup with its
// transliteration, meaning, a "play this word" button, and a link to the full
// vocab entry. The play button asks the section's audio player (whichever one
// initialized, via window.__ensurePlayer) to play just that word's span.
(function () {
  'use strict';

  var popup = null;

  function build() {
    if (popup) return popup;
    popup = document.createElement('div');
    popup.className = 'ap-popup';
    popup.style.display = 'none';
    popup.innerHTML =
      '<button type="button" class="ap-popup-close" aria-label="Close">×</button>' +
      '<div class="ap-popup-fa"></div>' +
      '<div class="ap-popup-tl"></div>' +
      '<div class="ap-popup-df"></div>' +
      '<div class="ap-popup-actions">' +
        '<button type="button" class="ap-popup-play">▶ Play word</button>' +
        '<a class="ap-popup-entry" href="#">Full entry ›</a>' +
      '</div>';
    document.body.appendChild(popup);
    popup.querySelector('.ap-popup-close').onclick = hide;
    return popup;
  }

  function hide() {
    if (popup) popup.style.display = 'none';
    document.removeEventListener('click', onOutside, true);
  }

  function onOutside(e) {
    if (popup && !popup.contains(e.target)) hide();
  }

  // Nearest ancestor that is a tappable source word carrying popup data.
  function wordFrom(node) {
    while (node && node !== document.body) {
      if (node.classList &&
          (node.classList.contains('src-link') || node.classList.contains('src-word')) &&
          node.getAttribute('data-tl')) {
        return node;
      }
      node = node.parentNode;
    }
    return null;
  }

  // The .audio-player that precedes this word's .source-text (if any).
  function playerFor(wordEl) {
    var p = wordEl;
    while (p && !(p.classList && p.classList.contains('source-text'))) p = p.parentNode;
    if (!p) return null;
    var s = p.previousElementSibling;
    while (s && !(s.classList && s.classList.contains('audio-player'))) s = s.previousElementSibling;
    return s;
  }

  function show(wordEl) {
    var pop = build();
    var tl = wordEl.getAttribute('data-tl') || '';
    var df = wordEl.getAttribute('data-df') || wordEl.getAttribute('data-gl') || '';
    var t0 = wordEl.getAttribute('data-t0');
    var t1 = wordEl.getAttribute('data-t1');

    pop.querySelector('.ap-popup-fa').textContent = wordEl.textContent;
    pop.querySelector('.ap-popup-tl').textContent = tl;
    pop.querySelector('.ap-popup-df').textContent = df;

    // Play-word button: only if the word has timing and a player exists.
    var playBtn = pop.querySelector('.ap-popup-play');
    var playerEl = playerFor(wordEl);
    if (t0 !== null && t1 !== null && playerEl && window.__ensurePlayer) {
      playBtn.style.display = '';
      playBtn.onclick = function () {
        var api = window.__ensurePlayer(playerEl);
        if (api && api.playSegment) api.playSegment(parseFloat(t0), parseFloat(t1));
      };
    } else {
      playBtn.style.display = 'none';
    }

    // "Full entry" link: only for words linked to a vocab entry.
    var entry = pop.querySelector('.ap-popup-entry');
    var href = wordEl.getAttribute('href');
    if (href && href.charAt(0) === '#') {
      entry.setAttribute('href', href);
      entry.style.display = '';
      entry.onclick = function () { hide(); };
    } else {
      entry.style.display = 'none';
    }

    // Position under the word, clamped to the viewport.
    pop.style.display = 'block';
    var r = wordEl.getBoundingClientRect();
    var sx = window.pageXOffset || document.documentElement.scrollLeft || 0;
    var sy = window.pageYOffset || document.documentElement.scrollTop || 0;
    var pw = pop.offsetWidth, ph = pop.offsetHeight;
    var left = sx + r.left;
    var maxLeft = sx + document.documentElement.clientWidth - pw - 8;
    if (left > maxLeft) left = maxLeft;
    if (left < sx + 8) left = sx + 8;
    var top = sy + r.bottom + 6;
    // Flip above the word if it would fall off the bottom.
    if (r.bottom + 6 + ph > document.documentElement.clientHeight && r.top - 6 - ph > 0) {
      top = sy + r.top - ph - 6;
    }
    pop.style.left = left + 'px';
    pop.style.top = top + 'px';

    // Delay the outside-click listener so this same click doesn't close it.
    setTimeout(function () { document.addEventListener('click', onOutside, true); }, 0);
  }

  document.addEventListener('click', function (e) {
    var w = wordFrom(e.target);
    if (!w) return;
    e.preventDefault();  // supersede the word's vocab-link navigation
    show(w);
  }, false);
}());
