/** 기사 IDE — 포항공대신문 480호 4면 [대학] 스타디움 & IT 아레나 공동 작업 문서용 (Google Docs 바운드 스크립트)
 *  설치: 문서에서 확장 프로그램 → Apps Script → 이 파일 내용을 Code.gs에, Sidebar.html을 새 HTML 파일로 붙여 넣고 저장 → 문서 새로고침 → 메뉴 '기사 IDE'.
 *  기준값 출처: 저장소 docs/layout_480_p4.md(분량 실측), docs/layout_spec.md(조판 규칙).
 */
const CFG = {
  MIN: 1720, MAX: 1850, TARGET: 1800,            // 본문 공백 포함 글자 수(실측 기반)
  PER_SLOT: 20.4,                                // 476~479호 [대학]면 실측: 줄 칸당 공백 포함 글자 수(문단 끝·소제목 포함)
  COLS: [['1단', 31], ['2단', 31], ['3단', 10], ['4단', 10], ['5단', 8]],
  BLOCK_TARGET: { '①': 250, '②': 550, '③': 250, '④': 550, '⑤': 200 },
  TITLE_MAX: 30, DECK_MAX: 55,
  SECTION: '대학',
  SUBMIT_FOLDER: '1OI4pAW6qr2dRzVORPN0qZlOqdCtVWeOy',
  PHOTO_FOLDER: '1gWY-JiU7kstcGBuOGD-oqs9y_ICSff6P',
  FIGMA: 'https://www.figma.com/design/zH4QLvTDwvimtvfw8UqRYW',
};

function onOpen() {
  DocumentApp.getUi().createMenu('기사 IDE')
    .addItem('사이드바 열기', 'showSidebar')
    .addItem('제출 빌드', 'buildSubmissionUi')
    .addToUi();
}
function showSidebar() {
  DocumentApp.getUi().showSidebar(HtmlService.createHtmlOutputFromFile('Sidebar').setTitle('기사 IDE'));
}

/* ---------- 문서 읽기 ---------- */
function parse_() {
  const body = DocumentApp.getActiveDocument().getBody();
  const out = { blocks: [], bylines: [], title: '', deck: '', captions: [], factOpen: [], highlights: 0, bodyText: '' };
  let inBody = false, cur = null;
  const n = body.getNumChildren();
  for (let i = 0; i < n; i++) {
    const el = body.getChild(i);
    const type = el.getType();
    if (type === DocumentApp.ElementType.PARAGRAPH) {
      const p = el.asParagraph(), t = p.getText().trim(), h = p.getHeading();
      if (/^확정 제목\s*:/.test(t)) out.title = t.replace(/^확정 제목\s*:\s*/, '');
      if (/^확정 부제\s*:/.test(t)) out.deck = t.replace(/^확정 부제\s*:\s*/, '');
      if (h === DocumentApp.ParagraphHeading.HEADING2) { inBody = /^8\./.test(t); cur = null; continue; }
      if (!inBody) continue;
      if (h === DocumentApp.ParagraphHeading.HEADING3 && /^[①②③④⑤]/.test(t)) {
        cur = { key: t[0], name: t, paras: [] }; out.blocks.push(cur); continue;
      }
      if (!t || /^블록 제목/.test(t)) continue;
      if (/기자\s+\S*@\S*$/.test(t)) { out.bylines.push(t); continue; }
      if (cur) cur.paras.push(t);
      out.highlights += countHighlights_(p);
    } else if (type === DocumentApp.ElementType.TABLE) {
      readTable_(el.asTable(), out);
    }
  }
  out.bodyText = out.blocks.map(b => b.paras.join('\n')).filter(Boolean).join('\n');
  return out;
}
function readTable_(tb, out) {
  if (tb.getNumRows() < 2) return;
  const head = [];
  for (let c = 0; c < tb.getRow(0).getNumCells(); c++) head.push(tb.getRow(0).getCell(c).getText().trim());
  const capCol = head.indexOf('캡션(작성)'), maxCol = head.indexOf('한 줄 최대'), stCol = head.indexOf('상태');
  for (let r = 1; r < tb.getNumRows(); r++) {
    const row = tb.getRow(r), cell = c => (c >= 0 && c < row.getNumCells()) ? row.getCell(c).getText().trim() : '';
    if (head[0] === '사진' && capCol >= 0) {
      const m = cell(maxCol).match(/(\d+)/);
      out.captions.push({ photo: cell(0), max: m ? +m[1] : 40, text: cell(capCol) });
    }
    if (stCol >= 0 && head[0] === '항목' && /확인 필요|재확인|미확인/.test(cell(stCol))) out.factOpen.push(cell(0));
  }
}
function countHighlights_(p) {
  let k = 0;
  for (let i = 0; i < p.getNumChildren(); i++) {
    const c = p.getChild(i);
    if (c.getType() !== DocumentApp.ElementType.TEXT) continue;
    const tx = c.asText(), idx = tx.getTextAttributeIndices();
    idx.forEach(o => { const bg = tx.getBackgroundColor(o); if (bg && bg.toLowerCase() !== '#ffffff') k++; });
  }
  return k;
}

