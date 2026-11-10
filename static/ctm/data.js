/* CTM data store (issue 308, step 2): keeps recent server reads in this tab's memory so pages draw at once and
   check for changes quietly, and loads the likely next page while the browser is idle.

   Rules (owner approval 2026-11-10, design on issue 308):
   - Memory only. Nothing is written to the browser's local or session storage, IndexedDB or a service worker, and
     api() keeps cache: "no-store", so case data never stays on the computer after the tab closes.
   - Only the reads on KEEP are kept. Files, assessments, medical reports, audit, timeline, notifications,
     decisions, votes, decrees, payments, messages and the session are never kept and never loaded ahead.
   - Kept per account. A different account, a 401 or any save (every method but GET) clears everything.
   - A repeat read within FRESH_MS comes from memory. Up to KEEP_MS, a page's first reads are drawn from memory
     at once and asked again quietly; the page draws again only if the answer changed.
   - Background reads (quiet refreshes and loading ahead) run at most BACKGROUND_MAX at a time, never while a
     read the user is waiting for is on its way, and never while the tab is hidden.
   The server still decides every read; this store only holds what it already sent to this account. */
(() => {
  "use strict";

  const FRESH_MS = 10 * 1000;
  const KEEP_MS = 5 * 60 * 1000;
  const MAX_ENTRIES = 50;
  const BACKGROUND_MAX = 2;

  // The reads that may be kept (paths as the modules ask for them). Everything else always goes to the server.
  const KEEP = [
    /^\/api\/cases\/(\?[^#]*)?$/, // case lists (all, ?mine=1)
    /^\/api\/cases\/[^/?#]+\/$/, // a case record
    /^\/api\/cases\/[^/?#]+\/requests\/$/, // a case's report requests (kind and status; never report content)
    /^\/api\/cases\/[^/?#]+\/parties\/$/,
    /^\/api\/applications\/$/,
    /^\/api\/dashboard\/$/,
    /^\/api\/dashboard\/members\/$/,
    /^\/api\/statistics\/summary\/$/,
    /^\/api\/sessions\/$/,
    /^\/api\/sessions\/[^/?#]+\/agenda\/$/,
    /^\/api\/sessions\/[^/?#]+\/attendance\/$/,
    /^\/api\/sessions\/[^/?#]+\/answers\/$/,
    /^\/api\/council\/members\/$/,
  ];
  const keepable = (url) => typeof url === "string" && KEEP.some((pattern) => pattern.test(url));

  let account = null; // the signed-in account id; nothing is kept before it is known
  let epoch = 0; // bumped by every clear, so a read that started before a save never fills the store
  const entries = new Map(); // url -> { text, at }; insertion order is the age order for eviction
  const flying = new Map(); // url -> { promise (JSON text), epoch }
  const readers = new Set();
  let current = null; // the reader whose loader is running right now (synchronous part only)
  let userReads = 0; // reads the user is waiting for
  let backgroundRunning = 0;
  const queue = []; // { url, kind: "refresh" | "prefetch" }
  let hiddenAt = null;

  const now = () => Date.now();
  const parse = (text) => JSON.parse(text);
  const hidden = () => typeof document !== "undefined" && document.visibilityState === "hidden";

  function clear() {
    epoch += 1;
    entries.clear();
    flying.clear();
    queue.length = 0;
  }

  function setAccount(id) {
    const next = id == null ? null : String(id);
    if (next === account) return;
    clear();
    account = next;
  }

  function notify(url) {
    for (const reader of [...readers]) {
      if (reader.urls.has(url)) Promise.resolve().then(() => readers.has(reader) && reader.urls.has(url) && reader.onChange());
    }
  }

  function keep(url, text) {
    const previous = entries.get(url);
    entries.delete(url);
    entries.set(url, { text, at: now() });
    while (entries.size > MAX_ENTRIES) entries.delete(entries.keys().next().value);
    if (previous && previous.text !== text) notify(url);
  }

  function drop(url) {
    if (!entries.delete(url)) return;
    notify(url);
  }

  // One request per address at a time; a later read of the same address joins it.
  function fetchText(raw, url, background) {
    const running = flying.get(url);
    if (running && running.epoch === epoch) return running.promise;
    const started = epoch;
    if (!background) userReads += 1;
    const promise = raw(url)
      .then(
        (value) => {
          const text = JSON.stringify(value === undefined ? null : value);
          if (started === epoch && account) keep(url, text);
          return text;
        },
        (error) => {
          if (error && error.status === 401) clear();
          // The server now refuses (403, 404, ...): forget the copy and let the pages that drew it ask again.
          else if (error && error.status && started === epoch) drop(url);
          throw error;
        },
      )
      .finally(() => {
        if (flying.get(url)?.promise === promise) flying.delete(url);
        if (!background) {
          userReads -= 1;
          pump();
        }
      });
    flying.set(url, { promise, epoch: started });
    return promise;
  }

  let rawApi = null;

  function read(raw, url) {
    const reader = current;
    if (reader) reader.urls.add(url);
    let entry = entries.get(url);
    if (entry && now() - entry.at >= KEEP_MS) {
      entries.delete(url);
      entry = null;
    }
    if (entry && now() - entry.at < FRESH_MS) return Promise.resolve(parse(entry.text));
    // Only a page's own first reads are drawn from an older copy, because only they are drawn again on a change.
    if (entry && reader) {
      schedule(url, "refresh");
      return Promise.resolve(parse(entry.text));
    }
    return fetchText(raw, url, false).then(parse);
  }

  function wrap(raw) {
    rawApi = raw;
    return function api(url, options = {}) {
      const method = String(options.method || "GET").toUpperCase();
      if (method !== "GET") {
        // A save may change anything this account can see: forget everything before and after it.
        clear();
        return raw(url, options).finally(clear);
      }
      if (!account || !keepable(url) || Object.keys(options).length)
        return raw(url, options).catch((error) => {
          if (error && error.status === 401) clear();
          throw error;
        });
      return read(raw, url);
    };
  }

  function schedule(url, kind) {
    if (!rawApi || !keepable(url) || !account) return;
    if (queue.some((job) => job.url === url)) return;
    if (kind === "refresh") queue.unshift({ url, kind });
    else queue.push({ url, kind });
    pump();
  }

  function pump() {
    while (backgroundRunning < BACKGROUND_MAX && queue.length) {
      if (userReads > 0 || hidden()) return; // resumes when the user's reads land or the tab shows again
      const job = queue.shift();
      const entry = entries.get(job.url);
      if (flying.has(job.url)) continue;
      if (job.kind === "prefetch" && entry && now() - entry.at < FRESH_MS) continue;
      backgroundRunning += 1;
      fetchText(rawApi, job.url, true)
        .catch(() => {})
        .finally(() => {
          backgroundRunning -= 1;
          pump();
        });
    }
  }

  const idle = (fn) =>
    typeof window !== "undefined" && typeof window.requestIdleCallback === "function"
      ? window.requestIdleCallback(fn, { timeout: 2000 })
      : setTimeout(fn, 300);

  // Loads the likely next reads while the browser is idle. Never a read off KEEP; nothing on a data-saving connection.
  function prefetch(urls) {
    if (!account) return;
    if (typeof navigator !== "undefined" && navigator.connection && navigator.connection.saveData) return;
    const wanted = (urls || []).filter(keepable);
    if (!wanted.length) return;
    idle(() => wanted.forEach((url) => schedule(url, "prefetch")));
  }

  // A reader is one page loader. run() notes the reads its loader starts at once; onChange is called when one of
  // them changes on the server (or is refused), so the page can draw again quietly.
  function reader(onChange) {
    const self = {
      urls: new Set(),
      onChange,
      run(loader) {
        self.urls = new Set();
        const saved = current;
        current = self;
        try {
          return loader();
        } finally {
          current = saved;
        }
      },
      // The page now shows something drawn without kept data: nothing to refresh.
      reset() {
        self.urls = new Set();
      },
      open() {
        readers.add(self);
      },
      close() {
        readers.delete(self);
      },
    };
    readers.add(self);
    return self;
  }

  // Back on the tab after a while: ask again for what the open pages drew.
  if (typeof document !== "undefined" && typeof document.addEventListener === "function") {
    document.addEventListener("visibilitychange", () => {
      if (hidden()) {
        hiddenAt = now();
        return;
      }
      const away = hiddenAt == null ? 0 : now() - hiddenAt;
      hiddenAt = null;
      if (away >= FRESH_MS)
        for (const r of readers) for (const url of r.urls) if (entries.has(url)) schedule(url, "refresh");
      pump();
    });
  }

  window.CTMData = {
    wrap,
    setAccount,
    clear,
    reader,
    prefetch,
    keepable,
    size: () => entries.size,
    limits: Object.freeze({ FRESH_MS, KEEP_MS, MAX_ENTRIES, BACKGROUND_MAX }),
  };
})();
