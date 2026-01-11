# Photo Critic - Agent Architecture

## System Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  CLI Input  │────▶│ Batch Queue  │────▶│ OpenAI API  │
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
  --model gpt-4o-mini \
  --dry-run
```

### Arguments

|Flag               |Default                     |Description                                     |
|-------------------|----------------------------|------------------------------------------------|
|`path`             |required                    |Folder containing images                        |
|`--output`, `-o`   |`./critic-report.json`      |Output file path                                |
|`--format`, `-f`   |`json`                      |Output format: `json`, `markdown`, `both`       |
|`--min-score`      |`0`                         |Only include images above this score            |
|`--provider`       |`openai`                    |API provider: `openai`                          |
|`--model`          |provider default            |Model to use (provider-specific)                |
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
def prepare_batch(images: list[Path], model: str, provider: str) -> list[dict]:
    """
    Convert images to batch request format.

    - Resize images > 1568px on long edge (API optimization)
    - Convert HEIC to JPEG if needed
    - Base64 encode
    - Build request with shared system prompt
    """
```

**Image preprocessing:**

- Long edge > 1568px → resize (preserves quality, reduces tokens)
- HEIC → JPEG conversion (API compatibility)
- Skip corrupt/unreadable files with warning

### 3. Batch Submission

Use the OpenAI batch API:

```python
def submit_batch(requests: list[dict]) -> str:
    """
    Submit batch to selected provider API.

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
├── CLAUDE.md              # AI instructions and criteria
├── agents.md              # This file
├── pyproject.toml         # Dependencies and metadata
├── src/
│   └── photo_critic/
│       ├── __init__.py
│       ├── cli.py         # Click/Typer CLI entry point
│       ├── discovery.py   # Image finding logic
│       ├── prepare.py     # Image preprocessing
│       ├── batch.py       # Batch API client (OpenAI)
│       └── report.py      # Output generation
└── tests/
    └── ...
```

## Dependencies

```toml
[project]
dependencies = [
    "click>=8.0",
    "openai>=1.30.0",
    "pillow>=10.0",
    "pillow-heif>=0.18",  # HEIC support
    "python-dotenv>=1.0.0",
    "rich>=13.0",         # Pretty console output
]
```

## Environment

```bash
OPENAI_API_KEY=sk-...
```

## Cost Estimation

OpenAI pricing varies by model; consult the OpenAI pricing page for estimates.

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
