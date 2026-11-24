# 사진 편집 기술 파이프라인 공개

포항공대신문 480호 4면 [대학] 「스타디움 & IT 아레나」 게재 사진
작성일 2026-11-24 · 대상 사진 2026-11-14 촬영분(Nikon D5500, JPG+NEF 1,186쌍)

이 문서는 사진 선별과 보정에 쓴 도구, 알고리즘, 수치, 판단 주체를 빠짐없이 기록한다. 이 문서에 적힌 모든 단계의 코드와 중간 산출물은 이 저장소에 함께 있다.

---

## 0. 지면 고지문(안)

> 이 기사의 사진은 본지 기자가 촬영했다. 촬영본 1,186장의 1차 선별과 보정은 AI 에이전트(Anthropic Claude)가 기자의 지시를 받아 수행했다. 사용한 도구는 공개 소스 소프트웨어와 이미지 분류 모델(CLIP)이고, 보정 범위는 밝기·색·대비·노이즈 제거·자르기다. 생성형 AI로 화면을 만들거나 지우거나 합성하지 않았다. 최종 게재 사진은 편집국이 확인했다. 전체 과정은 github.com/ahooncho/stadium-2026-photo-edit 에 공개한다.

공개 범위(저장소 공개 여부)와 '편집국 확인' 문구는 편집국이 실제 확인을 마친 뒤 확정한다.

---

## 1. 참여 주체와 역할

| 주체 | 역할 |
|---|---|
| 촬영 기자 | 현장 촬영(Nikon D5500, 파일명 접두 PT1·PT2). 기자명: ＿＿＿＿ |
| 담당 기자(지시자) | 작업 지시, 선별 기준 제시("인쇄 가능한 최상급, 보정 가능한 결점은 감점하지 않음"), 크리에이티브 방향 지시("예쁨·분위기 중시"), 산출물 확인 |
| AI 에이전트: Anthropic Claude (Claude Code, 클라우드 세션) | 맥락 수집, 파이프라인 설계·코드 작성·실행, 밀착 시트를 보고 후보 선별, 크롭·룩 결정, 보정 실행, 이 문서 작성 |
| 편집국 | 최종 게재 사진 확인(**미완료: 게재 전 필수**) |

**AI가 내린 편집 판단(사람의 확인 필요):**
- 1,186장 → 69장 → 50장으로 좁힌 시각적 선별
- 장면 설명 문구(`selection/final50.csv`의 '장면' 열)
- 컷별 크롭과 룩 배정(`looks/edits.tsv`)
- 지면 배치 제안(`docs/creative_brief.md` 4절)

---

## 2. 사용한 외부 서비스와 데이터 흐름

| 서비스 | 용도 | 데이터 방향 |
|---|---|---|
| Google Calendar(커넥터, 읽기) | 「포항공대신문 취재」 캘린더 11/14 일정에서 행사·경기 결과 확인 | 읽기만 |
| Google Drive(커넥터, 읽기) | 사진 폴더 목록, 「2026년 11월 8일 회의록」(지면 배정) 확인 | 읽기만 |
| Google Drive 공개 링크(HTTP) | 썸네일·EXIF 헤더·원본 다운로드. 폴더는 작업 전부터 '링크가 있는 모든 사용자(뷰어)'로 공유돼 있었고, 설정은 바꾸지 않음 | 다운로드만 |
| Notion(메모리 검색) | 이전 기록 확인(결과 없음) | 읽기만 |
| 웹 검색 | 보정 레퍼런스 조사(9절) | 질의만, 사진은 전송하지 않음 |
| Hugging Face / PyPI | CLIP 가중치와 파이썬 패키지 다운로드 | 다운로드만, 사진은 전송하지 않음 |
| GitHub 저장소 | 코드·중간 산출물·결과물 보관 | 업로드 |

사진 처리는 모두 Anthropic의 격리된 클라우드 컨테이너(Linux, CPU 4코어, GPU 없음) 안에서 했다. Adobe 등 다른 이미지 처리 서비스에는 사진을 보내지 않았다.

---

## 3. 소프트웨어 버전

Python 3.13.18 · rawpy 0.28.0 (LibRaw 0.22.2) · OpenCV 4.14.0 (opencv-python-headless) · NumPy 2.5.3 · Pillow 13.0.0 · PyTorch 2.15.0 (CPU) · open_clip 4.2.2 · ExifRead 3.5.1 · ImageHash 4.3.2
고정 버전은 `requirements.txt`에 있다.

