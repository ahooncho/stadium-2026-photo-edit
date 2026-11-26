# 기사 IDE (Google Docs 중심 공동 작업 환경)

480호 4면 [대학] 스타디움 & IT 아레나 기사용. Google Docs 문서가 원고의 원본이고, 문서에 붙인 Apps Script가 분량·린트·팩트 상태·제출 빌드를 맡는다.

- Drive 폴더: https://drive.google.com/drive/folders/1qv454-d2PxLLHRnptGNOvIKT3INlukSX
- 기사 문서: https://docs.google.com/document/d/1Y6M-EDTk-zytRGdeXmRlXg2HXOfkphlYMDaSA_0vW0o/edit (제목·부제·본문·바이라인·캡션·확인할 것만. 점검 기능은 전부 사이드바)
- `Code.gs`, `Sidebar.html`: 문서의 확장 프로그램 → Apps Script에 붙여 넣는 코드(Drive 04_레퍼런스·도구에도 사본)
- `article_template.html`, `facts.html`, `usage.html`: 기사 문서·취재 자료·사용법 원본(HTML → Google Docs 변환)
- `test_harness.js`: Apps Script 전역을 흉내 낸 시험 도구. `node test_harness.js`

기준값: 분량 1,720~1,850자(공백 포함), 줄 칸당 20.4자(476~479호 [대학]면 실측, `docs/layout_480_p4.md`), 5단 31·31·10·10·8줄. 조판 규칙은 `docs/layout_spec.md`.
