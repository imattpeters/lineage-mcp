"""Tests for tools/read_image.py module.

Tests image reading, width-based downscaling, resize=False passthrough,
error handling, change tracking, and the MCP image content conversion.
"""

import base64
import io
import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from PIL import Image

from tests.test_utils import TempWorkspace, run_async


def create_png_bytes(width: int, height: int, color=(200, 30, 30)) -> bytes:
    """Create solid-colour PNG bytes of the given size."""
    output = io.BytesIO()
    Image.new("RGB", (width, height), color).save(output, format="PNG")
    return output.getvalue()


def create_jpeg_bytes(width: int, height: int, color=(30, 30, 200)) -> bytes:
    """Create solid-colour JPEG bytes of the given size."""
    output = io.BytesIO()
    Image.new("RGB", (width, height), color).save(output, format="JPEG", quality=92)
    return output.getvalue()


class TestReadImageBasic(unittest.TestCase):
    """Tests for basic image reading and error paths."""

    def test_read_image_within_limit_passes_through_bytes(self) -> None:
        """Images at or below the width limit return their original bytes."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_image import read_image

            session.clear()
            original_bytes = create_png_bytes(300, 200)
            (ws.path / "small.png").write_bytes(original_bytes)

            parts = run_async(read_image("small.png"))

            self.assertIsInstance(parts, list)
            image_part = parts[0]
            self.assertEqual(image_part.data, original_bytes)
            self.assertEqual(image_part.to_image_content().data, base64.b64encode(original_bytes).decode("utf-8"))
            self.assertIn("no resize applied", parts[1])
            session.clear()

    def test_read_image_not_found_returns_error(self) -> None:
        """Non-existent files return an error string in the list."""
        with TempWorkspace():
            from session_state import session
            from tools.read_image import read_image

            session.clear()

            parts = run_async(read_image("missing.png"))

            self.assertEqual(len(parts), 1)
            self.assertIn("not found", parts[0].lower())
            session.clear()

    def test_read_image_unsupported_extension_returns_error(self) -> None:
        """Files without a supported image suffix are rejected."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_image import read_image

            session.clear()
            ws.create_file("notes.txt", "plain text")

            parts = run_async(read_image("notes.txt"))

            self.assertIn("Not a supported image", parts[0])
            session.clear()

    def test_read_image_corrupt_bytes_returns_error(self) -> None:
        """Text bytes in an image suffix produce a processing error."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_image import read_image

            session.clear()
            (ws.path / "broken.png").write_bytes(b"definitely not a png")

            parts = run_async(read_image("broken.png"))

            self.assertEqual(len(parts), 1)
            self.assertIn("Error", parts[0])
            session.clear()


class TestReadImageResize(unittest.TestCase):
    """Tests for width-based downscaling behaviour."""

    def test_read_image_downscales_wide_png_to_max_width(self) -> None:
        """A wide png comes back at the configured max width."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_image import read_image

            session.clear()
            (ws.path / "wide.png").write_bytes(create_png_bytes(2048, 800))

            parts = run_async(read_image("wide.png"))

            self.assertIn("resized to 1024px wide (from 2048px)", parts[1])
            decoded = Image.open(io.BytesIO(parts[0].data))
            self.assertEqual(decoded.size, (1024, 400))
            session.clear()

    def test_read_image_resize_false_returns_original_bytes(self) -> None:
        """resize=False skips downscaling and returns the untouched bytes."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_image import read_image

            session.clear()
            original_bytes = create_png_bytes(2048, 800)
            (ws.path / "wide.png").write_bytes(original_bytes)

            parts = run_async(read_image("wide.png", resize=False))

            self.assertEqual(parts[0].data, original_bytes)
            self.assertIn("no resize applied", parts[1])
            session.clear()

    def test_read_image_downscales_wide_jpeg_and_reencodes_jpeg(self) -> None:
        """A wide jpeg returns jpeg bytes at the max width."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_image import read_image

            session.clear()
            (ws.path / "wide.jpg").write_bytes(create_jpeg_bytes(1600, 900))

            parts = run_async(read_image("wide.jpg"))

            self.assertIn("image/jpeg", parts[1])
            decoded = Image.open(io.BytesIO(parts[0].data))
            self.assertEqual(decoded.format, "JPEG")
            self.assertEqual(decoded.size, (1024, 576))
            session.clear()

    def test_read_image_custom_max_width_override(self) -> None:
        """The max width parameter overrides the configured default."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_image import read_image

            session.clear()
            (ws.path / "wide.png").write_bytes(create_png_bytes(1200, 600))

            parts = run_async(read_image("wide.png", read_image_max_width=600))

            self.assertIn("resized to 600px wide (from 1200px)", parts[1])
            decoded = Image.open(io.BytesIO(parts[0].data))
            self.assertEqual(decoded.size, (600, 300))
            session.clear()

    def test_read_image_downscaled_animated_gif_notes_first_frame(self) -> None:
        """Resizing an animated gif reports that only the first frame is kept."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_image import read_image

            session.clear()
            frames = [Image.new("P", (1200, 400), frame_index) for frame_index in (10, 200)]
            gif_buffer = io.BytesIO()
            frames[0].save(
                gif_buffer, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0
            )
            (ws.path / "spin.gif").write_bytes(gif_buffer.getvalue())

            parts = run_async(read_image("spin.gif"))

            self.assertIn("resized to 1024px wide", parts[1])
            self.assertIn("animated source; resized image uses the first frame", parts[1])
            decoded = Image.open(io.BytesIO(parts[0].data))
            self.assertEqual(decoded.size, (1024, 341))
            session.clear()


