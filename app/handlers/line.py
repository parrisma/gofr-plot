from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from app.models import GraphData

from app.handlers.base import GraphHandler


class LineGraphHandler(GraphHandler):
    """Handler for line graphs"""

    def plot(self, ax: "Axes", data: "GraphData") -> None:
        """
        Plot line graph with error handling

        Raises:
            ValueError: If data cannot be plotted
        """
        try:
            kwargs: dict[str, Any] = {"linewidth": data.line_width, "alpha": data.alpha}
            if data.color:
                kwargs["color"] = data.color

            ax.plot(data.x, data.y, **kwargs)
        except Exception as e:
            raise ValueError(f"Failed to plot line graph: {str(e)}")
