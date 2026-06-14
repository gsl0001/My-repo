from lowcap_short_system.observability.audit import AuditLog


def test_record_appends_and_reads_back(tmp_path):
    log = AuditLog(str(tmp_path / "audit.jsonl"), config_version="v1", clock=lambda: 1000.0)
    log.record("SIGNAL", symbol="TICK", kind_detail="enter")
    log.record("ORDER", symbol="TICK", qty=1000)
    rows = log.read()
    assert len(rows) == 2
    assert rows[0]["kind"] == "SIGNAL" and rows[0]["config_version"] == "v1" and rows[0]["ts"] == 1000.0
    assert rows[1]["qty"] == 1000


def test_is_append_only(tmp_path):
    p = tmp_path / "audit.jsonl"
    AuditLog(str(p)).record("A")
    AuditLog(str(p)).record("B")  # a second logger appends, does not truncate
    assert [r["kind"] for r in AuditLog(str(p)).read()] == ["A", "B"]


def test_read_missing_file_is_empty(tmp_path):
    assert AuditLog(str(tmp_path / "none.jsonl")).read() == []
