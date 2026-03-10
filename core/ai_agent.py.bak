import os
from dotenv import load_dotenv
from openai import OpenAI
from .retriever import get_relevant_info

# 加载环境变量
load_dotenv()

# 初始化 DeepSeek 客户端
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

def generate_response(user_input):
    """
    核心逻辑：封装专家人设、执行All工作流、结合本地知识库生成回复
    """
    
    # 1. 检索阶段：从本地 knowledge.csv 获取针对性教育政策或教学资料
    local_context = get_relevant_info(user_input)
    
    # 2. 角色与任务建模 (System Prompt)
  
    system_instruction = f"""
    # 角色
    你是一位具备国际中文教育（博士）与教育技术学（硕士）双背景的国际多语言数字化教育顾问。你拥有10年HSK教学经验，使命是提供数字化教学解决方案。

    ## 核心工作流 (All 工作流)
    1. 初步判断：分析用户需求是否属于国际中文教育数字化范畴。
    2. 需求分类：区分是教学资源、工具推荐、政策咨询还是技术方案。
    3. 精准服务：结合本地参考资料给出专业建议。

    ## 限制与准则
    - 仅回答与国际中文教育数字化教学相关的问题。
    - 遵循地域适配优先和开源工具优先原则。
    - 拒绝涉及宗教/政治敏感内容。
    - 本地参考资料：{local_context}
    """

    try:
        # 3. 执行 AI 生成
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_input}
            ],
            temperature=0.3 # 降低随机性，确保专家回答的严谨性
        )
        
        content = response.choices[0].message.content
        
        # 4. 强制添加“人工审核提示” (符合你的限制要求)
        final_output = f"{content}\n\n---\n **人工审核提示**：本内容由 AI 生成，涉及具体教学决策或政策解读时，请结合实际教学环境及官方最新文件进行核实。"
        
        return final_output

    except Exception as e:
        return f"顾问系统暂时无法响应: {str(e)}"