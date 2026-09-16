"""One reply-language policy shared by all conversational modules."""
from typing import Literal

ResponseLanguage = Literal["auto", "profile", "zh", "en", "pt", "es", "fr", "de", "ja", "ko"]

LANGUAGE_NAMES = {
    "zh": "中文", "en": "English", "pt": "Português", "es": "Español",
    "fr": "Français", "de": "Deutsch", "ja": "日本語", "ko": "한국어",
}


def reply_language_policy(selection: str, profile_language: str) -> str:
    if selection == "auto":
        rule = (
            "默认使用用户本轮提问的主要语言回答：英文提问用英文，中文提问用中文，其他语言同理。"
            "依据用户自己的提问措辞判断，不要把引用的中文、待翻译/批改文本、知识库或历史助手回复的语言当作提问语言。"
            "例如 hello? 必须自然地用英文回应；What does ‘侬好’ mean? 应用英文解释。"
            "如果输入只有数字、表情或无法判断语言的短片段，先沿用最近用户提问的语言；"
            f"仍无法判断时才使用账号首选语言 {profile_language}。"
        )
    elif selection == "profile":
        rule = f"使用账号首选讲解语言 {profile_language} 回答。"
    elif selection in LANGUAGE_NAMES:
        rule = f"用户在回答语言选项中指定了 {LANGUAGE_NAMES[selection]}，使用该语言进行回答和讲解，不随输入语言改变。"
    else:
        raise ValueError("Unsupported response language")
    return (
        "## 本轮回答语言（统一适用于所有模块）\n" + rule + "\n"
        "本轮语言规则优先于账号画像和模块中的默认语言，不受界面语言影响。"
        "用户本轮明确要求用另一种语言回答时，遵循该明确要求。"
        "翻译的目标文本、中文纠错结果、中文例句及明确要求的中文角色台词，保留任务要求的语言；"
        "周围的解释、引导和反馈仍使用上述回答语言。不要因学习对象是中文就把全部讲解改成中文。"
    )
