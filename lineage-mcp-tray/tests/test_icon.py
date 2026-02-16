"""Tests for icon generation module."""

from lineage_tray.icon import create_tray_icon, create_tray_icon_with_badge


class TestCreateTrayIcon:
    """Tests for create_tray_icon function."""

    def test_default_size(self):
        icon = create_tray_icon()
        assert icon.size == (64, 64)
        assert icon.mode == "RGBA"

    def test_custom_size(self):
        icon = create_tray_icon(size=32)
        assert icon.size == (32, 32)

    def test_large_size(self):
        icon = create_tray_icon(size=128)
        assert icon.size == (128, 128)


class TestCreateTrayIconWithBadge:
    """Tests for create_tray_icon_with_badge function."""

    def test_no_badge_zero_count(self):
        base = create_tray_icon()
        result = create_tray_icon_with_badge(base, 0)
        assert result.size == base.size
        # Should be a copy, not the same object
        assert result is not base

    def test_badge_with_count(self):
        base = create_tray_icon()
        result = create_tray_icon_with_badge(base, 3)
        assert result.size == base.size
        # The badge modifies the image, so it should differ from base
        assert result is not base

    def test_badge_caps_at_9(self):
        base = create_tray_icon()
        # Should not raise even with count > 9
        result = create_tray_icon_with_badge(base, 15)
        assert result.size == base.size

    def test_does_not_modify_original(self):
        base = create_tray_icon()
        original_data = list(base.tobytes())
        create_tray_icon_with_badge(base, 5)
        assert list(base.tobytes()) == original_data
