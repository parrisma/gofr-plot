from pydantic import BaseModel
from typing import List, Literal, Optional


class GraphData(BaseModel):
    title: str
    x: List[float]
    y: List[float]
    xlabel: str = "X-axis"
    ylabel: str = "Y-axis"
    type: str = "line"  # Validated by GraphDataValidator for better error messages
    format: str = "png"  # Validated by GraphDataValidator for better error messages
    return_base64: bool = True  # False to return image directly
    color: Optional[str] = None  # e.g., "red", "#FF5733", "rgb(255,87,51)"
    line_width: float = 2.0  # for line plots
    marker_size: float = 36.0  # for scatter plots
    alpha: float = 1.0  # transparency (0.0 to 1.0)
    theme: str = "light"  # Validated by GraphDataValidator for better error messages
