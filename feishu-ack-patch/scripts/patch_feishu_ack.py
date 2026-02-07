#!/usr/bin/env python3
"""Patch OpenClaw built-in Feishu channel to support ACK reactions via message reactions.

This is a pragmatic, version-fragile patcher intended for local deployments.

Behavior:
- If the feature already exists, do nothing.
- Otherwise, patch two files under the OpenClaw installation:
  1) extensions/feishu/src/channel.ts: set capabilities.reactions = true
  2) dist/plugin-sdk/index.js: add ACK reaction create/delete around Feishu inbound handling

The patch is designed for OpenClaw 2026.2.x layouts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
from pathlib import Path


def backup(path: Path, backups_dir: Path) -> Path:
    backups_dir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = backups_dir / f"{path.name}.{ts}.bak"
    shutil.copy2(path, dst)
    return dst


def patch_channel_ts(channel_path: Path, backups_dir: Path) -> bool:
    s = channel_path.read_text(encoding="utf-8")
    if "reactions: true" in s:
        return False
    if "reactions: false" not in s:
        raise RuntimeError(f"Unexpected feishu channel.ts (no reactions flag found): {channel_path}")
    backup(channel_path, backups_dir)
    s2 = s.replace("reactions: false,", "reactions: true,")
    channel_path.write_text(s2, encoding="utf-8")
    return True


def patch_plugin_sdk_index(index_path: Path, backups_dir: Path, emoji_type: str) -> bool:
    s = index_path.read_text(encoding="utf-8")

    # Already patched?
    if "client.im.messageReaction.create" in s and "ACK reaction (\"processing\" indicator) via Feishu message reactions" in s:
        return False

    # Patch point 1: insert ACK create block.
    old1 = (
        "\tconst { onModelSelected, ...prefixOptions } = createReplyPrefixOptions({\n"
        "\t\tcfg,\n"
        "\t\tagentId: resolveSessionAgentId({ config: cfg }),\n"
        "\t\tchannel: \"feishu\",\n"
        "\t\taccountId\n"
        "\t});\n"
        "\tawait dispatchReplyWithBufferedBlockDispatcher({"
    )

    new1 = (
        "\tconst agentId = resolveSessionAgentId({ config: cfg });\n"
        "\tconst { onModelSelected, ...prefixOptions } = createReplyPrefixOptions({\n"
        "\t\tcfg,\n"
        "\t\tagentId,\n"
        "\t\tchannel: \"feishu\",\n"
        "\t\taccountId\n"
        "\t});\n\n"
        "\t// ACK reaction (\"processing\" indicator) via Feishu message reactions.\n"
        "\t// Feishu expects emoji_type enums (not raw unicode emoji).\n"
        "\tconst ackReactionScope = cfg.messages?.ackReactionScope ?? \"group-mentions\";\n"
        "\tconst removeAckAfterReply = cfg.messages?.removeAckAfterReply ?? false;\n"
        "\tconst ackReaction = resolveAckReaction(cfg, agentId);\n"
        "\tconst mapAckEmojiToFeishuEmojiType = (emoji) => {\n"
        "\t\tconst value = String(emoji ?? \"\").trim();\n"
        "\t\tif (!value) return null;\n"
        f"\t\tif (value === \"⏳\" || value === \"⌛\") return \"{emoji_type}\";\n"
        "\t\tif (value === \"👀\") return \"THINKING\";\n"
        "\t\tif (value === \"✅\") return \"DONE\";\n"
        "\t\treturn \"THINKING\";\n"
        "\t};\n"
        "\tconst shouldAck = Boolean(ackReaction && shouldAckReaction({\n"
        "\t\tscope: ackReactionScope,\n"
        "\t\tisDirect: !isGroup,\n"
        "\t\tisGroup,\n"
        "\t\tisMentionableGroup: isGroup,\n"
        "\t\trequireMention: true,\n"
        "\t\tcanDetectMention: true,\n"
        "\t\teffectiveWasMentioned: wasMentioned,\n"
        "\t\tshouldBypassMention: false\n"
        "\t}));\n"
        "\tlet ackReactionId = \"\";\n"
        "\tconst ackReactionPromise = shouldAck ? (async () => {\n"
        "\t\ttry {\n"
        "\t\t\tconst emojiType = mapAckEmojiToFeishuEmojiType(ackReaction);\n"
        "\t\t\tif (!emojiType) return false;\n"
        "\t\t\tconst res = await client.im.messageReaction.create({\n"
        "\t\t\t\tpath: { message_id: message.message_id },\n"
        "\t\t\t\tdata: { reaction_type: { emoji_type: emojiType } }\n"
        "\t\t\t});\n"
        "\t\t\tif (res?.code !== 0) return false;\n"
        "\t\t\tackReactionId = res?.data?.reaction_id ?? \"\";\n"
        "\t\t\treturn Boolean(ackReactionId);\n"
        "\t\t} catch (err) {\n"
        "\t\t\tlogVerbose(`feishu ack reaction failed: ${String(err)}`);\n"
        "\t\t\treturn false;\n"
        "\t\t}\n"
        "\t})() : null;\n\n"
        "\tawait dispatchReplyWithBufferedBlockDispatcher({"
    )

    if old1 not in s:
        raise RuntimeError(
            "OpenClaw plugin-sdk index.js does not match expected pattern for patch insertion. "
            "This patcher likely needs an update for your OpenClaw version."
        )

    # Patch point 2: insert optional reaction delete at end of processFeishuMessage.
    old2 = "\t});\n\tif (streamingSession?.isActive()) await streamingSession.close();\n}"
    new2 = (
        "\t});\n"
        "\tif (streamingSession?.isActive()) await streamingSession.close();\n\n"
        "\t// Optionally remove the ACK reaction after the reply is finished.\n"
        "\tif (removeAckAfterReply && ackReactionPromise) {\n"
        "\t\tconst didAck = await ackReactionPromise;\n"
        "\t\tif (didAck && ackReactionId) {\n"
        "\t\t\ttry {\n"
        "\t\t\t\tawait client.im.messageReaction.delete({\n"
        "\t\t\t\t\tpath: { message_id: message.message_id, reaction_id: ackReactionId }\n"
        "\t\t\t\t});\n"
        "\t\t\t} catch (err) {\n"
        "\t\t\t\tlogVerbose(`feishu remove ack reaction failed: ${String(err)}`);\n"
        "\t\t\t}\n"
        "\t\t}\n"
        "\t}\n"
        "}"
    )

    backup(index_path, backups_dir)
    s = s.replace(old1, new1)
    if old2 not in s:
        raise RuntimeError(
            "OpenClaw plugin-sdk index.js does not match expected pattern for patch end insertion. "
            "The patch may be partially applied; restore from backup and update the patcher."
        )
    s = s.replace(old2, new2)

    index_path.write_text(s, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--openclaw-root",
        default="/opt/homebrew/lib/node_modules/openclaw",
        help="OpenClaw install root (default: /opt/homebrew/lib/node_modules/openclaw)",
    )
    ap.add_argument(
        "--emoji-type",
        default="THINKING",
        help='Feishu emoji_type for ⏳/⌛ mapping (default: THINKING; alternatives include OneSecond, Typing, OnIt, etc.)',
    )
    ap.add_argument(
        "--backups-dir",
        default=str(Path.home() / ".openclaw" / "patch-backups" / "feishu-ack"),
        help="Where to store backups",
    )

    args = ap.parse_args()
    root = Path(args.openclaw_root)
    backups_dir = Path(args.backups_dir)

    channel_path = root / "extensions" / "feishu" / "src" / "channel.ts"
    index_path = root / "dist" / "plugin-sdk" / "index.js"

    if not channel_path.exists():
        raise SystemExit(f"Missing: {channel_path}")
    if not index_path.exists():
        raise SystemExit(f"Missing: {index_path}")

    changed = False
    changed |= patch_channel_ts(channel_path, backups_dir)
    changed |= patch_plugin_sdk_index(index_path, backups_dir, args.emoji_type)

    if changed:
        print("Patched OpenClaw Feishu ACK reactions successfully.")
        print(f"Backups saved under: {backups_dir}")
    else:
        print("No changes needed (already patched).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
