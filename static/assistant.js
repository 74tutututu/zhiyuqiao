(function () {
    const boot = window.__ZHIYUQIAO__ || {};
    const skills = boot.skills || [];
    const role = boot.role || "teacher";
    const state = {
        skills,
        selectedSkill: skills[0]?.key || "teacher_advisor",
        activeTopic: "自主探索",
        history: [],
        loading: false,
        taskRecords: boot.taskRecords || [],
        progress: boot.progress || { completed: 0, total: 6, percent: 0 },
        artifacts: boot.artifacts || [],
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
    const studentTaskList = document.getElementById("student-task-list");
    const teacherArtifactList = document.getElementById("teacher-artifact-list");

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

    async function postJSON(url, body) {
        const response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRF-Token": boot.csrfToken || "" },
            body: JSON.stringify(body),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || "操作失败");
        return payload;
    }

    function formatDate(value) {
        if (!value) return "刚刚保存";
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? "已保存" : new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
    }

    function updateProgress(progress) {
        state.progress = progress || state.progress;
        const fill = document.getElementById("progress-fill");
        const track = document.getElementById("progress-track");
        const copy = document.getElementById("progress-copy");
        if (fill) fill.style.width = `${state.progress.percent || 0}%`;
        if (track) track.setAttribute("aria-valuenow", String(state.progress.percent || 0));
        if (copy) copy.textContent = `已完成 ${state.progress.completed || 0} / ${state.progress.total || 6} 条文化线索`;
    }

    function renderTaskRecords() {
        if (!studentTaskList) return;
        if (!state.taskRecords.length) {
            studentTaskList.innerHTML = '<div class="record-empty"><strong>还没有学习记录</strong><span>完成一次 AI 对话后，点击“保存为学习任务”。</span></div>';
            return;
        }
        studentTaskList.innerHTML = state.taskRecords.map((task) => {
            const done = task.status === "completed";
            return `<article class="record-card ${done ? "completed" : ""}">
                <div class="record-card-head"><span>${escapeHtml(task.topic)}</span><em>${done ? "已完成" : "进行中"}</em></div>
                <h3>${escapeHtml(task.title)}</h3>
                <p>${escapeHtml(task.prompt)}</p>
                ${done ? `<blockquote><b>我的收获</b>${escapeHtml(task.reflection || "已完成")}</blockquote>` : `<button class="secondary-btn record-action" type="button" data-complete-task="${escapeHtml(task.id)}">完成任务并写反思</button>
                <form class="reflection-form" data-reflection-form="${escapeHtml(task.id)}" hidden><label for="reflection-${escapeHtml(task.id)}">我完成了什么、学会了什么？</label><textarea id="reflection-${escapeHtml(task.id)}" maxlength="2000" required></textarea><div><button class="quiet-btn" type="button" data-cancel-reflection>取消</button><button class="primary-btn" type="submit">保存完成记录</button></div></form>`}
                <small>${formatDate(task.completed_at || task.created_at)}</small>
            </article>`;
        }).join("");
    }

    function renderArtifacts() {
        if (!teacherArtifactList) return;
        if (!state.artifacts.length) {
            teacherArtifactList.innerHTML = '<div class="record-empty"><strong>还没有教案草稿</strong><span>生成教学方案后，点击“保存为教案草稿”。</span></div>';
            return;
        }
        teacherArtifactList.innerHTML = state.artifacts.map((artifact) => `<article class="record-card">
            <div class="record-card-head"><span>${escapeHtml(artifact.skill_key)}</span><em class="${artifact.review_status === "reviewed" ? "reviewed" : ""}">${artifact.review_status === "reviewed" ? "教师已审核" : "待审核"}</em></div>
            <h3>${escapeHtml(artifact.title)}</h3><p>${escapeHtml(artifact.prompt)}</p>
            <a class="secondary-btn record-action" href="/teacher/artifacts/${encodeURIComponent(artifact.id)}">编辑、审核与导出</a>
            <small>${formatDate(artifact.updated_at || artifact.created_at)}</small>
        </article>`).join("");
    }

    function appendResponseActions(container, prompt, reply) {
        const actions = document.createElement("div");
        actions.className = "response-actions";
        const copyButton = document.createElement("button");
        copyButton.type = "button";
        copyButton.className = "quiet-btn";
        copyButton.textContent = "复制内容";
        copyButton.addEventListener("click", async () => {
            await navigator.clipboard.writeText(reply);
            copyButton.textContent = "已复制";
        });
        const saveButton = document.createElement("button");
        saveButton.type = "button";
        saveButton.className = "primary-btn";
        saveButton.textContent = role === "student" ? "保存为学习任务" : "保存为教案草稿";
        saveButton.addEventListener("click", async () => {
            saveButton.disabled = true;
            saveButton.textContent = "正在保存…";
            try {
                if (role === "student") {
                    const payload = await postJSON("/api/student/tasks", {
                        topic: state.activeTopic,
                        title: `${state.activeTopic}学习任务`,
                        prompt,
                        assistant_reply: reply,
                    });
                    state.taskRecords.unshift(payload.task);
                    updateProgress(payload.progress);
                    renderTaskRecords();
                } else {
                    const skill = state.skills.find((item) => item.key === state.selectedSkill);
                    const payload = await postJSON("/api/teacher/artifacts", {
                        title: `${state.activeTopic} · ${skill?.label || "教案"}`,
                        skill_key: state.selectedSkill,
                        prompt,
                        content: reply,
                    });
                    state.artifacts.unshift(payload.artifact);
                    renderArtifacts();
                }
                saveButton.textContent = "已保存";
            } catch (error) {
                saveButton.disabled = false;
                saveButton.textContent = error.message || "保存失败，请重试";
            }
        });
        actions.append(copyButton, saveButton);
        container.appendChild(actions);
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
            appendResponseActions(loadingBubble, text, payload.reply);
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
        state.activeTopic = trigger.dataset.topic || trigger.textContent.trim() || "自主探索";
        composerInput.value = trigger.dataset.prompt || "";
        updateCharacterCount();
        document.querySelector(".assistant-workbench")?.scrollIntoView({ behavior: "smooth", block: "start" });
        window.setTimeout(() => composerInput.focus(), 350);
    });
    studentTaskList?.addEventListener("click", (event) => {
        const openButton = event.target.closest("[data-complete-task]");
        if (openButton) {
            const form = studentTaskList.querySelector(`[data-reflection-form="${CSS.escape(openButton.dataset.completeTask)}"]`);
            openButton.hidden = true;
            form.hidden = false;
            form.querySelector("textarea")?.focus();
            return;
        }
        const cancelButton = event.target.closest("[data-cancel-reflection]");
        if (cancelButton) {
            const form = cancelButton.closest(".reflection-form");
            form.hidden = true;
            form.previousElementSibling.hidden = false;
        }
    });
    studentTaskList?.addEventListener("submit", async (event) => {
        const form = event.target.closest("[data-reflection-form]");
        if (!form) return;
        event.preventDefault();
        const submitButton = form.querySelector('button[type="submit"]');
        const reflection = form.querySelector("textarea").value.trim();
        if (reflection.length < 2) return;
        submitButton.disabled = true;
        try {
            const payload = await postJSON(`/api/student/tasks/${encodeURIComponent(form.dataset.reflectionForm)}/complete`, { reflection });
            state.taskRecords = state.taskRecords.map((task) => task.id === payload.task.id ? payload.task : task);
            updateProgress(payload.progress);
            renderTaskRecords();
        } catch (error) {
            submitButton.disabled = false;
            submitButton.textContent = error.message || "保存失败，请重试";
        }
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
    updateProgress(state.progress);
    renderTaskRecords();
    renderArtifacts();
})();
