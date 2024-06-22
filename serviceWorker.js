const cacheName = 'v2'

const assets = [
  "app.css",
  "img/",
  "img/icon/",
  "img/icon/launchericon-144-144.png",
  "img/icon/launchericon-192-192.png",
  "img/icon/launchericon-48-48.png",
  "img/icon/launchericon-512-512.png",
  "img/icon/launchericon-72-72.png",
  "img/icon/launchericon-96-96.png",
  "index.html",
  "lemur/",
  "lemur/__init__.py",
  "lemur/__pycache__/",
  "lemur/__pycache__/__init__.cpython-312.pyc",
  "lemur/__pycache__/expensedb.cpython-312.pyc",
  "lemur/expensedb.py",
  "lemur/main.py",
  "puepy-0.3.0-py3-none-any.whl",
  "pyscript-config.toml",
  "serviceWorker.js",
]

self.addEventListener("install", installEvent => {
    installEvent.waitUntil(
        caches.open(staticPyPWA).then(cache => {
            cache.addAll(assets).then(r => {
                console.log("Cache assets downloaded");
            }).catch(err => console.log("Error caching item", err))
            console.log(`Cache ${staticPyPWA} opened.`);
        }).catch(err => console.log("Error opening cache", err))
    )
})

self.addEventListener("fetch", fetchEvent => {
    fetchEvent.respondWith(
        caches.match(fetchEvent.request).then(res => {
            return res || fetch(fetchEvent.request)
        }).catch(err => console.log("Cache fetch error: ", err))
    )
})