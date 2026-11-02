# Claudecode-AnimeVoice

[中文](README.md) | English

A local Japanese voice tool for Claude Code, powered by [VOICEVOX](https://voicevox.hiroshiba.jp/). It supports manual playback, scenario phrases, permission reminders, and chatter after tool calls.

Speech is synthesized locally without an additional API key. Input must be Japanese; translation is handled by the caller. Install the VOICEVOX engine separately.

Verified environment: Windows, Python 3.12, VOICEVOX 0.25.2.

Manual playback and simulated hook input have been verified in that environment. Confirm installation and actual hook delivery in your deployment environment.

## Quick start

1. Install Python 3.10 or later.
2. Install VOICEVOX and locate `vv-engine/run.exe`.
3. Copy `config.example.json` to `config.local.json` next to the scripts and set `engine_exe` to the actual path. Keep the engine's installation resources alongside it rather than copying only `run.exe`.

```json
{
  "engine_exe": "D:/Apps/VOICEVOX/vv-engine/run.exe"
}
```

`config.local.json` is ignored by Git. Run the following PowerShell commands from the repository root:

```powershell
python ./say.py "ねえ、聞こえる？"
python ./say_timer.py -S done
```

The core scripts use only the Python standard library. The historical mixing experiment additionally requires NumPy; it is not needed for normal use.

An environment variable can override the engine path:

```powershell
$env:VOICEVOX_ENGINE_EXE = 'D:/Apps/VOICEVOX/vv-engine/run.exe'
python ./say.py "テストです。"
```

This variable applies to the current PowerShell process and its children, not an already running Claude Code process. For hooks, use `config.local.json` next to the scripts to avoid depending on terminal environment variables.

The engine endpoint is fixed at `127.0.0.1:50021`. If a VOICEVOX engine is already available there, the script uses it without requiring a launch path or shutting it down. Otherwise, it starts the configured engine and closes that process when the call completes.

## Manual usage

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

| Option | Purpose |
|---|---|
| `-s / --speaker` | Select a voice; default: 47 |
| `--speed` | Override the engine's speech speed |
| `--pitch` | Override the engine's `pitchScale` |
| `--intonation` | Override intonation |
| `--volume` | Override volume |
| `-o / --out` | Save a WAV file without playback |
| `--no-play` | Synthesize without playback or saving audio |
| `--keep-engine` | Keep the engine started by this call running |

Unspecified synthesis parameters retain the values returned by the engine. Do not set all parameters to `1.0`: the default `pitchScale` is `0.0`.

Preview rendering uses `--keep-engine` for batch synthesis and leaves the engine running afterward. It overwrites numbered WAV files with matching names in the scenario directory. Use a different output directory to retain previous previews.

## Claude Code hook integration

[hooks.example.json](hooks.example.json) includes two events:

| Event | Trigger | Scenario | Cooldown |
|---|---|---|---|
| `PermissionRequest` | A tool requests permission | `comeback` | 30 seconds |
| `PostToolUse` | `PowerShell`, `Edit`, `Write`, or `Bash` completes successfully | `chatter` | 300 seconds |

Each scenario has an independent cooldown. Chatter plays after matching tool calls, not on a 300-second timer, so speech remains available when permission requests are infrequent. Keep only `PermissionRequest` if you only need permission reminders.

The `PostToolUse` matcher is `PowerShell|Edit|Write|Bash`. Adjust it to match the tools in use. The example excludes high-frequency tools such as `Read` and `Grep`.

### Configuration

Replace the Python and script paths with absolute paths on your machine, keeping each path quoted. Back up the settings file, then merge the events into its existing `hooks` without replacing other settings. The example uses `async: true` so playback does not block tool execution.

- Current project: use that project's `.claude/settings.local.json`. It applies only to that project.
- All projects: use `~/.claude/settings.json`. When using CC Switch or another configuration switching tool, maintain or preserve the hooks in its profile.

Register each event once to avoid duplicate playback across scopes. Restart Claude Code after changing hook settings, then confirm integration with a real permission request and a matching tool call.

### Simulated input

From the repository root:

```powershell
'{"hook_event_name":"PermissionRequest","tool_name":"Bash"}' | python ./hook_notify.py
'{"hook_event_name":"PostToolUse","tool_name":"Edit"}' | python ./hook_notify.py
```

Simulated input plays the corresponding scenario unless its cooldown is active. Results are written to `_hook.log`. This does not verify actual event delivery by Claude Code.

### Permission timeouts

A timeout reminder requires the caller to receive `Permission request timed out` and run:

```powershell
python ./say_timer.py -S missed --cooldown 60
```

The example does not configure automatic timeout notifications. Handling `PermissionDenied` is not equivalent to receiving a permission timeout event.

## Install the say skill

Copy `skill/SKILL.md` to `~/.claude/skills/say/SKILL.md`. Back up an existing skill with the same name before replacing it.

Replace `VOICE_PROJECT_DIR` in the installed copy with this repository's absolute path. It is a documentation placeholder, not an environment variable read by the program. Use `/say` in Claude Code or let Claude choose when a spoken reminder is appropriate.

Direct speech commands may require permission. Configure permissions narrowly for the tool and command used; otherwise, the notification command itself may wait for approval. The hook and the skill are separate entry points. Installing the skill does not install the hook.

## Customize phrases and voices

The default voice is `47 = ナースロボ＿タイプＴ / ノーマル`; an alternative is `14 = 冥鳴ひまり`. Use `--speakers` to list voices supported by the installed engine.

`lines.py` contains 48 Japanese phrases across nine scenarios: `chatter`, `sit`, `water`, `break`, `late`, `done`, `comeback`, `greet`, and `missed`. Edit a scenario's `lines` or `volume` to customize it. `TIMER_POOL` controls the selection pool when no scenario is specified.

`say_timer.py` triggers speech once per invocation. It is not a persistent scheduler and does not monitor input activity or determine whether the user has been sitting too long. Without an explicit scenario, it selects `late` between 23:00 and 06:00; otherwise, it randomly selects from the pool.

Phrase selection avoids recent entries where possible and retains the last 12 entries between calls; it does not guarantee that every phrase is used before repetition. Cooldowns are independent by scenario, with state updates protected by a cross-process file lock. Engine startup and shutdown are not fully isolated across concurrent calls for different scenarios.

Changes to phrases, voices, and cooldowns take effect on the next script invocation without restarting Claude Code.

## Troubleshooting

| Symptom | Check |
|---|---|
| Engine path is not configured | `config.local.json` or `VOICEVOX_ENGINE_EXE` |
| Engine exits before becoming ready | Engine path, resources, and port 50021 |
| Manual playback works but hooks produce no new log | Configuration scope, command paths, switching tools, and settings loading |
| Log reports `suppressed` | Wait for the cooldown to expire |
| Log reports `FAIL` or `EXCEPTION` | Follow the logged error and check Python and the engine |
| Log reports `spoke` but no audio is audible | Windows volume and output device; the log is not confirmation of audible playback |

`hook_notify.py` returns 0 even on failures to avoid disrupting Claude Code. Use the log rather than the exit code to diagnose playback. Logging occurs after the child process returns; a missing new entry may also mean synthesis is still running or the log directory is not writable.

`_hook.log` records events, tool names, results, and some messages and errors. It omits `tool_input` and `tool_response`. Review message and error fields before sharing logs.

## File structure

```text
Claudecode-AnimeVoice/
  say.py                    Synthesis, playback, and engine lifecycle
  lines.py                  Scenario phrase library
  say_timer.py              Selection, cooldowns, and state
  hook_notify.py            Hook input and diagnostic logging
  render_preview.py         Batch preview rendering
  config.example.json       Engine path configuration example
  hooks.example.json        Hook configuration example
  skill/SKILL.md            say skill template
  experiments/              Historical experiments
  LICENSE
```

Some scripts in `experiments/` require an engine to be running beforehand. Their parameter choices and mixing assumptions are not recommended defaults. The mixing experiment is not a supported voice blending feature.

## License and attribution

Project code is licensed under Apache-2.0; see [LICENSE](LICENSE). This does not grant additional rights to VOICEVOX software, models, voice libraries, character artwork, or generated speech.

Follow the terms and attribution requirements of VOICEVOX and the selected voice library. An attribution example for the default voice is `VOICEVOX:ナースロボ＿タイプＴ`. Update attribution and review the relevant terms when choosing another voice. Engine binaries, voice libraries, and third-party song material are not distributed with this project.
