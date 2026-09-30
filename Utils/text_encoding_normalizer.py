from __future__ import annotations
import re


class TextEncodingNormalizer:
    _MOJIBAKE_PAIR = re.compile("[РСÐÑ][^\\s]")
    _MOJIBAKE_SIGNATURES = (
        "Рџ",
        "рџ",
        "Рќ",
        "Рµ",
        "Р°",
        "РЅ",
        "СЃ",
        "С‚",
        "вЂ",
        "вњ",
        "Ð",
        "Ñ",
        "â€",
        "ðŸ",
    )
    _SOURCE_ENCODINGS = ("cp1251", "latin1")

    @classmethod
    def normalize(cls, text: str) -> str:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        normalized_text = text
        for _ in range(2):
            repaired_text = cls._select_repaired_text(normalized_text)
            if repaired_text == normalized_text:
                break
            normalized_text = repaired_text
        return normalized_text

    @classmethod
    def _select_repaired_text(cls, text: str) -> str:
        source_score = cls._mojibake_score(text)
        if source_score < 4:
            return text
        candidates = [text]
        for encoding in cls._SOURCE_ENCODINGS:
            try:
                candidates.append(text.encode(encoding).decode("utf-8"))
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
        return min(
            candidates,
            key=lambda candidate: (cls._mojibake_score(candidate), -len(candidate)),
        )

    @classmethod
    def _mojibake_score(cls, text: str) -> int:
        pair_score = len(cls._MOJIBAKE_PAIR.findall(text)) * 2
        signature_score = sum(
            (text.count(signature) * 3 for signature in cls._MOJIBAKE_SIGNATURES)
        )
        return pair_score + signature_score + text.count("�") * 8
