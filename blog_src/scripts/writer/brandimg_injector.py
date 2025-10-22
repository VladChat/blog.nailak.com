import re

def inject_brand_images(markdown_text: str) -> str:
    """
    Ставит {{< brandimg >}} после 1-й и 3-й секции (заголовков "## ...").
    Вставка идёт после конца строки заголовка, чтобы не ломать Markdown.
    Защита от дублирования: если рядом уже есть brandimg — пропускаем.
    """
    if not markdown_text:
        return markdown_text

    # Ищем заголовки H2: "##" + пробел(ы) + текст до конца строки
    h2_iter = list(re.finditer(r'^##\s+.*$', markdown_text, re.MULTILINE))
    insert_positions = []

    def after_line_end(idx: int) -> int:
        """Вернуть индекс сразу после перевода строки текущего заголовка."""
        nl = markdown_text.find('\n', idx)
        return len(markdown_text) if nl == -1 else nl + 1

    if len(h2_iter) >= 1:
        insert_positions.append(after_line_end(h2_iter[0].end()))
    if len(h2_iter) >= 3:
        insert_positions.append(after_line_end(h2_iter[2].end()))

    # Чтобы индексы не «съехали» при нескольких вставках — идём с конца
    snippet = "\n\n{{< brandimg >}}\n\n"
    for pos in sorted(insert_positions, reverse=True):
        # Если рядом уже есть brandimg, пропускаем
        window = markdown_text[max(0, pos - 64): min(len(markdown_text), pos + 64)]
        if "{{< brandimg" in window:
            continue
        markdown_text = markdown_text[:pos] + snippet + markdown_text[pos:]

    return markdown_text
