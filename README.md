# Claudecode-AnimeVoice

中文 | [English](README.en.md)

面向 Claude Code 的本地日语语音提醒工具。基于 [VOICEVOX](https://voicevox.hiroshiba.jp/)，支持手动合成与播放、按场景选择台词，以及在权限请求时通过 hook 播放提醒。

语音合成在本地完成，无需额外 API Key。输入使用日文，翻译由调用方完成；VOICEVOX 引擎需单独安装。

已验证环境：Windows、Python 3.12、VOICEVOX 0.25.2。

以下步骤覆盖手动播放、hook 和 skill 接入。手动播放与模拟 hook 已在上述环境验证，独立干净环境安装及真实 hook 事件接入仍需确认。

## 快速开始

1. 安装 Python 3.10 或更新版本。
2. 自行安装 VOICEVOX，找到引擎可执行文件 `vv-engine/run.exe`。
3. 将 `config.example.json` 复制为同目录的 `config.local.json`，将 `engine_exe` 改为真实路径。不要只复制 `run.exe`，它需要原安装目录中的资源。

```json
{
  "engine_exe": "D:/Apps/VOICEVOX/vv-engine/run.exe"
}
```

`config.local.json` 已被 Git 忽略。以下 PowerShell 命令在仓库根目录执行：

```powershell
python ./say.py "ねえ、聞こえる？"
python ./say_timer.py -S done
```

核心运行脚本只使用 Python 标准库，无需 `pip install`。历史混音实验另外依赖 NumPy，不影响上述用法。

也可以用环境变量指定引擎路径，它优先于配置文件：

```powershell
$env:VOICEVOX_ENGINE_EXE = 'D:/Apps/VOICEVOX/vv-engine/run.exe'
python ./say.py "テストです。"
```

这只设置当前 PowerShell 进程及其子进程的环境变量。已经启动的 Claude Code 不会因此获得新变量；hook 接入建议使用项目旁的 `config.local.json`，避免依赖终端环境。

引擎地址固定为 `127.0.0.1:50021`。若该端口已有可用的 VOICEVOX 引擎，脚本直接使用它，不要求配置启动路径，也不会关闭它。若引擎未运行，脚本按配置启动，并在调用结束后关闭自己启动的进程。

## 手动使用

```powershell
python ./say.py --status
python ./say.py --speakers
python ./say.py "お待たせ。終わったよ。" -s 47
python ./say.py "テストです。" --out test.wav
python ./say.py -f ./text.txt
python ./say_timer.py --list
python ./say_timer.py -S comeback --cooldown 30
python ./say_timer.py -S missed --cooldown 60
python ./say_timer.py -S chatter --dry-run
python ./render_preview.py comeback --out-dir ./_人类工作区
```

| 参数 | 用途 |
|---|---|
| `-s / --speaker` | 选择音色，默认 47 |
| `--speed` | 覆盖引擎语速参数 |
| `--pitch` | 覆盖引擎音高参数 `pitchScale` |
| `--intonation` | 覆盖引擎抑扬参数 |
| `--volume` | 覆盖引擎音量参数 |
| `-o / --out` | 导出 WAV，不播放 |
| `--no-play` | 合成但不播放、不保留音频 |
| `--keep-engine` | 保留本次启动的引擎 |

不指定的合成参数保持引擎返回值，尤其不要把所有参数补成 `1.0`。`pitchScale` 的默认值为 `0.0`，不是 `1.0`。

试听渲染使用 `--keep-engine` 加速批量合成，结束后引擎仍会运行。它会覆盖指定场景目录内同名的编号 WAV；需要保留旧试听时，请选择新的输出目录。

## 接入 Claude Code hook

权限提示弹出时，Claude 正在等待授权，不能再执行命令喊人。`PermissionRequest` hook 由 Claude Code 执行，可以在这个时刻调用语音脚本。

示例见 [hooks.example.json](hooks.example.json)。将其中的 Python 和项目路径替换为本机绝对路径，再合并到配置文件已有的 `hooks` 中。不要拿示例覆盖整份设置，也不要覆盖已有其他事件的 hook。

示例配置采用：

- `PermissionRequest`：调用 `comeback` 场景，冷却 30 秒。
- `async: true`：不等待音频播完；本项目不输出批准或拒绝决定，不改变权限判断。
- Python 和脚本路径分别加引号，支持路径中的空格。

### CC Switch 等工具可能覆盖设置

CC Switch 等配置切换工具可能按配置档案重写用户级 `~/.claude/settings.json`，覆盖手工添加的 hook。

可将 hook 合并到实际工作项目的 `.claude/settings.local.json`。该设置只对相应项目生效，语音脚本使用指向本仓库的绝对路径。

若需要对所有项目生效，可在用户级 `~/.claude/settings.json` 中配置，并通过切换工具维护或保留这段 hook。

同一 hook 只配置一次。不要同时在用户级、项目级和工具配置档案中重复添加，否则可能重复触发。修改后用真实权限请求确认是否生效；如果会话未加载新设置，再重新启动 Claude Code。

### 不改设置也能测试脚本

在仓库根目录执行下面的命令，会模拟权限请求输入并喊一句，不安装 hook、不修改 Claude Code 设置：

```powershell
'{"hook_event_name":"PermissionRequest","tool_name":"Bash"}' | python ./hook_notify.py
```

随后查看 `_hook.log`。冷却期内再次执行可能静默跳过。模拟测试只能证明脚本接收输入、合成和播放链路可运行；实际事件是否触发，需要在接入配置后另外确认。

### 权限超时的限制

当前示例只配置 `PermissionRequest`。权限超时后的第二次提醒依赖调用方收到 `Permission request timed out` 后主动执行：

```powershell
python ./say_timer.py -S missed --cooldown 60
```

项目未提供独立的自动超时通知机制。`PermissionDenied` 处理不等同于权限超时事件。

## 接入 say skill

将 `skill/SKILL.md` 复制到 `~/.claude/skills/say/SKILL.md`。安装前备份同名 skill；若已经存在，先决定是否替换。

将副本中的 `VOICE_PROJECT_DIR` 替换为本仓库的绝对路径。该名称是文档占位符，不是程序读取的环境变量。随后在 Claude Code 中使用 `/say`，或让 Claude 按场景判断是否出声。

主动出声的命令可能需要授权。请按实际调用的工具和命令形态配置最小范围权限；否则喊人的命令本身也会等待授权。hook 提醒和 skill 主动出声是两条独立入口，安装 skill 不会自动安装 hook。

## 修改台词和音色

默认音色为 `47 = ナースロボ＿タイプＴ / ノーマル`，备选为 `14 = 冥鳴ひまり`。可用 `--speakers` 查询当前引擎支持的音色。

`lines.py` 提供 9 个场景、48 句日语台词：`chatter`、`sit`、`water`、`break`、`late`、`done`、`comeback`、`greet`、`missed`。修改场景内的 `lines` 或 `volume` 即可；修改 `TIMER_POOL` 可以调整未指定场景时的候选池。

`say_timer.py` 每次运行只触发一次，不是常驻定时器，不检测键鼠，也不会自动知道用户是否久坐。23:00 至次日 06:00 未指定场景时选择 `late`，其余时段从候选池随机选择。

台词选择优先避开最近记录的句子，持久化记录保留最近 12 句，不保证严格遍历全部台词才重复。冷却按场景独立，状态更新使用跨进程文件锁；这不保证不同场景同时发声时的引擎启动和关闭互不影响。

修改台词、音色和冷却后，下次脚本调用即可读取，不需要重启 Claude Code。

## 排查没有声音

| 现象 | 检查方向 |
|---|---|
| 提示未配置引擎 | 检查 `config.local.json` 或 `VOICEVOX_ENGINE_EXE` |
| 引擎进程提前退出 | 检查路径、引擎资源、50021 端口占用 |
| 手动能说，真实 hook 没有新日志 | 检查配置作用域、路径、是否被切换工具覆盖、会话是否加载设置 |
| 日志为 `suppressed` | 冷却拦截，等待后再试 |
| 日志为 `FAIL` 或 `EXCEPTION` | 按日志中的错误检查引擎与 Python |
| 日志为 `spoke` 但听不到 | 检查 Windows 音量、输出设备；日志只是脚本结果，不是听觉确认 |

`hook_notify.py` 为了不干扰 Claude Code，失败时也返回 0，判断语音是否成功要看日志，而不能只看退出码。日志在子进程返回后写入；暂时没有新日志也可能是仍在合成，或日志目录无法写入。

`_hook.log` 记录触发事件、处理结果和部分错误信息。分享诊断日志前，应检查其中的工具响应和消息内容。

## 文件结构

```text
Claudecode-AnimeVoice/
  say.py                    合成、播放、引擎生命周期
  lines.py                  示例台词库
  say_timer.py              场景选择、冷却与状态
  hook_notify.py            hook 输入与诊断日志
  render_preview.py         批量试听渲染
  config.example.json       引擎路径配置示例
  hooks.example.json        hook 配置示例
  skill/SKILL.md            say skill 模板
  experiments/              历史探索脚本，不作为安装入口
  LICENSE                   本项目代码许可证
```

`experiments/` 保留探索过程，部分脚本要求引擎事先运行；其中的旧参数与混音假设不代表当前推荐方案。混音实验已被否决，不要把它当作音色融合功能。

## 许可与署名

本项目代码采用 Apache-2.0，见 [LICENSE](LICENSE)。它不授予 VOICEVOX 程序、模型、角色声库、角色形象或生成语音的额外权利。

使用者需遵守 VOICEVOX 和所选角色声库的各自条款，并按条款提供署名。默认音色的署名示例为 `VOICEVOX:ナースロボ＿タイプＴ`；更换音色时调整署名并核对对应条款。项目不分发引擎、声库或第三方歌曲素材。
