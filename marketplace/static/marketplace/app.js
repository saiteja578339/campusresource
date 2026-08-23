document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-dialog-open]").forEach((button) => {
    button.addEventListener("click", () => {
      const dialog = document.getElementById(button.dataset.dialogOpen);
      if (dialog && typeof dialog.showModal === "function") dialog.showModal();
    });
  });

  document.querySelectorAll("[data-dialog-close]").forEach((button) => {
    button.addEventListener("click", () => button.closest("dialog")?.close());
  });

  document.querySelectorAll("dialog").forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  });

  const toasts = document.querySelectorAll(".toast");
  if (toasts.length) {
    window.setTimeout(() => {
      toasts.forEach((toast) => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(-8px)";
        toast.style.transition = "all .25s ease";
      });
    }, 4500);
  }

  const assistant = document.querySelector("[data-chat-messages]");
  const assistantForm = document.querySelector("[data-assistant-form]");
  const assistantRoot = document.getElementById("assistant-chat");

  const addAssistantMessage = (role, text, listings = []) => {
    if (!assistant) return null;
    const article = document.createElement("article");
    article.className = `assistant-message ${role}`;
    const avatar = document.createElement("span");
    avatar.textContent = role === "user" ? "You" : "✦";
    const content = document.createElement("div");
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    content.appendChild(paragraph);
    if (listings.length) {
      const results = document.createElement("div");
      results.className = "assistant-results";
      listings.forEach((listing) => {
        const link = document.createElement("a");
        link.href = `/listing/${listing.id}/`;
        const name = document.createElement("span");
        name.textContent = listing.title;
        const price = document.createElement("b");
        price.textContent = listing.price === 0 ? listing.transaction_type : `₹${Math.round(listing.price)}`;
        link.append(name, price);
        results.appendChild(link);
      });
      content.appendChild(results);
    }
    const meta = document.createElement("small");
    meta.textContent = role === "user" ? "You" : "AI assistant";
    content.appendChild(meta);
    article.append(avatar, content);
    assistant.appendChild(article);
    assistant.scrollTop = assistant.scrollHeight;
    return article;
  };

  if (assistantForm && assistantRoot) {
    assistantForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const input = assistantForm.elements.message;
      const message = input.value.trim();
      if (!message) return;
      addAssistantMessage("user", message);
      const formData = new FormData(assistantForm);
      formData.set("message", message);
      input.value = "";
      const loading = addAssistantMessage("bot", "Searching the campus knowledge base…");
      loading?.classList.add("loading");
      try {
        const response = await fetch(assistantRoot.dataset.endpoint, {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const payload = await response.json();
        loading?.remove();
        if (!response.ok) throw new Error(payload.error || "Assistant request failed.");
        addAssistantMessage("bot", payload.reply, payload.listings || []);
      } catch (error) {
        loading?.remove();
        addAssistantMessage("bot", error.message || "Please try again.");
      }
      input.focus();
    });

    document.querySelectorAll("[data-assistant-prompt]").forEach((button) => {
      button.addEventListener("click", () => {
        assistantForm.elements.message.value = button.dataset.assistantPrompt;
        assistantForm.requestSubmit();
      });
    });
  }
});
