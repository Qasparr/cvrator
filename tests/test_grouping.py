# 93
# CVRATOR · tests — the grouping law, proven on fixtures (no network).
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cvrator.model import FileRecord, build_groups, human


def rec(id, name, size, h, created, alg="md5", provider="gdrive"):
    return FileRecord(provider=provider, id=id, name=name, size=size,
                      hash=h, hash_alg=alg if h else "", created=created)


class GroupingLaw(unittest.TestCase):
    def test_byte_identical_group_and_keeper_is_earliest(self):
        records = [
            rec("b", "copy.mp4", 100, "abc", "2024-06-20T00:00:00Z"),
            rec("a", "orig.mp4", 100, "abc", "2022-09-15T00:00:00Z"),
            rec("c", "other.mp4", 100, "xyz", "2023-01-01T00:00:00Z"),
        ]
        groups, reclaimable, stats = build_groups(records)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["keeper"]["id"], "a")
        self.assertEqual([d["id"] for d in groups[0]["duplicates"]], ["b"])
        self.assertEqual(reclaimable, 100)
        self.assertEqual(stats["seen"], 3)

    def test_same_name_different_bytes_is_not_a_duplicate(self):
        records = [
            rec("a", "same.pdf", 50, "h1", "2024-01-01T00:00:00Z"),
            rec("b", "same.pdf", 50, "h2", "2024-01-02T00:00:00Z"),
        ]
        groups, reclaimable, _ = build_groups(records)
        self.assertEqual(groups, [])
        self.assertEqual(reclaimable, 0)

    def test_no_hash_records_are_counted_and_skipped(self):
        records = [
            rec("a", "Doc", 10, "", "2024-01-01T00:00:00Z"),
            rec("b", "Doc copy", 10, "", "2024-01-02T00:00:00Z"),
        ]
        groups, _, stats = build_groups(records)
        self.assertEqual(groups, [])
        self.assertEqual(stats["no_hash"], 2)

    def test_hashes_never_compared_across_algorithms(self):
        records = [
            rec("a", "f.bin", 10, "deadbeef", "2024-01-01T00:00:00Z",
                alg="md5", provider="gdrive"),
            rec("b", "f.bin", 10, "deadbeef", "2024-01-02T00:00:00Z",
                alg="sha1", provider="onedrive"),
        ]
        groups, _, _ = build_groups(records)
        self.assertEqual(groups, [])

    def test_human_sizes(self):
        self.assertEqual(human(512), "512 B")
        self.assertTrue(human(380 * 1024 * 1024).startswith("380"))


if __name__ == "__main__":
    unittest.main()
