/* Service worker: mise en cache de l'application + notifications push. */
import { clientsClaim } from 'workbox-core'
import { precacheAndRoute, cleanupOutdatedCaches, createHandlerBoundToURL } from 'workbox-precaching'
import { registerRoute, NavigationRoute } from 'workbox-routing'

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting()
})

// Nettoyage de l'ancien cache de la page hors connexion
self.addEventListener('activate', (event) => {
  event.waitUntil(caches.delete('gnb41-offline-v1'))
})

cleanupOutdatedCaches()
precacheAndRoute(self.__WB_MANIFEST)
clientsClaim()

// Toute navigation de l'application sert l'interface en cache; les pages statiques restent au serveur.
registerRoute(
  new NavigationRoute(createHandlerBoundToURL('/index.html'), {
    denylist: [/^\/telecharger/, /^\/\.well-known/, /\.apk$/, /^\/apk-version\.json$/, /^\/manifest\.json$/],
  })
)

self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch (e) {
    data = { title: 'GNB41 IA', body: event.data ? event.data.text() : '' }
  }
  event.waitUntil(
    self.registration.showNotification(data.title || 'GNB41 IA', {
      body: data.body || '',
      icon: '/android-chrome-192x192.png',
      badge: '/android-chrome-192x192.png',
      data: { url: data.url || '/' },
    })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = (event.notification.data && event.notification.data.url) || '/'
  event.waitUntil(
    (async () => {
      const wins = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      for (const w of wins) {
        if ('focus' in w) {
          await w.focus()
          if ('navigate' in w) {
            try { await w.navigate(url) } catch (e) { /* ignore */ }
          }
          return
        }
      }
      await self.clients.openWindow(url)
    })()
  )
})
