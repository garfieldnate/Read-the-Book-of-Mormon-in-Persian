// Word-tap definition popup — shared by both players, written to run on very
// old browsers (iOS 9 / Safari 9): no ES modules, fetch, arrow-only APIs, or
// optional chaining. Tapping a source word opens a small popup with the word as
// it appears (transliteration, gloss, and its contextual translation from
// data-tr), then its lemma's details — meaning, plural, compound verbs, etym,
// family, notes — from the page's #vocab-data JSON (everything in the full
// entry except the list of forms), a "play this word" button, and a link to
// the full vocab entry. The play button asks the section's audio player
// (whichever one initialized, via window.__ensurePlayer) to play just that
// word's span.
(function () {
  'use strict';

  var popup = null;
  var vocab = null;

  // Lemma details keyed by vocab anchor, embedded once per page by the renderer.
  function vocabData() {
    if (vocab) return vocab;
    var el = document.getElementById('vocab-data');
    try { vocab = el ? JSON.parse(el.textContent) : {}; } catch (e) { vocab = {}; }
    return vocab;
  }

  var DIACRITICS = /[\u064B-\u0652\u0670]/g;
  function bare(fa) { return (fa || '').replace(DIACRITICS, '').replace(/\s+/g, ' ').trim(); }

  function build() {
    if (popup) return popup;
    popup = document.createElement('div');
    popup.className = 'ap-popup';
    popup.style.display = 'none';
    popup.innerHTML =
      '<button type="button" class="ap-popup-close" aria-label="Close">×</button>' +
      '<div class="ap-popup-body">' +
        '<div class="ap-popup-fa"></div>' +
        '<div class="ap-popup-tl"></div>' +
        '<div class="ap-popup-gl"></div>' +
        '<div class="ap-popup-tr"></div>' +
        '<div class="ap-popup-lemma"></div>' +
      '</div>' +
      '<div class="ap-popup-actions">' +
        '<button type="button" class="ap-popup-play">▶ Play word</button>' +
        '<a class="ap-popup-entry" href="#">Full entry ›</a>' +
      '</div>';
    document.body.appendChild(popup);
    popup.querySelector('.ap-popup-close').onclick = hide;
    // Following a link inside the popup (etym cross-reference, full entry)
    // leaves the word behind, so close it.
    popup.addEventListener('click', function (e) {
      var n = e.target;
      while (n && n !== popup) {
        if (n.tagName === 'A') { hide(); return; }
        n = n.parentNode;
      }
    }, false);
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

  function setText(pop, cls, text) {
    var el = pop.querySelector(cls);
    el.textContent = text || '';
    el.style.display = text ? '' : 'none';
  }

  // One labelled detail row ("Etym: …") of the lemma block; `cls` is the
  // full entry's row class, so the label is coloured the same way.
  function metaRow(cls, label, html) {
    return '<div class="ap-popup-meta ' + cls + '"><span class="meta-label">' +
      label + '</span>: ' + html + '</div>';
  }

  // The lemma block: headword line (only when the tapped form differs from
  // the headword), then plural, compound verbs, etym, family, notes, warning.
  function lemmaHtml(d, sameAsLemma) {
    var h = '';
    if (!sameAsLemma) {
      h += '<div class="ap-popup-head"><span class="persian">' + d.fa + '</span>' +
        (d.tl ? ' <em class="translit">' + d.tl + '</em>' : '') +
        (d.df ? ' — ' + d.df : '') + '</div>';
    }
    if (d.pl) h += d.pl;
    if (d.lv) h += d.lv;
    if (d.plnote) h += metaRow('vocab-plural', 'Plural', d.plnote);
    if (d.etym) h += metaRow('vocab-etym', 'Etym', d.etym);
    if (d.family) h += metaRow('vocab-family', 'Family', d.family);
    if (d.notes) {
      for (var i = 0; i < d.notes.length; i++) h += metaRow('vocab-meta-other', 'Note', d.notes[i]);
    }
    if (d.warn) h += '<div class="ap-popup-meta">⚠️ ' + d.warn + '</div>';
    return h;
  }

  function show(wordEl) {
    var pop = build();
    var tl = wordEl.getAttribute('data-tl') || '';
    var gl = wordEl.getAttribute('data-gl') || '';
    var tr = wordEl.getAttribute('data-tr') || '';
    var t0 = wordEl.getAttribute('data-t0');
    var t1 = wordEl.getAttribute('data-t1');
    var href = wordEl.getAttribute('href');
    var d = (href && href.charAt(0) === '#') ? vocabData()[href.slice(1)] : null;
    var surface = wordEl.textContent;
    var sameAsLemma = !!(d && bare(d.fa) === bare(surface));

    pop.querySelector('.ap-popup-fa').textContent = surface;
    setText(pop, '.ap-popup-tl', tl);
    setText(pop, '.ap-popup-gl', gl);

    // The form's own translation; a bare headword's meaning is exactly that.
    var trEl = pop.querySelector('.ap-popup-tr');
    if (tr) {
      trEl.textContent = tr;
      trEl.style.display = '';
    } else if (sameAsLemma && d.df) {
      trEl.innerHTML = d.df;
      trEl.style.display = '';
    } else {
      trEl.style.display = 'none';
    }

    var lemEl = pop.querySelector('.ap-popup-lemma');
    lemEl.innerHTML = d ? lemmaHtml(d, sameAsLemma) : '';
    lemEl.style.display = lemEl.innerHTML ? '' : 'none';
    pop.querySelector('.ap-popup-body').scrollTop = 0;

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
    if (href && href.charAt(0) === '#') {
      entry.setAttribute('href', href);
      entry.style.display = '';
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
