"""Tests for prepare module."""

import base64
import io
from pathlib import Path

from PIL import Image

from photo_critic.prepare import (
    MAX_LONG_EDGE,
    PHOTO_CRITIC_SYSTEM_PROMPT,
    build_batch_request,
    convert_heic_to_jpeg,
    encode_image_base64,
    prepare_batch,
    preprocess_image,
    resize_image,
)


def create_test_image(
    path: Path, width: int = 800, height: int = 600, format: str = "JPEG"
) -> Path:
    """Create a test image file."""
    img = Image.new("RGB", (width, height), color="red")
    img.save(path, format=format)
    return path


class TestResizeImage:
    """Tests for resize_image function."""

    def test_resize_image_no_resize_needed(self) -> None:
        """Test that small images are not resized."""
        img = Image.new("RGB", (800, 600))
        result = resize_image(img)
        assert result.size == (800, 600)

    def test_resize_image_landscape(self) -> None:
        """Test resizing landscape image (width > height)."""
        img = Image.new("RGB", (3000, 2000))
        result = resize_image(img)
        assert result.size[0] == MAX_LONG_EDGE
        assert result.size[1] == int(2000 * (MAX_LONG_EDGE / 3000))

    def test_resize_image_portrait(self) -> None:
        """Test resizing portrait image (height > width)."""
        img = Image.new("RGB", (2000, 3000))
        result = resize_image(img)
        assert result.size[1] == MAX_LONG_EDGE
        assert result.size[0] == int(2000 * (MAX_LONG_EDGE / 3000))

    def test_resize_image_maintains_aspect_ratio(self) -> None:
        """Test that aspect ratio is maintained after resize."""
        img = Image.new("RGB", (4000, 3000))
        original_ratio = 4000 / 3000
        result = resize_image(img)
        new_ratio = result.size[0] / result.size[1]
        assert abs(original_ratio - new_ratio) < 0.01

    def test_resize_image_exactly_max(self) -> None:
        """Test image exactly at max size is not resized."""
        img = Image.new("RGB", (MAX_LONG_EDGE, 1000))
        result = resize_image(img)
        assert result.size == (MAX_LONG_EDGE, 1000)


class TestConvertHeicToJpeg:
    """Tests for convert_heic_to_jpeg function."""

    def test_convert_rgb_image(self) -> None:
        """Test that RGB images pass through unchanged."""
        img = Image.new("RGB", (100, 100))
        result = convert_heic_to_jpeg(img)
        assert result.mode == "RGB"

    def test_convert_rgba_to_rgb(self) -> None:
        """Test that RGBA images are converted to RGB."""
        img = Image.new("RGBA", (100, 100))
        result = convert_heic_to_jpeg(img)
        assert result.mode == "RGB"

    def test_convert_l_to_rgb(self) -> None:
        """Test that grayscale images are converted to RGB."""
        img = Image.new("L", (100, 100))
        result = convert_heic_to_jpeg(img)
        assert result.mode == "RGB"


class TestEncodeImageBase64:
    """Tests for encode_image_base64 function."""

    def test_encode_returns_string(self) -> None:
        """Test that encoding returns a string."""
        img = Image.new("RGB", (100, 100))
        result = encode_image_base64(img)
        assert isinstance(result, str)

    def test_encode_is_valid_base64(self) -> None:
        """Test that result is valid base64."""
        img = Image.new("RGB", (100, 100))
        result = encode_image_base64(img)
        # Should not raise exception
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_encode_produces_valid_image(self) -> None:
        """Test that decoded base64 is a valid image."""
        img = Image.new("RGB", (100, 100), color="blue")
        result = encode_image_base64(img)
        decoded = base64.b64decode(result)
        reopened = Image.open(io.BytesIO(decoded))
        assert reopened.size == (100, 100)


