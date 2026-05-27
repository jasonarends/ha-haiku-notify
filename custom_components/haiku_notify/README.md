# Haiku Notify

Wraps an existing Home Assistant `notify.*` service with an LLM rephrasing layer.

Each call is routed through the user's existing **Anthropic AI integration** (via the `ai_task.generate_data` service) along with the last few messages from the same source, so reminder chains stop reading like:

> Reminder 1 of 6 — washer door still hasn't been opened
> Reminder 2 of 6 — washer door still hasn't been opened
> Reminder 3 of 6 — washer door still hasn't been opened
> ...

and instead vary their phrasing naturally while preserving every concrete data point (names, times, numbers, counters, URLs).

## Requirements

- Home Assistant with the [Anthropic Conversation / AI Task integration](https://www.home-assistant.io/integrations/anthropic/) already set up.
- An `ai_task.*` entity exposed by that integration (Haiku is recommended for cost/latency).
- An existing notify service to forward to (e.g. `notify.discord_automations`).

## Installation

### Manual

Copy `custom_components/haiku_notify/` to `<config>/custom_components/haiku_notify/` in your Home Assistant install and restart.

### HACS (custom repository)

Add this repo (`jasonarends/home-assistant-automations`) as a custom repository in HACS under the "Integration" category, install **Haiku Notify**, then restart Home Assistant.

## Configuration

1. **Settings → Devices & Services → Add Integration → "Haiku Notify"**.
2. Fill in:
   - **Service name** — what the registered service will be called (e.g. `haiku_discord` → registers `notify.haiku_discord`).
   - **Wrapped service** — the full notify service to forward rephrased messages to (e.g. `notify.discord_automations`).
   - **AI Task entity** — the LLM entity to use for rephrasing.
   - **History size** — how many recent messages to send as context (default 8).
   - **Instructions** — the rephrasing prompt sent to the AI. The default works for general use; tweak it to change tone, add household-specific rules, or constrain behavior further.

You can add multiple entries to wrap multiple notify services. To change instructions later: **Settings → Devices & Services → Haiku Notify → Configure**.

## Use in automations

Drop-in replace the notify service name. Add `data.source_id` to scope the rephrasing history bucket (so unrelated automations don't pollute each other's context).

```yaml
# Before
- service: notify.discord_automations
  data:
    message: "🧺 Washer cycle finished. Power is idle (0.0 W). Move laundry to the dryer when you get a chance."

# After
- service: notify.haiku_discord
  data:
    message: "🧺 Washer cycle finished. Power is idle (0.0 W). Move laundry to the dryer when you get a chance."
    data:
      source_id: washer_done
```

A reminder loop should reuse the same `source_id` for all reminders:

```yaml
- service: notify.haiku_discord
  data:
    message: "⏰ Laundry reminder. The washer finished and the door still hasn't been opened. (Reminder {{ count }} of 6)"
    data:
      source_id: washer_done_reminder
```

Any extra keys you pass under `data:` (besides `source_id`) are forwarded to the wrapped service unchanged, so per-channel Discord options etc. keep working.

## Failure behavior

If `ai_task.generate_data` errors, times out (15s), or returns empty text, the **original message is forwarded unchanged**. Notifications are never dropped.

## How history is stored

Per config entry, in HA's `Store` API (`.storage/haiku_notify_history_<entry_id>`). Survives restarts. One bucket per `source_id`.

## Default rephrasing instructions

```
You rephrase a home-automation notification so it does not repeat the exact
wording of recent prior notifications from the same source. Output one short
message (one or two sentences max), warm but concise, like a person nudging a
housemate.

HARD RULES:
- Preserve every concrete data point from the current message verbatim: names,
  times, numbers, wattages, URLs, reset links, counters such as "1 of 6", emoji.
- Do not add new facts, opinions, or speculation.
- Do not include preamble, quotes, JSON, or any prefix like "Here is".
- Vary phrasing, sentence structure, and tone vs. the recent messages shown.
- If you cannot rephrase safely while preserving every data point, output the
  current message exactly as given.
```
