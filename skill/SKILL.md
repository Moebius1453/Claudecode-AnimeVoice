---
name: say
description: 用本地 VOICEVOX 日语音色出声提醒、喊人或按需说一句。适用于用户需要听见提醒而不只是看到文字的场景，也可通过 /say 调用。
argument-hint: '"日本語のテキスト" [--volume 1.2]'
---

# say

安装时将本文中的 `VOICE_PROJECT_DIR` 替换为语音项目的绝对路径。它是文档占位符，不是环境变量。引擎路径由项目旁的 `config.local.json` 或 `VOICEVOX_ENGINE_EXE` 配置，接入方法见项目 README。

## 出声原则

文字负责完整信息，声音用于提醒和简短表达。用户在等结果、需要回来确认操作、需要听见提醒或明确要求说话时可以调用；常规技术交流不逐条朗读，不检测键鼠，不安装常驻调度。

输入使用自然的日语短句。若原意是中文，由 Claude 改写为日文再调用；程序不翻译，中文输入可能被按日语错误解析。将这视为 Claude 的语音输出，不描述成另一个人在替 Claude 喊人。

## 调用

使用绝对路径，避免依赖当前工作目录：

```powershell
python "VOICE_PROJECT_DIR/say.py" "ねえ、聞こえる？"
python "VOICE_PROJECT_DIR/say_timer.py" -S done
python "VOICE_PROJECT_DIR/say_timer.py" -S comeback --cooldown 30
python "VOICE_PROJECT_DIR/say_timer.py" -S missed --cooldown 60
python "VOICE_PROJECT_DIR/say_timer.py" --list
```

默认音色是 `47 = ナースロボ＿タイプＴ / ノーマル`，可用 `-s 14` 选择冥鳴ひまり。`--speakers` 查询当前引擎音色。支持 `--volume`、`--speed`、`--pitch`、`--intonation`、`-f`、`--out` 和 `--keep-engine`，完整说明见 README。

未指定的合成参数保留引擎默认值，不要统一补成 `1.0`。引擎默认按需启动、调用结束关闭；已经运行的引擎不会被本程序关闭。

## 权限提醒

权限请求弹出时由 `PermissionRequest` hook 调用 `hook_notify.py`，冷却 30 秒。安装 skill 不等于安装 hook，配置示例在 `hooks.example.json`。

在原验证环境中，权限超时没有触发尝试过的失败 hook。若工具返回 `Permission request timed out`，可主动调用 `missed` 场景，冷却 60 秒；不要声称这是一套保证触发的自动超时通知。

主动出声的命令应在用户授权的最小范围权限内运行。不要擅自扩大权限，也不要在等待权限时不断重试出声命令。避免在命令前加 `cd`，它可能改变命令前缀匹配，导致喊人的命令也等待授权。

CC Switch 等工具可能重写用户级 `~/.claude/settings.json` 并删除手工 hook。优先按 README 把 hook 合并进实际工作项目的 `.claude/settings.local.json`，不覆盖其他设置，也不在多个作用域重复配置。用户级 `~/.claude/settings.local.json` 曾在作者环境生效，但不是官方位置表列出的标准用户级入口。

## 维护

- 台词和场景音量：修改 `lines.py`；保留用户认可的台词，修改前确认范围。
- hook 事件和冷却：修改 `hook_notify.py` 的 `BEHAVIOR`；示例只挂 `PermissionRequest`。
- 音色：调用时用 `-s`，或修改 `say.py` 的 `DEFAULT_SPEAKER`。
- 试听：运行 `render_preview.py 场景名 --out-dir 输出目录`，会覆盖同名编号 WAV，并保留引擎。
- 诊断：查看项目的 `_hook.log`；冷却时跳过是预期行为。日志可能包含工作内容，分享前检查隐私。

台词挑选避开近期记录，但只持久化最近 12 句，不保证全池遍历。`say_timer.py` 是一次性触发脚本，不是独立定时调度器。不同场景并发调用的引擎生命周期未作完全隔离。

使用或发布生成语音时，遵守 VOICEVOX 及所选角色声库的条款和署名要求。本项目代码许可证不替代声库许可。
