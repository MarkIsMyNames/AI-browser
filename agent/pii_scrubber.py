"""Scrub PII and credentials from text before it reaches the AI.

Uses phonenumbers (every country), stdlib email.utils and ipaddress — no
hand-rolled regex. Phone detection runs last so it cannot misidentify IPs or
credit-card numbers that happen to match some country's dialling format.
"""

import ipaddress
from email.utils import parseaddr
from phonenumbers import PhoneNumberMatcher, SUPPORTED_REGIONS

_PUNCT    = frozenset('.,;:()[]{}"\' ')
_IP_PUNCT = frozenset('.,;()[]{}"\' ')  # colons excluded — IPv6 starts with '::'

_PASS_KEYWORDS = frozenset({'password', 'passwd', 'pwd', 'pass', 'secret'})
_CRED_KEYWORDS = _PASS_KEYWORDS | frozenset({'api_key', 'apikey', 'api-key', 'token', 'bearer'})
_SEPARATORS    = frozenset(':=')


def _tokenise(text):
    result = []
    cursor = 0
    length = len(text)
    while cursor < length:
        while cursor < length and text[cursor].isspace():
            cursor += 1
        if cursor >= length:
            break
        word_end = cursor
        while word_end < length and not text[word_end].isspace():
            word_end += 1
        result.append((cursor, text[cursor:word_end]))
        cursor = word_end
    return result


def _trim(token, chars):
    left, right = 0, len(token)
    while left < right and token[left] in chars:
        left += 1
    while right > left and token[right - 1] in chars:
        right -= 1
    return left, token[left:right]


def _email_spans(text):
    spans = []
    for pos, token in _tokenise(text):
        if '@' not in token:
            continue
        offset, candidate = _trim(token, _PUNCT)
        _, addr = parseaddr(candidate)
        if '@' in addr:
            local, domain = addr.rsplit('@', 1)
            if local and '.' in domain:
                start = pos + offset
                spans.append((start, start + len(candidate), '[EMAIL]'))
    return spans


def _ip_spans(text):
    spans = []
    for pos, token in _tokenise(text):
        offset, candidate = _trim(token, _IP_PUNCT)
        if not candidate:
            continue
        try:
            ipaddress.ip_address(candidate)
            start = pos + offset
            spans.append((start, start + len(candidate), '[IP_ADDRESS]'))
        except ValueError:
            pass
    return spans


def _luhn_valid(digits):
    if not (13 <= len(digits) <= 19):
        return False
    total = 0
    for position, digit in enumerate(reversed(digits)):
        if position % 2 == 1:
            digit = digit * 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _cc_spans(text):
    spans = []
    cursor, length = 0, len(text)
    while cursor < length:
        if text[cursor].isdigit():
            start, digits, end = cursor, [], cursor
            while end < length:
                if text[end].isdigit():
                    digits.append(int(text[end]))
                    end += 1
                elif text[end] in ' -' and end + 1 < length and text[end + 1].isdigit():
                    end += 1
                else:
                    break
            if _luhn_valid(digits):
                spans.append((start, end, '[CREDIT_CARD]'))
            cursor = end
        else:
            cursor += 1
    return spans


def _ssn_spans(text):
    spans = []
    for pos, token in _tokenise(text):
        offset, candidate = _trim(token, _PUNCT)
        parts = candidate.split('-')
        if (len(parts) == 3
                and parts[0].isdigit() and len(parts[0]) == 3
                and parts[1].isdigit() and len(parts[1]) == 2
                and parts[2].isdigit() and len(parts[2]) == 4):
            start = pos + offset
            spans.append((start, start + len(candidate), '[SSN]'))
    return spans


def _credential_spans(text):
    spans = []
    tokens = _tokenise(text)

    for idx, (pos, token) in enumerate(tokens):
        word = token.lower().rstrip('.,;')

        keyword = next(
            (kw for kw in _CRED_KEYWORDS
             if word == kw or (word.startswith(kw) and len(word) > len(kw) and word[len(kw)] in _SEPARATORS)),
            None
        )
        if not keyword:
            continue

        suffix = word[len(keyword):]

        if suffix and suffix[0] in _SEPARATORS:
            if suffix[1:]:
                # e.g. password=hunter2
                spans.append((pos, pos + len(token), '[REDACTED_CREDENTIAL]'))
            elif idx + 1 < len(tokens):
                # e.g. password= <next token>
                next_pos, next_tok = tokens[idx + 1]
                spans.append((pos, next_pos + len(next_tok), '[REDACTED_CREDENTIAL]'))
        else:
            if idx + 1 >= len(tokens):
                continue
            next_pos, next_tok = tokens[idx + 1]
            next_word = next_tok.lower().strip('.,;')

            if next_word in _SEPARATORS or (next_word and next_word[0] in _SEPARATORS):
                # e.g. password : hunter2
                value = next_word.lstrip(':=').strip()
                if value:
                    spans.append((pos, next_pos + len(next_tok), '[REDACTED_CREDENTIAL]'))
                elif idx + 2 < len(tokens):
                    val_pos, val_tok = tokens[idx + 2]
                    spans.append((pos, val_pos + len(val_tok), '[REDACTED_CREDENTIAL]'))
            else:
                # Bare keyword — only redact if value looks like a credential, not plain English
                if keyword in _PASS_KEYWORDS:
                    if not (any(not c.isalpha() for c in next_word) or len(next_word) >= 8):
                        continue
                spans.append((pos, next_pos + len(next_tok), '[REDACTED_CREDENTIAL]'))

    return spans


def _phone_spans(text, claimed):
    seen, spans = set(), []
    for region in [None, *SUPPORTED_REGIONS]:
        for match in PhoneNumberMatcher(text, region):
            if any(match.start < e and match.end > s for s, e in claimed):
                continue
            key = (match.start, match.end)
            if key not in seen:
                seen.add(key)
                spans.append((match.start, match.end, '[PHONE]'))
    return spans


def _merge(spans):
    result = []
    for span in sorted(spans, key=lambda x: x[0]):
        if result and span[0] < result[-1][1]:
            continue
        result.append(span)
    return result


def scrub(text: str) -> str:
    # High-confidence detectors run first
    primary_spans = (
        _email_spans(text)
        + _ip_spans(text)
        + _cc_spans(text)
        + _credential_spans(text)
        + _ssn_spans(text)
    )

    # Phone runs last, skipping anything already matched above
    claimed = {(start, end) for start, end, _ in primary_spans}
    spans = _merge(primary_spans + _phone_spans(text, claimed))

    # Apply right-to-left so earlier indices stay valid
    for start, end, replacement in sorted(spans, key=lambda x: x[0], reverse=True):
        text = text[:start] + replacement + text[end:]

    return text
