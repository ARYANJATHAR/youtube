# AGENTS.md

## Cursor Cloud specific instructions

This repository contains a Python-based YouTube Poop video generator (`generate_ytp.py`) that produces a surreal ~24-second video about "what it's like to be an LLM."

### Dependencies
- Python 3.12+ with `Pillow` and `numpy`
- `ffmpeg` (system package, used for video encoding and effects)

### Running
- `python3 generate_ytp.py` — renders the full video to `build/llm_ytp.mp4`
- Output is 1280x720 @ 30fps, H.264 with AAC audio
- Rendering takes ~40 seconds

### Notes
- The `build/` directory is generated output and should not be committed.
- No lint/test framework is configured; the script is standalone.
