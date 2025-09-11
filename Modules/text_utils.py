# text_utils.

import unicodedata, re
from functools import lru_cache
from opencc import OpenCC

def normalize_input(text: str):
    if not text or not isinstance(text, str):
        return "", ""
    # preserve paragraph breaks, compact per-line whitespace
    lines = text.splitlines()
    cleaned = [' '.join(line.split()) for line in lines]
    text = '\n'.join(cleaned)

    full_punct_map = {
        '!': '！', '"': '＂', '#': '＃', '$': '＄', '%':'％', '&':'＆', "'": '＇', '(':'（', ')':'）',
        '*':'＊', '+':'＋', ',':'，', '-':'－', '.':'。', '/':'／', ':':'：', ';':'；', '<':'＜',
        '=':'＝', '>':'＞', '?':'？', '@':'＠', '[':'［', '\\':'＼', ']':'］', '^':'＾',
        '_':'＿', '`':'｀', '{':'｛', '|':'｜', '}':'｝', '~':'～',
        '《':'〈', '》':'〉', '「':'『', '」':'』', '『':'「', '』':'」'
    }
    translator = str.maketrans(full_punct_map)
    text = unicodedata.normalize('NFKC', text).translate(translator)

    cc_t2s = OpenCC('t2s')
    cc_s2t = OpenCC('s2t')
    simplified = cc_t2s.convert(text)
    traditional = cc_s2t.convert(text)
    return traditional, simplified

@lru_cache(maxsize=16)
def normalize_input_cached(text: str):
    return normalize_input(text or "")

def highlight_words_dual(text_trad, text_simp, words_string, highlight_style="background-color: #ffffcc;"):
    """
    Highlight words in both Traditional and Simplified texts using HTML spans.
    """
    unified = (words_string or "").replace("，", ",")
    words_raw = [w.strip() for w in unified.split(",") if w.strip()]
    for w in words_raw:
        trad, simp = normalize_input(w)  # ✅ direct call, no import needed
        if trad:
            text_trad = re.sub(
                re.escape(trad),
                f'<span style="{highlight_style}">{trad}</span>',
                text_trad
            )
        if simp:
            text_simp = re.sub(
                re.escape(simp),
                f'<span style="{highlight_style}">{simp}</span>',
                text_simp
            )
    return text_trad, text_simp


def is_traditional(text_input, text_trad, text_simp):
    trad_matches = sum(1 for a, b in zip(text_input, text_trad) if a == b)
    simp_matches = sum(1 for a, b in zip(text_input, text_simp) if a == b)
    return trad_matches >= simp_matches

@lru_cache(maxsize=256)
def canon_title_for_compare(s: str) -> str:
    if not s:
        return ""
    trad, _ = normalize_input_cached(s)
    trad = re.sub(r"\s+", " ", trad).strip()
    return trad.lower()
