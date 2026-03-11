# 开源教育技术工具知识库 (Open Source EdTech Knowledge Base)

## 📌 项目简介
本知识库旨在为教育领域的**大语言模型 (LLM)** 和**知识图谱 (Knowledge Graph)** 构建提供高质量、结构化的底层语料。
数据涵盖了当前主流开源教育生态系统（学习管理系统、虚拟教室、互动课件）的官方底层架构、API 手册、使用指南和模板逻辑。

所有数据均经过深度清洗，去除了 HTML 标签、Docusaurus/Jekyll 框架配置头 (Front-matter) 以及冗余脚本，最终统一封装为面向机器阅读优化的 `.jsonl` (JSON Lines) 格式。

## 🗂️ 包含的数据集

| 文件名 | 所属工具 | 工具类型 | 数据来源与内容 |
| :--- | :--- | :--- | :--- |
| `moodle_knowledge_base.jsonl` | **Moodle** | LMS (学习管理系统) | 提取自 Moodle 官方开发者文档 (devdocs)。包含插件开发、系统架构、API 接口和管理员配置指南。 |
| `bbb_knowledge_base.jsonl` | **BigBlueButton** | Virtual Classroom (虚拟教室) | 提取自 BBB 核心源码库 (Docusaurus)。包含 WebRTC 音视频架构、录制机制、Greenlight 前端及部署手册。 |
| `jitsi_knowledge_base.jsonl` | **Jitsi Meet** | Video Conferencing (视频会议) | 提取自 Jitsi Handbook (Docusaurus)。包含 Jicofo/Videobridge 架构、自建服务器指南及集成说明。 |
| `learningapps_knowledge_base.jsonl` | **LearningApps** | Interactive Content (互动课件) | 提取自官方创建面板。包含 21 种核心教学模板的交互定义及底层教育逻辑映射。 |

## 📊 数据结构 (Data Schema)

每个 `.jsonl` 文件按行存储，每一行代表一个独立的文档节点或知识块。数据均采用统一的 JSON 键值结构：

```json
{
  "tool_name": "工具名称 (如: BigBlueButton)",
  "category": "分类路径 (如: docs/admin/setup)",
  "title": "文档或知识块标题",
  "content": "经过清洗后的纯净正文，适合进行文本切块 (Chunking) 和向量化 (Embedding)"
}