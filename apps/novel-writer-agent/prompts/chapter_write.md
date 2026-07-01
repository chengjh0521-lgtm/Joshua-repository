请根据本章规划，写第 $chapter_number 章正文。

最高规则：
$system_rules

用户本章要求：
$goal

写作要求：
- 只写当前一章，不连续生成下一章
- 每章标题由你自动生成
- 正文用中文小说自然叙述
- 开篇尽快进入场景，不写泛泛背景介绍
- 多用动作、对话、细节承载信息
- 少用“他知道”“这一刻”“命运齿轮”“空气仿佛凝固”等模板句
- 不要解释创作意图
- 不要输出 Markdown 标题符号
- 字数和段落数必须优先服从用户本章要求中的生成约束
- 如果受模型长度限制，可以适当缩短，但必须完整收束本章小钩子
- 必须遵守 Character DB、World DB、Lore DB
- 禁止自行新增世界观、能力体系、势力规则和人物关系
- 如果规划里没有新增设定，本章正文不得新增设定

输出必须使用：

---TITLE---
章节标题，不要带“第几章”。

---BODY---
章节正文。

本章规划：
$chapter_plan

小说大框架：
$story_bible

卷纲与剧情树：
$outline

人物状态：
$characters

世界观数据库：
$world

Lore Database：
$lore_db

剧情时间线：
$plot_timeline

伏笔记录：
$foreshadowing

章节摘要：
$chapter_summaries
