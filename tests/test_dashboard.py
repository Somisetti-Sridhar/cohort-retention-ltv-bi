"""Exercise every BI page against the real local gold marts when available."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not Path("data/build.json").exists(), reason="Real BI marts not present"
)


def test_all_report_pages():
    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(
        str(Path("app/observatory.py").resolve()), default_timeout=30
    ).run()
    assert not app.exception
    pages = [
        "Executive overview",
        "Retention & observed value",
        "Customer segments",
        "Campaigns & promotions",
        "Product portfolio",
        "Quality & provenance",
    ]
    for source in ["retail", "journey"]:
        app.sidebar.selectbox[0].set_value(source).run()
        for page in pages:
            app.sidebar.radio[0].set_value(page).run()
            assert not app.exception, f"{source}: {page}: {app.exception}"
