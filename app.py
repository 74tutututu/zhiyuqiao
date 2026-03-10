import threading
import gradio as gr
from core.ai_agent import generate_response_stream

# 用于控制流式生成的取消标志
cancel_event = threading.Event()

# ===== 修复 gradio_client 1.3.0 的 API schema bug =====
import gradio_client.utils as _gc_utils

_orig_json_schema_to_python_type = _gc_utils._json_schema_to_python_type

def _patched_json_schema_to_python_type(schema, defs=None):
    if isinstance(schema, bool):
        return "Any"
    return _orig_json_schema_to_python_type(schema, defs)

_gc_utils._json_schema_to_python_type = _patched_json_schema_to_python_type
# ===== End patch =====

# ==================== 自定义主题 ====================
theme = gr.themes.Soft(
    primary_hue=gr.themes.Color(
        c50="#FFF0F0", c100="#FFD6D6", c200="#FFB3B3",
        c300="#FF8A8A", c400="#E84545", c500="#C41A1A",
        c600="#A81515", c700="#8B1010", c800="#6E0C0C",
        c900="#520808", c950="#3A0505",
    ),
    secondary_hue="stone",
    neutral_hue="stone",
    font=("Noto Sans SC", "Microsoft YaHei", "PingFang SC", "sans-serif"),
    font_mono=("JetBrains Mono", "Consolas", "monospace"),
).set(
    body_background_fill="#FFF8F0",
    body_background_fill_dark="#1A1A1A",
    block_background_fill="white",
    block_background_fill_dark="#2C2C2C",
    block_border_width="0px",
    block_shadow="0 1px 4px rgba(0,0,0,0.06)",
    button_primary_background_fill="#C41A1A",
    button_primary_background_fill_hover="#A81515",
    button_primary_text_color="white",
    input_border_color="#E5DDD5",
    input_background_fill="#FFFDF9",
    input_background_fill_dark="#333333",
)

