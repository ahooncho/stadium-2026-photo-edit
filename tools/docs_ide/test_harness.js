// Apps Script 전역을 흉내 내 Code.gs의 parse_/getStatus를 실행하는 시험 도구
const fs=require('fs');
const ET={PARAGRAPH:'P',TABLE:'T',TEXT:'X'}, PH={HEADING2:'H2',HEADING3:'H3',NORMAL:'N'};
const P=(t,h='N',bg=null)=>({getType:()=>ET.PARAGRAPH,asParagraph(){return this},getText:()=>t,getHeading:()=>h,
  getNumChildren:()=>1,getChild:()=>({getType:()=>ET.TEXT,asText:()=>({getTextAttributeIndices:()=>[0],getBackgroundColor:()=>bg})})});
const T=rows=>({getType:()=>ET.TABLE,asTable(){return this},getNumRows:()=>rows.length,
  getRow:r=>({getNumCells:()=>rows[r].length,getCell:c=>({getText:()=>rows[r][c]})})});
const body=[
 P('3. 제목·부제','H2'),P('확정 제목: 7년 만에 포스텍서 열린 STadium, 우리대학 종합우승'),P('확정 부제: LoL 우승·농구 준우승… IT ARENA선 6개 대학 IT 동아리 교류'),
 P('5. 팩트 시트','H2'),T([['항목','내용','상태'],['참가','6개','확인'],['축구','결승','결승 스코어 확인 필요'],['야구','4-6','최종 스코어 재확인 권장']]),
 P('6. 사진과 캡션','H2'),T([['사진','위치·폭','한 줄 최대','캡션(작성)','확인할 것'],['LoL','2단','약 40자','▲LoL 결선에서 DGIST를 꺾은 우리대학 선수들',''],['축구','3단','약 60자','▲',''],['IT','2단','약 40자','학생회관 아틀라스홀에서 열린 Auto Car Race 출발선에 모인 관람객들과 참가자들',''],['농구','1단','약 19자','▲점프슛을 시도하는 우리대학 선수','']]),
 P('8. 본문 (여기에 작성)','H2'),P('블록 제목(①~⑤) 줄은 작업용 표시입니다.'),
 P('① 리드 [조아훈]','H3'),P('가'.repeat(260)),
 P('② STadium 경기 [조아훈]','H3'),P('축구, 농구, 배드민턴, 야구 경기가 열렸다. '+'나'.repeat(500)),P('중간 순위에서 KAIST 23점… 그러나… 결국… 끝','N','#ffff00'),
 P('③ 공연·폐막·교류 [조아훈]','H3'),P('다'.repeat(240)),
 P('④ IT ARENA [김민하]','H3'),P('라'.repeat(700)),
 P('⑤ 의미·과제 [김민하]','H3'),P(''),
 P('김민하 기자 eileen@postech.ac.kr'),P('조아훈 기자 ahoncho@postech.ac.kr'),
 P('9. 취재 메모','H2'),P('여기는 본문 아님 '+'마'.repeat(300)),
];
global.DocumentApp={ElementType:ET,ParagraphHeading:PH,getActiveDocument:()=>({getBody:()=>({getNumChildren:()=>body.length,getChild:i=>body[i]})})};
global.Utilities={formatDate:()=>'12:00:00'};
eval(fs.readFileSync('Code.gs','utf8')+';global.getStatus=getStatus;');
const s=getStatus();
console.log('chars',s.chars,'noSpace',s.noSpace);
console.log('blocks',s.blocks.map(b=>b.name.slice(0,1)+':'+b.chars+'/'+b.target).join(' '));
console.log('cols',s.cols.map(c=>c.name+' '+c.used+'/'+c.cap).join(' | '),'overflow',s.overflowLines);
console.log('title',s.title,'|',s.deck);
console.log('facts',s.factOpen);
s.lint.forEach(l=>console.log(' ',l.lv,l.msg));
