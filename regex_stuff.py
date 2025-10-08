import re

# ============================================================
# Shared regexes
# ============================================================

# Existing math segments to avoid double-wrapping
MATH_SEG_RE = re.compile(
    r'(\\\((?:\\.|[^\\])*?\\\)'        # \( ... \)
    r'|\\\[(?:\\.|[^\\])*?\\\]'        # \[ ... \]
    r'|(?<!\\)\$\$(?:\\.|[^\\])*?\$\$' # $$ ... $$
    r'|(?<!\\)\$(?:\\.|[^\\])*?\$)'    # $ ... $
)

# Big/comma-grouped numbers (detection)
BIG_NUMS_RE = re.compile(r'(?<!\\)\b(-?(?:\d{1,3}(?:,\d{3})+)(?:\.\d+)?)\b')

# Number core for detection helpers
NUM_CORE = r'(?:\d{1,3}(?:,\d{3})+|\d+|\d?\.\d+)'

# Percent values (detection)
PERCENT_DETECT_RE = re.compile(rf'(?<!\w)[+-]?{NUM_CORE}\s*%')

# Dollar amounts (detection) — no capturing groups needed
DOLLAR_DETECT_RE = re.compile(
    rf'(?<!\w)(?:\(\s*)?(?:(?:US)?\$)\s*[+-]?{NUM_CORE}\s*(?:\))?',
    flags=re.IGNORECASE
)

# Dollar amounts (wrapping) — named capture for the whole token
DOLLAR_WRAP_RE = re.compile(
    r"""
    (?<!\\)                 # not already escaped \$
    (?<!\w)                 # not part of a word
    (?P<amount>             # <-- capture the full amount to wrap
      (?:\(\s*)?            # optional '(' for negatives
      (?:
         [+-]?\s*(?:US)?\$\s*    # -$ or -US$
        |(?:US)?\$\s*[+-]?\s*    # $- or US$-
      )
      (?:\d{1,3}(?:,\d{3})+|\d+)  # 1,234 or 1234
      (?:\.\d+)?                  # decimals
      (?:\s*\))?                  # optional ')'
    )
    """,
    re.IGNORECASE | re.VERBOSE
)

# Precompiled wrapping patterns for percentages / numbers
PERCENT_WRAP_RE  = re.compile(r'(?<!\\)\b(-?\d+(?:\.\d+)?)%')
GROUPED_WRAP_RE  = re.compile(r'(?<!\\)\b(-?(?:\d{1,3}(?:,\d{3})+)(?:\.\d+)?)\b')
PLAIN_NUM_WRAP_RE = re.compile(r'(?<!\\)\b(-?\d+(?:\.\d+)?)\b')


# ============================================================
# Small helpers
# ============================================================

def _math_spans(s: str):
    """Return list of (start, end) spans of existing math segments in s."""
    return [m.span() for m in MATH_SEG_RE.finditer(s)]

def _in_spans(spans, i: int) -> bool:
    """True if position i lies inside any (start, end) span."""
    return any(a <= i < b for a, b in spans)


# ============================================================
# Wrapping functions
# ============================================================

def wrap_basic_numbers(text: str) -> str:
    """
    Wrap percentages and comma-grouped numbers with MathJax delimiters.
    Leaves existing math (\(...\), \[...\], $...$, $$...$$) untouched.
    """
    if text is None:
        return None
    s = str(text)

    math_spans = _math_spans(s)

    # 1) 33% → \(33\%\)
    def repl_percent(m):
        return m.group(0) if _in_spans(math_spans, m.start()) else rf'\({m.group(1)}\%\)'
    s = PERCENT_WRAP_RE.sub(repl_percent, s)

    # 2) 3,242 (and larger like 1,234,567.89) → \(3,242\)
    # NOTE: uses the same math_spans snapshot, preserving your original logic.
    def repl_grouped(m):
        return m.group(0) if _in_spans(math_spans, m.start()) else rf'\({m.group(1)}\)'
    s = GROUPED_WRAP_RE.sub(repl_grouped, s)

    return s


def number_handler(text: str) -> str:
    """
    Wrap percentages, comma-grouped numbers, and plain numbers with MathJax.
    Keeps your original pass order and 'in-math' check behavior.
    """
    if text is None:
        return None
    s = str(text)

    math_spans = _math_spans(s)

    # 1) Percentages
    def repl_percent(m):
        return m.group(0) if _in_spans(math_spans, m.start()) else rf'\({m.group(1)}\%\)'
    s = PERCENT_WRAP_RE.sub(repl_percent, s)

    # 2) Comma-grouped numbers
    def repl_grouped(m):
        return m.group(0) if _in_spans(math_spans, m.start()) else rf'\({m.group(1)}\)'
    s = GROUPED_WRAP_RE.sub(repl_grouped, s)

    # 3) Plain numbers
    def repl_plain(m):
        return m.group(0) if _in_spans(math_spans, m.start()) else rf'\({m.group(1)}\)'
    s = PLAIN_NUM_WRAP_RE.sub(repl_plain, s)

    return s


def wrap_dollar_amounts(text: str) -> str:
    """
    Wrap dollar amounts with MathJax \( ... \).
      '$3.99' -> '\(\$3.99\)'
    Skips amounts already inside math or already escaped as '\$'.
    """
    if text is None:
        return None
    s = str(text)

    math_spans = _math_spans(s)

    def repl(m: re.Match) -> str:
        if _in_spans(math_spans, m.start()):
            return m.group(0)
        token = m.group('amount')              # named capture (stable)
        token_escaped = token.replace('$', r'\$')
        return rf'\({token_escaped}\)'

    return DOLLAR_WRAP_RE.sub(repl, s)


# ============================================================
# Detection helpers (booleans + finders)
# ============================================================

def contains_percent(text: str) -> bool:
    """True if text contains at least one percent value (e.g., 33%)."""
    return bool(PERCENT_DETECT_RE.search(str(text)))

def find_percents(text: str):
    """Return all percent matches as they appear in the text."""
    s = str(text)
    return [m.group(0) for m in PERCENT_DETECT_RE.finditer(s)]

def contains_big_numbers(text: str) -> bool:
    """True if text contains comma-grouped numbers (e.g., 1,234)."""
    return bool(BIG_NUMS_RE.search(str(text)))

def contains_dollar_amount(text: str) -> bool:
    """True if text contains a dollar amount (e.g., $1,234.56)."""
    return bool(DOLLAR_DETECT_RE.search(str(text)))

def find_dollar_amounts(text: str):
    """Return all dollar amount matches as they appear in the text."""
    s = str(text)
    return [m.group(0) for m in DOLLAR_DETECT_RE.finditer(s)]
