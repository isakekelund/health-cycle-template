#!/usr/bin/env python3
"""Build the client version of Health Cycle from Isak's own app.

    python3 build_from_main.py [path/to/health-cycle/index.html]

Reads the personal app (default: ../health-cycle/index.html) and writes
./index.html with the client-specific parts layered on top:

  * on-device storage instead of Isak's Firebase account
  * generic starter habits and workouts
  * a Scoring settings page: tracked days, workout-every-day, how the miss
    penalty starts / grows / caps, and the date misses start counting from
  * welcome tour, example day, "add to home screen" guide, one-time tips
  * one-time repair of data saved by older client versions

Every replacement must match exactly once, so if the personal app changes
shape the build stops with a clear error instead of producing a broken file.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "health-cycle" / "index.html"
OUT = HERE / "index.html"

s = SRC.read_text()


def r(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit(f"build: expected {count} match(es), found {n}:\n{old[:200]}")
    s = s.replace(old, new)


def rx(pattern, new):
    global s
    m = list(re.finditer(pattern, s, re.S))
    if len(m) != 1:
        sys.exit(f"build: expected 1 regex match, found {len(m)}: {pattern[:120]}")
    s = s[: m[0].start()] + new + s[m[0].end():]


# ── 1. Storage: on-device instead of Firebase ─────────────────────────────
rx(
    r"import \{initializeApp\}.*?const UID=TEST_UID\|\|'isak';\n",
    r"""// ── ON-DEVICE DATA LAYER ──
// The client version runs entirely in the browser: no server, no account.
// Every path is stored under its own key ("hcdata:users/local/months/…"), and
// reads assemble a parent path from whatever children were written beneath it,
// the way a real tree database would.
const HC_PREFIX='hcdata:';
function ref(_db, path){ return path; }
// Data only lives on this device, so a listener just receives the stored value once.
function onValue(path,cb){ get(path).then(cb); return ()=>{}; }
function hcKeys(){
  const out=[];
  try{ for(let i=0;i<window.localStorage.length;i++){ const k=window.localStorage.key(i); if(k&&k.startsWith(HC_PREFIX)) out.push(k.slice(HC_PREFIX.length)); } }catch{}
  return out;
}
function hcRead(path){ const raw=localStorage.getItem(HC_PREFIX+path); return raw===null?undefined:JSON.parse(raw); }
function hcGet(path){
  // A value stored at an ancestor (e.g. a whole month object) may contain this path.
  let val;
  const parts=path.split('/');
  for(let i=1;i<parts.length;i++){
    let v=hcRead(parts.slice(0,i).join('/'));
    if(v===undefined) continue;
    for(const p of parts.slice(i)){ v=(v&&typeof v==='object')?v[p]:undefined; }
    if(v!==undefined) val=v;
  }
  const own=hcRead(path);
  if(own!==undefined) val=own;
  // Children written separately (e.g. days/2026-10-01) override and extend.
  const pre=path+'/';
  hcKeys().filter(k=>k.startsWith(pre)).sort((a,b)=>a.length-b.length).forEach(k=>{
    const rest=k.slice(pre.length).split('/');
    if(!val||typeof val!=='object'||Array.isArray(val)) val=(val&&typeof val==='object')?{...val}:{};
    let node=val;
    rest.slice(0,-1).forEach(p=>{ if(!node[p]||typeof node[p]!=='object') node[p]={}; node=node[p]; });
    node[rest[rest.length-1]]=hcRead(k);
  });
  return val;
}
function get(path){
  return Promise.resolve().then(()=>{
    const val=hcGet(path);
    return val===undefined||val===null?{exists:()=>false,val:()=>null}:{exists:()=>true,val:()=>val};
  });
}
function set(path, value){
  return Promise.resolve().then(()=>{
    // Replacing a node replaces its whole subtree.
    hcKeys().filter(k=>k===path||k.startsWith(path+'/')).forEach(k=>localStorage.removeItem(HC_PREFIX+k));
    if(value!==null&&value!==undefined) localStorage.setItem(HC_PREFIX+path, JSON.stringify(value));
  });
}
const db=null;
const TEST_UID=null;
const UID='local';
""",
)
# The safe-localStorage shim is declared after the data layer; hoist it above.
rx(r"\n// Some contexts \(opening the file directly.*?\n\}\)\(\);\n", "\n")
r("// ── ON-DEVICE DATA LAYER ──", r"""// Some contexts (private browsing, strict storage settings) throw on any
// localStorage access. Fall back to an in-memory store so startup never hangs.
const localStorage = (() => {
  try {
    window.localStorage.setItem('__hc_probe__','1');
    window.localStorage.removeItem('__hc_probe__');
    return window.localStorage;
  } catch {
    const mem = new Map();
    return {
      getItem: k => mem.has(k) ? mem.get(k) : null,
      setItem: (k,v) => { mem.set(k, String(v)); },
      removeItem: k => { mem.delete(k); },
    };
  }
})();

