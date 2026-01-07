# Photo Critic

AI-powered CLI tool for batch photo criticism using Claude's vision API. Quickly identify your best shots from hundreds of photos with detailed, professional critiques.

## Features

- **Batch Processing**: Analyze hundreds of photos efficiently using Claude's Message Batches API (50% cost savings)
- **Detailed Critiques**: Get scored feedback on composition, lighting, subject matter, and technical quality
- **Multiple Formats**: Generate reports in JSON or Markdown
- **Smart Filtering**: Filter results by minimum score to find your best work
- **Image Preprocessing**: Automatic resizing and format conversion (including HEIC support)
- **Beautiful CLI**: Rich terminal output with progress indicators

## Installation

### Requirements

- Python 3.11 or higher
- Anthropic API key

### Install from Source

```bash
# Clone the repository
git clone https://github.com/michaelcolenso/cull-the-herd.git
cd cull-the-herd

# Install with uv
uv sync

# Or install with dev dependencies
uv sync --dev
```

### Set up API Key

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

Or create a `.env` file:

```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

## Usage

### Basic Usage

```bash
# Analyze all photos in a directory
photo-critic ./photos

# Include subdirectories
photo-critic ./photos --recursive
```

### Output Formats

```bash
# Generate JSON report (default)
photo-critic ./photos --output results.json

# Generate Markdown report
photo-critic ./photos --format markdown --output results.md

# Generate both formats
photo-critic ./photos --format both --output results
```

### Filtering and Limits

```bash
# Only include photos scoring 7.0 or higher
photo-critic ./photos --min-score 7.0

# Limit to first 50 images
photo-critic ./photos --max-images 50
```

### Advanced Options

```bash
# Use a different Claude model
photo-critic ./photos --model claude-opus-4-5-20251101

# Dry run (see what would be processed)
photo-critic ./photos --dry-run

# Verbose logging
photo-critic ./photos --verbose
```

### Complete Example

```bash
photo-critic ./vacation-photos \
  --recursive \
  --format both \
  --output ./reports/vacation-critique \
  --min-score 6.5 \
  --max-images 100 \
  --verbose
```

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `path` | *required* | Folder containing images |
| `--output`, `-o` | `./critic-report.json` | Output file path |
| `--format`, `-f` | `json` | Output format: `json`, `markdown`, or `both` |
| `--min-score` | `0.0` | Only include images above this score |
| `--model` | `claude-sonnet-4-5-20250929` | Claude model to use |
| `--dry-run` | `false` | Show what would be processed without calling API |
| `--max-images` | `100` | Limit number of images to process |
| `--recursive`, `-r` | `false` | Include subdirectories |
| `--verbose`, `-v` | `false` | Enable verbose logging |

## Supported Image Formats

- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- WebP (`.webp`)
- HEIC (`.heic`) - requires `pillow-heif`

Images smaller than 100KB are automatically excluded to avoid thumbnails and cached files.

## Critique Scoring

Each photo receives scores (0-10) in four categories:

1. **Composition**: Rule of thirds, leading lines, balance, framing, negative space
2. **Lighting**: Quality, direction, exposure, dynamic range, mood
3. **Subject Matter**: Interest, clarity, storytelling, emotional impact
4. **Technical Quality**: Focus, sharpness, noise, color accuracy, processing

The **overall score** is the average of these four categories.

### Score Tiers

- **Excellent (9-10)**: Portfolio-worthy shots
- **Great (8-9)**: Strong images with minor room for improvement
- **Good (7-8)**: Solid photos worth keeping
- **Average (6-7)**: Usable but could be improved
- **Below Average (5-6)**: Significant issues
- **Poor (0-5)**: Consider culling

## Output Examples

### JSON Report

```json
{
  "generated_at": "2026-01-07T10:30:00",
  "statistics": {
    "total_images": 42,
    "mean_overall_score": 7.3,
    "score_distribution": {
      "excellent (9-10)": 3,
      "great (8-9)": 12,
      "good (7-8)": 18,
      "average (6-7)": 7,
      "below_average (5-6)": 2,
      "poor (0-5)": 0
    }
  },
  "results": [
    {
      "filename": "sunset-beach.jpg",
      "overall_score": 9.2,
      "composition_score": 9.5,
      "lighting_score": 9.0,
      "subject_score": 9.0,
      "technical_score": 9.5,
      "summary": "Stunning composition with perfect golden hour lighting...",
      "strengths": ["Excellent use of rule of thirds", "Beautiful warm tones"],
      "improvements": ["Horizon could be slightly more level"]
    }
  ]
}
```

### Markdown Report

See example output in the [reports/](reports/) directory.

## Cost Estimation

Using the Message Batches API provides a 50% discount:

- **Sonnet 4.5**: ~$1.50/1M input tokens, ~$7.50/1M output tokens
- **Typical image**: ~1,500 input tokens + ~300 output tokens
- **Per image cost**: ~$0.003-0.005
- **100 images**: ~$0.30-0.50

The CLI displays an estimated cost before submitting the batch.

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/michaelcolenso/cull-the-herd.git
cd cull-the-herd

# Install with dev dependencies (uv creates/manages venv automatically)
uv sync --dev
```

### Run Tests

```bash
uv run pytest
```

### Code Formatting

```bash
# Format code with Black
uv run black src/ tests/

# Lint with Ruff
uv run ruff check src/ tests/

# Type checking with mypy
uv run mypy src/
```

### Project Structure

```
cull-the-herd/
├── src/photo_critic/
│   ├── __init__.py       # Package exports
│   ├── cli.py            # CLI entry point
│   ├── discovery.py      # Image discovery
│   ├── prepare.py        # Image preprocessing
│   ├── batch.py          # Anthropic batch API client
│   └── report.py         # Report generation
├── tests/                # Test suite
├── pyproject.toml        # Package configuration
├── README.md             # This file
├── CLAUDE.md            # AI assistant guide
└── agents.md            # Architecture documentation
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and formatting
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built with [Anthropic's Claude API](https://www.anthropic.com)
- CLI built with [Click](https://click.palletsprojects.com/)
- Rich terminal output with [Rich](https://rich.readthedocs.io/)

## Support

- **Issues**: [GitHub Issues](https://github.com/michaelcolenso/cull-the-herd/issues)
- **Discussions**: [GitHub Discussions](https://github.com/michaelcolenso/cull-the-herd/discussions)

---

**Happy shooting!** 📸