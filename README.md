# stadium-2026-photo-edit

포항공대신문 480호 4면 [대학] 「스타디움 & IT 아레나」 사진 데스크.
2026 STadium·IST-TECH IT ARENA(11/14) 사진 1,186장 → 게재 후보 50장 선별 → 장면별 룩으로 RAW 현상.

- **기술 파이프라인 공개 문서: [`docs/disclosure_pipeline.md`](docs/disclosure_pipeline.md)** ← 지면 고지문(안) 포함
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

필요 패키지: `pip install -r requirements.txt`

## 폴더 지도
| 경로 | 내용 |
|---|---|
| `out/` | **최종 보정본 50장, v3**(JPEG q95, sRGB, 300dpi, 인쇄용 CMYK 변환 전) |
| `work/01_inventory/` | Drive 파일 목록, 최종 50장 NEF ID, 전체 EXIF(1,186장) |
| `work/02_thumbs/` | 1차 평가에 쓴 2000px 썸네일 1,186장 |
| `work/03_scores/` | 기술 지표, CLIP 점수·장면, 임베딩, 후보·검증 결과, 69장·50장 목록 |
| `work/04_review_sheets/` | AI가 검토한 밀착 시트 13장(1차 147컷, 추가 60컷, 자동탈락 재검토 47컷) |
| `work/05_focus_check/` | 69장 원본 50% 배율 초점 검증 시트 |
| `work/06_crop_grid/` | 크롭 결정용 10% 격자 시트 |
| `work/07_look_dev/` | 룩 개발 전후 비교, 노이즈 처리 전후, 컷별 현상 파라미터 |
| `work/08_logs/` | 실행 로그 |

NEF 원본은 저장소에 넣지 않는다. Drive 폴더 「2026Stadium사진」이 기준이다(ID: `work/01_inventory/final50_nef_ids.tsv`).

## 보정 원칙
객체를 지우거나 합성하지 않는다. 크롭으로 사람을 자르지 않는다. 최종 룩은 v3(전역 톤·색 보정)이며, v3.1·v3.2·v4 시도는 폐기했다(브리프 2절, 공개 문서 6.1절). 현재 `out/`은 v3다.
