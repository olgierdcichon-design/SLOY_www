/* SLOY: cookie consent + Google Analytics 4 (loaded only after consent, only on sloy.pl). */
(function () {
  var s = document.currentScript, GA = s && s.getAttribute('data-ga');
  var KEY = 'sloy-consent', host = location.hostname;
  var prod = host === 'sloy.pl' || host === 'www.sloy.pl';
  var test = false;
  try { test = localStorage.getItem('sloy-consent-test') === '1'; } catch (e) {}
  if (!prod && !test) return; // staging / preview: no banner, no tracking

  function get() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function set(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }

  var loaded = false;
  function loadGA() {
    if (loaded || !GA || !prod) return; loaded = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { dataLayer.push(arguments); };
    gtag('consent', 'default', { ad_storage: 'granted', ad_user_data: 'granted', ad_personalization: 'granted', analytics_storage: 'granted' });
    gtag('js', new Date());
    gtag('config', GA);
    var t = document.createElement('script'); t.async = true;
    t.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA;
    document.head.appendChild(t);
  }

  function banner() {
    if (document.querySelector('.consent')) return;
    var d = document.createElement('div');
    d.className = 'consent'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-label', 'Pliki cookie');
    d.innerHTML = '<p>Używamy plików cookie do analizy ruchu (Google Analytics), żeby lepiej pokazywać nasze przedmioty. ' +
      'Niezbędne pliki działają zawsze. <a class="link" href="/cookies/">Więcej o cookies</a></p>' +
      '<div class="consent__actions"><button type="button" class="btn" data-c="all">Akceptuję</button>' +
      '<button type="button" class="btn btn--line" data-c="necessary">Tylko niezbędne</button></div>';
    d.addEventListener('click', function (e) {
      var v = e.target.getAttribute && e.target.getAttribute('data-c');
      if (!v) return;
      set(v); d.remove();
      if (v === 'all') loadGA();
      else if (loaded) location.reload(); // withdraw consent: stop GA
    });
    document.body.appendChild(d);
  }

  // "Ustawienia cookies" links: <a href="#cookies">
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href="#cookies"]');
    if (a) { e.preventDefault(); banner(); }
  });

  var v = get();
  if (v === 'all') loadGA();
  // show banner after hydration so React never sees it
  if (!v) window.addEventListener('load', function () { setTimeout(banner, 600); });
})();
