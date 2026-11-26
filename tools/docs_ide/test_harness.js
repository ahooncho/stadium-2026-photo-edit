// Apps Script 전역을 흉내 내 Code.gs의 parse_/getStatus를 실행하는 시험 도구
const fs=require('fs');
const ET={PARAGRAPH:'P',TABLE:'T',TEXT:'X',LIST_ITEM:'L'}, PH={HEADING2:'H2',HEADING3:'H3',NORMAL:'N'};
const P=(t,h='N',bg=null)=>({getType:()=>ET.PARAGRAPH,asParagraph(){return this},getText:()=>t,getHeading:()=>h,editAsText:()=>({getTextAttributeIndices:()=>[0],getBackgroundColor:()=>bg}),
  getNumChildren:()=>1,getChild:()=>({getType:()=>ET.TEXT,asText:()=>({getTextAttributeIndices:()=>[0],getBackgroundColor:()=>bg})})});
const T=rows=>({getType:()=>ET.TABLE,asTable(){return this},getNumRows:()=>rows.length,
  getRow:r=>({getNumCells:()=>rows[r].length,getCell:c=>({getText:()=>rows[r][c]})})});
const LI=(t,struck=false)=>({getType:()=>'L',asListItem(){return this},getText:()=>t,getHeading:()=>'N',editAsText:()=>({getText:()=>t,isStrikethrough:()=>struck,getTextAttributeIndices:()=>[0],getBackgroundColor:()=>null})});
const body=[
 P('제목: 7년 만에 포스텍서 열린 STadium, 우리대학 종합우승'),P('부제: LoL 우승·농구 준우승… IT ARENA선 6개 대학 IT 동아리 교류'),
 P('본문','H2'),P('가'.repeat(260)),P('축구, 농구, 배드민턴, 야구 경기가 열렸다. '+'나'.repeat(500)),P('중간 순위에서 KAIST 23점… 그러나… 결국… 끝','N','#ffff00'),P('다'.repeat(940)),
 P('김민하 기자 eileen@postech.ac.kr'),P('조아훈 기자 ahoncho@postech.ac.kr'),
 P('캡션','H2'),P('1 LoL — ▲LoL 결선에서 DGIST를 꺾은 우리대학 선수들'),P('2 축구 — ▲'),P('3 IT ARENA — 학생회관 아틀라스홀 Auto Car Race 출발선'),P('4 농구 — ▲골밑으로 뛰어올라 점프슛을 시도하는 우리대학 선수'),
 P('확인할 것','H2'),LI('축구 결승 결과(UNIST전)'),LI('야구 스코어',true),LI("'7년 만에'"),
];
global.DocumentApp={ElementType:ET,ParagraphHeading:PH,getActiveDocument:()=>({getBody:()=>({getNumChildren:()=>body.length,getChild:i=>body[i]})})};
global.Utilities={formatDate:()=>'12:00:00'};
eval(fs.readFileSync('Code.gs','utf8')+';global.getStatus=getStatus;');
const s=getStatus();
console.log('chars',s.chars,'noSpace',s.noSpace);
console.log('cols',s.cols.map(c=>c.name+' '+c.used+'/'+c.cap).join(' | '),'overflow',s.overflowLines);
console.log('title',s.title,'|',s.deck);
console.log('facts',s.factOpen);
s.lint.forEach(l=>console.log(' ',l.lv,l.msg));
