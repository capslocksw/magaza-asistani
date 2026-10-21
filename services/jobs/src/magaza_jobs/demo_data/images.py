"""Consistent SVG placeholder product images with a category icon (no real product photos)."""

from __future__ import annotations

import hashlib
from html import escape

# Stroke-only line icons drawn around (0, 0) within roughly +-110 units.
ICONS: dict[str, str] = {
    "paint": '<path d="M-80 -40 H80 L66 95 H-66 Z"/><path d="M-80 -40 Q0 -110 80 -40"/><path d="M-40 -40 V10 Q-40 30 -25 30 Q-10 30 -10 10 V-40"/>',
    "primer": '<path d="M-80 -40 H80 L66 95 H-66 Z"/><path d="M-80 -40 Q0 -110 80 -40"/><path d="M-60 20 H60 M-62 50 H62"/>',
    "roller": '<rect x="-90" y="-90" width="150" height="55" rx="14"/><path d="M60 -62 H90 V0 H0 V40"/><rect x="-12" y="40" width="24" height="70" rx="8"/>',
    "brush": '<rect x="-45" y="-100" width="90" height="70" rx="8"/><path d="M-45 -30 H45 V0 H-45 Z"/><path d="M-12 0 V100 M12 0 V100"/>',
    "tape": '<circle r="80"/><circle r="38"/><path d="M80 0 V95 H20"/>',
    "tray": '<path d="M-100 -30 H100 L70 70 H-70 Z"/><path d="M-20 -30 L-5 70 M20 -30 L35 70 M60 -30 L70 30"/>',
    "film": '<rect x="-95" y="-55" width="150" height="110" rx="20"/><ellipse cx="55" cy="0" rx="20" ry="55"/><path d="M75 0 H100"/>',
    "sand": '<rect x="-80" y="-80" width="160" height="160" rx="10"/><path d="M-50 -40 h10 M0 -50 h10 M40 -30 h10 M-40 10 h10 M10 0 h10 M-10 45 h10 M45 40 h10"/>',
    "trowel": '<path d="M-90 40 L40 -90 L90 -40 L-40 90 Z"/><path d="M40 -90 L70 -110"/>',
    "tube": '<path d="M-30 -95 H30 L40 -70 V90 H-40 V-70 Z"/><path d="M-12 -95 V-115 H12 V-95"/><path d="M-40 -10 H40 M-40 30 H40"/>',
    "foam": '<rect x="-45" y="-70" width="90" height="170" rx="22"/><path d="M-20 -70 V-100 H20 V-70 M20 -90 H70"/>',
    "gun": '<path d="M-100 -40 H60 V10 H-100 Z"/><path d="M60 -15 H100"/><path d="M-20 10 L-40 95 H-5 L10 10"/><path d="M-100 -15 H-115"/>',
    "screw": '<path d="M-50 -95 H50 L35 -60 H-35 Z"/><path d="M-20 -60 V80 L0 105 L20 80 V-60"/><path d="M-20 -30 L20 -20 M-20 0 L20 10 M-20 30 L20 40 M-20 60 L20 70"/>',
    "hook": '<path d="M0 -100 V20 Q0 70 -45 70 Q-85 70 -85 30"/><rect x="-30" y="-110" width="60" height="40" rx="10"/>',
    "bracket": '<path d="M-70 -90 V90 H90"/><path d="M-70 40 L40 90"/><circle cx="-50" cy="-50" r="8"/><circle cx="50" cy="70" r="8"/>',
    "hinge": '<rect x="-80" y="-80" width="70" height="160" rx="8"/><rect x="10" y="-80" width="70" height="160" rx="8"/><path d="M-10 -90 V90 M10 -90 V90"/>',
    "clamp": '<circle r="70"/><path d="M50 -50 L95 -95 M60 -80 L80 -60"/>',
    "lock": '<rect x="-70" y="-10" width="140" height="110" rx="14"/><path d="M-45 -10 V-55 Q-45 -100 0 -100 Q45 -100 45 -55 V-10"/><circle cy="40" r="12"/>',
    "hammer": '<path d="M-90 -80 H40 V-30 H-90 Z"/><path d="M40 -70 L90 -95 M40 -40 L90 -20"/><rect x="-35" y="-30" width="30" height="135" rx="10"/>',
    "screwdriver": '<rect x="-25" y="-105" width="50" height="95" rx="18"/><path d="M0 -10 V90 M-12 90 H12"/>',
    "pliers": '<path d="M-15 -100 L-5 -10 L-60 100 M15 -100 L5 -10 L60 100"/><circle cy="-10" r="12"/>',
    "cutter": '<path d="M-100 40 L60 -40 L90 -10 L-70 70 Z"/><path d="M60 -40 L100 -80 L95 -20"/>',
    "tape-measure": '<rect x="-90" y="-80" width="150" height="150" rx="40"/><circle cx="-15" cy="-5" r="30"/><path d="M60 50 H105 V70"/>',
    "level": '<rect x="-105" y="-30" width="210" height="60" rx="10"/><rect x="-25" y="-15" width="50" height="30" rx="15"/><path d="M-75 -30 V30 M75 -30 V30"/>',
    "wrench": '<path d="M-90 90 L30 -30"/><path d="M30 -30 Q20 -80 60 -100 L70 -70 L95 -75 Q100 -35 55 -25 Z"/>',
    "saw": '<path d="M-100 -20 H70 L100 40 H-100 Z"/><path d="M-100 40 L-90 55 L-80 40 L-70 55 L-60 40 L-50 55 L-40 40 L-30 55 L-20 40 L-10 55 L0 40"/><rect x="60" y="-70" width="40" height="50" rx="10"/>',
    "stapler": '<path d="M-100 20 H90 V50 H-100 Z"/><path d="M-90 20 V-40 H60 L90 20"/>',
    "toolbox": '<rect x="-100" y="-30" width="200" height="120" rx="12"/><path d="M-40 -30 V-70 H40 V-30 M-100 20 H100"/>',
    "ladder": '<path d="M-60 100 L-30 -100 M60 100 L30 -100 M-52 50 H52 M-44 0 H44 M-36 -50 H36"/>',
    "drill": '<path d="M-90 -60 H50 V-10 H-90 Z"/><path d="M50 -45 H80 M80 -50 V-20 H50 M80 -35 H110"/><path d="M-60 -10 L-80 90 H-30 L-10 -10"/>',
    "grinder": '<circle cx="40" cy="0" r="60"/><rect x="-110" y="-25" width="110" height="50" rx="20"/>',
    "sander": '<rect x="-90" y="20" width="180" height="50" rx="10"/><path d="M-50 20 V-40 Q-50 -80 0 -80 H50 V20"/>',
    "bit": '<path d="M-15 -100 H15 V20 L0 105 L-15 20 Z"/><path d="M-15 -40 L15 -20 M-15 -10 L15 10 M-15 20 L10 40"/>',
    "plug": '<rect x="-60" y="-40" width="120" height="90" rx="16"/><path d="M-25 -40 V-90 M25 -40 V-90 M0 50 V105"/>',
    "faucet": '<path d="M-90 -60 H30 Q70 -60 70 -20 V10"/><rect x="-40" y="-100" width="40" height="40" rx="8"/><path d="M70 40 Q60 60 70 75 Q80 60 70 40 Z M70 90 Q62 105 70 115"/>',
    "shower": '<path d="M-90 100 V-60 Q-90 -100 -40 -100 H20"/><path d="M0 -100 H80 L60 -60 H20 Z"/><path d="M30 -40 V-20 M50 -40 V-15 M70 -40 V-20"/>',
    "pen": '<path d="M-80 80 L50 -50 L80 -20 L-50 110 Z"/><path d="M50 -50 L75 -75 L105 -45 L80 -20"/>',
    "spray": '<rect x="-50" y="-30" width="100" height="130" rx="14"/><path d="M-25 -30 V-70 H40 V-55 H70"/><path d="M85 -75 L100 -85 M85 -55 L105 -55 M85 -35 L100 -25"/>',
    "glove": '<path d="M-60 100 V-10 L-80 -50 M-60 -10 V-90 M-25 -10 V-105 M10 -10 V-100 M45 -10 V-80 M-60 100 H50 V-10 H-60"/>',
    "box": '<path d="M0 -95 L95 -45 V55 L0 105 L-95 55 V-45 Z"/><path d="M-95 -45 L0 5 L95 -45 M0 5 V105"/><path d="M-48 -70 L48 -20"/>',
    "bubble": '<circle cx="-55" cy="-55" r="28"/><circle cx="10" cy="-55" r="28"/><circle cx="75" cy="-55" r="28"/><circle cx="-55" cy="10" r="28"/><circle cx="10" cy="10" r="28"/><circle cx="75" cy="10" r="28"/><circle cx="-55" cy="75" r="28"/><circle cx="10" cy="75" r="28"/>',
    "fill": '<path d="M-90 -40 q20 -30 40 0 t40 0 t40 0 t40 0 M-90 20 q20 -30 40 0 t40 0 t40 0 t40 0 M-90 80 q20 -30 40 0 t40 0 t40 0 t40 0"/>',
    "label": '<path d="M-100 -60 H50 L100 0 L50 60 H-100 Z"/><circle cx="45" cy="0" r="12"/><path d="M-70 -20 H10 M-70 20 H-10"/>',
    "envelope": '<rect x="-100" y="-65" width="200" height="130" rx="10"/><path d="M-100 -60 L0 15 L100 -60"/>',
}

