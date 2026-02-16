"""Programmatic icon generation for the system tray using Pillow."""

from PIL import Image, ImageDraw, ImageFont


def create_tray_icon(size: int = 64) -> Image.Image:
    """Generate a lineage-mcp tray icon programmatically.

    Design: A stylized "L" on a steel-blue circular background.

    Args:
        size: Icon size in pixels (width and height).

    Returns:
        PIL Image suitable for use as a system tray icon.
    """
    # Create a transparent background
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)

    # Background circle
    padding = 2
    dc.ellipse(
        [padding, padding, size - padding, size - padding],
        fill=(70, 130, 180),  # Steel blue
        outline=(50, 100, 150),
        width=2,
    )

    # Draw "L" letter
    margin = size // 5
    stroke_width = size // 8

    # Vertical stroke
    dc.rectangle(
        [margin, margin, margin + stroke_width, size - margin],
        fill="white",
    )
    # Horizontal stroke
    dc.rectangle(
        [margin, size - margin - stroke_width, size - margin, size - margin],
        fill="white",
    )

    return image


def create_tray_icon_with_badge(
    base_icon: Image.Image, count: int
) -> Image.Image:
    """Add a session count badge to the icon.

    Args:
        base_icon: The base tray icon image.
        count: Number of active sessions. 0 means no badge.

    Returns:
        New PIL Image with the badge overlaid (or a copy if count is 0).
    """
    icon = base_icon.copy()
    if count == 0:
        return icon

    dc = ImageDraw.Draw(icon)
    size = icon.size[0]

    # Red badge circle in bottom-right
    badge_size = size // 3
    badge_x = size - badge_size - 2
    badge_y = size - badge_size - 2
    dc.ellipse(
        [badge_x, badge_y, badge_x + badge_size, badge_y + badge_size],
        fill="red",
    )

    # Count text (cap at 9)
    text = str(min(count, 9))
    try:
        font = ImageFont.truetype("arial.ttf", badge_size - 4)
    except (OSError, IOError):
        font = ImageFont.load_default()

    bbox = dc.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    dc.text(
        (
            badge_x + (badge_size - text_w) // 2,
            badge_y + (badge_size - text_h) // 2 - 1,
        ),
        text,
        fill="white",
        font=font,
    )

    return icon
