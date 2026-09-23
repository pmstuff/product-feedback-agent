"""
design/tokens.py — Arco Design System tokens for the Product Feedback Agent.

Source: https://arco.design/react/docs/token
Figma:  https://www.figma.com/design/A9S0ExZuQvdET2wnbqRNyq/Arco-Design-System--Community-

Import these constants anywhere you need to reference a color, size, or shadow
programmatically (e.g. in dynamic chart colour palettes).

For CSS injection in Streamlit, use design/arco.css or the GLOBAL_CSS constant
in this module.
"""

# ─── Primary (Blue) ───────────────────────────────────────────────────────────
PRIMARY_1 = "#E8F3FF"   # lightest tint — hover backgrounds, tag fills
PRIMARY_2 = "#BEDAFF"
PRIMARY_3 = "#94BFFF"
PRIMARY_4 = "#6AA1FF"
PRIMARY_5 = "#4080FF"   # hover state on primary button
PRIMARY_6 = "#165DFF"   # ★ brand blue — buttons, links, active states
PRIMARY_7 = "#0E42D2"   # pressed / active
PRIMARY_8 = "#072CA6"
PRIMARY_9 = "#031A79"
PRIMARY_10 = "#000D4D"  # darkest shade

# ─── Neutral (Text & Borders) ─────────────────────────────────────────────────
TEXT_PRIMARY   = "#1D2129"   # headings, labels
TEXT_SECONDARY = "#4E5969"   # body text, descriptions
TEXT_TERTIARY  = "#86909C"   # placeholders, captions
TEXT_DISABLED  = "#C9CDD4"   # disabled state
BORDER         = "#E5E6EB"   # default border
BORDER_STRONG  = "#C9CDD4"   # focused border
FILL_1         = "#F7F8FA"   # subtle background fill
FILL_2         = "#F2F3F5"   # page background
WHITE          = "#FFFFFF"

# ─── Semantic ─────────────────────────────────────────────────────────────────
SUCCESS        = "#00B42A"
SUCCESS_BG     = "#E8FFEA"
WARNING        = "#FF7D00"
WARNING_BG     = "#FFF7E8"
DANGER         = "#F53F3F"
DANGER_BG      = "#FFECE8"
INFO           = "#165DFF"
INFO_BG        = "#E8F3FF"

# ─── Typography ───────────────────────────────────────────────────────────────
FONT_FAMILY = (
    '-apple-system, BlinkMacSystemFont, "PingFang SC", '
    '"Helvetica Neue", Helvetica, Arial, sans-serif'
)
FONT_SIZE_XS   = "12px"
FONT_SIZE_SM   = "13px"
FONT_SIZE_MD   = "14px"   # base body
FONT_SIZE_LG   = "16px"
FONT_SIZE_XL   = "20px"
FONT_SIZE_2XL  = "24px"

LINE_HEIGHT_BASE = "1.5715"

FONT_WEIGHT_REGULAR = "400"
FONT_WEIGHT_MEDIUM  = "500"
FONT_WEIGHT_BOLD    = "600"

# ─── Spacing ──────────────────────────────────────────────────────────────────
SPACE_1  = "4px"
SPACE_2  = "8px"
SPACE_3  = "12px"
SPACE_4  = "16px"
SPACE_5  = "20px"
SPACE_6  = "24px"
SPACE_8  = "32px"

# ─── Border radius ────────────────────────────────────────────────────────────
RADIUS_SM   = "2px"    # tags, badges
RADIUS_MD   = "4px"    # inputs, buttons (default)
RADIUS_LG   = "8px"    # cards, modals
RADIUS_XL   = "16px"   # large cards
RADIUS_FULL = "9999px" # pills, avatars

# ─── Shadows ──────────────────────────────────────────────────────────────────
SHADOW_1 = "0 1px 2px rgba(0,0,0,0.05)"
SHADOW_2 = "0 2px 5px rgba(0,0,0,0.08), 0 0 2px rgba(0,0,0,0.05)"   # cards
SHADOW_3 = "0 4px 10px rgba(0,0,0,0.10), 0 0 2px rgba(0,0,0,0.05)"  # modals

# ─── Transition ───────────────────────────────────────────────────────────────
TRANSITION_BASE = "all 0.1s cubic-bezier(0, 0, 1, 1)"
