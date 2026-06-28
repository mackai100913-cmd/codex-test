/* Atelier Sage — 火の妖精（3D Fire Sprite + Dialogue）
 * - 立体的に存在する火（CSS 3D perspective + 多層レイヤー + 軌道粒子）
 * - 火と対話できる（カード追加・壁打ち・新結合で育つ／クリックで対話開始）
 * 状態は localStorage 'atelierSage.fairy.v1'。4アプリで共有。
 */
(function(){
  const K='atelierSage.fairy.v1';
  const STAGES=[
    {min:0,   name:'火種',     poet:'まだ小さな火種。書くたびに育つ'},
    {min:10,  name:'灯火',     poet:'静かに揺らぐ灯。あなたの工房に灯る'},
    {min:30,  name:'焚火',     poet:'力強く燃える。思考を温める'},
    {min:80,  name:'舞う火',   poet:'形を持ち始める。あなたを見守る'},
    {min:180, name:'火の妖精', poet:'あなたの思考に寄り添う妖精'},
  ];

  // 対話の応答プール（段階×トピック）
  const GREETINGS={
    0:['…じっと火を見つめている','ぱちり、と小さな音がした','まだ言葉を覚えていない'],
    1:['やあ、今日も来てくれた','ようこそ、思考の工房へ','静かに揺れている'],
    2:['炎が踊っている。いい風が吹いてる','今日も書きにきたんだね','体が温かい'],
    3:['君のことを見ていた。何か話そうか','言葉を待っていた','風向きを感じる'],
    4:['やあ、相棒。今日は何を考えてる？','君の思考は今日も冴えてる','一緒に火を眺めよう'],
  };
  const REPLIES={
    tired:['ゆっくりで大丈夫。火は消えない','休むのも仕事。明日また書こう','深呼吸して。火は待ってるよ'],
    idea:['書き出してみよう。私が見てる','その思いつき、もう一枚書ける？','種は書いて初めて芽になる'],
    lost:['二択に絞ると見えてくる','迷うのは進んでる証拠','一つ捨てると、残った一つが光る'],
    why:['問いを残すと、明日の火になる','「なぜ」は最も強い薪だ','理由を言葉にすると、火が立つ'],
    no:['それでいい。書かない日もある','私はここにいる、ずっと','明日でも、明後日でも'],
    yes:['よし、火を強くしよう','一緒にやろう','その一歩で十分'],
    thanks:['いいや、お互いさま','こちらこそ','火は誰かの手で育つもの'],
    name:['名前か。…君が決めて？','「あなたの相棒」でいい','まだ呼ばれていない'],
    test:['聞こえてる、ちゃんと','声が届いた','一緒にいる'],
  };
  const PROMPTS={
    0:['…','もっと書いて'],
    1:['今日のもう一枚は？','何の問いを温めたい？'],
    2:['次は何の問い？','どの軸を磨く？','迷ってる軸ある？'],
    3:['書いたカードの中で、今いちばん気になる一枚は？','他のカードと繋いでみない？','逆に考えるとどう？'],
    4:['今日の北極星はどこ？','一番"効きそう"な打ち手は？','物語の主役は誰？'],
  };

  const CSS=`
  .atSage-fairy{position:fixed;bottom:18px;right:18px;z-index:90;cursor:pointer;
    perspective:280px;perspective-origin:50% 65%;
    animation:atSage-float 5s ease-in-out infinite}
  .atSage-stage{position:relative;width:80px;height:96px;transform-style:preserve-3d;
    animation:atSage-orbit 7s ease-in-out infinite;
    --fs:.55}
  .atSage-fairy[data-stage="1"] .atSage-stage{--fs:.72}
  .atSage-fairy[data-stage="2"] .atSage-stage{--fs:.88}
  .atSage-fairy[data-stage="3"] .atSage-stage{--fs:1.0}
  .atSage-fairy[data-stage="4"] .atSage-stage{--fs:1.16}
  .atSage-fairy.fed .atSage-stage{animation:atSage-orbit 7s ease-in-out infinite, atSage-bounce .65s ease-out}
  .atSage-layer{position:absolute;left:50%;bottom:0;width:40px;height:56px;margin-left:-20px;
    transform-style:preserve-3d;transform-origin:50% 100%;pointer-events:none}
  .atSage-layer svg{width:100%;height:100%;display:block}
  .atSage-outer{transform:translateZ(-12px) scale(calc(var(--fs) * 1.35));opacity:.32;filter:blur(3px)}
  .atSage-mid  {transform:translateZ(0px) scale(var(--fs));opacity:.92;animation:atSage-flicker 1.6s ease-in-out infinite}
  .atSage-core {transform:translateZ(12px) scale(calc(var(--fs) * .58));filter:drop-shadow(0 0 6px #FFE7AE)}
  .atSage-base{position:absolute;left:50%;bottom:-6px;width:36px;height:14px;margin-left:-18px;
    background:radial-gradient(ellipse at center, rgba(181,86,44,.45), transparent 75%);filter:blur(2px)}
  .atSage-ring{position:absolute;inset:0;transform-style:preserve-3d;
    animation:atSage-ring 9s linear infinite}
  .atSage-sp{position:absolute;left:50%;top:50%;width:5px;height:5px;margin:-2.5px;
    border-radius:50%;background:#FFE7AE;box-shadow:0 0 7px #FFE7AE;
    opacity:0;transform-style:preserve-3d}
  .atSage-fairy[data-stage="2"] .atSage-sp[data-i="0"],
  .atSage-fairy[data-stage="2"] .atSage-sp[data-i="1"],
  .atSage-fairy[data-stage="3"] .atSage-sp{opacity:1}
  .atSage-fairy[data-stage="4"] .atSage-sp{opacity:1;width:6px;height:6px}
  .atSage-sp[data-i="0"]{animation:atSage-orbit-p1 4.2s linear infinite}
  .atSage-sp[data-i="1"]{animation:atSage-orbit-p2 5.0s linear infinite}
  .atSage-sp[data-i="2"]{animation:atSage-orbit-p3 4.6s linear infinite}
  .atSage-sp[data-i="3"]{animation:atSage-orbit-p4 5.3s linear infinite}
  .atSage-sp[data-i="4"]{animation:atSage-orbit-p5 4.4s linear infinite}
  @keyframes atSage-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
  @keyframes atSage-orbit{0%,100%{transform:rotateY(-14deg) rotateX(5deg)}50%{transform:rotateY(14deg) rotateX(-5deg)}}
  @keyframes atSage-flicker{
    0%,100%{transform:translateZ(0) scale(var(--fs))}
    25%{transform:translateZ(0) scale(calc(var(--fs)*1.07)) translateY(-1px)}
    50%{transform:translateZ(0) scale(calc(var(--fs)*.93)) translateY(1px)}
    75%{transform:translateZ(0) scale(calc(var(--fs)*1.02))}}
  @keyframes atSage-bounce{
    0%,100%{transform:translateY(0)}
    40%{transform:translateY(-9px) scale(1.04)}
    70%{transform:translateY(-2px)}}
  @keyframes atSage-ring{from{transform:rotateY(0deg)}to{transform:rotateY(360deg)}}
  @keyframes atSage-orbit-p1{
    0%{transform:rotateY(0)   translateX(28px) translateY(-6px) rotateY(0)}
    100%{transform:rotateY(360deg) translateX(28px) translateY(-6px) rotateY(-360deg)}}
  @keyframes atSage-orbit-p2{
    0%{transform:rotateY(72deg)  translateX(24px) translateY(0) rotateY(0)}
    100%{transform:rotateY(432deg) translateX(24px) translateY(0) rotateY(-360deg)}}
  @keyframes atSage-orbit-p3{
    0%{transform:rotateY(144deg) translateX(26px) translateY(6px) rotateY(0)}
    100%{transform:rotateY(504deg) translateX(26px) translateY(6px) rotateY(-360deg)}}
  @keyframes atSage-orbit-p4{
    0%{transform:rotateY(216deg) translateX(30px) translateY(-3px) rotateY(0)}
    100%{transform:rotateY(576deg) translateX(30px) translateY(-3px) rotateY(-360deg)}}
  @keyframes atSage-orbit-p5{
    0%{transform:rotateY(288deg) translateX(22px) translateY(4px) rotateY(0)}
    100%{transform:rotateY(648deg) translateX(22px) translateY(4px) rotateY(-360deg)}}
  @media (prefers-reduced-motion:reduce){
    .atSage-fairy,.atSage-stage,.atSage-mid,.atSage-ring,.atSage-sp{animation:none}}

  .atSage-dlg{position:fixed;bottom:118px;right:18px;width:320px;max-width:calc(100vw - 36px);
    max-height:64vh;z-index:91;background:#FBF7EF;border:1px solid #D9D2C4;border-radius:12px;
    display:flex;flex-direction:column;
    box-shadow:0 14px 32px rgba(31,42,36,.22);
    font-family:system-ui,-apple-system,'Hiragino Sans','Hiragino Kaku Gothic ProN',sans-serif;
    color:#2E3A33;font-size:13px;line-height:1.55;
    animation:atSage-pop .28s cubic-bezier(.2,.7,.2,1);overflow:hidden}
  .atSage-dlg[hidden]{display:none}
  @keyframes atSage-pop{from{opacity:0;transform:translateY(10px) scale(.98)}to{opacity:1;transform:none}}
  .atSage-head{display:flex;align-items:center;gap:8px;padding:11px 14px;border-bottom:1px solid #D9D2C4;flex-shrink:0;background:#F4EFE6}
  .atSage-name{font-family:Georgia,'游明朝','Yu Mincho',serif;font-size:17px;color:#1F2A24;letter-spacing:0}
  .atSage-poet{font-size:11px;color:#5A6B61;margin-left:6px}
  .atSage-x{margin-left:auto;background:transparent;border:none;color:#5A6B61;cursor:pointer;
    font-size:20px;padding:0 4px;line-height:1;font-family:inherit}
  .atSage-x:hover{color:#1F2A24}
  .atSage-meta{padding:8px 14px;border-bottom:1px solid #D9D2C4;font-size:11.5px;color:#5A6B61;background:#FBF7EF;display:none}
  .atSage-meta.show{display:block}
  .atSage-meta b{color:#1F2A24;font-variant-numeric:tabular-nums;margin:0 2px}
  .atSage-pr{height:5px;background:rgba(63,107,78,.12);border-radius:3px;overflow:hidden;margin-bottom:6px}
  .atSage-bar{height:100%;background:linear-gradient(90deg,#FFB66C,#B5562C);
    transition:width 600ms cubic-bezier(.2,.7,.2,1)}
  .atSage-stats{font-size:11.5px;color:#5A6B61;margin-top:4px}
  .atSage-stats b{color:#1F2A24;font-variant-numeric:tabular-nums;margin:0 2px}
  .atSage-statbtn{background:transparent;border:1px solid #D9D2C4;color:#5A6B61;cursor:pointer;
    border-radius:6px;padding:3px 8px;font-size:11px;font-family:inherit}
  .atSage-statbtn.on{background:#3F6B4E;color:#fff;border-color:#3F6B4E}
  .atSage-log{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px;min-height:120px}
  .atSage-msg{padding:7px 11px;border-radius:11px;max-width:80%;
    line-height:1.55;white-space:pre-wrap;word-break:break-word;font-size:13px;
    animation:atSage-msg .3s cubic-bezier(.2,.7,.2,1)}
  @keyframes atSage-msg{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
  .atSage-msg.fairy{align-self:flex-start;background:#F4EFE6;color:#2E3A33;border:1px solid #D9D2C4;
    border-top-left-radius:3px}
  .atSage-msg.user{align-self:flex-end;background:#EAF2EC;color:#1F2A24;border:1px solid #C5D9C8;
    border-top-right-radius:3px}
  .atSage-input{display:flex;gap:6px;padding:10px 12px;border-top:1px solid #D9D2C4;background:#FBF7EF;flex-shrink:0}
  .atSage-input input{flex:1;padding:7px 11px;border:1px solid #D9D2C4;border-radius:6px;
    background:#FFFCF3;color:#2E3A33;font-family:inherit;font-size:13px;outline:none}
  .atSage-input input:focus{border-color:#3F6B4E}
  .atSage-input button{background:#3F6B4E;color:#fff;border:none;border-radius:6px;
    padding:7px 13px;font-size:12.5px;cursor:pointer;font-family:inherit;font-weight:600}
  .atSage-input button:hover{background:#345A41}

  .atSage-gr{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:100;
    background:rgba(31,42,36,.32);pointer-events:none;opacity:0;animation:atSage-grow 2.6s ease-out forwards}
  .atSage-grc{background:#FBF7EF;border:1px solid #D9D2C4;border-radius:12px;
    padding:24px 32px;text-align:center;font-family:Georgia,'游明朝','Yu Mincho',serif;
    font-size:22px;color:#1F2A24;box-shadow:0 12px 32px rgba(31,42,36,.3)}
  .atSage-grc small{display:block;font-family:system-ui,sans-serif;font-size:13px;color:#5A6B61;margin-top:6px}
  @keyframes atSage-grow{0%{opacity:0;transform:scale(.92)}20%{opacity:1;transform:scale(1)}80%{opacity:1}100%{opacity:0;transform:scale(1.05)}}
  `;

  const FLAME_SVG = '<svg viewBox="0 0 24 32" aria-hidden="true">'
    +'<defs><linearGradient id="atSageG_$ID" x1="50%" y1="0%" x2="50%" y2="100%">'
    +'<stop offset="0%" stop-color="#FFE3A8"/><stop offset="55%" stop-color="#E58A5C"/>'
    +'<stop offset="100%" stop-color="#B5562C"/></linearGradient></defs>'
    +'<path d="M12 1.5 C 7.5 9, 4 13.5, 4 19.5 C 4 26, 7.5 30.5, 12 30.5 C 16.5 30.5, 20 26, 20 19.5 C 20 13.5, 16.5 9, 12 1.5 Z" fill="url(#atSageG_$ID)"/>'
    +'<ellipse cx="12" cy="23" rx="3.2" ry="5.5" fill="#FFEDB6" opacity=".82"/>'
    +'</svg>';

  function todayMs(){var d=new Date();d.setHours(0,0,0,0);return d.getTime()}
  function getState(){try{return Object.assign({actions:0,today:0,lastDay:0,streak:0,stage:0},JSON.parse(localStorage.getItem(K))||{})}catch(e){return{actions:0,today:0,lastDay:0,streak:0,stage:0}}}
  function stageOf(a){var i=0;for(var j=0;j<STAGES.length;j++) if(a>=STAGES[j].min) i=j; return i}
  function rand(arr){return arr[Math.floor(Math.random()*arr.length)]}

  function replyToMessage(text, stage){
    var t=(text||'').toLowerCase();
    if(/疲れ|つかれ|休|しんど|忙し/.test(t)) return rand(REPLIES.tired);
    if(/アイデア|思いつ|ひらめ|思いつき/.test(t)) return rand(REPLIES.idea);
    if(/迷|わからない|どっち|決め|選/.test(t)) return rand(REPLIES.lost);
    if(/なぜ|どうし|why|理由/.test(t)) return rand(REPLIES.why);
    if(/^(無理|やめ|もういい|だめ)/.test(t)) return rand(REPLIES.no);
    if(/^(よし|やる|がんば|頑張|ok|オーケー)/.test(t)) return rand(REPLIES.yes);
    if(/ありがと|サンキュー|thanks/.test(t)) return rand(REPLIES.thanks);
    if(/名前|なまえ|呼び方/.test(t)) return rand(REPLIES.name);
    if(/聞こえ|テスト|test|hello|こんにち|おはよ|こんばん/.test(t)) return rand(REPLIES.test);
    // fallback: stage-aware prompt
    var pool=(PROMPTS[stage]||PROMPTS[0]).slice();
    return rand(pool);
  }

  function renderFairy(s){
    var f=document.getElementById('atSage-fairy'); if(!f) return;
    f.dataset.stage=s.stage;
    f.setAttribute('aria-label','火の妖精（'+STAGES[s.stage].name+'）と話す');
    var d=document.getElementById('atSage-dlg'); if(!d) return;
    var cur=STAGES[s.stage], next=STAGES[s.stage+1];
    d.querySelector('.atSage-name').textContent=cur.name;
    d.querySelector('.atSage-poet').textContent=cur.poet;
    var bA=d.querySelector('.atSage-a'); if(bA) bA.textContent=s.actions;
    var bD=d.querySelector('.atSage-d'); if(bD) bD.textContent=s.today||0;
    var bS=d.querySelector('.atSage-s'); if(bS) bS.textContent=s.streak||1;
    if(next){
      var togo=Math.max(0,next.min-s.actions);
      var bT=d.querySelector('.atSage-t'); if(bT) bT.textContent=togo+'回';
      var pct=Math.min(100,Math.round((s.actions-cur.min)/(next.min-cur.min)*100));
      var bar=d.querySelector('.atSage-bar'); if(bar) bar.style.width=pct+'%';
    } else {
      var bT2=d.querySelector('.atSage-t'); if(bT2) bT2.textContent='—（最大）';
      var bar2=d.querySelector('.atSage-bar'); if(bar2) bar2.style.width='100%';
    }
  }
  function celebrate(s){
    var ov=document.createElement('div'); ov.className='atSage-gr';
    ov.innerHTML='<div class="atSage-grc">✨ 火が大きくなった<small>'+STAGES[s.stage].name+' ― '+STAGES[s.stage].poet+'</small></div>';
    document.body.appendChild(ov);
    setTimeout(function(){ov.remove()},2600);
  }
  function feed(n){
    n=n||1;
    var s=getState();
    s.actions=(s.actions||0)+n;
    var t=todayMs();
    if(s.lastDay!==t){
      var diff=s.lastDay?Math.round((t-s.lastDay)/86400000):0;
      s.streak=(diff===1)?((s.streak||0)+1):1;
      s.lastDay=t; s.today=0;
    }
    s.today=(s.today||0)+n;
    var ns=stageOf(s.actions), grew=ns>(s.stage||0);
    s.stage=ns;
    try{localStorage.setItem(K,JSON.stringify(s))}catch(e){}
    renderFairy(s);
    var f=document.getElementById('atSage-fairy');
    if(f){f.classList.remove('fed'); void f.offsetWidth; f.classList.add('fed')}
    if(grew) celebrate(s);
  }

  function appendMsg(role, text){
    var log=document.getElementById('atSage-log'); if(!log) return;
    var d=document.createElement('div'); d.className='atSage-msg '+role; d.textContent=text;
    log.appendChild(d); log.scrollTop=log.scrollHeight;
  }
  function fairySays(text, delay){
    setTimeout(function(){appendMsg('fairy', text)}, delay||450);
  }
  function userSpeaks(text){
    text=(text||'').trim(); if(!text) return;
    appendMsg('user', text);
    var s=getState();
    fairySays(replyToMessage(text, s.stage), 500 + Math.random()*400);
  }

  function buildDOM(){
    if(document.getElementById('atSage-fairy')) return;
    var st=document.createElement('style'); st.textContent=CSS; document.head.appendChild(st);
    var w=document.createElement('div');
    var flames = FLAME_SVG.replace(/\$ID/g,'o')
      + FLAME_SVG.replace(/\$ID/g,'m')
      + FLAME_SVG.replace(/\$ID/g,'c');
    w.innerHTML=''
      +'<div id="atSage-fairy" class="atSage-fairy" role="button" tabindex="0" data-stage="0" aria-label="火の妖精と話す">'
        +'<div class="atSage-stage">'
          +'<div class="atSage-base"></div>'
          +'<div class="atSage-layer atSage-outer">'+FLAME_SVG.replace(/\$ID/g,'o')+'</div>'
          +'<div class="atSage-layer atSage-mid">'+FLAME_SVG.replace(/\$ID/g,'m')+'</div>'
          +'<div class="atSage-layer atSage-core">'+FLAME_SVG.replace(/\$ID/g,'c')+'</div>'
          +'<div class="atSage-ring">'
            +'<div class="atSage-sp" data-i="0"></div><div class="atSage-sp" data-i="1"></div>'
            +'<div class="atSage-sp" data-i="2"></div><div class="atSage-sp" data-i="3"></div>'
            +'<div class="atSage-sp" data-i="4"></div>'
          +'</div>'
        +'</div>'
      +'</div>'
      +'<div id="atSage-dlg" class="atSage-dlg" hidden>'
        +'<div class="atSage-head">'
          +'<span class="atSage-name">火種</span>'
          +'<span class="atSage-poet">まだ小さな火種</span>'
          +'<button class="atSage-statbtn" title="ステータス" aria-label="ステータスを切替">📊</button>'
          +'<button class="atSage-x" aria-label="閉じる">×</button>'
        +'</div>'
        +'<div class="atSage-meta">'
          +'<div class="atSage-pr"><div class="atSage-bar"></div></div>'
          +'<div class="atSage-stats">合計 <b class="atSage-a">0</b>回 ／ 次の段階まで <b class="atSage-t">10回</b><br>'
          +'今日 <b class="atSage-d">0</b>回 ／ 連続 <b class="atSage-s">1</b>日</div>'
        +'</div>'
        +'<div class="atSage-log" id="atSage-log"></div>'
        +'<div class="atSage-input">'
          +'<input type="text" id="atSage-input" placeholder="火に話しかける…" autocomplete="off">'
          +'<button id="atSage-send">送る</button>'
        +'</div>'
      +'</div>';
    while(w.firstChild) document.body.appendChild(w.firstChild);
  }

  function mount(){
    if(!document.body){document.addEventListener('DOMContentLoaded',mount);return}
    buildDOM();
    var fairy=document.getElementById('atSage-fairy');
    var dlg=document.getElementById('atSage-dlg');
    var statBtn=dlg.querySelector('.atSage-statbtn');
    var meta=dlg.querySelector('.atSage-meta');
    var closeBtn=dlg.querySelector('.atSage-x');
    var input=document.getElementById('atSage-input');
    var sendBtn=document.getElementById('atSage-send');
    var greeted=false;

    function openDlg(){
      dlg.hidden=false;
      renderFairy(getState());
      if(!greeted){
        greeted=true;
        var s=getState();
        fairySays(rand(GREETINGS[s.stage]||GREETINGS[0]), 300);
      }
      setTimeout(function(){input&&input.focus()},120);
    }
    function closeDlg(){dlg.hidden=true}

    fairy.addEventListener('click',function(){dlg.hidden?openDlg():closeDlg()});
    fairy.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();dlg.hidden?openDlg():closeDlg()}});
    closeBtn.addEventListener('click',closeDlg);
    statBtn.addEventListener('click',function(){
      var on=meta.classList.toggle('show');
      statBtn.classList.toggle('on',on);
    });
    sendBtn.addEventListener('click',function(){var v=input.value;input.value='';userSpeaks(v)});
    input.addEventListener('keydown',function(e){
      if(e.key==='Enter'){e.preventDefault();var v=input.value;input.value='';userSpeaks(v)}
      if(e.key==='Escape'){closeDlg()}
    });
    document.addEventListener('keydown',function(e){if(e.key==='Escape'&&!dlg.hidden)closeDlg()});

    renderFairy(getState());
  }

  window.atSageFairy={feed:feed,getState:getState};
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',mount);
  else mount();
})();
