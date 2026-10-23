"""Design tokens shared by the chart, the HTML components and the theme.

Colour carries meaning in this interface, so each token has one job:

* GREEN  - the route that was found, and anything "open"
* CLARET - anything closed or failing
* GILT   - frames and ornaments only; it never carries meaning on its own
* SEPIA  - everything inactive (unused links, secondary text)

The same hex values are repeated in ``.streamlit/config.toml`` and
``ui/theme.css``; change all three together.
"""

from __future__ import annotations

INK = "#2B2118"         # iron-gall ink: body text
SEPIA = "#6E5B45"       # secondary text (4.9:1 on parchment)
LINE = "#8C7A62"        # unused links on the chart
PARCHMENT = "#ECE0C1"   # page background
VELLUM = "#F6EEDA"      # panels and markers
GREEN = "#1F4436"       # bottle green: selected route, primary actions
CLARET = "#7B2230"      # closures and errors
GILT = "#A9853A"        # frames and ornaments
GILT_PALE = "#D4B26A"   # gilt text on the green sidebar (5.3:1)

FONT = "'Libre Caslon Text', Georgia, 'Times New Roman', serif"
DISPLAY_FONT = "'Abril Fatface', 'Libre Caslon Text', Georgia, serif"

# Engraved maps told transport modes apart by line pattern rather than colour,
# which also keeps the chart readable for colour-blind viewers.
MODE_DASH = {
    "air": "dot",
    "sea": "dash",
    "road": "solid",
    "land convoy": "dashdot",
    "sea + road": "longdashdot",
    "multimodal": "longdashdot",
}

# CSS classes in ui/theme.css that redraw the same dash patterns (in px) for
# the journey strip and the key, so they match the chart exactly.
MODE_CSS = {
    "air": "m-air",
    "sea": "m-sea",
    "road": "m-road",
    "land convoy": "m-convoy",
    "sea + road": "m-searoad",
    "multimodal": "m-searoad",
}

MODE_NAMES = {
    "air": "Air",
    "sea": "Sea",
    "road": "Road",
    "land convoy": "Land convoy",
    "sea + road": "Sea + road",
    "multimodal": "Multimodal",
}

NODE_TYPE_NAMES = {
    "origin": "Origin hub",
    "destination": "Destination",
    "airport": "Airport",
    "port": "Sea port",
    "hub": "Logistics hub",
    "staging": "Staging area",
}


def mode_key(mode: str) -> str:
    """Normalise a mode string from the data file, e.g. 'Sea + Road' -> 'sea + road'."""
    return mode.strip().lower()


def mode_css(mode: str) -> str:
    return MODE_CSS.get(mode_key(mode), "m-road")


def mode_name(mode: str) -> str:
    return MODE_NAMES.get(mode_key(mode), mode.strip().title())


def node_type_name(node_type: str) -> str:
    return NODE_TYPE_NAMES.get(node_type.strip().lower(), node_type.strip().title())
