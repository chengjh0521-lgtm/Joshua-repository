请根据已完成章节更新小说记忆。

要求：
- 只记录本章已经发生的事实
- 不虚构后续未发生剧情
- 人物状态要覆盖旧状态，保持可供下一章读取
- 剧情时间线要覆盖旧时间线并加入本章事件
- 伏笔记录要覆盖旧伏笔记录，标注新增、推进、回收、未回收
- 章节摘要要简洁但包含本章结果和结尾钩子

输出必须使用以下分隔段：

---CHAPTER_SUMMARY---
第 $chapter_number 章《$title》摘要。

---CHARACTERS---
更新后的完整人物状态。

---PLOT_TIMELINE---
更新后的完整剧情时间线。

---FORESHADOWING---
更新后的完整伏笔记录。

---NEXT_HOOK---
下一章建议钩子，一到三句话。

旧人物状态：
$characters

旧剧情时间线：
$plot_timeline

旧伏笔记录：
$foreshadowing

旧章节摘要：
$chapter_summaries

本章正文：
$chapter
