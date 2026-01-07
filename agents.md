# Photo Critic - Agent Architecture

## System Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  CLI Input  │────▶│ Batch Queue  │────▶│ Claude API  │
│  (folder)   │     │  (JSONL)     │     │  (Vision)   │
└─────────────┘     └──────────────┘     └─────────────┘
                                                │
                    ┌──────────────┐            │
                    │   Report     │◀───────────┘
                    │  (JSON/MD)   │
                    └──────────────┘
```

## CLI Interface

```bash
# Basic usage
photo-critic ./photos

# Options
photo-critic ./photos \
  --output results.json \
  --format markdown \
  --min-score 7.0 \
  --model claude-sonnet-4-5-20250929 \
  --dry-run
```

### Arguments

|Flag               |Default                     |Description                                     |
|-------------------|----------------------------|------------------------------------------------|
|`path`             |required                    |Folder containing images                        |
|`--output`, `-o`   |`./critic-report.json`      |Output file path                                |
|`--format`, `-f`   |`json`                      |Output format: `json`, `markdown`, `both`       |
|`--min-score`      |`0`                         |Only include images above this score            |
|`--model`          |`claude-sonnet-4-5-20250929`|Claude model to use                             |
|`--dry-run`        |`false`                     |Show what would be processed without calling API|
|`--max-images`     |`100`                       |Limit number of images to process               |
|`--recursive`, `-r`|`false`                     |Include subdirectories                          |

## Processing Pipeline

### 1. Discovery Phase

```python
def discover_images(path: Path, recursive: bool = False) -> list[Path]:
    """
    Find all supported images in directory.

    Supported formats: .jpg, .jpeg, .png, .webp, .heic
    Excludes: thumbnails, _cache folders, files < 100KB
    """
```

### 2. Preparation Phase

```python
def prepare_batch(images: list[Path]) -> list[dict]:
    """
    Convert images to batch request format.

    - Resize images > 1568px on long edge (API optimization)
    - Convert HEIC to JPEG if needed
    - Base64 encode
    - Build request with system prompt from Claude.md
    """
```

**Image preprocessing:**

- Long edge > 1568px → resize (preserves quality, reduces tokens)
- HEIC → JPEG conversion (API compatibility)
- Skip corrupt/unreadable files with warning

### 3. Batch Submission

Use Claude's Message Batches API for 50% cost savings:

```python
def submit_batch(requests: list[dict]) -> str:
    """
    Submit batch to Claude API.

    Returns: batch_id for polling

    Rate limits:
    - 10,000 requests per batch max
    - 32MB total request size
    """
```

### 4. Polling & Collection

```python
def poll_batch(batch_id: str, interval: int = 30) -> dict:
    """
    Poll until batch completes.

    States: in_progress, ended (success/failed/expired)
    Default poll interval: 30 seconds
    Timeout: 24 hours (API limit)
    """
```

### 5. Report Generation

```python
def generate_report(results: list[dict], format: str) -> None:
    """
    Generate final report.

    - Sort by overall_score descending
    - Group by tier
    - Calculate statistics (mean, distribution)
    - Write to output file(s)
    """
```

## File Structure

```
photo-critic/
├── Claude.md              # AI instructions and criteria
├── agents.md              # This file
├── pyproject.toml         # Dependencies and metadata
├── src/
│   └── photo_critic/
│       ├── __init__.py
│       ├── cli.py         # Click/Typer CLI entry point
│       ├── discovery.py   # Image finding logic
│       ├── prepare.py     # Image preprocessing
│       ├── batch.py       # Anthropic batch API client
│       └── report.py      # Output generation
└── tests/
    └── ...
```

## Dependencies

```toml
[project]
dependencies = [
    "anthropic>=0.40.0",
    "click>=8.0",
    "pillow>=10.0",
    "pillow-heif>=0.18",  # HEIC support
    "rich>=13.0",         # Pretty console output
]
```

## Environment

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

## Cost Estimation

With batch API (50% discount):

- Sonnet 4.5: ~$1.50/1M input tokens, ~$7.50/1M output tokens
- Typical image: ~1,500 tokens input + ~300 tokens output
- **Per image: ~$0.003-0.005**
- **100 images: ~$0.30-0.50**

## Error Handling

|Error          |Handling                               |
|---------------|---------------------------------------|
|Corrupt image  |Log warning, skip, continue            |
|API rate limit |Exponential backoff                    |
|Batch timeout  |Save partial results, report incomplete|
|Network failure|Retry with backoff, save progress      |

## Future Enhancements

- [ ] Resume interrupted batches
- [ ] Side-by-side comparison mode
- [ ] Lightroom XMP sidecar generation (ratings)
- [ ] Web UI for reviewing results
- [ ] Custom criteria profiles
