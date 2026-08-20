/* Boss Bird Service Worker —— 离线缓存游戏外壳，打开更快、能"添加到主屏幕" */
const CACHE = 'bossbird-v4';   // 版本号：每次大改缓存策略时 +1，强制浏览器更新 SW
const CORE = [
  'index.html',
  'BossBird.html',
  'manifest.webmanifest',
  'icon-192.png',
  'icon-512.png',
];

// 安装时缓存核心文件
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting())
  );
});

// 激活时清掉旧缓存（v1 等历史版本）
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// 请求拦截
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return; // 外部请求直接放行（走默认网络）

  // API 请求：永远走网络，绝不缓存（登录/成绩数据必须实时，缓存会导致成绩面板不刷新）
  if (url.pathname.startsWith('/api/')) return;

  // HTML 走 network-first：每次刷新都向服务器拿最新游戏，断网时再退回缓存
  if (url.pathname.endsWith('.html') || url.pathname === '/' || url.pathname === '') {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const cp = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, cp)); // 顺手更新缓存，供离线使用
          return res;
        })
        .catch(() => caches.match(e.request)) // 断网 / 失败 -> 用缓存兜底
    );
    return;
  }

  // 其它静态资源（图标 / manifest）走 cache-first：几乎不变，优先读缓存更快
  e.respondWith(
    caches.match(e.request).then((cached) => {
      if (cached) return cached;
      return fetch(e.request).then((res) => {
        if (res && res.ok) {
          const cp = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, cp));
        }
        return res;
      });
    })
  );
});