// ── ON-DEVICE DATA LAYER ──""")

# ── 2. Generic starter habits and workouts ──────────────────────────────
rx(r"const DEFAULT_HABITS=\[.*?\n\];\n", """const DEFAULT_HABITS=[
  {id:'h_m1',name:'Drink a glass of water',group:'morning'},
  {id:'h_m2',name:'5 minutes of stretching',group:'morning'},
  {id:'h_m3',name:'Plan the day',group:'morning'},
  {id:'h_m4',name:'Meditate',group:'morning'},
  {id:'h_m12',name:'Workout',group:'morning'},
  {id:'h_e1',name:'Read for 15 minutes',group:'evening'},
  {id:'h_e2',name:'Journal',group:'evening'},
  {id:'h_e3',name:'No screens before bed',group:'evening'},
  {id:'h_g1',name:'Eat a healthy meal',group:'general'},
  {id:'h_g2',name:'Take a walk',group:'general'},
  {id:'h_g3',name:'Limit social media',group:'general'},
];
""")
rx(r"const DEFAULT_QUESTIONS=\[.*?\n\];\n", """const DEFAULT_QUESTIONS=[
  {id:'q1',text:'One thing you are grateful for?'},
  {id:'q2',text:'What did you do well today?'},
];
""")
rx(r"const WP_DEFAULT_CYCLE_SUMMER = \[.*?const WP_DEFAULT_CARDIO_WINTER = [^\n]*\n", """const WP_DEFAULT_CYCLE_WINTER = [
  {id:1,name:'Workout',group:'gym'},{id:2,name:'Cardio',group:'cardio'},
  {id:3,name:'Workout',group:'gym'},{id:4,name:'Cardio',group:'cardio'},
];
const WP_DEFAULT_CYCLE_SUMMER = WP_DEFAULT_CYCLE_WINTER;
const WP_DEFAULT_SEL_WINTER = {1:'Full body',2:'Steady state',3:'Full body',4:'Steady state'};
const WP_DEFAULT_SEL_SUMMER = {1:'Outdoor',2:'Run',3:'Outdoor',4:'Run'};
const WP_DEFAULT_GYM_WINTER = [
  {name:'Full body',blocks:[{type:'label',text:'Warm-up'},{type:'single',text:'5 minutes light cardio'},{type:'label',text:'Supersets'},{type:'pair',a:'Squats',b:'Push-ups'},{type:'pair',a:'Rows',b:'Lunges'},{type:'pair',a:'Plank',b:'Glute bridge'},{type:'label',text:'Finisher'},{type:'single',text:'Stretch & cool down'}]},
];
const WP_DEFAULT_GYM_SUMMER = [
  {name:'Outdoor',blocks:[{type:'label',text:'Warm-up'},{type:'single',text:'Light jog or brisk walk'},{type:'label',text:'Supersets'},{type:'pair',a:'Push-ups',b:'Bodyweight squats'},{type:'pair',a:'Lunges',b:'Plank'},{type:'label',text:'Finisher'},{type:'single',text:'Stretch outdoors'}]},
];
const WP_DEFAULT_CARDIO_SUMMER = [
  {name:'Run',options:['Outdoor run','Hike','Beach walk','Bike ride','Swim']},
];
const WP_DEFAULT_CARDIO_WINTER = [
  {name:'Steady state',options:['Running','Cycling','Swimming','Walking','Rowing']},
];
""")
# Clients have stored workout state at version 4; keep it so it isn't wiped.
r("const WP_VERSION = '5';", "const WP_VERSION = '4';")
# Isak-specific preset migration has nothing to do for clients.
r("  wpMigratePresets();\n", "")
rx(r"\n// One-way fixes for presets already saved.*?\n\}\n", "\n")