**Adobe Photoshop은 쓰지 않았다.** 처음에는 기자의 PC에 설치된 Photoshop(Camera Raw)으로 보정할 계획이었다. 하지만 클라우드 세션에서 PC 폴더에 원격으로 연결하는 데 실패했고, 기자의 결정에 따라 오픈소스 RAW 현상(LibRaw)으로 전환했다.

---

## 4. 선별 파이프라인

### 4.1 맥락 수집
- 캘린더 「포항공대신문 취재」의 11/14 일정 17건과 회의록을 읽어 `docs/context.md`로 정리했다.
- 첫 검색에서는 기본 캘린더만 조회해 일정을 놓쳤다. 이후 기자의 지적으로 취재 캘린더를 찾았다.

### 4.2 인벤토리 (`pipeline/fetch.sh`, 결과: `work/01_inventory/`)
- Drive 폴더에서 JPG 1,186장의 ID·크기·시각을 확보했다(`drive_jpg_list.tsv`).
- 각 JPG에 대해 두 가지를 받았다.
  1. Google Drive 썸네일 엔드포인트의 긴 변 2000px 이미지. Google이 다시 압축한 사본이며, 원본에서 줄인 것이다(`work/02_thumbs/`).
  2. 원본 파일의 앞 96KB(EXIF 헤더). 파싱 결과는 `exif_all.json`에 있다.
- 원본 13GB 전체는 내려받지 않았다.
- **카메라 시계 주의:** EXIF 촬영 시각이 15:53~익일 04:57로, 실제 행사 시간(09:00–21:00)과 맞지 않는다. 카메라 시계가 틀어져 있었던 것으로 보이며, 캡션 시각에 쓰면 안 된다.

### 4.3 기술 지표 (`pipeline/tech.py`, 결과: `work/03_scores/tech.json`)
썸네일(2000px)에서 계산했다. 사람의 개입은 없다.
- **선명도:** 그레이스케일 라플라시안을 8×8 타일로 나눠 분산을 구하고, 그 95 백분위값(`sharp_p95`)을 쓴다. 주 피사체가 화면에서 가장 선명하다는 가정이다.
- **엣지 강도:** 소벨 크기의 99 백분위값(`tenen99`). 기록용이며 점수에는 쓰지 않았다.
- **클리핑:** 밝기 250 이상 비율, 5 이하 비율.
- **pHash:** 기록용.
- **EXIF:** ISO, 셔터, 조리개, 초점거리, 촬영 시각.

### 4.4 이미지 분류 모델 (`pipeline/clipscore.py`, 결과: `clip.json`, `emb.npy`)
- **모델:** OpenAI CLIP ViT-L/14(open_clip `pretrained="openai"`). 생성 모델이 아니라 이미지와 문장의 유사도를 재는 분류 모델이다.
- **보도사진다움 점수(`clipq`):** 아래 긍정 문장 3개와 부정 문장 4개에 대한 소프트맥스 확률 중, 긍정 쪽 확률의 합이다.
  - 긍정: "a professional award-winning sports photojournalism photo, sharp focus, decisive moment" / "a compelling newspaper photograph with clear subject and strong composition" / "a sharp, well-composed event photo with expressive faces and emotion"
  - 부정: "a blurry out of focus snapshot" / "a boring amateur photo with no clear subject" / "a motion-blurred, badly framed photo" / "a photo of people's backs with nothing happening"
- **장면 분류:** 15개 장면 문장(축구, 농구, 배드민턴, 야구, e스포츠, 밴드, 댄스, 힙합, 응원단, 시상식, RC카, 발표, 코딩, 관중, 부스)에 대한 제로샷 분류. 오분류가 있을 수 있어 장면별 장수 상한을 정하는 데에만 썼다.
- **편향 주의:** 문장 선택 자체가 '어떤 사진이 좋은가'에 대한 가정이다. 영어 문장 기반 모델이고, 학습 데이터의 미감 편향이 있을 수 있다.

