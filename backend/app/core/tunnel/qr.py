"""Render a QR-code → base64 PNG suitable for an <img src=...> tag."""

from __future__ import annotations

import base64
import io


def make_qr(data: str, scale: int = 8) -> str:
    """Return a `data:image/png;base64,...` URI."""
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=scale,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#2A2520", back_color="#FBF7EC")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
