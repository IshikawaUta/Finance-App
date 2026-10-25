// Runs before the Svelte bundle to avoid a theme flash.
// Loaded as a same-origin static file so the Tauri CSP stays strict.
(function () {
  try {
    var stored = localStorage.getItem('finance.theme');
    var theme =
      stored === 'dark' || stored === 'light'
        ? stored
        : window.matchMedia('(prefers-color-scheme: dark)').matches
          ? 'dark'
          : 'light';
    document.documentElement.setAttribute('data-theme', theme);
  } catch (error) {
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();
