# 按学习工具隔离并持久化对话记录实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 让每个左侧学习工具独立显示、保存和恢复自己的对话记录，刷新页面后仍可恢复。

**架构：** 新增浏览器端的纯历史仓储模块，负责按工具键加载、校验、裁剪和持久化消息。`assistant.js` 只保存当前工具键并通过该模块读取/写入记录；所有工具切换入口共用生成中禁用的切换守卫。历史按账号和角色隔离在 `localStorage`，每个工具最多保存 20 条成对消息。

**技术栈：** 原生 JavaScript、浏览器 `localStorage`、Node.js 内置 `assert`、FastAPI/Jinja 模板。

---

## 文件结构

- 创建：`static/chat_history.js`：纯历史仓储模块；用条件 UMD 导出，在浏览器暴露 `window.ZhiYuQiaoChatHistory`，在 Node.js 暴露 `module.exports`。
- 创建：`static/assistant_state.js`：纯控制器模块，集中构造受 20 条上限约束的请求历史、处理停止生成记录，并提供两个可测试的工具切换入口。
- 创建：`test_chat_history_storage.js`：以真实仓储模块验证工具隔离、持久化、校验与问答对裁剪。
- 创建：`test_assistant_state.js`：以真实控制器验证 API 请求长度、停止生成和两个切换入口的生成中守卫。
- 修改：`static/assistant.js`：调用控制器读写当前工具记录，按控制器结果渲染界面。
- 修改：`templates/student_dashboard.html`、`templates/teacher_dashboard.html`、`templates/assistant.html`：在 `assistant.js` 前加载两个模块。

### 任务 1：建立工具历史仓储和失败测试

**文件：**

- 创建：`test_chat_history_storage.js`
- 创建：`static/chat_history.js`

- [ ] **步骤 1：编写失败的测试**

```js
const assert = require("node:assert/strict");
const { createHistoryStore } = require("./static/chat_history.js");

const storage = new Map();
const store = createHistoryStore({
  storage: { getItem: (key) => storage.get(key) || null, setItem: (key, value) => storage.set(key, value) },
  storageKey: "zhiyuqiao:chat-history:v1:student:user-1",
  skillKeys: ["culture_explorer", "speaking_partner"],
});

store.appendTurn("culture_explorer", "你好", "你好！");
store.appendTurn("speaking_partner", "练习口语", "我们开始吧。");
assert.deepEqual(store.getHistory("culture_explorer"), [
  { role: "user", content: "你好" },
  { role: "assistant", content: "你好！" },
]);
assert.deepEqual(store.getHistory("speaking_partner"), [
  { role: "user", content: "练习口语" },
  { role: "assistant", content: "我们开始吧。" },
]);
```

- [ ] **步骤 2：运行测试验证失败**

运行：`node test_chat_history_storage.js`

预期：失败，提示无法加载 `./static/chat_history.js`。

- [ ] **步骤 3：编写最少实现代码**

在 `static/chat_history.js` 中实现条件 UMD 暴露，禁止无条件引用 `window` 或 `module`：

```js
const MAX_HISTORY_MESSAGES = 20;

function createHistoryStore({ storage, storageKey, skillKeys }) {
  // 加载有效的、按 user/assistant 成对排列的记录；
  // appendTurn 在追加前移除最早的完整问答对，确保每个工具最多 20 条。
  // persist 只写入当前允许的 skillKeys。
}

const api = { createHistoryStore, MAX_HISTORY_MESSAGES };
if (typeof module !== "undefined" && module.exports) module.exports = api;
if (typeof window !== "undefined") window.ZhiYuQiaoChatHistory = api;
```

模块必须：

- 忽略未知工具、无效角色、空白内容、超过 12,000 字符的内容和损坏 JSON。
- 仅保留消息数不超过 20 的完整 `user → assistant` 对。
- 支持清空单个工具，且不影响其他工具。
- 将停止生成视为正常助手消息，因此可由 `appendTurn` 持久化。

- [ ] **步骤 4：运行测试验证通过**

运行：`node test_chat_history_storage.js`

预期：通过并输出 `chat history storage checks passed`。

- [ ] **步骤 5：扩展边界测试并再次验证**

在同一测试文件补充：第 11 个问答对淘汰最早问答对；序列化后新建仓储能恢复；异常 JSON 被忽略；清空一个工具不影响另一个工具。运行：`node test_chat_history_storage.js`。预期：通过。

- [ ] **步骤 6：提交**

```bash
git add static/chat_history.js test_chat_history_storage.js
git commit -m "feat(会话): 新增工具级历史仓储"
```

### 任务 2：建立可测试的聊天状态控制器

**文件：**

- 创建：`static/assistant_state.js`
- 创建：`test_assistant_state.js`

- [ ] **步骤 1：编写失败的控制器测试**

在 `test_assistant_state.js` 中调用尚未实现的 `createAssistantStateController()`：

```js
const { createAssistantStateController } = require("./static/assistant_state.js");

const controller = createAssistantStateController({ historyStore: store, selectedSkill: "culture_explorer" });
controller.recordUserMessage("第 11 个问题");
const payload = controller.buildRequestPayload();
assert.ok(payload.history.length <= 20);

const before = controller.snapshot();
assert.equal(controller.selectFromSidebar("speaking_partner", { loading: true }), false);
assert.deepEqual(controller.snapshot(), before);
assert.equal(controller.selectFromShortcut("speaking_partner", { loading: true, topic: "口语" }), false);
assert.deepEqual(controller.snapshot(), before);
```

