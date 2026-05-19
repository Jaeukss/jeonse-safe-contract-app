"""Collect public real-estate data for the Jeonse Guard MVP.

Usage:
  set DATA_GO_KR_SERVICE_KEY=your-decoded-or-encoded-key
  python scripts/collect_public_data.py --lawd-cd 11500 --months 202511 202512

The script writes raw XML under data/raw and normalized CSV under data/processed.
Most official APIs require a data.go.kr service key, so this collector is not
expected to run without that key.
"""

from __future__ import annotations

import argparse
import csv
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

RTMS_SERVICES = {
    "apt_rent": ("아파트", "전세", "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"),
    "apt_trade": ("아파트", "매매", "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"),
    "rh_rent": ("연립다세대", "전세", "https://apis.data.go.kr/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent"),
    "rh_trade": ("연립다세대", "매매", "https://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade"),
    "offi_rent": ("오피스텔", "전세", "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"),
    "offi_trade": ("오피스텔", "매매", "https://apis.data.go.kr/1613000/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade"),
    "sh_rent": ("다가구", "전세", "https://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent"),
    "sh_trade": ("다가구", "매매", "https://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade"),
}


def text(item: ET.Element, *names: str) -> str:
    for name in names:
        found = item.find(name)
        if found is not None and found.text:
            return found.text.strip()
    return ""


def money_to_int(value: str) -> int:
    clean = value.replace(",", "").replace(" ", "")
    return int(float(clean) * 10000) if clean else 0


def fetch(url: str, params: dict[str, str]) -> bytes:
    query = urllib.parse.urlencode(params, safe="%")
    with urllib.request.urlopen(f"{url}?{query}", timeout=30) as response:
        return response.read()


def collect_rtms(service_key: str, lawd_cd: str, months: list[str]) -> list[dict[str, object]]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for service_id, (housing_type, trade_type, url) in RTMS_SERVICES.items():
        for month in months:
            payload = fetch(url, {
                "serviceKey": service_key,
                "LAWD_CD": lawd_cd,
                "DEAL_YMD": month,
                "pageNo": "1",
                "numOfRows": "1000",
            })
            (RAW_DIR / f"{service_id}_{lawd_cd}_{month}.xml").write_bytes(payload)
            root = ET.fromstring(payload)
            for item in root.findall(".//item"):
                price_text = text(item, "거래금액", "보증금액", "보증금")
                area_text = text(item, "전용면적", "계약면적", "연면적")
                if not price_text or not area_text:
                    continue
                rows.append({
                    "region": text(item, "법정동"),
                    "legal_dong_code": lawd_cd,
                    "housing_type": housing_type,
                    "trade_type": trade_type,
                    "trade_month": month,
                    "price_won": money_to_int(price_text),
                    "monthly_rent_won": money_to_int(text(item, "월세금액", "월세")),
                    "exclusive_area_m2": float(area_text),
                    "floor": text(item, "층") or "0",
                    "built_year": text(item, "건축년도") or "",
                })
            time.sleep(0.15)
    return rows


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["region", "legal_dong_code", "housing_type", "trade_type", "trade_month", "price_won", "monthly_rent_won", "exclusive_area_m2", "floor", "built_year"]
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lawd-cd", required=True, help="법정동코드 앞 5자리, 예: 11500")
    parser.add_argument("--months", nargs="+", required=True, help="계약년월 YYYYMM 목록")
    args = parser.parse_args()
    service_key = os.environ.get("DATA_GO_KR_SERVICE_KEY")
    if not service_key:
        raise SystemExit("DATA_GO_KR_SERVICE_KEY 환경변수가 필요합니다.")
    rows = collect_rtms(service_key, args.lawd_cd, args.months)
    out = PROCESSED_DIR / f"rtms_{args.lawd_cd}_{args.months[0]}_{args.months[-1]}.csv"
    write_csv(rows, out)
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
