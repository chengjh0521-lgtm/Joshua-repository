from __future__ import annotations

from pydantic import BaseModel

from agents.common import section
from services.deepseek_client import DeepSeekClient


HUMANIZE_INSTRUCTION = """需要按番茄小说签约编辑和百万字网文作者的标准降低 AI 写作特征。目标不是华丽，而是真实。

硬性规则：
1. 不删除剧情，不改变人物、伏笔、世界观和章节节奏，仅修改表达方式。
2. 降低 AI 节奏。不要每隔几百字就强行刺激一次；如果事件连续推进，要加入人物观察、人物思考、无效动作和环境变化，让节奏自然呼吸。
3. 增加真人写作特征。允许人物停顿、犹豫、走神、误判、自我否定。少用“他发现”“他知道”“他意识到”，可以改成“他怀疑”“他不确定”“他觉得可能”“他甚至怀疑是不是自己看错”。
4. 减少模板句。谨慎使用“他愣了一下”“他没有说话”“他知道”“他觉得”“他看向”“他低头”“他沉默了”“像是什么”“仿佛”“似乎”，同一种句式不要连续出现。
5. 增加生活噪音。允许天气、虫鸣、衣服、泥土、鞋底、呼吸、手部动作、无意义观察、村民闲聊、生活细节；这些细节不要推动剧情，只用于增加真实感。
6. 降低信息密度。不要连续抛伏笔；已有神秘物品、神秘人物、神秘地点、神秘能力时，不再增加新的谜团。
7. 人物反应符合真人。第一次看见异常时，先惊讶、怀疑、害怕、试探，最后才行动，不要立刻接受、调查、分析。
8. 对白真人化。人物不要只说推动剧情的话，允许重复、停顿、欲言又止、说废话、说错话。
9. 环境不要模板化。不要每段都描写环境，少用“风吹过”“月光洒下”“空气安静”这类模板句。
10. 允许留白。伏笔成立后不要立刻解释所有东西。

最终目标：让专业编辑更倾向认为这是成熟网文作者写作，而不是 AI 生成。"""


class ShortStory(BaseModel):
    title: str
    body: str
    notes: str


class ShortStoryWriter:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def run(
        self,
        *,
        goal: str,
        genre: str,
        style: str,
        min_words: int,
        max_words: int,
        max_paragraphs: int,
        remove_ai: bool,
        trope_library: str,
        originality_rules: str,
    ) -> ShortStory:
        prompt = self.client.render_prompt(
            "short_story_write.md",
            goal=goal,
            genre=genre,
            style=style,
            min_words=min_words,
            max_words=max_words,
            max_paragraphs=max_paragraphs,
            remove_ai_instruction=HUMANIZE_INSTRUCTION if remove_ai else "不需要额外执行去 AI 改写，但仍需保持自然中文表达。",
            trope_library=trope_library,
            originality_rules=originality_rules,
        )
        result = self.client.chat(
            prompt,
            system="你是中文短篇小说作者。只写一个完整原创短篇，不写成长篇章节。",
            temperature=0.78,
            max_tokens=9000,
        )
        return ShortStory(
            title=section(result, "TITLE") or "未命名短篇",
            body=section(result, "BODY") or result,
            notes=section(result, "NOTES") or "已生成完整原创短篇。",
        )
