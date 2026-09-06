"""
Filter button-syntax parser (ported from the reference Filter-Bot-Dev
plugins/utils.py `parser()` / BTN_URL_REGEX, same syntax and behaviour):

    [Google](buttonurl:https://google.com)
    [Google](buttonurl:https://google.com:same)   -> same row as the previous button
    [Click me](buttonalert:This is a popup message)

The reference implementation stores buttons as a Python-repr string of real
InlineKeyboardButton objects and reconstructs them with eval() when sending
a filter reply. We keep the exact same button syntax and end-user behaviour,
but store buttons as plain JSON-safe dicts instead - MongoDB can't store
InlineKeyboardButton objects anyway, and this avoids ever eval()'ing text
that came from a stored document. Alert popups are still referenced as
"alertmessage:{index}:{keyword}" in callback_data, matching the reference.
"""

import re
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

BTN_URL_REGEX = re.compile(
    r"(\[([^\[]+?)\]\((buttonurl|buttonalert):(?:/{0,2})(.+?)(:same)?\))"
)


def parse_buttons(text: str, keyword: str = ""):
    """
    Splits `text` into (clean_text, button_rows, alerts).
    - button_rows: list of rows, each row a list of {"text":.., "url":..}
      (url button) or {"text":.., "alert_index": i} (alert button) dicts.
    - alerts: list of alert popup strings, indexed by position (matches
      the alert_index stored in the button dict).
    """
    if not text:
        return text, [], []

    clean_text = ""
    prev = 0
    rows = []
    alerts = []

    for match in BTN_URL_REGEX.finditer(text):
        n_escapes = 0
        check_pos = match.start(1) - 1
        while check_pos >= 0 and text[check_pos] == "\\":
            n_escapes += 1
            check_pos -= 1

        if n_escapes % 2 == 0:
            btn_text = match.group(2)
            btn_type = match.group(3)
            btn_data = match.group(4)
            same_line = bool(match.group(5))

            clean_text += text[prev:match.start(1)]
            prev = match.end(1)

            if btn_type == "buttonurl":
                button = {"text": btn_text, "url": btn_data.replace(" ", "")}
            else:  # buttonalert
                alerts.append(btn_data)
                button = {"text": btn_text, "alert_index": len(alerts) - 1}

            if same_line and rows:
                rows[-1].append(button)
            else:
                rows.append([button])
        else:
            clean_text += text[prev:check_pos + 1]
            prev = match.start(1)

    clean_text += text[prev:]
    return clean_text.strip(), rows, alerts


def build_markup(button_rows, keyword: str = ""):
    """Turns stored button rows back into a pyrogram InlineKeyboardMarkup, or None if empty."""
    if not button_rows:
        return None

    keyboard = []
    for row in button_rows:
        line = []
        for btn in row:
            if "url" in btn:
                line.append(InlineKeyboardButton(btn["text"], url=btn["url"]))
            else:  # alert button
                line.append(InlineKeyboardButton(
                    btn["text"],
                    callback_data=f"alertmessage:{btn['alert_index']}:{keyword}"
                ))
        keyboard.append(line)
    return InlineKeyboardMarkup(keyboard)


def serialize_existing_markup(inline_keyboard):
    """
    Converts a real InlineKeyboardMarkup.inline_keyboard (e.g. from a message
    someone replied to that already has buttons) into the same storable
    format as parse_buttons(). URL buttons are kept; buttons of other types
    (switch_inline_query, callback_data from another bot, etc.) are dropped
    since we can't meaningfully replay them from a filter.
    """
    if not inline_keyboard:
        return []
    rows = []
    for row in inline_keyboard:
        line = []
        for btn in row:
            if getattr(btn, "url", None):
                line.append({"text": btn.text, "url": btn.url})
        if line:
            rows.append(line)
    return rows
