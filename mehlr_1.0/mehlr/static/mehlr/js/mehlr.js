"use strict";

const MEHLR = (() => {

  const Chat = {
    container: null, form: null, input: null, sendBtn: null, conversationId: null,

    init() {
      this.container  = document.getElementById("chat-messages");
      this.form       = document.getElementById("chat-form");
      this.input      = document.getElementById("chat-input");
      this.sendBtn    = document.getElementById("chat-send-btn");
      this.conversationId = document.getElementById("conversation-id-field")?.value || null;
      if (!this.form) return;
      this._bindEvents();
      this.scrollToBottom();
    },

    _bindEvents() {
      this.input?.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); this.submit(); }
      });

      this.input?.addEventListener("input", () => {
        const count = this.input.value.length;
        const counter = document.getElementById("char-counter");
        if (counter) counter.textContent = `${count} / 2000`;
        if (count > 1900) counter?.classList.add("text-red-500");
        else counter?.classList.remove("text-red-500");
      });

      document.addEventListener("htmx:beforeRequest", (e) => {
        if (e.detail.elt === this.form) {
          this._setLoading(true);
          this._appendUserBubble(this.input.value.trim());
        }
      });

      document.addEventListener("htmx:afterSwap", (e) => {
        if (e.detail.target?.id === "chat-messages" ||
            e.detail.target?.closest("#chat-messages")) {
          this._setLoading(false);
          this.scrollToBottom();
          this._updateConversationUrl();
          this.input.value = "";
          this.input.focus();
        }
      });

      document.addEventListener("htmx:responseError", () => {
        this._setLoading(false);
        this._showError("Yanıt alınamadı. Lütfen tekrar deneyin.");
      });

      document.addEventListener("htmx:sendError", () => {
        this._setLoading(false);
        this._showError("Bağlantı hatası. İnternet bağlantınızı kontrol edin.");
      });
    },

    submit() {
      if (!this.input?.value.trim()) return;
      this.form?.dispatchEvent(new Event("submit", { bubbles: true }));
    },

    scrollToBottom(smooth = true) {
      if (!this.container) return;
      this.container.scrollTo({ top: this.container.scrollHeight, behavior: smooth ? "smooth" : "instant" });
    },

    _setLoading(isLoading) {
      if (this.sendBtn) {
        this.sendBtn.disabled = isLoading;
        this.sendBtn.innerHTML = isLoading
          ? `<span class="mehlr-spinner"></span> Yanıt bekleniyor…`
          : `Gönder`;
      }
      const typingEl = document.getElementById("typing-indicator");
      if (typingEl) typingEl.classList.toggle("hidden", !isLoading);
    },

    _appendUserBubble(text) {
      if (!this.container || !text) return;
      const bubble = document.createElement("div");
      bubble.className = "message message--user fade-in";
      bubble.innerHTML = `<div class="message__content">${_escapeHtml(text)}</div>`;
      this.container.appendChild(bubble);
      this.scrollToBottom();
    },

    _updateConversationUrl() {
      const newId = document.getElementById("conversation-id-field")?.value;
      if (newId && newId !== this.conversationId) {
        this.conversationId = newId;
        window.history.replaceState({}, "", `/mehlr/chat/conversation/${newId}/`);
      }
    },

    _showError(msg) {
      if (!this.container) return;
      const el = document.createElement("div");
      el.className = "message message--error fade-in";
      el.innerHTML = `<div class="message__content text-red-500">⚠ ${_escapeHtml(msg)}</div>`;
      this.container.appendChild(el);
      this.scrollToBottom();
      setTimeout(() => el.remove(), 6000);
    },
  };

  const ProjectSelector = {
    init() {
      document.querySelector(".project-item.active")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      document.addEventListener("htmx:afterSwap", (e) => {
        if (e.detail.target?.id === "project-meta-panel") _renderCapabilityBadges(e.detail.target);
      });
    },
  };

  const Report = {
    init() {
      const form = document.getElementById("report-create-form");
      if (!form) return;
      const typeSelect = form.querySelector("[name=report_type]");
      typeSelect?.addEventListener("change", () => this._updateDescription(typeSelect.value));
    },
    _updateDescription(type) {
      const descriptions = {
        summary: "Genel durum özeti — metrikler, gelişmeler, öneriler.",
        trend_report: "Trend analizi — yönelimler ve gelecek tahminleri.",
        audit_report: "Denetim raporu — uyumluluk, riskler, aksiyonlar.",
        performance: "Performans raporu — KPI'lar ve iyileştirme alanları.",
        custom: "Özel sorgu — serbest metin girin.",
      };
      const desc = document.getElementById("report-type-description");
      if (desc) desc.textContent = descriptions[type] || "";
      const customInput = document.getElementById("custom-query-wrapper");
      if (customInput) customInput.classList.toggle("hidden", type !== "custom");
    },
  };

  const Dashboard = {
    init() {
      document.querySelectorAll(".project-card").forEach((card) => {
        card.addEventListener("mouseenter", () => card.classList.add("project-card--hover"));
        card.addEventListener("mouseleave", () => card.classList.remove("project-card--hover"));
      });
      document.querySelectorAll("[data-count-to]").forEach((el) => {
        _animateCount(el, parseInt(el.dataset.countTo, 10));
      });
    },
  };

  const Toast = {
    show(message, type = "info", duration = 4000) {
      const container = document.getElementById("toast-container") || _createToastContainer();
      const toast = document.createElement("div");
      toast.className = `toast toast--${type} fade-in`;
      toast.innerHTML = `<span>${_escapeHtml(message)}</span><button onclick="this.parentElement.remove()" class="toast__close">✕</button>`;
      container.appendChild(toast);
      setTimeout(() => toast.classList.add("toast--visible"), 10);
      setTimeout(() => { toast.classList.remove("toast--visible"); setTimeout(() => toast.remove(), 300); }, duration);
    },
  };

  function _escapeHtml(str) {
    return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  }
  function _createToastContainer() {
    const el = document.createElement("div");
    el.id = "toast-container"; el.className = "toast-container";
    document.body.appendChild(el); return el;
  }
  function _renderCapabilityBadges(panel) {
    panel.querySelectorAll("[data-capability]").forEach((el) => {
      el.textContent = el.dataset.capability.replace(/_/g," ").replace(/\b\w/g,(c)=>c.toUpperCase());
    });
  }
  function _animateCount(el, target) {
    let current = 0; const step = Math.ceil(target / 40);
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current.toLocaleString("tr-TR");
      if (current >= target) clearInterval(timer);
    }, 30);
  }
  function _initDjangoMessages() {
    document.querySelectorAll("[data-django-message]").forEach((el) => {
      const type = el.dataset.djangoMessageLevel === "40" ? "error" : el.dataset.djangoMessageLevel === "30" ? "warning" : "info";
      Toast.show(el.textContent.trim(), type); el.remove();
    });
  }

  function init() {
    Chat.init(); ProjectSelector.init(); Report.init(); Dashboard.init(); _initDjangoMessages();
  }

  document.addEventListener("DOMContentLoaded", init);
  return { Chat, Toast, Report, Dashboard };
})();
