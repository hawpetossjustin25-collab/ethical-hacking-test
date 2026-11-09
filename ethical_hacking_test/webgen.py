"""Builds the phone/web version (index.html) from the same question bank, so both apps always match."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ethical_hacking_test.engine import MAX_WRONG, REVEAL_SECONDS
from ethical_hacking_test.question_bank import build_bank
from ethical_hacking_test.radio import DEFAULT_VOLUME, stations_json

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#1f8a4c"><title>Ethical Hacking Practice Test</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,Segoe UI,Arial,sans-serif;background:#1e1e1e;color:#e0e0e0;min-height:100vh;padding-bottom:120px}.radio{position:fixed;left:0;right:0;bottom:0;background:#262626;border-top:1px solid #444;padding:8px 10px;z-index:9}.radio .row{max-width:700px;margin:0 auto;display:flex;gap:6px;align-items:center;flex-wrap:wrap}.radio button{background:#1f8a4c;color:#fff;border:none;border-radius:6px;padding:9px 12px;font-weight:bold;font-size:15px}.radio select{flex:1;min-width:150px;background:#333;color:#e0e0e0;border:1px solid #555;border-radius:6px;padding:8px;font-size:14px}.radio input{width:90px}.radio #rStatus{width:100%;max-width:700px;margin:4px auto 0;font-size:12px;color:#aaa}
.wrap{max-width:700px;margin:0 auto;padding:16px}h1{color:#3cc47c;font-size:20px;text-align:center;margin-bottom:10px}
.bar{background:#2b2b2b;border:1px solid #444;border-radius:8px;padding:10px;margin-bottom:12px;font-weight:bold;
font-size:14px;display:flex;justify-content:space-between}.bar .wrong{color:#ff7777}
.qbox{background:#2b2b2b;border:1px solid #444;border-radius:10px;padding:16px;margin-bottom:12px}
.qtext{font-size:17px;font-weight:600;line-height:1.4;margin-bottom:6px}.qmeta{font-size:12px;color:#888;margin-bottom:12px}
.opt{display:block;width:100%;text-align:left;background:#1e1e1e;color:#e0e0e0;border:2px solid #444;border-radius:8px;
padding:14px;margin:8px 0;font-size:16px;cursor:pointer}.opt.sel{border-color:#1f8a4c;background:#173d2a}.opt.right{border-color:#28a745;background:#173d2a}.opt.bad{border-color:#c0392b;background:#3d1717}.reveal{margin-top:10px;color:#ffb3b3;font-size:15px}
.btn{background:#1f8a4c;color:#fff;border:none;border-radius:8px;padding:14px;font-size:16px;font-weight:bold;cursor:pointer}
.btn.red{background:#c0392b}.nav{display:flex;gap:8px;margin-top:12px}.nav .btn{flex:1}
.prog{height:8px;background:#2b2b2b;border-radius:4px;overflow:hidden;margin-bottom:12px}
.prog div{height:100%;background:#1f8a4c;width:0%}.res{text-align:center}.big{font-size:42px;font-weight:bold;margin:12px 0}
.pass{color:#28a745}.fail{color:#ff5555}.wrongitem{background:#2b2b2b;border-left:4px solid #c0392b;border-radius:6px;
padding:12px;margin:10px 0;font-size:14px}.ca{color:#7fd77f}.ex{color:#aaa;font-style:italic}.hidden{display:none}
.note{font-size:12px;color:#777;text-align:center;margin-top:16px}
</style></head><body><div class="wrap"><h1>Ethical Hacking &amp; Cybersecurity Test</h1>
<div id="home"><div class="qbox" style="text-align:center"><p style="margin-bottom:14px;font-size:15px">
<b>__TOTAL__ questions</b> on hacking terms, the pen-test methodology, tools, attacks, defense, and the law - beginner to advanced
without new code liens.<br><br>Answer them all. Get <b>__LIMIT1__ wrong</b> and the test <b>restarts
automatically</b>.<br><br>Questions you miss come back <b>first</b> next time.</p>
<button class="btn" style="width:100%" onclick="startTest()">Start Test</button><br><br>
<button class="btn" style="width:100%" onclick="showWrong()">Study My Missed Questions</button><br><br>
<button class="btn red" style="width:100%" onclick="resetAll()">Reset Progress</button></div>
<p class="note">Study tool only. Practice only on systems you own or have written permission to test.</p></div>
<div id="quiz" class="hidden"><div class="bar"><span id="qnum"></span><span class="wrong" id="wcount"></span></div>
<div class="prog"><div id="pbar"></div></div><div class="qbox"><div class="qmeta" id="qch"></div>
<div class="qtext" id="qtext"></div><div id="opts"></div><div id="reveal" class="reveal"></div></div>
<div class="nav"><button class="btn" onclick="prev()">Back</button><button class="btn" onclick="next()">Next</button>
<button class="btn red" onclick="finish()">Finish</button></div></div>
<div id="result" class="hidden"><div class="qbox res"><div id="rverdict" class="big"></div><div id="rscore"></div><br>
<button class="btn" style="width:100%" onclick="showWrong()">Study Missed Questions</button><br><br>
<button class="btn" style="width:100%" onclick="goHome()">Home</button></div></div>
<div id="study" class="hidden"><div class="bar"><span>Missed questions</span><span id="studyN"></span></div>
<div id="studylist"></div><button class="btn" style="width:100%;margin-top:12px" onclick="goHome()">Home</button></div></div>
<div class="radio"><div class="row"><button onclick="rPick(rs.i-1)" aria-label="Previous station">&laquo;</button>
<button id="rPlay" onclick="rToggle()">Play</button><button onclick="rPick(rs.i+1)" aria-label="Next station">&raquo;</button>
<select id="rSel" aria-label="Station"></select><input id="rVol" type="range" min="0" max="100" aria-label="Volume"></div>
<div id="rStatus"></div><audio id="radio" preload="none"></audio></div>
<script>
const BANK=__BANK__;
const MAX_WRONG=__MAX_WRONG__;const REVEAL_MS=__REVEAL_MS__;const KEY='eht_stats';
let order=[],answers=[],scored=[],locked=[],wrong=[],cur=0,revealing=false;
function loadStats(){try{return JSON.parse(localStorage.getItem(KEY))||{}}catch(e){return {}}}
function saveStats(s){localStorage.setItem(KEY,JSON.stringify(s))}
function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
function buildOrder(){const st=loadStats(),missed=[],unseen=[],known=[];
 BANK.forEach((q,i)=>{const s=st[q.id];if(!s||!s.answered)unseen.push(i);else if(s.wrong)missed.push(i);else known.push(i)});
 return shuffle(missed).concat(shuffle(unseen),shuffle(known))}
function startTest(){order=buildOrder();answers=order.map(()=>-1);scored=order.map(()=>false);locked=order.map(()=>false);revealing=false;wrong=[];cur=0;show('quiz');render()}
function render(){const q=BANK[order[cur]];document.getElementById('qnum').textContent='Question '+(cur+1)+' of '+order.length;
 document.getElementById('wcount').textContent='Wrong: '+wrong.length+'/'+MAX_WRONG;
 document.getElementById('pbar').style.width=((cur+1)/order.length*100)+'%';
 document.getElementById('qch').textContent=q.ch;document.getElementById('qtext').textContent=q.q;
 const box=document.getElementById('opts');box.innerHTML='';document.getElementById('reveal').textContent='';
 q.o.forEach((o,i)=>{const b=document.createElement('button');b.className='opt'+(answers[cur]===i?' sel':'');
 b.textContent=String.fromCharCode(65+i)+'. '+o;b.onclick=()=>pick(i);box.appendChild(b)})}
function pick(i){if(revealing||locked[cur])return;answers[cur]=i;const q=BANK[order[cur]];
 if(i===q.c){render();return}const restart=scoreCur(true);locked[cur]=true;revealing=true;render();
 const btns=document.querySelectorAll('#opts .opt');btns.forEach((b,k)=>{b.disabled=true;b.className='opt'+(k===q.c?' right':(k===i?' bad':''))});
 let left=REVEAL_MS/1000;const r=document.getElementById('reveal');
 const say=()=>{r.textContent='Wrong - correct answer: '+String.fromCharCode(65+q.c)+'. '+q.o[q.c]+' — '+q.e+' (next in '+left+'s)'};say();
 const t=setInterval(()=>{left--;if(left>0)say()},1000);
 setTimeout(()=>{clearInterval(t);revealing=false;if(restart){alert((MAX_WRONG+1)+' wrong answers - test restarting! Your missed questions come first.');startTest()}
  else if(cur<order.length-1){cur++;render()}else render()},REVEAL_MS)}
function scoreCur(noRestart){if(scored[cur]||answers[cur]===-1)return false;scored[cur]=true;const q=BANK[order[cur]];
 const st=loadStats();st[q.id]=st[q.id]||{r:0,w:0,wrong:false};st[q.id].answered=true;
 if(answers[cur]===q.c){st[q.id].r++;st[q.id].wrong=false}else{st[q.id].w++;st[q.id].wrong=true;wrong.push(order[cur])}
 saveStats(st);if(wrong.length>MAX_WRONG){if(noRestart)return true;alert((MAX_WRONG+1)+' wrong answers - test restarting! Your missed questions come first.');startTest();return true}return false}
function next(){if(revealing||scoreCur())return;if(cur<order.length-1){cur++;render()}}
function prev(){if(revealing||scoreCur())return;if(cur>0){cur--;render()}}
function finish(){if(revealing||scoreCur())return;for(let i=0;i<order.length;i++){if(!scored[i]&&answers[i]===-1){scored[i]=true;wrong.push(order[i])}
 else{cur=i;if(scoreCur())return}}const pass=wrong.length<=MAX_WRONG;
 document.getElementById('rverdict').textContent=pass?'PASSED':'RESTART NEEDED';document.getElementById('rverdict').className='big '+(pass?'pass':'fail');
 document.getElementById('rscore').textContent=(order.length-wrong.length)+' correct / '+wrong.length+' wrong (limit '+MAX_WRONG+')';show('result')}
function showWrong(){const st=loadStats(),list=document.getElementById('studylist');list.innerHTML='';let n=0;
 BANK.forEach(q=>{if(st[q.id]&&st[q.id].wrong){n++;const d=document.createElement('div');d.className='wrongitem';
 const b=document.createElement('b');b.textContent=q.q;const c=document.createElement('div');c.className='ca';c.textContent='Correct: '+q.o[q.c];
 const e=document.createElement('div');e.className='ex';e.textContent=q.e;d.append(b,c,e);list.appendChild(d)}});
 document.getElementById('studyN').textContent=n+' to study';if(!n)list.innerHTML='<div class="qbox">No missed questions yet. Great job!</div>';show('study')}
function resetAll(){if(confirm('Erase all progress and missed-question memory?')){localStorage.removeItem(KEY);goHome()}}
function show(id){['home','quiz','result','study'].forEach(x=>document.getElementById(x).classList.add('hidden'));
 document.getElementById(id).classList.remove('hidden');window.scrollTo(0,0)}
function goHome(){show('home')}
const STATIONS=__STATIONS__;const RKEY='atl_radio';const radio=document.getElementById('radio');
let rs={i:0,v:__RVOL__},rUrl=0,rOn=false;try{const s=JSON.parse(localStorage.getItem(RKEY));if(s&&s.i>=0&&s.i<STATIONS.length)rs.i=s.i;if(s&&s.v>=0&&s.v<=100)rs.v=s.v}catch(e){}
function rSave(){localStorage.setItem(RKEY,JSON.stringify(rs))}
function rSay(t){document.getElementById('rStatus').textContent=t}
function rLoad(){radio.src=STATIONS[rs.i].u[rUrl];if(rOn){rSay('Connecting to '+STATIONS[rs.i].n+'...');radio.play().catch(()=>{})}}
function rPick(i){rs.i=(i+STATIONS.length)%STATIONS.length;rUrl=0;document.getElementById('rSel').value=rs.i;rSave();rLoad()}
function rToggle(){rOn=!rOn;document.getElementById('rPlay').textContent=rOn?'Stop':'Play';
 if(rOn){rLoad()}else{radio.pause();radio.removeAttribute('src');radio.load();rSay('Stopped')}}
radio.addEventListener('playing',()=>rSay('Playing '+STATIONS[rs.i].n+' - '+STATIONS[rs.i].g));
radio.addEventListener('waiting',()=>rOn&&rSay('Buffering...'));
radio.addEventListener('error',()=>{if(!rOn||!radio.getAttribute('src'))return;if(rUrl+1<STATIONS[rs.i].u.length){rUrl++;rLoad();return}
 rOn=false;document.getElementById('rPlay').textContent='Play';rSay(STATIONS[rs.i].n+' is offline - try another station')});
(function(){const sel=document.getElementById('rSel');STATIONS.forEach((s,i)=>{const o=document.createElement('option');o.value=i;o.textContent=s.n+' ('+s.d+')';sel.appendChild(o)});
 sel.value=rs.i;sel.onchange=()=>rPick(+sel.value);const vol=document.getElementById('rVol');vol.value=rs.v;radio.volume=rs.v/100;
 vol.oninput=()=>{rs.v=+vol.value;radio.volume=rs.v/100;rSave()};rSay(STATIONS[rs.i].g)})();
</script>
</body></html>
"""


def bank_json(bank: list[dict]) -> str:
    compact = [{"id": q["id"], "q": q["question"], "o": q["options"], "c": q["correct"], "e": q["explanation"],
                "ch": q["chapter"]} for q in bank]
    return json.dumps(compact, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def render_html(bank: list[dict]) -> str:
    return (TEMPLATE.replace("__BANK__", bank_json(bank)).replace("__MAX_WRONG__", str(MAX_WRONG)).replace("__REVEAL_MS__", str(REVEAL_SECONDS * 1000))
            .replace("__STATIONS__", stations_json()).replace("__RVOL__", str(DEFAULT_VOLUME))
            .replace("__TOTAL__", str(len(bank))).replace("__LIMIT1__", str(MAX_WRONG + 1)))


def write_index(path: Path) -> Path:
    path.write_text(render_html(build_bank()), encoding="utf-8")
    return path


if __name__ == "__main__":
    out = write_index(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "index.html")
    print(f"wrote {out}")
