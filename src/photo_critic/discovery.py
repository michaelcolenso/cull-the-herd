"""Image discovery module for finding images in directories."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported image formats
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}

# Minimum file size to avoid thumbnails and tiny images (100KB)
MIN_FILE_SIZE = 100 * 1024

# Directory patterns to exclude
EXCLUDED_DIRS = {"_cache", "__MACOSX", "thumbnails", ".thumbnails"}


def discover_images(
    path: Path, recursive: bool = False, max_images: int | None = None
) -> list[Path]:
    """Find all supported images in directory.

    Supported formats: .jpg, .jpeg, .png, .webp, .heic
    Excludes: thumbnails, _cache folders, files < 100KB

    Args:
        path: Directory path to search
        recursive: If True, search subdirectories
        max_images: Optional limit on number of images to return

    Returns:
        List of Path objects for discovered images, sorted by modification time

    Raises:
        ValueError: If path doesn't exist or isn't a directory
        PermissionError: If directory cannot be read
    """
    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")

    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    logger.info(f"Discovering images in: {path} (recursive={recursive})")

    images: list[Path] = []

    try:
        # Use rglob for recursive, glob for non-recursive
        pattern = "**/*" if recursive else "*"

        for file_path in path.glob(pattern):
            # Skip if not a file
            if not file_path.is_file():
                continue

            # Skip if in excluded directory
            if any(excluded in file_path.parts for excluded in EXCLUDED_DIRS):
                logger.debug(f"Skipping (excluded dir): {file_path}")
                continue

            # Check extension (case-insensitive)
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            # Check minimum file size
            try:
                if file_path.stat().st_size < MIN_FILE_SIZE:
                    logger.debug(
                        f"Skipping (too small): {file_path} "
                        f"({file_path.stat().st_size} bytes)"
                    )
                    continue
            except OSError as e:
                logger.warning(f"Cannot stat file {file_path}: {e}")
                continue

            images.append(file_path)
            logger.debug(f"Discovered: {file_path}")

            # Stop if we've reached the max
            if max_images and len(images) >= max_images:
                logger.info(f"Reached max_images limit: {max_images}")
                break

    except PermissionError:
        logger.error(f"Permission denied reading directory: {path}")
        raise

    # Sort by modification time (newest first)
    images.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    logger.info(f"Discovered {len(images)} images")
    return images


def filter_by_extension(
    images: list[Path], extensions: set[str] | None = None
) -> list[Path]:
    """Filter images by file extension.

    Args:
        images: List of image paths
        extensions: Set of extensions to keep (e.g., {'.jpg', '.png'})
                   If None, uses all supported extensions

    Returns:
        Filtered list of image paths
    """
    if extensions is None:
        extensions = SUPPORTED_EXTENSIONS

    # Normalize extensions to lowercase with dot
    extensions = {
        ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions
    }

    return [img for img in images if img.suffix.lower() in extensions]


def get_image_stats(images: list[Path]) -> dict[str, int | float]:
    """Get statistics about discovered images.

    Args:
        images: List of image paths

    Returns:
        Dictionary with statistics:
        - total: Total number of images
        - total_size_mb: Total size in MB
        - avg_size_mb: Average size per image in MB
        - by_extension: Count by file extension
    """
    if not images:
        return {
            "total": 0,
            "total_size_mb": 0.0,
            "avg_size_mb": 0.0,
            "by_extension": {},
        }

    total_size = sum(img.stat().st_size for img in images)
    total_size_mb = total_size / (1024 * 1024)
    avg_size_mb = total_size_mb / len(images)

    # Count by extension
    by_extension: dict[str, int] = {}
    for img in images:
        ext = img.suffix.lower()
        by_extension[ext] = by_extension.get(ext, 0) + 1

    return {
        "total": len(images),
        "total_size_mb": round(total_size_mb, 2),
        "avg_size_mb": round(avg_size_mb, 2),
        "by_extension": by_extension,
    }
