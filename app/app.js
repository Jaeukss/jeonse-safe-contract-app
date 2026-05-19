const engine = window.JeonseRiskEngine;
const form = document.querySelector("#riskForm");
const documentText = document.querySelector("#documentText");
let lastReport;

const textFields = [
  "address",
  "legalDongCode",
  "housingType",
  "deposit",
  "monthlyRent",
  "area",
  "floor",
  "builtYear",
  "contractStage",
  "mortgageAmount",
  "documentText"
];
const boolFields = [
  "registryChecked",
  "buildingChecked",
  "explanationChecked",
  "mortgageFlag",
  "seizureFlag",
  "provisionalSeizureFlag",
  "trustFlag",
  "leaseholdRegistrationFlag",
  "ownershipTransferFlag",
  "violationFlag",
  "seniorDepositUnknown"
];

const officialSources = [
  {
    group: "규정·서식",
    title: "주택임대차보호법",
    provider: "법제처 국가법령정보센터",
    url: "https://www.law.go.kr/LSW/lsInfoP.do?lsId=001248",
    use: "대항력, 확정일자, 우선변제권, 보증금 보호 설명"
  },
  {
    group: "규정·서식",
    title: "주택임대차보호법 시행령",
    provider: "법제처 국가법령정보센터",
    url: "https://www.law.go.kr/법령/주택임대차보호법시행령",
    use: "소액임차인 보호 범위와 보증금 규모별 확인"
  },
  {
    group: "규정·서식",
    title: "공인중개사법",
    provider: "법제처 국가법령정보센터",
    url: "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=273341",
    use: "중개대상물 확인·설명 의무와 설명자료 요구"
  },
  {
    group: "규정·서식",
    title: "부동산등기법",
    provider: "법제처 국가법령정보센터",
    url: "https://www.law.go.kr/법령/부동산등기법",
    use: "근저당권, 압류, 가압류, 신탁등기 위험 설명"
  },
  {
    group: "규정·서식",
    title: "주택임대차 표준계약서",
    provider: "법무부",
    url: "https://moj.go.kr/moj/314/subview.do",
    use: "특약, 보증금 반환, 관리비, 권리보장 조항 확인"
  },
  {
    group: "규정·서식",
    title: "중개대상물 확인·설명서",
    provider: "법제처 국가법령정보센터",
    url: "https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joNo=0016&lsiSeq=263573&urlMode=lsScJoRltInfoR",
    use: "주거용 건축물 확인설명서 서식과 필수 확인 항목"
  },
  {
    group: "안내·보증",
    title: "건축물대장 발급·열람 안내",
    provider: "정부24",
    url: "https://m.gov.kr/mw/AA020InfoCappView.do?CappBizCD=15000000098&HighCtgCD=A09005&tp_seq=01",
    use: "주용도, 전유면적, 사용승인일, 위반건축물 확인"
  },
  {
    group: "안내·보증",
    title: "HUG 전세보증금반환보증",
    provider: "주택도시보증공사",
    url: "https://www.khug.or.kr/hug/web/ig/dr/igdr000001.jsp",
    use: "보증한도, 보증조건, 선순위채권 확인"
  },
  {
    group: "안내·보증",
    title: "국토교통부 안전한 집",
    provider: "국토교통부",
    url: "https://www.molit.go.kr/2023safehome/main.jsp",
    use: "전세사기 예방 체크리스트와 계약 단계별 확인"
  },
  {
    group: "안내·보증",
    title: "서울시 전세사기 예방 안내",
    provider: "서울주거포털",
    url: "https://housing.seoul.go.kr/site/main/content/sh05_070100",
    use: "지자체 상담센터와 피해 예방·지원 절차"
  },
  {
    group: "공공데이터 API",
    title: "아파트 전월세 실거래가",
    provider: "국토교통부 공공데이터포털",
    url: "https://www.data.go.kr/data/15126474/openapi.do",
    use: "전세 시세 비교"
  },
  {
    group: "공공데이터 API",
    title: "아파트 매매 실거래가",
    provider: "국토교통부 공공데이터포털",
    url: "https://www.data.go.kr/data/15126469/openapi.do",
    use: "추정 매매가와 전세가율 계산"
  },
  {
    group: "공공데이터 API",
    title: "오피스텔 전월세 실거래가",
    provider: "국토교통부 공공데이터포털",
    url: "https://www.data.go.kr/data/15126475/openapi.do",
    use: "오피스텔 전세 시세 비교"
  },
  {
    group: "공공데이터 API",
    title: "오피스텔 매매 실거래가",
    provider: "국토교통부 공공데이터포털",
    url: "https://www.data.go.kr/data/15126464/openapi.do",
    use: "오피스텔 추정 매매가 계산"
  },
  {
    group: "공공데이터 API",
    title: "실거래가 정보 파일데이터",
    provider: "국토교통부 공공데이터포털",
    url: "https://www.data.go.kr/data/3050988/fileData.do",
    use: "CSV 다운로드 기반 운영 데이터 교체"
  },
  {
    group: "공공데이터 API",
    title: "건축물대장 정보 서비스",
    provider: "국토교통부 공공데이터포털",
    url: "https://www.data.go.kr/dataset/15004825/openapi.do",
    use: "건축물대장 표제부, 전유부, 층별개요 수집"
  }
];

