const CACHE_NAME = 'cbs-3icell-v4';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/css/mobile-nav.css',
    '/static/css/dashboard-responsive.css',
    '/static/js/main.js',
    '/static/js/offline-notifications.js',
    '/static/images/logo1.png',
    '/static/manifest.json',
    '/offline',
    'https://cdn.jsdelivr.net/npm/@phosphor-icons/web@2.1.2/src/regular/style.css',
    'https://cdn.jsdelivr.net/npm/@phosphor-icons/web@2.1.2/src/bold/style.css',
    'https://cdn.jsdelivr.net/npm/@phosphor-icons/web@2.1.2/src/fill/style.css',
    'https://cdn.jsdelivr.net/npm/@phosphor-icons/web@2.1.2/src/duotone/style.css',
    'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap'
];

self.addEventListener('install', (event) => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(STATIC_ASSETS))
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_NAME) return caches.delete(key);
                })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    // Skip cross-origin requests like Mixpanel/Analytics if any
    if (
        !event.request.url.startsWith(self.location.origin) &&
        !event.request.url.includes('unpkg') &&
        !event.request.url.includes('jsdelivr') &&
        !event.request.url.includes('fonts')
    ) {
        return; 
    }

    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    return caches.match(event.request)
                        .then((response) => {
                            return response || caches.match('/offline');
                        });
                })
        );
    } else if (event.request.url.includes('/static/css/') || event.request.url.includes('/static/js/')) {
        event.respondWith(
            fetch(event.request)
                .then((networkResp) => {
                    if (networkResp && networkResp.status === 200) {
                        const copy = networkResp.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
                    }
                    return networkResp;
                })
                .catch(() => caches.match(event.request))
        );
    } else {
        event.respondWith(
            caches.match(event.request)
                .then((response) => {
                    return response || fetch(event.request);
                })
        );
    }
});


// ── Web Push Event Listener (Receives notifications when app/tab is closed) ──
self.addEventListener('push', (event) => {
    let payload = {
        title: 'CBS Placement Cell (3i-cell)',
        body: 'New verified placement circular or opportunity released.',
        icon: '/static/images/logo1.png',
        badge: '/static/images/logo1.png',
        url: '/'
    };

    if (event.data) {
        try {
            payload = Object.assign(payload, event.data.json());
        } catch (e) {
            payload.body = event.data.text();
        }
    }

    const options = {
        body: payload.body,
        icon: payload.icon || '/static/images/logo1.png',
        badge: payload.badge || '/static/images/logo1.png',
        vibrate: [100, 50, 100],
        data: {
            url: payload.url || '/'
        },
        actions: [
            { action: 'explore', title: 'View Details' }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(payload.title, options)
    );
});

// ── Notification Click Handler (Opens relevant destination on user click) ────
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const targetUrl = (event.notification.data && event.notification.data.url) ? event.notification.data.url : '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            for (const client of clientList) {
                if (client.url && client.url.includes(self.location.origin) && 'focus' in client) {
                    client.navigate(targetUrl);
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});
