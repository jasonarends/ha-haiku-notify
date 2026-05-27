# 🌀 Haiku Notify

<p align="center"><img src="icon.png" alt="Haiku Notify" width="128" height="128"/></p>

> Stop your Home Assistant reminders from reading like a script being recited verbatim.

Drop-in replacement for any `notify.*` service. Each message is routed through your **existing Anthropic AI integration** (via `ai_task.generate_data`) along with the last few messages from the same source, so chained reminders vary phrasing naturally — while preserving every concrete data point (names, times, numbers, counters, URLs).

[![GitHub Release][releases-shield]][releases]
[![GitHub License][license-shield]][license]
[![GitHub Last Commit][lastcommit-shield]][commits]
[![HACS Custom][hacs-shield]][hacs]

* * *

## 🥲 The problem

```
🧺 Washer cycle finished. Move laundry to the dryer when you get a chance.
⏰ Laundry reminder. The washer finished and the door still hasn't been opened. (Reminder 1 of 6)
⏰ Laundry reminder. The washer finished and the door still hasn't been opened. (Reminder 2 of 6)
⏰ Laundry reminder. The washer finished and the door still hasn't been opened. (Reminder 3 of 6)
⏰ Laundry reminder. The washer finished and the door still hasn't been opened. (Reminder 4 of 6)
⏰ Laundry reminder. The washer finished and the door still hasn't been opened. (Reminder 5 of 6)
⏰ Laundry reminder. The washer finished and the door still hasn't been opened. (Reminder 6 of 6)
☕ Coffee is ready! Brewer power dropped to the warmer range (51.0 W).
☕ Coffee is ready! Brewer power dropped to the warmer range (52.0 W).
```

## 😌 What you get instead

```
🧺 Washer cycle finished. Move laundry to the dryer when you get a chance.
⏰ The washer's been sitting unopened for a bit — laundry's ready to move. (Reminder 1 of 6)
⏰ Still no movement on the washer door. (Reminder 2 of 6)
⏰ Friendly nudge — washer still waiting. (Reminder 3 of 6)
⏰ Laundry's been done a while; mind grabbing it? (Reminder 4 of 6)
⏰ Heads up — washer's been ready for a bit. (Reminder 5 of 6)
⏰ Last call on the washer load. (Reminder 6 of 6)
☕ Coffee is ready! Brewer dropped to the warmer range (51.0 W).
☕ Fresh pot just settled into the warmer (52.0 W).
```

Same data, varied delivery — like a person nudging you, not a service printing the same line.

* * *

## ✨ Features

| | |
|---|---|
| 🪶 **Drop-in replacement** | `service: notify.haiku_<name>` takes the same payload as the service it wraps |
| 🧠 **Uses your existing AI** | No new API key — calls `ai_task.generate_data` on an entity you already configured |
| 🗂️ **Per-source history** | Bucketed by `data.source_id`, persisted via HA's `Store` API (survives restarts) |
| 🖊️ **UI-editable prompt** | Tweak the rephrasing instructions from the integration's options page, no file edits |
| 🛡️ **Fails safe** | Any AI error / timeout / empty response → forward the **original** message untouched |
| 🔁 **Wrap many services** | Add multiple entries to wrap different notify targets (Discord, mobile, persistent, etc.) |

* * *

## ⚡ Quick Start

### 1. Install via HACS

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=jasonarends&repository=ha-haiku-notify&category=Integration" target="_blank" rel="noopener noreferrer"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." /></a>

```
HACS → ⋮ (top right) → Custom repositories
URL: https://github.com/jasonarends/ha-haiku-notify   |   Type: Integration
→ Download "Haiku Notify" → Restart HA
```

### 2. Add the integration

<a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=haiku_notify" target="_blank" rel="noopener noreferrer"><img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Open your Home Assistant instance and start setting up a new integration." /></a>

```
Settings → Devices & Services → Add Integration → "Haiku Notify"
```

Fill in: service name, wrapped notify service, AI Task entity, history size, (optional) custom instructions.

### 3. Update one automation

```yaml
# Before
- service: notify.discord_automations
  data:
    message: "🧺 Washer cycle finished. Move laundry to the dryer."

# After
- service: notify.haiku_discord
  data:
    message: "🧺 Washer cycle finished. Move laundry to the dryer."
    data:
      source_id: washer_done
```

That's it. Fire a few reminders and watch the wording change. 🎉

* * *

## 🔑 Requirements