# ── 3. Configurable scoring ──────────────────────────────────────────────
r(
    """function isTrackingDay(d){ const dow=d.getDay(); return dow>=1&&dow<=4; }
// The workout is tracked every day of the week; everything else Mon–Thu only.
const WORKOUT_ID='h_m12';
function isTrackedFor(habitId,d){ return habitId===WORKOUT_ID || isTrackingDay(d); }""",
    """// Scoring rules, editable in Settings → Scoring. Defaults mirror the original app.
const SCORING_DEFAULTS={days:[1,2,3,4],workoutEveryDay:true,start:1,growth:'linear',cap:0};
let SCORING={...SCORING_DEFAULTS};
function isTrackingDay(d){ return SCORING.days.includes(d.getDay()); }
const WORKOUT_ID='h_m12';
function isTrackedFor(habitId,d){ return (habitId===WORKOUT_ID&&SCORING.workoutEveryDay) || isTrackingDay(d); }
const DAY_SHORT=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const WEEK_ORDER=[1,2,3,4,5,6,0];
function trackedDaysText(){
  if(SCORING.days.length===7) return 'every day';
  const on=WEEK_ORDER.filter(d=>SCORING.days.includes(d));
  // Collapse runs like Mon–Thu
  const runs=[];let run=[on[0]];
  for(let i=1;i<on.length;i++){ if(WEEK_ORDER.indexOf(on[i])===WEEK_ORDER.indexOf(on[i-1])+1) run.push(on[i]); else {runs.push(run);run=[on[i]];} }
  runs.push(run);
  return runs.map(r=>r.length>2?`${DAY_SHORT[r[0]]}–${DAY_SHORT[r[r.length-1]]}`:r.map(d=>DAY_SHORT[d]).join(', ')).join(', ');
}
function weeklyGoal(){ return SCORING.days.length; }
function penaltyFor(streak){
  const b=SCORING.start;
  let p=SCORING.growth==='flat'?b:SCORING.growth==='double'?b*2**streak:b*(streak+1);
  return SCORING.cap>0?Math.min(p,SCORING.cap):p;
}
function penaltySequenceText(n=4){
  const seq=[];for(let i=0;i<n;i++) seq.push('−'+penaltyFor(i));
  const capped=SCORING.cap>0&&penaltyFor(n)<=SCORING.cap&&penaltyFor(n)===penaltyFor(n-1);
  return seq.join(', ')+(SCORING.growth==='flat'||capped?'':SCORING.cap>0?` … up to −${SCORING.cap}`:' … with no limit');
}
function saveScoring(){
  fbSet('settings/scoring',SCORING);
  renderDailyScore(); renderHabits();
  if(activeTab==='overview') renderOverview();
}""",
)
r(
    """function getMissPenalty(habitId, date){
  return getMissStreakBefore(habitId, date) + 1;
}""",
    """function getMissPenalty(habitId, date){
  if(SCORING.growth==='flat') return penaltyFor(0);
  return penaltyFor(getMissStreakBefore(habitId, date));
}""",
)
r(
    "    document.getElementById('dailyMeta').innerHTML=`Rest day — only the workout is tracked${pts}`;",
    "    document.getElementById('dailyMeta').innerHTML=(dp.total?'Rest day — only the workout counts today':`Rest day — tracked days are ${trackedDaysText()}`)+pts;",
)
r(
    "<p class=\"card-note\">Habits are tracked Monday to Thursday.</p>",
    "<p class=\"card-note\">Habits are tracked ${trackedDaysText()}. Change this in Settings → Scoring.</p>",
)
r(
    "list.innerHTML='<section class=\"card\"><div class=\"card-head\" style=\"margin-bottom:6px\"><h2 class=\"card-title\">Rest day</h2></div><p class=\"card-note\">Habits are tracked ${trackedDaysText()}. Change this in Settings → Scoring.</p></section>';",
    "list.innerHTML=`<section class=\"card\"><div class=\"card-head\" style=\"margin-bottom:6px\"><h2 class=\"card-title\">Rest day</h2></div><p class=\"card-note\">Habits are tracked ${trackedDaysText()}. Change this in Settings → Scoring.</p></section>`;",
)
r(
    "<p class=\"card-note\">Other habits rest Fri–Sun, but the workout counts every day.</p>",
    "<p class=\"card-note\">${SCORING.workoutEveryDay?'Other habits rest today, but the workout counts every day.':'Other habits rest today, but you can still log a workout.'}</p>",
)
r(
    "  if(!isWorkoutHabit && (dow===0||dow>=5)){showToast('Only tracked Mon–Thu');return;}",
    "  if(!isWorkoutHabit && !isTrackingDay(currentDate)){showToast('Only tracked '+trackedDaysText());return;}",
)
# Weekly score: loop the whole week and use the tracked-day count as the goal.
r(
    """  for(let i=0;i<4;i++){
    const d=new Date(mon);d.setDate(d.getDate()+i);
    if(d>today)break;
    if(!isTrackingDay(d))continue;""",
    """  for(let i=0;i<7;i++){
    const d=new Date(mon);d.setDate(d.getDate()+i);
    if(d>today)break;
    if(!isTrackingDay(d))continue;""",
)
r(
    """  const scoreColor=score>=7?'var(--gold)':score>0?'var(--green-bright)':score<0?'var(--red-bright)':'var(--text)';
  const el=document.getElementById('scoreNumber');
  el.textContent=(score>0?'+'+score:score)+(score>=7?' 🏆':'');
  el.style.color=scoreColor;
  const pct=Math.min(100,Math.max(0,(score/4)*100));
  const fill=document.getElementById('weeklyFill');
  fill.style.width=pct+'%';
  fill.style.background=score>=7?'var(--gold)':score>0?'var(--green)':'var(--red)';
  document.getElementById('weeklyProgress').textContent=`${score} of 7 · Goal: +4 per week`;""",
    """  const goal=weeklyGoal();
  const scoreColor=score>=goal?'var(--gold)':score>0?'var(--green-bright)':score<0?'var(--red-bright)':'var(--text)';
  const el=document.getElementById('scoreNumber');
  el.textContent=(score>0?'+'+score:score)+(score>=goal?' 🏆':'');
  el.style.color=scoreColor;
  const pct=Math.min(100,Math.max(0,(score/goal)*100));
  const fill=document.getElementById('weeklyFill');
  fill.style.width=pct+'%';
  fill.style.background=score>=goal?'var(--gold)':score>0?'var(--green)':'var(--red)';
  document.getElementById('weeklyProgress').textContent=`${score} of ${goal} · Goal: +${goal} per week`;
  renderScoringExplain();""",
)
r(
    """  const dayNames=['Mon','Tue','Wed','Thu'];
  let graphData=[],totalDone=0,totalHabits=0,dLogged=0;
  document.getElementById('weekGrid').innerHTML=dayNames.map((label,i)=>{
    const d=new Date(mon);d.setDate(d.getDate()+i);""",
    """  const shown=WEEK_ORDER.map((dow,i)=>({dow,i})).filter(x=>SCORING.days.includes(x.dow));
  let graphData=[],totalDone=0,totalHabits=0,dLogged=0;
  document.getElementById('weekGrid').style.gridTemplateColumns=`repeat(${shown.length},1fr)`;
  document.getElementById('weekGrid').innerHTML=shown.map(({dow,i})=>{
    const label=DAY_SHORT[dow];
    const d=new Date(mon);d.setDate(d.getDate()+i);""",
)
r("  drawGraph('weekGraphContainer',graphData.slice(0,4),100);", "  drawGraph('weekGraphContainer',graphData,100);")
r(
    """  let reflHtml='';
  for(let i=0;i<4;i++){""",
    """  let reflHtml='';
  for(let i=0;i<7;i++){""",
)
rx(
    r"""        <div class="explain-body">\n          Each habit done = \+1 point\..*?</div>\n      </details>""",
    """        <div class="explain-body" id="scoringExplain"></div>
      </details>""",
)
r(
    "// GRAPH\n",
    """function renderScoringExplain(){
  const el=document.getElementById('scoringExplain'); if(!el) return;
  const grow={flat:'Every missed day costs the same',linear:'Each miss in a row costs more',double:'Each miss in a row doubles'}[SCORING.growth];
  el.innerHTML=`Each habit done = +1 point. ${grow}: ${penaltySequenceText()}${SCORING.growth==='flat'?'':' — until you do it again'}.<br>
    <strong style="color:var(--green-bright);font-weight:500">A day counts as positive</strong> when total points are above 0.<br>
    <strong style="color:var(--red-bright);font-weight:500">A day counts as negative</strong> when total points are 0 or below.<br>
    Tracked days: ${trackedDaysText()}${SCORING.workoutEveryDay&&SCORING.days.length<7?' (the workout counts every day)':''}. Goal: +${weeklyGoal()} per week.
    <br><a href="#" onclick="openSettings('scoring');return false" style="color:var(--gold)">Change scoring</a>`;
}

// GRAPH
""",
)

