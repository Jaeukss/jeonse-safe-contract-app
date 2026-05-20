from src.agent.graph import run_agent_workflow
from src.input_layer import snapshot as snapshot_module


def test_agent_workflow_creates_report(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot_module, "SNAPSHOT_DIR", tmp_path)
    records = [
        {
            "input_id": "RAW-1",
            "session_id": "S-TEST",
            "source": "user_input",
            "data": {
                "address": "서울시 관악구 신림동",
                "district": "관악구",
                "dong": "신림동",
                "housing_type": "다가구",
                "deposit": 135_000_000,
                "area_m2": 27.1,
                "floor": 2,
            },
        },
        {
            "input_id": "RAW-2",
            "session_id": "S-TEST",
            "source": "manual_correction",
            "data": {
                "registry_checked": True,
                "building_register_checked": True,
                "broker_explanation_checked": False,
                "mortgage_flag": False,
                "seizure_flag": False,
                "trust_flag": None,
                "senior_deposit_checked": False,
            },
        },
    ]

    result = run_agent_workflow({"session_id": "S-TEST", "records": records})

    assert result["grade"]["grade"] in {"확인 양호", "주의", "위험", "고위험", "검토불가"}
    assert "전세계약 위험진단 리포트" in result["report_markdown"]