_YM_PALETTE = [
    ("#FFF4E6", "#E8590C"),
    ("#F1F3F5", "#1F2937"),
    ("#FFF9DB", "#B45309"),
    ("#E7F5FF", "#1864AB"),
    ("#EBFBEE", "#2B8A3E"),
]
_KC_PALETTE = [("#F8F1E7", "#8B5A2B"), ("#E6FCF5", "#0F766E"), ("#FFF4E6", "#B45309"), ("#F1F3F5", "#374151")]


def _palette(tenant_prefix: str, key: str) -> tuple[str, str]:
    palette = _YM_PALETTE if tenant_prefix == "YM" else _KC_PALETTE
    digest = int(hashlib.sha1(key.encode()).hexdigest(), 16)
    return palette[digest % len(palette)]


def _wrap(text: str, width: int = 26, max_lines: int = 2) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > width and current:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: width - 1] + "…"
    return lines


def product_svg(*, sku: str, title: str, brand: str, icon: str, badge: str, category: str) -> str:
    bg, fg = _palette(sku[:2], category)
    short = title.removeprefix(brand).strip()
    lines = _wrap(short)
    text = "".join(
        f'<text x="300" y="{500 + i * 34}" text-anchor="middle" font-size="25" fill="#374151">{escape(line)}</text>'
        for i, line in enumerate(lines)
    )
    badge_w = 26 + 15 * len(badge)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" role="img" aria-label="{escape(title)}">'
        f'<rect width="600" height="600" fill="{bg}"/>'
        f'<circle cx="300" cy="245" r="165" fill="#FFFFFF" opacity="0.75"/>'
        f'<g transform="translate(300 245)" fill="none" stroke="{fg}" stroke-width="12" stroke-linecap="round" '
        f'stroke-linejoin="round">{ICONS.get(icon, ICONS["box"])}</g>'
        f'<g font-family="Segoe UI, Helvetica, Arial, sans-serif">'
        f'<rect x="28" y="28" rx="20" width="{badge_w}" height="44" fill="{fg}"/>'
        f'<text x="{28 + badge_w / 2}" y="58" text-anchor="middle" font-size="22" font-weight="700" fill="#FFFFFF">{escape(badge)}</text>'
        f'<text x="300" y="458" text-anchor="middle" font-size="30" font-weight="800" fill="{fg}">{escape(brand.upper())}</text>'
        f"{text}</g></svg>"
    )


def category_svg(*, tenant_prefix: str, slug: str, icon: str) -> str:
    bg, fg = _palette(tenant_prefix, slug)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" role="img" aria-hidden="true">'
        f'<rect width="240" height="240" rx="36" fill="{bg}"/>'
        f'<g transform="translate(120 120) scale(0.72)" fill="none" stroke="{fg}" stroke-width="13" stroke-linecap="round" '
        f'stroke-linejoin="round">{ICONS.get(icon, ICONS["box"])}</g></svg>'
    )


def logo_svg(*, name: str, primary: str, accent: str, icon: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="{escape(name)}">'
        f'<rect width="64" height="64" rx="14" fill="{primary}"/>'
        f'<g transform="translate(32 32) scale(0.2)" fill="none" stroke="#FFFFFF" stroke-width="16" stroke-linecap="round" '
        f'stroke-linejoin="round">{ICONS[icon]}</g><circle cx="52" cy="12" r="5" fill="{accent}"/></svg>'
    )
