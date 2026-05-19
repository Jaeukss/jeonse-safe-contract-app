from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional local fallback
    PdfReader = None

from backend.app.pipeline import diagnose_contract
from backend.app.schemas import ContractInput


ROOT = Path(__file__).resolve().parent


EXAMPLES = {
    "전세가율이 높은 빌라": {
        "address": "서울 강서구 화곡동 1027-8 해든빌라 402호",
        "legal_dong_code": "1150010300",
        "housing_type": "연립다세대",
        "deposit_won": 270_000_000,
        "monthly_rent_won": 0,
        "exclusive_area_m2": 42.1,
        "floor": 4,
        "built_year": 2016,
        "contract_stage": "계약 전 확인",
        "document_text": "등기부등본 을구 근저당권 설정, 채권최고액 9천만원. 최근 소유권 이전 있음.",
        "registry_checked": True,
        "building_checked": True,
        "explanation_checked": False,
        "senior_deposit_unknown": False,
    },
    "신탁/압류가 보이는 집": {
        "address": "인천 미추홀구 주안동 1450-4 새담빌 301호",
        "legal_dong_code": "2817710500",
        "housing_type": "연립다세대",
        "deposit_won": 165_000_000,
        "monthly_rent_won": 0,
        "exclusive_area_m2": 39.2,
        "floor": 3,
        "built_year": 2002,
        "contract_stage": "잔금 전 확인",
        "document_text": "신탁등기, 압류, 채권최고액 7천만원. 위반건축물 표시가 확인됨.",
        "registry_checked": True,
        "building_checked": True,
        "explanation_checked": True,
        "senior_deposit_unknown": False,
    },
    "특이사항이 적은 아파트": {
        "address": "서울 송파구 가락동 479 그린파크 1502호",
        "legal_dong_code": "1171010700",
        "housing_type": "아파트",
        "deposit_won": 620_000_000,
        "monthly_rent_won": 0,
        "exclusive_area_m2": 59.8,
        "floor": 15,
        "built_year": 2018,
        "contract_stage": "계약 전 확인",
        "document_text": "근저당권, 압류, 가압류, 신탁등기, 위반건축물 표시 없음.",
        "registry_checked": True,
        "building_checked": True,
        "explanation_checked": True,
        "senior_deposit_unknown": False,
    },
}


HOUSING_TYPES = ["아파트", "오피스텔", "연립다세대", "다가구", "단독주택"]
CONTRACT_STAGES = ["매물 검토", "계약 전 확인", "계약 당일", "잔금 전 확인", "입주 직전"]


def is_streamlit_runtime() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


def read_json(relative_path: str, fallback: Any = None) -> Any:
    path = ROOT / relative_path
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def tenant_guide() -> dict[str, Any]:
    return read_json("data/tenant_action_guide.json", {"upload_files": [], "risk_actions": {}, "official_links": []})


def read_uploaded_text(file: Any) -> str:
    if file is None:
        return ""
    if isinstance(file, list):
        return "\n".join(read_uploaded_text(item) for item in file if item is not None)

    if hasattr(file, "read") and not isinstance(file, (str, Path)):
        data = file.read()
        if hasattr(file, "seek"):
            file.seek(0)
        name = getattr(file, "name", "")
        if str(name).lower().endswith(".pdf") and PdfReader is not None:
            reader = PdfReader(BytesIO(data))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        for encoding in ("utf-8", "cp949"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="ignore")

    path = Path(file.name if hasattr(file, "name") else file)
    if path.suffix.lower() == ".pdf" and PdfReader is not None:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp949", errors="ignore")


def money(value: int | float) -> str:
    value = int(value or 0)
    eok, rest = divmod(value, 100_000_000)
    man = rest // 10_000
    if eok and man:
        return f"{eok}억 {man:,}만원"
    if eok:
        return f"{eok}억원"
    return f"{man:,}만원"


def level_color(grade: str) -> str:
    if "고위험" in grade or "위험" in grade:
        return "#b42318"
    if "주의" in grade:
        return "#b54708"
    if "검토" in grade:
        return "#344054"
    return "#027a48"


