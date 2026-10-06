"""Sáu bước tiến độ — ``src/ai/rag/ingest/tien_do.py``."""

from src.ai.rag.ingest.tien_do import CAC_BUOC, buoc_hien_tai, dung_cac_buoc


def test_sau_buoc_dung_ten_enum_scr033():
    assert CAC_BUOC == ("QUEUED", "EXTRACTING", "CHUNKING", "EMBEDDING", "INDEXING", "DONE")


def test_pending_la_queued():
    assert buoc_hien_tai("PENDING", None) == "QUEUED"
    assert dung_cac_buoc("PENDING", None)[0] == ("QUEUED", "RUNNING")
    assert {t for _, t in dung_cac_buoc("PENDING", None)[1:]} == {"PENDING"}


def test_dang_nhung_thi_ba_buoc_dau_xong():
    assert buoc_hien_tai("PROCESSING", "EMBEDDING") == "EMBEDDING"
    assert [t for _, t in dung_cac_buoc("PROCESSING", "EMBEDDING")] == [
        "DONE", "DONE", "DONE", "RUNNING", "PENDING", "PENDING",
    ]


def test_ready_thi_ca_sau_buoc_xong():
    assert buoc_hien_tai("READY", None) == "DONE"
    assert {t for _, t in dung_cac_buoc("READY", None)} == {"DONE"}


def test_failed_to_do_dung_buoc_hong():
    assert buoc_hien_tai("FAILED", "EXTRACTING") == "FAILED"
    assert [t for _, t in dung_cac_buoc("FAILED", "EXTRACTING")] == [
        "DONE", "FAILED", "SKIPPED", "SKIPPED", "SKIPPED", "SKIPPED",
    ]


def test_failed_truoc_v211_khong_doan_buoc_hong():
    assert "FAILED" not in {t for _, t in dung_cac_buoc("FAILED", None)}
