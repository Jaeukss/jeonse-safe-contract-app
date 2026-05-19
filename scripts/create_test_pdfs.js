const fs = require("node:fs");
const path = require("node:path");

const outDir = path.join(__dirname, "..", "samples");
fs.mkdirSync(outDir, { recursive: true });

const docs = [
  {
    file: "01_registry_mortgage.pdf",
    title: "등기부등본 위험 신호 예시",
    lines: [
      "등기부등본 을구",
      "근저당권 설정 채권최고액 2억 4천만원",
      "가압류 있음",
      "신탁등기 없음",
      "위반건축물 표시 없음"
    ]
  },
  {
    file: "02_trust_seizure_violation.pdf",
    title: "신탁 압류 위반건축물 예시",
    lines: [
      "등기부등본 갑구 및 건축물대장",
      "신탁등기 있음",
      "압류 있음",
      "채권최고액 7천만원",
      "위반건축물 표시 있음"
    ]
  },
  {
    file: "03_clear_documents.pdf",
    title: "확인 양호 문서 예시",
    lines: [
      "등기부등본 및 건축물대장 확인",
      "근저당권 없음",
      "압류 없음",
      "가압류 없음",
      "신탁등기 없음",
      "위반건축물 표시 없음"
    ]
  }
];

function escapePdfText(text) {
  return text.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

function makePdf({ title, lines }) {
  const textOps = [
    "BT",
    "/F1 12 Tf",
    "50 750 Td",
    `(${escapePdfText(title)}) Tj`,
    ...lines.flatMap((line) => ["0 -24 Td", `(${escapePdfText(line)}) Tj`]),
    "ET"
  ].join("\n");
  const stream = Buffer.from(textOps, "utf8");

  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    `<< /Length ${stream.length} >>\nstream\n${textOps}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
  ];

  let body = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(body, "utf8"));
    body += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });

  const xrefOffset = Buffer.byteLength(body, "utf8");
  body += `xref\n0 ${objects.length + 1}\n`;
  body += "0000000000 65535 f \n";
  for (let i = 1; i < offsets.length; i += 1) {
    body += `${String(offsets[i]).padStart(10, "0")} 00000 n \n`;
  }
  body += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;
  return body;
}

docs.forEach((doc) => {
  fs.writeFileSync(path.join(outDir, doc.file), makePdf(doc), "utf8");
  console.log(`created samples/${doc.file}`);
});