# Scoring settings page
r(
    """      <div id="sp-data" class="spage hidden">""",
    """      <div id="sp-scoring" class="spage hidden">
        <section class="card">
          <div class="card-head"><h2 class="card-title">Tracked days</h2></div>
          <p class="card-note" style="margin-bottom:10px">Habits only count on these days. The rest are rest days.</p>
          <div class="day-pill-row" id="scDays"></div>
          <label class="sc-check"><input type="checkbox" id="scWorkout" onchange="scSet('workoutEveryDay',this.checked)"> <span>Workout counts every day, rest days included</span></label>
        </section>
        <section class="card">
          <div class="card-head"><h2 class="card-title">Missed habits</h2></div>
          <div class="sc-field">
            <div class="sc-label">First miss costs</div>
            <div class="tabs sc-seg" id="scStart"></div>
          </div>
          <div class="sc-field">
            <div class="sc-label">Each extra day in a row</div>
            <div class="tabs sc-seg" id="scGrowth"></div>
          </div>
          <div class="sc-field">
            <div class="sc-label">Maximum penalty</div>
            <div class="tabs sc-seg" id="scCap"></div>
          </div>
          <div class="sc-preview" id="scPreview"></div>
        </section>
        <section class="card">
          <div class="card-head"><h2 class="card-title">Start counting misses from</h2></div>
          <p class="card-note" style="margin-bottom:10px">Missed days before this date are ignored. Handy after a holiday or when you're starting out.</p>
          <input class="input" type="date" id="scEscStart" onchange="setEscalationStart(this.value)" style="width:100%">
        </section>
        <section class="card flush">
          <div class="action-row">
            <div class="srow-main">
              <div class="srow-name">Restore defaults</div>
              <div class="srow-sub">Mon–Thu, workout every day, −1 growing by 1 each day with no limit.</div>
            </div>
            <button class="btn" onclick="scRestoreDefaults()">Restore</button>
          </div>
        </section>
      </div>

      <div id="sp-install" class="spage hidden">
        <section class="card">
          <div class="install-block">
            <div class="install-device">iPhone / iPad (Safari)</div>
            <ol class="install-steps">
              <li>Tap the <strong>Share</strong> button (square with an arrow)</li>
              <li>Scroll down and tap <strong>Add to Home Screen</strong></li>
              <li>Tap <strong>Add</strong> in the top right</li>
            </ol>
          </div>
          <div class="install-block">
            <div class="install-device">Android (Chrome)</div>
            <ol class="install-steps">
              <li>Tap the <strong>⋮</strong> menu in the top right</li>
              <li>Tap <strong>Add to Home screen</strong> or <strong>Install app</strong></li>
              <li>Confirm by tapping <strong>Add</strong></li>
            </ol>
          </div>
          <div class="install-block">
            <div class="install-device">Mac / Windows (Chrome)</div>
            <ol class="install-steps">
              <li>Click the install icon in the address bar (or the <strong>⋮</strong> menu)</li>
              <li>Select <strong>Install</strong></li>
            </ol>
          </div>
          <div class="install-note">Once added, it opens like a normal app. Your data stays on this device only.</div>
        </section>
      </div>

      <div id="sp-data" class="spage hidden">""",
)
r(
    "  months:'Month archive',data:'Scoring & data',why:'Why a habit tracker',",
    "  months:'Month archive',data:'Resets & data',why:'Why a habit tracker',\n  scoring:'Scoring',install:'Add to home screen',",
)
r(
    "    ['data','Scoring & data','Reset miss penalties or weekly score, export, clear data'],",
    """    ['scoring','Scoring',`${trackedDaysText()} · misses cost ${penaltySequenceText(3).replace(' … with no limit','…')}`],
    ['data','Resets & data','Reset miss penalties or weekly score, export, clear data'],
    ['install','Add to home screen','Use it like a normal app on your phone or computer'],""",
)
r(
    "  if(page==='data') renderDataPage();\n",
    "  if(page==='data') renderDataPage();\n  if(page==='scoring') renderScoringSettings();\n"
    "  if(page==='menu') showContextTip('settings','sp-menu','Everything is yours to change: habits, groups, the workout, and in <strong>Scoring</strong> which days count and how hard misses hit.');\n",
)
r(
    "function normGroup(h){",
    """function segHTML(id,options,current,key){
  document.getElementById(id).innerHTML=options.map(([v,label])=>
    `<button class="seg-btn${String(v)===String(current)?' active':''}" onclick="scSet('${key}',${typeof v==='string'?`'${v}'`:v})">${label}</button>`).join('');
}
function renderScoringSettings(){
  document.getElementById('scDays').innerHTML=WEEK_ORDER.map(d=>
    `<button class="day-pill${SCORING.days.includes(d)?' on':''}" onclick="scToggleDay(${d})">${DAY_SHORT[d]}</button>`).join('');
  document.getElementById('scWorkout').checked=SCORING.workoutEveryDay;
  segHTML('scStart',[[1,'−1'],[2,'−2'],[3,'−3'],[5,'−5']],SCORING.start,'start');
  segHTML('scGrowth',[['flat','Same'],['linear','Adds up'],['double','Doubles']],SCORING.growth,'growth');
  segHTML('scCap',[[0,'None'],[5,'5'],[7,'7'],[10,'10'],[20,'20']],SCORING.cap,'cap');
  document.getElementById('scPreview').innerHTML=`Missing a habit several days in a row: <strong>${penaltySequenceText(5)}</strong>`;
  const d=ESCALATION_START;
  document.getElementById('scEscStart').value=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
window.scSet=function(key,val){ SCORING[key]=val; saveScoring(); renderScoringSettings(); };
window.scToggleDay=function(d){
  const on=SCORING.days.includes(d);
  if(on&&SCORING.days.length<=1){ showToast('Keep at least one tracked day'); return; }
  SCORING.days=on?SCORING.days.filter(x=>x!==d):[...SCORING.days,d];
  saveScoring(); renderScoringSettings();
};
window.scRestoreDefaults=function(){ SCORING={...SCORING_DEFAULTS,days:[...SCORING_DEFAULTS.days]}; saveScoring(); renderScoringSettings(); showToast('Scoring defaults restored'); };
window.setEscalationStart=function(v){
  if(!v) return;
  const d=new Date(v+'T00:00:00'); if(isNaN(d)) return;
  ESCALATION_START=d;
  localStorage.setItem('hc-escalation-start',d.toISOString());
  fbSet('escalationStart',d.toISOString());
  renderDailyScore(); renderHabits();
  showToast('Misses now count from '+d.getDate()+' '+MONTHS_SHORT[d.getMonth()]);
};

function normGroup(h){""",
)

