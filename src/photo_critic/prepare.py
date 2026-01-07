"""Image preprocessing module for preparing images for batch API submission."""

import base64
import io
import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

# Maximum long edge for API optimization (reduces tokens while preserving quality)
MAX_LONG_EDGE = 1568

# HEIC support
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False
    logger.warning("pillow-heif not installed, HEIC images will be skipped")


# System prompt for photo criticism
PHOTO_CRITIC_SYSTEM_PROMPT = """You are an expert photography critic with deep knowledge of composition, lighting, technical execution, and artistic merit.

Your task is to provide detailed, constructive criticism of photographs. For each image, analyze:

1. **Composition** (0-10): Rule of thirds, leading lines, balance, framing, negative space
2. **Lighting** (0-10): Quality, direction, exposure, dynamic range, mood
3. **Subject Matter** (0-10): Interest, clarity, storytelling, emotional impact
4. **Technical Quality** (0-10): Focus, sharpness, noise, color accuracy, processing

Provide your critique in the following JSON format:

{
  "composition_score": <0-10>,
  "composition_notes": "<brief explanation>",
  "lighting_score": <0-10>,
  "lighting_notes": "<brief explanation>",
  "subject_score": <0-10>,
  "subject_notes": "<brief explanation>",
  "technical_score": <0-10>,
  "technical_notes": "<brief explanation>",
  "overall_score": <average of the four scores>,
  "summary": "<1-2 sentence overall assessment>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "improvements": ["<suggestion 1>", "<suggestion 2>"]
}

Be honest but constructive. Focus on actionable feedback."""


def resize_image(img: Image.Image, max_long_edge: int = MAX_LONG_EDGE) -> Image.Image:
    """Resize image if long edge exceeds max_long_edge.

    Args:
        img: PIL Image object
        max_long_edge: Maximum dimension for long edge

    Returns:
        Resized PIL Image (or original if already smaller)
    """
    width, height = img.size
    long_edge = max(width, height)

    if long_edge <= max_long_edge:
        return img

    # Calculate new dimensions maintaining aspect ratio
    if width > height:
        new_width = max_long_edge
        new_height = int(height * (max_long_edge / width))
    else:
        new_height = max_long_edge
        new_width = int(width * (max_long_edge / height))

    logger.debug(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def convert_heic_to_jpeg(img: Image.Image) -> Image.Image:
    """Convert HEIC image to JPEG format.

    Args:
        img: PIL Image object (HEIC)

    Returns:
        PIL Image in RGB mode
    """
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def encode_image_base64(img: Image.Image, format: str = "JPEG") -> str:
    """Encode PIL Image to base64 string.

    Args:
        img: PIL Image object
        format: Output format (JPEG, PNG)

    Returns:
        Base64-encoded image string
    """
    buffer = io.BytesIO()
    img.save(buffer, format=format, quality=95)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def preprocess_image(path: Path) -> dict[str, str] | None:
    """Preprocess a single image for API submission.

    - Resize if needed (> 1568px long edge)
    - Convert HEIC to JPEG
    - Encode to base64

    Args:
        path: Path to image file

    Returns:
        Dictionary with image data and metadata, or None if processing failed

    Raises:
        ValueError: If image cannot be processed
    """
    try:
        logger.debug(f"Preprocessing: {path}")

        # Check HEIC support
        if path.suffix.lower() == ".heic" and not HEIC_SUPPORTED:
            logger.warning(f"Skipping HEIC image (no support): {path}")
            return None

        # Open image with context manager to ensure file handle is released
        with Image.open(path) as img:
            # Load image data into memory before exiting context
            # This allows the file handle to be released while we continue processing
            img.load()

            # Get original dimensions
            original_width, original_height = img.size

            # Convert HEIC to JPEG
            is_heic = path.suffix.lower() == ".heic"
            if is_heic:
                img = convert_heic_to_jpeg(img)
                format_name = "JPEG"
                media_type = "image/jpeg"
            else:
                # Determine format
                if path.suffix.lower() in {".jpg", ".jpeg"}:
                    format_name = "JPEG"
                    media_type = "image/jpeg"
                elif path.suffix.lower() == ".png":
                    format_name = "PNG"
                    media_type = "image/png"
                elif path.suffix.lower() == ".webp":
                    format_name = "WEBP"
                    media_type = "image/webp"
                else:
                    format_name = "JPEG"
                    media_type = "image/jpeg"

            # Resize if needed
            img = resize_image(img)

            # Encode to base64
            base64_image = encode_image_base64(img, format=format_name)

            processed_width, processed_height = img.size

        logger.debug(f"Preprocessed successfully: {path}")

        return {
            "path": str(path),
            "filename": path.name,
            "base64_data": base64_image,
            "media_type": media_type,
            "original_width": original_width,
            "original_height": original_height,
            "processed_width": processed_width,
            "processed_height": processed_height,
        }

    except Exception as e:
        logger.error(f"Failed to preprocess {path}: {e}")
        return None


def build_batch_request(image_data: dict[str, str], custom_id: str, model: str) -> dict:
    """Build a single batch request for the Anthropic API.

    Args:
        image_data: Preprocessed image data from preprocess_image()
        custom_id: Unique identifier for this request
        model: Claude model to use

    Returns:
        Batch request dictionary in Anthropic format
    """
    return {
        "custom_id": custom_id,
        "params": {
            "model": model,
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_data["media_type"],
                                "data": image_data["base64_data"],
                            },
                        },
                        {
                            "type": "text",
                            "text": "Please critique this photograph according to the system prompt.",
                        },
                    ],
                }
            ],
            "system": PHOTO_CRITIC_SYSTEM_PROMPT,
        },
    }


def prepare_batch(
    images: list[Path], model: str = "claude-sonnet-4-5-20250929"
) -> tuple[list[dict], list[dict]]:
    """Prepare batch of images for API submission.

    Args:
        images: List of image paths
        model: Claude model to use

    Returns:
        Tuple of (batch_requests, image_metadata)
        - batch_requests: List of batch request dictionaries
        - image_metadata: List of metadata for each successfully processed image
    """
    batch_requests = []
    image_metadata = []

    for idx, img_path in enumerate(images):
        # Preprocess image
        img_data = preprocess_image(img_path)

        if img_data is None:
            logger.warning(f"Skipping image (preprocessing failed): {img_path}")
            continue

        # Build batch request
        custom_id = f"img_{idx:04d}_{img_path.stem}"
        request = build_batch_request(img_data, custom_id, model)

        batch_requests.append(request)
        image_metadata.append(
            {
                "custom_id": custom_id,
                "path": str(img_path),
                "filename": img_path.name,
                "original_dimensions": (
                    img_data["original_width"],
                    img_data["original_height"],
                ),
            }
        )

        logger.info(f"Prepared: {img_path.name} ({custom_id})")

    logger.info(f"Prepared {len(batch_requests)} requests from {len(images)} images")

    return batch_requests, image_metadata
