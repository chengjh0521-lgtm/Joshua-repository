from __future__ import annotations

import re
import unicodedata
from pydantic import BaseModel


class SubtitleCue(BaseModel):
    index: int
    start_seconds: float
    end_seconds: float
    text: str


def parse_duration(value: str) -> float:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Duration cannot be empty.")
    if re.fullmatch(r"\d+(\.\d+)?", cleaned):
        seconds = float(cleaned)
    else:
        parts = cleaned.split(":")
        if len(parts) == 2:
            minutes, seconds_part = parts
            seconds = int(minutes) * 60 + float(seconds_part)
        elif len(parts) == 3:
            hours, minutes, seconds_part = parts
            seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds_part)
        else:
            raise ValueError("Duration must be seconds, MM:SS, or HH:MM:SS.")
    if seconds <= 0:
        raise ValueError("Duration must be greater than 0.")
    return seconds


def txt_to_srt(text: str, total_seconds: float, *, max_chars: int = 24) -> str:
    chunks = split_text_for_subtitles(text, max_chars=max_chars)
    if not chunks:
        raise ValueError("Input text is empty.")

    weights = [max(len(chunk.replace("\n", "")), 1) for chunk in chunks]
    total_weight = sum(weights)
    cues: list[SubtitleCue] = []
    elapsed = 0.0

    for index, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
        if index == len(chunks):
            end = total_seconds
        else:
            elapsed += total_seconds * weight / total_weight
            end = elapsed
        start = cues[-1].end_seconds if cues else 0.0
        if end <= start:
            end = min(total_seconds, start + 0.001)
        cues.append(SubtitleCue(index=index, start_seconds=start, end_seconds=end, text=wrap_subtitle_text(chunk, max_chars)))

    return "\n\n".join(format_srt_cue(cue) for cue in cues) + "\n"


def split_text_for_subtitles(text: str, *, max_chars: int) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    sentence_pattern = r"[^。！？!?；;…\n]+[。！？!?；;…]*|[^\n]+"
    sentences = [match.group(0).strip() for match in re.finditer(sentence_pattern, normalized) if match.group(0).strip()]

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        parts = split_long_text(sentence, max_chars)
        for part in parts:
            candidate = current + part if current else part
            if current and len(candidate) > max_chars:
                chunks.append(current)
                current = part
            else:
                current = candidate
    if current:
        chunks.append(current)
    return chunks


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_long_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    return [text[index : index + max_chars] for index in range(0, len(text), max_chars)]


def wrap_subtitle_text(text: str, max_chars: int) -> str:
    return clean_subtitle_punctuation(re.sub(r"\s+", " ", text).strip())


def clean_subtitle_punctuation(text: str) -> str:
    text = re.sub(r"[。.!！?？;；…]+", "。", text)
    text = re.sub(r"[，,、:：]+", "，", text)

    cleaned_chars: list[str] = []
    for char in text:
        if char in {"。", "，"}:
            cleaned_chars.append(char)
            continue
        category = unicodedata.category(char)
        if category.startswith(("P", "S")):
            continue
        cleaned_chars.append(char)

    cleaned = "".join(cleaned_chars)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"，{2,}", "，", cleaned)
    cleaned = re.sub(r"。{2,}", "。", cleaned)
    cleaned = re.sub(r"，。", "。", cleaned)
    cleaned = re.sub(r"。，", "。", cleaned)
    return cleaned


def format_srt_cue(cue: SubtitleCue) -> str:
    return f"{cue.index}\n{format_srt_time(cue.start_seconds)} --> {format_srt_time(cue.end_seconds)}\n{cue.text}"


def format_srt_time(seconds: float) -> str:
    milliseconds_total = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds_total, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