### 4.5 점수 결합과 후보 추리기 (`pipeline/rank.py`, 결과: `cand.json`, `work/04_review_sheets/`)
- **결합 점수** = 0.5·z(log 선명도) + 0.5·z(logit clipq) − 감점
  - 감점 1.0: 클리핑 하이라이트 8% 초과 또는 섀도 20% 초과(보정으로 되살릴 수 없는 노출)
  - 감점 0.3: ISO 6400 이상
  - 감점 0.4: 셔터가 1/(1.5×초점거리)보다 느림(흔들림 위험)
- **자동 탈락:** 선명도 z < −1.0(하위 약 16%).
- **연사 묶기:** 시간순으로 3초 이내이고 CLIP 코사인 유사도가 0.88 초과면 같은 묶음으로 보고, 묶음마다 최고점 1장만 남겼다. 그 결과 346개 묶음이 나왔고, 자동 탈락을 빼면 283개가 남았다.
- **다양성 확보:** 점수순으로 고르되 이미 고른 사진과 코사인 0.95를 넘으면 제외했다. 장면별 상한은 40장으로 두었고, 상위 147장을 밀착 시트로 만들었다(`sheet_00~07`).
  - 1차 시도는 유사도 0.93, 상한 26장으로 돌렸다. 107장만 나와서 기준을 완화했다.
- **추가 검토:** 상한에 걸려 빠진 농구·e스포츠 60장을 `extra_0~2`로 만들었다.
- **자동 탈락 재검토:** 어두운 무대 사진은 선명도 지표가 실제보다 낮게 나오는 경향이 있었다. 그래서 자동 탈락한 무대·시상·e스포츠 묶음 47장을 `rej_0~1`로 다시 봤다. 이 단계에서 PT1_0253, 0573, 0580, 0620, 0642 등이 살아났다.

### 4.6 AI 시각 검토 → 69장
Claude가 위 밀착 시트 13장(약 254컷)을 보고 보도 가치, 순간성, 구도, 장면 다양성을 기준으로 69장을 골랐다(`shortlist69.txt`).

### 4.7 원본 초점 검증 (`pipeline/verify.py`, 결과: `work/05_focus_check/`, `verify.json`)
- 69장의 원본 JPG(6016×4016)를 내려받았다.
- OpenCV Haar 얼굴 검출기로 가장 큰 얼굴을 찾았다. 얼굴이 없으면 라플라시안 에너지가 가장 큰 지점을 썼다.
- 그 주변 600×600을 잘라 50%로 축소해 검토했다. 신문 지면 크기에 맞춘 배율이다.
- **한계:** 12장(PT1_0100, 0101, 0108, 0365, 0491, 0493, 0573, 0580, 0596, 0616, 0620, 0623)은 검증 영역이 배경에 잡혀 초점을 확인하지 못했다.
- 19장을 제외해 50장을 확정했다(`final50.txt`). 제외 사유는 아래와 같다.
  - **초점·흔들림 미흡:** PT1_0514, 0541, 0594, 0672, 0083, 0695
  - **비슷한 컷 중복:** PT1_0260, 0209, 0628, 0649, 0573↔0596 비교 끝에 0573 유지, PT2_0463, 0471
  - **구도·보도 가치 약함:** PT1_0047, 0420, 0429, 0692, 0635, PT2_0345, 0370

---

## 5. 크리에이티브 방향 수립
- 기자의 지시("크리에이티브 디렉터 관점, 예쁨·분위기 중시")에 따라 웹 레퍼런스를 조사했다(9절).
- 그 결과로 콘셉트 「차가운 비, 뜨거운 사람들」과 장면별 룩 7종을 정했다(`docs/creative_brief.md`).
- 크롭은 10% 격자를 얹은 시트(`work/06_crop_grid/`)를 보고 컷별로 정했다(`looks/edits.tsv`). 50컷 중 31컷에 크롭을 적용했다.

---

## 6. 보정(현상) 파이프라인 (`pipeline/develop.py`)

입력은 NEF 원본 50장이다. 모든 처리는 **이미지 전체에 같은 수식을 적용하는 전역 연산**이다. 위치를 지정한 국소 보정(브러시·마스크로 특정 사물만 손대기)은 없다. 예외는 노이즈 제거와 샤프닝인데, 둘 다 화소 값에 따라 자동으로 세기가 달라질 뿐 위치를 지정하지 않는다.

