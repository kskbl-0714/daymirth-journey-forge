importScripts('./cache-config.js');
const prefix = self.TRIP_CACHE.namespace;
const cacheName = prefix + self.TRIP_CACHE.revision;
const allowed = new Set(self.TRIP_CACHE.assets.map(p => new URL(p, self.registration.scope).href));
self.addEventListener('install', event => event.waitUntil(caches.open(cacheName).then(cache => cache.addAll(self.TRIP_CACHE.assets)).then(() => self.skipWaiting())));
self.addEventListener('activate', event => event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith(prefix) && k !== cacheName).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  if (event.request.mode === 'navigate' && url.href.startsWith(self.registration.scope)) {
    event.respondWith(fetch(event.request).catch(() => caches.open(cacheName).then(c => c.match('index.html'))));
  } else if (allowed.has(url.href)) {
    event.respondWith(caches.open(cacheName).then(async cache => (await cache.match(event.request)) || fetch(event.request)));
  }
});
