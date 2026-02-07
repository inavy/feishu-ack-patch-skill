# feishu-ack-patch-skill

[English](README.md) | [中文](README.zh-CN.md)

An OpenClaw skill that patches the built-in Feishu channel to show a **processing indicator** using **message reactions** (ACK reaction on inbound messages).

This is a pragmatic local patch meant for deployments where OpenClaw upgrades overwrite local edits under:

- `/opt/homebrew/lib/node_modules/openclaw`

## What it does

- Enables `capabilities.reactions` for the built-in Feishu channel.
- Adds an inbound ACK reaction that reacts to the original inbound message using Feishu `im.messageReaction.create`.
- Optionally removes the ACK reaction after reply (if `messages.removeAckAfterReply=true`).
- Writes timestamped backups before patching.

## Install / Use

After installing/importing the skill, when the feature disappears after an upgrade, re-apply:

```bash
python3 skills/local/feishu-ack-patch/scripts/patch_feishu_ack.py
openclaw gateway restart
```

## Configure the ACK emoji

In OpenClaw config:

```json5
{
  "messages": {
    "ackReaction": "⏳",
    "ackReactionScope": "direct"
  }
}
```

**Note:** Feishu reactions API uses `emoji_type` enums (not raw Unicode). The patcher maps `⏳/⌛` to a configurable `emoji_type` (default: `THINKING`).

To change mapping (example: `OneSecond`):

```bash
python3 skills/local/feishu-ack-patch/scripts/patch_feishu_ack.py --emoji-type OneSecond
openclaw gateway restart
```

## Backups / Rollback

Backups are saved under:

- `~/.openclaw/patch-backups/feishu-ack/`

To rollback, restore the latest `.bak` files back to their original locations and restart the gateway.

## Risks

- This is **version-fragile** and patches OpenClaw’s compiled output (`dist/plugin-sdk/index.js`).
- If OpenClaw changes internal code structure, the patcher will refuse to patch with a “pattern does not match” error.

## Release artifact

- `dist/feishu-ack-patch.skill`
