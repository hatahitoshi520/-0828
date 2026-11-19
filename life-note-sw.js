/* ============================================================
   ライフノートのサービスワーカー（オフライン対応）
   ------------------------------------------------------------
   ・ページ本体（life-note.html）は「ネット優先」。つながらない時
     だけ前回保存したものを表示する（更新がすぐ反映されるように）
   ・React / Babel / Tailwind などのライブラリは「保存優先」
   ・Google / Anthropic のAPI通信には一切手を出さない
   登録時のスコープを "./life-note" にしているので、同じサイトの
   POS（index.html）など他のページには影響しない。
   ============================================================ */
const CACHE = "lifenote-v1";
const APP_SHELL = [
  "./life-note.html",
  "./life-note.webmanifest",
  "./life-note-icons/icon-192.png",
  "./life-note-icons/icon-512.png",
  "./life-note-icons/apple-touch-icon.png",
];
const LIB_HOSTS = ["cdn.jsdelivr.net", "unpkg.com", "cdn.tailwindcss.com"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(APP_SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith("lifenote-") && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  if (LIB_HOSTS.includes(url.hostname)) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }))
    );
    return;
  }

  if (url.origin === self.location.origin) {
    event.respondWith(
      fetch(req).then((res) => {
        if (res.ok && req.mode === "navigate") {
          const copy = res.clone();
          // ?_v=… 付きでも同じページとして保存する
          caches.open(CACHE).then((c) => c.put(url.pathname, copy));
        }
        return res;
      }).catch(() => caches.match(req, { ignoreSearch: true }).then((hit) => hit || caches.match("./life-note.html")))
    );
  }
});
