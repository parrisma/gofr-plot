# Themes Module

The themes module provides a flexible theming system for graph rendering, allowing users to control colors, fonts, backgrounds, and other visual aspects of matplotlib charts.

## Architecture

- **Theme** (base.py) - Abstract base class defining the theme interface
- **LightTheme** (light.py) - Clean, bright theme with white background
- **DarkTheme** (dark.py) - Muted colors with dark background for reduced eye strain
- **BizLightTheme** (bizlight.py) - Professional business light theme with corporate styling
- **BizDarkTheme** (bizdark.py) - Professional business dark theme for low-glare displays

## Built-in Themes

### Light Theme (Default)
- White background (#FFFFFF)
- Dark text (#000000)
- Light grid (#E0E0E0)
- Blue default color (#1f77b4)
- 8 distinct colors for multi-series plots

### Dark Theme
- Dark background (#1E1E1E)
- Light text (#E0E0E0)
- Dark grid (#3A3A3A)
- Light blue default color (#5DADE2)
- 8 muted colors optimized for dark backgrounds

### BizLight Theme
- Professional business light theme
- Clean white background (#FFFFFF)
- Dark professional text (#222222)
- Subtle grid (#D0D4D9)
- Corporate blue accent (#2F6DB2)
- 8 professional business colors
- DejaVu Sans font (Arial when available via Docker fonts)

### BizDark Theme
- Professional business dark theme for low-glare displays
- Dark background (#0F1113) for reduced eye strain
- High legibility text (#E6E6E6)
- Subdued windowframe-style grid (#3A3F44)
- BTIG-style calm blue accent (#2F6DB2)
- 8 muted professional colors
- DejaVu Sans font (Arial when available via Docker fonts)

## Usage

### Using Built-in Themes

```python
from app.themes import get_theme

# Get a theme
theme = get_theme("dark")

# Apply to matplotlib figure
fig, ax = plt.subplots()
theme.apply(fig, ax)

# Get theme colors
default_color = theme.get_default_color()
colors = theme.get_colors()
```

### Via REST API

```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Chart",
    "x": [1, 2, 3],
    "y": [1, 4, 9],
    "theme": "dark"
  }'
```

## Creating Custom Themes

### Step 1: Define Your Theme

```python
from app.themes.base import Theme
from typing import Dict, Any

class CustomTheme(Theme):
    def __init__(self):
        self.background_color = "#F5F5DC"  # Beige
        self.text_color = "#2C3E50"
        self.grid_color = "#D3D3D3"
        self.default_color = "#E74C3C"
        self.colors = [
            "#E74C3C", "#3498DB", "#2ECC71",
            "#F39C12", "#9B59B6", "#1ABC9C"
        ]
        self.font_family = "serif"
        self.font_size = 11
    
    def apply(self, fig, ax):
        # Set backgrounds
        fig.patch.set_facecolor(self.background_color)
        ax.set_facecolor(self.background_color)
        
        # Set text colors
        ax.title.set_color(self.text_color)
        ax.xaxis.label.set_color(self.text_color)
        ax.yaxis.label.set_color(self.text_color)
        ax.tick_params(colors=self.text_color)
        
        # Set spines
        for spine in ax.spines.values():
            spine.set_edgecolor(self.grid_color)
        
        # Grid
        ax.grid(True, alpha=0.3, color=self.grid_color)
        
        # Fonts
        ax.title.set_fontfamily(self.font_family)
        ax.title.set_fontsize(self.font_size + 2)
    
    def get_default_color(self):
        return self.default_color
    
    def get_colors(self):
        return self.colors
    
    def get_config(self):
        return {
            "name": "custom",
            "background_color": self.background_color,
            "text_color": self.text_color,
            "colors": self.colors
        }
```

### Step 2: Register Your Theme

```python
from app.themes import register_theme

# Register the theme
register_theme("custom", CustomTheme())

# Now it can be used
theme = get_theme("custom")
```

### Step 3: Use Your Theme

```python
from app.graph_params import GraphParams
from app.render import GraphRenderer

renderer = GraphRenderer()
data = GraphParams(
    title="Custom Theme Chart",
    x=[1, 2, 3],
    y=[1, 4, 9],
    theme="custom"  # Use your custom theme
)

image = renderer.render(data)
```

## Theme Interface

All themes must implement:

- `apply(fig, ax)` - Apply theme styling to figure and axes
- `get_default_color()` - Return default plot color
- `get_colors()` - Return list of colors for multi-series
- `get_config()` - Return theme configuration dictionary

## Available Themes

```python
from app.themes import list_themes

# Get all registered themes
themes = list_themes()  # ["light", "dark", ...]
```

## Advanced Customization

Themes can control all matplotlib styling:

- Background colors
- Text colors and fonts
- Grid appearance
- Spine/border colors
- Plot colors
- Font families and sizes
- Line styles
- Marker styles

## Examples

### Minimal Theme
```python
class MinimalTheme(Theme):
    def apply(self, fig, ax):
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(False)
    
    def get_default_color(self):
        return "black"
    
    def get_colors(self):
        return ["black", "gray"]
    
    def get_config(self):
        return {"name": "minimal"}
```

### High Contrast Theme
```python
class HighContrastTheme(Theme):
    def apply(self, fig, ax):
        fig.patch.set_facecolor("black")
        ax.set_facecolor("black")
        ax.tick_params(colors="white")
        ax.spines["bottom"].set_color("white")
        ax.spines["left"].set_color("white")
        ax.grid(True, color="white", alpha=0.3)
    
    def get_default_color(self):
        return "yellow"
    
    def get_colors(self):
        return ["yellow", "cyan", "magenta", "white"]
    
    def get_config(self):
        return {"name": "high_contrast"}
```

## Back to Main Documentation

[← Back to Project README](../README.md)
