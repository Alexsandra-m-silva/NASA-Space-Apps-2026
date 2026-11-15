(() => {
  const isPortuguese = document.documentElement.lang.toLowerCase().startsWith("pt");
  const text = isPortuguese
    ? {
        open: "Abrir chat do Climate Guardian",
        close: "Fechar chat",
        title: "Climate Guardian",
        subtitle: "Pergunte sobre os dados desta tela",
        welcome: "Olá! Posso ajudar a interpretar os dados e indicadores exibidos nesta página.",
        placeholder: "Escreva sua pergunta…",
        send: "Enviar",
        thinking: "Analisando os dados da tela…",
        error: "Não foi possível obter uma resposta. Tente novamente.",
        contextMissing: "Nenhum texto de dados foi encontrado nesta tela.",
      }
    : {
        open: "Open Climate Guardian chat",
        close: "Close chat",
        title: "Climate Guardian",
        subtitle: "Ask about the data on this screen",
        welcome: "Hello! I can help interpret the data and indicators shown on this page.",
        placeholder: "Ask a question…",
        send: "Send",
        thinking: "Reviewing the screen data…",
        error: "Could not get a response. Please try again.",
        contextMissing: "No screen text was found.",
      };

  const root = document.createElement("section");
  root.id = "guardian-chat";
  root.dataset.assistantUi = "true";
  root.innerHTML = `
    <section id="guardian-chat-panel" role="dialog" aria-modal="false"
      aria-labelledby="guardian-chat-title" aria-hidden="true" hidden>
      <header id="guardian-chat-header">
        <div>
          <strong id="guardian-chat-title">${text.title}</strong>
          <span>${text.subtitle}</span>
        </div>
        <button id="guardian-chat-close" type="button" aria-label="${text.close}">×</button>
      </header>
      <div id="guardian-chat-messages" role="log" aria-live="polite"></div>
      <form id="guardian-chat-form">
        <textarea id="guardian-chat-input" rows="2" maxlength="4000"
          aria-label="${text.placeholder}" placeholder="${text.placeholder}" required></textarea>
        <button id="guardian-chat-send" type="submit">${text.send}</button>
      </form>
    </section>
    <button id="guardian-chat-toggle" type="button" aria-label="${text.open}" aria-expanded="false">
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <circle cx="32" cy="32" r="30" fill="#f0c36a"/>
        <path d="M12 52c2-10 9-15 20-15s18 5 20 15" fill="#254c3b"/>
        <circle cx="32" cy="26" r="13" fill="#f4d0a0"/>
        <path d="M19 26c0-11 6-17 14-17 9 0 15 7 14 17-3-2-6-6-8-10-4 5-11 8-20 8z" fill="#35251d"/>
        <circle cx="27" cy="27" r="1.5" fill="#30231a"/>
        <circle cx="37" cy="27" r="1.5" fill="#30231a"/>
        <path d="M28 33c2 2 6 2 8 0" fill="none" stroke="#9c5946" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
    </button>`;
  document.body.appendChild(root);

  const panel = root.querySelector("#guardian-chat-panel");
  const toggle = root.querySelector("#guardian-chat-toggle");
  const close = root.querySelector("#guardian-chat-close");
  const messages = root.querySelector("#guardian-chat-messages");
  const form = root.querySelector("#guardian-chat-form");
  const input = root.querySelector("#guardian-chat-input");
  const send = root.querySelector("#guardian-chat-send");
  const history = [];

  function addMessage(content, role) {
    const bubble = document.createElement("div");
    bubble.className = `guardian-chat-message ${role}`;
    bubble.textContent = content;
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
  }

  function collectScreenContext() {
    const snapshot = document.body.cloneNode(true);
    snapshot.querySelectorAll("[data-assistant-ui], script, style, noscript").forEach((node) => node.remove());
    const visibleText = (snapshot.innerText || snapshot.textContent || "").replace(/\n{3,}/g, "\n\n").trim();
    const controls = [...document.querySelectorAll("input, select, textarea")]
      .filter((control) => !control.closest("[data-assistant-ui]") &&
        control.type !== "password" && control.type !== "hidden" && control.getClientRects().length > 0)
      .map((control) => {
        const label = control.getAttribute("aria-label") || control.id || control.name || control.tagName.toLowerCase();
        const value = control.type === "checkbox" || control.type === "radio"
          ? (control.checked ? "checked" : "not checked")
          : control.value;
        return value ? `${label}: ${value}` : "";
      })
      .filter(Boolean);
    const imageDescriptions = [...snapshot.querySelectorAll("img[alt]")]
      .map((image) => image.alt.trim())
      .filter(Boolean)
      .map((alt) => `Image: ${alt}`);
    const context = [
      `Page: ${document.title} (${location.pathname})`,
      visibleText,
      controls.length ? `Current control values:\n${controls.join("\n")}` : "",
      imageDescriptions.length ? imageDescriptions.join("\n") : "",
    ].filter(Boolean).join("\n\n");
    const limit = 15950;
    return context.length > limit ? `${context.slice(0, limit)}\n[Screen context truncated]` : (context || text.contextMissing);
  }

  function setOpen(open) {
    panel.hidden = !open;
    panel.setAttribute("aria-hidden", String(!open));
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? text.close : text.open);
    if (open) input.focus();
    else toggle.focus();
  }

  addMessage(text.welcome, "assistant");
  toggle.addEventListener("click", () => setOpen(panel.hidden));
  close.addEventListener("click", () => setOpen(false));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) setOpen(false);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (!question || send.disabled) return;

    addMessage(question, "user");
    input.value = "";
    send.disabled = true;
    input.disabled = true;
    const pending = addMessage(text.thinking, "assistant pending");
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: question,
          screen_context: collectScreenContext(),
          history: history.slice(-12),
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || text.error);
      pending.textContent = result.answer;
      history.push({ role: "user", content: question }, { role: "assistant", content: result.answer });
      if (history.length > 12) history.splice(0, history.length - 12);
    } catch (error) {
      pending.textContent = error.message || text.error;
      pending.classList.add("error");
    } finally {
      pending.classList.remove("pending");
      send.disabled = false;
      input.disabled = false;
      input.focus();
      messages.scrollTop = messages.scrollHeight;
    }
  });
})();
