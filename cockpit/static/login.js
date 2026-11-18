(function () {
  var fr = /^fr/i.test((function () { try { return JSON.parse(localStorage.getItem("cockpit.lang")) || navigator.language; } catch (e) { return navigator.language; } })() || "");
  var T = fr ? { sub: "Connexion au cockpit", lbl: "Mot de passe", b: "Se connecter", wrong: "Mot de passe incorrect.", wait: "Trop d'essais : réessaie dans {n} s.",
                 none: "Aucun mot de passe n'est défini : lance ./setup.sh sur le serveur.", err: "Le cockpit ne répond pas.",
                 h: "Le mot de passe s'affiche à la fin de <code>./setup.sh</code> et se trouve dans <code>.env</code> (COCKPIT_PASSWORD)." }
               : { sub: "Sign in to the cockpit", lbl: "Password", b: "Sign in", wrong: "Wrong password.", wait: "Too many attempts: try again in {n} s.",
                 none: "No password is set: run ./setup.sh on the server.", err: "The cockpit does not answer.", h: null };
  document.documentElement.lang = fr ? "fr" : "en";
  document.getElementById("sub").textContent = T.sub;
  document.getElementById("lbl").textContent = T.lbl;
  document.getElementById("b").textContent = T.b;
  if (T.h) document.getElementById("h").innerHTML = T.h;
  var m = document.getElementById("m"), b = document.getElementById("b");
  document.getElementById("f").addEventListener("submit", function (e) {
    e.preventDefault(); m.textContent = ""; b.disabled = true;
    fetch("api/login", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ password: document.getElementById("p").value }) })
      .then(function (r) { return r.json().then(function (d) { return { s: r.status, d: d }; }); })
      .then(function (x) {
        if (x.s === 200) { location.href = "./" + (location.hash || ""); return; }
        m.textContent = x.s === 429 ? T.wait.replace("{n}", x.d.retry_after) : x.s === 503 ? T.none : T.wrong;
      })
      .catch(function () { m.textContent = T.err; })
      .then(function () { b.disabled = false; });
  });
})();
