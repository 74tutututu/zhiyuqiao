(function () {
    const boot = window.__ZHIYUQIAO__ || {};
    const skills = boot.skills || [];
    const role = boot.role || "teacher";
    const skillKeys = skills.map((item) => item.key).filter(Boolean);
    const userId = typeof boot.user?.user_id === "string" ? boot.user.user_id.trim() : "";
    let browserStorage = null;
    if (userId) {
        try {
            browserStorage = window.localStorage;
        } catch (_) {
            browserStorage = null;
        }
    }
    const historyStore = window.ZhiYuQiaoChatHistory.createHistoryStore({
        storage: browserStorage,
        storageKey: `zhiyuqiao:chat-history:v1:${role}:${userId}`,
        skillKeys,
    });
    const selectionStorageKey = `zhiyuqiao:chat-selection:v1:${role}:${userId}`;
    let initialSkill = skills[0]?.key || "teacher_advisor";
    try {
        const savedSkill = browserStorage?.getItem(selectionStorageKey);
        if (skillKeys.includes(savedSkill)) initialSkill = savedSkill;
    } catch (_) { /* Keep the default if storage is unavailable. */ }
    const assistantController = window.ZhiYuQiaoAssistantState.createAssistantStateController({
        historyStore,
        selectedSkill: initialSkill,
        topic: skills.find((item) => item.key === initialSkill)?.label || "",
        skillKeys,
    });

    // UI strings come from core/i18n.py via the page bootstrap. The second argument is
    // the Chinese fallback, so this file still reads correctly if i18n is ever absent.
    const i18n = boot.i18n || {};
    const locale = boot.locale || "zh-CN";
    function t(key, fallback, values) {
        const text = i18n[key] || fallback;
        if (!values) return text;
        return text.replace(/\{(\w+)\}/g, (match, name) => (name in values ? String(values[name]) : match));
    }

    const state = {
        skills,
        selectedSkill: assistantController.snapshot().selectedSkill,
        activeTopic: t("js.topic.default", "自主探索"),
        loading: false,
        abortController: null,
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
    const responseLanguage = document.getElementById("response-language");
    const languageStorageKey = `zhiyuqiao:reply-language:v1:${role}:${userId}`;
    if (responseLanguage) {
        try {
            const saved = browserStorage?.getItem(languageStorageKey);
            if (Array.from(responseLanguage.options).some((option) => option.value === saved)) {
                responseLanguage.value = saved;
            }
        } catch (_) { /* Default to matching the question if storage is unavailable. */ }
        responseLanguage.addEventListener("change", () => {
            try { browserStorage?.setItem(languageStorageKey, responseLanguage.value); } catch (_) { /* Still usable in memory. */ }
        });
    }
    const studentTaskList = document.getElementById("student-task-list");
    const teacherArtifactList = document.getElementById("teacher-artifact-list");

    function currentHistory() {
        return assistantController.snapshot().history;
    }

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
        if (!chatMessages || currentHistory().length) return;
        const copy = role === "student"
            ? [t("js.empty.student.title", "从一个问题开始"), t("js.empty.student.body", "你可以用中文或熟悉的语言提问，我会按你的水平解释。")]
            : [t("js.empty.teacher.title", "把教学情境说具体一点"), t("js.empty.teacher.body", "学习者水平、课堂时长、文化主题和预期产出越清楚，建议越可用。")];
        chatMessages.innerHTML = `<div class="chat-empty"><div><strong>${copy[0]}</strong><span>${copy[1]}</span></div></div>`;
    }

    async function postJSON(url, body) {
        const response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRF-Token": boot.csrfToken || "" },
            body: JSON.stringify(body),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || t("js.error.generic", "操作失败"));
        return payload;
    }

    function formatDate(value) {
        if (!value) return t("js.date.just_saved", "刚刚保存");
        const date = new Date(value);
        return Number.isNaN(date.getTime())
            ? t("js.date.saved", "已保存")
            : new Intl.DateTimeFormat(locale, { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
    }

    function updateProgress(progress) {
        state.progress = progress || state.progress;
        const fill = document.getElementById("progress-fill");
        const track = document.getElementById("progress-track");
        const copy = document.getElementById("progress-copy");
        if (fill) fill.style.width = `${state.progress.percent || 0}%`;
        if (track) track.setAttribute("aria-valuenow", String(state.progress.percent || 0));
        if (copy) {
            copy.textContent = t("js.progress", "已完成 {completed} / {total} 条文化线索", {
                completed: state.progress.completed || 0,
                total: state.progress.total || 6,
            });
        }
    }

    function renderTaskRecords() {
        if (!studentTaskList) return;
        if (!state.taskRecords.length) {
            studentTaskList.innerHTML = `<div class="record-empty"><strong>${escapeHtml(t("js.tasks.empty_title", "还没有学习记录"))}</strong><span>${escapeHtml(t("js.tasks.empty_body", "完成一次 AI 对话后，点击“保存为学习任务”。"))}</span></div>`;
            return;
        }
        studentTaskList.innerHTML = state.taskRecords.map((task) => {
            const done = task.status === "completed";
            return `<article class="record-card ${done ? "completed" : ""}">
                <div class="record-card-head"><span>${escapeHtml(task.topic)}</span><em>${escapeHtml(done ? t("js.status.completed", "已完成") : t("js.status.in_progress", "进行中"))}</em></div>
                <h3>${escapeHtml(task.title)}</h3>
                <p>${escapeHtml(task.prompt)}</p>
                ${done ? `<blockquote><b>${escapeHtml(t("js.tasks.reflection_label", "我的收获"))}</b>${escapeHtml(task.reflection || t("js.status.completed", "已完成"))}</blockquote>` : `<button class="secondary-btn record-action" type="button" data-complete-task="${escapeHtml(task.id)}">${escapeHtml(t("js.tasks.complete", "完成任务并写反思"))}</button>
                <form class="reflection-form" data-reflection-form="${escapeHtml(task.id)}" hidden><label for="reflection-${escapeHtml(task.id)}">${escapeHtml(t("js.tasks.reflection_prompt", "我完成了什么、学会了什么？"))}</label><textarea id="reflection-${escapeHtml(task.id)}" maxlength="2000" required></textarea><div><button class="quiet-btn" type="button" data-cancel-reflection>${escapeHtml(t("js.cancel", "取消"))}</button><button class="primary-btn" type="submit">${escapeHtml(t("js.tasks.reflection_save", "保存完成记录"))}</button></div></form>`}
                <small>${formatDate(task.completed_at || task.created_at)}</small>
            </article>`;
        }).join("");
    }

    function renderArtifacts() {
        if (!teacherArtifactList) return;
        if (!state.artifacts.length) {
            teacherArtifactList.innerHTML = `<div class="record-empty"><strong>${escapeHtml(t("js.artifacts.empty_title", "还没有教案草稿"))}</strong><span>${escapeHtml(t("js.artifacts.empty_body", "生成教学方案后，点击“保存为教案草稿”。"))}</span></div>`;
            return;
        }
        teacherArtifactList.innerHTML = state.artifacts.map((artifact) => `<article class="record-card">
            <div class="record-card-head"><span>${escapeHtml(artifact.skill_key)}</span><em class="${artifact.review_status === "reviewed" ? "reviewed" : ""}">${escapeHtml(artifact.review_status === "reviewed" ? t("js.artifacts.reviewed", "教师已审核") : t("js.artifacts.pending", "待审核"))}</em></div>
            <h3>${escapeHtml(artifact.title)}</h3><p>${escapeHtml(artifact.prompt)}</p>
            <a class="secondary-btn record-action" href="/teacher/artifacts/${encodeURIComponent(artifact.id)}">${escapeHtml(t("js.artifacts.open", "编辑、审核与导出"))}</a>
            <small>${formatDate(artifact.updated_at || artifact.created_at)}</small>
        </article>`).join("");
    }

    function appendResponseActions(container, prompt, reply) {
        const actions = document.createElement("div");
        actions.className = "response-actions";
        const copyButton = document.createElement("button");
        copyButton.type = "button";
        copyButton.className = "quiet-btn";
        copyButton.textContent = t("js.copy", "复制内容");
        copyButton.addEventListener("click", async () => {
            try {
                await navigator.clipboard.writeText(reply);
                copyButton.textContent = t("js.copied", "已复制");
            } catch (_) {
                copyButton.textContent = t("js.copy_failed", "复制失败，请手动选择");
            }
        });
        const saveButton = document.createElement("button");
        saveButton.type = "button";
        saveButton.className = "primary-btn";
        saveButton.textContent = role === "student" ? t("js.save.task", "保存为学习任务") : t("js.save.artifact", "保存为教案草稿");
        saveButton.addEventListener("click", async () => {
            saveButton.disabled = true;
            saveButton.textContent = t("js.save.saving", "正在保存…");
            try {
                if (role === "student") {
                    const payload = await postJSON("/api/student/tasks", {
                        topic: state.activeTopic,
                        title: t("js.task.title", "{topic}学习任务", { topic: state.activeTopic }),
                        prompt,
                        assistant_reply: reply,
                    });
                    state.taskRecords.unshift(payload.task);
                    updateProgress(payload.progress);
                    renderTaskRecords();
                } else {
                    const skill = state.skills.find((item) => item.key === state.selectedSkill);
                    const payload = await postJSON("/api/teacher/artifacts", {
                        title: `${state.activeTopic} · ${skill?.label || t("js.artifacts.fallback_title", "教案")}`,
                        skill_key: state.selectedSkill,
                        prompt,
                        content: reply,
                    });
                    state.artifacts.unshift(payload.artifact);
                    renderArtifacts();
                }
                saveButton.textContent = t("js.save.saved", "已保存");
            } catch (error) {
                saveButton.disabled = false;
                saveButton.textContent = error.message || t("js.save.failed", "保存失败，请重试");
            }
        });
        actions.append(copyButton, saveButton);
        container.appendChild(actions);
    }

    function appendSources(container, sources) {
        if (!container || !Array.isArray(sources) || !sources.length) return;
        const section = document.createElement("section");
        section.className = "answer-sources";
        const sourcesHeading = t("js.sources.heading", "回答依据");
        section.setAttribute("aria-label", sourcesHeading);
        const heading = document.createElement("h4");
        heading.textContent = sourcesHeading;
        section.appendChild(heading);
        const list = document.createElement("div");
        list.className = "source-card-list";
        sources.forEach((source) => {
            const card = document.createElement("a");
            card.className = "source-card";
            const sourceUrl = /^https?:\/\//i.test(source.source_url || "") ? source.source_url : "";
            card.href = sourceUrl || "#";
            if (sourceUrl) {
                card.target = "_blank";
                card.rel = "noopener noreferrer";
            }
            const meta = [source.source_org, source.published_date].filter(Boolean).join(" · ");
            const status = source.dynamic ? t("js.sources.dynamic", "动态信息 · 使用前复核") : t("js.sources.verified", "公开资料 · 已核验");
            card.innerHTML = `<span>${escapeHtml(source.topic || t("js.sources.topic_fallback", "海派文化"))}</span><strong>${escapeHtml(source.title || source.source || t("js.sources.title_fallback", "来源资料"))}</strong><small>${escapeHtml(meta)}</small><em>${escapeHtml(status)} ↗</em>`;
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
        const snapshot = assistantController.snapshot();
        state.selectedSkill = snapshot.selectedSkill;
        try {
            browserStorage?.setItem(selectionStorageKey, state.selectedSkill);
        } catch (_) { /* The in-memory conversation remains usable. */ }
        if (typeof snapshot.topic === "string" && snapshot.topic) state.activeTopic = snapshot.topic;
        currentSkillTitle.textContent = skill.label;
        currentSkillDescription.textContent = skill.description;
        document.querySelectorAll(".skill-item").forEach((button) => {
            const active = button.dataset.skillKey === skill.key;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", String(active));
        });
        renderStarterPrompts(skill);
        renderHistory();
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
            bubble.innerHTML = `<p>${escapeHtml(t("js.loading", "正在组织答案，请稍等……"))}</p>`;
        }
        wrapper.appendChild(bubble);
        chatMessages.appendChild(wrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return bubble;
    }

    function renderHistory() {
        if (!chatMessages) return;
        const history = currentHistory();
        chatMessages.innerHTML = "";
        if (!history.length) {
            renderEmptyState();
            return;
        }
        history.forEach((message, index) => {
            const bubble = appendMessage(message.role, message.content);
            if (message.role === "assistant" && history[index - 1]?.role === "user") {
                appendSources(bubble, message.sources);
                appendResponseActions(bubble, history[index - 1].content, message.content);
            }
        });
    }

    async function sendMessage() {
        const text = composerInput.value.trim();
        if (!text || state.loading) return;
        if (!assistantController.recordUserMessage(text)) return;
        const requestPayload = assistantController.buildRequestPayload();
        const requestSkill = requestPayload.skill_key;
        state.loading = true;
        if (responseLanguage) responseLanguage.disabled = true;
        state.abortController = new AbortController();
        composerInput.value = "";
        updateCharacterCount();
        sendBtn.innerHTML = `${escapeHtml(t("js.stop", "停止生成"))} <span>■</span>`;
        sendBtn.setAttribute("aria-label", t("js.stop_aria", "停止生成回答"));
        chatMessages.setAttribute("aria-busy", "true");
        appendMessage("user", text);
        const loadingBubble = appendMessage("assistant", "", { loading: true });
        let finalReply = "";
        let finalSources = [];

        try {
            const response = await fetch("/api/message/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRF-Token": boot.csrfToken || "" },
                body: JSON.stringify({ skill_key: requestSkill, text, history: requestPayload.history, response_language: responseLanguage?.value || "auto" }),
                signal: state.abortController.signal,
            });
            if (!response.ok) {
                const payload = await response.json();
                throw new Error(payload.detail || t("js.request_failed", "请求失败"));
            }
            if (!response.body) throw new Error(t("js.no_stream", "当前浏览器不支持流式回答"));
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            while (true) {
                const { value, done } = await reader.read();
                buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
                const lines = buffer.split("\n");
                buffer = done ? "" : lines.pop();
                for (const line of lines) {
                    if (!line.trim()) continue;
                    const event = JSON.parse(line);
                    if (event.type === "error") throw new Error(event.detail || t("js.request_failed", "请求失败"));
                    if (event.content) {
                        finalReply = event.content;
                        loadingBubble.innerHTML = renderMarkdownLite(finalReply);
                    }
                    if (event.type === "done") finalSources = event.sources || [];
                }
                chatMessages.scrollTop = chatMessages.scrollHeight;
                if (done) break;
            }
            const completionFallback = "暂时无法完成，请重试。";
            finalReply = finalReply.trim() || completionFallback;
            assistantController.recordAssistantCompletion(finalReply, finalSources);
            const savedHistory = currentHistory();
            const savedMessage = savedHistory[savedHistory.length - 1];
            const savedReply = savedMessage?.role === "assistant" ? savedMessage.content : completionFallback;
            loadingBubble.innerHTML = renderMarkdownLite(savedReply);
            if (savedReply !== completionFallback) appendSources(loadingBubble, finalSources);
            appendResponseActions(loadingBubble, text, savedReply);
            delete loadingBubble.dataset.loading;
            loadingBubble.removeAttribute("role");
        } catch (error) {
            if (error.name === "AbortError") {
                const stoppedLabel = finalReply
                    ? t("js.stopped_suffix", "已停止生成。")
                    : t("js.stopped", "已停止生成，你可以调整问题后重试。");
                const stopped = finalReply
                    ? `${finalReply}\n\n---\n${stoppedLabel}`
                    : stoppedLabel;
                assistantController.recordAssistantStop(finalReply, stoppedLabel);
                loadingBubble.innerHTML = renderMarkdownLite(stopped);
                if (finalReply) appendResponseActions(loadingBubble, text, finalReply);
            } else {
                const reason = error.message || t("js.unavailable", "系统不可用");
                const failedReply = t("js.failed", "暂时无法完成：{message}。请稍后重试。", { message: reason });
                assistantController.recordAssistantCompletion(failedReply);
                loadingBubble.innerHTML = `<p>${escapeHtml(failedReply)}</p>`;
            }
            delete loadingBubble.dataset.loading;
        } finally {
            state.loading = false;
            if (responseLanguage) responseLanguage.disabled = false;
            state.abortController = null;
            sendBtn.innerHTML = `${escapeHtml(t("js.send", "发送"))} <span>↗</span>`;
            sendBtn.setAttribute("aria-label", t("js.send_aria", "发送消息"));
            chatMessages.removeAttribute("aria-busy");
            composerInput.focus();
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    function clearChat() {
        if (state.loading) return;
        assistantController.clearCurrentHistory();
        renderHistory();
        composerInput.focus();
    }

    function focusConversation() {
        const workbench = document.querySelector(".assistant-workbench, .chat-shell");
        if (!workbench) return;
        const navHeight = document.querySelector(".app-topbar")?.getBoundingClientRect().height || 0;
        workbench.style.scrollMarginTop = `${Math.ceil(navHeight) + 16}px`;
        workbench.scrollIntoView({
            behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
            block: "start",
        });
        composerInput?.focus({ preventScroll: true });
    }

    skillList?.addEventListener("click", (event) => {
        const button = event.target.closest(".skill-item");
        if (button) {
            if (!assistantController.selectFromSidebar(button.dataset.skillKey, {
                loading: state.loading,
                topic: button.dataset.skillLabel || t("js.topic.default", "自主探索"),
            })) return;
            setSkill(button.dataset.skillKey);
            focusConversation();
        }
    });
    document.addEventListener("click", (event) => {
        const trigger = event.target.closest("[data-skill-target]");
        if (!trigger) return;
        if (!assistantController.selectFromShortcut(trigger.dataset.skillTarget, {
            loading: state.loading,
            topic: trigger.dataset.topic || trigger.textContent.trim() || t("js.topic.default", "自主探索"),
            prompt: trigger.dataset.prompt || "",
        })) return;
        setSkill(trigger.dataset.skillTarget);
        composerInput.value = assistantController.snapshot().inputPrefill;
        updateCharacterCount();
        focusConversation();
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
            submitButton.textContent = error.message || t("js.save.failed", "保存失败，请重试");
        }
    });
    sendBtn?.addEventListener("click", () => {
        if (state.loading) state.abortController?.abort();
        else sendMessage();
    });
    clearBtn?.addEventListener("click", clearChat);
    composerInput?.addEventListener("input", updateCharacterCount);
    composerInput?.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
            event.preventDefault();
            if (!state.loading) sendMessage();
        }
    });

    setSkill(state.selectedSkill);
    updateCharacterCount();
    renderEmptyState();
    updateProgress(state.progress);
    renderTaskRecords();
    renderArtifacts();
})();
