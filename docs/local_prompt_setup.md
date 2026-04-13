# Local Prompt Harness

This repo now includes a small CLI for repeatable prompts against a local OpenAI-compatible endpoint such as LM Studio.

## Defaults

- Endpoint: `http://localhost:1234/v1`
- Model: first model returned by `GET /models` unless `--model` is provided
- Runtime: `.venv\Scripts\python.exe`

## Quick commands

List available local models:

```powershell
c:/Users/jamie/OneDrive/Personel/Documents/AI-Martin/AIMartinSuiteGLCVersion/.venv/Scripts/python.exe .\scripts\local_prompt.py --list-models
```

Ask a documentation question about the current launcher module:

```powershell
c:/Users/jamie/OneDrive/Personel/Documents/AI-Martin/AIMartinSuiteGLCVersion/.venv/Scripts/python.exe .\scripts\local_prompt.py --preset docs --prompt "Summarize the startup flow for maintainers." --context-file .\launcher.py --print-model
```

Ask a freeform code question:

```powershell
c:/Users/jamie/OneDrive/Personel/Documents/AI-Martin/AIMartinSuiteGLCVersion/.venv/Scripts/python.exe .\scripts\local_prompt.py --preset code --prompt "Write a small argparse example for an optional --module flag." --print-model
```

Use a longer prompt from a file:

```powershell
c:/Users/jamie/OneDrive/Personel/Documents/AI-Martin/AIMartinSuiteGLCVersion/.venv/Scripts/python.exe .\scripts\local_prompt.py --preset docs --prompt-file .\prompts\my_question.md --context-file .\launcher.py
```

## Presets

- `docs`: documentation and summarization
- `code`: small code generation or coding questions
- `review`: terse review-style output

You can also append a custom system prompt with `--system-file`.

## VS Code tasks

The task runner includes:

- `Local Prompt: Ask About Current File`
- `Local Prompt: Free Prompt`
- `Local Prompt: List Local Models`

The current-file task uses the active editor file as prompt context.