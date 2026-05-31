"""Overlay theme colour palettes for BO3 Tracker."""

OVERLAY_BASE_WIDTH = 280
OVERLAY_BASE_HEIGHT = 340
OVERLAY_SIZE_MIN = 70
OVERLAY_SIZE_MAX = 150
OVERLAY_SIZE_DEFAULT = 100

OVERLAY_THEMES = {
    "default": {
        "bg": "#0b0c10", "panel": "#0b0c10", "border": "#66fcf1",
        "title": "#66fcf1", "text": "#ffffff", "muted": "#777777",
        "damage": "#ff9d00", "divider": "#333333", "fallback": "#333333",
        "shadow": "0 0 10px rgba(102, 252, 241, 0.25)"
    },
    "void": {
        "bg": "#050510", "panel": "#100b22", "border": "#7b4397",
        "title": "#e0b0ff", "text": "#f3eaff", "muted": "#9b86c7",
        "damage": "#b19cd9", "divider": "#352253", "fallback": "#231437",
        "shadow": "0 0 16px rgba(148, 0, 211, 0.35)"
    },
    "115_Origins": {
        "bg": "#071018", "panel": "#0b1824", "border": "#00a8ff",
        "title": "#58a6ff", "text": "#d7f3ff", "muted": "#7e9db5",
        "damage": "#ffb347", "divider": "#19384c", "fallback": "#13293a",
        "shadow": "0 0 14px rgba(0, 168, 255, 0.28)"
    },
    "RedHex": {
        "bg": "#120606", "panel": "#1a0808", "border": "#ff3333",
        "title": "#ff7777", "text": "#fff0f0", "muted": "#aa7777",
        "damage": "#ffcc00", "divider": "#4a1515", "fallback": "#2a1010",
        "shadow": "0 0 14px rgba(255, 0, 0, 0.3)"
    },
    "Golden Divinium": {
        "bg": "#151004", "panel": "#201806", "border": "#ffd700",
        "title": "#fff3a6", "text": "#fff8d8", "muted": "#b8a45d",
        "damage": "#ffd700", "divider": "#5a4610", "fallback": "#382a08",
        "shadow": "0 0 14px rgba(255, 215, 0, 0.28)"
    },
    "retro": {
        "bg": "#080416", "panel": "#100725", "border": "#00f2ff",
        "title": "#ff00ff", "text": "#f3f3ff", "muted": "#9d8dcc",
        "damage": "#00ffff", "divider": "#262626", "fallback": "#1a1a1a",
        "shadow": "0 0 14px rgba(0, 242, 255, 0.28)"
    },
    "matrix": {
        "bg": "#000000", "panel": "#000000", "border": "#00ff00",
        "title": "#00ff00", "text": "#00ff00", "muted": "#00ff00",
        "damage": "#ff9d00", "divider": "#333333", "fallback": "#333333",
        "shadow": "0 0 14px rgba(0, 255, 0, 0.3)"
    },
    "trench": {
        "bg": "#2f2f2f", "panel": "#3a3a3a", "border": "#c9bca7",
        "title": "#d4b56a", "text": "#e0e0e0", "muted": "#8f8f8f",
        "damage": "#b19cd9", "divider": "#4a3f35", "fallback": "#2c2825",
        "shadow": "0 0 14px rgba(201, 188, 167, 0.28)"
    },
    "neon_pulse": {
        "bg": "#0a0a0a", "panel": "#121212", "border": "#00f5ff",
        "title": "#00f5ff", "text": "#e0e0e0", "muted": "#666666",
        "damage": "#ff00ff", "divider": "#333333", "fallback": "#222222",
        "shadow": "0 0 14px rgba(0, 245, 255, 0.3)"
    },
    "Darkwood": {
        "bg": "#1a1a1a", "panel": "#252525", "border": "#e2c13d",
        "title": "#f3d446", "text": "#e0e0e0", "muted": "#aaaaaa",
        "damage": "#f3d446", "divider": "#4a3f35", "fallback": "#2c2825",
        "shadow": "0 0 14px rgba(226, 193, 61, 0.28)"
    },
    "Cherry Blossom": {
        "bg": "#1a1a1a", "panel": "#252525", "border": "#e91e63",
        "title": "#fff8fa", "text": "#e0e0e0", "muted": "#aaaaaa",
        "damage": "#ff6b9a", "divider": "#4a3f35", "fallback": "#2c2825",
        "shadow": "0 0 14px rgba(233, 30, 99, 0.28)"
    },
    "Clouds": {
        "bg": "#061a30", "panel": "#0d3858", "border": "#b8e8ff",
        "title": "#ffffff", "text": "#f8fdff", "muted": "#b8d8ea",
        "damage": "#ffe08a", "divider": "#2d6688", "fallback": "#244b64",
        "shadow": "0 0 14px rgba(116, 217, 255, 0.30)"
    },
    "Dog Pack": {
        "bg": "#120e0d", "panel": "#2a1f1a", "border": "#f2c16b",
        "title": "#fff8e8", "text": "#f6ead6", "muted": "#c9b292",
        "damage": "#f2c16b", "divider": "#5a3d2c", "fallback": "#3d2b22",
        "shadow": "0 0 14px rgba(242, 193, 107, 0.28)"
    },
    "Shi No Numa": {
        "bg": "#071111", "panel": "#0d1814", "border": "#b7d97b",
        "title": "#d8c889", "text": "#e5eadc", "muted": "#9aa88c",
        "damage": "#f0d66a", "divider": "#3f4e2d", "fallback": "#1b2a20",
        "shadow": "0 0 14px rgba(183, 217, 123, 0.24)"
    },
    "DeadOps Arcade": {
        "bg": "#0b0c10", "panel": "#0b0c10", "border": "#00f5ff",
        "title": "#ffd340", "text": "#f8f6d8", "muted": "#bbbbbb",
        "damage": "#ff304f", "divider": "#333333", "fallback": "#222222",
        "shadow": "0 0 14px rgba(0, 245, 255, 0.28)"
    },
    "Pacific Paradise": {
        "bg": "#f8f9fa", "panel": "#ffffff", "border": "#2e8b57",
        "title": "#2e8b57", "text": "#2f4f4f", "muted": "#6c757d",
        "damage": "#ff69b4", "divider": "#dee2e6", "fallback": "#adb5bd",
        "shadow": "0 0 12px rgba(46, 139, 87, 0.2)"
    },
    "diamond": {
        "bg": "#080c24", "panel": "#111638", "border": "#00e5ff",
        "title": "#00e5ff", "text": "#e0f7fa", "muted": "#7c8ab5",
        "damage": "#b388ff", "divider": "#1a237e", "fallback": "#0a0e27",
        "shadow": "0 0 14px rgba(0, 229, 255, 0.30)"
    },
    "factory": {
        "bg": "#060807", "panel": "#121714", "border": "#68ff5a",
        "title": "#68ff5a", "text": "#c8d0c2", "muted": "#7e8b80",
        "damage": "#ffb347", "divider": "#1b241f", "fallback": "#0a0f0c",
        "shadow": "0 0 14px rgba(104, 255, 90, 0.30)"
    },
    "Extinction": {
        "bg": "#030607", "panel": "#081012", "border": "#25f4ff",
        "title": "#85fbff", "text": "#d6e6e7", "muted": "#84979b",
        "damage": "#ffb14a", "divider": "#223036", "fallback": "#061012",
        "shadow": "0 0 16px rgba(37, 244, 255, 0.30)"
    },
    "cartoon_graffiti_theme": {
        "bg": "#14071f", "panel": "#1a0826", "border": "#ff3bd4",
        "title": "#ffe94f", "text": "#ffe9ff", "muted": "#c5a9d8",
        "damage": "#23f6ff", "divider": "#2d1040", "fallback": "#1a0826",
        "shadow": "0 0 14px rgba(255, 59, 212, 0.35)"
    }
}
