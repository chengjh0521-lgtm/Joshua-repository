import re


QUOTE_CHARS = str.maketrans(
    {
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
    }
)


def normalize_answer_style(text: str) -> str:
    text = text.translate(QUOTE_CHARS)
    text = text.replace("——", "").replace("—", "").replace("--", "")
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    cleaned = []

    for line in lines:
        if not line:
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*+]\s+", "", line)
        line = re.sub(r"^\d+[.)、]\s*", "", line)
        line = re.sub(r"^[一二三四五六七八九十]+[、.]\s*", "", line)
        line = line.replace("——", "").replace("—", "").replace("--", "")
        cleaned.append(line.strip())

    return "\n\n".join(cleaned)
