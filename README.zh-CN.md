# local-gpt-image 中文说明

`local-gpt-image`技能是用来把 Codex 内置 `image_gen` 生成出来的图片，稳定保存成本机目录里的普通图片文件。

它不是一个新的生图模型，也不是一个独立的生图 API 封装。它解决的是另一个更具体的问题：图片已经由 Codex 的内置 `image_gen` 生成出来了，如何把这些图片可靠地复制到你指定的文件夹里。

## 它解决什么问题

在 Codex 对话里调用 `image_gen` 后，图片通常会先出现在当前会话中，同时会落到本地生成图片缓存目录。

如果只是看一眼，问题不大。  
如果你要把图片用于公众号封面、文章配图、素材归档，或者交给后续脚本处理，就需要一个稳定的落盘流程。

`local-gpt-image` 的工作方式是：

1. 生图前先记录一次当前图片缓存快照。
2. 由 Agent 调用内置 `image_gen` 生成图片。
3. 生图后对比前后缓存变化。
4. 找到新生成的图片。
5. 复制到你指定的输出目录。
6. 默认保留原始缓存文件，除非用户明确要求删除。

## 运行条件

需要满足以下条件：

- Python 3.10 或更高版本
- Codex / OpenClaw 环境
- 当前环境支持内置 `image_gen`
- 能访问 Codex 图片缓存目录，默认是 `~/.codex/generated_images`

默认目录结构建议如下：

```text
~/.openclaw/workspace/
├── scripts/
│   └── imagegen_cache_extractor.py
└── skills/
    └── local-gpt-image/
        ├── SKILL.md
        └── scripts/
```

如果你的安装路径不同，可以通过环境变量指定：

```bash
export OPENCLAW_WORKSPACE_DIR="/path/to/openclaw/workspace"
export LOCAL_GPT_IMAGE_SNAPSHOTTER="/path/to/imagegen_cache_extractor.py"
export LOCAL_GPT_IMAGE_FINISHER="/path/to/local-gpt-image/scripts/extract_and_delete.py"
export LOCAL_GPT_IMAGE_GENERATED_ROOT="$HOME/.codex/generated_images"
```

## 适合哪些场景

适合：

- 用内置 `image_gen` 生成图片，并保存到指定本地目录
- 把当前对话里生成的图片批量归档
- 给公众号封面、文章配图、创意草图做本地保存
- 少量批量生图后统一整理文件
- 明确需要把生成图片从缓存中提取出来

不适合：

- 完全后台无人值守的 API 生图流水线
- 需要参考图强一致性的图生图生产流程
- 大批量电商主图、详情图、场景图生产
- 飞书多维表格自动生图任务

这些场景更适合使用专门的 API 生图技能或业务流水线。

## 基本用法

第一步，开始任务并创建缓存快照：

```bash
python3 scripts/local_gpt_image_job.py start \
  --out-dir /absolute/output/dir \
  --prompt "一张关于 AI 工作流的公众号封面图，干净，高级，科技感" \
  --count 1
```

命令会输出一个 `state` 路径，例如：

```text
/tmp/local-gpt-image-jobs/JOB_ID/state.json
```

第二步，由 Agent 调用内置 `image_gen`，使用同一个 prompt 生成图片。

注意：这一步不是 shell 命令。  
`image_gen` 是 Codex 的模型工具，脚本不能直接调用它。

第三步，完成任务并把图片复制到输出目录：

```bash
python3 scripts/local_gpt_image_job.py finish \
  --state /tmp/local-gpt-image-jobs/JOB_ID/state.json \
  --keep-originals
```

建议默认使用 `--keep-originals`。  
这样会复制新图，但不会删除原始缓存文件。

## 删除原图的安全策略

如果用户明确要求删除原始图片，本技能也会非常保守地处理：

- 只删除 `~/.codex/generated_images` 下面的原始文件
- 不会删除目标输出目录中的图片
- 不会删除浏览器缓存、Electron 缓存或系统目录
- 删除前会校验 SHA1，确认复制后的文件和原始文件一致
- 如果校验失败，会跳过删除并记录原因

## 输出结果怎么看

`finish` 命令会输出 JSON。

重点看这几个字段：

- `saved_count`：成功保存到目标目录的图片数量
- `saved`：每张图片的来源和输出路径
- `deleted_original_count`：删除的原始缓存文件数量
- `skipped_delete`：未删除的文件和原因

如果 `saved_count` 是 `0`，不能认为任务成功。通常需要检查：

- 是否在生图前执行了 `start`
- `image_gen` 是否真的生成了图片
- Codex 的生成图片缓存路径是否变化
- 是否用了其他生图通道，而不是内置 `image_gen`

## 一句话理解

`image_gen` 负责生成图片。  
`local-gpt-image` 负责把生成结果从本地缓存中提取出来，保存到你指定的目录。