# Load scoring (and older clients' tracked-days setting) on startup.
r(
    "      if(s.groupLabels){localStorage.setItem('hc-group-labels',JSON.stringify(s.groupLabels));}\n    }",
    """      if(s.groupLabels){localStorage.setItem('hc-group-labels',JSON.stringify(s.groupLabels));}
      if(s.scoring) SCORING={...SCORING_DEFAULTS,...s.scoring};
    }
    if(!settingsSnap.exists()||!settingsSnap.val().scoring){
      // Older client versions kept tracked days in their own key.
      const legacy=JSON.parse(localStorage.getItem('hc-tracking-days')||'null');
      if(legacy&&legacy.length) SCORING.days=legacy;
    }""",
)

# ── 4. Onboarding: welcome tour, example day, tips ──────────────────────
r(
    "  renderDailyScore();\n  if(activeTab==='overview') renderOverview();\n}",
    "  renderDailyScore();\n  if(activeTab==='overview') renderOverview();\n"
    "  showContextTip('today','tab-today','This is your checklist for today. Tap a habit to check it off, and tap <strong>Workout</strong> to open the built-in workout tracker.');\n}",
)
r(
    "    if(!cur) promptNewMonth();\n  }catch(e){",
    "    if(!localStorage.getItem('hc-welcomed')) document.getElementById('welcomeModal').classList.remove('hidden');\n"
    "    else if(!cur) promptNewMonth();\n"
    "  }catch(e){",
)
r(
    "  if(name==='overview'){ flushReflection(); renderOverview(); }\n};",
    "  if(name==='overview'){ flushReflection(); renderOverview(); showContextTip('overview','tab-overview','Your week and month at a glance. Tap any day to jump to it, and open <strong>How scoring works</strong> to see the rules.'); }\n};\n"
    """
// One-time dismissible tips, shown the first time a screen is visited.
function showContextTip(key, containerId, message){
  if(localStorage.getItem('hc-tip-'+key)) return;
  const c=document.getElementById(containerId);
  if(!c||c.querySelector('[data-tipkey="'+key+'"]')) return;
  const t=document.createElement('div');
  t.className='context-tip'; t.dataset.tipkey=key;
  t.innerHTML=`<div class="context-tip-icon">💡</div><div class="context-tip-text">${message}</div><button class="context-tip-close" aria-label="Dismiss" onclick="dismissTip('${key}',this)">✕</button>`;
  c.insertBefore(t,c.firstChild);
}
function tipHtml(key,message){
  if(localStorage.getItem('hc-tip-'+key)) return '';
  return `<div class="context-tip" data-tipkey="${key}"><div class="context-tip-icon">💡</div><div class="context-tip-text">${message}</div><button class="context-tip-close" aria-label="Dismiss" onclick="dismissTip('${key}',this)">✕</button></div>`;
}
window.dismissTip=function(key,btn){ localStorage.setItem('hc-tip-'+key,'1'); const el=btn.closest('.context-tip'); if(el) el.remove(); };

window.closeWelcome=function(){
  document.getElementById('welcomeModal').classList.add('hidden');
  localStorage.setItem('hc-welcomed','1');
  if(!findCurrentMonthId()) promptNewMonth();
};
// A one-off example month with a half-finished day, so a first-time user can
// see checked habits, streaks and a saved reflection before starting their own.
window.loadExampleDay=async function(){
  document.getElementById('welcomeModal').classList.add('hidden');
  localStorage.setItem('hc-welcomed','1');
  const id='example-'+Date.now();
  const done={}; DEFAULT_HABITS.forEach((h,i)=>{ if(i%2===0) done[h.id]=true; });
  monthList.push({id,name:'Example month',created:`Created ${today.getDate()} ${MONTHS_SHORT[today.getMonth()]} ${today.getFullYear()}`,logged:1});
  await fbSet(`months/${id}/habits`,DEFAULT_HABITS);
  await fbSet(`months/${id}/questions`,DEFAULT_QUESTIONS);
  await fbSet(`months/${id}/days/${dk(today)}`,{habits:done,reflection:{[DEFAULT_QUESTIONS[0].id]:'This is what a saved reflection looks like.'}});
  await fbSet('monthList',monthList);
  await openArchivedMonth(id);
  showToast('Example month — remove it anytime in Settings → Month archive');
};""",
)
r(
    "  let html = `\n    <div class=\"wp-season-toggle\">",
    "  let html = `\n    ${tipHtml('workout','Your built-in workout tracker. Switch between Summer and Winter plans, tap a session to pick a workout, and tick the circle when it\\'s done. Edit the plans in Settings → Workout.')}\n    <div class=\"wp-season-toggle\">",
)
r(
    '<div class="toast" id="toast"></div>',
    """<!-- WELCOME -->
<div id="welcomeModal" class="modal-overlay hidden">
  <div class="modal" style="max-width:400px">
    <div class="modal-title">Welcome to Health Cycle</div>
    <div class="welcome-body">
      A quick tour before you start:
      <ul>
        <li><strong>Today</strong> is your daily checklist. Tap a habit to check it off.</li>
        <li><strong>Overview</strong> shows your week and month, your score and the habits you miss most.</li>
        <li><strong>Missed habits cost points</strong>, and the cost grows the longer you skip them. Only doing them stops it.</li>
        <li><strong>Workout</strong> opens a built-in tracker with Summer and Winter plans.</li>
        <li><strong>⚙ Settings</strong> lets you change everything: habits, groups, the workout, and in <strong>Scoring</strong> which days count and how hard misses hit.</li>
      </ul>
      Your data is stored on this device only.
    </div>
    <div class="modal-btns">
      <button class="btn" onclick="loadExampleDay()">See an example</button>
      <button class="btn btn-primary" onclick="closeWelcome()">Get started</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>""",
)

