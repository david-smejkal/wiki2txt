class WikiData:
    """Data structure designed to hold parsed data."""

    def __init__(self):
        self.plain_text = None
        self.redirect = None
        self.links = []
        self.categories = []