/* ---------- 측정·린트 ---------- */
function width_(s) { let w = 0; for (const ch of s) w += /[\u0000-\u007f]/.test(ch) ? 0.55 : 1; return w; }
function getStatus() {
  const d = parse_();
  const chars = d.bodyText.replace(/\n/g, '').length, noSpace = d.bodyText.replace(/\s/g, '').length;
  const blocks = d.blocks.map(b => {
    const c = b.paras.join('').length; return { name: b.name, chars: c, target: CFG.BLOCK_TARGET[b.key] || 0 };
  });
  // 5단 채움 예측: 실측 칸당 글자 수로 필요한 줄 칸을 구해 읽는 순서대로 채운다
  let slots = chars / CFG.PER_SLOT; const cols = [];
  CFG.COLS.forEach(([name, cap]) => { const used = Math.min(cap, Math.max(0, slots)); cols.push({ name, cap, used: +used.toFixed(1) }); slots -= cap; });
  const overflowLines = slots > 0 ? +slots.toFixed(1) : 0;
  const lint = [];
  const L = (lv, msg) => lint.push({ lv, msg });
  if (chars < CFG.MIN) L('warn', `본문이 ${CFG.MIN - chars}자 모자랍니다(허용 ${CFG.MIN}~${CFG.MAX}).`);
  if (chars > CFG.MAX) L('err', `본문이 ${chars - CFG.MAX}자 넘칩니다(허용 ${CFG.MIN}~${CFG.MAX}).`);
  if (!d.title) L('warn', '3절 "확정 제목:" 줄이 비어 있습니다.');
  if (d.title && width_(d.title) > CFG.TITLE_MAX) L('err', `제목이 한 줄(약 ${CFG.TITLE_MAX}자)을 넘을 수 있습니다: ${d.title.length}자.`);
  if (d.deck && width_(d.deck) > CFG.DECK_MAX) L('err', `부제가 한 줄(약 ${CFG.DECK_MAX}자)을 넘을 수 있습니다.`);
  d.bylines.forEach((b, i) => {
    if (i === 0 && !/기자\s+\S+@postech\.ac\.kr$/.test(b)) L('err', `첫 바이라인은 도메인까지 전부: "${b}"`);
    if (i > 0 && !/기자\s+\S+@$/.test(b)) L('err', `두 번째 이후 바이라인은 "아이디@"까지만: "${b}"`);
  });
  const ell = (d.bodyText.match(/…|\.\.\./g) || []).length;
  if (ell > 2) L('warn', `말줄임표가 ${ell}번 나옵니다. 남발하지 않습니다.`);
  if (/KAIST\s*23|POSTECH\s*20|중간\s*순위/.test(d.bodyText)) L('err', '19:38 중간 순위(KAIST 23·POSTECH 20)로 보이는 표현이 있습니다. 최종 결과는 POSTECH 종합우승.');
  d.bodyText.split('\n').forEach(par => {
    if (!/△/.test(par) && /(?:[가-힣A-Za-z0-9]+, ){2,}[가-힣A-Za-z0-9]+/.test(par)) L('info', `쉼표 나열 3개 이상 → △ 나열 검토: "${par.slice(0, 30)}…"`);
  });
  d.captions.forEach(c => {
    if (!c.text || c.text === '▲') { L('warn', `캡션 미작성: ${c.photo}`); return; }
    if (!c.text.startsWith('▲')) L('err', `캡션은 ▲로 시작: ${c.photo}`);
    if (width_(c.text) > c.max) L('err', `캡션 한 줄(약 ${c.max}자) 초과 가능: ${c.photo} (${c.text.length}자)`);
  });
  if (d.highlights) L('warn', `본문에 형광펜(확인 필요 표시)이 ${d.highlights}곳 남아 있습니다.`);
  blocks.forEach(b => { if (b.target && b.chars > b.target * 1.25) L('info', `${b.name}: 목표 ${b.target}자보다 ${b.chars - b.target}자 많습니다.`); });
  return { chars, noSpace, target: CFG.TARGET, min: CFG.MIN, max: CFG.MAX, blocks, cols, overflowLines,
           title: d.title, deck: d.deck, factOpen: d.factOpen, lint, figma: CFG.FIGMA,
           updated: Utilities.formatDate(new Date(), 'Asia/Seoul', 'HH:mm:ss') };
}

