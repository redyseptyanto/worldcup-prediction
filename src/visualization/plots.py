"""Optional plotting wrappers."""

from __future__ import annotations


def package_status() -> dict[str, bool]:
    """Report whether optional visualization dependencies are installed."""

    try:
        import plotly  # noqa: F401

        plotly_installed = True
    except ImportError:
        plotly_installed = False
    try:
        import streamlit  # noqa: F401

        streamlit_installed = True
    except ImportError:
        streamlit_installed = False
    return {"plotly": plotly_installed, "streamlit": streamlit_installed}
