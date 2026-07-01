import argparse
import asyncio
import json
from pathlib import Path

from backend.main import GenerateArticleRequest, GenerateIdeaRequest, generate_article_draft, generate_idea


def preview_file(path_value: str | None, limit: int = 2400) -> dict | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "path": str(path),
        "name": path.name,
        "preview": text[:limit],
        "size": path.stat().st_size,
    }


async def run(args: argparse.Namespace) -> dict:
    if args.kind == "idea":
        response = await generate_idea(GenerateIdeaRequest(topic=args.topic))
    else:
        response = await generate_article_draft(GenerateArticleRequest(topic=args.topic))

    data = response.model_dump()
    data["latest_file"] = preview_file(data.get("text_path") or data.get("markdown_path"))
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Zhihu writer agent.")
    parser.add_argument("--kind", choices=["article", "idea"], required=True)
    parser.add_argument("--topic", required=True)
    args = parser.parse_args()

    try:
        result = asyncio.run(run(args))
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