/* ---------- 제출 빌드 ---------- */
function buildSubmissionUi() {
  const r = buildSubmission();
  DocumentApp.getUi().alert(r.ok ? `빌드 완료\n${r.url}\n${r.notes.join('\n')}` : `빌드 중단: ${r.error}`);
}
function buildSubmission() {
  const d = parse_();
  if (!d.title) return { ok: false, error: '3절 "확정 제목:"을 먼저 채우세요.' };
  const base = `[${CFG.SECTION}] ${d.title}`.replace(/[\\/:*?"<>|]/g, ' ').trim();
  const stamp = Utilities.formatDate(new Date(), 'Asia/Seoul', 'MMdd-HHmm');
  const folder = DriveApp.getFolderById(CFG.SUBMIT_FOLDER).createFolder(`빌드 ${stamp}`);
  const notes = [];
  // 1) 원고(제목·부제·본문·바이라인)
  const doc = DocumentApp.create(base); const b = doc.getBody();
  b.appendParagraph(d.title).setHeading(DocumentApp.ParagraphHeading.TITLE);
  if (d.deck) b.appendParagraph(d.deck).setHeading(DocumentApp.ParagraphHeading.SUBTITLE);
  d.blocks.forEach(bl => bl.paras.forEach(t => b.appendParagraph(t)));
  b.appendParagraph('');
  d.bylines.forEach(t => b.appendParagraph(t).setAlignment(DocumentApp.HorizontalAlignment.RIGHT));
  if (b.getChild(0).asParagraph().getText() === '') b.removeChild(b.getChild(0));
  doc.saveAndClose();
  const f = DriveApp.getFileById(doc.getId()); f.moveTo(folder);
  // 2) 캡션 .txt(기사 파일 이름과 같게)
  const caps = d.captions.map(c => c.text).filter(t => t && t !== '▲');
  folder.createFile(`${base}.txt`, caps.join('\n'), MimeType.PLAIN_TEXT);
  if (caps.length < d.captions.length) notes.push(`캡션 ${d.captions.length - caps.length}개 미작성`);
  // 3) 사진 사본: 02_사진_확정의 1_~4_ 순서 → "[대학] 제목 n.jpg"
  const files = []; const it = DriveApp.getFolderById(CFG.PHOTO_FOLDER).getFiles();
  while (it.hasNext()) { const p = it.next(); const m = p.getName().match(/^(\d)_.*\.(jpe?g|png)$/i); if (m) files.push([+m[1], p, m[2]]); }
  files.sort((a, b) => a[0] - b[0]).forEach(([k, p, ext]) => p.makeCopy(`${base} ${k}.${ext.toLowerCase()}`, folder));
  if (files.length < 4) notes.push(`사진 ${files.length}/4장만 복사(02_사진_확정 확인)`);
  const st = getStatus();
  notes.push(`본문 ${st.chars}자(공백 포함), 경고 ${st.lint.filter(x => x.lv === 'err').length}건`);
  return { ok: true, url: folder.getUrl(), notes };
}