const submissionAssets = [
  {
    group: "백서·증빙",
    title: "프로젝트 백서",
    provider: "MVP 제출 문서",
    url: "../docs/WHITEPAPER.md",
    use: "문제정의, 데이터셋, RAG, 진단 로직, 배포 구조 설명"
  },
  {
    group: "백서·증빙",
    title: "공식 RAG 출처 링크표",
    provider: "MVP 제출 문서",
    url: "../docs/OFFICIAL_RAG_SOURCE_LINKS.md",
    use: "법령, 안내문, 표준서식, 공공데이터 API 공식 링크"
  },
  {
    group: "백서·증빙",
    title: "AI 활용 및 데이터 사용 증빙",
    provider: "MVP 제출 문서",
    url: "../docs/AI_USE_EVIDENCE.md",
    use: "AI 도구 활용과 데이터 활용 사실 증빙"
  },
  {
    group: "데이터셋",
    title: "사용자 입력 샘플 CSV",
    provider: "MVP 데이터",
    url: "../data/user_input_samples.csv",
    use: "주소, 법정동코드, 주택유형, 보증금, 월세, 면적, 층, 계약 단계"
  },
  {
    group: "데이터셋",
    title: "실거래가 MVP CSV",
    provider: "MVP 데이터",
    url: "../data/market_transactions_mvp.csv",
    use: "전세가율, 시세괴리율, 적정 전세가, 추정 매매가 계산"
  },
  {
    group: "데이터셋",
    title: "건축물대장 MVP CSV",
    provider: "MVP 데이터",
    url: "../data/building_registry_mvp.csv",
    use: "주용도, 전유면적, 사용승인연도, 위반건축물 여부"
  },
  {
    group: "RAG",
    title: "RAG 근거 문서 데이터",
    provider: "MVP 데이터",
    url: "../data/rag_documents_mvp.json",
    use: "위험키별 공식 근거 요약 chunk와 응답 규칙"
  },
  {
    group: "RAG",
    title: "RAG 공식 출처 원장",
    provider: "MVP 데이터",
    url: "../data/rag_official_sources.json",
    use: "RAG 문서 10종의 공식 URL, 확인일, 활용 목적"
  },
  {
    group: "API",
    title: "공공데이터 API 카탈로그",
    provider: "MVP 데이터",
    url: "../data/source_catalog.json",
    use: "RTMS, 건축물대장, 법령, 보증 안내 원천 목록"
  },
  {
    group: "API",
    title: "공공데이터 수집기",
    provider: "MVP 스크립트",
    url: "../scripts/collect_public_data.py",
    use: "data.go.kr 서비스키 기반 원천 XML 수집과 CSV 정규화"
  },
  {
    group: "배포",
    title: "Hugging Face 배포 메모",
    provider: "MVP 제출 문서",
    url: "../docs/HUGGINGFACE_DEPLOYMENT.md",
    use: "Static Space 설정, 검증 명령, 필요한 배포 정보"
  },
  {
    group: "배포",
    title: "제출 패키지 매니페스트",
    provider: "MVP 데이터",
    url: "../data/submission_package.json",
    use: "앱, 데이터셋, 문서, 배포 구성을 한 번에 확인"
  }
];

