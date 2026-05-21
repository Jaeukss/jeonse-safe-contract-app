from pathlib import Path

from streamlit.testing.v1 import AppTest


SAMPLE_CONTRACT_TEXT = (
    "주소: 서울 강서구 화곡동 1027-8 해든빌라 402호\n"
    "주택유형: 연립다세대\n"
    "전세보증금: 2억 7천만원\n"
    "전용면적: 42.10㎡\n"
    "층: 4층\n"
    "사용승인일: 2016\n"
    "계약 전 확인\n"
    "근저당권 설정, 채권최고액 9천만원"
)


def test_pasted_document_prefills_basic_inputs():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)

    app.text_area[0].set_value(SAMPLE_CONTRACT_TEXT)
    app.run(timeout=20)
    app.button[0].click()
    app.run(timeout=20)

    assert app.session_state["basic_deposit"] == 270_000_000
    assert app.session_state["basic_area_m2"] == 42.1
    assert app.session_state["basic_floor"] == 4
    assert app.session_state["basic_built_year"] == 2016
    assert app.session_state["basic_contract_stage"] == "계약 전 확인"
    assert app.session_state["basic_address"].startswith("서울 강서구")


def test_uploaded_pdf_is_cached_and_parsed():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)

    sample = Path("samples/01_registry_mortgage.pdf")
    app.file_uploader[0].upload(sample.name, sample.read_bytes(), "application/pdf")
    app.run(timeout=20)

    records = app.session_state["uploaded_document_results"]
    data = next(iter(records.values()))["record"]["data"]
    assert data["mortgage_flag"] is True
    assert data["mortgage_amount"] == 240_000_000


def test_uploaded_file_prefill_overwrites_quick_case_once():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)

    app.selectbox[0].select("신탁 확인이 필요한 다가구")
    app.run(timeout=20)
    assert app.session_state["basic_deposit"] == 650_000_000

    sample = (
        "주소: 서울 강서구 화곡동 999-1 테스트빌라 201호\n"
        "주택유형: 연립다세대\n"
        "전세보증금: 1억 5천만원\n"
        "월차임: 30만원\n"
        "전용면적: 33.50㎡\n"
        "층: 2층\n"
        "사용승인일: 2010\n"
        "계약일: 2026.05.21"
    ).encode("utf-8")
    app.file_uploader[0].upload("sample_contract.txt", sample, "text/plain")
    app.run(timeout=20)

    assert app.session_state["basic_address"] == "서울 강서구 화곡동 999-1 테스트빌라 201호"
    assert app.session_state["basic_housing_type"] == "연립다세대"
    assert app.session_state["basic_deposit"] == 150_000_000
    assert app.session_state["basic_monthly_rent"] == 300_000
    assert app.session_state["basic_area_m2"] == 33.5
    assert app.session_state["basic_floor"] == 2
    assert app.session_state["basic_built_year"] == 2010
    assert app.session_state["basic_contract_stage"] == "계약 당일"


def test_pasted_document_runs_diagnosis_without_default_false_conflicts():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)

    app.text_area[0].set_value(SAMPLE_CONTRACT_TEXT)
    app.run(timeout=20)
    app.button[0].click()
    app.run(timeout=20)

    # After prefill there are three buttons:
    # 0 pasted text analysis, 1 overwrite basic input, 2 start diagnosis.
    app.button[2].click()
    app.run(timeout=30)

    result = app.session_state["result"]
    assert result["snapshot"]["deposit"] == 270_000_000
    assert result["snapshot"]["mortgage_flag"] is True
    assert result["snapshot"]["mortgage_amount"] == 90_000_000
    assert result["conflicts"] == []