# ==================== 自定义 CSS ====================
custom_css = """
/* ---------- 主题色 CSS 变量（红色 - 默认） ---------- */
:root, .theme-red {
    --c-primary: #C41A1A;
    --c-primary-dark: #8B1010;
    --c-primary-light: #E84545;
    --c-primary-hover: #A81515;
    --c-primary-bg: #FFF0F0;
    --c-primary-shadow: rgba(196,26,26,0.1);
    --c-body-bg: #FFF8F0;
    --c-bot-bg: #FFF8F0;
    --c-border: #F0E6DA;
    --c-border-input: #E5DDD5;
    --c-input-bg: #FFFDF9;
    --c-sidebar-text: #4A3F35;
    --c-sidebar-desc: #8B7B6B;
    --c-example-text: #6B5E52;
    --c-dropdown-bg: #FFFDF9;
    /* Gradio 内部变量覆盖 */
    --color-accent: #C41A1A !important;
    --color-accent-soft: #FFD6D6 !important;
    --checkbox-label-background-fill: transparent !important;
    --checkbox-label-background-fill-selected: #C41A1A !important;
    --checkbox-label-border-color: #E5DDD5 !important;
    --checkbox-label-border-color-selected: #C41A1A !important;
    --checkbox-label-text-color-selected: white !important;
    --checkbox-background-color-selected: #C41A1A !important;
    --checkbox-border-color-selected: #C41A1A !important;
    --block-label-text-color: #C41A1A !important;
    --block-label-background-fill: #FFF0F0 !important;
}

/* ---------- 蓝色主题 ---------- */
.theme-blue {
    --c-primary: #1A6FC4;
    --c-primary-dark: #0E4A8B;
    --c-primary-light: #4595E8;
    --c-primary-hover: #155AA8;
    --c-primary-bg: #EFF6FF;
    --c-primary-shadow: rgba(26,111,196,0.1);
    --c-body-bg: #F5F8FF;
    --c-bot-bg: #F0F6FF;
    --c-border: #D6E4F0;
    --c-border-input: #D0DDEA;
    --c-input-bg: #FAFCFF;
    --c-sidebar-text: #354A5E;
    --c-sidebar-desc: #6B7F8B;
    --c-example-text: #52636B;
    --c-dropdown-bg: #FAFCFF;
    /* Gradio 内部变量覆盖 */
    --color-accent: #1A6FC4 !important;
    --color-accent-soft: #D6E4F0 !important;
    --checkbox-label-background-fill: transparent !important;
    --checkbox-label-background-fill-selected: #1A6FC4 !important;
    --checkbox-label-border-color: #D0DDEA !important;
    --checkbox-label-border-color-selected: #1A6FC4 !important;
    --checkbox-label-text-color-selected: white !important;
    --checkbox-background-color-selected: #1A6FC4 !important;
    --checkbox-border-color-selected: #1A6FC4 !important;
    --block-label-text-color: #1A6FC4 !important;
    --block-label-background-fill: #EFF6FF !important;
}

/* ---------- 品牌栏 ---------- */
.brand-header {
    background: linear-gradient(135deg, var(--c-primary) 0%, var(--c-primary-dark) 100%);
    padding: 20px 28px;
    border-radius: 12px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 18px;
    transition: background 0.4s;
}
.brand-header img {
    width: 56px; height: 56px;
    border-radius: 12px;
    background: white;
    padding: 5px;
}
.brand-title {
    color: white; font-size: 26px; font-weight: 700;
    margin: 0; letter-spacing: 2px;
}
.brand-subtitle {
    color: rgba(255,255,255,0.85); font-size: 13px;
    margin: 3px 0 0 0;
}

/* ---------- 侧边栏 ---------- */
.sidebar {
    background: white !important;
    border: 1px solid var(--c-border) !important;
    border-radius: 12px !important;
    padding: 8px !important;
    transition: border-color 0.4s;
}
.sidebar-title {
    color: #2C2C2C; font-size: 14px; font-weight: 600;
    margin: 8px 0 4px 4px; padding: 0;
}
.sidebar-desc {
    color: var(--c-sidebar-desc); font-size: 12px;
    margin: 0 0 6px 4px;
}
.sidebar .nav-btn {
    border: 1.5px solid var(--c-border) !important;
    border-radius: 10px !important;
    background: var(--c-input-bg) !important;
    color: var(--c-sidebar-text) !important;
    font-size: 13px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 10px 14px !important;
    margin-bottom: 4px !important;
    transition: all 0.2s;
}
.sidebar .nav-btn:hover {
    border-color: var(--c-primary) !important;
    color: var(--c-primary) !important;
    background: var(--c-primary-bg) !important;
}

/* ---------- 聊天区域 ---------- */
#chatbot {
    border: 1px solid var(--c-border) !important;
    border-radius: 12px !important;
    background: white !important;
    min-height: 460px;
    transition: border-color 0.4s;
}
#chatbot .message {
    border-radius: 12px !important;
    font-size: 15px !important;
    line-height: 1.7 !important;
}
#chatbot .bot {
    background: var(--c-bot-bg) !important;
    border: 1px solid var(--c-border) !important;
    transition: background 0.4s, border-color 0.4s;
}
#chatbot .user {
    background: linear-gradient(135deg, var(--c-primary), var(--c-primary-light)) !important;
    color: white !important;
    transition: background 0.4s;
}

/* ---------- 输入区 ---------- */
.input-row textarea {
    border-radius: 10px !important;
    border: 1.5px solid var(--c-border-input) !important;
    font-size: 15px !important;
    transition: border-color 0.2s;
}
.input-row textarea:focus {
    border-color: var(--c-primary) !important;
    box-shadow: 0 0 0 2px var(--c-primary-shadow) !important;
}
.send-btn {
    border-radius: 10px !important;
    min-width: 72px !important;
    height: 46px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    background: var(--c-primary) !important;
    transition: background 0.3s;
}
.send-btn:hover {
    background: var(--c-primary-hover) !important;
}
.action-btn {
    border-radius: 10px !important;
    border: 1.5px solid var(--c-border-input) !important;
    color: var(--c-sidebar-desc) !important;
    background: transparent !important;
    min-width: 46px !important;
    height: 46px !important;
}
.action-btn:hover {
    border-color: var(--c-primary) !important;
    color: var(--c-primary) !important;
}

/* ---------- 示例按钮 ---------- */
.example-btn {
    border: 1.5px solid var(--c-border-input) !important;
    border-radius: 20px !important;
    padding: 8px 16px !important;
    font-size: 12.5px !important;
    color: var(--c-example-text) !important;
    background: var(--c-input-bg) !important;
    transition: all 0.2s;
}
.example-btn:hover {
    border-color: var(--c-primary) !important;
    color: var(--c-primary) !important;
    background: var(--c-primary-bg) !important;
}

/* ---------- Gradio 按钮主色覆盖 ---------- */
.primary {
    background: var(--c-primary) !important;
    border-color: var(--c-primary) !important;
}
.primary:hover {
    background: var(--c-primary-hover) !important;
    border-color: var(--c-primary-hover) !important;
}

/* ---------- Radio / Dropdown 主题色覆盖 ---------- */
.sidebar input[type="radio"]:checked + label,
.sidebar .wrap label.selected {
    background: var(--c-primary) !important;
    border-color: var(--c-primary) !important;
    color: white !important;
}
.sidebar input[type="radio"]:checked {
    accent-color: var(--c-primary) !important;
}
.sidebar .wrap label:hover {
    border-color: var(--c-primary) !important;
    color: var(--c-primary) !important;
}
/* Gradio Radio 选中态内圈 - 覆盖所有可能的圆点选择器 */
.sidebar label.selected span,
.sidebar label.selected .inner {
    background: var(--c-primary) !important;
}
label.selected > span:first-child > span {
    background-color: var(--c-primary) !important;
}
label.selected > span:first-child {
    border-color: var(--c-primary) !important;
}
.radio-group label.selected span.inner-circle,
label.selected span[data-testid] {
    background: var(--c-primary) !important;
}
/* Dropdown 边框聚焦 */
.sidebar .wrap .wrap-inner:focus-within,
.sidebar .dropdown-container:focus-within {
    border-color: var(--c-primary) !important;
    box-shadow: 0 0 0 2px var(--c-primary-shadow) !important;
}
/* Dropdown 默认背景框与边框 */
.sidebar .dropdown-container,
.sidebar .dropdown-container > div,
.sidebar .dropdown-container input,
.sidebar .wrap-inner {
    background: var(--c-dropdown-bg) !important;
    border-color: var(--c-border-input) !important;
    transition: background 0.4s, border-color 0.4s;
}
/* Dropdown label 颜色 */
.sidebar .dropdown-container label,
.sidebar span.svelte-1gfkn6j,
.sidebar label.svelte-1b6s6s {
    color: var(--c-primary) !important;
    transition: color 0.4s;
}

/* ---------- body 背景过渡 ---------- */
gradio-app {
    background: var(--c-body-bg) !important;
    transition: background 0.4s;
}

/* ---------- 底部 ---------- */
.footer-text {
    text-align: center; color: #A89888;
    font-size: 12px; margin-top: 6px; padding: 6px;
}

/* ---------- 主题切换器样式 ---------- */
.theme-switcher {
    display: flex; gap: 8px; margin: 4px 4px 8px 4px;
}
.theme-dot {
    width: 28px; height: 28px; border-radius: 50%;
    border: 2.5px solid #E5DDD5; cursor: pointer;
    transition: all 0.2s; position: relative;
}
.theme-dot:hover { transform: scale(1.1); }
.theme-dot.active { border-color: #2C2C2C; box-shadow: 0 0 0 2px rgba(0,0,0,0.15); }
.theme-dot.dot-red { background: linear-gradient(135deg, #C41A1A, #E84545); }
.theme-dot.dot-blue { background: linear-gradient(135deg, #1A6FC4, #4595E8); }

/* ---------- 移动端适配 ---------- */
@media (max-width: 768px) {
    .brand-header { padding: 14px 16px; gap: 12px; }
    .brand-header img { width: 40px; height: 40px; }
    .brand-title { font-size: 20px; }
    .brand-subtitle { font-size: 11px; }
    #chatbot { min-height: 350px; }
    .sidebar { display: none !important; }
}
"""

