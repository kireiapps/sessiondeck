<p align="center">
  <img src="assets/banner.jpg" alt="Session Deck Banner" width="100%">
</p>

# 🃏 Session Deck

> **Control. Observe. Purge.**

Turn forgotten Hermes sessions into a living deck of knowledge.

Session Deck transforms old Hermes conversations into an interactive deck of cards. Every card represents a past conversation waiting for a decision. Instead of letting sessions accumulate forever, you decide what deserves to be forgotten, remembered, or transformed into reusable knowledge.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)
![Hermes Skill](https://img.shields.io/badge/Hermes-Skill-000000?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-success?style=flat-square)

---

## 🃏 How it Works

Every turn starts the same way.

```text
🎴 Draw a random Session Card
            │
            ▼
   Read the session preview
            │
            ▼
      Make a decision
```

If the preview isn't enough, inspect the full conversation first.

```text
👁️ Inspect
Open the complete conversation history,
then return to the decision.
```

Then choose one of the five actions.

| Action | Description |
|--------|-------------|
| 🔥 **Discard** | Permanently delete the session. |
| ✨ **Distill** | Extract reusable knowledge and convert it into a Skill. |
| 🧠 **Imprint** | Store important information as permanent Memory instead of creating a Skill. |
| 👁️ **Inspect** | Open the full conversation before making a decision. |
| ⏭️ **Pass** | Keep the session exactly as it is and draw another card. |

---

## 💡 Why?

Most AI conversations slowly become digital clutter.

Some deserve to be forgotten.

Some contain workflows worth turning into reusable Skills.

Some hold long-term preferences that belong in Memory.

Session Deck lets you curate your AI's history instead of endlessly collecting it.

Every session becomes a conscious decision rather than forgotten context.

---

## 🚀 Installation

```bash
cp -r session-deck ~/.hermes/skills/automation/session-deck
```

Verify the installation:

```bash
hermes skills list
```

---

## ▶️ Usage

```bash
python3 scripts/session_deck.py pick
```

Or simply ask your Hermes agent:

```text
Start Session Deck.

Draw a random card.

Wait for my decision.

Discard
Distill
Imprint
Inspect
Pass

Repeat.
```

---

## ⚙️ Philosophy

AI memory shouldn't grow forever.

It should be curated.

Every discarded session removes noise.

Every distilled session creates a reusable capability.

Every imprint strengthens long-term memory.

Every decision makes your AI a little better than yesterday.

---

## 📜 License

MIT License

Use it. Fork it. Improve it. Build on it.