- Home Assistant **2025.7** or newer (needs the `ai_task` integration)
- [Anthropic Conversation / AI Task integration](https://www.home-assistant.io/integrations/anthropic/) already configured
- An `ai_task.*` entity exposed by that integration — **Haiku is recommended** for cost & latency
- An existing notify service to forward to (e.g. `notify.discord_automations`, `notify.mobile_app_<phone>`)

* * *

## 🔧 Configuration

All configuration happens through the integration UI. Add an entry per `notify.*` service you want to wrap.

| Field | Required | Notes |
|---|---|---|
| **Service name** | yes | Registered as `notify.<name>`. e.g. `haiku_discord` → `notify.haiku_discord`. |
| **Wrapped service** | yes | Full notify service to forward rephrased messages to. e.g. `notify.discord_automations`. |
| **AI Task entity** | yes | Which `ai_task.*` entity to call. Use a Haiku-configured one if possible. |
| **History size** | no (default `8`) | How many recent messages per `source_id` to include as context. Max `25`. |
| **Instructions** | no | The rephrasing prompt. Default prefilled — tweak tone, add household-specific rules, etc. |

Change any of these later via **Settings → Devices & Services → Haiku Notify → Configure**. Saving reloads the integration.

### Recommended AI Task entity settings

Tune your dedicated AI Task entity for this use case:

| Setting | Recommended | Why |
|---|---|---|
| Model | **Claude Haiku** | Plenty smart for rephrasing; cheap; fast |
| Max tokens in response | **200** | One or two sentences max — cap prevents runaway |
| Thinking budget | **0** (or lowest) | No thinking needed for a tiny rephrase |
| Caching strategy | **System prompt** | Modest help during reminder bursts |
| Code execution | off | Not needed |
| Web search | off | Would tempt the model to "verify" data — bad |
| Include home location | off | Irrelevant to notification text |

* * *

## 📝 Usage

### Basic call

```yaml
- service: notify.haiku_discord
  data:
    message: "🐕 Goomba was just let out — timer reset."
    data:
      source_id: dog_let_out_goomba
```

### Reminder chains share a `source_id`

All reminders in the chain should use the **same `source_id`** so each iteration sees the prior ones:

```yaml
- service: notify.haiku_discord
  data:
    message: >-
      ⏰ Laundry reminder. The washer finished and the door still hasn't been
      opened. (Reminder {{ count }} of 6)
    data:
      source_id: washer_done_reminder
```

### Title, target, and extra data pass through

Any keys other than `source_id` under `data:` are forwarded to the wrapped service unchanged:

```yaml
- service: notify.haiku_discord
  data:
    title: "Washer alert"
    message: "🧺 Cycle done."
    target: "#automations"
    data:
      source_id: washer_done
      embed: { color: 0x5865F2 }   # forwarded as-is to Discord
```

### What gets sent to the AI

```
<your instructions, default or custom>

Recent prior notifications from this source (oldest first):
- <history msg 1>
- <history msg 2>
- ...

CURRENT MESSAGE TO REPHRASE:
<the new message>
```

* * *

## 🛡️ Failure behavior

If **anything** goes wrong — `ai_task.generate_data` errors, times out (15 s), or returns empty/unreadable text — the **original message is forwarded unchanged**. Notifications are never silently dropped.

The forward step itself (to the wrapped `notify.*` service) does propagate errors as normal, so a misconfigured wrapped service will surface in your HA log.

* * *

## 💾 How history is stored

- One JSON blob per config entry in `.storage/haiku_notify_history_<entry_id>` (HA's [`Store` API](https://developers.home-assistant.io/docs/api/storage)).
- Keys are your `source_id` values; values are lists of the last N raw messages.
- Survives restarts and reboots.
- Trimmed to `history_size` on every write.

To wipe history for one source: edit the JSON file and restart HA (or remove and re-add the config entry).

* * *

## 🎛️ Default rephrasing instructions

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

Override from the integration's **Configure** page. Common tweaks: change tone (snarky, dry, formal), add household-specific glossary, restrict emoji use.

* * *

## ❓ FAQ

<details>
<summary><b>Does it work without a <code>source_id</code>?</b></summary>

Yes — all calls without `source_id` share a single `_default` bucket. Fine for casual use, but reminders from unrelated automations will start influencing each other's phrasing. Set explicit `source_id`s for anything that fires repeatedly.

</details>

<details>
<summary><b>What if I want one bucket per dog / per child / per room?</b></summary>

Just template the `source_id`:

```yaml
data:
  source_id: "dog_let_out_{{ trigger.event.data.dog_name }}"
```

</details>

<details>
<summary><b>Will it cost much?</b></summary>

For Haiku (~$1/M input tokens, ~$5/M output) on short notifications (~500 input tokens, ~50 output tokens per call), each rephrase is well under a hundredth of a cent. A few hundred notifications a day is still pennies a month.

</details>

<details>
<summary><b>Can I disable rephrasing temporarily without changing automations?</b></summary>

Yes — in **Configure**, swap the AI Task entity for one that errors (or remove the integration entirely). All wrapped calls fall back to the original message and continue working.

</details>

<details>
<summary><b>Does the first message in a new <code>source_id</code> bucket get rephrased?</b></summary>

No — there's no history yet, so it's forwarded unchanged. Rephrasing kicks in on the 2nd message onward.

</details>

<details>
<summary><b>Can I use a non-Anthropic model?</b></summary>

Any `ai_task.*` entity works (Google, OpenAI, etc. — anything that implements the `ai_task` platform). Anthropic + Haiku is just the recommended pairing for cost/latency.

</details>

* * *

## 📜 License

MIT — see [LICENSE](LICENSE).

* * *

[releases-shield]: https://img.shields.io/github/v/release/jasonarends/ha-haiku-notify?style=for-the-badge
[releases]: https://github.com/jasonarends/ha-haiku-notify/releases
[license-shield]: https://img.shields.io/github/license/jasonarends/ha-haiku-notify?style=for-the-badge
[license]: https://github.com/jasonarends/ha-haiku-notify/blob/main/LICENSE
[lastcommit-shield]: https://img.shields.io/github/last-commit/jasonarends/ha-haiku-notify?style=for-the-badge
[commits]: https://github.com/jasonarends/ha-haiku-notify/commits/main
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
