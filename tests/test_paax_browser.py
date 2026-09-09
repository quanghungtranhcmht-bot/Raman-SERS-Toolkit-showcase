from __future__ import annotations

from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.io.vendor_importers import load_paax_traces

PAAX = PROJECT_ROOT / "examples" / "electrochemistry" / "Session Data [2026-JUN-01 1216 #1].paax"


def get_meta(trace, key, default=""):
    md = getattr(trace, "metadata", {}) or {}
    return md.get(key, getattr(trace, key, default))


class PaaxBrowserDataTests(unittest.TestCase):

    @unittest.skipUnless(PAAX.exists(), "Optional local PAAX example not available")
    def test_paax_browser_source_has_displayable_traces(self):
        traces = load_paax_traces(PAAX)

        self.assertGreater(len(traces), 0)

        first = traces[0]
        self.assertTrue(get_meta(first, "name", ""))
        self.assertTrue(get_meta(first, "xlabel", ""))
        self.assertTrue(get_meta(first, "ylabel", ""))
        self.assertGreater(len(first.x), 0)


if __name__ == "__main__":
    unittest.main()
