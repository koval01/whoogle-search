import io
from datetime import datetime

import matplotlib.pyplot as plt
import seaborn as sns
from flask import g

from app.utils.external_api import get_currency_history


class CurrencyGraph:
    def __init__(self, flask_g: g) -> None:
        """
        Initialize CurrencyGraph with Flask's g object.

        :param flask_g: The Flask's g object containing request parameters.
        """
        self.flask_g = flask_g

        # Fetch currency history data using external API
        self.data: dict = get_currency_history(
            flask_g.request_params.get('start_date'),
            flask_g.request_params.get('end_date'),
            flask_g.request_params.get('symbols'),
            flask_g.request_params.get('base')
        )

        # Extract dates and values from the data
        self.dates: list[datetime] = \
            [
                datetime.strptime(date, "%Y-%m-%d")
                for date in self.data["rates"]
            ]

        self.values: list = \
            [
                rate.get(flask_g.request_params.get('symbols'), 0)  # Get value if key exists, else 0
                for rate in self.data["rates"].values()
            ]

    def create_graph(self) -> plt.Figure:
        """
        Create a currency exchange rate graph.

        :return: Matplotlib figure object containing the graph.
        """
        sns.set_style("darkgrid")

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(self.dates, self.values, marker=None, color="royalblue", linewidth=2)
        ax.fill_between(self.dates, self.values, color="royalblue", alpha=0.3)

        # Set transparent background for both figure and axes
        ax.set_facecolor((0, 0, 0, 0))
        fig.patch.set_alpha(0)

        # Remove axis lines and ticks
        ax.spines['bottom'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.set_xticks([])
        ax.set_yticks([])

        # Adjust layout and margins
        plt.tight_layout()
        plt.margins(0)
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

        # Set a minimal threshold for y-axis
        min_value = min(self.values)
        threshold = min_value - (.1 * min_value)
        plt.ylim(bottom=threshold)

        # Add a small top margin
        plt.subplots_adjust(top=.75)

        return fig

    def get_graph_as_image(self) -> io.BytesIO:
        """
        Convert the graph to an image and return as a byte stream.

        :return: Byte stream containing the graph image.
        """
        plt_ = self.create_graph()
        image_stream = io.BytesIO()
        plt_.savefig(image_stream, format='png', transparent=True)
        plt_.clf()  # Clear the figure
        image_stream.seek(0)
        return image_stream
