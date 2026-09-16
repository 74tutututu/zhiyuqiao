"""Interface localisation for the web workspace.

Scope note: this module localises the **interface chrome only**. The AI reply
language stays driven by the account's own ``teaching_languages`` /
``primary_language`` profile fields, which ``core/ai_agent.py`` interpolates
into the system prompt. Never route a UI locale into those prompts.

Adding a language is a data-only change: add the code to ``LANG_LABELS``,
``HTML_LANG`` and ``JS_LOCALE``, then fill in the new column in ``CATALOG``.
Missing entries fall back to Chinese, so a partial translation is safe to ship.
"""

from __future__ import annotations

import os
from typing import Any, Callable

DEFAULT_LANG = "zh"
LANG_COOKIE_NAME = "zhiyuqiao_lang"
LANG_COOKIE_TTL_DAYS = int(os.getenv("ZHIYUQIAO_LANG_TTL_DAYS", "180"))

LANG_LABELS = {
    "zh": "中文",
    "en": "English",
}

HTML_LANG = {
    "zh": "zh-CN",
    "en": "en",
}

JS_LOCALE = {
    "zh": "zh-CN",
    "en": "en-US",
}

SUPPORTED_LANGS = tuple(LANG_LABELS)


# key -> lang -> text. Chinese is the source of truth; ``en`` may be absent.
CATALOG: dict[str, dict[str, str]] = {
    # ---------------------------------------------------------------- chrome
    "nav.skip": {"zh": "跳到主要内容", "en": "Skip to main content"},
    "nav.settings": {"zh": "设置", "en": "Settings"},
    "nav.settings_aria": {"zh": "账号设置", "en": "Account settings"},
    "nav.logout": {"zh": "退出", "en": "Log out"},
    "nav.back": {"zh": "返回", "en": "Back"},
    "nav.page_aria": {"zh": "页面导航", "en": "Page navigation"},
    "nav.account_aria": {"zh": "账户导航", "en": "Account navigation"},
    "nav.teacher_aria": {"zh": "教师账户导航", "en": "Teacher account navigation"},
    "nav.student_aria": {"zh": "学生账户导航", "en": "Student account navigation"},
    "nav.language": {"zh": "Language", "en": "Language"},
    "nav.lang_aria": {"zh": "语言 / Language", "en": "Language / 语言"},
    # ----------------------------------------------------------- page titles
    "page.register": {"zh": "注册账号", "en": "Create account"},
    "page.login": {"zh": "登录", "en": "Sign in"},
    "page.teacher": {"zh": "教师工作台", "en": "Teacher workspace"},
    "page.privacy": {"zh": "隐私与 AI 使用说明", "en": "Privacy & AI notice"},
    "page.student": {"zh": "学习空间", "en": "Learning space"},
    "page.settings": {"zh": "账号设置", "en": "Account settings"},
    # ------------------------------------------------------------ workspaces
    "workspace.student": {"zh": "学生学习空间", "en": "Student learning space"},
    "workspace.student_short": {"zh": "学习空间", "en": "Learning space"},
    "workspace.teacher": {"zh": "教师工作台", "en": "Teacher workspace"},
    # --------------------------------------------------------- profile enums
    "profile.role.student": {"zh": "中文学习者", "en": "Chinese learner"},
    "profile.role.teacher": {"zh": "中文教师", "en": "Chinese teacher"},
    "profile.level.starter": {"zh": "刚开始学中文", "en": "Just starting Chinese"},
    "profile.level.hsk1": {"zh": "HSK 1", "en": "HSK 1"},
    "profile.level.hsk2": {"zh": "HSK 2", "en": "HSK 2"},
    "profile.level.hsk3": {"zh": "HSK 3", "en": "HSK 3"},
    "profile.level.hsk4": {"zh": "HSK 4", "en": "HSK 4"},
    "profile.level.hsk5": {"zh": "HSK 5", "en": "HSK 5"},
    "profile.level.hsk6": {"zh": "HSK 6", "en": "HSK 6"},
    "profile.level.advanced": {"zh": "高级学习者", "en": "Advanced learner"},
    "profile.goal.culture_explorer": {"zh": "在上海学文化", "en": "Learning culture in Shanghai"},
    "profile.goal.daily_chinese": {"zh": "日常中文交流", "en": "Everyday conversation"},
    "profile.goal.hsk_exam": {"zh": "HSK 备考", "en": "HSK exam preparation"},
    "profile.goal.speaking": {"zh": "提升口语表达", "en": "Better speaking"},
    "profile.goal.writing": {"zh": "提升中文写作", "en": "Better writing"},
    "profile.teacher_level.novice_teacher": {"zh": "新手教师", "en": "New teacher"},
    "profile.teacher_level.experienced_teacher": {"zh": "成熟教师", "en": "Experienced teacher"},
    "profile.teacher_level.researcher": {"zh": "教研人员", "en": "Teaching researcher"},
    "profile.theme.china_red": {"zh": "中国红", "en": "China Red"},
    "profile.theme.academy_blue": {"zh": "学院蓝", "en": "Academy Blue"},
    "profile.language_field.student": {"zh": "讲解语言", "en": "Explanation language"},
    "profile.language_field.teacher": {"zh": "教学语种", "en": "Teaching languages"},
    # ---------------------------------------------------------- shared forms
    "common.cancel": {"zh": "取消", "en": "Cancel"},
    "common.clear": {"zh": "清空", "en": "Clear"},
    "common.send": {"zh": "发送", "en": "Send"},
    "common.starter_aria": {"zh": "推荐问题", "en": "Suggested questions"},
    "form.username": {"zh": "登录账号", "en": "Username"},
    "form.username_placeholder": {"zh": "英文字母或数字", "en": "Letters or numbers"},
    "form.display_name": {"zh": "显示名称", "en": "Display name"},
    "form.display_name_placeholder": {"zh": "大家如何称呼你", "en": "What should people call you"},
    "form.password": {"zh": "密码", "en": "Password"},
    "form.password_placeholder_new": {"zh": "至少8个字符", "en": "At least 8 characters"},
    "form.student_level": {"zh": "当前中文水平", "en": "Current Chinese level"},
    "form.learning_goal": {"zh": "主要学习目标", "en": "Main learning goal"},
    "form.teacher_level": {"zh": "教师经验", "en": "Teaching experience"},
    "form.primary_language": {"zh": "首选讲解语言", "en": "Preferred explanation language"},
    "form.primary_language_hint": {
        "zh": "AI 会优先使用它解释；中文例句仍保留中文。",
        "en": "The AI explains in this language; Chinese examples stay in Chinese.",
    },
    "form.theme": {"zh": "界面主题", "en": "Interface theme"},
    # ----------------------------------------------------------------- login
    "auth.login.kicker": {"zh": "欢迎回来", "en": "Welcome back"},
    "auth.login.title_1": {"zh": "从一句中文，", "en": "One sentence of Chinese,"},
    "auth.login.title_2": {"zh": "走进一座城市。", "en": "and a whole city opens up."},
    "auth.login.quote": {
        "zh": "“语言是桥，真实任务让桥通向生活。”",
        "en": "“Language is the bridge; real tasks carry it into daily life.”",
    },
    "auth.login.heading": {"zh": "进入你的智语桥", "en": "Enter your Zhiyuqiao"},
    "auth.login.subheading": {
        "zh": "登录后，系统会根据你的身份进入学生学习空间或教师工作台。",
        "en": "After signing in you go to the student learning space or the teacher workspace, based on your role.",
    },
    "auth.login.identifier": {"zh": "账号或显示名称", "en": "Username or display name"},
    "auth.login.identifier_placeholder": {"zh": "请输入账号", "en": "Enter your username"},
    "auth.login.password_placeholder": {"zh": "请输入密码", "en": "Enter your password"},
    "auth.login.role_student": {"zh": "学生", "en": "Student"},
    "auth.login.role_student_items": {
        "zh": "文化探索 · 口语陪练 · 中文反馈",
        "en": "Culture exploration · Speaking practice · Chinese feedback",
    },
    "auth.login.role_teacher": {"zh": "教师", "en": "Teacher"},
    "auth.login.role_teacher_items": {
        "zh": "海派课程 · 教学设计 · 标准政策",
        "en": "Haipai lessons · Lesson design · Standards & policy",
    },
    "auth.login.footer": {"zh": "还没有账号？", "en": "No account yet?"},
    "auth.login.footer_link": {"zh": "选择身份并注册", "en": "Choose a role and sign up"},
    # -------------------------------------------------------------- register
    "auth.register.kicker": {
        "zh": "语言互通 · 文明互鉴",
        "en": "Languages connect · Cultures learn from each other",
    },
    "auth.register.title_1": {"zh": "一座桥，连接", "en": "One bridge, connecting"},
    "auth.register.title_2": {"zh": "学习者与教师。", "en": "learners and teachers."},
    "auth.register.proof_topics": {"zh": "个文化主题", "en": "cultural themes"},
    "auth.register.proof_tools": {"zh": "类教师工具", "en": "teacher tools"},
    "auth.register.proof_sources": {"zh": "条可检索资料", "en": "searchable sources"},
    "auth.register.kicker_first": {"zh": "创建第一个账号", "en": "Create the first account"},
    "auth.register.kicker_join": {"zh": "加入智语桥", "en": "Join Zhiyuqiao"},
    "auth.register.heading": {"zh": "先告诉我们，你是谁？", "en": "First, tell us who you are"},
    "auth.register.subheading": {
        "zh": "系统会根据你的身份展示不同的功能；注册后仍可在设置中修改。",
        "en": "Your role decides which tools you see. You can change it later in Settings.",
    },
    "auth.register.legend_role": {"zh": "选择身份", "en": "Choose your role"},
    "auth.register.role_student": {"zh": "我是学生", "en": "I am a student"},
    "auth.register.role_student_hint": {
        "zh": "学中文、练表达、探索上海",
        "en": "Learn Chinese, practise speaking, explore Shanghai",
    },
    "auth.register.role_teacher": {"zh": "我是教师", "en": "I am a teacher"},
    "auth.register.role_teacher_hint": {
        "zh": "备课、批改、设计文化任务",
        "en": "Plan lessons, give feedback, design cultural tasks",
    },
    "auth.register.legend_languages": {
        "zh": "希望 AI 使用哪些语言讲解？（可多选）",
        "en": "Which languages should the AI explain in? (choose any)",
    },
    "auth.register.consent_pre": {"zh": "我已阅读", "en": "I have read the "},
    "auth.register.consent_post": {
        "zh": "，并同意不要在对话中提交敏感个人信息。",
        "en": ", and I agree not to submit sensitive personal information in conversations.",
    },
    "auth.register.submit": {"zh": "创建账号并进入我的空间", "en": "Create account and enter my space"},
    "auth.register.footer": {"zh": "已有账号？", "en": "Already have an account?"},
    "auth.register.footer_link": {"zh": "直接登录", "en": "Sign in"},
    # ----------------------------------------------------- student dashboard
    "student.sidebar.kicker": {"zh": "LEARNING TOOLS", "en": "LEARNING TOOLS"},
    "student.sidebar.title": {"zh": "我的学习工具", "en": "My learning tools"},
    "student.sidebar.hint": {
        "zh": "根据你的中文水平提供讲解和练习",
        "en": "Explanations and practice matched to your Chinese level",
    },
    "student.greeting": {"zh": "你好，{name}", "en": "Hi, {name}"},
    "student.note.title": {"zh": "学习提示", "en": "Study tip"},
    "student.note.body": {
        "zh": "可以用 {languages} 提问；回答会参考你的中文水平。",
        "en": "You can ask in {languages}; answers follow your Chinese level.",
    },
    "student.hero.kicker": {"zh": "在上海，学中文", "en": "Learning Chinese in Shanghai"},
    "student.hero.title": {"zh": "今天，从一条城市线索开始。", "en": "Today, start from a single city clue."},
    "student.hero.body": {
        "zh": "观察建筑、倾听城市语言，用已经掌握的中文完成一次真实交流。",
        "en": "Watch the buildings, listen to the city's languages, and hold a real conversation with the Chinese you already have.",
    },
    "student.hero.cta_explore": {"zh": "开始文化探索", "en": "Start exploring culture"},
    "student.hero.cta_speak": {"zh": "练习开口表达", "en": "Practise speaking"},
    "student.level_card.label": {"zh": "我的中文", "en": "My Chinese"},
    "student.progress_aria": {"zh": "海派文化学习进度", "en": "Haipai culture learning progress"},
    "student.topics.kicker": {"zh": "EXPLORE SHANGHAI", "en": "EXPLORE SHANGHAI"},
    "student.topics.title": {"zh": "六条海派文化学习线索", "en": "Six Haipai culture learning clues"},
    "student.topics.hint": {
        "zh": "不只是“知道”，还要能用中文表达",
        "en": "Not just knowing it — being able to say it in Chinese",
    },
    "student.topics.start": {"zh": "开始 →", "en": "Start →"},
    "student.topic.bund.title": {"zh": "外滩与陆家嘴", "en": "The Bund & Lujiazui"},
    "student.topic.bund.contrast": {"zh": "历史 × 现代", "en": "History × Modernity"},
    "student.topic.bund.task": {"zh": "观察两岸建筑，说一处不同", "en": "Compare both riverbanks, name one difference"},
    "student.topic.greeting.title": {"zh": "你好与侬好", "en": "Nihao and Nong Hao"},
    "student.topic.greeting.contrast": {"zh": "普通话 × 沪语", "en": "Mandarin × Shanghainese"},
    "student.topic.greeting.task": {"zh": "听懂城市里的两种问候", "en": "Understand the city's two greetings"},
    "student.topic.tea.title": {"zh": "茶与咖啡", "en": "Tea & Coffee"},
    "student.topic.tea.contrast": {"zh": "传统 × 日常", "en": "Tradition × Everyday"},
    "student.topic.tea.task": {"zh": "用中文表达自己的选择", "en": "State your own choice in Chinese"},
    "student.topic.metro.title": {"zh": "上海地铁", "en": "Shanghai Metro"},
    "student.topic.metro.contrast": {"zh": "路线 × 礼貌", "en": "Routes × Courtesy"},
    "student.topic.metro.task": {"zh": "完成一次问路与指路", "en": "Ask for and give directions once"},
    "student.topic.architecture.title": {"zh": "建筑可阅读", "en": "Readable Architecture"},
    "student.topic.architecture.contrast": {"zh": "材料 × 故事", "en": "Materials × Stories"},
    "student.topic.architecture.task": {"zh": "从一扇门讲一个上海故事", "en": "Tell a Shanghai story through one door"},
    "student.topic.yangpu.title": {"zh": "杨浦滨江", "en": "Yangpu Riverside"},
    "student.topic.yangpu.contrast": {"zh": "工业 × 更新", "en": "Industry × Renewal"},
    "student.topic.yangpu.task": {"zh": "看见过去如何进入今天", "en": "See how the past enters the present"},
    "student.workbench.kicker": {"zh": "LEARNING COMPANION", "en": "LEARNING COMPANION"},
    "student.workbench.badge": {"zh": "按 {level} 讲解", "en": "Explained at {level}"},
    "student.composer.label": {"zh": "向学习伙伴提问", "en": "Ask your learning companion"},
    "student.composer.placeholder": {
        "zh": "可以用中文或你设置的讲解语言提问。例如：“侬好”是什么意思？",
        "en": "Ask in Chinese or your chosen explanation language. For example: what does “nong hao” mean?",
    },
    "assistant.review_notice": {
        "zh": "AI 回答仅供学习与备课参考；涉及事实、政策或教学决策时，请结合实际情况核验。",
        "en": "AI responses are for learning and lesson preparation. Verify facts, policy and teaching decisions before use.",
    },
    "student.record.kicker": {"zh": "MY LEARNING RECORD", "en": "MY LEARNING RECORD"},
    "student.record.title": {"zh": "我的学习记录", "en": "My learning record"},
    "student.record.hint": {
        "zh": "保存 AI 给出的任务，完成后写下真实收获",
        "en": "Save the tasks the AI gives you, then write what you actually gained",
    },
    # ----------------------------------------------------- teacher dashboard
    "teacher.sidebar.kicker": {"zh": "TEACHING TOOLS", "en": "TEACHING TOOLS"},
    "teacher.sidebar.title": {"zh": "教学工具箱", "en": "Teaching toolkit"},
    "teacher.sidebar.hint": {"zh": "从文化任务到课堂评价", "en": "From cultural tasks to classroom assessment"},
    "teacher.evidence.title": {"zh": "AI + 人工把关", "en": "AI + human review"},
    "teacher.evidence.body": {
        "zh": "文化事实、政策与教学决策请由教师核验后使用。",
        "en": "Verify cultural facts, policy and teaching decisions before classroom use.",
    },
    "teacher.hero.kicker": {"zh": "今日教学空间", "en": "Today's teaching space"},
    "teacher.hero.title": {"zh": "{name}，把上海变成一间中文课堂。", "en": "{name}, turn Shanghai into a Chinese classroom."},
    "teacher.hero.body": {
        "zh": "从真实的城市场景出发，生成语言支架清晰、文化信息可核验、评价环节完整的教学方案。",
        "en": "Start from real city scenes and build lessons with clear language scaffolding, verifiable cultural information and complete assessment.",
    },
    "teacher.hero.cta_lesson": {"zh": "设计一节海派文化课", "en": "Design a Haipai culture lesson"},
    "teacher.hero.cta_task": {"zh": "生成现场任务", "en": "Generate an on-site task"},
    "teacher.metrics.sources": {"zh": "可检索资料", "en": "Searchable sources"},
    "teacher.metrics.topics": {"zh": "海派主题", "en": "Haipai themes"},
    "teacher.metrics.tools": {"zh": "教师工具", "en": "Teacher tools"},
    "teacher.topics.kicker": {"zh": "HAIPAI TASKS", "en": "HAIPAI TASKS"},
    "teacher.topics.title": {"zh": "从城市资源到课堂任务", "en": "From city resources to classroom tasks"},
    "teacher.topics.hint": {"zh": "选择主题，自动带入课程实验室", "en": "Pick a theme and it loads into the lesson lab"},
    "teacher.topic.bund.title": {"zh": "外滩 × 陆家嘴", "en": "The Bund × Lujiazui"},
    "teacher.topic.bund.tag": {"zh": "城市时间", "en": "Urban time"},
    "teacher.topic.greeting.title": {"zh": "你好 × 侬好", "en": "Nihao × Nong Hao"},
    "teacher.topic.greeting.tag": {"zh": "语言接触", "en": "Language contact"},
    "teacher.topic.tea.title": {"zh": "茶 × 咖啡", "en": "Tea × Coffee"},
    "teacher.topic.tea.tag": {"zh": "日常交融", "en": "Everyday blending"},
    "teacher.topic.metro.title": {"zh": "上海地铁", "en": "Shanghai Metro"},
    "teacher.topic.metro.tag": {"zh": "公共文明", "en": "Public courtesy"},
    "teacher.topic.architecture.title": {"zh": "建筑可阅读", "en": "Readable Architecture"},
    "teacher.topic.architecture.tag": {"zh": "城市记忆", "en": "Urban memory"},
    "teacher.topic.yangpu.title": {"zh": "杨浦滨江", "en": "Yangpu Riverside"},
    "teacher.topic.yangpu.tag": {"zh": "工业遗产", "en": "Industrial heritage"},
    "teacher.workbench.kicker": {"zh": "AI WORKBENCH", "en": "AI WORKBENCH"},
    "teacher.workbench.badge": {"zh": "知识库已连接", "en": "Knowledge base connected"},
    "teacher.composer.label": {"zh": "描述教学需求", "en": "Describe your teaching need"},
    "teacher.composer.placeholder": {
        "zh": "描述学习者水平、课堂时长、文化主题和你希望得到的产出……",
        "en": "Describe learner level, lesson length, cultural theme and the output you want…",
    },
    "teacher.archive.kicker": {"zh": "TEACHING ARCHIVE", "en": "TEACHING ARCHIVE"},
    "teacher.archive.title": {"zh": "教案草稿与审核", "en": "Lesson drafts & review"},
    "teacher.archive.hint": {
        "zh": "保存 AI 产出，进入编辑页核验后再导出",
        "en": "Save AI output, verify it on the edit page, then export",
    },
    # -------------------------------------------------------------- settings
    "settings.back": {"zh": "返回{workspace}", "en": "Back to {workspace}"},
    "settings.title": {"zh": "账号与学习画像", "en": "Account & learning profile"},
    "settings.subtitle": {
        "zh": "智语桥会根据你的身份、中文水平或教学经验展示相应功能，并调整 AI 的回答方式。",
        "en": "Zhiyuqiao adapts its tools and the AI's answers to your role, Chinese level or teaching experience.",
    },
    "settings.summary.account": {"zh": "账号", "en": "Account"},
    "settings.summary.workspace": {"zh": "当前空间", "en": "Current space"},
    "settings.panel.kicker": {"zh": "个人设置", "en": "Personal settings"},
    "settings.panel.title": {"zh": "让空间更适合你", "en": "Make the space fit you"},
    "settings.legend_role": {"zh": "账号身份", "en": "Account role"},
    "settings.role_student": {"zh": "学生", "en": "Student"},
    "settings.role_student_hint": {"zh": "学习中文与探索文化", "en": "Learn Chinese and explore culture"},
    "settings.role_teacher": {"zh": "教师", "en": "Teacher"},
    "settings.role_teacher_hint": {"zh": "教学设计与内容审核", "en": "Lesson design and content review"},
    "settings.legend_languages": {
        "zh": "讲解或教学语言（可多选）",
        "en": "Explanation or teaching languages (choose any)",
    },
    "settings.new_password": {"zh": "新密码（选填）", "en": "New password (optional)"},
    "settings.new_password_placeholder": {
        "zh": "至少8个字符；不修改可留空",
        "en": "At least 8 characters; leave blank to keep the current one",
    },
    "settings.save": {"zh": "保存设置", "en": "Save settings"},
    "settings.danger.kicker": {"zh": "DATA CONTROL", "en": "DATA CONTROL"},
    "settings.danger.title": {"zh": "注销账号与删除数据", "en": "Delete account & data"},
    "settings.danger.body": {
        "zh": "此操作会永久删除账号、学习任务、反思记录、教案草稿和登录会话，无法撤销。",
        "en": "This permanently deletes your account, learning tasks, reflections, lesson drafts and sessions. It cannot be undone.",
    },
    "settings.danger.confirm": {
        "zh": "确认永久删除账号及全部个人档案吗？此操作无法撤销。",
        "en": "Permanently delete your account and all personal records? This cannot be undone.",
    },
    "settings.current_password": {"zh": "当前密码", "en": "Current password"},
    "settings.confirm_username": {"zh": "输入登录账号 {username} 以确认", "en": "Type your username {username} to confirm"},
    "settings.delete": {"zh": "永久删除我的账号", "en": "Permanently delete my account"},
    # --------------------------------------------------------------- privacy
    "privacy.kicker": {"zh": "PRIVACY & AI", "en": "PRIVACY & AI"},
    "privacy.zh_only_note": {
        "zh": "",
        "en": "This privacy and AI notice is currently maintained in Chinese only. An English version is planned; "
              "please ask the project team if you need a translation before agreeing.",
    },
    # -------------------------------------------------------------- artifact
    "artifact.topbar": {"zh": "教案审核与导出", "en": "Lesson review & export"},
    "artifact.nav_aria": {"zh": "教案操作", "en": "Lesson actions"},
    "artifact.back": {"zh": "返回工作台", "en": "Back to workspace"},
    "artifact.download": {"zh": "下载 Markdown", "en": "Download Markdown"},
    "artifact.print": {"zh": "打印 / 导出 PDF", "en": "Print / Export PDF"},
    "artifact.saved": {
        "zh": "修改已保存。审核状态会同步回教师工作台。",
        "en": "Changes saved. The review status is synced back to the teacher workspace.",
    },
    "artifact.kicker": {"zh": "TEACHING ARTIFACT", "en": "TEACHING ARTIFACT"},
    "artifact.status.reviewed": {"zh": "教师已审核", "en": "Reviewed by teacher"},
    "artifact.status.draft": {"zh": "AI 草稿 · 待审核", "en": "AI draft · Pending review"},
    "artifact.context.prompt": {"zh": "原始教学需求", "en": "Original teaching request"},
    "artifact.context.usage": {"zh": "使用说明", "en": "How to use"},
    "artifact.context.usage_body": {
        "zh": "AI 生成内容仅作为备课起点；涉及文化事实、政策、安全和学习者评价时，请教师复核后使用。",
        "en": "AI output is only a starting point. Verify cultural facts, policy, safety and learner assessment before classroom use.",
    },
    "artifact.field.title": {"zh": "教案标题", "en": "Lesson title"},
    "artifact.field.content": {"zh": "教案正文（可直接修改）", "en": "Lesson body (edit directly)"},
    "artifact.legend_status": {"zh": "审核状态", "en": "Review status"},
    "artifact.status.continue": {"zh": "继续编辑", "en": "Keep editing"},
    "artifact.status.continue_hint": {"zh": "保留为待审核草稿", "en": "Keep as a pending draft"},
    "artifact.status.reviewed_hint": {"zh": "确认已核验并完成修改", "en": "Verified and edits complete"},
    "artifact.save": {"zh": "保存修改", "en": "Save changes"},
    # ----------------------------------------------------------------- skill
    "skill.haipai_lesson_lab.label": {"zh": "海派文化课程实验室", "en": "Haipai Culture Lesson Lab"},
    "skill.haipai_lesson_lab.description": {
        "zh": "把上海文化场景转化为分级、可执行、可核验的中文课堂任务。",
        "en": "Turn Shanghai's cultural scenes into levelled, workable, verifiable classroom tasks.",
    },
    "skill.haipai_lesson_lab.starter.0": {
        "zh": "为HSK1学习者设计10分钟外滩与陆家嘴对比活动",
        "en": "Design a 10-minute Bund vs. Lujiazui comparison activity for HSK 1 learners",
    },
    "skill.haipai_lesson_lab.starter.1": {
        "zh": "把杨浦滨江工业遗产改造成HSK3口语任务",
        "en": "Turn the Yangpu Riverside industrial heritage into an HSK 3 speaking task",
    },
    "skill.haipai_lesson_lab.starter.2": {
        "zh": "设计一节茶与咖啡主题的跨文化中文课",
        "en": "Design a cross-cultural Chinese lesson on tea and coffee",
    },
    "skill.teacher_advisor.label": {"zh": "教学顾问", "en": "Teaching Advisor"},
    "skill.teacher_advisor.description": {
        "zh": "围绕学情、课堂组织、资源选择与教学难点给出综合建议。",
        "en": "Advice on learner needs, class organisation, resource choice and teaching pain points.",
    },
    "skill.teacher_advisor.starter.0": {
        "zh": "如何帮助初级学习者理解上海城市文化？",
        "en": "How can I help beginners understand Shanghai's urban culture?",
    },
    "skill.teacher_advisor.starter.1": {
        "zh": "为一节混合水平中文课设计差异化任务",
        "en": "Design differentiated tasks for a mixed-level Chinese class",
    },
    "skill.bridge_lesson_design.label": {"zh": "教学设计", "en": "Lesson Design"},
    "skill.bridge_lesson_design.description": {
        "zh": "生成目标、流程、活动、材料与评价一致的课堂方案。",
        "en": "Build lesson plans where objectives, flow, activities, materials and assessment line up.",
    },
    "skill.bridge_lesson_design.starter.0": {
        "zh": "设计一节45分钟的上海地铁公共文明主题课",
        "en": "Design a 45-minute lesson on courtesy in the Shanghai Metro",
    },
    "skill.bridge_lesson_design.starter.1": {
        "zh": "把建筑可阅读任务改成小组项目",
        "en": "Turn the Readable Architecture task into a group project",
    },
    "skill.bridge_translate.label": {"zh": "跨语种解释", "en": "Cross-language Explainer"},
    "skill.bridge_translate.description": {
        "zh": "翻译教学或学习文本，并补充拼音、词汇和语境提示。",
        "en": "Translate teaching or study texts, with pinyin, vocabulary and context notes.",
    },
    "skill.bridge_translate.starter.0": {
        "zh": "用英语解释“海纳百川”，并给出两个中文例句",
        "en": "Explain “海纳百川” in English and give two Chinese example sentences",
    },
    "skill.bridge_translate.starter.1": {
        "zh": "把这段上海城市介绍改写成适合初学者的双语文本",
        "en": "Rewrite this Shanghai city introduction as a beginner-friendly bilingual text",
    },
    "skill.bridge_correct.label": {"zh": "中文表达反馈", "en": "Chinese Writing Feedback"},
    "skill.bridge_correct.description": {
        "zh": "批改中文句子或短文，解释偏误并给出自然表达。",
        "en": "Correct Chinese sentences or short texts, explain the errors and give natural alternatives.",
    },
    "skill.bridge_correct.starter.0": {
        "zh": "请帮我修改：上海的建筑让我感觉历史和现代一起。",
        "en": "Please correct this: 上海的建筑让我感觉历史和现代一起。",
    },
    "skill.bridge_correct.starter.1": {
        "zh": "批改这段中文，并告诉我最需要练习的三个问题",
        "en": "Correct this Chinese and tell me the three things I most need to practise",
    },
    "skill.bridge_hsk_coaching.label": {"zh": "HSK 学习计划", "en": "HSK Study Plan"},
    "skill.bridge_hsk_coaching.description": {
        "zh": "制定阶段计划、能力重点、资源安排和模拟练习策略。",
        "en": "Stage-by-stage plans, skill priorities, resources and mock-practice strategy.",
    },
    "skill.bridge_hsk_coaching.starter.0": {
        "zh": "为我制定四周HSK3复习计划",
        "en": "Build me a four-week HSK 3 revision plan",
    },
    "skill.bridge_hsk_coaching.starter.1": {
        "zh": "我听力较弱，如何安排每天30分钟练习？",
        "en": "My listening is weak — how should I structure 30 minutes a day?",
    },
    "skill.bridge_tool_recommendation.label": {"zh": "数字教学工具", "en": "Digital Teaching Tools"},
    "skill.bridge_tool_recommendation.description": {
        "zh": "按课堂或作业场景推荐工具，并给出可落地的使用步骤。",
        "en": "Tool recommendations for class or homework scenarios, with practical setup steps.",
    },
    "skill.bridge_tool_recommendation.starter.0": {
        "zh": "推荐适合国际学生城市观察任务的协作工具",
        "en": "Recommend collaboration tools for international students' city observation tasks",
    },
    "skill.bridge_tool_recommendation.starter.1": {
        "zh": "如何低成本收集课堂即时反馈？",
        "en": "How can I collect instant classroom feedback cheaply?",
    },
    "skill.bridge_policy_interpretation.label": {"zh": "标准与政策", "en": "Standards & Policy"},
    "skill.bridge_policy_interpretation.description": {
        "zh": "解释国际中文教育标准、数字教育政策和教学合规边界。",
        "en": "Explain international Chinese-education standards, digital-education policy and compliance limits.",
    },
    "skill.bridge_policy_interpretation.starter.0": {
        "zh": "三等九级标准如何用于海派文化任务分级？",
        "en": "How do the three-tier nine-level standards apply to grading Haipai culture tasks?",
    },
    "skill.bridge_policy_interpretation.starter.1": {
        "zh": "AI生成教学材料需要注意哪些审核边界？",
        "en": "What review boundaries apply to AI-generated teaching materials?",
    },
    "skill.culture_explorer.label": {"zh": "海派文化探索", "en": "Haipai Culture Explorer"},
    "skill.culture_explorer.description": {
        "zh": "用适合你中文水平的方式认识上海，并完成真实交际任务。",
        "en": "Get to know Shanghai at your Chinese level, and finish a real communication task.",
    },
    "skill.culture_explorer.starter.0": {
        "zh": "我想用中文看懂外滩建筑，从哪里开始？",
        "en": "I want to read the Bund's architecture in Chinese — where do I start?",
    },
    "skill.culture_explorer.starter.1": {
        "zh": "为什么上海人会说“侬好”？我应该怎么用？",
        "en": "Why do Shanghai people say “nong hao”? How should I use it?",
    },
    "skill.culture_explorer.starter.2": {
        "zh": "带我完成一次杨浦滨江中文观察任务",
        "en": "Walk me through a Chinese observation task at Yangpu Riverside",
    },
    "skill.student_tutor.label": {"zh": "中文学习伙伴", "en": "Chinese Learning Companion"},
    "skill.student_tutor.description": {
        "zh": "解释词汇、语法和生活表达，按你的水平给例句与练习。",
        "en": "Explains vocabulary, grammar and everyday phrases, with examples and practice at your level.",
    },
    "skill.student_tutor.starter.0": {
        "zh": "“一边……一边……”怎么用？",
        "en": "How do I use “一边……一边……”?",
    },
    "skill.student_tutor.starter.1": {
        "zh": "在上海问路时，我可以怎么说？",
        "en": "How can I ask for directions in Shanghai?",
    },
    "skill.speaking_partner.label": {"zh": "情景口语陪练", "en": "Situational Speaking Partner"},
    "skill.speaking_partner.description": {
        "zh": "围绕城市生活进行角色对话，提供提示、追问和即时反馈。",
        "en": "Role-play city-life conversations with prompts, follow-up questions and instant feedback.",
    },
    "skill.speaking_partner.starter.0": {
        "zh": "和我练习在咖啡店点单，你做店员",
        "en": "Practise ordering at a cafe with me — you play the barista",
    },
    "skill.speaking_partner.starter.1": {
        "zh": "模拟我向同学介绍外滩和陆家嘴",
        "en": "Role-play me introducing the Bund and Lujiazui to a classmate",
    },
    # -------------------------------------------------- client-side strings
    "js.topic.default": {"zh": "自主探索", "en": "Open exploration"},
    "js.empty.student.title": {"zh": "从一个问题开始", "en": "Start with a question"},
    "js.empty.student.body": {
        "zh": "你可以用中文或熟悉的语言提问，我会按你的水平解释。",
        "en": "Ask in Chinese or a language you know well — I'll explain at your level.",
    },
    "js.empty.teacher.title": {"zh": "把教学情境说具体一点", "en": "Describe the teaching situation"},
    "js.empty.teacher.body": {
        "zh": "学习者水平、课堂时长、文化主题和预期产出越清楚，建议越可用。",
        "en": "The clearer the learner level, lesson length, cultural theme and expected output, the more usable the advice.",
    },
    "js.error.generic": {"zh": "操作失败", "en": "Something went wrong"},
    "js.date.just_saved": {"zh": "刚刚保存", "en": "Just saved"},
    "js.date.saved": {"zh": "已保存", "en": "Saved"},
    "js.progress": {"zh": "已完成 {completed} / {total} 条文化线索", "en": "{completed} of {total} cultural clues completed"},
    "js.tasks.empty_title": {"zh": "还没有学习记录", "en": "No learning records yet"},
    "js.tasks.empty_body": {
        "zh": "完成一次 AI 对话后，点击“保存为学习任务”。",
        "en": "After a conversation with the AI, click “Save as learning task”.",
    },
    "js.status.completed": {"zh": "已完成", "en": "Completed"},
    "js.status.in_progress": {"zh": "进行中", "en": "In progress"},
    "js.tasks.reflection_label": {"zh": "我的收获", "en": "What I gained"},
    "js.tasks.complete": {"zh": "完成任务并写反思", "en": "Complete and write a reflection"},
    "js.tasks.reflection_prompt": {"zh": "我完成了什么、学会了什么？", "en": "What did I do, and what did I learn?"},
    "js.tasks.reflection_save": {"zh": "保存完成记录", "en": "Save completion record"},
    "js.cancel": {"zh": "取消", "en": "Cancel"},
    "js.artifacts.empty_title": {"zh": "还没有教案草稿", "en": "No lesson drafts yet"},
    "js.artifacts.empty_body": {
        "zh": "生成教学方案后，点击“保存为教案草稿”。",
        "en": "After generating a lesson plan, click “Save as lesson draft”.",
    },
    "js.artifacts.reviewed": {"zh": "教师已审核", "en": "Reviewed"},
    "js.artifacts.pending": {"zh": "待审核", "en": "Pending review"},
    "js.artifacts.open": {"zh": "编辑、审核与导出", "en": "Edit, review & export"},
    "js.artifacts.fallback_title": {"zh": "教案", "en": "Lesson plan"},
    "js.copy": {"zh": "复制内容", "en": "Copy"},
    "js.copied": {"zh": "已复制", "en": "Copied"},
    "js.copy_failed": {"zh": "复制失败，请手动选择", "en": "Copy failed — select the text manually"},
    "js.save.task": {"zh": "保存为学习任务", "en": "Save as learning task"},
    "js.save.artifact": {"zh": "保存为教案草稿", "en": "Save as lesson draft"},
    "js.save.saving": {"zh": "正在保存…", "en": "Saving…"},
    "js.save.saved": {"zh": "已保存", "en": "Saved"},
    "js.save.failed": {"zh": "保存失败，请重试", "en": "Save failed — please try again"},
    "js.task.title": {"zh": "{topic}学习任务", "en": "{topic} learning task"},
    "js.sources.heading": {"zh": "回答依据", "en": "Sources"},
    "js.sources.dynamic": {"zh": "动态信息 · 使用前复核", "en": "Live information · verify before use"},
    "js.sources.verified": {"zh": "公开资料 · 已核验", "en": "Public source · verified"},
    "js.sources.topic_fallback": {"zh": "海派文化", "en": "Haipai culture"},
    "js.sources.title_fallback": {"zh": "来源资料", "en": "Source material"},
    "js.loading": {"zh": "正在组织答案，请稍等……", "en": "Composing an answer, one moment…"},
    "js.stop": {"zh": "停止生成", "en": "Stop"},
    "js.stop_aria": {"zh": "停止生成回答", "en": "Stop generating the answer"},
    "js.request_failed": {"zh": "请求失败", "en": "Request failed"},
    "js.no_stream": {"zh": "当前浏览器不支持流式回答", "en": "This browser does not support streamed answers"},
    "js.stopped_suffix": {"zh": "已停止生成。", "en": "Generation stopped."},
    "js.stopped": {"zh": "已停止生成，你可以调整问题后重试。", "en": "Generation stopped. Adjust your question and try again."},
    "js.failed": {"zh": "暂时无法完成：{message}。请稍后重试。", "en": "Could not finish: {message}. Please try again shortly."},
    "js.unavailable": {"zh": "系统不可用", "en": "service unavailable"},
    "js.send": {"zh": "发送", "en": "Send"},
    "js.send_aria": {"zh": "发送消息", "en": "Send message"},
}


