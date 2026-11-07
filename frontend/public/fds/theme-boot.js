/* fleet-design-system theme boot (copy of the inline snippet in theme.js, as a file so CSP-strict pages can load it
   synchronously in <head> before CSS paints). */
(function(){try{var c=localStorage.getItem("fds-theme")||"system";var d=c==="dark"||(c==="system"&&matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.setAttribute("data-theme",d?"dark":"light")}catch(e){}})();
