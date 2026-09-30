import re
from html import escape
from html.parser import HTMLParser

from tg_bot.constants.premium_emoji import MAX_TEXT_EMOJI, PROTECTED_HTML_TAGS


def valid_icons(icons):
    return {
        emoji: identity
        for emoji, identity in icons.items()
        if isinstance(emoji, str)
        and emoji
        and isinstance(identity, str)
        and identity.isascii()
        and identity.isdecimal()
    }


class EmojiTextParser(HTMLParser):
    def __init__(self, source, icons):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.icons = icons
        self.pattern = re.compile(
            "|".join(re.escape(key) for key in sorted(icons, key=len, reverse=True))
        )
        self.line_offsets = [0] + [
            index + 1 for index, value in enumerate(source) if value == "\n"
        ]
        self.protected = []
        self.candidates = []
        self.existing = 0

    def handle_starttag(self, tag, attrs):
        if tag == "tg-emoji":
            self.existing += 1
        if tag in PROTECTED_HTML_TAGS:
            self.protected.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag == "tg-emoji":
            self.existing += 1

    def handle_endtag(self, tag):
        if tag in self.protected:
            position = len(self.protected) - self.protected[::-1].index(tag) - 1
            del self.protected[position:]

    def handle_data(self, data):
        if self.protected or len(self.candidates) >= MAX_TEXT_EMOJI:
            return
        line, column = self.getpos()
        offset = self.line_offsets[line - 1] + column
        for match in self.pattern.finditer(data):
            self.candidates.append(
                (offset + match.start(), offset + match.end(), match.group())
            )
            if len(self.candidates) >= MAX_TEXT_EMOJI:
                break

    def render(self):
        parts = []
        previous = 0
        available = max(0, MAX_TEXT_EMOJI - self.existing)
        for start, end, emoji in self.candidates[:available]:
            parts.append(self.source[previous:start])
            parts.append(
                f'<tg-emoji emoji-id="{self.icons[emoji]}">{escape(emoji)}</tg-emoji>'
            )
            previous = end
        parts.append(self.source[previous:])
        return "".join(parts)


def decorate_html(text, icons):
    selected = valid_icons(icons)
    if not text or not selected:
        return text
    parser = EmojiTextParser(text, selected)
    parser.feed(text)
    parser.close()
    return parser.render()
