# CLAUDE.md - AI Assistant Development Guide

**Last Updated:** 2026-01-07
**Repository:** cull-the-herd
**Owner:** michaelcolenso

---

## Table of Contents

1. [Repository Overview](#repository-overview)
2. [Current State](#current-state)
3. [Development Workflow](#development-workflow)
4. [Git Conventions](#git-conventions)
5. [Code Conventions](#code-conventions)
6. [AI Assistant Guidelines](#ai-assistant-guidelines)
7. [Project Structure](#project-structure)
8. [Key Files and Directories](#key-files-and-directories)

---

## Repository Overview

### Purpose
**Photo Critic** - An AI-powered CLI tool that uses Claude's vision API to critique and rate photos in bulk, helping photographers quickly identify their best shots.

The tool processes folders of images using Claude's Message Batches API for cost-effective batch analysis (50% discount), providing detailed critiques including composition, lighting, subject matter, and technical quality assessments with numerical ratings.

### Technology Stack
- **Language:** Python 3.11+
- **CLI Framework:** Click
- **AI API:** Anthropic Claude (Message Batches API)
- **Image Processing:** Pillow, pillow-heif
- **Output:** Rich (console formatting), JSON/Markdown reports
- **Package Manager:** uv
- **Build System:** pyproject.toml (PEP 621)
- **Testing:** pytest (planned)

---

## Current State

### Repository Status
- **Initialization Date:** January 6, 2026
- **Total Commits:** 1 (Initial commit)
- **Active Files:** 1 (README.md)
- **Working Tree:** Clean

### What Exists
- ✅ README.md with basic project title
- ✅ Git repository initialized
- ✅ SSH-based commit signing configured
- ✅ Remote origin configured

### What Doesn't Exist Yet
- ❌ Source code files
- ❌ Configuration files (package.json, requirements.txt, etc.)
- ❌ .gitignore file
- ❌ Test files or test structure
- ❌ Build/deployment configuration
- ❌ Comprehensive documentation
- ❌ CI/CD pipelines
- ❌ License file
- ❌ Contributing guidelines

---

## Development Workflow

### Branch Strategy

This repository follows a **feature branch workflow** with Claude-specific conventions:

#### Branch Naming Convention
```
claude/<feature-description>-<session-id>
```

**Examples:**
- `claude/add-claude-documentation-u9EsU`
- `claude/implement-user-auth-x7Kp2`
- `claude/fix-memory-leak-9qW4s`

**Rules:**
1. All Claude-created branches MUST start with `claude/`
2. Use kebab-case for feature descriptions
3. Include a session ID suffix (5-6 characters)
4. Keep branch names descriptive but concise (max 50 characters)

#### Branch Lifecycle
1. **Create branch** from main/master (or specified base branch)
2. **Develop** all changes on the feature branch
3. **Commit** regularly with clear messages
4. **Push** to origin with `-u` flag: `git push -u origin <branch-name>`
5. **Create PR** when ready for review
6. **Merge** after approval (branch may be auto-deleted)

### Development Process

1. **Understand the Request**
   - Read issue/request thoroughly
   - Ask clarifying questions if needed
   - Identify dependencies and constraints

2. **Plan the Implementation**
   - Break down complex tasks into steps
   - Identify files that need changes
   - Consider edge cases and testing needs

3. **Implement Changes**
   - Read existing code before modifying
   - Follow established patterns and conventions
   - Write clean, maintainable code
   - Add tests for new functionality

4. **Verify Changes**
   - Run tests (when test infrastructure exists)
   - Check for linting errors
   - Verify functionality manually if needed
   - Review your own changes

5. **Commit and Push**
   - Write clear commit messages
   - Push to the designated feature branch
   - Create PR with descriptive summary

---

## Git Conventions

### Commit Messages

Follow the **Conventional Commits** specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Commit Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring without feature changes
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system or dependency changes
- `ci`: CI/CD configuration changes
- `chore`: Maintenance tasks

#### Examples
```bash
feat(auth): add user authentication system

Implement JWT-based authentication with login and logout endpoints.
Includes password hashing with bcrypt and token refresh mechanism.

Closes #123
```

```bash
fix(api): resolve memory leak in request handler

The request handler was not properly releasing resources after
each request, causing memory to accumulate over time.

Fixes #456
```

```bash
docs: create comprehensive CLAUDE.md guide

Add detailed documentation for AI assistants including codebase
structure, development workflows, and coding conventions.
```

### Commit Signing
All commits in this repository are signed using SSH keys:
- **Signing Method:** SSH
- **Key Location:** `/home/claude/.ssh/commit_signing_key.pub`
- This is configured automatically and should not require manual intervention

### Push/Pull Best Practices

**Pushing:**
```bash
# First push of a new branch
git push -u origin claude/feature-name-abc12

# Subsequent pushes
git push
```

**Network Retry Policy:**
- If push/pull fails due to network errors, retry up to 4 times
- Use exponential backoff: 2s, 4s, 8s, 16s between retries

**Fetching Updates:**
```bash
# Fetch specific branch
git fetch origin <branch-name>

# Pull with specific branch
git pull origin <branch-name>
```

---

## Code Conventions

> **Note:** These conventions should be updated once the primary technology stack is established.

### General Principles

1. **Readability First**
   - Code is read more often than written
   - Use descriptive variable and function names
   - Add comments only when logic isn't self-evident

2. **Simplicity Over Complexity**
   - Avoid over-engineering
   - Don't add features beyond requirements
   - Prefer simple solutions to clever ones

3. **Consistency**
   - Follow existing patterns in the codebase
   - Match the style of surrounding code
   - Use established conventions for the language/framework

4. **Security**
   - Never commit secrets or credentials
   - Validate user input at system boundaries
   - Avoid common vulnerabilities (XSS, SQL injection, etc.)
   - Follow OWASP Top 10 guidelines

### File Organization

**Python Package Structure:**

```
cull-the-herd/
├── src/
│   └── photo_critic/       # Main package
│       ├── __init__.py     # Package initialization
│       ├── cli.py          # Click CLI entry point
│       ├── discovery.py    # Image finding logic
│       ├── prepare.py      # Image preprocessing
│       ├── batch.py        # Anthropic batch API client
│       └── report.py       # Output generation
├── tests/                  # Test files
│   ├── __init__.py
│   ├── test_discovery.py
│   ├── test_prepare.py
│   ├── test_batch.py
│   └── test_report.py
├── pyproject.toml          # Project metadata and dependencies
├── README.md               # User documentation
├── CLAUDE.md              # AI assistant guide (this file)
├── agents.md              # Architecture documentation
└── .gitignore             # Git ignore patterns
```

### Python Conventions

Follow **PEP 8** style guide with these specifics:

1. **Type Hints:** Use type hints for all function signatures
   ```python
   def discover_images(path: Path, recursive: bool = False) -> list[Path]:
       """Find all supported images in directory."""
   ```

2. **Docstrings:** Use Google-style docstrings
   ```python
   def process_image(path: Path) -> dict:
       """Process a single image for batch submission.

       Args:
           path: Path to the image file

       Returns:
           Dictionary containing the batch request

       Raises:
           ValueError: If image is corrupt or unsupported
       """
   ```

3. **Imports:** Group imports (stdlib, third-party, local)
   ```python
   import os
   from pathlib import Path

   from anthropic import Anthropic
   from PIL import Image

   from photo_critic.utils import resize_image
   ```

4. **Error Handling:** Be explicit about exceptions
   - Use specific exception types
   - Log warnings for non-critical errors (skip corrupt images)
   - Fail fast for critical errors (API key missing, batch submission failed)

5. **Line Length:** 88 characters (Black formatter default)

6. **Naming:**
   - Functions/variables: `snake_case`
   - Classes: `PascalCase`
   - Constants: `UPPER_SNAKE_CASE`
   - Private: `_leading_underscore`

### Testing Standards

- Write tests for new features
- Update tests when changing functionality
- Maintain test coverage above 80%
- Run tests before committing: `uv run pytest`
- Include both unit and integration tests
- Mock external API calls in tests

---

## AI Assistant Guidelines

### Core Responsibilities

When working on this repository, AI assistants should:

1. **Analyze Before Acting**
   - Read existing files before modifying
   - Understand current patterns and conventions
   - Ask questions when requirements are unclear

2. **Maintain Context**
   - Keep track of changes across multiple files
   - Consider downstream effects of modifications
   - Update related documentation when code changes

3. **Be Thorough**
   - Don't skip error handling
   - Consider edge cases
   - Test changes when possible
   - Update tests when changing functionality

4. **Communicate Clearly**
   - Explain what changes you're making and why
   - Highlight potential issues or trade-offs
   - Document non-obvious decisions
   - Use clear commit messages

### What to Do

✅ **DO:**
- Read files before editing them
- Follow existing patterns and conventions
- Write clear, descriptive commit messages
- Ask for clarification when needed
- Break down complex tasks into steps
- Update documentation when changing functionality
- Test your changes
- Consider security implications
- Keep code simple and maintainable
- Use the designated feature branch

### What NOT to Do

❌ **DON'T:**
- Make changes without reading existing code first
- Add features beyond what was requested
- Commit secrets, credentials, or sensitive data
- Push to main/master without approval
- Use `git push --force` unless explicitly requested
- Skip commit signing or hooks
- Guess at unclear requirements
- Over-engineer simple solutions
- Create unnecessary abstractions
- Add backwards-compatibility hacks for removed code
- Push to branches other than the designated feature branch

### Workflow Checklist

Before considering a task complete:

- [ ] All requested changes implemented
- [ ] Existing code patterns followed
- [ ] No security vulnerabilities introduced
- [ ] Code is clear and maintainable
- [ ] Related documentation updated
- [ ] Tests written/updated (when applicable)
- [ ] Changes committed with clear messages
- [ ] Pushed to correct feature branch
- [ ] PR created with comprehensive description

---

## Project Structure

### Full Structure
```
cull-the-herd/
├── .git/                   # Git internal directory
├── .gitignore              # Git ignore patterns
├── README.md               # User-facing documentation
├── CLAUDE.md              # This file - AI assistant guide
├── agents.md              # Architecture documentation
├── pyproject.toml          # Package metadata and dependencies
├── src/
│   └── photo_critic/       # Main package
│       ├── __init__.py     # Package exports
│       ├── cli.py          # CLI entry point (Click)
│       ├── discovery.py    # Image file discovery
│       ├── prepare.py      # Image preprocessing
│       ├── batch.py        # Anthropic batch API client
│       └── report.py       # Report generation
└── tests/                  # Test suite
    ├── __init__.py
    ├── test_discovery.py
    ├── test_prepare.py
    ├── test_batch.py
    └── test_report.py
```

### Module Responsibilities

#### `cli.py`
- Entry point for `photo-critic` command
- Argument parsing with Click
- Orchestrates the full pipeline
- Progress display with Rich

#### `discovery.py`
- Find image files in directory
- Filter by extension (.jpg, .jpeg, .png, .webp, .heic)
- Exclude thumbnails and cached files
- Support recursive directory traversal

#### `prepare.py`
- Image preprocessing (resize, convert)
- Base64 encoding for API
- HEIC to JPEG conversion
- Request formatting for batch API

#### `batch.py`
- Anthropic batch API client
- Batch submission
- Status polling
- Result collection
- Retry logic with exponential backoff

#### `report.py`
- Parse batch results
- Generate JSON reports
- Generate Markdown reports
- Calculate statistics (mean score, distribution)
- Sort and tier images by score

---

## Key Files and Directories

### Configuration Files

#### `pyproject.toml`
- **Purpose:** Package metadata, dependencies, and build configuration
- **Format:** TOML (PEP 621)
- **Key sections:**
  - `[project]`: Package name, version, description, authors
  - `[project.dependencies]`: Runtime dependencies
  - `[project.optional-dependencies]`: Dev dependencies
  - `[project.scripts]`: CLI entry point (`photo-critic`)
  - `[tool.pytest]`: Test configuration

#### `.gitignore`
- **Purpose:** Exclude files from version control
- **Excludes:**
  - Python artifacts: `__pycache__/`, `*.pyc`, `.pytest_cache/`
  - Virtual environments: `venv/`, `.venv/`, `env/`
  - Build artifacts: `dist/`, `build/`, `*.egg-info/`
  - IDE files: `.vscode/`, `.idea/`, `*.swp`
  - Output files: `critic-report.json`, `critic-report.md`
  - Environment: `.env`, `.env.local`

### Documentation Files

#### `README.md`
- **Purpose:** User-facing documentation and installation guide
- **Audience:** End users and contributors
- **Contents:** Installation, usage examples, CLI options, features

#### `CLAUDE.md` (this file)
- **Purpose:** Guide for AI assistants working on this codebase
- **Audience:** Claude and other AI assistants
- **Contents:** Architecture, conventions, workflows, guidelines

#### `agents.md`
- **Purpose:** Detailed architecture and system design documentation
- **Audience:** Developers and AI assistants
- **Contents:** System overview, processing pipeline, API details, cost estimates

### Environment Variables

Required environment variables:

```bash
# Required: Anthropic API key
ANTHROPIC_API_KEY=sk-ant-api03-...
```

Optional environment variables:

```bash
# Optional: Override default model
PHOTO_CRITIC_MODEL=claude-sonnet-4-5-20250929

# Optional: Default output directory
PHOTO_CRITIC_OUTPUT_DIR=./reports

# Optional: API request timeout (seconds)
PHOTO_CRITIC_TIMEOUT=300
```

---

## Git Configuration

### Repository Configuration

```ini
[core]
    repositoryformatversion = 0
    filemode = true
    logallrefupdates = true
[commit]
    gpgsign = true
[user]
    signingkey = /home/claude/.ssh/commit_signing_key.pub
[gpg]
    format = ssh
[gc]
    auto = 0
```

### Remote Origin
```
http://local_proxy@127.0.0.1:36978/git/michaelcolenso/cull-the-herd
```

---

## Maintenance Notes

### Updating This Document

This document should be updated when:
- Technology stack is chosen and configured
- Directory structure is established
- Coding conventions are agreed upon
- New tools or frameworks are added
- Development workflow changes
- New team conventions are established

### Version History

- **2026-01-07 (v2):** Updated for Photo Critic project
  - Added Python-specific conventions and type hints
  - Documented Photo Critic architecture and purpose
  - Added module responsibilities and structure
  - Included environment variable documentation
  - Added testing standards and error handling guidelines

- **2026-01-07 (v1):** Initial version created
  - Documented repository state at initialization
  - Established git conventions and workflow
  - Created AI assistant guidelines
  - Set up structure for future updates

---

## Questions or Issues?

If you encounter ambiguities or need clarification:
1. Check existing code patterns first
2. Review similar projects for conventions
3. Ask the repository owner for guidance
4. Document your decision rationale in commit messages

---

**Remember:** This is a living document. Keep it updated as the project evolves!
