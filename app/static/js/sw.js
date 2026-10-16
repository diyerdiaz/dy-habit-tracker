// Service worker de Habits: permite instalar la app en el celular y muestra una
// página amable cuando no hay internet. No guarda en caché las páginas con tus
// datos (siempre se piden al servidor); solo la página sin conexión y el logo.
const CACHE = 'habits-v1';
const BASICOS = ['/offline', '/static/img/logo.svg', '/static/img/icon-192.png'];

self.addEventListener('install', (event) => {
    event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(BASICOS)));
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((nombres) =>
            Promise.all(nombres.filter((n) => n !== CACHE).map((n) => caches.delete(n)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    if (event.request.mode === 'navigate') {
        event.respondWith(fetch(event.request).catch(() => caches.match('/offline')));
    }
});