# ==================== HTML 片段 ====================
BRAND_HTML = """
<div class="brand-header">
    <img src="/file=assets/logo.svg" alt="智语桥">
    <div>
        <p class="brand-title">智语桥</p>
        <p class="brand-subtitle">国际中文教育 AI 助手 · International Chinese Education AI Assistant</p>
    </div>
</div>
"""

FOOTER_HTML = """
<div class="footer-text">
    ⚠️ 本内容由 AI 生成，涉及具体教学决策或政策解读时，请结合实际教学环境及官方最新文件进行核实。<br>
    © 2026 智语桥 ZhiYuQiao — Powered by DeepSeek
</div>
"""

# ==================== 示例问题 ====================
EXAMPLE_QUESTIONS = [
    "HSK4 阅读理解有什么备考策略？",
    "如何为零基础留学生设计第一堂中文课？",
    "有哪些适合中文教学的免费数字化工具？",
    "请帮我制定一份 HSK3 级词汇教学方案",
]

HSK_LEVELS = ["不限", "HSK 1", "HSK 2", "HSK 3", "HSK 4", "HSK 5", "HSK 6"]

# ==================== 核心逻辑 ====================
def user_submit(message, history, hsk_level):
    """用户发送消息：追加到历史并清空输入框"""
    if not message or not message.strip():
        return "", history
    history = history + [[message.strip(), None]]
    return "", history


