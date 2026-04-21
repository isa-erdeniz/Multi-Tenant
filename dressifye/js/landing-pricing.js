/**
 * Ana sayfa #pricing: /api/pricing (D1) ile fiyat + features güncellenir.
 * Kartlar: card-starter, card-elite, card-platinum + ul.feature-list
 * Diamond: #enterprise-section (tier_slug diamond)
 */
(function () {
  function checkSvg(iconClass) {
    return (
      '<svg class="w-5 h-5 ' +
      iconClass +
      ' flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>'
    );
  }

  function priceNum(row) {
    var v = row.price_usd;
    if (v == null) return NaN;
    return Number(v);
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

  /** tier_slug öncelikli; isimden elite ile platinum ayrılır (ikisi birden olmamalı). */
  function inferTierSlug(row) {
    if (row.tier_slug)
      return String(row.tier_slug).toLowerCase().trim();
    var n = String(row.name || row.plan_name || "").toLowerCase();
    if (n.indexOf("başlang") >= 0 || n.indexOf("baslang") >= 0) return "starter";
    if (n.indexOf("kurum") >= 0) return "diamond";
    if (n.indexOf("platin") >= 0 || n.indexOf("profes") >= 0) return "platinum";
    if (n.indexOf("elite") >= 0) return "elite";
    return "";
  }

  function indexByTier(rows) {
    var map = {};
    rows.forEach(function (r) {
      if (r.error) return;
      var slug = inferTierSlug(r);
      if (slug) map[slug] = r;
    });
    return map;
  }

  function sortPlans(rows) {
    return rows
      .filter(function (r) {
        return !r.error;
      })
      .slice()
      .sort(function (a, b) {
        return priceNum(a) - priceNum(b);
      });
  }

  function formatUsd(n) {
    if (!isFinite(n)) return "—";
    return "$" + n;
  }

  function rowForTier(byTier, sorted, slug) {
    if (byTier[slug]) return byTier[slug];
    for (var i = 0; i < sorted.length; i++) {
      if (inferTierSlug(sorted[i]) === slug) return sorted[i];
    }
    return null;
  }

  function resolveDiamondRow(byTier, sorted) {
    if (byTier.diamond) return byTier.diamond;
    if (sorted.length === 0) return null;
    var last = sorted[sorted.length - 1];
    if (inferTierSlug(last) === "diamond") return last;
    return null;
  }

  function featureLinesFromRow(row) {
    var lines = parseFeatures(row.features).map(function (s) {
      return String(s);
    });
    var maxT = row.max_tryon;
    if (maxT != null && Number(maxT) < 999999) {
      lines.push("Deneme kotası: " + maxT);
    }
    return lines;
  }

  function fillFeatureList(ul, row, iconClass) {
    if (!ul || !row) return;
    var lines = featureLinesFromRow(row);
    if (lines.length === 0) return;
    iconClass = iconClass || "text-primary";
    ul.innerHTML = "";
    lines.forEach(function (text) {
      var li = document.createElement("li");
      li.className = "flex items-center gap-3";
      li.innerHTML = checkSvg(iconClass);
      var span = document.createElement("span");
      span.textContent = text;
      li.appendChild(span);
      ul.appendChild(li);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var starter = document.getElementById("landing-price-starter");
    var elite = document.getElementById("landing-price-elite");
    var platinum = document.getElementById("landing-price-platinum");
    var enterpriseUsd = document.getElementById("landing-price-enterprise-usd");
    var enterpriseText = document.getElementById("landing-price-enterprise-text");
    var enterpriseBlurbTr = document.getElementById("enterprise-blurb-tr");
    var enterpriseBlurbEn = document.getElementById("enterprise-blurb-en");
    var proProduct = document.getElementById("pro-product-price");
    var listStarter = document.querySelector("#card-starter .feature-list");
    var listElite = document.querySelector("#card-elite .feature-list");
    var listPlatinum = document.querySelector("#card-platinum .feature-list");
    var listDiamond = document.querySelector("#enterprise-section .feature-list");

    if (
      !starter &&
      !elite &&
      !platinum &&
      !enterpriseUsd &&
      !enterpriseText &&
      !proProduct &&
      !listStarter &&
      !listElite &&
      !listPlatinum &&
      !listDiamond
    )
      return;

    fetch("/api/pricing")
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!Array.isArray(data) || data.length === 0) return;
        var sorted = sortPlans(data);
        if (sorted.length === 0) return;
        var byTier = indexByTier(data);

        var starterRow = rowForTier(byTier, sorted, "starter") || sorted[0];
        var eliteRow = rowForTier(byTier, sorted, "elite");
        var platinumRow = rowForTier(byTier, sorted, "platinum");
        if (!platinumRow && sorted.length >= 2) {
          var last = sorted[sorted.length - 1];
          if (inferTierSlug(last) === "diamond" && sorted.length >= 3) {
            platinumRow = sorted[sorted.length - 2];
          } else if (inferTierSlug(last) !== "diamond") {
            platinumRow = last;
          }
        }
        var diamondRow = resolveDiamondRow(byTier, sorted);

        if (starter && starterRow) {
          starter.textContent = formatUsd(priceNum(starterRow));
        }
        if (elite && eliteRow) {
          elite.textContent = formatUsd(priceNum(eliteRow));
        }
        if (platinum && platinumRow) {
          platinum.textContent = formatUsd(priceNum(platinumRow));
        }
        if (enterpriseUsd && enterpriseText && diamondRow) {
          var ep = priceNum(diamondRow);
          if (isFinite(ep) && ep > 0) {
            enterpriseUsd.textContent = formatUsd(ep);
            enterpriseUsd.classList.remove("hidden");
            enterpriseText.classList.add("hidden");
          }
        }

        if (diamondRow) {
          if (enterpriseBlurbTr && diamondRow.description) {
            enterpriseBlurbTr.textContent = String(diamondRow.description);
          }
          if (enterpriseBlurbEn) {
            if (diamondRow.description_en) {
              enterpriseBlurbEn.textContent = String(diamondRow.description_en);
            } else if (diamondRow.description) {
              enterpriseBlurbEn.textContent = String(diamondRow.description);
            }
          }
        }

        fillFeatureList(listStarter, starterRow);
        fillFeatureList(listElite, eliteRow);
        fillFeatureList(listPlatinum, platinumRow);
        fillFeatureList(listDiamond, diamondRow, "text-amber-400");

        if (proProduct) {
          var pr = rowForTier(byTier, sorted, "platinum");
          if (
            !pr &&
            sorted.length >= 2 &&
            inferTierSlug(sorted[sorted.length - 1]) === "diamond"
          ) {
            pr = sorted[sorted.length - 2];
          }
          if (pr) proProduct.textContent = formatUsd(priceNum(pr));
          var btnPro = document.getElementById("btn-cart-platinum-pro");
          if (btnPro && pr && isFinite(priceNum(pr))) {
            btnPro.setAttribute(
              "onclick",
              "addToCart('platinum-plan', " + priceNum(pr) + ")"
            );
          }
        }

        function patchCartBtn(btnId, planId, row, enterpriseOnly) {
          var el = document.getElementById(btnId);
          if (!el) return;
          if (enterpriseOnly) {
            el.setAttribute("onclick", "addToCart('enterprise-plan', 0)");
            return;
          }
          if (!row) return;
          var u = priceNum(row);
          if (!isFinite(u)) return;
          el.setAttribute(
            "onclick",
            "addToCart('" + planId + "', " + u + ")"
          );
        }
        patchCartBtn("btn-cart-starter", "starter-plan", starterRow, false);
        patchCartBtn("btn-cart-elite", "elite-plan", eliteRow, false);
        patchCartBtn("btn-cart-platinum", "platinum-plan", platinumRow, false);
        patchCartBtn("btn-cart-enterprise", "enterprise-plan", diamondRow, true);
      })
      .catch(function () {});
  });
})();