def run_diagnosis(
    uploaded_file: Any,
    address: str,
    legal_dong_code: str,
    housing_type: str,
    deposit_won: float,
    monthly_rent_won: float,
    exclusive_area_m2: float,
    floor: float,
    built_year: float,
    contract_stage: str,
    document_text: str,
    registry_checked: bool,
    building_checked: bool,
    explanation_checked: bool,
    senior_deposit_unknown: bool,
) -> tuple[Any, str, str]:
    payload_data = dict(
        address=address,
        legal_dong_code=legal_dong_code,
        housing_type=housing_type,
        deposit_won=int(deposit_won or 0),
        monthly_rent_won=int(monthly_rent_won or 0),
        exclusive_area_m2=float(exclusive_area_m2 or 0),
        floor=int(floor or 0),
        built_year=int(built_year or 0),
        contract_stage=contract_stage,
        document_text=(document_text or "") + "\n" + read_uploaded_text(uploaded_file),
        registry_checked=registry_checked,
        building_checked=building_checked,
        explanation_checked=explanation_checked,
        senior_deposit_unknown=senior_deposit_unknown,
    )
    result = diagnose_contract(ContractInput(**payload_data))
    raw_json = json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
    return result, result.report_html, raw_json


def load_example(name: str) -> dict[str, Any]:
    return dict(EXAMPLES[name])


