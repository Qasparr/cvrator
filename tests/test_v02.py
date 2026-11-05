# 93
# CVRATOR · tests/test_v02.py — registry, catalog and planner law.
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cvrator.model import FileRecord
from cvrator.registry import REGISTRY, recommend_target
from cvrator.catalog import build_catalog, catalog_stats, search_catalog
from cvrator.archive import select_candidates, make_plan

GB = 1024 ** 3
MB = 1024 ** 2
NOW = datetime(2026, 11, 5, tzinfo=timezone.utc)


def rec(provider, id, name, size, created):
    return FileRecord(provider=provider, id=id, name=name, size=size,
                      hash="h" + id, hash_alg="md5", created=created)


class RegistryLaw(unittest.TestCase):
    def test_degoo_is_manual_only_and_flagged(self):
        d = REGISTRY["degoo"]
        self.assertEqual(d.automation, "manual_only")
        self.assertEqual(d.inactivity_days, 90)
        self.assertEqual(d.max_file_bytes, 256 * MB)

    def test_filen_is_an_automated_vault(self):
        self.assertNotEqual(REGISTRY["filen"].automation, "manual_only")
        self.assertTrue(REGISTRY["filen"].zero_knowledge)

    def test_small_set_goes_to_filen(self):
        t = recommend_target(1 * GB, 100 * MB, source_key="gdrive")
        self.assertEqual(t["key"], "filen")

    def test_oversized_set_falls_to_local(self):
        t = recommend_target(50 * GB, 100 * MB, source_key="gdrive")
        self.assertEqual(t["key"], "local")
        self.assertIn("filen", t["rejected_before_it"])

    def test_source_is_never_its_own_target(self):
        t = recommend_target(1 * GB, 1 * MB, source_key="filen")
        self.assertNotEqual(t["key"], "filen")


class CatalogLaw(unittest.TestCase):
    def setUp(self):
        self.db = os.path.join(tempfile.mkdtemp(), "catalog.db")
        build_catalog(self.db, {
            "gdrive": [rec("gdrive", "1", "alpha.txt", 10,
                           "2020-01-01T00:00:00Z"),
                       rec("gdrive", "2", "beta.mp4", 20,
                           "2021-01-01T00:00:00Z")],
            "onedrive": [rec("onedrive", "3", "alpha-copy.txt", 10,
                             "2022-01-01T00:00:00Z")]})

    def test_stats_unify_the_houses(self):
        st = catalog_stats(self.db)
        self.assertEqual(st["providers"]["total"]["files"], 3)
        self.assertEqual(st["providers"]["total"]["bytes"], 40)

    def test_search_crosses_providers(self):
        hits = search_catalog(self.db, "alpha")
        self.assertEqual({h["provider"] for h in hits},
                         {"gdrive", "onedrive"})


class ArchiveLaw(unittest.TestCase):
    def setUp(self):
        self.records = [
            rec("gdrive", "old", "ancient.txt", 5, "2010-06-01T00:00:00Z"),
            rec("gdrive", "new", "fresh.txt", 7, "2025-06-01T00:00:00Z"),
            rec("gdrive", "nodate", "mystery.txt", 9, "")]

    def test_ten_year_rule_selects_only_the_ancient(self):
        sel = select_candidates(self.records, years=10, now=NOW)
        self.assertEqual([r.id for r in sel["records"]], ["old"])
        self.assertEqual(sel["total_bytes"], 5)
        self.assertEqual(sel["skipped_no_date"], 1)

    def test_plan_carries_the_law_and_a_vault(self):
        plan = make_plan(self.records, "gdrive", years=10, now=NOW)
        self.assertIn("PLAN ONLY", plan["law"])
        self.assertEqual(plan["target"]["key"], "filen")


if __name__ == "__main__":
    unittest.main()

# 93 — Live, Love, and let Love, Live.
