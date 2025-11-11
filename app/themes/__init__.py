from typing import Dict
from .base import Theme
from .light import LightTheme
from .dark import DarkTheme
from .bizlight import BizLightTheme
from .bizdark import BizDarkTheme

# Registry of available themes
_THEMES: Dict[str, Theme] = {
    "light": LightTheme(),
    "dark": DarkTheme(),
    "bizlight": BizLightTheme(),
    "bizdark": BizDarkTheme(),
}


def get_theme(name: str = "light") -> Theme:
    """
    Get a theme by name with safe fallback

    Args:
        name: Theme name (light, dark, bizlight, bizdark)

    Returns:
        Theme instance

    Raises:
        ValueError: If theme name is not found and no fallback is available
    """
    try:
        theme_name = name.lower() if name else "light"
        theme = _THEMES.get(theme_name)

        if theme is None:
            available = ", ".join(_THEMES.keys())
            raise ValueError(f"Unknown theme '{name}'. Available themes: {available}")

        return theme
    except Exception as e:
        # If all else fails, return light theme as safe fallback
        if "light" in _THEMES:
            return _THEMES["light"]
        # If even light theme is missing, raise the original error
        raise ValueError(f"Theme system error: {str(e)}")


def register_theme(name: str, theme: Theme) -> None:
    """
    Register a custom theme

    Args:
        name: Theme name
        theme: Theme instance
    """
    _THEMES[name.lower()] = theme


def list_themes() -> list[str]:
    """Get a list of available theme names"""
    return list(_THEMES.keys())


__all__ = [
    "Theme",
    "LightTheme",
    "DarkTheme",
    "BizLightTheme",
    "BizDarkTheme",
    "get_theme",
    "register_theme",
    "list_themes",
]
