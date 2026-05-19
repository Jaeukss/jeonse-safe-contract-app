const assert = require("node:assert/strict");
const engine = require("../src/risk-engine.js");

const expected = {
  highRatio: "고위험",
  trust: "고위험",
  safe: "안전",
  unknown: "검토불가"
};

for (const [key, grade] of Object.entries(expected)) {
  const report = engine.runLagChain(engine.examples[key].input);
  assert.equal(report.grade, grade, key);
  assert.ok(report.chain.length >= 5, "LAG chain should be present");
  assert.ok(Number.isFinite(report.score), "score should be finite");
  console.log(`${key}: ${report.grade} / ${Math.round(report.score)}점 / ${report.confidenceLabel}`);
}

const parsed = engine.parseDocumentText("등기부등본 을구 근저당권 채권최고액 2억 4천만원, 가압류 있음");
assert.equal(parsed.mortgageFlag, true);
assert.equal(parsed.provisionalSeizureFlag, true);
assert.equal(parsed.mortgageAmount, 240000000);
console.log("document parser: ok");
