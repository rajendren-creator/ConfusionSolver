const chatEl = document.getElementById("chat");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const resetBtn = document.getElementById("reset");

// Conversation sent to the API. The greeting is display-only (API history must start with a user turn).
let history = [];
let greeting = "";
let busy = false;

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function inline(s) {
  return s
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|\W)_(.+?)_(?=\W|$)/g, "$1<em>$2</em>")
    .replace(/(^|[^*])\*([^*]+?)\*(?!\*)/g, "$1<em>$2</em>");
}

// Minimal Markdown: headings, bullet/numbered lists, bold/italic, paragraphs.
function renderMarkdown(md) {
  const lines = escapeHtml(md).split("\n");
  let html = "", list = null, para = [];
  const flushPara = () => { if (para.length) { html += `<p>${inline(para.join("<br>"))}</p>`; para = []; } };
  const closeList = () => { if (list) { html += `</${list}>`; list = null; } };

  for (const raw of lines) {
    const line = raw.trimEnd();
    let m;
    if ((m = line.match(/^#{1,6}\s+(.*)/))) {
      flushPara(); closeList();
      html += `<h3>${inline(m[1])}</h3>`;
    } else if ((m = line.match(/^\s*[-*]\s+(.*)/))) {
      flushPara();
      if (list !== "ul") { closeList(); html += "<ul>"; list = "ul"; }
      html += `<li>${inline(m[1])}</li>`;
    } else if ((m = line.match(/^\s*\d+[.)]\s+(.*)/))) {
      flushPara();
      if (list !== "ol") { closeList(); html += "<ol>"; list = "ol"; }
      html += `<li>${inline(m[1])}</li>`;
    } else if (line.trim() === "") {
      flushPara(); closeList();
    } else {
      closeList();
      para.push(line);
    }
  }
  flushPara(); closeList();
  return html;
}

function addMessage(role, text) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  setContent(el, role, text);
  chatEl.appendChild(el);
  chatEl.scrollTop = chatEl.scrollHeight;
  return el;
}

function setContent(el, role, text) {
  if (role === "user") el.textContent = text;
  else el.innerHTML = renderMarkdown(text);
}

function setBusy(b) {
  busy = b;
  sendBtn.disabled = b;
  resetBtn.disabled = b;
}

async function send(text) {
  history.push({ role: "user", content: text });
  addMessage("user", text);
  const el = addMessage("assistant", "");
  el.classList.add("pending");
  setBusy(true);

  let reply = "";
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      reply += decoder.decode(value, { stream: true });
      setContent(el, "assistant", reply);
      chatEl.scrollTop = chatEl.scrollHeight;
    }
  } catch (err) {
    reply += `\n\n_Connection problem (${err.message}). Please try again._`;
    setContent(el, "assistant", reply);
  } finally {
    el.classList.remove("pending");
    setBusy(false);
    input.focus();
  }

  if (reply.trim()) {
    history.push({ role: "assistant", content: reply });
  } else {
    // Keep the history valid (alternating turns) if nothing came back.
    history.pop();
  }
}

function reset() {
  history = [];
  chatEl.innerHTML = "";
  if (greeting) addMessage("assistant", greeting);
  input.value = "";
  input.focus();
}

form.addEventListener("submit", e => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || busy) return;
  input.value = "";
  send(text);
});

input.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

resetBtn.addEventListener("click", reset);

fetch("/api/greeting")
  .then(r => r.json())
  .then(d => { greeting = d.greeting; reset(); })
  .catch(() => reset());
