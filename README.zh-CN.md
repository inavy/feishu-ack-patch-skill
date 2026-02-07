# feishu-ack-patch-skill（飞书 ACK 表情补丁 Skill）

这是一个用于 **OpenClaw** 的 skill：当你在飞书里给机器人发消息后，在机器人正式回复前，先给你的那条消息加一个 **表情回应（reaction）** 作为“处理中/正在处理”的 ACK（处理指示）。

适用于以下场景：
- 你希望在飞书里看到机器人“已收到/处理中”的可视反馈（类似 typing indicator）。
- 你曾经手工修改过 OpenClaw 安装目录（例如 `/opt/homebrew/lib/node_modules/openclaw`）来实现该功能，但 **升级 OpenClaw 后修改会被覆盖**，需要一键补回。

> 说明：这是一个“本地补丁”方案，会修改 OpenClaw 已安装的文件，并在修改前自动备份。

---

## 这个 skill 做了什么

- 将内置 Feishu channel 的 `capabilities.reactions` 设为启用。
- 在飞书入站消息处理时调用飞书接口 `im.messageReaction.create` 给**原消息**加一个 reaction。
- （可选）在回复完成后删除该 reaction（如果你开启了 `messages.removeAckAfterReply=true`）。
- 修改前会写入带时间戳的备份文件，方便回滚。

---

## 使用方法

当你升级 OpenClaw 后发现 ACK 表情功能消失，执行：

```bash
python3 skills/local/feishu-ack-patch/scripts/patch_feishu_ack.py
openclaw gateway restart
```

如果脚本提示“pattern 不匹配/找不到预期片段”，说明 OpenClaw 新版本内部结构变了，需要更新补丁脚本。

---

## 配置 ACK 表情

在 OpenClaw 配置里设置：

```json5
{
  "messages": {
    "ackReaction": "⏳",
    "ackReactionScope": "direct"
  }
}
```

注意：飞书的 reaction API 需要传 `emoji_type`（枚举），不是直接传 Unicode 表情字符。
补丁脚本会把 `⏳/⌛` 映射为可配置的 `emoji_type`（默认 `THINKING`）。

如果你想把 `⏳` 映射到其它 `emoji_type`（例如 `OneSecond`），执行：

```bash
python3 skills/local/feishu-ack-patch/scripts/patch_feishu_ack.py --emoji-type OneSecond
openclaw gateway restart
```

---

## 备份与回滚

脚本会把被修改的文件备份到：

- `~/.openclaw/patch-backups/feishu-ack/`

回滚方式：把最新的 `.bak` 文件覆盖回原路径，然后重启 gateway：

```bash
openclaw gateway restart
```

---

## 风险提示

- 这是对 OpenClaw 安装目录的补丁，**版本敏感**。
- 它会修改 OpenClaw 的编译产物（例如 `dist/plugin-sdk/index.js`）。
- 如果 OpenClaw 升级后内部实现变化，脚本会拒绝打补丁，需要更新脚本。

---

## 发布包

仓库里包含一个可分发的 skill 包：

- `dist/feishu-ack-patch.skill`
