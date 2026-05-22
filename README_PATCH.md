# OCR 권리관계 자동반영 + 노이즈 OCR 보강 교체 파일

## 적용 위치

저장소 루트에서 ZIP을 풀어 같은 경로에 덮어쓰세요.

```powershell
python scripts/run_mvp_smoke.py
pytest tests
```

## 포함 변경

- 기본정보뿐 아니라 OCR 결과 확인 및 보완입력 폼에도 추출값 자동 주입
- 근저당권, 채권최고액, 압류, 가압류, 신탁등기, 전세권, 임차권등기, 소유권 변동, 가등기/경매/가처분 등 권리관계 필드 추가
- 문서 분류가 `unknown`이어도 등기부 키워드가 보이면 registry parser fallback 실행
- 신규 권리관계 필드 병합, 충돌 감지, 위험점수 반영
- OpenRouter JSON schema에 신규 권리관계 필드 추가
- 노이즈 이미지/PDF OCR 보강:
  - EXIF 방향 보정
  - 저해상도 이미지 확대
  - autocontrast
  - contrast/sharpen 변형
  - median filter
  - 다중 threshold
  - Tesseract PSM 4/6/11/12 다중 실행 후 품질 점수 기반 선택
  - 스캔 PDF 렌더링 3x 우선, 실패 시 2x fallback

## PR 생성 관련

현재 ChatGPT GitHub 연결 앱이 브랜치 생성 권한에서 403을 반환했습니다. 로컬에서 직접 PR을 만들려면 아래 명령을 쓰면 됩니다.

```bash
git checkout -b fix/ocr-rights-prefill
unzip jeonse_ocr_rights_prefill_noise_ocr_replacement_files.zip -d /tmp/jeonse_patch
rsync -av /tmp/jeonse_patch/jeonse_patch_files/ ./ --exclude='__pycache__'
python scripts/run_mvp_smoke.py
pytest tests
git add app src tests README_PATCH.md
git commit -m "Improve OCR rights prefill and noisy scan extraction"
git push origin fix/ocr-rights-prefill
```
