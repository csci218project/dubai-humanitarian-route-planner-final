"""Scroll-driven 3D opening: the camera orbits the globe as you scroll.

The frames in ``static/sequence/`` come from a 10-second video generated with
Gemini and converted by ``scripts/make_sequence.py``. The opening section is
taller than the screen; while it scrolls past, a sticky stage stays pinned and
a small script picks which frame to draw from how far you've scrolled:

    progress = distance scrolled into the section / (section height - screen height)
    frame    = round(progress * (number of frames - 1))

If the frames are missing, ``hero_sequence()`` returns False and the app shows
the plain masthead instead. With "reduce motion" switched on in the operating
system, the opening shows one still frame and no scroll animation.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

import streamlit as st

SEQUENCE_DIR = Path(__file__).resolve().parents[1] / "static" / "sequence"
SEQUENCE_URL = "app/static/sequence/"   # where Streamlit's static serving exposes the folder
PLANNER_ANCHOR = "hrp-planner"

# (label, text, position class, scroll range where the card is visible)
CARDS = [
    ("The problem", "Relief cargo leaves Dubai by air, sea and road, and any airport, port or corridor "
     "on the way can close.", "at-right", 0.20, 0.44),
    ("The search", "When something closes, the planner searches the network again for the next best "
     "route by time, cost and risk.", "at-left", 0.46, 0.70),
    ("The comparison", "Dijkstra, A* and hierarchical search solve the same request side by side, so "
     "you can see how much of the network each one explores.", "at-right-low", 0.72, 0.97),
]


def load_manifest() -> dict | None:
    """Read static/sequence/manifest.json; None if the sequence isn't usable."""
    try:
        data = json.loads((SEQUENCE_DIR / "manifest.json").read_text(encoding="utf-8"))
        count = int(data["count"])
        pattern = str(data["pattern"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if count < 2:
        return None
    if not all((SEQUENCE_DIR / pattern.format(index=i)).exists() for i in (0, count - 1)):
        return None
    return data


def frame_urls(manifest: dict) -> list[str]:
    # The version stamp makes browsers fetch new frames after the sequence is regenerated.
    version = int((SEQUENCE_DIR / "manifest.json").stat().st_mtime)
    return [f"{SEQUENCE_URL}{manifest['pattern'].format(index=i)}?v={version}" for i in range(int(manifest["count"]))]


def hero_sequence() -> bool:
    """Render the opening sequence. Returns False (renders nothing) if the frames are missing."""
    manifest = load_manifest()
    if manifest is None:
        return False
    urls = frame_urls(manifest)
    poster = f"{SEQUENCE_URL}{escape(str(manifest.get('poster', manifest['pattern'].format(index=0))))}"
    cards = "".join(
        f'<aside class="hrp-hero-card {position}" data-from="{start}" data-to="{end}">'
        f'<p class="hrp-hero-card-label">{escape(label)}</p><p>{escape(text)}</p></aside>'
        for label, text, position, start, end in CARDS
    )
    html = (
        '<section class="hrp-hero" aria-label="Opening: a globe turns as you scroll">'
        '<div class="hrp-hero-stage">'
        f'<img class="hrp-hero-poster" src="{poster}" alt="" aria-hidden="true">'
        '<canvas class="hrp-hero-canvas" aria-hidden="true"></canvas>'
        '<div class="hrp-hero-title">'
        '<p class="hrp-kicker">A Dubai Humanitarian use case for CSCI218, Project B</p>'
        '<h1 class="hrp-title">Humanitarian Route Planner</h1>'
        '<p class="hrp-standfirst">Find the best way to move relief cargo from Dubai, then close airports, '
        "ports and corridors to see how Dijkstra, A* and hierarchical search adapt.</p></div>"
        f'<div class="hrp-hero-cards">{cards}</div>'
        '<div class="hrp-hero-foot">'
        '<span class="hrp-hero-hint">Scroll to turn the globe</span>'
        f'<a class="hrp-hero-skip" href="#{PLANNER_ANCHOR}">Skip to the planner</a>'
        "</div></div></section>"
        "<script>" + _PLAYER_JS.replace("__FRAMES__", json.dumps(urls)).replace("__ANCHOR__", PLANNER_ANCHOR) + "</script>"
    )
    st.html(html, unsafe_allow_javascript=True)
    return True


def planner_anchor() -> None:
    """Invisible target for the 'Skip to the planner' link."""
    st.html(f'<div id="{PLANNER_ANCHOR}" class="hrp-anchor"></div>')


_PLAYER_JS = r"""
(() => {
  const FRAMES = __FRAMES__;
  const roots = document.querySelectorAll('.hrp-hero');
  const root = roots[roots.length - 1];
  if (!root) return;
  const previous = window.__hrpHero;
  if (previous && previous.root === root && root.isConnected) return;   // already running here
  if (previous) { try { previous.destroy(); } catch (err) {} }

  const stage = root.querySelector('.hrp-hero-stage');
  const canvas = root.querySelector('canvas');
  const context = canvas.getContext('2d');
  const title = root.querySelector('.hrp-hero-title');
  const cards = Array.from(root.querySelectorAll('.hrp-hero-card'));
  const hint = root.querySelector('.hrp-hero-hint');
  const skip = root.querySelector('.hrp-hero-skip');
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Streamlit scrolls an inner element, not the window: find it.
  let scroller = null;
  for (let node = root.parentElement; node && node !== document.body; node = node.parentElement) {
    const overflow = getComputedStyle(node).overflowY;
    if (overflow === 'auto' || overflow === 'scroll') { scroller = node; break; }
  }
  const scrollTarget = scroller || window;

  // Decoded frames survive Streamlit reruns, so they are only downloaded once.
  const cache = window.__hrpFrameCache || (window.__hrpFrameCache = new Map());
  const images = FRAMES.map((src) => {
    let image = cache.get(src);
    if (!image) { image = new Image(); image.decoding = 'async'; image.src = src; cache.set(src, image); }
    return image;
  });
  const isReady = (image) => image.complete && image.naturalWidth > 0;
  const nearestReady = (index) => {
    for (let step = 0; step < images.length; step++) {
      if (index - step >= 0 && isReady(images[index - step])) return index - step;
      if (index + step < images.length && isReady(images[index + step])) return index + step;
    }
    return -1;
  };

  let drawn = -1;
  let pending = 0;

  function sizeCanvas() {
    const box = stage.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.round(box.width * ratio));
    const height = Math.max(1, Math.round(box.height * ratio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width; canvas.height = height; drawn = -1;
    }
  }

  function draw(index) {
    const ready = nearestReady(index);
    if (ready < 0 || ready === drawn) return;
    const image = images[ready];
    const cw = canvas.width, ch = canvas.height;
    const iw = image.naturalWidth, ih = image.naturalHeight;
    // Fill the stage, but never crop away more than half the width (keeps the globe on phones).
    const scale = Math.min(Math.max(cw / iw, ch / ih), cw / (0.5 * iw));
    const w = iw * scale, h = ih * scale, x = (cw - w) / 2, y = (ch - h) / 2;
    context.globalCompositeOperation = 'source-over';
    context.clearRect(0, 0, cw, ch);
    context.drawImage(image, x, y, w, h);
    // Feather the visible part of the frame so its edges melt into the parchment page.
    const vx = Math.max(0, x), vy = Math.max(0, y);
    const vw = Math.min(cw, x + w) - vx, vh = Math.min(ch, y + h) - vy;
    context.save();
    context.globalCompositeOperation = 'destination-in';
    context.translate(vx + vw / 2, vy + vh / 2);
    context.scale(vw / 2, vh / 2);
    const feather = context.createRadialGradient(0, 0, 0, 0, 0, 1);
    feather.addColorStop(0, 'rgba(0,0,0,1)');
    feather.addColorStop(0.6, 'rgba(0,0,0,1)');
    feather.addColorStop(1, 'rgba(0,0,0,0)');
    context.fillStyle = feather;
    context.fillRect(-1, -1, 2, 2);
    context.restore();
    drawn = ready;
    root.classList.add('is-ready');
  }

  function progress() {
    const box = root.getBoundingClientRect();
    const viewTop = scroller ? scroller.getBoundingClientRect().top : 0;
    const viewHeight = scroller ? scroller.clientHeight : window.innerHeight;
    const travel = box.height - viewHeight;
    if (travel <= 0) return 0;
    return Math.min(1, Math.max(0, (viewTop - box.top) / travel));
  }

  const window01 = (p, from, to, edge) =>
    (p <= from || p >= to) ? 0 : Math.min(1, (p - from) / edge, (to - p) / edge);

  function show(element, amount, shift) {
    element.style.opacity = amount.toFixed(3);
    element.style.transform = 'translateY(' + ((1 - amount) * shift).toFixed(1) + 'px)';
    element.style.visibility = amount < 0.01 ? 'hidden' : 'visible';
  }

  function update() {
    pending = 0;
    if (!root.isConnected) { destroy(); return; }
    sizeCanvas();
    if (reduceMotion) { draw(0); return; }
    const p = progress();
    draw(Math.round(p * (images.length - 1)));
    if (title) show(title, Math.max(0, 1 - p / 0.16), -28);
    cards.forEach((card) => show(card, window01(p, +card.dataset.from, +card.dataset.to, 0.06), 18));
    if (hint) hint.style.opacity = Math.max(0, 1 - p / 0.08).toFixed(3);
  }

  function schedule() { if (!pending) pending = requestAnimationFrame(update); }

  function onSkip(event) {
    const target = document.getElementById('__ANCHOR__');
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
  }

  const resizeObserver = new ResizeObserver(schedule);
  function destroy() {
    scrollTarget.removeEventListener('scroll', schedule);
    window.removeEventListener('resize', schedule);
    resizeObserver.disconnect();
    if (skip) skip.removeEventListener('click', onSkip);
    if (pending) cancelAnimationFrame(pending);
    if (window.__hrpHero && window.__hrpHero.root === root) window.__hrpHero = null;
  }

  if (reduceMotion) root.classList.add('is-static');
  else scrollTarget.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', schedule);
  resizeObserver.observe(stage);
  if (skip) skip.addEventListener('click', onSkip);
  images.forEach((image) => { if (!isReady(image)) image.addEventListener('load', schedule, { once: true }); });
  window.__hrpHero = { root, destroy };
  schedule();
})();
"""