def render_result_cards(st: Any, result: Any) -> None:
    features = result.features
    grade_color = level_color(result.grade)
    st.markdown(
        f"""
        <div style="border:1px solid #d0d5dd;border-left:10px solid {grade_color};border-radius:10px;padding:18px 20px;background:#ffffff;">
          <div style="font-size:1rem;color:#475467;">진단 결과</div>
          <div style="font-size:2rem;font-weight:800;color:{grade_color};">{result.grade}</div>
          <div style="margin-top:6px;color:#475467;">점수가 높을수록 계약 전 추가 확인이 필요합니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("위험 점수", f"{result.score}점")
    c2.metric("진단 신뢰도", result.confidence)
    c3.metric("전세가율", f"{features['jeonse_ratio']:.1f}%")
    c4.metric("유사 거래", f"{features['similar_transaction_count']}건")

    c5, c6 = st.columns(2)
    c5.metric("예상 적정 전세가", money(features["predicted_rent_price"]))
    c6.metric("추정 매매가", money(features["predicted_sale_price"]))


def render_file_cards(st: Any, guide: dict[str, Any]) -> None:
    st.subheader("업로드하면 좋은 파일")
    st.caption("모든 파일이 없어도 진단은 가능하지만, 문서가 많을수록 결과 신뢰도가 올라갑니다.")
    files = guide.get("upload_files", [])
    for row_start in range(0, len(files), 2):
        cols = st.columns(2)
        for col, item in zip(cols, files[row_start:row_start + 2]):
            col.markdown(
                f"""
                <div class="info-card">
                  <div class="card-title">{item['title']}</div>
                  <div class="card-body">{item['why']}</div>
                  <div class="card-body"><b>어디서:</b> {item['where']}</div>
                  <div class="card-body"><b>방법:</b> {item['how']}</div>
                  <a class="card-link" href="{item['url']}" target="_blank" rel="noopener">공식 사이트 열기</a>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_guided_actions(st: Any, result: Any, guide: dict[str, Any]) -> None:
    risk_actions = guide.get("risk_actions", {})
    keys = [signal.get("key") for signal in result.signals]
    ordered_keys = list(dict.fromkeys(keys + ["unchecked", "jeonse_ratio"]))
    st.subheader("어디서 어떻게 확인하나요?")
    shown = 0
    for key in ordered_keys:
        actions = risk_actions.get(key)
        if not actions:
            continue
        shown += 1
        st.markdown("".join(f"- {action}\n" for action in actions))
    if shown == 0:
        st.write("계약 직전 등기부등본과 건축물대장을 다시 발급해 최신 권리관계를 확인하세요.")

    st.markdown("#### 공식 확인 링크")
    for item in guide.get("upload_files", [])[:5]:
        st.markdown(f"- [{item['where']} - {item['title']}]({item['url']})")


def render_streamlit_app() -> None:
    import streamlit as st
    import streamlit.components.v1 as components

    st.set_page_config(
        page_title="전세계약 안심진단",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
        .stApp, [data-testid="stAppViewContainer"] {background:#f5f7fb !important; color:#101828 !important;}
        [data-testid="stHeader"] {background:rgba(245,247,251,0.96) !important;}
        .block-container {max-width: 1080px; padding-top: 2rem;}
        div[data-testid="stMetric"] {background: #ffffff; border: 1px solid #d0d5dd; padding: 14px 16px; border-radius: 8px;}
        .step-box {border:1px solid #e4e7ec; border-radius:10px; padding:16px 18px; background:#ffffff;}
        .info-card {border:1px solid #d0d5dd;border-radius:8px;background:#fff;padding:16px 18px;margin-bottom:12px;min-height:190px;}
        .card-title {font-weight:800;color:#003675;font-size:1.02rem;margin-bottom:8px;}
        .card-body {color:#344054;font-size:.94rem;margin:5px 0;line-height:1.45;}
        .card-link {display:inline-block;margin-top:8px;color:#005ea8;font-weight:700;text-decoration:none;}
        .card-link:hover {text-decoration:underline;}
        h1, h2, h3 {color:#101828;}
        .muted {color:#667085;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("전세계약 안심진단")
    st.caption("계약 전에 보증금, 집 정보, 등기부·건축물대장 내용을 한 번에 점검해보는 임차인용 MVP입니다.")
    guide = tenant_guide()

    st.info("이 서비스는 법률 판단을 대신하지 않습니다. 위험 신호가 나오면 계약을 서두르지 말고 공인중개사, HUG, 지자체 상담창구 또는 법률 전문가에게 확인하세요.")

    with st.expander("처음 사용하는 분을 위한 진행 순서", expanded=True):
        cols = st.columns(3)
        cols[0].markdown('<div class="step-box"><b>1. 문서 준비</b><br><span class="muted">등기부등본, 건축물대장, 계약서 내용을 업로드하거나 붙여넣습니다.</span></div>', unsafe_allow_html=True)
        cols[1].markdown('<div class="step-box"><b>2. 계약 정보 입력</b><br><span class="muted">주소, 보증금, 면적, 층, 건축연도만 입력하면 됩니다.</span></div>', unsafe_allow_html=True)
        cols[2].markdown('<div class="step-box"><b>3. 결과 확인</b><br><span class="muted">위험등급, 이유, 다음 행동, 공식 근거를 확인합니다.</span></div>', unsafe_allow_html=True)

    render_file_cards(st, guide)

    scenario = st.selectbox("빠른 테스트 예시", list(EXAMPLES.keys()), index=0)
    defaults = load_example(scenario)

    with st.form("tenant_diagnosis_form"):
        st.subheader("계약 정보")
        left, right = st.columns([1, 1])
        with left:
            address = st.text_input("주소", defaults["address"])
            legal_dong_code = st.text_input("법정동코드", defaults["legal_dong_code"], help="모르면 비워두지 말고 현재 알고 있는 코드나 행정동 정보를 입력하세요.")
            housing_type = st.selectbox(
                "주택유형",
                HOUSING_TYPES,
                index=HOUSING_TYPES.index(defaults["housing_type"]) if defaults["housing_type"] in HOUSING_TYPES else 0,
            )
            deposit_won = st.number_input("전세보증금", min_value=0, value=int(defaults["deposit_won"]), step=10_000_000, format="%d")
            monthly_rent_won = st.number_input("월세가 있으면 입력", min_value=0, value=int(defaults["monthly_rent_won"]), step=50_000, format="%d")
        with right:
            exclusive_area_m2 = st.number_input("전용면적(㎡)", min_value=1.0, value=float(defaults["exclusive_area_m2"]), step=1.0)
            floor = st.number_input("층", min_value=-5, max_value=80, value=int(defaults["floor"]), step=1)
            built_year = st.number_input("건축연도", min_value=1900, max_value=2030, value=int(defaults["built_year"]), step=1)
            contract_stage = st.selectbox(
                "현재 단계",
                CONTRACT_STAGES,
                index=CONTRACT_STAGES.index(defaults["contract_stage"]) if defaults["contract_stage"] in CONTRACT_STAGES else 1,
            )

        st.subheader("확인한 문서")
        doc_left, doc_right = st.columns([1, 1])
        with doc_left:
            uploaded_file = st.file_uploader("등기부등본/건축물대장/계약서 PDF 또는 TXT", type=["pdf", "txt"], accept_multiple_files=True)
            document_text = st.text_area("문서에서 보이는 특이사항을 붙여넣기", defaults["document_text"], height=150)
        with doc_right:
            registry_checked = st.checkbox("등기부등본을 확인했습니다", value=bool(defaults["registry_checked"]))
            building_checked = st.checkbox("건축물대장을 확인했습니다", value=bool(defaults["building_checked"]))
            explanation_checked = st.checkbox("중개대상물 확인설명서를 받았습니다", value=bool(defaults["explanation_checked"]))
            senior_deposit_unknown = st.checkbox("다가구 주택의 다른 임차인 보증금을 아직 모릅니다", value=bool(defaults["senior_deposit_unknown"]))

        submitted = st.form_submit_button("안심진단 시작", type="primary", use_container_width=True)

    if submitted:
        with st.spinner("계약 정보를 진단하고 공식 근거를 찾는 중입니다."):
            result, html_report, raw_json = run_diagnosis(
                uploaded_file,
                address,
                legal_dong_code,
                housing_type,
                deposit_won,
                monthly_rent_won,
                exclusive_area_m2,
                floor,
                built_year,
                contract_stage,
                document_text,
                registry_checked,
                building_checked,
                explanation_checked,
                senior_deposit_unknown,
            )
        st.session_state["last_result"] = result
        st.session_state["last_html_report"] = html_report
        st.session_state["last_json"] = raw_json

    result = st.session_state.get("last_result")
    if result:
        st.divider()
        render_result_cards(st, result)

        signals = result.signals
        if signals:
            st.subheader("왜 위험한가요?")
            for item in signals[:6]:
                st.markdown(f"**[{item['level']}] {item['title']}**  \n{item['detail']}")
        else:
            st.success("현재 입력값에서는 큰 위험 신호가 낮게 탐지되었습니다. 그래도 계약 직전 등기부등본은 다시 확인하세요.")

        render_guided_actions(st, result, guide)

        st.subheader("지금 해야 할 일")
        for index, action in enumerate(result.actions, start=1):
            st.markdown(f"{index}. {action}")

        st.subheader("공식 근거")
        for item in result.evidence[:5]:
            st.markdown(f"- [{item['title']}]({item['official_url']}) - {item['provider']}")

        with st.expander("건축물대장 검색 참고"):
            matches = result.features.get("building_registry_matches", [])[:3]
            if not matches:
                st.write("입력 주소와 강하게 매칭된 건축물대장 샘플이 없습니다.")
            for match in matches:
                st.write(match.get("text", match.get("title", "")))

        st.download_button(
            "진단 리포트 HTML 다운로드",
            data=st.session_state["last_html_report"].encode("utf-8"),
            file_name="jeonse-risk-report.html",
            mime="text/html",
            use_container_width=True,
        )

    with st.expander("이 앱이 참고하는 공식자료"):
        for item in guide.get("upload_files", []):
            st.markdown(f"- [{item['title']}]({item['url']}) - {item['source_basis']}")
        for item in guide.get("official_links", []):
            st.markdown(f"- [{item['title']}]({item['url']})")

    st.caption("GitHub 저장소에는 데이터 전처리, RAG 구축, 모델 학습, 성능평가 코드와 포트폴리오 문서를 별도로 포함했습니다.")


render_streamlit_app()
