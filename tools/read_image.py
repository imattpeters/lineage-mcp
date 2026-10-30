"""Read image tool - returns images to the LLM as MCP image content.

Images wider than the configured maximum width are downscaled before they
reach the model. The AI can request the original bytes with resize=False.
"""

import base64
import io
from pathlib import Path

from path_utils import get_base_dir, get_file_mtime_ms, resolve_path
from session_state import session

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_MIME_TYPES_BY_FORMAT = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "GIF": "image/gif",
    "WEBP": "image/webp",
}
_MIME_TYPES_BY_EXTENSION = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
_JPEG_REENCODE_QUALITY = 85


def is_image_file(file_path: Path) -> bool:
    """Check whether the file suffix is a supported image extension.

    Args:
        file_path: Absolute path to check.

    Returns:
        True for png, jpg, jpeg, gif, and webp suffixes.
    """
    return file_path.suffix.lower() in IMAGE_EXTENSIONS


def _sniff_mime_type(image_bytes: bytes, file_path: Path) -> str:
    """Determine the mime type from the actual image content.

    Falls back to the extension when Pillow cannot read the header, so the
    returned value always matches the bytes that end up in the response.

    Args:
        image_bytes: Raw image bytes.
        file_path: Path whose suffix is the fallback source.

    Returns:
        mime type string such as image/png.
    """
    try:
        from PIL import Image

        with Image.open(io.BytesIO(image_bytes)) as pillow_image:
            format_name = pillow_image.format
        if format_name in _MIME_TYPES_BY_FORMAT:
            return _MIME_TYPES_BY_FORMAT[format_name]
    except Exception:
        pass

    return _MIME_TYPES_BY_EXTENSION.get(file_path.suffix.lower(), "application/octet-stream")


def _resize_image_if_wider(
    image_bytes: bytes,
    max_width: int,
) -> tuple[bytes, int, int, bool]:
    """Downscale the image when it is wider than the maximum width.

    The aspect ratio is preserved, images are never upscaled, and images
    already within the width limit are passed through byte-for-byte.

    Args:
        image_bytes: Raw bytes of a Pillow-readable image.
        max_width: Maximum allowed width in pixels (for example 1024).

    Returns:
        Tuple of (image bytes, original width, returned width, resized flag).
        The bytes equal the input when resized is False.

    Raises:
        Exception: Any Pillow error for unsupported or corrupt images; the
        caller converts it into a tool error message.
    """
    from PIL import Image

    with Image.open(io.BytesIO(image_bytes)) as source_image:
        original_width, original_height = source_image.size
        if original_width <= max_width:
            return image_bytes, original_width, original_width, False

        scale = max_width / original_width
        resized_height = max(1, round(original_height * scale))
        resized_size = (max_width, resized_height)

        # Palette modes produce artifacts when resized directly
        working_image = source_image.convert("RGBA") if source_image.mode in ("P", "1") else source_image
        resized_image = working_image.resize(resized_size, Image.Resampling.LANCZOS)

        target_format = source_image.format or "PNG"
        output_buffer = io.BytesIO()
        if target_format == "JPEG":
            resized_image = resized_image.convert("RGB")
            resized_image.save(output_buffer, format=target_format, quality=_JPEG_REENCODE_QUALITY)
        else:
            resized_image.save(output_buffer, format=target_format)

        return output_buffer.getvalue(), original_width, resized_size[0], True


def _detect_animated_source(image_bytes: bytes) -> bool:
    """Check whether the image contains animation frames.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        True when Pillow reports more than one frame; resizing such an image
        returns only its first frame.
    """
    try:
        from PIL import Image

        with Image.open(io.BytesIO(image_bytes)) as pillow_image:
            return bool(getattr(pillow_image, "is_animated", False)) and pillow_image.n_frames > 1
    except Exception:
        return False


async def read_image(
    file_path: str,
    resize: bool = True,
    read_image_max_width: int | None = None,
) -> list[object]:
    """Read an image file and return it as image content the LLM can see.

    Tracks the file modification time for change detection like read().
    When the image is wider than readImageMaxWidth it is downscaled to that
    width with the aspect ratio preserved; otherwise the original bytes are
    returned untouched.

    Args:
        file_path: Path to the image relative to the base directory.
        resize: Set False to skip downscaling and receive the original bytes.
        read_image_max_width: Optional max width override. If None, uses the
            readImageMaxWidth value from config (default 1024).

    Returns:
        List whose first element is mcp ImageContent-convertible and whose
        second element is a text summary of the read; error paths (unknown
        file, unsupported type, corrupt image, missing Pillow) return a
        single text string describing the problem.
    """
    if read_image_max_width is None:
        from config import READ_IMAGE_MAX_WIDTH

        effective_max_width = READ_IMAGE_MAX_WIDTH
    else:
        effective_max_width = read_image_max_width

    result = resolve_path(file_path)
    if not result.success:
        return [result.error]

    full_path = result.path
    if not full_path.exists():
        return [f"Error: File not found: {file_path} (base directory: {get_base_dir()})"]
    if not full_path.is_file():
        return [f"Error: Path is not a file: {file_path} (base directory: {get_base_dir()})"]
    if not is_image_file(full_path):
        supported = ", ".join(sorted(IMAGE_EXTENSIONS))
        return [f"Error: Not a supported image (expected one of: {supported}): {file_path}"]

    try:
        image_bytes = full_path.read_bytes()
    except OSError as read_error:
        return [f"Error reading file: {read_error}"]

    output_bytes = image_bytes
    original_width = 0
    returned_width = 0
    was_resized = False
    if resize and effective_max_width > 0:
        try:
            output_bytes, original_width, returned_width, was_resized = _resize_image_if_wider(
                output_bytes, effective_max_width
            )
        except Exception as resize_error:
            image_name = full_path.name
            return [f"Error: Image could not be processed ({image_name}): {resize_error}"]

    mime_type = _sniff_mime_type(output_bytes, full_path)
    source_is_animated = was_resized and _detect_animated_source(image_bytes)

    mtime_ms = get_file_mtime_ms(full_path)
    session.track_file(str(full_path), mtime_ms, "")

    from mcp.server.fastmcp.utilities.types import Image

    if was_resized:
        resize_description = f"resized to {returned_width}px wide (from {original_width}px)"
    else:
        resize_description = "no resize applied"
    image_text_summary = f"Image read: {file_path}; {len(output_bytes)} bytes; {mime_type}; {resize_description}"
    if source_is_animated:
        image_text_summary += " (animated source; resized image uses the first frame)"

    return [Image(data=output_bytes), image_text_summary]
