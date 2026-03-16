## Terminal / Shell

PowerShell 7+ (pwsh) is available via Scoop. The `powershell` tool can be used to execute commands.

- OS: Windows (Git Bash as default user terminal)
- pwsh is at: `~/scoop/shims/pwsh`

## Python environment

- Conda env: `bfa-cl-modelos-v2` (activate: `conda activate bfa-cl-modelos-v2`)
- Python executable: `/c/Users/vlandaetat/AppData/Local/anaconda3/envs/bfa-cl-modelos-v2/python`
- Always use this Python, never the base Anaconda or system Python.

## Project context

- Language: Python
- OS: Windows (Git Bash as default terminal)
- Dependencies: `requirements.txt` (pip)
- Entry point: `python main.py`
- Natural Language for code comments, documentation, and commit messages: Spanish, but use English for code identifiers (variable names, function names, etc.) to maintain readability and consistency with common programming practices, and also technical terms that may not have a direct translation in Spanish.

## Unicode / encoding

- **NEVER use emojis or non-ASCII symbols** (arrows like `←`, `→`, em-dashes `—`, etc.) in Python source files, YAML configs, or any file that Python reads at runtime. Windows default encoding is `cp1252` and these characters cause `UnicodeDecodeError` when read without explicit encoding.
- Use ASCII equivalents instead: `<-`, `->`, `--`, etc.
- **Always specify `encoding='utf-8'`** in every `open()` call that reads/writes text files. Never rely on the system default encoding.
- Spanish accented characters (á, é, í, ó, ú, ñ) are acceptable **only in YAML/text comments and documentation**, never in Python identifiers.