# Client-only CSS
r(
    "</style>",
    """.context-tip{display:flex;align-items:flex-start;gap:10px;font-family:'Outfit',sans-serif;letter-spacing:0;text-transform:none;background:var(--gold-bg);border:1px solid var(--gold-dim);border-radius:12px;padding:12px 14px;margin-bottom:12px;animation:tipIn .3s ease}
.context-tip-icon{font-size:16px;flex-shrink:0;line-height:1.4}
.context-tip-text{flex:1;font-size:13px;color:var(--text-mid);line-height:1.55}
.context-tip-close{background:none;border:none;color:var(--gold-dim);cursor:pointer;font-size:13px;padding:0 0 0 4px;flex-shrink:0}
@keyframes tipIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}
.welcome-body{font-size:13px;color:var(--text-mid);line-height:1.65;margin-bottom:16px}
.welcome-body ul{margin:10px 0 12px;padding-left:18px}.welcome-body li{margin-bottom:7px}
.welcome-body strong{color:var(--text);font-weight:500}
.day-pill-row{display:flex;gap:6px}
.day-pill{flex:1;min-width:0;padding:11px 0;text-align:center;background:var(--surface);border:1px solid var(--border);border-radius:9px;font-size:12px;color:var(--text-dim);cursor:pointer;font-family:inherit;transition:all .15s}
.day-pill.on{background:var(--green-bg);border-color:var(--green);color:var(--green-bright);font-weight:500}
.sc-check{display:flex;align-items:center;gap:8px;margin-top:12px;font-size:13px;color:var(--text-mid);cursor:pointer}
.sc-check input{width:16px;height:16px;accent-color:var(--green)}
.sc-field{margin-bottom:12px}
.sc-label{font-size:12px;color:var(--text-dim);margin-bottom:6px}
.sc-seg{margin:0}
.sc-preview{font-size:13px;color:var(--text-mid);background:var(--surface2);border-radius:9px;padding:10px 12px;line-height:1.5}
.sc-preview strong{color:var(--red-bright);font-weight:500}
.install-block{margin-bottom:14px}
.install-device{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--gold-dim);margin-bottom:6px;font-weight:500}
.install-steps{margin:0;padding-left:18px;font-size:13px;color:var(--text-mid);line-height:1.8}
.install-note{font-size:12px;color:var(--text-dim);padding-top:10px;border-top:1px solid var(--border)}
</style>""",
)

