"""Constants for the Haiku Notify integration."""

DOMAIN = "haiku_notify"

CONF_NAME = "name"
CONF_WRAPPED_SERVICE = "wrapped_service"
CONF_AI_TASK_ENTITY = "ai_task_entity"
CONF_HISTORY_SIZE = "history_size"
CONF_INSTRUCTIONS = "instructions"
CONF_PERSONAS_ENABLED = "personas_enabled"
CONF_PERSONAS = "personas"

DEFAULT_HISTORY_SIZE = 8
MAX_HISTORY_SIZE = 25
DEFAULT_PERSONAS_ENABLED = True
DEFAULT_PERSONAS = (
    "sassy teenage daughter who's mildly inconvenienced\n"
    "grumpy old man who just wants some peace and quiet\n"
    "overly enthusiastic life coach\n"
    "corporate middle manager addicted to synergy\n"
    "pirate, but a domestic one\n"
    "exhausted parent on their third cup of coffee"
)

STORAGE_VERSION = 1
STORAGE_KEY_TEMPLATE = "haiku_notify_history_{entry_id}"

DATA_SOURCE_ID = "source_id"

DEFAULT_INSTRUCTIONS = """\
You rephrase a home-automation notification so it does not repeat the exact \
wording of recent prior notifications from the same source. Output one short \
message (one or two sentences max), warm but concise, like a person nudging a \
housemate.

HARD RULES:
- Preserve every concrete data point from the current message verbatim: names, \
times, numbers, wattages, URLs, reset links, counters such as "1 of 6", emoji.
- Do not add new facts, opinions, or speculation.
- Do not include preamble, quotes, JSON, or any prefix like "Here is".
- Vary phrasing, sentence structure, and tone vs. the recent messages shown.
- If you cannot rephrase safely while preserving every data point, output the \
current message exactly as given.
"""