function el(name) {
  return form.elements[name];
}

function readForm() {
  const input = {};
  textFields.forEach((name) => {
    const field = name === "documentText" ? documentText : el(name);
    input[name] = field.type === "number" ? Number(field.value || 0) : field.value;
  });
  boolFields.forEach((name) => input[name] = el(name).checked);
  return input;
}

function fillCase(key) {
  const item = engine.examples[key];
  if (!item) return;
  textFields.forEach((name) => {
    const field = name === "documentText" ? documentText : el(name);
    field.value = item.input[name] ?? (field.type === "number" ? 0 : "");
  });
  boolFields.forEach((name) => el(name).checked = Boolean(item.input[name]));
  document.querySelector("#scenarioLabel").textContent = item.label;
  document.querySelectorAll("[data-case]").forEach((button) => button.classList.toggle("active", button.dataset.case === key));
  render();
}

function metric(label, value) {
  return `<article class="metric"><span>${label}</span><strong>${value}</strong></article>`;
}

function pct(value) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function render() {
  lastReport = engine.runLagChain(readForm());
  document.querySelector("#grade").textContent = lastReport.grade;
  document.querySelector("#summary").textContent = lastReport.summary;
  document.querySelector("#score").textContent = `${Math.round(lastReport.score)}점`;
  document.querySelector("#confidence").textContent = `진단 신뢰도 ${lastReport.confidenceLabel}`;

  const gradeCard = document.querySelector(".status-grade");
  gradeCard.className = `status-card status-grade ${lastReport.tone}`;

  document.querySelector("#metrics").innerHTML = [
    metric("예측 적정 전세가", engine.money(lastReport.features.predicted_rent_price)),
    metric("추정 매매가", engine.money(lastReport.features.predicted_sale_price)),
    metric("전세가율", pct(lastReport.features.jeonse_ratio)),
    metric("시세괴리율", pct(lastReport.features.rent_gap_rate))
  ].join("");

  document.querySelector("#signals").innerHTML = lastReport.signals.length
    ? lastReport.signals.slice(0, 7).map(renderSignal).join("")
    : `<article class="risk-card"><h3>중대한 위험 신호 낮음</h3><p>확인된 범위에서는 큰 위험 신호가 낮게 나타났습니다.</p><small>계약 전 최신 문서 재확인은 필요합니다.</small></article>`;

  document.querySelector("#extractedSignals").innerHTML = renderExtracted(lastReport.parsed);
  document.querySelector("#chainView").innerHTML = lastReport.chain.map(renderProcessStep).join("");
  document.querySelector("#evidence").innerHTML = lastReport.evidence.length
    ? lastReport.evidence.map(renderEvidence).join("")
    : `<article class="evidence-card"><h3>근거 연결 대기</h3><p>위험 신호가 적거나 문서 정보가 부족합니다.</p><small>데이터를 추가하면 관련 근거를 연결합니다.</small></article>`;
  document.querySelector("#actions").innerHTML = lastReport.actions.map((item) => `<li>${item}</li>`).join("");
  renderOfficialSources();
  renderSubmissionAssets();
  renderMarketRows();
}

