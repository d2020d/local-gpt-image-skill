# local-gpt-image

中文说明: [README.zh-CN.md](README.zh-CN.md)

`local-gpt-image` is a Codex/OpenClaw skill for saving built-in `image_gen`
outputs as normal local files.

It does not call an image model by itself. The workflow is:

1. Take a snapshot of the current generated-image cache.
2. Let the assistant call the built-in `image_gen` tool.
3. Compare the cache before and after generation.
4. Copy the new images into a target directory.
5. Keep original generated files by default unless deletion is explicitly requested.

## When to use

Use this skill when a user asks to:

- generate images with built-in `image_gen` and save them to a local directory
- batch save images generated in the current Codex conversation
- optionally delete original generated-image cache files after copying

Do not use it for fully unattended API image pipelines. The scripts cannot call
Codex `image_gen` directly; the assistant must call `image_gen` between the
`start` and `finish` steps.

## Requirements

- Python 3.10+
- Codex/OpenClaw environment with built-in `image_gen`
- Shared extractor script at `scripts/imagegen_cache_extractor.py` in the
  OpenClaw workspace, or a custom path provided via environment variable
- Access to the Codex generated-image cache, usually:
  `~/.codex/generated_images`

## Installation

Place this directory under your OpenClaw skills folder:

```text
~/.openclaw/workspace/skills/local-gpt-image/
```

Expected default workspace layout:

```text
~/.openclaw/workspace/
├── scripts/
│   └── imagegen_cache_extractor.py
└── skills/
    └── local-gpt-image/
        ├── SKILL.md
        └── scripts/
```

If your layout is different, set one of these environment variables:

```bash
export OPENCLAW_WORKSPACE_DIR="/path/to/openclaw/workspace"
export LOCAL_GPT_IMAGE_SNAPSHOTTER="/path/to/imagegen_cache_extractor.py"
export LOCAL_GPT_IMAGE_FINISHER="/path/to/local-gpt-image/scripts/extract_and_delete.py"
export LOCAL_GPT_IMAGE_GENERATED_ROOT="$HOME/.codex/generated_images"
```

## Usage

Start a job and take a cache snapshot:

```bash
python3 scripts/local_gpt_image_job.py start \
  --out-dir /absolute/output/dir \
  --prompt "A clean editorial cover image about AI workflows" \
  --count 1
```

The command prints a `state` JSON path.

Then the assistant must call built-in `image_gen` with the same prompt.

Finish the job and copy the generated images:

```bash
python3 scripts/local_gpt_image_job.py finish \
  --state /tmp/local-gpt-image-jobs/JOB_ID/state.json \
  --keep-originals
```

Use `--keep-originals` unless the user explicitly asks to delete original cache
files.

## Safety

Deletion is intentionally narrow.

- Only files under `~/.codex/generated_images` are eligible for deletion.
- The target output directory is never deleted.
- Browser, Electron, and system cache directories are never deleted.
- Source files are deleted only after SHA1 verification.

## Files

```text
local-gpt-image/
├── SKILL.md
├── README.md
├── .gitignore
└── scripts/
    ├── local_gpt_image_job.py
    └── extract_and_delete.py
```
