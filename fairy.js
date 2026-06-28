/* Atelier Sage — 火の妖精（Fire Sprite）
 * カードを書く・壁打ち・新結合 で育つコンパニオン。
 * 4アプリ共有：状態は localStorage 'atelierSage.fairy.v1' に保存。
 * 使い方：window.atSageFairy.feed(n) を呼ぶと n 行動ぶん育つ。
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
  const CSS=`
  .atSage-fairy{position:fixed;bottom:18px;right:18px;width:62px;height:62px;z-index:90;cursor:pointer;
    display:flex;align-items:flex-end;justify-content:center;
    animation:atSage-float 4s ease-in-out infinite;--fs:.55}
  .atSage-fairy[data-stage="1"]{--fs:.72}
  .atSage-fairy[data-stage="2"]{--fs:.88}
  .atSage-fairy[data-stage="3"]{--fs:1}
  .atSage-fairy[data-stage="4"]{--fs:1.16}
  .atSage-fbg{position:absolute;inset:-10px;border-radius:50%;
    background:radial-gradient(circle,rgba(181,86,44,.22),transparent 65%);
    pointer-events:none;animation:atSage-pulse 3s ease-in-out infinite}
  .atSage-fl{width:36px;height:48px;filter:drop-shadow(0 0 8px rgba(229,138,92,.55));
    transform-origin:bottom;animation:atSage-flicker 1.6s ease-in-out infinite}
  .atSage-fairy.fed{animation:atSage-bounce .6s ease-out}
  .atSage-sp{position:absolute;width:5px;height:5px;border-radius:50%;background:#FFE7AE;
    box-shadow:0 0 6px #FFE7AE;opacity:0;pointer-events:none}
  .atSage-fairy[data-stage="3"] .atSage-sp[data-i="0"],
  .atSage-fairy[data-stage="3"] .atSage-sp[data-i="1"],
  .atSage-fairy[data-stage="3"] .atSage-sp[data-i="2"],
  .atSage-fairy[data-stage="4"] .atSage-sp{opacity:1}
  .atSage-sp[data-i="0"]{top:0;left:6px;animation:atSage-spark 2.2s ease-in-out infinite}
  .atSage-sp[data-i="1"]{top:8px;right:4px;animation:atSage-spark 2.6s ease-in-out infinite .4s}
  .atSage-sp[data-i="2"]{bottom:14px;left:-2px;animation:atSage-spark 2.4s ease-in-out infinite .8s}
  .atSage-sp[data-i="3"]{bottom:6px;right:-2px;animation:atSage-spark 2.8s ease-in-out infinite 1.1s}
  .atSage-sp[data-i="4"]{top:18px;left:0;animation:atSage-spark 2.3s ease-in-out infinite .6s}
  @keyframes atSage-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}
  @keyframes atSage-pulse{0%,100%{opacity:.7;transform:scale(1)}50%{opacity:1;transform:scale(1.1)}}
  @keyframes atSage-flicker{0%,100%{transform:scale(var(--fs))}
    25%{transform:scale(calc(var(--fs)*1.06)) translateY(-1px)}
    50%{transform:scale(calc(var(--fs)*.94)) translateY(1px)}
    75%{transform:scale(calc(var(--fs)*1.02))}}
  @keyframes atSage-spark{0%,100%{opacity:0;transform:translate(0,2px)}
    50%{opacity:1;transform:translate(-2px,-9px)}}
  @keyframes atSage-bounce{0%,100%{transform:translateY(0) scale(1)}
    40%{transform:translateY(-9px) scale(1.14)}
    70%{transform:translateY(-2px) scale(1.05)}}
  @media (prefers-reduced-motion:reduce){.atSage-fairy,.atSage-fl,.atSage-fbg,.atSage-sp{animation:none}}
  .atSage-fp{position:fixed;bottom:88px;right:18px;width:270px;z-index:91;
    background:#FBF7EF;border:1px solid #D9D2C4;border-radius:10px;
    padding:14px 16px;box-shadow:0 10px 24px rgba(31,42,36,.18);
    font-family:system-ui,-apple-system,'Hiragino Sans','Hiragino Kaku Gothic ProN',sans-serif;
    color:#2E3A33;font-size:13px;line-height:1.6;animation:atSage-pop .25s cubic-bezier(.2,.7,.2,1)}
  .atSage-fp[hidden]{display:none}
  @keyframes atSage-pop{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .atSage-nm{font-family:Georgia,'游明朝','Yu Mincho',serif;font-size:18px;color:#1F2A24;margin:0 0 2px}
  .atSage-pt{font-size:12px;color:#5A6B61;margin-bottom:10px}
  .atSage-pr{height:5px;background:rgba(63,107,78,.12);border-radius:3px;overflow:hidden;margin-bottom:8px}
  .atSage-bar{height:100%;background:linear-gradient(90deg,#FFB66C,#B5562C);
    transition:width 600ms cubic-bezier(.2,.7,.2,1)}
  .atSage-st{font-size:12px;color:#5A6B61}
  .atSage-st b{color:#1F2A24;font-variant-numeric:tabular-nums;margin:0 2px}
  .atSage-hi{font-size:11.5px;color:#5A6B61;margin-top:4px}
  .atSage-hi b{color:#B5562C;font-variant-numeric:tabular-nums;margin:0 2px}
  .atSage-cl{margin-top:10px;background:transparent;border:1px solid #D9D2C4;color:#2E3A33;
    border-radius:5px;padding:5px 12px;cursor:pointer;font-size:12px;font-family:inherit}
  .atSage-gr{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:100;
    background:rgba(31,42,36,.32);pointer-events:none;opacity:0;animation:atSage-grow 2.6s ease-out forwards}
  .atSage-grc{background:#FBF7EF;border:1px solid #D9D2C4;border-radius:12px;
    padding:24px 32px;text-align:center;font-family:Georgia,'游明朝','Yu Mincho',serif;
    font-size:22px;color:#1F2A24;box-shadow:0 12px 32px rgba(31,42,36,.3)}
  .atSage-grc small{display:block;font-family:system-ui,sans-serif;font-size:13px;color:#5A6B61;margin-top:6px}
  @keyframes atSage-grow{0%{opacity:0;transform:scale(.92)}20%{opacity:1;transform:scale(1)}80%{opacity:1}100%{opacity:0;transform:scale(1.05)}}
  `;
  const SVG = '<svg class="atSage-fl" viewBox="0 0 24 32" aria-hidden="true">'
    +'<defs><linearGradient id="atSageG" x1="50%" y1="0%" x2="50%" y2="100%">'
    +'<stop offset="0%" stop-color="#FFE3A8"/><stop offset="60%" stop-color="#E58A5C"/>'
    +'<stop offset="100%" stop-color="#B5562C"/></linearGradient></defs>'
    +'<path d="M12 2 C 8 9, 4.5 13, 4.5 19 C 4.5 25.5, 8 30, 12 30 C 16 30, 19.5 25.5, 19.5 19 C 19.5 13, 16 9, 12 2 Z" fill="url(#atSageG)"/>'
    +'<ellipse cx="12" cy="22" rx="3.5" ry="6" fill="#FFE7AE" opacity=".7"/></svg>';

  function todayMs(){var d=new Date();d.setHours(0,0,0,0);return d.getTime()}
  function getState(){try{return Object.assign({actions:0,today:0,lastDay:0,streak:0,stage:0},JSON.parse(localStorage.getItem(K))||{})}catch(e){return {actions:0,today:0,lastDay:0,streak:0,stage:0}}}
  function stageOf(a){var i=0;for(var j=0;j<STAGES.length;j++) if(a>=STAGES[j].min) i=j; return i}

  function render(s){
    var f=document.getElementById('atSage-fairy'); if(!f) return;
    f.dataset.stage=s.stage;
    var p=document.getElementById('atSage-fp'); if(!p) return;
    var cur=STAGES[s.stage], next=STAGES[s.stage+1];
    p.querySelector('.atSage-nm').textContent=cur.name;
    p.querySelector('.atSage-pt').textContent=cur.poet;
    p.querySelector('.atSage-a').textContent=s.actions;
    p.querySelector('.atSage-d').textContent=s.today||0;
    p.querySelector('.atSage-s').textContent=s.streak||1;
    if(next){
      var togo=Math.max(0,next.min-s.actions);
      p.querySelector('.atSage-t').textContent=togo+'回';
      var pct=Math.min(100,Math.round((s.actions-cur.min)/(next.min-cur.min)*100));
      p.querySelector('.atSage-bar').style.width=pct+'%';
    } else {
      p.querySelector('.atSage-t').textContent='—（最大）';
      p.querySelector('.atSage-bar').style.width='100%';
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
    render(s);
    var f=document.getElementById('atSage-fairy');
    if(f){f.classList.remove('fed'); void f.offsetWidth; f.classList.add('fed')}
    if(grew) celebrate(s);
  }

  function mount(){
    if(document.getElementById('atSage-fairy')) return;
    var st=document.createElement('style'); st.textContent=CSS; document.head.appendChild(st);
    var w=document.createElement('div');
    w.innerHTML='<div id="atSage-fairy" class="atSage-fairy" role="button" tabindex="0" aria-label="火の妖精" title="火の妖精" data-stage="0">'
      +'<div class="atSage-fbg"></div>'+SVG
      +'<div class="atSage-sp" data-i="0"></div><div class="atSage-sp" data-i="1"></div>'
      +'<div class="atSage-sp" data-i="2"></div><div class="atSage-sp" data-i="3"></div>'
      +'<div class="atSage-sp" data-i="4"></div></div>'
      +'<div id="atSage-fp" class="atSage-fp" hidden>'
      +'<div class="atSage-nm">火種</div><div class="atSage-pt">まだ小さな火種</div>'
      +'<div class="atSage-pr"><div class="atSage-bar"></div></div>'
      +'<div class="atSage-st">合計 <b class="atSage-a">0</b>回 ／ 次の段階まで <b class="atSage-t">10回</b></div>'
      +'<div class="atSage-hi">今日 <b class="atSage-d">0</b>回 ／ 連続 <b class="atSage-s">1</b>日</div>'
      +'<button class="atSage-cl">閉じる</button></div>';
    while(w.firstChild) document.body.appendChild(w.firstChild);
    var f=document.getElementById('atSage-fairy'), p=document.getElementById('atSage-fp');
    f.addEventListener('click',function(){p.hidden=!p.hidden});
    f.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();p.hidden=!p.hidden}});
    p.querySelector('.atSage-cl').addEventListener('click',function(){p.hidden=true});
    render(getState());
  }

  window.atSageFairy={feed:feed,getState:getState};
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',mount);
  else mount();
})();