运行：`node test_assistant_state.js`。

预期：失败，提示无法加载 `./static/assistant_state.js`。

- [ ] **步骤 2：实现最小控制器与 UMD 边界**

在 `static/assistant_state.js` 使用与仓储模块相同的 `typeof module` / `typeof window` 条件 UMD 写法。控制器必须提供：

- `selectFromSidebar(skillKey, { loading, topic })` 与 `selectFromShortcut(skillKey, { loading, topic, prompt })`，二者在 `loading` 时都返回 `false` 且不改变选中工具、主题或预填输入；非生成状态返回 `true` 并更新状态。
- `recordUserMessage(text)`：在追加前淘汰最早完整问答对，确保为助手回复预留 1 条空间。
- `buildRequestPayload()`：返回当前工具的历史，永远不超过 20 条。
- `recordAssistantCompletion(reply)` 与 `recordAssistantStop(partialReply, stoppedLabel)`：始终完成本轮问答对，停止时保存部分内容加停止标记，或保存停止提示。
- `clearCurrentHistory()` 与 `snapshot()`。

- [ ] **步骤 3：运行控制器测试验证通过**

运行：`node test_assistant_state.js`。

预期：通过，并断言第 11 个问答对的请求负载为 20 条或更少，且两种 `loading=true` 的入口均不改变快照。

- [ ] **步骤 4：扩展停止和刷新恢复测试**

在 `test_assistant_state.js` 断言：停止后当前工具保存 `user → assistant` 成对记录；新建仓储和控制器后仍读取该记录；工具 A 和工具 B 的快照互不混合。运行：`node test_assistant_state.js`。预期：通过。

- [ ] **步骤 5：提交**

```bash
git add static/assistant_state.js test_assistant_state.js test_chat_history_storage.js
git commit -m "feat(会话): 新增工具级聊天状态控制器"
```

### 任务 3：让聊天界面按控制器结果切换和恢复

**文件：**

- 修改：`static/assistant.js:13-25, 282-296, 322-403, 407-427, 471-475`
- 修改：`templates/student_dashboard.html:75-76`
- 修改：`templates/teacher_dashboard.html:82-83`
- 修改：`templates/assistant.html:73-78`
- 测试：`test_assistant_state.js`

- [ ] **步骤 1：在模板中加载两个纯模块**

在 3 个模板的 `assistant.js` 脚本标签前插入：

```html
<script src="{{ url_for('static', path='/chat_history.js') }}"></script>
<script src="{{ url_for('static', path='/assistant_state.js') }}"></script>
```

- [ ] **步骤 2：在 `assistant.js` 接入控制器**

1. 用 `boot.user?.user_id`、`role` 和 `skills.map(item => item.key)` 初始化仓储；缺少 `user_id` 时传入不可写存储，使页面保持临时空记录。
2. 用仓储和当前工具创建控制器；`state.selectedSkill` 只通过控制器切换。
3. `renderHistory()` 清空消息容器后依次复用 `appendMessage()`，空数组时复用 `renderEmptyState()`；`setSkill()` 在控制器切换成功后才调用它。
4. 发送时经 `recordUserMessage()` 和 `buildRequestPayload()` 生成请求体，不能直接把数组写入 `fetch`。断言测试中的请求历史最多 20 条。
5. 正常完成和停止生成分别调用控制器完成本轮问答；随后重新渲染或追加对应气泡。
6. `clearChat()` 调用 `clearCurrentHistory()`，仅清空当前工具后重渲染。

- [ ] **步骤 3：让两条 UI 入口使用同一个生成中守卫**

左侧 `.skill-item` 处理器必须调用 `selectFromSidebar()`；`[data-skill-target]` 处理器必须调用 `selectFromShortcut()`。两者在返回 `false` 时立刻结束，不能更改标题、`activeTopic`、输入框或滚动位置。控制器测试的两个入口断言是这条守卫的回归证明。

- [ ] **步骤 4：运行测试验证通过**

运行：`node test_chat_history_storage.js`，然后运行 `node test_assistant_state.js`。

预期：通过，覆盖工具隔离、刷新恢复、20 条上限、单工具清空、停止记录与两个切换入口。

- [ ] **步骤 5：执行前端语法检查**

运行：`node --check static/chat_history.js`，`node --check static/assistant_state.js`，然后运行 `node --check static/assistant.js`。

预期：3 个命令退出码均为 0。

- [ ] **步骤 6：提交**

```bash
git add static/assistant.js templates/student_dashboard.html templates/teacher_dashboard.html templates/assistant.html
git commit -m "fix(会话): 按工具切换并恢复对话记录"
```

### 任务 4：回归验证

**文件：**

- 验证：`test_chat_history_storage.js`
- 验证：`test_assistant_state.js`
- 验证：`test_conversation_routing.py`
- 验证：`test_minimal_launch.py`

- [ ] **步骤 1：运行浏览器历史回归测试**

运行：`node test_chat_history_storage.js`，然后运行 `node test_assistant_state.js`。

预期：通过。

- [ ] **步骤 2：运行后端会话与启动回归**

运行：`python test_conversation_routing.py`，然后运行 `python test_minimal_launch.py`。

预期：两个脚本退出码均为 0。

- [ ] **步骤 3：检查变更与提交状态**

运行：`git diff --check` 和 `git status --short`。

预期：无空白错误；除视觉伴侣临时目录外，工作区无未提交的产品代码变更。
