(function () { // thème avant le premier rendu, pour éviter le flash
    var th; try { th = JSON.parse(localStorage.getItem("cockpit.theme")); } catch (e) {}
    if (th !== "day" && th !== "night") th = window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches ? "day" : "night";
    document.documentElement.dataset.theme = th;
  })();
