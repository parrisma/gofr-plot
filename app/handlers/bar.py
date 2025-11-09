from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from app.models import GraphData

from app.handlers.base import GraphHandler


class BarGraphHandler(GraphHandler):
    """Handler for bar charts"""

    def plot(self, ax: "Axes", data: "GraphData") -> None:
        """
        Plot bar chart with error handling

        Raises:
            ValueError: If data cannot be plotted
        """
        try:
            kwargs: dict[str, Any] = {"alpha": data.alpha}
            if data.color:
                kwargs["color"] = data.color

            ax.bar(data.x, data.y, **kwargs)
        except Exception as e:
            raise ValueError(f"Failed to plot bar chart: {str(e)}")