| 순서 | 처리 | 방법·수치 |
|---|---|---|
| 1 | RAW 현상 | LibRaw(rawpy) 기본 디모자이크(AHD). 카메라 화이트밸런스 사용, 하이라이트 모드 Blend, 출력은 선형 16비트 sRGB, 자동 밝기 끔 |
| 2 | 크롭 | `looks/edits.tsv`의 정규화 좌표대로 자름. 수평 보정은 하지 않음 |
| 3 | 부분 화이트밸런스 | 밝기 20–90 백분위 화소로 회색 세계(gray-world) 이득을 계산한 뒤 `이득^wb`로 일부만 적용(룩별 0.0–0.8). 이어서 룩별 RGB 틴트 배율을 곱함 |
| 4 | 노출 | 화면 중앙 2/3 영역의 중앙값이 톤맵 후 표시값으로 룩별 목표(`mid` 0.28–0.48)가 되도록 노출(EV)을 이분 탐색. 범위 −3~+5EV, 실제 적용값은 컷별로 `develop_params.csv`에 기록 |
| 5 | 톤 매핑 | ACES 근사 곡선(Narkowicz), sRGB 감마, smoothstep S커브 콘트라스트(룩별 0.25–0.45) |
| 6 | 노이즈 제거(ISO 800 이상) | 색 노이즈: YCrCb 색차 채널에 가우시안 블러(σ 1.5–5.0). 휘도 노이즈: OpenCV Non-Local Means(h 3–11), 원본과의 잔차로 적용. ISO 1600/3200/6400 경계로 4단계 |
| 7 | 색 | HSV 색상 대역별 채도·색상 조정(대역마다 가우시안 가중, 무채색 영역은 영향 감소). 룩별 전역 채도 0.92–1.00. 채도 0.8을 넘으면 0.4배로 압축(신문 색역 대비) |
| 8 | 국소 대비 | 휘도 − 큰 반경 블러(σ = 긴 변/150)를 중간톤 가중으로 더함(룩별 0.20–0.30) |
| 9 | 신문 출력 보정 | 감마 0.92(망점 확대 선보상), 블랙 리프트 0–0.035, 주변부 비네팅 5–20%(가장자리를 어둡게 하는 전통적 번 처리) |
| 10 | 출력 샤프닝 | 휘도 언샤프 마스크(σ 1.1). 세기는 0.65이고 ISO 3200 이상은 ×0.7, 6400 이상은 ×0.45. 평탄부(노이즈)는 제외하고 엣지에만 적용 |
| 11 | 저장 | JPEG 품질 95, 4:4:4, sRGB ICC 내장, 300dpi 메타데이터 |

룩별 수치는 `develop.py`의 `LOOKS`에, 컷별 적용 기록(ISO, 실제 EV, 출력 크기 등)은 `work/07_look_dev/develop_params.csv`에 있다.

### 6.1 반복 이력
- **v1:** 노출을 선형 목표값으로 맞추고 상한을 +2.2EV로 고정했다. 6컷 모두 상한에 걸렸고, 결과가 뿌옇게 떠서 시상식은 보라색, 무대·LoL은 과하게 밝았다. 이 결과물은 남아 있지 않고 문장으로만 기록한다.
- **v2:** 노출을 표시값 기준 이분 탐색으로 바꾸고 S커브를 추가했다. 시상식은 화이트밸런스 중화를 약하게(0.25) 하고 따뜻한 틴트를 줬다(`before_after_v2.jpg`, 왼쪽은 카메라 JPG). 이후 시상식 틴트를 (1.04, 1.00, 0.94)에서 (1.06, 1.00, 0.92)로 더 따뜻하게 했다.
- **v3:** 50% 확대에서 ISO 7200–11400 컷의 노이즈가 보였다(`detail_50pct_v2_beforeNR.jpg`). 그래서 노이즈 제거 단계를 4단계로 늘리고 엣지 마스크 샤프닝을 도입했다(`detail_50pct_v3_afterNR.jpg`). 최종본은 v3로 50장 전체를 다시 현상한 결과다.

---

## 7. 하지 않은 것
- 생성형 AI로 화소를 만들거나 채우거나 확장하지 않았다.
- 사람이나 사물을 지우거나 옮기거나 합성하지 않았다.
- 특정 인물의 얼굴이나 피부만 골라 보정하지 않았다. 무대 피부 복원은 색상 대역 전체에 대한 전역 조정이다.
- 수평 보정을 하지 않았다.
- CMYK 변환과 인쇄 프로파일 적용은 아직 하지 않았다. 인쇄소 사양을 받은 뒤 진행한다.

