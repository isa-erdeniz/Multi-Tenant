/**
 * Sepet: localStorage (dressifye_cart_v1), tek plan kuralı — add() önceki satırları siler.
 * Fiyatlar USD: satırda unitPriceUsd (addToCart ile) yoksa katalog price (USD) kullanılır.
 * Rozet: saveCart → updateBadges; storage / pageshow / visibility ile senkron.
 */
(function () {
  var STORAGE_KEY = 'dressifye_cart_v1';

  function catalog() {
    return {
      'starter-plan': {
        id: 'starter-plan',
        nameTr: 'Başlangıç Planı',
        nameEn: 'Starter Plan',
        price: 49,
      },
      'pro-plan': {
        id: 'pro-plan',
        nameTr: 'Pro Plan',
        nameEn: 'Pro Plan',
        price: 899,
      },
      'elite-plan': {
        id: 'elite-plan',
        nameTr: 'Elite Plan',
        nameEn: 'Elite Plan',
        price: 249,
      },
      'platinum-plan': {
        id: 'platinum-plan',
        nameTr: 'Platinum Plan',
        nameEn: 'Platinum Plan',
        price: 899,
      },
      'enterprise-plan': {
        id: 'enterprise-plan',
        nameTr: 'Kurumsal Plan',
        nameEn: 'Enterprise Plan',
        price: 0,
        priceOnRequest: true,
      },
    };
  }

  function loadCart() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      var data = JSON.parse(raw);
      return Array.isArray(data) ? data : [];
    } catch (e) {
      return [];
    }
  }

  function saveCart(items) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    updateBadges();
    window.dispatchEvent(new CustomEvent('dressifye-cart-updated'));
    window.dispatchEvent(new CustomEvent('cart-updated'));
  }

  function lineTotal(item) {
    var p = catalog()[item.id];
    if (!p || p.priceOnRequest) return 0;
    var snap = item.unitPriceUsd;
    if (snap != null && isFinite(Number(snap))) {
      return Number(snap) * item.qty;
    }
    return p.price * item.qty;
  }

  window.dressifyeCart = {
    catalog: catalog,
    getItems: loadCart,
    /**
     * Tek plan kuralı. unitPriceUsd: D1’den gelen USD (addToCart ile); yoksa katalog fiyatı.
     */
    add: function (productId, qty, unitPriceUsd) {
      var c = catalog();
      if (!c[productId]) return;
      var q = Math.max(1, parseInt(qty, 10) || 1);
      var line = { id: productId, qty: q };
      var u = unitPriceUsd;
      if (u !== undefined && u !== null && isFinite(Number(u))) {
        line.unitPriceUsd = Number(u);
      }
      saveCart([line]);
    },
    setQty: function (productId, qty) {
      var items = loadCart();
      var q = parseInt(qty, 10);
      var idx = items.findIndex(function (i) {
        return i.id === productId;
      });
      if (q <= 0) {
        if (idx >= 0) items.splice(idx, 1);
      } else if (idx >= 0) items[idx].qty = q;
      saveCart(items);
    },
    remove: function (productId) {
      saveCart(
        loadCart().filter(function (i) {
          return i.id !== productId;
        })
      );
    },
    clear: function () {
      saveCart([]);
    },
    lineTotal: lineTotal,
    getTotal: function () {
      return loadCart().reduce(function (sum, item) {
        return sum + lineTotal(item);
      }, 0);
    },
    getItemCount: function () {
      return loadCart().reduce(function (sum, item) {
        return sum + item.qty;
      }, 0);
    },
    getProduct: function (productId) {
      return catalog()[productId];
    },
  };

  function updateBadges() {
    var n = window.dressifyeCart.getItemCount();
    document.querySelectorAll('[data-cart-badge]').forEach(function (el) {
      el.textContent = n > 99 ? '99+' : String(n);
      el.classList.toggle('hidden', n === 0);
    });
  }

  document.addEventListener('DOMContentLoaded', updateBadges);
  window.addEventListener('storage', function (e) {
    if (e.key === STORAGE_KEY) updateBadges();
  });
  window.addEventListener('pageshow', function (ev) {
    if (ev.persisted) updateBadges();
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') updateBadges();
  });

  window.addToCart = function (productId, price) {
    var raw = parseFloat(price);
    var unit = isFinite(raw) ? raw : undefined;
    window.dressifyeCart.add(productId, 1, unit);
    if (window.console && console.debug) {
      console.debug('addToCart', productId, unit);
    }
    window.location.href = '/sepet/';
  };
})();
