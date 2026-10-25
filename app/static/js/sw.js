// Service worker de Habits: permite instalar la app en el celular y muestra una
// página amable cuando no hay internet. No guarda en caché las páginas con tus
// datos (siempre se piden al servidor); solo la página sin conexión, el logo y
// los archivos de diseño (CSS, JS, íconos y Bootstrap).
const CACHE = 'habits-v3';  // subir el número cuando cambien el logo o la página sin conexión
const CACHE_ESTATICOS = 'habits-estaticos';
const BASICOS = ['/offline', '/static/img/logo.svg', '/static/img/icon-192.png'];
// Bootstrap y sus íconos: la URL lleva la versión exacta, así que nunca cambian
const CDN = 'https://cdn.jsdelivr.net/npm/';

self.addEventListener('install', (event) => {
    event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(BASICOS)));
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((nombres) =>
            Promise.all(nombres.filter((n) => n !== CACHE && n !== CACHE_ESTATICOS).map((n) => caches.delete(n)))
        )
    );
    self.clients.claim();
});

// Los archivos de /static/ llevan ?v=<fecha>: si el archivo cambia, cambia la URL.
// Por eso se pueden servir desde el celular/PC sin preguntar al servidor, y el
// diseño carga aunque el internet esté malo.
function esEstaticoVersionado(url) {
    return url.origin === self.location.origin && url.pathname.startsWith('/static/') && url.searchParams.has('v');
}

async function desdeCache(request) {
    const cache = await caches.open(CACHE_ESTATICOS);
    const guardado = await cache.match(request);
    if (guardado) return guardado;

    const respuesta = await fetch(request);
    if (respuesta.ok || respuesta.type === 'opaque') {
        const url = new URL(request.url);
        if (url.origin === self.location.origin) {
            // Borra las versiones viejas del mismo archivo para que la caché no crezca
            const viejas = await cache.keys();
            await Promise.all(viejas
                .filter((r) => new URL(r.url).pathname === url.pathname)
                .map((r) => cache.delete(r)));
        }
        await cache.put(request, respuesta.clone());
    }
    return respuesta;
}

self.addEventListener('fetch', (event) => {
    const request = event.request;
    if (request.method !== 'GET') return;

    if (request.mode === 'navigate') {
        event.respondWith(fetch(request).catch(() => caches.match('/offline')));
        return;
    }

    const url = new URL(request.url);
    if (esEstaticoVersionado(url) || request.url.startsWith(CDN)) {
        event.respondWith(desdeCache(request));
    }
});
