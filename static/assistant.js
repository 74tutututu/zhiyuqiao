(function () {
    const boot = window.__ZHIYUQIAO__ || {};
    const skills = boot.skills || [];
    const role = boot.role || "teacher";
    const state = {
        skills,
        selectedSkill: skills[0]?.key || "teacher_advisor",
        history: [],
        loading: false,
    };

    const skillList = document.getElementById("skill-list");
    const currentSkillTitle = document.getElementById("current-skill-title");
    const currentSkillDescription = document.getElementById("current-skill-description");
    const starterPrompts = document.getElementById("starter-prompts");
    const chatMessages = document.getElementById("chat-messages");
    const composerInput = document.getElementById("composer-input");
    const characterCount = document.getElementById("character-count");
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
        const lines = escapeHtml(text)
            .replace(/\r\n/g, "\n")
            // A few models stream compact Markdown tables with || in place of a newline.
            .replace(/\s*\|\|\s*/g, "|\n|")
            .split("\n");
        const html = [];
        const inline = (value) => value
            .replace(/`([^`]+)`/g, "<code>$1</code>")
            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
        const isTableSeparator = (value) => /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(value);
        const tableCells = (value) => value.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());

        let index = 0;
        while (index < lines.length) {
            const line = lines[index].trim();
            if (!line) { index += 1; continue; }
            if (index + 1 < lines.length && line.includes("|") && isTableSeparator(lines[index + 1])) {
                const headers = tableCells(line);
                index += 2;
                const rows = [];
                while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
                    rows.push(tableCells(lines[index])); index += 1;
                }
                html.push(`<div class="table-scroll"><table><thead><tr>${headers.map((cell) => `<th>${inline(cell)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${headers.map((_, cellIndex) => `<td>${inline(row[cellIndex] || "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
                continue;
            }
            const heading = line.match(/^(#{1,4})\s+(.+)$/);
            if (heading) { const level = heading[1].length; html.push(`<h${level}>${inline(heading[2])}</h${level}>`); index += 1; continue; }
            if (/^(-{3,}|\*{3,})$/.test(line)) { html.push("<hr>"); index += 1; continue; }
            const unordered = /^[-*]\s+/.test(line);
            const ordered = /^\d+[.)]\s+/.test(line);
            if (unordered || ordered) {
                const tag = unordered ? "ul" : "ol";
                const matcher = unordered ? /^[-*]\s+/ : /^\d+[.)]\s+/;
                const items = [];
                while (index < lines.length && matcher.test(lines[index].trim())) {
                    items.push(`<li>${inline(lines[index].trim().replace(matcher, ""))}</li>`); index += 1;
                }
                html.push(`<${tag}>${items.join("")}</${tag}>`); continue;
            }
            if (line.startsWith("&gt; ")) {
                const quotes = [];
                while (index < lines.length && lines[index].trim().startsWith("&gt; ")) {
                    quotes.push(inline(lines[index].trim().slice(5))); index += 1;
                }
                html.push(`<blockquote>${quotes.join("<br>")}</blockquote>`); continue;
            }
            const paragraph = [];
            while (index < lines.length && lines[index].trim()) {
                const current = lines[index].trim();
                if (paragraph.length && (/^(#{1,4})\s+/.test(current) || /^[-*]\s+/.test(current) || /^\d+[.)]\s+/.test(current))) break;
                paragraph.push(inline(current)); index += 1;
            }
            html.push(`<p>${paragraph.join("<br>")}</p>`);
        }
        return html.join("");
    }

    function renderEmptyState() {
        if (!chatMessages || state.history.length) return;
        const copy = role === "student"
            ? ["从一个问题开始", "你可以用中文或熟悉的语言提问，我会按你的水平解释。"]
            : ["把教学情境说具体一点", "学习者水平、课堂时长、文化主题和预期产出越清楚，建议越可用。"];
        chatMessages.innerHTML = `<div class="chat-empty"><div><strong>${copy[0]}</strong><span>${copy[1]}</span></div></div>`;
    }

    function appendSources(container, sources) {
        if (!container || !Array.isArray(sources) || !sources.length) return;
        const section = document.createElement("section");
        section.className = "answer-sources";
        section.setAttribute("aria-label", "回答依据");
        const heading = document.createElement("h4");
        heading.textContent = "回答依据";
        section.appendChild(heading);
        const list = document.createElement("div");
        list.className = "source-card-list";
        sources.forEach((source) => {
            const card = document.createElement("a");
            card.className = "source-card";
            card.href = source.source_url || "#";
            if (source.source_url) {
                card.target = "_blank";
                card.rel = "noopener noreferrer";
            }
            const meta = [source.source_org, source.published_date].filter(Boolean).join(" · ");
            const status = source.dynamic ? "动态信息 · 使用前复核" : "公开资料 · 已核验";
            card.innerHTML = `<span>${escapeHtml(source.topic || "海派文化")}</span><strong>${escapeHtml(source.title || source.source || "来源资料")}</strong><small>${escapeHtml(meta)}</small><em>${escapeHtml(status)} ↗</em>`;
            list.appendChild(card);
        });
        section.appendChild(list);
        container.appendChild(section);
    }

    function renderStarterPrompts(skill) {
        if (!starterPrompts) return;
        starterPrompts.innerHTML = "";
        (skill?.starter_prompts || []).forEach((prompt) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "starter-prompt";
            button.textContent = prompt;
            button.addEventListener("click", () => {
                composerInput.value = prompt;
                updateCharacterCount();
                composerInput.focus();
            });
            starterPrompts.appendChild(button);
        });
    }

    function setSkill(skillKey) {
        const skill = state.skills.find((item) => item.key === skillKey);
        if (!skill) return;
        state.selectedSkill = skill.key;
        currentSkillTitle.textContent = skill.label;
        currentSkillDescription.textContent = skill.description;
        document.querySelectorAll(".skill-item").forEach((button) => {
            const active = button.dataset.skillKey === skill.key;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", String(active));
        });
        renderStarterPrompts(skill);
    }

    function updateCharacterCount() {
        if (characterCount && composerInput) characterCount.textContent = `${composerInput.value.length} / 6000`;
    }

    function appendMessage(messageRole, text, options = {}) {
        chatMessages.querySelector(".chat-empty")?.remove();
        const wrapper = document.createElement("div");
        wrapper.className = `message ${messageRole}`;
        const bubble = document.createElement("div");
        bubble.className = "message-bubble";
        if (messageRole === "assistant") {
            bubble.classList.add("assistant-rendered");
            bubble.innerHTML = renderMarkdownLite(text);
        } else {
            bubble.textContent = text;
        }
        if (options.loading) {
            bubble.dataset.loading = "true";
            bubble.setAttribute("role", "status");
            bubble.innerHTML = "<p>正在组织答案，请稍等……</p>";
        }
        wrapper.appendChild(bubble);
        chatMessages.appendChild(wrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return bubble;
    }

    async function sendMessage() {
        const text = composerInput.value.trim();
        if (!text || state.loading) return;
        state.loading = true;
        composerInput.value = "";
        updateCharacterCount();
        sendBtn.disabled = true;
        appendMessage("user", text);
        state.history.push({ role: "user", content: text });
        const loadingBubble = appendMessage("assistant", "", { loading: true });

        try {
            const response = await fetch("/api/message", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRF-Token": boot.csrfToken || "" },
                body: JSON.stringify({ skill_key: state.selectedSkill, text, history: state.history }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.detail || "请求失败");
            loadingBubble.innerHTML = renderMarkdownLite(payload.reply);
            appendSources(loadingBubble, payload.sources);
            delete loadingBubble.dataset.loading;
            loadingBubble.removeAttribute("role");
            state.history.push({ role: "assistant", content: payload.reply });
        } catch (error) {
            loadingBubble.innerHTML = `<p>暂时无法完成：${escapeHtml(error.message || "系统不可用")}。请稍后重试。</p>`;
            delete loadingBubble.dataset.loading;
        } finally {
            state.loading = false;
            sendBtn.disabled = false;
            composerInput.focus();
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    function clearChat() {
        state.history = [];
        chatMessages.innerHTML = "";
        renderEmptyState();
        composerInput.focus();
    }

    skillList?.addEventListener("click", (event) => {
        const button = event.target.closest(".skill-item");
        if (button) setSkill(button.dataset.skillKey);
    });
    document.addEventListener("click", (event) => {
        const trigger = event.target.closest("[data-skill-target]");
        if (!trigger) return;
        setSkill(trigger.dataset.skillTarget);
        composerInput.value = trigger.dataset.prompt || "";
        updateCharacterCount();
        document.querySelector(".assistant-workbench")?.scrollIntoView({ behavior: "smooth", block: "start" });
        window.setTimeout(() => composerInput.focus(), 350);
    });
    sendBtn?.addEventListener("click", sendMessage);
    clearBtn?.addEventListener("click", clearChat);
    composerInput?.addEventListener("input", updateCharacterCount);
    composerInput?.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); sendMessage(); }
    });

    setSkill(state.selectedSkill);
    updateCharacterCount();
    renderEmptyState();
})();