function applyParsedToChecklist(parsed) {
  const syncMap = {
    mortgageFlag: parsed.mortgageFlag,
    seizureFlag: parsed.seizureFlag,
    provisionalSeizureFlag: parsed.provisionalSeizureFlag,
    trustFlag: parsed.trustFlag,
    leaseholdRegistrationFlag: parsed.leaseholdRegistrationFlag,
    ownershipTransferFlag: parsed.ownershipTransferFlag,
    violationFlag: parsed.violationFlag
  };
  Object.entries(syncMap).forEach(([name, value]) => {
    el(name).checked = Boolean(value);
  });
  if (parsed.mortgageAmount) {
    el("mortgageAmount").value = parsed.mortgageAmount;
  } else if (parsed.extractedChars > 0 && !parsed.mortgageFlag) {
    el("mortgageAmount").value = 0;
  }
}

function renderSignal(signal) {
  const cls = signal.level === "고위험" ? "critical" : signal.level === "위험" ? "danger" : signal.level === "주의" ? "warning" : "";
  return `<article class="risk-card ${cls}"><h3>${signal.title}</h3><p>${signal.detail}</p><small>${signal.action}</small></article>`;
}

function renderEvidence(item) {
  return `<article class="evidence-card"><h3>${item.title}</h3><p>${item.plain}</p><small>근거: ${item.source}<br />행동: ${item.action}</small></article>`;
}

function renderOfficialSources() {
  document.querySelector("#officialSources").innerHTML = officialSources.map((item) => `
    <article>
      <span class="source-kind">${item.group}</span>
      <b>${item.title}</b>
      <span>${item.provider}</span>
      <p>${item.use}</p>
      <a href="${item.url}" target="_blank" rel="noopener noreferrer">공식 자료 열기</a>
    </article>
  `).join("");
}

function renderSubmissionAssets() {
  document.querySelector("#submissionAssets").innerHTML = submissionAssets.map((item) => `
    <article>
      <span class="source-kind">${item.group}</span>
      <b>${item.title}</b>
      <span>${item.provider}</span>
      <p>${item.use}</p>
      <a href="${item.url}" target="_blank" rel="noopener noreferrer">자료 열기</a>
    </article>
  `).join("");
}

function renderProcessStep(step, index) {
  return `<article class="process-step"><b>${index + 1}</b><div><h3>${step.label}</h3><p>${step.detail}</p></div></article>`;
}

function renderExtracted(parsed) {
  const items = [
    ["근저당권", parsed.mortgageFlag ? `있음 / ${engine.money(parsed.mortgageAmount)}` : "미검출"],
    ["압류", parsed.seizureFlag ? "있음" : "미검출"],
    ["가압류", parsed.provisionalSeizureFlag ? "있음" : "미검출"],
    ["신탁등기", parsed.trustFlag ? "있음" : "미검출"],
    ["임차권등기", parsed.leaseholdRegistrationFlag ? "있음" : "미검출"],
    ["위반건축물", parsed.violationFlag ? "있음" : "미검출"],
    ["소유권 이전", parsed.ownershipTransferFlag ? "확인 필요" : "미검출"],
    ["추출 문자수", `${parsed.extractedChars}자`]
  ];
  return items.map(([key, value]) => `<article><b>${key}</b><span>${value}</span></article>`).join("");
}

function renderMarketRows() {
  const rows = [...lastReport.market.rent, ...lastReport.market.sale].slice(0, 8);
  document.querySelector("#marketRows").innerHTML = rows.map((row) => `
    <tr>
      <td>${row.region}</td>
      <td>${row.housingType}</td>
      <td>${row.tradeType}</td>
      <td>${engine.money(row.price)}</td>
      <td>${engine.money(row.monthlyRent || 0)}</td>
      <td>${row.area.toFixed(1)}m²</td>
      <td>${row.tradeMonth}</td>
    </tr>
  `).join("");
}

