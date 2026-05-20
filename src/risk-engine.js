(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.JeonseRiskEngine = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const HUNDRED_MILLION = 100000000;
  const MILLION = 1000000;

  const marketSeed = [
    ["서울 마포구 아현동", "1144010100", "오피스텔", "전세", "2025-12", 265000000, 0, 29.8, 8, 2019],
    ["서울 마포구 아현동", "1144010100", "오피스텔", "전세", "2025-10", 252000000, 0, 30.4, 11, 2018],
    ["서울 마포구 아현동", "1144010100", "오피스텔", "매매", "2025-11", 392000000, 0, 29.8, 8, 2019],
    ["서울 마포구 아현동", "1144010100", "오피스텔", "매매", "2025-07", 381000000, 0, 30.1, 10, 2018],
    ["서울 강서구 화곡동", "1150010300", "연립다세대", "전세", "2025-12", 218000000, 0, 42.1, 4, 2016],
    ["서울 강서구 화곡동", "1150010300", "연립다세대", "전세", "2025-09", 225000000, 0, 44.2, 3, 2015],
    ["서울 강서구 화곡동", "1150010300", "연립다세대", "매매", "2025-11", 285000000, 0, 42.0, 4, 2016],
    ["서울 강서구 화곡동", "1150010300", "연립다세대", "매매", "2025-07", 292000000, 0, 44.3, 3, 2015],
    ["서울 관악구 신림동", "1162010200", "다가구", "전세", "2025-12", 135000000, 0, 27.1, 2, 2004],
    ["서울 관악구 신림동", "1162010200", "다가구", "전세", "2025-08", 145000000, 0, 29.5, 3, 2006],
    ["서울 관악구 신림동", "1162010200", "다가구", "매매", "2025-10", 690000000, 0, 137.0, 0, 2004],
    ["서울 관악구 신림동", "1162010200", "다가구", "매매", "2025-05", 735000000, 0, 151.0, 0, 2006],
    ["서울 송파구 가락동", "1171010700", "아파트", "전세", "2025-12", 655000000, 0, 59.8, 15, 2018],
    ["서울 송파구 가락동", "1171010700", "아파트", "전세", "2025-09", 642000000, 0, 59.9, 12, 2017],
    ["서울 송파구 가락동", "1171010700", "아파트", "매매", "2025-11", 1140000000, 0, 59.8, 15, 2018],
    ["서울 송파구 가락동", "1171010700", "아파트", "매매", "2025-08", 1115000000, 0, 59.9, 12, 2017],
    ["인천 미추홀구 주안동", "2817710500", "연립다세대", "전세", "2025-11", 118000000, 0, 39.2, 3, 2002],
    ["인천 미추홀구 주안동", "2817710500", "연립다세대", "전세", "2025-05", 126000000, 0, 41.0, 4, 2003],
    ["인천 미추홀구 주안동", "2817710500", "연립다세대", "매매", "2025-10", 168000000, 0, 39.1, 3, 2002],
    ["인천 미추홀구 주안동", "2817710500", "연립다세대", "매매", "2025-04", 176000000, 0, 41.2, 4, 2003]
  ].map(([region, legalDongCode, housingType, tradeType, tradeMonth, price, monthlyRent, area, floor, builtYear]) => ({
    region,
    legalDongCode,
    housingType,
    tradeType,
    tradeMonth,
    price,
    monthlyRent,
    area,
    floor,
    builtYear
  }));

  const buildingSeed = [
    { address: "서울특별시 강서구 화곡동 1027-8 해솔빌라 402호", legalDongCode: "1150010300", housingType: "연립다세대", buildingName: "해솔빌라", mainUse: "공동주택", exclusiveArea: 42.1, approvalYear: 2016, violationFlag: false },
    { address: "서울특별시 송파구 가락동 479 그린파크 1502호", legalDongCode: "1171010700", housingType: "아파트", buildingName: "그린파크", mainUse: "공동주택", exclusiveArea: 59.8, approvalYear: 2018, violationFlag: false },
    { address: "인천광역시 미추홀구 주안동 1450-4 도담빌 301호", legalDongCode: "2817710500", housingType: "연립다세대", buildingName: "도담빌", mainUse: "공동주택", exclusiveArea: 39.2, approvalYear: 2002, violationFlag: true },
    { address: "서울특별시 관악구 신림동 1542-3 한빛하우스 203호", legalDongCode: "1162010200", housingType: "다가구", buildingName: "한빛하우스", mainUse: "단독주택(다가구)", exclusiveArea: 27.1, approvalYear: 2004, violationFlag: false }
  ];

  const knowledge = [
    { key: "jeonse_ratio", source: "국토교통부 실거래가 공개자료, HUG 전세보증금반환보증 안내", title: "전세가율", plain: "보증금이 추정 매매가에 비해 높으면 경매나 급매 상황에서 보증금 회수가 어려워질 수 있습니다.", action: "주변 매매 실거래가와 보증보험 가능성을 함께 확인하세요." },
    { key: "rent_gap", source: "국토교통부 실거래가 공개자료", title: "시세괴리", plain: "주변 전세 거래보다 보증금이 높으면 가격 산정 근거를 추가로 확인해야 합니다.", action: "같은 법정동, 같은 주택유형, 유사 면적 거래를 3건 이상 비교하세요." },
    { key: "mortgage", source: "부동산등기사항증명서 확인 안내", title: "근저당권", plain: "근저당권은 집을 담보로 돈을 빌렸다는 표시라 보증금보다 먼저 변제될 금액이 있을 수 있습니다.", action: "채권최고액, 말소 조건, 잔금 전 말소 등기 여부를 확인하세요." },
    { key: "seizure", source: "부동산등기법 관련 안내", title: "압류·가압류", plain: "압류나 가압류는 소유자의 채무 문제로 재산 처분이 제한될 수 있다는 신호입니다.", action: "말소 등기 완료 전까지 계약 진행을 보류하고 전문가 검토를 받으세요." },
    { key: "trust", source: "전세사기 예방 안내자료, 주택임대차 표준계약서", title: "신탁등기", plain: "신탁등기가 있으면 등기상 소유자와 임대 권한자가 다를 수 있습니다.", action: "수탁자 동의서와 신탁원부를 우선 확인하세요." },
    { key: "violation", source: "건축물대장 확인 안내", title: "위반건축물", plain: "위반건축물은 보증보험, 대출, 주택 용도 판단에 영향을 줄 수 있습니다.", action: "정부24 또는 세움터에서 건축물대장을 확인하세요." },
    { key: "multifamily", source: "국토교통부 전세사기 예방 체크리스트", title: "다가구 선순위 보증금", plain: "다가구는 같은 건물의 다른 임차인 보증금 규모가 반환 순위에 영향을 줄 수 있습니다.", action: "선순위 임차보증금 총액과 확정일자 현황을 확인하세요." },
    { key: "unchecked", source: "전세계약 전 확인서류 안내", title: "문서 미확인", plain: "문서를 확인하지 않으면 권리관계와 건물 용도 판단이 제한됩니다.", action: "계약 전과 잔금 전 등기부등본, 건축물대장을 다시 발급하세요." }
  ];

  const examples = {
    highRatio: {
      label: "전세가율 높음",
      input: {
        address: "서울특별시 강서구 화곡동 1027-8 해솔빌라 402호",
        legalDongCode: "1150010300",
        housingType: "연립다세대",
        deposit: 270000000,
        monthlyRent: 0,
        area: 42.1,
        floor: 4,
        builtYear: 2016,
        contractStage: "계약 전 확인",
        registryChecked: true,
        buildingChecked: true,
        explanationChecked: false,
        mortgageAmount: 90000000,
        documentText: "등기부등본 을구 근저당권 설정 채권최고액 9천만원. 최근 소유권 이전 있음."
      }
    },
    trust: {
      label: "신탁·압류 고위험",
      input: {
        address: "인천광역시 미추홀구 주안동 1450-4 도담빌 301호",
        legalDongCode: "2817710500",
        housingType: "연립다세대",
        deposit: 165000000,
        monthlyRent: 0,
        area: 39.2,
        floor: 3,
        builtYear: 2002,
        contractStage: "잔금 전 확인",
        registryChecked: true,
        buildingChecked: true,
        explanationChecked: true,
        mortgageAmount: 70000000,
        documentText: "신탁등기, 압류, 채권최고액 7천만원, 위반건축물 표시가 확인됨."
      }
    },
    safe: {
      label: "확인 양호",
      input: {
        address: "서울특별시 송파구 가락동 479 그린파크 1502호",
        legalDongCode: "1171010700",
        housingType: "아파트",
        deposit: 620000000,
        monthlyRent: 0,
        area: 59.8,
        floor: 15,
        builtYear: 2018,
        contractStage: "계약 전 확인",
        registryChecked: true,
        buildingChecked: true,
        explanationChecked: true,
        mortgageAmount: 0,
        documentText: "근저당권, 압류, 가압류, 신탁등기, 위반건축물 표시 없음."
      }
    },
    unknown: {
      label: "자료 부족",
      input: {
        address: "서울특별시 중구 예시동 10-1",
        legalDongCode: "1114019900",
        housingType: "단독주택",
        deposit: 180000000,
        monthlyRent: 0,
        area: 45,
        floor: 1,
        builtYear: 1998,
        contractStage: "매물 검토",
        registryChecked: false,
        buildingChecked: false,
        explanationChecked: false,
        mortgageAmount: 0,
        documentText: ""
      }
    }
  };

  function number(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function median(values) {
    const clean = values.filter(Number.isFinite).sort((a, b) => a - b);
    if (!clean.length) return 0;
    const mid = Math.floor(clean.length / 2);
    return clean.length % 2 ? clean[mid] : (clean[mid - 1] + clean[mid]) / 2;
  }

  function roundMillion(value) {
    return Math.round(value / MILLION) * MILLION;
  }

  function money(value) {
    const amount = Math.round(number(value));
    if (!amount) return "0원";
    const eok = Math.floor(amount / HUNDRED_MILLION);
    const man = Math.round((amount % HUNDRED_MILLION) / 10000);
    if (eok && man) return `${eok}억 ${man.toLocaleString("ko-KR")}만원`;
    if (eok) return `${eok}억원`;
    return `${man.toLocaleString("ko-KR")}만원`;
  }

  function parseKoreanMoney(text) {
    const normalized = String(text || "").replace(/,/g, "").replace(/\s+/g, "");
    let total = 0;
    const eok = normalized.match(/(\d+(?:\.\d+)?)억/);
    const cheonMan = normalized.match(/(\d+(?:\.\d+)?)천만/);
    const man = normalized.match(/(\d+(?:\.\d+)?)만/);
    if (eok) total += Number(eok[1]) * HUNDRED_MILLION;
    if (cheonMan) total += Number(cheonMan[1]) * 10000000;
    if (man) total += Number(man[1]) * 10000;
    if (!total) {
      const digits = normalized.match(/\d{7,}/);
      if (digits) total = Number(digits[0]);
    }
    return Number.isFinite(total) ? total : 0;
  }

  function comparable(input, tradeType) {
    const code = String(input.legalDongCode || "");
    const type = String(input.housingType || "");
    const area = number(input.area);
    const builtYear = number(input.builtYear);
    const pool = marketSeed.filter((row) => row.tradeType === tradeType && row.housingType === type);
    return pool
      .map((row) => {
        const sameDong = row.legalDongCode === code ? 50 : 0;
        const areaScore = area ? Math.max(0, 30 - Math.abs(row.area - area)) : 8;
        const yearScore = builtYear ? Math.max(0, 20 - Math.abs(row.builtYear - builtYear)) : 8;
        return { ...row, matchScore: sameDong + areaScore + yearScore };
      })
      .filter((row) => row.matchScore > 0)
      .sort((a, b) => b.matchScore - a.matchScore)
      .slice(0, 8);
  }

  function predictMarket(input) {
    const rent = comparable(input, "전세");
    const sale = comparable(input, "매매");
    const area = number(input.area);
    const rentPerM2 = median(rent.map((row) => row.price / row.area));
    const salePerM2 = median(sale.map((row) => row.price / row.area));
    const predictedRent = roundMillion((rentPerM2 || salePerM2 * 0.62) * area);
    const predictedSale = roundMillion((salePerM2 || predictedRent / 0.62) * area);
    const count = rent.length + sale.length;
    const confidence = count >= 6 ? "높음" : count >= 4 ? "보통" : count >= 2 ? "낮음" : "매우 낮음";
    return { rent, sale, predictedRent, predictedSale, comparableCount: count, marketConfidence: confidence };
  }

  function parseDocumentText(text) {
    const raw = String(text || "");
    const compact = raw.replace(/\s+/g, "");
    const allClear = /없음|해당없음|말소완료|기재사항없음/.test(compact) && !/있음|설정|확인됨|채권최고액\s*\d/.test(compact);
    const moneyPattern = /(\d+(?:[,.]\d+)?\s*억(?:\s*\d+(?:[,.]\d+)?\s*천?\s*만원?)?|\d+(?:[,.]\d+)?\s*천?\s*만원?|\d{7,})/;
    const amountMatch =
      raw.match(new RegExp(`채권최고액[^0-9]*${moneyPattern.source}`)) ||
      raw.match(new RegExp(`근저당[^0-9]*${moneyPattern.source}`));
    return {
      mortgageFlag: !allClear && /근저당|채권최고액/.test(compact) && !/근저당권?없음|채권최고액없음/.test(compact),
      mortgageAmount: amountMatch ? parseKoreanMoney(amountMatch[1]) : 0,
      seizureFlag: !allClear && /(?<!가)압류/.test(compact) && !/압류없음/.test(compact),
      provisionalSeizureFlag: !allClear && /가압류/.test(compact) && !/가압류없음/.test(compact),
      trustFlag: !allClear && /신탁/.test(compact) && !/신탁등기없음|신탁없음/.test(compact),
      leaseholdRegistrationFlag: !allClear && /임차권등기/.test(compact),
      ownershipTransferFlag: /소유권이전|최근소유권/.test(compact),
      violationFlag: !allClear && /위반건축물|위반건축/.test(compact) && !/위반건축물.*없음|위반건축없음/.test(compact),
      extractedChars: raw.trim().length
    };
  }

  function findBuilding(input) {
    return buildingSeed.find((item) => item.legalDongCode === input.legalDongCode && item.housingType === input.housingType);
  }

  function bool(value) {
    return value === true || value === "true" || value === "on" || value === "1" || value === 1;
  }

  function runLagChain(input) {
    const parsed = parseDocumentText(input.documentText);
    const building = findBuilding(input);
    const market = predictMarket(input);
    const docs = {
      registryChecked: bool(input.registryChecked),
      buildingChecked: bool(input.buildingChecked),
      explanationChecked: bool(input.explanationChecked),
      mortgageFlag: bool(input.mortgageFlag) || parsed.mortgageFlag,
      mortgageAmount: Math.max(number(input.mortgageAmount), parsed.mortgageAmount),
      seizureFlag: bool(input.seizureFlag) || parsed.seizureFlag,
      provisionalSeizureFlag: bool(input.provisionalSeizureFlag) || parsed.provisionalSeizureFlag,
      trustFlag: bool(input.trustFlag) || parsed.trustFlag,
      leaseholdRegistrationFlag: bool(input.leaseholdRegistrationFlag) || parsed.leaseholdRegistrationFlag,
      ownershipTransferFlag: bool(input.ownershipTransferFlag) || parsed.ownershipTransferFlag,
      violationFlag: bool(input.violationFlag) || parsed.violationFlag || Boolean(building?.violationFlag),
      seniorDepositUnknown: bool(input.seniorDepositUnknown)
    };
    const deposit = number(input.deposit);
    const jeonseRatio = market.predictedSale ? (deposit / market.predictedSale) * 100 : 0;
    const rentGapRate = market.predictedRent ? (deposit / market.predictedRent) * 100 : 0;
    const signals = [];
    let score = 0;

    function signal(points, level, title, detail, key, action) {
      score += points;
      signals.push({ points, level, title, detail, key, action });
    }

    if (jeonseRatio >= 90) signal(35, "위험", "전세가율 90% 이상", `입력 보증금이 추정 매매가의 ${jeonseRatio.toFixed(1)}%입니다.`, "jeonse_ratio", "HUG 보증 가능성과 보증금 조정을 확인하세요.");
    else if (jeonseRatio >= 80) signal(22, "주의", "전세가율 80% 이상", `입력 보증금이 추정 매매가의 ${jeonseRatio.toFixed(1)}%입니다.`, "jeonse_ratio", "주변 매매 실거래가를 더 확인하세요.");
    if (rentGapRate >= 115) signal(18, "주의", "시세보다 높은 보증금", `예측 적정 전세가보다 ${(rentGapRate - 100).toFixed(1)}% 높습니다.`, "rent_gap", "최근 전세 거래 3건 이상과 비교하세요.");
    if (market.comparableCount < 3) signal(12, "확인", "유사 거래 부족", "비슷한 거래가 부족해 시세 신뢰도가 낮습니다.", "rent_gap", "조회 기간과 인접 법정동을 넓혀 확인하세요.");
    if (docs.mortgageFlag) signal(20, "주의", "근저당권 확인", `채권최고액 ${money(docs.mortgageAmount)}이 입력 또는 추출되었습니다.`, "mortgage", "말소 조건을 계약서 특약에 넣고 잔금 전 등기부등본을 재확인하세요.");
    if (docs.mortgageAmount && market.predictedSale && (docs.mortgageAmount + deposit) / market.predictedSale >= 0.85) signal(15, "위험", "선순위 금액과 보증금 합계가 큼", "근저당 채권최고액과 보증금 합계가 추정 매매가의 85% 이상입니다.", "mortgage", "보증보험 가능성과 보증금 반환 순위를 확인하세요.");
    if (docs.seizureFlag) signal(38, "위험", "압류 확인", "문서 또는 입력값에서 압류 신호가 확인되었습니다.", "seizure", "말소 전까지 계약 진행을 보류하세요.");
    if (docs.provisionalSeizureFlag) signal(34, "위험", "가압류 확인", "문서 또는 입력값에서 가압류 신호가 확인되었습니다.", "seizure", "원인과 말소 가능성을 확인하세요.");
    if (docs.trustFlag) signal(45, "고위험", "신탁등기 확인", "임대 권한 확인이 우선인 신탁등기 신호가 있습니다.", "trust", "수탁자 동의서와 신탁원부를 확인하세요.");
    if (docs.violationFlag) signal(18, "주의", "위반건축물 확인", "건축물대장 또는 문서에서 위반건축물 신호가 있습니다.", "violation", "건축물대장 원본과 보증보험 가능 여부를 확인하세요.");
    if (input.housingType === "다가구") signal(12, "확인", "다가구 선순위 보증금 확인", "다가구는 다른 임차인의 보증금 총액이 중요합니다.", "multifamily", "선순위 임차보증금과 확정일자 현황을 요청하세요.");
    if (!docs.registryChecked) signal(10, "확인", "등기부등본 미확인", "근저당, 압류, 신탁 여부를 원본으로 확인하지 못했습니다.", "unchecked", "계약 전과 잔금 전 등기부등본을 다시 발급하세요.");
    if (!docs.buildingChecked) signal(8, "확인", "건축물대장 미확인", "주택 용도와 위반건축물 여부를 원본으로 확인하지 못했습니다.", "unchecked", "정부24 또는 세움터에서 건축물대장을 확인하세요.");

    const documentBlind = !docs.registryChecked && !docs.buildingChecked && parsed.extractedChars < 10;
    const confidenceScore = Math.min(96, 22 + (market.marketConfidence === "높음" ? 34 : market.marketConfidence === "보통" ? 24 : market.marketConfidence === "낮음" ? 14 : 4) + (docs.registryChecked ? 18 : 0) + (docs.buildingChecked ? 12 : 0) + (parsed.extractedChars > 10 ? 8 : 0));
    let grade = "안전";
    let tone = "stable";
    if (!input.address || !input.legalDongCode || !input.housingType || !deposit || !number(input.area) || documentBlind && market.comparableCount < 2) {
      grade = "검토불가";
      tone = "blocked";
    } else if (docs.trustFlag || score >= 85) {
      grade = "고위험";
      tone = "critical";
    } else if (score >= 60) {
      grade = "위험";
      tone = "danger";
    } else if (score >= 28) {
      grade = "주의";
      tone = "warning";
    }

    const evidenceKeys = new Set(signals.map((item) => item.key));
    const evidence = knowledge.filter((item) => evidenceKeys.has(item.key));
    const actions = Array.from(new Set(signals.map((item) => item.action).concat([
      "계약 전, 잔금 전, 입주 직전에 등기부등본과 건축물대장을 다시 확인하세요.",
      "특약에는 근저당 말소, 권리 변동 금지, 보증보험 협조 조건을 구체적으로 적으세요."
    ]))).slice(0, 6);

    const chain = [
      { id: "load", name: "Load", label: "사용자 입력·PDF 문서 로드", status: "done", detail: parsed.extractedChars ? `문서 텍스트 ${parsed.extractedChars}자 반영` : "사용자 직접입력 반영" },
      { id: "analyze_market", name: "Analyze", label: "공공데이터 시세 비교", status: "done", detail: `유사 거래 ${market.comparableCount}건, 신뢰도 ${market.marketConfidence}` },
      { id: "analyze_docs", name: "Analyze", label: "권리관계 위험 신호 추출", status: "done", detail: signals.length ? `${signals.length}개 신호` : "중대 신호 낮음" },
      { id: "score", name: "Graph", label: "위험 기준 적용·등급 산출", status: "done", detail: `${grade} / ${Math.round(score)}점` },
      { id: "ground", name: "Ground", label: "공공문서 근거 연결", status: "done", detail: `${evidence.length}개 근거 문서 연결` },
      { id: "report", name: "Generate", label: "최종 리포트 생성", status: "done", detail: actions[0] || "추가 확인 안내" }
    ];

    return {
      input,
      parsed,
      building,
      market,
      docs,
      features: {
        predicted_rent_price: market.predictedRent,
        predicted_sale_price: market.predictedSale,
        jeonse_ratio: jeonseRatio,
        rent_gap_rate: rentGapRate,
        similar_transaction_count: market.comparableCount,
        market_confidence: market.marketConfidence,
        document_confidence: confidenceScore
      },
      score: Math.min(100, score),
      confidenceScore,
      confidenceLabel: confidenceScore >= 76 ? "높음" : confidenceScore >= 55 ? "보통" : "낮음",
      grade,
      tone,
      signals: signals.sort((a, b) => b.points - a.points),
      evidence,
      actions,
      chain,
      summary: grade === "검토불가"
        ? "현재 정보만으로는 판단 범위가 제한됩니다. 문서와 시세 데이터를 추가로 확인해야 합니다."
        : signals[0]
          ? `${signals[0].title} 때문에 보증금 반환 위험이 높아질 수 있어 추가 확인이 필요합니다.`
          : "확인된 범위에서는 중대한 위험 신호가 낮게 나타났습니다."
    };
  }

  return {
    marketSeed,
    buildingSeed,
    knowledge,
    examples,
    parseDocumentText,
    predictMarket,
    runLagChain,
    money
  };
});
