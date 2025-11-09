from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from app.models import GraphData

from app.handlers.base import GraphHandler


class ScatterGraphHandler(GraphHandler):
    """Handler for scatter plots"""

    def plot(self, ax: "Axes", data: "GraphData") -> None:
        """
        Plot scatter plot with error handling

        Raises:
            ValueError: If data cannot be plotted
        """
        try:
            kwargs: dict[str, Any] = {"s": data.marker_size, "alpha": data.alpha}
            if data.color:
                kwargs["c"] = data.color

            ax.scatter(data.x, data.y, **kwargs)
        except Exception as e:
            raise ValueError(f"Failed to plot scatter chart: {str(e)}")