class _SafeDict(dict):
    """Leaves unknown ``{placeholders}`` untouched instead of raising."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def normalize_lang(value: str | None) -> str | None:
    """Map a raw code (``en``, ``en-US``, ``zh-Hans``) onto a supported language."""
    if not value:
        return None
    code = str(value).strip().lower().replace("_", "-")
    if code in SUPPORTED_LANGS:
        return code
    base = code.split("-", 1)[0]
    return base if base in SUPPORTED_LANGS else None


def _from_accept_header(header: str | None) -> str | None:
    if not header:
        return None
    for chunk in header.split(","):
        code = normalize_lang(chunk.split(";", 1)[0])
        if code:
            return code
    return None


def resolve_lang(request: Any) -> str:
    """Cookie wins, then ``Accept-Language``, then Chinese."""
    cookie = normalize_lang(request.cookies.get(LANG_COOKIE_NAME))
    if cookie:
        return cookie
    return _from_accept_header(request.headers.get("accept-language")) or DEFAULT_LANG


def translate(key: str, lang: str = DEFAULT_LANG, **values: Any) -> str:
    """Look up ``key``; fall back to Chinese, then to the key itself.

    Falling back rather than raising keeps a partial translation shippable —
    an untranslated key renders Chinese instead of a raw slug.
    """
    entry = CATALOG.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if values and "{" in text:
        return text.format_map(_SafeDict(values))
    return text


def translator(lang: str = DEFAULT_LANG) -> Callable[..., str]:
    """Bind a language for template use: ``t('nav.logout')``."""

    def _t(key: str, **values: Any) -> str:
        return translate(key, lang, **values)

    return _t


def client_strings(lang: str = DEFAULT_LANG) -> dict[str, str]:
    """The ``js.*`` subset handed to ``static/assistant.js``."""
    return {key: translate(key, lang) for key in CATALOG if key.startswith("js.")}


def lang_options(current: str = DEFAULT_LANG) -> list[tuple[str, str, bool]]:
    """``(code, label, is_current)`` rows for the switcher partial."""
    return [(code, label, code == current) for code, label in LANG_LABELS.items()]


def html_lang(lang: str = DEFAULT_LANG) -> str:
    return HTML_LANG.get(lang, HTML_LANG[DEFAULT_LANG])


def js_locale(lang: str = DEFAULT_LANG) -> str:
    return JS_LOCALE.get(lang, JS_LOCALE[DEFAULT_LANG])
