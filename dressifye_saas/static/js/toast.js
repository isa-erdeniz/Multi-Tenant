/**
 * Garment Core toast bildirimleri — koyu tema, sabit konum.
 * API: garmentCoreToast.success(msg), .error(), .info(), .warning(), .show(msg, opts)
 * Alias: window.toast
 */
(function () {
    var DEFAULT_MS = 5200;
    var MAX_VISIBLE = 5;

    var variantMeta = {
        success: {
            border: "border-emerald-600/60",
            bg: "bg-gray-900/95",
            text: "text-emerald-100",
            iconWrap: "bg-emerald-500/20 text-emerald-400",
            path: "M5 13l4 4L19 7",
        },
        error: {
            border: "border-red-600/60",
            bg: "bg-gray-900/95",
            text: "text-red-100",
            iconWrap: "bg-red-500/20 text-red-400",
            path: "M6 18L18 6M6 6l12 12",
        },
        info: {
            border: "border-sky-600/60",
            bg: "bg-gray-900/95",
            text: "text-sky-100",
            iconWrap: "bg-sky-500/20 text-sky-400",
            path: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
        },
        warning: {
            border: "border-amber-600/60",
            bg: "bg-gray-900/95",
            text: "text-amber-100",
            iconWrap: "bg-amber-500/20 text-amber-400",
            path: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
        },
    };

    var rootEl = null;

    function ensureRoot() {
        if (rootEl && rootEl.parentNode) return rootEl;
        rootEl = document.createElement("div");
        rootEl.id = "garment-core-toast-root";
        rootEl.setAttribute("aria-live", "polite");
        rootEl.setAttribute("aria-relevant", "additions");
        rootEl.className =
            "pointer-events-none fixed top-4 right-4 z-[100] flex max-h-[calc(100vh-6rem)] w-[min(100vw-2rem,22rem)] flex-col gap-2 overflow-y-auto sm:top-6 sm:right-6";
        document.body.appendChild(rootEl);
        return rootEl;
    }

    function trimStack() {
        var root = ensureRoot();
        while (root.children.length > MAX_VISIBLE) {
            root.removeChild(root.firstChild);
        }
    }

    function iconSvg(variant) {
        var m = variantMeta[variant] || variantMeta.info;
        var isCheck = variant === "success";
        var isErr = variant === "error";
        if (isCheck) {
            return (
                '<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">' +
                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="' +
                m.path +
                '"/></svg>'
            );
        }
        if (isErr) {
            return (
                '<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">' +
                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="' +
                m.path +
                '"/></svg>'
            );
        }
        return (
            '<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">' +
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="' +
            m.path +
            '"/></svg>'
        );
    }

    function push(message, variant, duration) {
        if (!message) return;
        variant = variantMeta[variant] ? variant : "info";
        duration = typeof duration === "number" ? duration : DEFAULT_MS;
        var m = variantMeta[variant];

        var wrap = document.createElement("div");
        wrap.className =
            "pointer-events-auto flex translate-x-4 items-start gap-3 rounded-xl border p-4 opacity-0 shadow-xl backdrop-blur-md transition-all duration-300 ease-out " +
            m.bg +
            " " +
            m.border +
            " " +
            m.text;

        wrap.setAttribute("role", "status");

        var iconBox = document.createElement("span");
        iconBox.className =
            "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg " + m.iconWrap;
        iconBox.innerHTML = iconSvg(variant);

        var text = document.createElement("p");
        text.className = "min-w-0 flex-1 text-sm font-medium leading-snug";
        text.textContent = message;

        var closeBtn = document.createElement("button");
        closeBtn.type = "button";
        closeBtn.className =
            "shrink-0 rounded-lg p-1 text-gray-400 transition-colors hover:bg-white/10 hover:text-white";
        closeBtn.setAttribute("aria-label", "Kapat");
        closeBtn.innerHTML =
            '<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>';

        wrap.appendChild(iconBox);
        wrap.appendChild(text);
        wrap.appendChild(closeBtn);

        var root = ensureRoot();
        trimStack();
        root.appendChild(wrap);

        var hideTimer = null;

        function removeToast() {
            if (hideTimer) clearTimeout(hideTimer);
            wrap.classList.add("translate-x-4", "opacity-0");
            setTimeout(function () {
                if (wrap.parentNode) wrap.parentNode.removeChild(wrap);
            }, 320);
        }

        closeBtn.addEventListener("click", removeToast);

        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                wrap.classList.remove("translate-x-4", "opacity-0");
                wrap.classList.add("translate-x-0", "opacity-100");
            });
        });

        if (duration > 0) {
            hideTimer = setTimeout(removeToast, duration);
        }

        return { dismiss: removeToast };
    }

    var api = {
        show: function (message, opts) {
            opts = opts || {};
            return push(String(message), opts.variant || "info", opts.duration);
        },
        success: function (message, duration) {
            return push(String(message), "success", duration);
        },
        error: function (message, duration) {
            return push(String(message), "error", duration);
        },
        info: function (message, duration) {
            return push(String(message), "info", duration);
        },
        warning: function (message, duration) {
            return push(String(message), "warning", duration);
        },
    };

    window.garmentCoreToast = api;
    window.toast = api;
})();
