/* Apply the saved theme before CSS paints. Dark is always the default. */
(() => {
  'use strict';
  const modes = Object.freeze(['dark', 'light', 'system']);
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let mode = 'dark';
  try {
    const saved = JSON.parse(localStorage.getItem('nuvel-obsidian-preferences-v1') || '{}');
    if (modes.includes(saved?.theme)) mode = saved.theme;
  } catch { /* A missing or unavailable cache must still start in Dark. */ }
  function apply() {
    const resolved = mode === 'system' ? (system.matches ? 'dark' : 'light') : mode;
    document.documentElement.dataset.theme = resolved;
    for (const [name, value] of Object.entries({
      'color-scheme': resolved, 'theme-color': resolved === 'dark' ? '#0d1016' : '#f2f3f6'
    })) document.querySelector('meta[name="' + name + '"]')?.setAttribute('content', value);
  }
  function set(value) {
    mode = modes.includes(value) ? value : 'dark';
    apply();
  }
  system.addEventListener('change', () => { if (mode === 'system') apply(); });
  window.StudioTheme = Object.freeze({modes, set, get mode() { return mode; }});
  apply();
})();
