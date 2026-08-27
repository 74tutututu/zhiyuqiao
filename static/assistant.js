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
        const lines = escapeHtml(text).replace(/\r\n/g, "\n").split("\n");
        const html = [];

        function inline(value) {
            return value
                .replace(/`([^`]+)`/g, "<code>$1</code>")
                .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
        }

        function isTableSeparator(value) {
            return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(value);
        }

        function tableCells(value) {
            return value.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
        }

        let index = 0;
        while (index < lines.length) {
            const line = lines[index].trim();
            if (!line) {
                index += 1;
                continue;
            }
            if (index + 1 < lines.length && line.includes("|") && isTableSeparator(lines[index + 1])) {
                const headers = tableCells(line);
                index += 2;
                const rows = [];
                while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
                    rows.push(tableCells(lines[index]));
                    index += 1;
                }
                html.push(`<div class="table-scroll"><table><thead><tr>${headers.map((cell) => `<th>${inline(cell)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${headers.map((_, cellIndex) => `<td>${inline(row[cellIndex] || "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
                continue;
            }
            const heading = line.match(/^(#{1,3})\s+(.+)$/);
            if (heading) {
                const level = heading[1].length;
                html.push(`<h${level}>${inline(heading[2])}</h${level}>`);
                index += 1;
                continue;
            }
            if (/^(-{3,}|\*{3,})$/.test(line)) {
                html.push("<hr>");
                index += 1;
                continue;
            }
            const unordered = /^[-*]\s+/.test(line);
            const ordered = /^\d+[.)]\s+/.test(line);
            if (unordered || ordered) {
                const tag = unordered ? "ul" : "ol";
                const matcher = unordered ? /^[-*]\s+/ : /^\d+[.)]\s+/;
                const items = [];
                while (index < lines.length && matcher.test(lines[index].trim())) {
                    items.push(`<li>${inline(lines[index].trim().replace(matcher, ""))}</li>`);
                    index += 1;
                }
                html.push(`<${tag}>${items.join("")}</${tag}>`);
                continue;
            }
            if (line.startsWith("&gt; ")) {
                const quotes = [];
                while (index < lines.length && lines[index].trim().startsWith("&gt; ")) {
                    quotes.push(inline(lines[index].trim().slice(5)));
                    index += 1;
                }
                html.push(`<blockquote>${quotes.join("<br>")}</blockquote>`);
                continue;
            }
            const paragraph = [];
            while (index < lines.length && lines[index].trim()) {
                const current = lines[index].trim();
                if (paragraph.length && (/^(#{1,3})\s+/.test(current) || /^[-*]\s+/.test(current) || /^\d+[.)]\s+/.test(current))) {
                    break;
                }
                paragraph.push(inline(current));
                index += 1;
            }
            html.push(`<p>${paragraph.join("<br>")}</p>`);
        }
        return html.join("");
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
