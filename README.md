# stadium-2026-photo-edit

포항공대신문 480호 4면 [대학] 「스타디움 & IT 아레나」 사진 데스크.
2026 STadium·IST-TECH IT ARENA(11/14) 사진 1,186장 → 게재 후보 50장 선별 → 장면별 룩으로 RAW 현상.

- 취재 맥락: [`docs/context.md`](docs/context.md)
- 크리에이티브 브리프·룩북·지면 제안: [`docs/creative_brief.md`](docs/creative_brief.md)
- 선정 목록: [`selection/final50.csv`](selection/final50.csv), 보정본 밀착: `selection/final50_graded_contact.jpg`
- 컷별 룩·크롭 지시: [`looks/edits.tsv`](looks/edits.tsv)

## 파이프라인

| 단계 | 스크립트 | 하는 일 | 모델 토큰 |
|---|---|---|---|
| 1 | `pipeline/fetch.sh` | Drive 공개 폴더에서 2000px 썸네일 + EXIF 헤더(앞 96KB)만 받기 | 0 |
| 2 | `pipeline/tech.py` | 구역별 선명도, 클리핑, ISO·셔터, pHash | 0 |
| 3 | `pipeline/clipscore.py` | CLIP ViT-L/14: 보도사진다움 점수, 장면 분류, 임베딩 | 0 |
| 4 | `pipeline/rank.py` | 점수 결합 → 연사 묶음 정리 → 장면 쿼터 → 밀착 시트 | 시트만 검토 |
| 5 | `pipeline/verify.py` | 후보 원본으로 50% 배율 초점 검증 크롭 | 시트만 검토 |
| 6 | `pipeline/develop.py` | NEF → 장면별 룩 현상(WB·노출·톤·HSL·NR·국소대비·신문 출력 보정) | 0 |

```bash
python3 -I pipeline/develop.py raw/ out/ looks/edits.tsv            # 전체
python3 -I pipeline/develop.py raw/ out/ looks/edits.tsv PT1_0556   # 일부만
```

필요 패키지: `rawpy opencv-python-headless<5 pillow numpy exifread imagehash open_clip_torch torch`

## 산출물 관리
NEF 원본(`raw/`)과 보정 JPG(`out/`)는 용량이 커서 git에 넣지 않는다(.gitignore).
보정본은 GitHub Release 첨부 파일로 배포하고, 원본은 Drive 폴더 `2026Stadium사진`을 기준으로 한다(NEF ID는 `selection/nef_ids.tsv`).

## 보정 원칙
전역 톤·색, 크롭, 수평만 쓴다. 합성하거나 객체를 지우지 않는다. 자세한 기준은 브리프 2절에 있다.
