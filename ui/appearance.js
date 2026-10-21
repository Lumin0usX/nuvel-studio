/* Optional glass surfaces and interruption-safe motion; no rendering loop at idle. */
(() => {
  'use strict';
  const root = document.documentElement;
  const styles = Object.freeze(['obsidian', 'glass']);
  const systemMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const animations = new Map();
  let visualStyle = 'obsidian', reducedMotion = false;
  let mounted = false;
  let navSurface, formatSurface;
  const ease = 'cubic-bezier(.22, 1, .36, 1)';

  function apply() {
    root.dataset.visualStyle = visualStyle;
    root.dataset.motion = reducedMotion || systemMotion.matches ? 'off' : 'on';
    if (root.dataset.motion === 'off') {
      for (const animation of animations.values()) animation.cancel();
      animations.clear();
    }
  }
  function set(values = {}) {
    visualStyle = styles.includes(values.visualStyle) ? values.visualStyle : 'obsidian';
    reducedMotion = values.reducedMotion === true;
    apply();
  }
  function enter(element, kind = 'page') {
    if (!element) return;
    animations.get(element)?.cancel();
    animations.delete(element);
    if (root.dataset.motion !== 'on' || element.hidden || !element.animate) return;
    const transforms = kind === 'toast' ? ['translate(-50%, 6px)', 'translate(-50%, 0)'] :
      kind === 'dialog' ? ['translateY(8px) scale(.985)', 'translateY(0) scale(1)'] :
      ['translateY(6px)', 'translateY(0)'];
    const animation = element.animate([
      {opacity: 0, transform: transforms[0]}, {opacity: 1, transform: transforms[1]}
    ], {duration: kind === 'page' ? 260 : 220, easing: ease});
    animations.set(element, animation);
    animation.finished.then(() => {
      if (animations.get(element) === animation) animations.delete(element);
    }, () => { /* Replaced or disabled motion is ordinary cancellation. */ });
  }
  function place(surface, target) {
    if (!target || !surface) return;
    const parent = surface.parentElement;
    const host = parent.getBoundingClientRect();
    const rect = target.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    // Set the first position without sweeping from the top left on startup.
    const first = !surface.dataset.placed;
    if (first) surface.style.transition = 'none';
    surface.style.width = rect.width + 'px';
    surface.style.height = rect.height + 'px';
    surface.style.transform = `translate(${rect.left - host.left - parent.clientLeft + parent.scrollLeft}px, ${rect.top - host.top - parent.clientTop + parent.scrollTop}px)`;
    if (first) {
      surface.getBoundingClientRect();
      surface.style.removeProperty('transition');
      surface.dataset.placed = 'true';
    }
  }
  function syncSelections() {
    if (!mounted) return;
    place(navSurface, document.querySelector('.nav-item[data-page].selected'));
    place(formatSurface, document.querySelector('.format-control input:checked + span'));
  }
  function mount() {
    if (mounted) return;
    mounted = true;
    for (const [host, className] of [['.sidebar', 'nav-selection'], ['.format-control', 'format-selection']]) {
      const container = document.querySelector(host);
      if (!container) continue;
      const surface = document.createElement('span');
      surface.className = className; surface.setAttribute('aria-hidden', 'true');
      container.prepend(surface);
      if (host === '.sidebar') navSurface = surface; else formatSurface = surface;
    }
    if (window.ResizeObserver) {
      const observer = new ResizeObserver(syncSelections);
      for (const element of [navSurface?.parentElement, formatSurface?.parentElement])
        if (element) observer.observe(element);
    }
    window.addEventListener('resize', syncSelections);
    syncSelections();
  }
  try {
    const saved = JSON.parse(localStorage.getItem('ytdl-obsidian-preferences-v1') || '{}');
    if (styles.includes(saved?.visualStyle)) visualStyle = saved.visualStyle;
    reducedMotion = saved?.reducedMotion === true;
  } catch { /* The original appearance stays usable when storage is unavailable. */ }
  systemMotion.addEventListener('change', apply);
  window.StudioAppearance = Object.freeze({styles, set, enter, mount, syncSelections,
    get motionEnabled() { return root.dataset.motion === 'on'; }});
  apply();
})();