def bot_respond(history, hsk_level):
    """Bot 流式生成回复"""
    cancel_event.clear()  # 每次开始生成前重置取消标志
    if not history or history[-1][1] is not None:
        yield history
        return
    user_msg = history[-1][0]
    # 传入历史（不含当前未回复的最后一轮）
    prev_history = history[:-1] if len(history) > 1 else None
    for partial in generate_response_stream(user_msg, history=prev_history, hsk_level=hsk_level, cancel_event=cancel_event):
        history[-1][1] = partial
        yield history


def use_example(example_text, history, hsk_level):
    """点击示例：追加到历史"""
    if not example_text:
        return "", history
    history = history + [[example_text, None]]
    return "", history


def export_chat(history):
    """导出聊天记录为 Markdown 文本"""
    if not history:
        return "暂无对话记录可导出。"
    lines = ["# 智语桥对话记录\n"]
    for i, (user_msg, bot_msg) in enumerate(history, 1):
        lines.append(f"## 第 {i} 轮\n")
        lines.append(f"**🧑 用户：**\n{user_msg}\n")
        if bot_msg:
            lines.append(f"**🤖 智语桥：**\n{bot_msg}\n")
        lines.append("---\n")
    return "\n".join(lines)


def clear_chat():
    """清空对话"""
    return [], None


def stop_generation():
    """终止 AI 生成"""
    cancel_event.set()


