import re
import urllib.parse as urlparse
from typing import List
from urllib.parse import parse_qs

import cssutils
from bs4 import BeautifulSoup
from bs4.element import ResultSet, Tag
from cryptography.fernet import Fernet
from flask import render_template

from app.models.config import Config
from app.models.endpoint import Endpoint
from app.models.g_classes import GClasses
from app.request import VALID_PARAMS, MAPS_URL
from app.utils.misc import get_abs_url, read_config_bool
from app.utils.results import (
    BLANK_B64, GOOG_IMG, GOOG_STATIC, G_M_LOGO_URL, LOGO_URL, SITE_ALTS,
    has_ad_content, filter_link_args, append_anon_view, get_site_alt,
)

MAPS_ARGS = ["q", "daddr"]

minimal_mode_sections = ["Top stories", "Images", "People also ask"]
unsupported_g_pages = [
    "support.google.com",
    "accounts.google.com",
    "policies.google.com",
    "google.com/preferences",
    "google.com/intl",
    "advanced_search",
    "tbm=shop"
]


def extract_q(q_str: str, href: str) -> str:
    """Extracts the "q" element from a result link. This is typically
    either the link to a result's website, or a string.

    Args:
        q_str: The result link to parse
        href: The full url to check for standalone "q" elements first,
              rather than parsing the whole query string and then checking.

    Returns:
        str: The "q" element of the link, or an empty string
    """
    return parse_qs(q_str)["q"][0] if ("&q=" in href or "?q=" in href) else ""


def build_map_url(href: str) -> str:
    """Tries to extract known args that explain the location in the url. If a
    location is found, returns the default url with it. Otherwise, returns the
    url unchanged.

    Args:
        href: The full url to check.

    Returns:
        str: The parsed url, or the url unchanged.
    """
    # parse the url
    parsed_url = parse_qs(href)
    # iterate through the known parameters and try build the url
    for param in MAPS_ARGS:
        if param in parsed_url:
            return MAPS_URL + "?q=" + parsed_url[param][0]

    # query could not be extracted returning unchanged url
    return href


def clean_query(query: str) -> str:
    """Strips the blocked site list from the query, if one is being
    used.

    Args:
        query: The query string

    Returns:
        str: The query string without any "-site:..." filters
    """
    return query[:query.find("-site:")] if "-site:" in query else query


def clean_css(css: str, page_url: str) -> str:
    """Removes all remote URLs from a CSS string.

    Args:
        css: The CSS string
        page_url: The page url string

    Returns:
        str: The filtered CSS, with URLs proxied through Whoogle
    """
    sheet = cssutils.parseString(css)
    urls = cssutils.getUrls(sheet)

    for url in urls:
        abs_url = get_abs_url(url, page_url)
        if abs_url.startswith("data:"):
            continue
        css = css.replace(
            url,
            f"{Endpoint.element}?type=image/png&url={abs_url}"
        )

    return css


