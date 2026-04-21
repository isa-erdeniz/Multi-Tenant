/**
 * Dressifye fiyatlandırma: HTMX + garment_core API + iyzico form gömme.
 */
(function () {
  function apiBase() {
    var m = document.querySelector('meta[name="garment-core-api"]');
    return (m && m.getAttribute("content")) || "";
  }

  function parseFeatures(raw) {
    if (!raw) return [];
    if (Array.isArray(raw)) return raw;
    try {
      var p = JSON.parse(raw);
      return Array.isArray(p) ? p : [];
    } catch (_) {
      return [];
    }
  }

  function inferTierSlug(row) {
    if (row.tier_slug) return String(row.tier_slug).toLowerCase().trim();
    var n = (row.name || "").toLowerCase();
    if (n.indexOf("başlang") >= 0 || n.indexOf("baslang") >= 0) return "starter";
    if (n.indexOf("kurum") >= 0) return "diamond";
    if (n.indexOf("platin") >= 0 || n.indexOf("profes") >= 0) return "platinum";
    if (n.indexOf("elite") >= 0) return "elite";
    return "starter";
  }

  function rowToTier(row) {
    var features = parseFeatures(row.features);
    if (row.max_tryon != null && row.max_tryon < 999999) {
      features = features.concat(["Deneme kotası: " + row.max_tryon]);
    }
    var usd = Number(row.price_usd) || 0;
    var tryP = row.price_try != null ? Number(row.price_try) : null;
    var monthly =
      tryP != null && !isNaN(tryP)
        ? "₺" + tryP + "/ay"
        : "$" + usd + "/ay";
    var yearly =
      tryP != null && !isNaN(tryP)
        ? "₺" + Math.round(tryP * 10) + "/yıl (tahmini)"
        : "$" + Math.round(usd * 10) + "/yıl (tahmini)";
    return {
      id: inferTierSlug(row),
      name: row.name || "Plan",
      blurb: row.description || "",
      monthly: monthly,
      yearly: yearly,
      features: features,
      popular: !!row.is_popular,
    };
  }

  function mountIyzicoForm(htmlContent) {
    var slot = document.getElementById("iyzipay-checkout-form");
    if (!slot || !htmlContent) return;
    slot.innerHTML = htmlContent;
    slot.querySelectorAll("script").forEach(function (old) {
      var s = document.createElement("script");
      if (old.src) s.src = old.src;
      else s.textContent = old.textContent;
      old.replaceWith(s);
    });
  }

  window.pricingPage = function () {
    return {
      period: "monthly",
      customTitle: "",
      selectedTier: "starter",
      d1Source: false,
      init: function () {
        var self = this;
        fetch("/api/pricing")
          .then(function (r) {
            return r.json();
          })
          .then(function (data) {
            if (!data || data.error) return;
            if (!Array.isArray(data) || data.length === 0) return;
            self.tiers = data.map(rowToTier);
            self.d1Source = true;
          })
          .catch(function () {
            /* varsayılan tiers kalır */
          });
      },
      tiers: [
        {
          id: "starter",
          name: "Starter",
          blurb: "Ücretsiz deneme seviyesine yakın giriş paketi.",
          monthly: "₺99",
          yearly: "₺990",
          features: ["Temel AI önerileri", "Sınırlı gardırop", "E-posta destek"],
        },
        {
          id: "elite",
          name: "Elite",
          blurb: "Stil Plus seviyesi — temel premium.",
          monthly: "₺199",
          yearly: "₺1 990",
          features: ["AI stil önerileri", "Sınırlı sanal deneme", "Sosyal paylaşım"],
        },
        {
          id: "platinum",
          name: "Platinum",
          blurb: "Stil Pro + sesli AI asistan.",
          monthly: "₺399",
          yearly: "₺3 990",
          features: [
            "Tüm Elite özellikleri",
            "Sesli AI asistan (Voice AI)",
            "Öncelikli destek",
          ],
        },
        {
          id: "diamond",
          name: "Diamond",
          blurb: "Platinum + white-label raporlar.",
          monthly: "₺699",
          yearly: "₺6 990",
          features: [
            "Tüm Platinum özellikleri",
            "White-label raporlar",
            "Sınırsız kullanım (plan kotasına tabi)",
          ],
        },
      ],
      selectTier: function (id) {
        this.selectedTier = id;
        this.submitCheckout();
      },
      submitCheckout: function () {
        var st = document.getElementById("checkout-status");
        var tok = sessionStorage.getItem("dressifye_access");
        if (!tok) {
          if (st) st.textContent = "Önce Garment Core hesabıyla giriş yapın.";
          return;
        }
        var form = document.getElementById("checkout-init-form");
        if (form) {
          form.classList.remove("hidden");
          if (window.htmx) htmx.trigger(form, "submit");
        }
      },
    };
  };

  document.addEventListener("DOMContentLoaded", function () {
    var base = apiBase().replace(/\/+$/, "");
    if (!base) {
      console.warn("meta garment-core-api tanımlı değil");
      return;
    }

    var loginForm = document.getElementById("login-form");
    if (loginForm) {
      loginForm.setAttribute("hx-post", base + "/api/v1/auth/token/");
      loginForm.setAttribute("hx-target", "#login-status");
      loginForm.setAttribute("hx-swap", "none");
    }

    var checkoutForm = document.getElementById("checkout-init-form");
    if (checkoutForm) {
      checkoutForm.setAttribute(
        "hx-post",
        base + "/api/v1/payments/dressifye/subscription/init/"
      );
      checkoutForm.setAttribute("hx-swap", "none");
    }

    if (window.htmx) {
      if (loginForm) htmx.process(loginForm);
      if (checkoutForm) htmx.process(checkoutForm);
    }

    document.body.addEventListener("htmx:configRequest", function (e) {
      if (e.detail.elt && e.detail.elt.id === "checkout-init-form") {
        var t = sessionStorage.getItem("dressifye_access");
        if (t) e.detail.headers["Authorization"] = "Bearer " + t;
      }
    });

    document.body.addEventListener("htmx:afterRequest", function (e) {
      var el = e.detail.elt;
      var xhr = e.detail.xhr;
      if (!el || !xhr) return;

      if (el.id === "login-form") {
        var loginStatus = document.getElementById("login-status");
        if (xhr.status === 200) {
          try {
            var d = JSON.parse(xhr.responseText);
            sessionStorage.setItem("dressifye_access", d.access || "");
            sessionStorage.setItem("dressifye_refresh", d.refresh || "");
            if (loginStatus)
              loginStatus.textContent = "Giriş başarılı. Plan seçip Satın alabilirsiniz.";
          } catch (err) {
            if (loginStatus) loginStatus.textContent = "Yanıt çözümlenemedi.";
          }
        } else {
          var msg = "Giriş başarısız.";
          try {
            var err = JSON.parse(xhr.responseText);
            if (err.detail) msg = String(err.detail);
            else if (err.error) msg = String(err.error);
          } catch (_) {}
          if (loginStatus) loginStatus.textContent = msg;
        }
        return;
      }

      if (el.id === "checkout-init-form") {
        var cs = document.getElementById("checkout-status");
        if (xhr.status === 200) {
          try {
            var data = JSON.parse(xhr.responseText);
            if (cs) cs.textContent = "";
            mountIyzicoForm(data.checkout_form_content);
          } catch (err) {
            if (cs) cs.textContent = "Form yanıtı işlenemedi.";
          }
        } else {
          var em = "Ödeme formu oluşturulamadı.";
          try {
            var j = JSON.parse(xhr.responseText);
            if (j.error) em = j.error;
          } catch (_) {}
          if (cs) cs.textContent = em;
        }
      }
    });
  });
})();
