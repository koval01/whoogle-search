from bs4 import BeautifulSoup


class ImageGalleryGenerator:
    """
    A class for generating an image gallery from HTML content.

    This class encapsulates the functionality to extract image cells from provided HTML content,
    generate a Bootstrap grid with images, captions, and sources, and produce a complete image gallery.

    Args:
        html (str): The HTML content containing image cells for the gallery.

    Attributes:
        html (str): The HTML content containing image cells for the gallery.
        image_cells (list): A list to store extracted image cells.
        bootstrap_grid (str): A string containing the initial Bootstrap grid structure.
    """

    def __init__(self, html):
        """
        Initialize the ImageGalleryGenerator instance.

        This constructor initializes the instance with the provided HTML content and initializes
        the lists for storing extracted image cells and the Bootstrap grid structure.

        Args:
            html (str): The HTML content containing image cells for the gallery.
        """
        self.html = html
        self.image_cells = []
        self.bootstrap_grid = "<div class=\"container\"><div class=\"row w-100 m-0\">"

    def extract_image_cells(self):
        """
        Extract image cells from the HTML.

        This method parses the provided HTML content using BeautifulSoup and searches for table rows (tr) containing
        image cells. It extracts the image cells represented by table cells (td) with the specified class name.
        The extracted image cell information is appended to the "image_cells" list attribute of the class.

        Note:
            This method assumes that the "html" attribute has been initialized before calling it.

        Raises:
            AttributeError: If required HTML elements or class attributes are not found in the HTML structure.
        """
        soup = BeautifulSoup(self.html, "lxml")
        rows = soup.find_all("tr")

        for row in rows:
            cells = row.find_all("td", class_="e3goi")
            self.image_cells.append(cells)

    def generate_bootstrap_grid(self):
        """
        Generate a Bootstrap grid with images, captions, and sources.

        This method processes the extracted image cells and generates a Bootstrap grid for the image gallery.
        It iterates through each image cell, extracts the necessary information such as the link, image source,
        caption, and source text. The generated HTML code includes an anchor tag wrapping the image and captions,
        with appropriate Bootstrap classes for responsive layout.

        Note:
            This method assumes that image cells have been extracted before calling it.

        Raises:
            AttributeError: If required HTML elements are not found in the image cell structure.
        """
        for row_cells in self.image_cells:
            for cell in row_cells:
                link = cell.find("a")["href"]
                image_src = cell.find("img")["src"]

                caption_div = cell.find("div", class_="jB2rPd")
                caption = caption_div.find("span", class_="fYyStc").text.strip()
                source = caption_div.find("span", class_="qXLe6d F9iS2e").text.strip()

                image_html = f"""
                    <div class="col-6 col-md-4 col-xl-3 mb-4">
                        <a href="{link}" target="_blank" class="card">
                            <img src="{image_src}" class="card-img-top img-fluid rounded-top" alt="Image">
                            <div class="card-body text-center">
                                <div class="card-text">{caption}</div>
                                <p class="card-text source">{source}</p>
                            </div>
                        </a>
                    </div>
                """
                self.bootstrap_grid += image_html

        self.bootstrap_grid += "</div></div>"

    def generate_gallery(self):
        """
        Generate the complete image gallery.

        This method orchestrates the process of generating a complete image gallery using the provided HTML content.
        It calls the necessary methods to extract image cells from the HTML, generate the Bootstrap grid with images,
        captions, and sources, and returns the resulting HTML code representing the image gallery.

        Returns:
            str: The HTML code representing the complete image gallery with images, captions, and sources.
        """
        self.extract_image_cells()
        self.generate_bootstrap_grid()
        return self.bootstrap_grid
