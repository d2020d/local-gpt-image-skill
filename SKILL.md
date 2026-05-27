---
name: local-gpt-image
description: Legacy helper for built-in image_gen workflows. The current workspace default image route is CLIProxyAPI gpt-image-2; use this skill only when the user explicitly asks for built-in image_gen output capture/saving.
---

# Local GPT Image

Use this skill only when the user explicitly asks to generate images with built-in `image_gen` and save the outputs as normal local files in a user-specified directory. Keep the original Codex generated-image files unless the user explicitly asks to delete originals.

Workspace default: general image generation must use local CLIProxyAPI `gpt-image-2` instead of built-in `image_gen`.

This skill is a one-request workflow for the user. The user should not need to manually split the task into "generate image" and "save image" steps.

Important technical boundary: `image_gen` is a Codex model tool, not a shell command. Bundled scripts cannot invoke it directly. The assistant must call `image_gen` between the `start` and `finish` script steps.

## When To Use

Use this skill when the user asks for any of these:

- 用内置 `image_gen` 生成图片并保存到某个目录
- 批量生成图片并保存到本机目录
- 生成后删除原始图片
- 保存 `image_gen` 返回到当前对话里的图片
- 使用 `local-gpt-image`

Do not use this skill for:

- 默认生图任务；按当前系统约束应走本机 CLIProxyAPI，模型 `gpt-image-2`
- 图生图且需要参考图一致性的生产流程；按当前系统约束应走本机 CLIProxyAPI `/v1/images/edits`，模型 `gpt-image-2`
- 必须完全由 shell/Python 后台脚本无人值守执行的生图任务；本技能的脚本不能直接调用 Codex `image_gen`，必须由 Agent 在 `start` 与 `finish` 之间调用内置 `image_gen`
- 飞书多维表格自动生图任务；优先使用对应业务技能，除非该业务技能明确要求由 Agent 层接管无参考图生成

## Core Workflow

Follow this exact sequence internally. Do not ask the user to run a separate image generation step.

1. Confirm the target output directory.
2. Start a local-gpt-image job, which creates a cache snapshot.
3. Call built-in `image_gen` with the user's prompt.
4. Finish the local-gpt-image job, which copies generated images into the target directory. Pass `--keep-originals` unless the user explicitly asked to delete originals.
5. Report saved image paths and deletion status.

## One-Request Usage

When this skill triggers, execute the workflow yourself:

```bash
python3 {SKILL_DIR}/scripts/local_gpt_image_job.py start \
  --out-dir /absolute/target/output/dir \
  --prompt "USER_IMAGE_PROMPT" \
  --count 1
```

Then call `image_gen` with the same prompt.

After `image_gen` finishes, run:

```bash
python3 {SKILL_DIR}/scripts/local_gpt_image_job.py finish \
  --state /tmp/local-gpt-image-jobs/JOB_ID/state.json \
  --keep-originals
```

The `start` command prints the exact `state` path needed by `finish`.

## Commands

Prefer the `local_gpt_image_job.py start` and `finish` commands above. Use the lower-level commands below only for debugging.

## Portable Path Configuration

The scripts infer paths from the skill location by default. The expected layout is:

```text
<workspace>/
├── scripts/imagegen_cache_extractor.py
└── skills/local-gpt-image/
```

If the skill is installed somewhere else, configure paths with environment variables:

```bash
export OPENCLAW_WORKSPACE_DIR="/path/to/openclaw/workspace"
export LOCAL_GPT_IMAGE_SNAPSHOTTER="/path/to/imagegen_cache_extractor.py"
export LOCAL_GPT_IMAGE_FINISHER="/path/to/local-gpt-image/scripts/extract_and_delete.py"
export LOCAL_GPT_IMAGE_GENERATED_ROOT="$HOME/.codex/generated_images"
```

Create a pre-generation snapshot:

```bash
python3 <workspace>/scripts/imagegen_cache_extractor.py snapshot \
  --out /tmp/local-gpt-image-before.json
```

After calling `image_gen`, copy generated images into the target directory:

```bash
python3 {SKILL_DIR}/scripts/extract_and_delete.py \
  --before /tmp/local-gpt-image-before.json \
  --out-dir /absolute/target/output/dir \
  --json-out /tmp/local-gpt-image-result.json \
  --keep-originals
```

The script prints JSON. The most important fields are:

- `saved_count`: number of images copied into the target directory
- `saved`: copied image list with `output` paths
- `deleted_original_count`: number of original generated files deleted. This should be `0` unless the user explicitly requested deletion.
- `skipped_delete`: source files not deleted, with reasons

## Batch Generation

For best one-to-one control, use one snapshot per image:

1. Snapshot.
2. Call `image_gen` once.
3. Extract and delete.
4. Repeat.

If the user only needs all generated images in one folder and does not need one-to-one prompt mapping, it is acceptable to:

1. Snapshot once.
2. Call `image_gen` multiple times.
3. Extract and delete once.

The safer option is one snapshot per generated image because it avoids mixing unrelated images created by another concurrent Codex session.

## Safety Rules

Deletion is intentionally narrow.

- Only delete originals under `~/.codex/generated_images`.
- Never delete files in the user's target output directory.
- Never delete files from browser or Electron cache directories.
- Verify the source file SHA1 still matches the copied image before deleting it.
- If verification fails, skip deletion and report the reason.

## Example

User request:

> 用 image_gen 生成 3 张北欧风客厅绿植图，保存到 `/absolute/output/dir`，生成后删除原图。

Assistant process:

1. Run `local_gpt_image_job.py start --out-dir /absolute/output/dir --prompt "..." --count 3`.
2. Call `image_gen` with the prompt three times, or once if the prompt explicitly requests a batch image.
3. Run `local_gpt_image_job.py finish --state ...`.
4. Reply with copied image paths and deleted-original count.

## Failure Handling

If `saved_count` is `0`, do not claim success. Check:

- Was the snapshot taken before `image_gen`?
- Did `image_gen` actually produce an image?
- Did Codex change the generated image directory?
- Was another workflow used instead of built-in `image_gen`?

If extraction repeatedly fails, tell the user that the local generated-image cache path may have changed and inspect `~/.codex/generated_images`.