---

## 8. 알려진 한계와 게재 전 확인 사항
1. **편집국 최종 확인이 필요하다.** 선별, 크롭, 장면 설명은 모두 AI의 판단이다.
2. **장면 설명과 등번호·학교 표기는 확인되지 않았다.** 예를 들어 '63번', 'KAIST전'은 AI가 사진을 보고 쓴 것이라 캡션 전에 사실 확인이 필요하다.
3. **카메라 EXIF 시각이 실제와 다르다.**
4. **초점 확인 미완료 12장**은 4.7절에 정리했다.
5. **고감도 컷의 잔노이즈:** LoL 4컷 일부와 RC카 컷에 미세한 휘도 노이즈가 남아 있다.
6. **썸네일 기반 1차 평가:** 1차 평가는 Google이 다시 압축한 썸네일로 했다. 원본보다 선명도가 낮게 측정됐을 수 있다.
7. **촬영되지 않은 종목:** 배드민턴·야구·밴드 공연은 폴더에 사진이 거의 없어 선정에 포함되지 않았다.

---

## 9. 레퍼런스(보정 방향 근거)
- World Press Photo, *What counts as manipulation* — https://www.worldpressphoto.org/contest/verification-process/what-counts-as-manipulation
- Adobe Community, ISOnewspaper26v4 총잉크 240% 관련 스레드 — https://community.adobe.com/t5/indesign-discussions/isonewspaper26v4-doesn-t-give-240-ink-coverage/m-p/14087834
- Post Newspapers, Technical Information(비도공지 망점 확대 26%) — https://postnewspapers.com.au/wp-content/uploads/2024/03/Technical-Information-Newspaper.pdf
- O'Reilly, *Preparing a CMYK Image for Use in Newsprint* — https://www.oreilly.com/library/view/commercial-photoshop-retouching/059600849X/ch08s02.html
- Color Correction for Concert Lighting(Lightroom 캘리브레이션) — https://digifella.github.io/ai-wiki/inbox/2026-04-14-Watch-Color-Correction-for-Concert-Lighting-Fixing-Extreme-Color-Tints-in-Adobe
- Imagen, Skin tone correction checklist for concert photographers — https://imagen-ai.com/valuable-tips/skin-tone-correction-checklist-for-concert-photographers/
- PetaPixel, White balance for streetlights — https://petapixel.com/2016/12/16/set-white-balance-common-types-streetlights/
- Amateur Photographer, Rugby in the rain — https://amateurphotographer.com/technique/photo_appraisals/photo-appraisal-rugby-in-the-rain/
- Skylum, Football photography tips — https://blog.skylum.com/football-photography-tips/

---

## 10. 재현 방법
```bash
pip install -r requirements.txt
# 스크립트는 <작업폴더>/thumbs, <작업폴더>/exifhead 구조를 쓴다(저장소의 work/02_thumbs 는 그 결과물 보관본)
export WORK=rerun; mkdir -p $WORK/thumbs $WORK/exifhead
cut -f1,2 work/01_inventory/drive_jpg_list.tsv | xargs -P 12 -n 2 pipeline/fetch.sh
python3 -I pipeline/tech.py $WORK && python3 -I pipeline/clipscore.py $WORK && python3 -I pipeline/rank.py $WORK 160
# NEF 50장: work/01_inventory/final50_nef_ids.tsv 의 ID로 Drive에서 받아 raw/ 에 저장
python3 -I pipeline/develop.py raw out looks/edits.tsv
```
CLIP 추론은 CPU에서 결정적이지만, 라이브러리 버전이 다르면 점수가 소수점 수준에서 달라질 수 있다.

## 11. 저장소에 넣지 않은 것
- NEF 원본(50장, 약 1.2GB)과 카메라 원본 JPG 사본(69장, 약 0.8GB)은 넣지 않았다. 원본은 Drive 폴더 「2026Stadium사진」에 그대로 있고, 파일 ID는 `work/01_inventory/`에 있다.
- 원본 앞 96KB 바이트(EXIF 헤더)도 넣지 않았다. 파싱 결과는 `exif_all.json`에 있다.
