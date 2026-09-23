# Design System — Arco Design (ByteDance)

This folder contains the Arco Design System tokens and styles adapted for the
Product Feedback Agent.

**Figma source:** https://www.figma.com/design/A9S0ExZuQvdET2wnbqRNyq/Arco-Design-System--Community-  
**Official docs:** https://arco.design  
**GitHub:** https://github.com/arco-design/arco-design

---

## Files

| File | Purpose |
|---|---|
| `tokens.py` | All design tokens as Python constants — colors, typography, spacing, shadows |
| `arco.css` | Canonical CSS reference using `--arco-*` custom properties |
| `streamlit_css.py` | CSS adapted for Streamlit's selector structure, injected at app startup |

---

## How it's applied

`app.py` imports `ARCO_CSS` from `streamlit_css.py` and injects it immediately
after `st.set_page_config()`:

```python
from design.streamlit_css import ARCO_CSS
st.markdown(ARCO_CSS, unsafe_allow_html=True)
```

`.streamlit/config.toml` sets the native Streamlit theme so the color picker,
progress bars, and other non-overridable components also use Arco's primary blue.

---

## Key tokens

| Token | Value | Use |
|---|---|---|
| Primary | `#165DFF` | Buttons, links, active states |
| Text primary | `#1D2129` | Headings, labels |
| Text secondary | `#4E5969` | Body text |
| Text tertiary | `#86909C` | Placeholders, captions |
| Border | `#E5E6EB` | Input borders, dividers |
| Page background | `#F2F3F5` | App background |
| Card background | `#FFFFFF` | Panels, cards |
| Success | `#00B42A` | Positive states |
| Warning | `#FF7D00` | Caution states |
| Danger | `#F53F3F` | Error states |

---

## Updating styles

1. Edit the token in `tokens.py`.
2. Update the corresponding `--arco-*` variable in `arco.css`.
3. Update the Streamlit selector in `streamlit_css.py`.
4. Restart Streamlit (`Ctrl+C` → `streamlit run app.py`).
