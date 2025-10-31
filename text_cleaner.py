# text_cleaner.py

def clean_response(text: str) -> str:
    """
    Clean Qwen-style outputs: remove role echoes and system prompt echoes.
    """
    if text is None:
        return ""

    text = text.strip()

    # Remove common role tokens that may appear in generations
    for tag in ["user", "assistant", "system"]:
        text = text.replace(f"{tag}\n", "")
        text = text.replace(f"{tag}\r\n", "")
        text = text.replace(tag, "").strip()

    # Remove echoes of system prompt or model self-descriptions
    system_starts = [
        "You are GPTCoach",
        "You are Qwen",
        "You are a helpful assistant",
        "You are an AI assistant",
    ]
    for start in system_starts:
        if text.startswith(start):
            parts = text.split(". ", 1)
            if len(parts) > 1:
                text = parts[1].strip()
            else:
                text = ""
            break

    # Deduplicate consecutive identical lines
    lines = [line.rstrip() for line in text.splitlines()]
    deduped_lines = []
    for line in lines:
        if not deduped_lines or deduped_lines[-1] != line:
            deduped_lines.append(line)

    return "\n".join(deduped_lines).strip()
