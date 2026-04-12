---
agent: ask
description: Delegate a bounded coding task to a local Ollama Qwen model such as qwen2.5-coder:14b or qwen2.5-coder:7b and return the saved result path.
---

Delegate this task to a local Ollama model:

Task: ${input:task}
Mode: ${input:mode}
Context file (optional): ${input:contextFile}
Model (optional): ${input:model}

Use this command pattern:

scripts/qwen_delegate.sh --task "${input:task}" --mode "${input:mode}"

If context file is provided, run:

scripts/qwen_delegate.sh --task "${input:task}" --mode "${input:mode}" --context "${input:contextFile}"

If model is provided, add:

scripts/qwen_delegate.sh --task "${input:task}" --mode "${input:mode}" --model "${input:model}"

After execution:
- Report the output file path under docs/ai-delegation.
- Summarize top findings in 5 bullets max.
- If mode is patch, flag any uncertainty before applying changes.
- If the selected model is a Phi model, emphasize only non-obvious findings and avoid paraphrasing the supplied context.
