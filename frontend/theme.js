/* Light is the default; the choice made with the theme button is remembered. */
try { document.documentElement.dataset.theme = localStorage.getItem("itoc.theme") || "light"; } catch (_) { document.documentElement.dataset.theme = "light"; }
