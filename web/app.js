(() => {
  const chat = document.getElementById("chat");
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("send");
  const userIdInput = document.getElementById("userId");
  let sessionId = localStorage.getItem("session_id") || "";

  function append(role, text) {
    const el = document.createElement("div");
    el.className = "msg " + (role === "user" ? "user" : "bot");
    el.textContent = text;
    chat.appendChild(el);
    chat.scrollTop = chat.scrollHeight;
  }

  async function send() {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    append("user", text);
    sendBtn.disabled = true;
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          user_id: userIdInput.value.trim() || "u001",
          session_id: sessionId || undefined
        })
      });
      const data = await res.json();
      if (data.session_id && !sessionId) {
        sessionId = data.session_id;
        localStorage.setItem("session_id", sessionId);
      }
      append("bot", data.reply || "（无响应）");
    } catch (e) {
      append("bot", "请求失败");
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") send();
  });
})();
