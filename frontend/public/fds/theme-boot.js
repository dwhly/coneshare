/* fleet-design-system — theme-boot.js (v0.9.1)
   The theme boot snippet as a FILE, for products whose CSP forbids inline scripts.
   Load it synchronously in <head> (no defer/async), after <meta name="color-scheme" content="light dark">,
   so data-theme and the meta are set before first paint. Same logic as the snippet at the foot of theme.js. */
(function(){try{var c=localStorage.getItem("fds-theme")||"system";var d=c==="dark"||(c==="system"&&matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.setAttribute("data-theme",d?"dark":"light");var m=document.querySelector('meta[name="color-scheme"]');if(m)m.content=c==="system"?"light dark":c}catch(e){}})();