class TestPreprocessImage:
    """Tests for preprocess_image function."""

    def test_preprocess_jpeg(self, tmp_path: Path) -> None:
        """Test preprocessing a JPEG image."""
        img_path = create_test_image(tmp_path / "test.jpg", 800, 600)
        result = preprocess_image(img_path)

        assert result is not None
        assert result["filename"] == "test.jpg"
        assert result["media_type"] == "image/jpeg"
        assert result["original_width"] == 800
        assert result["original_height"] == 600
        assert "base64_data" in result

    def test_preprocess_png(self, tmp_path: Path) -> None:
        """Test preprocessing a PNG image."""
        img_path = create_test_image(tmp_path / "test.png", 800, 600, format="PNG")
        result = preprocess_image(img_path)

        assert result is not None
        assert result["media_type"] == "image/png"

    def test_preprocess_resizes_large_image(self, tmp_path: Path) -> None:
        """Test that large images are resized."""
        img_path = create_test_image(tmp_path / "large.jpg", 4000, 3000)
        result = preprocess_image(img_path)

        assert result is not None
        assert result["original_width"] == 4000
        assert result["original_height"] == 3000
        assert result["processed_width"] == MAX_LONG_EDGE
        assert result["processed_height"] < 3000

    def test_preprocess_invalid_file(self, tmp_path: Path) -> None:
        """Test that invalid files return None."""
        invalid_path = tmp_path / "invalid.jpg"
        invalid_path.write_text("not an image")
        result = preprocess_image(invalid_path)
        assert result is None

    def test_preprocess_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that nonexistent files return None."""
        result = preprocess_image(tmp_path / "nonexistent.jpg")
        assert result is None


class TestBuildBatchRequest:
    """Tests for build_batch_request function."""

    def test_build_request_structure(self) -> None:
        """Test that request has correct structure."""
        image_data = {
            "base64_data": "dGVzdA==",
            "media_type": "image/jpeg",
        }
        result = build_batch_request(
            image_data, "test_id", "claude-sonnet-4-5-20250929"
        )

        assert result["custom_id"] == "test_id"
        assert "params" in result
        assert result["params"]["model"] == "claude-sonnet-4-5-20250929"
        assert result["params"]["max_tokens"] == 1024
        assert result["params"]["system"] == PHOTO_CRITIC_SYSTEM_PROMPT

    def test_build_request_message_content(self) -> None:
        """Test that message content includes image and text."""
        image_data = {
            "base64_data": "dGVzdA==",
            "media_type": "image/jpeg",
        }
        result = build_batch_request(
            image_data, "test_id", "claude-sonnet-4-5-20250929"
        )

        messages = result["params"]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

        content = messages[0]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "image"
        assert content[1]["type"] == "text"


class TestPrepareBatch:
    """Tests for prepare_batch function."""

    def test_prepare_batch_single_image(self, tmp_path: Path) -> None:
        """Test preparing a batch with a single image."""
        img_path = create_test_image(tmp_path / "photo.jpg")
        requests, metadata = prepare_batch([img_path])

        assert len(requests) == 1
        assert len(metadata) == 1
        assert metadata[0]["filename"] == "photo.jpg"
        assert "img_0000_photo" in metadata[0]["custom_id"]

    def test_prepare_batch_multiple_images(self, tmp_path: Path) -> None:
        """Test preparing a batch with multiple images."""
        paths = []
        for i in range(3):
            path = create_test_image(tmp_path / f"photo{i}.jpg")
            paths.append(path)

        requests, metadata = prepare_batch(paths)

        assert len(requests) == 3
        assert len(metadata) == 3

    def test_prepare_batch_skips_invalid(self, tmp_path: Path) -> None:
        """Test that invalid images are skipped."""
        valid_path = create_test_image(tmp_path / "valid.jpg")
        invalid_path = tmp_path / "invalid.jpg"
        invalid_path.write_text("not an image")

        requests, metadata = prepare_batch([valid_path, invalid_path])

        assert len(requests) == 1
        assert len(metadata) == 1
        assert metadata[0]["filename"] == "valid.jpg"

    def test_prepare_batch_custom_model(self, tmp_path: Path) -> None:
        """Test preparing batch with custom model."""
        img_path = create_test_image(tmp_path / "photo.jpg")
        requests, _ = prepare_batch([img_path], model="claude-opus-4-20250514")

        assert requests[0]["params"]["model"] == "claude-opus-4-20250514"