class Filter:
    # Limit used for determining if a result is a "regular" result or a list
    # type result (such as "people also asked", "related searches", etc)
    RESULT_CHILD_LIMIT = 7

    def __init__(
            self,
            user_key: bytes,
            config: Config,
            root_url="",
            page_url="",
            query="",
            mobile=False) -> None:
        self.soup: BeautifulSoup = BeautifulSoup()
        self.config: Config = config
        self.mobile: bool = mobile
        self.user_key: bytes = user_key
        self.page_url: str = page_url
        self.query: str = query
        self.main_divs: BeautifulSoup = ResultSet("")
        self._elements: int = 0
        self._av: set = set()

        self.root_url = root_url[:-1] if root_url.endswith("/") else root_url

    def __getitem__(self, name):
        return getattr(self, name)

    @property
    def elements(self):
        return self._elements

    def encrypt_path(self, path, is_element=False) -> str:
        """
        Encrypts the provided path string to avoid plaintext results in logs.

        This function encrypts the given 'path' string using the Fernet symmetric encryption algorithm to avoid storing
        sensitive information in plaintext format in logs. If 'is_element' is True, the element paths are encrypted separately
        from text to allow key regeneration once all items have been served to the user.

        Parameters:
            self (object): The object containing the user_key used for encryption.
            path (str): The path string to be encrypted.
            is_element (bool, optional): A flag indicating if the path corresponds to an element. Defaults to False.

        Returns:
            str: The encrypted path string.
        """
        # Encrypts path to avoid plaintext results in logs
        if is_element:
            # Element paths are encrypted separately from text, to allow key
            # regeneration once all items have been served to the user
            enc_path = Fernet(self.user_key).encrypt(path.encode()).decode()
            self._elements += 1
            return enc_path

        return Fernet(self.user_key).encrypt(path.encode()).decode()

    def clean(self, soup) -> BeautifulSoup:
        """
        Cleans and modifies the HTML content.

        This function applies a series of cleaning and modification operations to the 'soup' object, including removing ads,
        block titles, block URLs, and block tabs. It also collapses sections, updates CSS and styling, updates parent elements
        with new classes based on certain criteria, removes specific elements, updates element source attributes for images
        and audio, updates link attributes, swaps site alts, updates form attributes, removes extra scripts, and updates
        default footer and header. Finally, it removes search results from blocked sites based on the 'config' attribute.

        Parameters:
            self (object): The object containing various configurations and preferences for the cleaning process.
            soup (BeautifulSoup): The BeautifulSoup object representing the parsed HTML content.

        Returns:
            BeautifulSoup: The cleaned and modified BeautifulSoup object.
        """
        self.soup = soup
        self.main_divs = self.soup.find('div', {'id': 'main'})
        self.remove_ads()
        self.remove_block_titles()
        self.remove_block_url()
        self.collapse_sections()
        self.update_css()
        self.update_styling()
        self.remove_block_tabs()
        self.disable_theme_link()

        self.updater_parent(soup, [
            {"selector": GClasses.result_class_a,
             "class": "result"},
            {"selector": GClasses.result_class_a,
             "class": "search-settings", "s_id": "st-card"},
            {"selector": GClasses.swiper_images,
             "class": "img-swiper"},
            {"selector": GClasses.additional_result,
             "class": "additional-result", "tag": "span"},
            {"selector": GClasses.result_class_images,
             "class": "images-ct", "tag": "table"},
            {"selector": GClasses.sugges_search,
             "class": "suggest-ct", "s_id": "scc"},
            {"selector": GClasses.next_page_button,
             "class": "next-page-button"},
        ])

        self.remove_element(soup, [
            {"tag": "title", "cls": None},
            {"tag": "table", "cls": "bookcf"},
            {"tag": "span", "cls": "unknown_loc"}
        ])

        for img in [_ for _ in self.soup.find_all('img') if 'src' in _.attrs]:
            self.update_element_src(img, "image/png")

        for audio in [_ for _ in self.soup.find_all('audio') if 'src' in _.attrs]:
            self.update_element_src(audio, "audio/mpeg")

        for link in self.soup.find_all('a', href=True):
            self.update_link(link)

        if self.config.alts:
            self.site_alt_swap()

        input_form = self.soup.find('form')
        if input_form is not None:
            input_form["method"] = "GET" if self.config.get_only else "POST"
            # Use a relative URI for submissions
            input_form["action"] = "search"

        # Ensure no extra scripts passed through
        for script in self.soup('script'):
            script.decompose()

        # Update default footer and header
        footer = self.soup.find('footer')
        if footer:
            # Remove divs that have multiple links beyond just page navigation
            [_.decompose() for _ in footer.find_all("div", recursive=False)
             if len(_.find_all("a", href=True)) > 3]
            for link in footer.find_all('a', href=True):
                link['href'] = f'{link["href"]}&preferences={self.config.preferences}'

        header = self.soup.find('header')
        if header:
            header.decompose()

        self.remove_site_blocks(self.soup)
        return self.soup

    def remove_site_blocks(self, soup) -> None:
        """
        Removes search results from the HTML content based on blocked sites specified in the 'config' attribute.

        This function removes specific search results from the 'soup' object based on the blocked sites specified in the
        'config' attribute of the object. It uses a search string created by joining the blocked sites with "-site:" to
        exclude those sites from the search results. The function then finds and modifies the selected search results by
        removing the search string from the text.

        Parameters:
            self (object): The object containing the 'config' attribute specifying the blocked sites.
            soup (BeautifulSoup): The BeautifulSoup object representing the parsed HTML content.

        Returns:
            None: This function does not return any value. It modifies the 'soup' object in place by removing blocked search results.
        """
        if not self.config.block or not soup.body:
            return
        search_string = " ".join(["-site:" +
                                  _ for _ in self.config.block.split(",")])
        selected = soup.body.findAll(string=re.compile(search_string))

        for result in selected:
            result.string.replace_with(result.string.replace(
                search_string, ""))

    @staticmethod
    def updater_parent(soup: BeautifulSoup, classes: List[dict]) -> None:
        """
        Updates the parent elements of HTML elements in the BeautifulSoup object based on given class specifications.

        This static method modifies the parent elements of certain HTML elements in the 'soup' object by adding a new class
        to the parent elements. The new class is determined based on the specifications provided in the 'classes' list. Each
        class specification in the list is a dictionary containing 'tag', 'selector', 's_id', and 'class' keys. 'tag' and
        'selector' represent the HTML tag and class attributes of the elements to update their parent, respectively. 's_id'
        is an optional key representing the 'id' attribute of the elements to further refine the selection. 'class' is the
        new class to be added to the parent elements.

        Parameters:
            soup (BeautifulSoup): The BeautifulSoup object representing the parsed HTML content.
            classes (List[dict]): A list of dictionaries containing class specifications, where each dictionary has 'tag',
                                  'selector', 's_id', and 'class' keys representing the HTML tag, class attributes, optional
                                  'id' attribute, and the new class to be added to the parent elements.

        Returns:
            None: This method does not return any value. It modifies the 'soup' object in place by updating parent elements.
        """
        for cl in classes:
            if "s_id" not in cl.keys():
                cl["s_id"] = ""
            for el in soup.find_all(
                    cl["tag"] if "tag" in cl.keys() else "div",
                    attrs={"class": cl["selector"], "id": cl["s_id"]}
            ):
                try:
                    el.parent["class"]
                except KeyError:
                    el.parent["class"] = []
                el.parent["class"].append(f'p-{cl["class"]}')

    @staticmethod
    def remove_element(soup: BeautifulSoup, elements: List[dict]) -> None:
        """
        Removes HTML elements from the BeautifulSoup object based on given element specifications.

        This static method removes specific HTML elements from the 'soup' object based on the element specifications provided
        in the 'elements' list. Each element specification in the list is a dictionary containing 'tag' and 'cls' keys, which
        represent the HTML tag and class attributes of the element to be removed.

        Parameters:
            soup (BeautifulSoup): The BeautifulSoup object representing the parsed HTML content.
            elements (List[dict]): A list of dictionaries containing element specifications, where each dictionary has 'tag'
                                   and 'cls' keys representing the HTML tag and class attributes of the element to remove.

        Returns:
            None: This method does not return any value. It modifies the 'soup' object in place by removing specified elements.
        """
        for el in elements:
            selector = soup.find(
                el["tag"],
                attrs={"class": el["cls"]}
            )

            if selector:
                selector.decompose()

    def remove_ads(self) -> None:
        """
        Removes advertisements from the list of search result divs in the HTML content.

        This function scans through the 'main_divs' of the object and attempts to remove ads based on the 'has_ad_content'
        function. If 'main_divs' is not available, it simply returns without performing any action.

        Parameters:
            self (object): The object containing the HTML content in 'main_divs'.

        Returns:
            None: This function does not return any value. It modifies the HTML content in place by removing ads.
        """
        if not self.main_divs:
            return

        for div in [_ for _ in self.main_divs.find_all("div", recursive=True)]:
            div_ads = [_ for _ in div.find_all("span", recursive=True)
                       if has_ad_content(_.text)]
            div.decompose() if len(div_ads) else None

    def remove_block_titles(self) -> None:
        """
        Removes block titles from the HTML content based on a regular expression.

        This function removes specific HTML titles from the 'main_divs' of the object based on the regular expression provided
        in the 'block_title' attribute of the 'config' object. It first checks if 'main_divs' and 'config.block_title' are
        both available. If not, it simply returns without performing any action.

        Parameters:
            self (object): The object containing the HTML content in 'main_divs' and the 'config' object with the
                           'block_title' attribute containing the regular expression to match titles.

        Returns:
            None: This function does not return any value. It modifies the HTML content in place by removing block titles.
        """
        if not self.main_divs or not self.config.block_title:
            return
        block_title = re.compile(self.config.block_title)
        for div in [_ for _ in self.main_divs.find_all("div", recursive=True)]:
            block_divs = [_ for _ in div.find_all("h3", recursive=True)
                          if block_title.search(_.text) is not None]
            div.decompose() if len(block_divs) else None

    def remove_block_url(self) -> None:
        """
        Removes block URLs from the HTML content based on a regular expression.

        This function removes specific URLs from the HTML content based on the regular expression provided in the 'block_url'
        attribute of the 'config' object. It first checks if 'main_divs' and 'config.block_url' are both available, and if
        not, it simply returns without performing any action.

        Parameters:
            self (object): The object containing the HTML content in 'main_divs' and the 'config' object with the
                           'block_url' attribute containing the regular expression to match URLs.

        Returns:
            None: This function does not return any value. It modifies the HTML content in place by removing block URLs.
        """
        if not self.main_divs or not self.config.block_url:
            return
        block_url = re.compile(self.config.block_url)
        for div in [_ for _ in self.main_divs.find_all("div", recursive=True)]:
            block_divs = [_ for _ in div.find_all("a", recursive=True)
                          if block_url.search(_.attrs["href"]) is not None]
            div.decompose() if len(block_divs) else None

    def disable_theme_link(self) -> None:
        """
        Disables the theme link in the HTML content.

        This function finds the last occurrence of a link with the class "xeDNfc" within the "main_divs" HTML content.
        If such a link is found, it will be converted into a paragraph tag ("<p>") and the 'href' and 'rel' attributes
        will be removed, effectively disabling the link.

        Parameters:
            self (object): The object containing the HTML content in the 'main_divs' attribute.

        Returns:
            None: This function does not return any value. It modifies the HTML content in place.
        """
        if not self.main_divs or not self.config.block_url:
            return
        __tag = self.main_divs.find_all("a", {"class": "xeDNfc"})[-1:]

        # change if found tag
        if __tag:
            t = __tag[0]
            t.name = "p"
            del t['href']
            del t["rel"]

    def remove_block_tabs(self) -> None:
        """
        Removes block tabs from the HTML content.

        This function finds and removes specific block tabs with the corresponding class names. It looks for block tabs
        with class '{GClasses.main_tbm_tab}' in the 'main_divs' of the object. If found, those block tabs will be removed.
        If 'main_divs' is not available (indicating being in the 'images' tab), it will look for block tabs with class
        '{GClasses.images_tbm_tab}' in the overall soup object, and then remove them.

        Parameters:
            self (object): The object containing the HTML content and the class attributes '{GClasses.main_tbm_tab}' and
                           '{GClasses.images_tbm_tab}'.

        Returns:
            None: This function does not return any value. It modifies the HTML content in place by removing block tabs.
        """
        if self.main_divs:
            for div in self.main_divs.find_all(
                    'div',
                    attrs={'class': f'{GClasses.main_tbm_tab}'}
            ):
                div.decompose()
        else:
            # when in images tab
            for div in self.soup.find_all(
                'div',
                attrs={'class': f'{GClasses.images_tbm_tab}'}
            ):
                div.decompose()

    def collapse_sections(self) -> None:
        """Collapses long result sections ("people also asked", "related
         searches", etc) into "details" elements

        These sections are typically the only sections in the results page that
        have more than ~5 child divs within a primary result div.

        Returns:
            None (The soup object is modified directly)
        """
        minimal_mode = read_config_bool("WHOOGLE_MINIMAL")

        def pull_child_divs(result_div: BeautifulSoup):
            try:
                return result_div.findChildren(
                    "div", recursive=False
                )[0].findChildren(
                    "div", recursive=False)
            except IndexError:
                return []

        if not self.main_divs:
            return

        # Loop through results and check for the number of child divs in each
        for result in self.main_divs.find_all():
            result_children = pull_child_divs(result)
            if minimal_mode:
                if any(f">{x}</span" in str(s) for s in result_children
                       for x in minimal_mode_sections):
                    result.decompose()
                    continue
                for s in result_children:
                    if "Twitter ›" in str(s):
                        result.decompose()
                        continue
                if len(result_children) < self.RESULT_CHILD_LIMIT:
                    continue
            else:
                if len(result_children) < self.RESULT_CHILD_LIMIT:
                    continue

            # Find and decompose the first element with an inner HTML text val.
            # This typically extracts the title of the section (i.e. "Related
            # Searches", "People also ask", etc)
            # If there are more than one child tags with text
            # parenthesize the rest except the first
            label = "Collapsed Results"
            subtitle = None
            for elem in result_children:
                if elem.text:
                    content = list(elem.strings)
                    label = content[0]
                    if len(content) > 1:
                        subtitle = "<span> (" + \
                                   "".join(content[1:]) + ")</span>"
                    elem.decompose()
                    break

            # Create the new details element to wrap around the result's
            # first parent
            parent = None
            idx = 0
            while not parent and idx < len(result_children):
                parent = result_children[idx].parent
                idx += 1

            details = BeautifulSoup(features="html.parser").new_tag("details")
            summary = BeautifulSoup(features="html.parser").new_tag("summary")
            summary.string = label

            if subtitle:
                soup = BeautifulSoup(subtitle, "html.parser")
                summary.append(soup)

            details.append(summary)

            if parent and not minimal_mode:
                parent.wrap(details)
            elif parent and minimal_mode:
                # Remove parent element from document if "minimal mode" is
                # enabled
                parent.decompose()

    def update_element_src(self, element: Tag, mime: str, attr="src") -> None:
        """Encrypts the original src of an element and rewrites the element src
        to use the "/element?src=" pass-through.

        Returns:
            None (The soup element is modified directly)

        """
        src = element[attr].split(" ")[0]

        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("data:"):
            return

        if src.startswith(LOGO_URL):
            # Re-brand with Whoogle logo
            element.replace_with(BeautifulSoup(
                render_template("logo.html"),
                features="html.parser"))
            return
        elif src.startswith(G_M_LOGO_URL):
            # Re-brand with single-letter Whoogle logo
            element["src"] = "static/img/favicon/apple-icon.png"
            element.parent["href"] = "home"
            return
        elif src.startswith(GOOG_IMG) or GOOG_STATIC in src:
            element["src"] = BLANK_B64
            return

        element[attr] = f"{self.root_url}/{Endpoint.element}?url=" + (
                self.encrypt_path(
                    src,
                    is_element=True
                ) + "&type=" + urlparse.quote(mime)
        )

    def update_css(self) -> None:
        """Updates URLs used in inline styles to be proxied by Whoogle
        using the /element endpoint.

        Returns:
            None (The soup element is modified directly)

        """
        # Filter all <style> tags
        for style in self.soup.find_all("style"):
            style.string = clean_css(style.string, self.page_url)

        # TODO: Convert remote stylesheets to style tags and proxy all
        # remote requests
        # for link in soup.find_all("link", attrs={"rel": "stylesheet"}):
        # print(link)

    def update_styling(self) -> None:
        # Update CSS classes for result divs
        soup = GClasses.replace_css_classes(self.soup)

        # Remove unnecessary button(s)
        for button in self.soup.find_all("button"):
            button.decompose()

        # Remove svg logos
        for svg in self.soup.find_all("svg"):
            svg.decompose()

        # Update logo
        logo = self.soup.find("a", {"class": "l"})
        if logo and self.mobile:
            logo["style"] = ("display:flex; justify-content:center; "
                             "align-items:center; color:#685e79; "
                             "font-size:18px; ")

        # Fix search bar length on mobile
        try:
            search_bar = self.soup.find("header").find("form").find("div")
            search_bar["style"] = "width: 100%;"
        except AttributeError:
            pass

        # Fix body max width on images tab
        style = self.soup.find('style')
        div = self.soup.find('div', attrs={
            'class': f'{GClasses.images_tbm_tab}'})
        if style and div and not self.mobile:
            css = style.string
            css_html_tag = (
                "html{"
                "font-family: Roboto, Helvetica Neue, Arial, sans-serif;"
                "font-size: 14px;"
                "line-height: 20px;"
                "text-size-adjust: 100%;"
                "word-wrap: break-word;"
                "}"
            )
            css = f"{css_html_tag}{css}"
            css = re.sub("body{(.*?)}",
                         "body{padding:0 8px;margin:0 auto;max-width:736px;}",
                         css)
            style.string = css

    def update_link(self, link: Tag) -> None:
        """Update internal link paths with encrypted path, otherwise remove
        unnecessary redirects and/or marketing params from the url

        Args:
            link: A bs4 Tag element to inspect and update

        Returns:
            None (the tag is updated directly)

        """
        parsed_link = urlparse.urlparse(link["href"])
        if "/url?q=" in link["href"]:
            link_netloc = extract_q(parsed_link.query, link["href"])
        else:
            link_netloc = parsed_link.netloc

        # Remove any elements that direct to unsupported Google pages
        if any(url in link_netloc for url in unsupported_g_pages):
            # FIXME: The "Shopping" tab requires further filtering (see #136)
            # Temporarily removing all links to that tab for now.

            # Replaces the /url google unsupported link to the direct url
            link["href"] = link_netloc
            parent = link.parent

            if "google.com/preferences?hl=" in link_netloc:
                # Handle case where a search is performed in a different
                # language than what is configured. This usually returns a
                # div with the same classes as normal search results, but with
                # a link to configure language preferences through Google.
                # Since we want all language config done through Whoogle, we
                # can safely decompose this element.
                while parent:
                    p_cls = parent.attrs.get("class") or []
                    if f"{GClasses.result_class_a}" in p_cls:
                        parent.decompose()
                        break
                    parent = parent.parent
            else:
                # Remove cases where google links appear in the footer
                while parent:
                    p_cls = parent.attrs.get("class") or []
                    if parent.name == "footer" or f"{GClasses.footer}" in p_cls:
                        link.decompose()
                    parent = parent.parent

            if link.decomposed:
                return

        # Replace href with only the intended destination (no "utm" type tags)
        href = link["href"].replace("https://www.google.com", "")
        result_link = urlparse.urlparse(href)
        q = extract_q(result_link.query, href)

        if q.startswith("/") and q not in self.query and "spell=1" not in href:
            # Internal google links (i.e. mail, maps, etc) should still
            # be forwarded to Google
            link["href"] = "https://google.com" + q
        elif q.startswith("https://accounts.google.com"):
            # Remove Sign-in link
            link.decompose()
            return
        elif "/search?q=" in href:
            # "li:1" implies the query should be interpreted verbatim,
            # which is accomplished by wrapping the query in double quotes
            if "li:1" in href:
                q = '"' + q + '"'
            new_search = "search?q=" + self.encrypt_path(q)

            query_params = parse_qs(urlparse.urlparse(href).query)
            for param in VALID_PARAMS:
                if param not in query_params:
                    continue
                param_val = query_params[param][0]
                new_search += "&" + param + "=" + param_val
            link["href"] = new_search
        elif "url?q=" in href:
            # Strip unneeded arguments
            link["href"] = filter_link_args(q)

            # Add alternate viewing options for results,
            # if the result doesn't already have an AV link
            netloc = urlparse.urlparse(link["href"]).netloc
            if self.config.anon_view and netloc not in self._av:
                self._av.add(netloc)
                append_anon_view(link, self.config)

        else:
            if href.startswith(MAPS_URL):
                # Maps links don't work if a site filter is applied
                link["href"] = build_map_url(link["href"])
            elif (href.startswith("/?") or href.startswith("/search?") or
                  href.startswith("/imgres?")):
                # make sure that tags can be clicked as relative URLs
                link["href"] = href[1:]
            elif href.startswith("/intl/"):
                # do nothing, keep original URL for ToS
                pass
            elif href.startswith("/preferences"):
                # there is no config specific URL, remove this
                link.decompose()
                return
            else:
                link["href"] = href

        if self.config.new_tab and (
                link["href"].startswith("http")
                or link["href"].startswith("imgres?")
        ):
            link["target"] = "_blank"

        # Replace link location if "alts" config is enabled
    def site_alt_swap(self) -> None:
        """Replaces link locations and page elements if "alts" config
        is enabled
        """
        for site, alt in SITE_ALTS.items():
            if site != "medium.com" and alt != "":
                # Ignore medium.com replacements since these are handled
                # specifically in the link description replacement, and medium
                # results are never given their own "card" result where this
                # replacement would make sense.
                # Also ignore if the alt is empty, since this is used to indicate
                # that the alt is not enabled.
                for div in self.soup.find_all('div', text=re.compile(site)):
                    # Use the number of words in the div string to determine if the
                    # string is a result description (shouldn't replace domains used
                    # in desc text).
                    if len(div.string.split(' ')) == 1:
                        div.string = div.string.replace(site, alt)

            for link in self.soup.find_all('a', href=True):
                # Search and replace all link descriptions
                # with alternative location
                link['href'] = get_site_alt(link['href'])
                link_desc = link.find_all(
                    text=re.compile('|'.join(SITE_ALTS.keys())))
                if len(link_desc) == 0:
                    continue

                # Replace link description
                link_desc = link_desc[0]
                if site not in link_desc or not alt:
                    continue

                new_desc = BeautifulSoup(features="html.parser").new_tag("div")
                link_desc.replace_with(new_desc)

                link_str = str(link_desc)

                # Medium links should be handled differently, since 'medium.com'
                # is a common substring of domain names, but shouldn't be
                # replaced (i.e. 'philomedium.com' should stay as it is).
                if 'medium.com' in link_str:
                    if link_str.startswith('medium.com') or '.medium.com' in link_str:
                        link_str = SITE_ALTS['medium.com'] + \
                                   link_str[link_str.find('medium.com') + len('medium.com'):]
                    new_desc.string = link_str
                else:
                    new_desc.string = link_str.replace(site, alt)

    @staticmethod
    def view_image(soup) -> BeautifulSoup:
        """Replaces the soup with a new one that handles mobile results and
        adds the link of the image full res to the results.

        Args:
            soup: A BeautifulSoup object containing the image mobile results.

        Returns:
            BeautifulSoup: The new BeautifulSoup object
        """

        # get some tags that are unchanged between mobile and pc versions
        cor_suggested = soup.find_all("table", attrs={"class": "By0U9"})
        next_pages = soup.find('table', attrs={'class': "uZgmoc"})

        results = []
        # find results div
        results_div = soup.find('div', attrs={'class': "nQvrDb"})
        # find all the results (if any)
        results_all = []
        if results_div:
            results_all = results_div.find_all('div', attrs={'class': "lIMUZd"})

        for item in results_all:
            urls = item.find("a")["href"].split("&imgrefurl=")

            # Skip urls that are not two-element lists
            if len(urls) != 2:
                continue

            img_url = urlparse.unquote(urls[0].replace(
                f"/{Endpoint.imgres}?imgurl=", ""))

            try:
                # Try to strip out only the necessary part of the web page link
                web_page = urlparse.unquote(urls[1].split("&")[0])
            except IndexError:
                web_page = urlparse.unquote(urls[1])

            img_tbn = urlparse.unquote(item.find("a").find("img")["src"])

            results.append({
                "domain": urlparse.urlparse(web_page).netloc,
                "img_url": img_url,
                "web_page": web_page,
                "img_tbn": img_tbn
            })

        soup = BeautifulSoup(render_template("imageresults.html",
                                             length=len(results),
                                             results=results,
                                             view_label="View Image"),
                             features="html.parser")

        # replace correction suggested by google object if exists
        if len(cor_suggested):
            soup.find_all(
                "table",
                attrs={"class": "By0U9"}
            )[0].replaceWith(cor_suggested[0])
        # replace next page object at the bottom of the page
        soup.find_all("table",
                      attrs={"class": "uZgmoc"})[0].replaceWith(next_pages)

        return soup
