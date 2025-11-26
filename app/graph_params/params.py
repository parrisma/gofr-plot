"""Graph rendering parameters

Defines the data model for graph rendering requests.
"""

from pydantic import BaseModel
from typing import List, Optional


class GraphParams(BaseModel):
    """Parameters for rendering a graph with support for up to 5 datasets"""

    title: str

    # X-axis data (optional, defaults to indices if not provided)
    x: Optional[List[float]] = None

    # Y-axis datasets (at least y1 or y is required, up to y5 supported)
    y1: Optional[List[float]] = None  # Made optional for backward compatibility
    y2: Optional[List[float]] = None
    y3: Optional[List[float]] = None
    y4: Optional[List[float]] = None
    y5: Optional[List[float]] = None  # Labels for each dataset (optional)
    label1: Optional[str] = None
    label2: Optional[str] = None
    label3: Optional[str] = None
    label4: Optional[str] = None
    label5: Optional[str] = None

    # Colors for each dataset (optional, uses theme defaults if not provided)
    color1: Optional[str] = None
    color2: Optional[str] = None
    color3: Optional[str] = None
    color4: Optional[str] = None
    color5: Optional[str] = None

    xlabel: str = "X-axis"
    ylabel: str = "Y-axis"
    type: str = "line"  # Validated by GraphDataValidator for better error messages
    format: str = "png"  # Validated by GraphDataValidator for better error messages
    return_base64: bool = True  # False to return image directly
    proxy: bool = False  # If True, save to disk and return GUID instead of base64
    alias: Optional[str] = (
        None  # Optional memorable name for proxy mode (3-64 chars, alphanumeric + hyphens/underscores)
    )
    line_width: float = 2.0  # for line plots
    marker_size: float = 36.0  # for scatter plots
    alpha: float = 1.0  # transparency (0.0 to 1.0)
    theme: str = "light"  # Validated by GraphDataValidator for better error messages

    # Backward compatibility: accept old 'y' parameter and map to y1, old 'color' to color1
    y: Optional[List[float]] = None
    color: Optional[str] = None

    # Axis limits
    xmin: Optional[float] = None  # Minimum value for x-axis
    xmax: Optional[float] = None  # Maximum value for x-axis
    ymin: Optional[float] = None  # Minimum value for y-axis
    ymax: Optional[float] = None  # Maximum value for y-axis

    # Major tick settings
    x_major_ticks: Optional[List[float]] = None  # Custom major tick positions for x-axis
    y_major_ticks: Optional[List[float]] = None  # Custom major tick positions for y-axis

    # Minor tick settings
    x_minor_ticks: Optional[List[float]] = None  # Custom minor tick positions for x-axis
    y_minor_ticks: Optional[List[float]] = None  # Custom minor tick positions for y-axis

    def model_post_init(self, __context) -> None:
        """Handle backward compatibility for old x,y,color parameters"""
        # Map old 'y' to 'y1' if y1 not provided
        if self.y is not None and self.y1 is None:
            object.__setattr__(self, "y1", self.y)

        # Validate that at least y1 or y is provided
        if self.y1 is None and self.y is None:
            raise ValueError(
                "At least one dataset (y1 or y for backward compatibility) is required"
            )

        # Map old 'color' to 'color1' if color1 not provided
        if self.color is not None and self.color1 is None:
            object.__setattr__(self, "color1", self.color)

    def get_datasets(self) -> List[tuple[List[float], Optional[str], Optional[str]]]:
        """
        Get all datasets as list of (y_data, label, color) tuples

        Returns:
            List of tuples containing (y_values, label, color) for each dataset
        """
        datasets = []
        for i in range(1, 6):
            y_attr = f"y{i}"
            label_attr = f"label{i}"
            color_attr = f"color{i}"

            y_data = getattr(self, y_attr, None)
            if y_data is not None:
                label = getattr(self, label_attr, None)
                color = getattr(self, color_attr, None)
                datasets.append((y_data, label, color))

        return datasets

    def get_x_values(self, y_length: int) -> List[float]:
        """
        Get x-axis values, generating indices if not provided

        Args:
            y_length: Length of y dataset to generate matching x values

        Returns:
            X-axis values as list of floats
        """
        if self.x is not None:
            return self.x
        else:
            # Generate indices starting from 0
            return list(range(y_length))


# Backward compatibility alias
GraphData = GraphParams
