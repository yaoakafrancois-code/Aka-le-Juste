{% load static %}// Service worker CacaoCoop {{ version }}
const CACHE = "cacaocoop-{{ version }}";
const FICHIERS = ["{% static 'css/app.css' %}", "{% static 'icones/icone-192.png' %}", "{% url 'core:hors_ligne' %}"];
// Page de collecte terrain et ses données : gardées en cache pour rouvrir la page sans réseau.
const TERRAIN = ["{% url 'achats:terrain' %}", "{% url 'achats:terrain_donnees' %}"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FICHIERS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((cles) => Promise.all(cles.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.pathname.startsWith("{% get_static_prefix %}")) {
    // Fichiers statiques : cache d'abord.
    e.respondWith(caches.match(req).then((r) => r || fetch(req).then((rep) => {
      const copie = rep.clone(); caches.open(CACHE).then((c) => c.put(req, copie)); return rep;
    })));
  } else if (TERRAIN.includes(url.pathname)) {
    // Collecte terrain : réseau d'abord, copie en cache, cache si hors connexion.
    e.respondWith(fetch(req).then((rep) => {
      if (rep.ok && !rep.redirected) { const copie = rep.clone(); caches.open(CACHE).then((c) => c.put(url.pathname, copie)); }
      return rep;
    }).catch(() => caches.match(url.pathname).then((r) => r || caches.match("{% url 'core:hors_ligne' %}"))));
  } else if (req.mode === "navigate") {
    // Pages : toujours les données à jour ; page d'attente si le serveur est injoignable.
    e.respondWith(fetch(req).catch(() => caches.match("{% url 'core:hors_ligne' %}")));
  }
});