# ── 5. One-time repair of data saved by older client versions ───────────
# Older builds saved each day under the UTC date, which is the previous day
# for anyone east of UTC (all of Europe). Move those entries to the right day.
r(
    "async function loadApp(){\n  try{",
    """async function repairOldDayKeys(){
  if(localStorage.getItem('hc-daykeys-fixed')) return;
  const ml=(await get(ref(db,`users/${UID}/monthList`))).val()||[];
  for(const m of ml){
    const ds=(await get(ref(db,`users/${UID}/months/${m.id}/days`))).val();
    if(!ds) continue;
    const fixed={};
    Object.keys(ds).sort().forEach(k=>{
      const [y,mo,da]=k.split('-').map(Number);
      const next=new Date(y,mo-1,da+1);
      const nk=next.getTimezoneOffset()<0?dk(next):k;
      if(fixed[nk]){ // two entries landed on one day: keep every checked habit
        const a=fixed[nk],b=ds[k];
        fixed[nk]={habits:{...(a.habits||{}),...(b.habits||{})},reflection:{...(a.reflection||{}),...(b.reflection||{})}};
      } else fixed[nk]=ds[k];
    });
    await fbSet(`months/${m.id}/days`,fixed);
  }
  localStorage.setItem('hc-daykeys-fixed','1');
}

async function loadApp(){
  try{
    await repairOldDayKeys();""",
)

# Marker so the built file says where it came from.
r("<head>", "<head>\n<!-- Client version — generated by build_from_main.py from the personal app. Edit the build script, not this file. -->", 1)

OUT.write_text(s)
print(f"built {OUT} ({len(s):,} bytes) from {SRC}")