class TestReadImageTracking(unittest.TestCase):
    """Tests for change detection integration."""

    def test_read_image_tracks_file_for_change_detection(self) -> None:
        """Read images register the file so later changes are reported."""
        with TempWorkspace() as ws:
            from file_watcher import format_changed_files_section
            from session_state import session
            from tools.read_image import read_image

            session.clear()
            image_path = ws.path / "tracked.png"
            image_path.write_bytes(create_png_bytes(100, 100))

            run_async(read_image("tracked.png"))
            self.assertIn(str(image_path), session.mtimes)

            image_path.write_bytes(create_png_bytes(120, 120, color=(10, 10, 10)))
            changed_section = format_changed_files_section()

            self.assertIn("tracked.png (modified)", changed_section)
            self.assertIn("1-EOF", changed_section)
            session.clear()


class TestReadImageSdk(unittest.TestCase):
    """Tests for the FastMCP conversion to wire content."""

    def test_tool_runner_converts_image_to_image_content(self) -> None:
        """FastMCP converts the returned list into ImageContent plus TextContent."""
        from mcp.server.fastmcp.tools.base import Tool

        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_image import read_image

            session.clear()
            (ws.path / "sdk.png").write_bytes(create_png_bytes(50, 50))

            async def tool_body() -> list:
                return await read_image("sdk.png")

            tool = Tool.from_function(tool_body, name="read_image")
            converted_content_blocks = run_async(tool.run({}, convert_result=True))

            self.assertEqual(converted_content_blocks[0].type, "image")
            self.assertEqual(converted_content_blocks[0].mimeType, "image/png")
            self.assertIn("Image read:", converted_content_blocks[1].text)
            session.clear()

    def test_read_pointer_for_image_via_read_file(self) -> None:
        """read() on an image suggests read_image instead of failing."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()
            image_path = ws.path / "pointer.png"
            image_path.write_bytes(create_png_bytes(20, 20))

            result = run_async(read_file("pointer.png"))

            self.assertIn("read_image", result)
            self.assertIn("downscaled to the configured max width", result)
            self.assertNotIn("Error reading file", result)
            session.clear()


if __name__ == "__main__":
    unittest.main()