# ==================== 主题切换 JS ====================
THEME_HEAD = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    document.documentElement.classList.add('theme-red');
});
</script>
"""

SWITCH_THEME_JS = """
function(choice) {
    var isBlue = (choice === '🔵 学院蓝');
    var t = isBlue ? 'blue' : 'red';
    document.documentElement.className = '';
    document.documentElement.classList.add('theme-' + t);

    // 强制覆盖 Gradio 内联样式变量
    var vars = {
        red: {
            '--color-accent': '#C41A1A',
            '--color-accent-soft': '#FFD6D6',
            '--checkbox-label-background-fill': 'transparent',
            '--checkbox-label-background-fill-selected': '#C41A1A',
            '--checkbox-label-border-color': '#E5DDD5',
            '--checkbox-label-border-color-selected': '#C41A1A',
            '--checkbox-label-text-color-selected': 'white',
            '--block-label-text-color': '#C41A1A',
            '--button-primary-background-fill': '#C41A1A',
            '--button-primary-background-fill-hover': '#A81515',
            '--input-border-color-focus': '#C41A1A',
            '--input-border-color': '#E5DDD5',
            '--input-background-fill': '#FFFDF9',
            '--block-label-background-fill': '#FFF0F0',
            '--checkbox-background-color-selected': '#C41A1A',
            '--checkbox-border-color-selected': '#C41A1A',
        },
        blue: {
            '--color-accent': '#1A6FC4',
            '--color-accent-soft': '#D6E4F0',
            '--checkbox-label-background-fill': 'transparent',
            '--checkbox-label-background-fill-selected': '#1A6FC4',
            '--checkbox-label-border-color': '#D0DDEA',
            '--checkbox-label-border-color-selected': '#1A6FC4',
            '--checkbox-label-text-color-selected': 'white',
            '--block-label-text-color': '#1A6FC4',
            '--button-primary-background-fill': '#1A6FC4',
            '--button-primary-background-fill-hover': '#155AA8',
            '--input-border-color-focus': '#1A6FC4',
            '--input-border-color': '#D0DDEA',
            '--input-background-fill': '#FAFCFF',
            '--block-label-background-fill': '#EFF6FF',
            '--checkbox-background-color-selected': '#1A6FC4',
            '--checkbox-border-color-selected': '#1A6FC4',
        }
    };
    var ga = document.querySelector('gradio-app');
    if (ga) {
        var v = vars[t];
        for (var k in v) { ga.style.setProperty(k, v[k]); }
    }
    return choice;
}
"""

# ==================== 构建界面 ====================
with gr.Blocks(
    theme=theme,
    css=custom_css,
    title="智语桥 - 国际中文教育 AI 助手",
    head=THEME_HEAD,
) as demo:

    # ===== 顶部品牌栏 =====
    gr.HTML(BRAND_HTML)

    with gr.Row():
        # ===== 左侧边栏 =====
        with gr.Column(scale=1, min_width=200, elem_classes=["sidebar"]):
            gr.HTML('<p class="sidebar-title">📚 快捷功能</p>')
            gr.HTML('<p class="sidebar-desc">选择场景快速提问</p>')

            nav_teaching = gr.Button("🎓 教学设计咨询", elem_classes=["nav-btn"])
            nav_hsk = gr.Button("📝 HSK 备考指导", elem_classes=["nav-btn"])
            nav_tools = gr.Button("🛠️ 数字化工具推荐", elem_classes=["nav-btn"])
            nav_policy = gr.Button("📋 政策法规解读", elem_classes=["nav-btn"])

            gr.HTML('<p class="sidebar-title" style="margin-top:16px;">🎨 主题色</p>')
            theme_radio = gr.Radio(
                choices=["🔴 中国红", "🔵 学院蓝"],
                value="🔴 中国红",
                label="",
                interactive=True,
                container=False,
            )

            gr.HTML('<p class="sidebar-title" style="margin-top:12px;">⚙️ 设置</p>')
            hsk_dropdown = gr.Dropdown(
                choices=HSK_LEVELS,
                value="不限",
                label="HSK 等级",
                interactive=True,
            )

            gr.HTML('<p class="sidebar-title" style="margin-top:16px;">📥 工具</p>')
            export_btn = gr.Button("📄 导出对话记录", elem_classes=["nav-btn"])
            export_output = gr.Textbox(
                label="导出内容（可复制）",
                lines=3,
                max_lines=8,
                visible=False,
                interactive=False,
            )

        # ===== 右侧主聊天区 =====
        with gr.Column(scale=4):
            chatbot = gr.Chatbot(
                elem_id="chatbot",
                show_label=False,
                bubble_full_width=False,
                height=480,
            )

            # 示例按钮
            with gr.Row():
                example_btns = []
                for eq in EXAMPLE_QUESTIONS:
                    example_btns.append(
                        gr.Button(eq, elem_classes=["example-btn"], size="sm")
                    )

            # 输入区
            with gr.Row(elem_classes=["input-row"]):
                msg = gr.Textbox(
                    placeholder="请输入你的中文教学问题…",
                    show_label=False,
                    scale=8,
                    container=False,
                    max_lines=4,
                )
                send_btn = gr.Button("发送", variant="primary", elem_classes=["send-btn"], scale=1)
                stop_btn = gr.Button("⏹️", elem_classes=["action-btn"], scale=0)
                clear_btn = gr.Button("🗑️", elem_classes=["action-btn"], scale=0)

    # ===== 底部 =====
    gr.HTML(FOOTER_HTML)

    # ==================== 事件绑定 ====================

    # 主题切换
    theme_radio.change(
        fn=None,
        inputs=[theme_radio],
        outputs=[theme_radio],
        js=SWITCH_THEME_JS,
    )

    # 发送消息 → 流式回复
    msg.submit(
        user_submit, [msg, chatbot, hsk_dropdown], [msg, chatbot]
    ).then(
        bot_respond, [chatbot, hsk_dropdown], [chatbot]
    )
    send_btn.click(
        user_submit, [msg, chatbot, hsk_dropdown], [msg, chatbot]
    ).then(
        bot_respond, [chatbot, hsk_dropdown], [chatbot]
    )

    # 停止生成
    stop_btn.click(stop_generation, None, None)

    # 清空
    clear_btn.click(clear_chat, None, [chatbot, export_output])

    # 示例按钮
    for btn in example_btns:
        btn.click(
            use_example, [btn, chatbot, hsk_dropdown], [msg, chatbot]
        ).then(
            bot_respond, [chatbot, hsk_dropdown], [chatbot]
        )

    # 侧边栏导航 — 填充预设问题
    nav_teaching.click(
        lambda h, hsk: use_example("如何为零基础留学生设计第一堂中文课？", h, hsk),
        [chatbot, hsk_dropdown], [msg, chatbot]
    ).then(bot_respond, [chatbot, hsk_dropdown], [chatbot])

    nav_hsk.click(
        lambda h, hsk: use_example("HSK 各等级备考有什么通用策略和资源推荐？", h, hsk),
        [chatbot, hsk_dropdown], [msg, chatbot]
    ).then(bot_respond, [chatbot, hsk_dropdown], [chatbot])

    nav_tools.click(
        lambda h, hsk: use_example("有哪些适合国际中文教学的免费数字化工具？", h, hsk),
        [chatbot, hsk_dropdown], [msg, chatbot]
    ).then(bot_respond, [chatbot, hsk_dropdown], [chatbot])

    nav_policy.click(
        lambda h, hsk: use_example("最新的国际中文教育政策有哪些重要变化？", h, hsk),
        [chatbot, hsk_dropdown], [msg, chatbot]
    ).then(bot_respond, [chatbot, hsk_dropdown], [chatbot])

    # 导出
    export_btn.click(
        export_chat, [chatbot], [export_output]
    ).then(
        lambda: gr.update(visible=True), None, [export_output]
    )


if __name__ == "__main__":
    demo.launch(share=True, allowed_paths=["assets"])
