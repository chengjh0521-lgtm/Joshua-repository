请根据已完成章节更新小说记忆。

要求：
- 只记录本章已经发生的事实
- 不虚构后续未发生剧情
- Character DB 要覆盖旧状态，保持可供下一章读取
- World DB 只记录已经成立的世界观事实，不得扩写解释
- Lore DB 只记录已经出现的物品、地点、秘密、能力、伏笔和其当前状态
- 剧情时间线要覆盖旧时间线并加入本章事件
- 伏笔记录要覆盖旧伏笔记录，标注新增、推进、回收、未回收
- 章节摘要要简洁但包含本章结果和结尾钩子
- 不要为了完整而新增未出现信息

输出必须使用以下分隔段：

---CHAPTER_SUMMARY---
第 $chapter_number 章《$title》摘要。

---CHARACTERS---
更新后的完整 Character DB，优先使用 JSON。

---WORLD---
更新后的完整 World DB，优先使用 JSON。

---LORE_DB---
更新后的完整 Lore DB，优先使用 JSON。

---PLOT_TIMELINE---
更新后的完整剧情时间线。

---FORESHADOWING---
更新后的完整伏笔记录。

---NEXT_HOOK---
下一章建议钩子，一到三句话。

旧人物状态：
$characters

旧 World DB：
$world

旧 Lore DB：
$lore_db

旧剧情时间线：
$plot_timeline

旧伏笔记录：
$foreshadowing

旧章节摘要：
$chapter_summaries

本章正文：
$chapter
