import os
import requests
from bs4 import BeautifulSoup
from unidecode import unidecode
from telegraph import upload_file


class GoogleReverseImageSearch:
    """
    A class for performing a reverse image search on Google.
    """

    GOOGLE_IMAGE_SEARCH_URL = "https://images.google.com/searchbyimage?safe=off&sbisrc=tg&client=app&image_url={img_url}"
    USER_AGENT = (
        "Mozilla/5.0 (Linux; Android 6.0.1; SM-G920V Build/MMB29K) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.98 "
        "Mobile Safari/537.36"
    )

    def __init__(self) -> None:
        """
        Initialize the GoogleReverseImageSearch instance.
        """
        self._client = requests.Session()

    @staticmethod
    def _get_image_url(address: str):
        """
        Get the image URL, either from a file upload or directly if it's a URL.

        Returns:
            str: The image URL.
        """
        if os.path.isfile(address):
            assert (
                os.path.getsize(address) <= 5979648
            ), "File size must be less than 5.7 MB"
            return  f"https://graph.org{upload_file(address)[0]}"
        else:
            return address

    def reverse_search_image(self, address: str):
        """
        Perform a reverse image search on Google and retrieve results.

        Returns:
            dict: A dictionary containing search results, including 'similar' and 'output'.
        """
        img_url = self._get_image_url(address=address)
        response = self._client.get(
            url=self.GOOGLE_IMAGE_SEARCH_URL.format(img_url=img_url),
            headers={"User-agent": self.USER_AGENT},
        )
        soup = BeautifulSoup(response.text, "html.parser")
        result = {"similar": response.url, "output": ""}

        # Google's result-snippet CSS class names are short, obfuscated
        # strings that Google regenerates periodically - hardcoding a single
        # one (like the old "r5a77d") silently breaks the moment Google
        # changes it. Try a few known/likely selectors as a best-effort, but
        # never let a failed scrape here block the actual search link below
        # (that's the part that matters and doesn't depend on this at all).
        for selector in (
            {"class": "r5a77d"},
            {"class": "fKDtNb"},
            {"class": "wDYxhc"},
        ):
            for best in soup.find_all("div", selector):
                text = best.get_text(strip=True)
                if text:
                    result["output"] = unidecode(text)
                    break
            if result["output"]:
                break

        if not result["output"]:
            # Fall back to the page <title>, which Google almost always sets
            # to something like "<guess> - Google Search" - still useful,
            # and far less likely to break than a specific CSS class.
            if soup.title and soup.title.string:
                title = soup.title.string.replace("- Google Search", "").strip()
                if title:
                    result["output"] = unidecode(title)

        return result

    @staticmethod
    def get_requirements():
        return ["unidecode", "telegraph", "bs4", "requests"]