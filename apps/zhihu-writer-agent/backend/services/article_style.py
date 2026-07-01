import re


QUOTE_CHARS = str.maketrans({
    "“": "",
    "”": "",
    "‘": "",
    "’": "",
    "\"": "",
    "'": "",
    "《": "",
    "》": "",
    "「": "",
    "」": "",
    "『": "",
    "』": "",
    "—": "",
    "–": "",
})


def normalize_answer_style(text: str, max_paragraphs: int = 5) -> str:
    text = text.translate(QUOTE_CHARS)
    text = text.replace("——", "").replace("--", "")
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    cleaned = []

    for line in lines:
        if not line:
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*+]\s+", "", line)
        line = re.sub(r"^\d+[.)、]\s*", "", line)
        line = re.sub(r"^[一二三四五六七八九十]+[、.]\s*", "", line)
        line = line.replace("——", "").replace("--", "")
        cleaned.append(line.strip())

    if not cleaned:
        return ""

    if len(cleaned) <= max_paragraphs:
        return "\n\n".join(cleaned)

    buckets = [[] for _ in range(max_paragraphs)]
    for index, paragraph in enumerate(cleaned):
        bucket_index = min(index * max_paragraphs // len(cleaned), max_paragraphs - 1)
        buckets[bucket_index].append(paragraph)

    return "\n\n".join(" ".join(bucket).strip() for bucket in buckets if bucket)
