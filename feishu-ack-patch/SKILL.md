---
name: feishu-ack-patch
description: Patch OpenClaw built-in Feishu channel to support ACK reactions (processing indicator) via Feishu message reactions. Use when user wants Feishu “typing/processing” feedback using emoji reactions (e.g., ⏳/👀), especially after upgrading OpenClaw where the feature disappears because local edits under /opt/homebrew/lib/node_modules/openclaw were overwritten.
---

# Feishu ACK Reaction Patch

Run a safe(ish) local patch after an OpenClaw upgrade overwrites your Feishu ACK-reaction changes.

This patch:
- Enables `capabilities.reactions` for the built-in Feishu channel.
- Adds an inbound “ACK reaction” that reacts to the original inbound message using Feishu `im.messageReaction.create`.

## Apply patch

1) Run the patcher (from this skill folder):

```bash
python3 skills/local/feishu-ack-patch/scripts/patch_feishu_ack.py
```

2) Restart gateway:

```bash
openclaw gateway restart
```

## Configure ACK emoji

OpenClaw config:

- `messages.ackReaction`: set to `⏳` (or `👀` / `✅`)
- `messages.ackReactionScope`: usually `direct`

Note: Feishu reactions API uses `emoji_type` enums, not raw Unicode. The patcher maps:
- `⏳`/`⌛` → `THINKING` (default)
- `👀` → `THINKING`
- `✅` → `DONE`

To map `⏳` to a different Feishu `emoji_type` (example: `OneSecond`), re-run:

```bash
python3 skills/local/feishu-ack-patch/scripts/patch_feishu_ack.py \
  --emoji-type OneSecond
openclaw gateway restart
```

## Safety / rollback

The patcher writes timestamped backups to:

`~/.openclaw/patch-backups/feishu-ack/`

To rollback, restore the latest `.bak` files back to their original locations and restart.

## Notes

- This is version-fragile: it expects OpenClaw’s `dist/plugin-sdk/index.js` to contain a specific code shape. If the patcher errors with “does not match expected pattern”, the OpenClaw version changed and the patcher needs an update.
