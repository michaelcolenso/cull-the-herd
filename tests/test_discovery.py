"""Tests for discovery module."""

from pathlib import Path

import pytest

from photo_critic.discovery import (
    MIN_FILE_SIZE,
    discover_images,
    filter_by_extension,
    get_image_stats,
)


class TestDiscoverImages:
    """Tests for discover_images function."""

    def test_discover_images_nonexistent_path(self, tmp_path: Path) -> None:
        """Test that ValueError is raised for nonexistent path."""
        fake_path = tmp_path / "nonexistent"
        with pytest.raises(ValueError, match="Path does not exist"):
            discover_images(fake_path)

    def test_discover_images_file_not_directory(self, tmp_path: Path) -> None:
        """Test that ValueError is raised when path is a file."""
        file_path = tmp_path / "test.jpg"
        file_path.touch()
        with pytest.raises(ValueError, match="Path is not a directory"):
            discover_images(file_path)

    def test_discover_images_empty_directory(self, tmp_path: Path) -> None:
        """Test empty directory returns empty list."""
        result = discover_images(tmp_path)
        assert result == []

    def test_discover_images_finds_supported_formats(self, tmp_path: Path) -> None:
        """Test that all supported formats are discovered."""
        # Create test files with supported extensions (> MIN_FILE_SIZE)
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            file_path = tmp_path / f"test{ext}"
            file_path.write_bytes(b"x" * (MIN_FILE_SIZE + 1000))

        result = discover_images(tmp_path)
        assert len(result) == 4

    def test_discover_images_ignores_unsupported_formats(self, tmp_path: Path) -> None:
        """Test that unsupported formats are ignored."""
        # Create unsupported file
        (tmp_path / "test.txt").write_bytes(b"x" * (MIN_FILE_SIZE + 1000))
        (tmp_path / "test.gif").write_bytes(b"x" * (MIN_FILE_SIZE + 1000))
        # Create supported file
        (tmp_path / "test.jpg").write_bytes(b"x" * (MIN_FILE_SIZE + 1000))

        result = discover_images(tmp_path)
        assert len(result) == 1
        assert result[0].suffix == ".jpg"

    def test_discover_images_ignores_small_files(self, tmp_path: Path) -> None:
        """Test that files smaller than MIN_FILE_SIZE are ignored."""
        # Create small file (thumbnail size)
        (tmp_path / "thumbnail.jpg").write_bytes(b"x" * 100)
        # Create normal size file
        (tmp_path / "photo.jpg").write_bytes(b"x" * (MIN_FILE_SIZE + 1000))

        result = discover_images(tmp_path)
        assert len(result) == 1
        assert result[0].name == "photo.jpg"

    def test_discover_images_excludes_cache_directories(self, tmp_path: Path) -> None:
        """Test that excluded directories are skipped."""
        # Create file in excluded directory
        cache_dir = tmp_path / "_cache"
        cache_dir.mkdir()
        (cache_dir / "cached.jpg").write_bytes(b"x" * (MIN_FILE_SIZE + 1000))

        # Create file in normal directory
        (tmp_path / "photo.jpg").write_bytes(b"x" * (MIN_FILE_SIZE + 1000))

        result = discover_images(tmp_path, recursive=True)
        assert len(result) == 1
        assert result[0].name == "photo.jpg"

    def test_discover_images_recursive(self, tmp_path: Path) -> None:
        """Test recursive discovery in subdirectories."""
        # Create subdirectory with image
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.jpg").write_bytes(b"x" * (MIN_FILE_SIZE + 1000))
        (tmp_path / "root.jpg").write_bytes(b"x" * (MIN_FILE_SIZE + 1000))

        # Non-recursive should only find root image
        result = discover_images(tmp_path, recursive=False)
        assert len(result) == 1

        # Recursive should find both
        result = discover_images(tmp_path, recursive=True)
        assert len(result) == 2

    def test_discover_images_max_images_limit(self, tmp_path: Path) -> None:
        """Test that max_images limits the number of results."""
        # Create multiple images
        for i in range(5):
            (tmp_path / f"photo{i}.jpg").write_bytes(b"x" * (MIN_FILE_SIZE + 1000))

        result = discover_images(tmp_path, max_images=3)
        assert len(result) == 3

    def test_discover_images_case_insensitive_extensions(self, tmp_path: Path) -> None:
        """Test that extension matching is case-insensitive."""
        (tmp_path / "photo.JPG").write_bytes(b"x" * (MIN_FILE_SIZE + 1000))
        (tmp_path / "photo.Png").write_bytes(b"x" * (MIN_FILE_SIZE + 1000))

        result = discover_images(tmp_path)
        assert len(result) == 2


class TestFilterByExtension:
    """Tests for filter_by_extension function."""

    def test_filter_by_extension_default(self) -> None:
        """Test filtering with default supported extensions."""
        images = [
            Path("/test/photo.jpg"),
            Path("/test/photo.png"),
            Path("/test/photo.gif"),  # Not supported
        ]
        result = filter_by_extension(images)
        assert len(result) == 2

    def test_filter_by_extension_custom(self) -> None:
        """Test filtering with custom extensions."""
        images = [
            Path("/test/photo.jpg"),
            Path("/test/photo.png"),
            Path("/test/photo.webp"),
        ]
        result = filter_by_extension(images, extensions={".jpg"})
        assert len(result) == 1
        assert result[0].suffix == ".jpg"

    def test_filter_by_extension_normalizes_input(self) -> None:
        """Test that extensions without dots are normalized."""
        images = [Path("/test/photo.jpg"), Path("/test/photo.png")]
        result = filter_by_extension(images, extensions={"jpg"})  # No dot
        assert len(result) == 1


class TestGetImageStats:
    """Tests for get_image_stats function."""

    def test_get_image_stats_empty_list(self) -> None:
        """Test stats for empty image list."""
        result = get_image_stats([])
        assert result["total"] == 0
        assert result["total_size_mb"] == 0.0
        assert result["avg_size_mb"] == 0.0
        assert result["by_extension"] == {}

    def test_get_image_stats_calculates_correctly(self, tmp_path: Path) -> None:
        """Test that stats are calculated correctly."""
        # Create test files with known sizes
        file1 = tmp_path / "photo1.jpg"
        file2 = tmp_path / "photo2.png"
        file1.write_bytes(b"x" * (1024 * 1024))  # 1 MB
        file2.write_bytes(b"x" * (2 * 1024 * 1024))  # 2 MB

        result = get_image_stats([file1, file2])

        assert result["total"] == 2
        assert result["total_size_mb"] == 3.0
        assert result["avg_size_mb"] == 1.5
        assert result["by_extension"] == {".jpg": 1, ".png": 1}

    def test_get_image_stats_extension_counting(self, tmp_path: Path) -> None:
        """Test that extensions are counted correctly."""
        files = []
        for i in range(3):
            f = tmp_path / f"photo{i}.jpg"
            f.write_bytes(b"x" * 1000)
            files.append(f)
        f = tmp_path / "photo.png"
        f.write_bytes(b"x" * 1000)
        files.append(f)

        result = get_image_stats(files)
        assert result["by_extension"][".jpg"] == 3
        assert result["by_extension"][".png"] == 1
