"""
Normaliza el texto que redacta el agente al subconjunto de HTML que acepta Telegram.

El prompt pide "solo HTML con <b>, <i>, <code> y <a>", pero es una instrucción, no
una garantía: el modelo a veces responde con Markdown (viñetas `*`, `**negrita**`)
o con etiquetas que Telegram no soporta (`<ul>`, `<br>`). Con `parse_mode="HTML"`
Telegram no muestra eso mal: **rechaza el mensaje entero** (BadRequest "can't
parse entities"), igual que con un `<` o `&` suelto en el texto ("a < b",
"Simon & Garfunkel", una URL con `&`).

`normalize_html()` se aplica a la respuesta final del agente (ver
`MusicAssistant._agent_query`) y deja siempre un HTML válido para Telegram. El
frontend web lo convierte después a Markdown (`frontend/app.py::_html_to_md`),
que deshace también el escapado de entidades.
"""
import html
import re

_ALLOWED = {"b", "i", "code", "a"}
# Etiquetas de bloque que no existen en Telegram: se sustituyen por un salto de línea
_BLOCK = {"br", "p", "div", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "blockquote", "hr", "table", "tr"}
_TAG_RE = re.compile(r"</?([a-zA-Z][a-zA-Z0-9]*)\b[^<>]*>")
_ENTITY_RE = re.compile(r"&(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);")
_HREF_RE = re.compile(r'''^<a\s+href\s*=\s*["']([^"'<>]+)["']\s*>$''', re.IGNORECASE)


def _markdown_to_html(text: str) -> str:
    """Convierte el Markdown más habitual en las etiquetas equivalentes."""
    # Bloques de código: se quedan como <code> (Telegram no tiene <pre> en este subconjunto)
    text = re.sub(r"```[a-zA-Z]*\n?(.*?)```", lambda m: f"<code>{m.group(1).strip()}</code>", text, flags=re.DOTALL)
    # Encabezados "## Título" -> negrita en su propia línea
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", r"<b>\1</b>", text)
    # Viñetas "* ", "- ", "+ " al principio de línea -> "• " (conservando la sangría)
    text = re.sub(r"(?m)^(\s*)[*+-]\s+", r"\1• ", text)
    # Enlaces [texto](url)
    text = re.sub(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', text)
    # Negrita **x** / __x__ antes que cursiva, para no confundir los asteriscos dobles
    text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<b>\1</b>", text, flags=re.DOTALL)
    text = re.sub(r"__(?=\S)(.+?)(?<=\S)__", r"<b>\1</b>", text, flags=re.DOTALL)
    # Cursiva *x* (sin espacios pegados a los asteriscos, para no tocar "3 * 4")
    text = re.sub(r"(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])", r"<i>\1</i>", text)
    # Código en línea `x`
    text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)
    return text


def _join_bullets(m: "re.Match") -> str:
    """Quita la línea en blanco antes de una viñeta solo si la línea anterior también lo es."""
    before = m.string[:m.start()]
    prev_line = before[before.rfind("\n") + 1:]
    return "\n" if prev_line.lstrip().startswith("• ") else m.group(0)


def _escape_text(segment: str) -> str:
    """Escapa &, < y > de un trozo de texto sin etiquetas, respetando entidades ya escritas."""
    out, last = [], 0
    for m in _ENTITY_RE.finditer(segment):
        out.append(html.escape(segment[last:m.start()], quote=False))
        out.append(m.group(0))
        last = m.end()
    out.append(html.escape(segment[last:], quote=False))
    return "".join(out)


def normalize_html(text: str) -> str:
    """Devuelve `text` como HTML válido para Telegram (b, i, code, a), sin perder contenido."""
    if not text:
        return text
    text = _markdown_to_html(text)

    tokens = []  # (tipo, valor): ("text", str) o ("open"/"close", nombre, html)
    last = 0
    for m in _TAG_RE.finditer(text):
        if m.start() > last:
            tokens.append(("text", text[last:m.start()]))
        name, raw = m.group(1).lower(), m.group(0)
        closing = raw.startswith("</")
        if name in _ALLOWED:
            if name == "a" and not closing:
                href = _HREF_RE.match(raw)
                if href:
                    tokens.append(("open", "a", f'<a href="{html.escape(href.group(1), quote=True)}">'))
                # <a> sin href válido: se descarta la etiqueta, el texto se queda
            else:
                tokens.append(("close" if closing else "open", name, f"</{name}>" if closing else f"<{name}>"))
        elif name == "li" and not closing:
            tokens.append(("text", "\n• "))
        elif name in _BLOCK:
            tokens.append(("text", "\n"))
        # Cualquier otra etiqueta (span, u, s...) se elimina sin dejar rastro
        last = m.end()
    if last < len(text):
        tokens.append(("text", text[last:]))

    # Equilibrar etiquetas: Telegram también rechaza un <b> sin cerrar o un </i> huérfano.
    # Se recorre con una pila; los cierres sin apertura se descartan y lo que quede abierto
    # se cierra al final.
    out, stack = [], []
    for tok in tokens:
        kind = tok[0]
        if kind == "text":
            out.append(_escape_text(tok[1]))
        elif kind == "open":
            if tok[1] in stack:  # Telegram no admite anidar una etiqueta dentro de sí misma
                continue
            stack.append(tok[1])
            out.append(tok[2])
        else:
            if tok[1] not in stack:
                continue
            # Cerrar en orden lo que esté abierto por encima (anidamiento mal hecho)
            while stack:
                top = stack.pop()
                out.append(f"</{top}>")
                if top == tok[1]:
                    break
    while stack:
        out.append(f"</{stack.pop()}>")

    result = "".join(out)
    # Líneas en blanco de más que dejan las etiquetas de bloque eliminadas, y la
    # línea en blanco entre viñetas consecutivas (el modelo a veces las separa)
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = re.sub(r"\n[ \t]*\n(?=[ \t]*• )", _join_bullets, result)
    return result.strip()