async function extractFileText(file) {
  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  const utf8 = new TextDecoder("utf-8", { fatal: false }).decode(bytes);
  if (!file.name.toLowerCase().endsWith(".pdf")) return utf8;

  const chunks = [];
  const latin = new TextDecoder("latin1", { fatal: false }).decode(bytes);
  [utf8, latin].forEach((source) => {
    for (const match of source.matchAll(/\(([^()]{2,300})\)\s*Tj/g)) chunks.push(match[1]);
    for (const match of source.matchAll(/\[([^\]]{2,1200})\]\s*TJ/g)) chunks.push(match[1].replace(/[()<>]/g, " "));
  });

  const decoded = chunks.join("\n").replace(/\\([()\\])/g, "$1");
  if (decoded.trim()) return decoded.trim();

  return ["근저당권", "채권최고액", "압류", "가압류", "신탁등기", "임차권등기", "위반건축물", "소유권이전"]
    .filter((word) => utf8.includes(word) || latin.includes(word))
    .join("\n")
    .trim();
}

function setManualInput() {
  document.querySelector("#scenarioLabel").textContent = "직접 입력";
  document.querySelectorAll("[data-case]").forEach((button) => button.classList.remove("active"));
}

document.querySelector("#documentFile").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  document.querySelector("#fileState").textContent = `${file.name} (${Math.round(file.size / 1024)}KB) 읽는 중`;
  const text = await extractFileText(file);
  documentText.value = text || "텍스트를 자동 추출하지 못했습니다. 스캔 PDF라면 주요 항목을 직접 입력하세요.";
  applyParsedToChecklist(engine.parseDocumentText(documentText.value));
  document.querySelector("#fileState").textContent = `${file.name} 업로드 완료 · 추출 ${documentText.value.length}자`;
  setManualInput();
  render();
});

form.addEventListener("input", () => {
  setManualInput();
  render();
});

documentText.addEventListener("input", () => {
  setManualInput();
  render();
});

document.querySelectorAll("[data-case]").forEach((button) => {
  button.addEventListener("click", () => fillCase(button.dataset.case));
});

document.querySelectorAll("[data-next]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector(button.dataset.next)?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

const sectionLinks = Array.from(document.querySelectorAll("[data-section-link]"));
function setActiveSection(id) {
  sectionLinks.forEach((link) => link.classList.toggle("active", link.getAttribute("href") === `#${id}`));
}

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (visible) setActiveSection(visible.target.id);
  }, { rootMargin: "-20% 0px -55% 0px", threshold: [0.15, 0.35, 0.6] });

  document.querySelectorAll(".step-page").forEach((section) => observer.observe(section));
}

sectionLinks.forEach((link) => {
  link.addEventListener("click", () => {
    const id = link.getAttribute("href")?.slice(1);
    if (id) setActiveSection(id);
  });
});

function reportText() {
  const r = lastReport;
  const input = readForm();
  return [
    "전세계약 위험 진단 리포트",
    `위험등급: ${r.grade}`,
    `진단 신뢰도: ${r.confidenceLabel} (${r.confidenceScore}점)`,
    `계약 단계: ${input.contractStage}`,
    `전세보증금: ${engine.money(input.deposit)}`,
    `월세: ${engine.money(input.monthlyRent)}`,
    `예측 적정 전세가: ${engine.money(r.features.predicted_rent_price)}`,
    `추정 매매가: ${engine.money(r.features.predicted_sale_price)}`,
    `전세가율: ${pct(r.features.jeonse_ratio)}`,
    "",
    "핵심 위험 신호",
    ...(r.signals.length ? r.signals.map((signal) => `- ${signal.title}: ${signal.detail}`) : ["- 중대한 위험 신호 낮음"]),
    "",
    "다음 행동",
    ...r.actions.map((action, index) => `${index + 1}. ${action}`),
    "",
    "참고 근거",
    ...(r.evidence.length ? r.evidence.map((evidence) => `- ${evidence.title}: ${evidence.source}`) : ["- 추가 확인 필요"])
  ].join("\n");
}

document.querySelector("#copyReport").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(reportText());
  } catch {
    const backup = document.createElement("textarea");
    backup.value = reportText();
    document.body.appendChild(backup);
    backup.select();
    document.execCommand("copy");
    backup.remove();
  }
});

document.querySelector("#downloadJson").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(lastReport, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "jeonse-contract-risk-report.json";
  a.click();
  URL.revokeObjectURL(url);
});

fillCase("highRatio");
