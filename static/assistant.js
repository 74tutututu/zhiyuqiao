(function () {
    const state = {
        skills: (window.__ZHIYUQIAO__ && window.__ZHIYUQIAO__.skills) || [],
        selectedSkill: ((window.__ZHIYUQIAO__ && window.__ZHIYUQIAO__.skills) || [])[0]?.key || "teacher_advisor",
        history: [],
        loading: false,
    };

    const skillList = document.getElementById("skill-list");
    const currentSkillTitle = document.getElementById("current-skill-title");
    const currentSkillDescription = document.getElementById("current-skill-description");
    const chatMessages = document.getElementById("chat-messages");
    const composerInput = document.getElementById("composer-input");
    const sendBtn = document.getElementById("send-btn");
    const clearBtn = document.getElementById("clear-btn");

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function renderMarkdownLite(text) {
        const normalized = escapeHtml(text).replace(/\r\n/g, "\n");
        const blocks = normalized.split(/\n\n+/).map((item) => item.trim()).filter(Boolean);
        const rendered = blocks.map((block) => {
            if (block.startsWith("### ")) {
                return `<h3>${block.slice(4)}</h3>`;
            }
            const lines = block.split("\n");
            if (lines.every((line) => line.trim().startsWith("- "))) {
                const items = lines
                    .map((line) => line.trim().slice(2))
                    .map((line) => `<li>${line.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")}</li>`)
                    .join("");
                return `<ul>${items}</ul>`;
            }
            const html = lines
                .map((line) => line.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>"))
                .join("<br>");
            return `<p>${html}</p>`;
        });
        return rendered.join("");
    }

    function appendMessage(role, text, options = {}) {
        const wrapper = document.createElement("div");
        wrapper.className = `message ${role}`;

        const bubble = document.createElement("div");
        bubble.className = "message-bubble";
        if (role === "assistant") {
            bubble.classList.add("assistant-rendered");
            bubble.innerHTML = renderMarkdownLite(text);
        } else {
            bubble.textContent = text;
        }
        if (options.loading) {
            bubble.dataset.loading = "true";
            bubble.textContent = "正在思考，请稍等...";
        }

        wrapper.appendChild(bubble);
        chatMessages.appendChild(wrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return bubble;
    }

    function setSkill(skillKey) {
        state.selectedSkill = skillKey;
        const skill = state.skills.find((item) => item.key === skillKey);
        if (!skill) {
            return;
        }
        currentSkillTitle.textContent = skill.label;
        currentSkillDescription.textContent = skill.description;
        document.querySelectorAll(".skill-item").forEach((button) => {
            button.classList.toggle("active", button.dataset.skillKey === skillKey);
        });
    }

    async function sendMessage() {
        const text = composerInput.value.trim();
        if (!text || state.loading) {
            return;
        }

        state.loading = true;
        composerInput.value = "";
        sendBtn.disabled = true;

        appendMessage("user", text);
        state.history.push({ role: "user", content: text });
        const loadingBubble = appendMessage("assistant", "", { loading: true });

        try {
            const response = await fetch("/api/message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    skill_key: state.selectedSkill,
                    text,
                    history: state.history,
                }),
            });

            const payload = await response.json();
            if (!response.ok) {
                throw new Error(payload.detail || "请求失败");
            }

            loadingBubble.innerHTML = renderMarkdownLite(payload.reply);
            delete loadingBubble.dataset.loading;
            state.history.push({ role: "assistant", content: payload.reply });
        } catch (error) {
            loadingBubble.innerHTML = `<p>⚠️ ${escapeHtml(error.message || "系统暂时不可用")}</p>`;
            delete loadingBubble.dataset.loading;
        } finally {
            state.loading = false;
            sendBtn.disabled = false;
            composerInput.focus();
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    if (skillList) {
        skillList.addEventListener("click", function (event) {
            const button = event.target.closest(".skill-item");
            if (!button) {
                return;
            }
            setSkill(button.dataset.skillKey);
        });
    }

    if (sendBtn) {
        sendBtn.addEventListener("click", sendMessage);
    }

    if (clearBtn) {
        clearBtn.addEventListener("click", function () {
            state.history = [];
            chatMessages.innerHTML = "";
            composerInput.focus();
        });
    }

    if (composerInput) {
        composerInput.addEventListener("keydown", function (event) {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                event.preventDefault();
                sendMessage();
            }
        });
    }
})();
