"""
HABIT UP - the whole app in ONE file (backend + website + app files).

Run it:
    pip install flask
    python habitup.py
Open http://localhost:5000 . Friends on the same Wi-Fi open
http://YOUR-COMPUTER-IP:5000 . Data is saved in habitup.db next to this file.
To host it online, upload this file to a Python host (PythonAnywhere, Render).
"""
import json, os, secrets, sqlite3
import base64
from flask import Flask, Response, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

HERE = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(HERE, "habitup.db")
app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 1_000_000


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_FILE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


def init():
    c = sqlite3.connect(DB_FILE)
    c.execute("create table if not exists users(name_key text primary key, name text, pw text, data text, grp text, streak int, points int)")
    c.execute("create table if not exists sessions(token text primary key, name_key text)")
    c.commit()
    c.close()


def start_session(key, name, data):
    token = secrets.token_urlsafe(24)
    db().execute("insert into sessions values(?,?)", (token, key))
    db().commit()
    return jsonify(token=token, name=name, data=data)


def me():
    token = (request.headers.get("Authorization") or "")[7:]
    row = db().execute("select u.* from sessions s join users u on u.name_key=s.name_key where s.token=?", (token,)).fetchone()
    return row


@app.get("/")
def home():
    return serve("index.html")


@app.get("/<name>")
def files(name):
    return serve(name)


def serve(name):
    item = ASSETS.get(name)
    if not item:
        return "Not found", 404
    return Response(item[0], mimetype=item[1])


@app.post("/api/signup")
def signup():
    j = request.get_json(silent=True) or {}
    name = (j.get("name") or "").strip()[:20]
    pw = j.get("password") or ""
    if not name or len(pw) < 4:
        return jsonify(error="Enter a name and a password of at least 4 characters."), 400
    key = name.lower()
    if db().execute("select 1 from users where name_key=?", (key,)).fetchone():
        return jsonify(error="That name is already taken. Please choose a different name."), 409
    db().execute("insert into users values(?,?,?,?,?,?,?)", (key, name, generate_password_hash(pw), "{}", "", 0, 0))
    db().commit()
    return start_session(key, name, {})


@app.post("/api/login")
def login():
    j = request.get_json(silent=True) or {}
    key = (j.get("name") or "").strip().lower()
    row = db().execute("select * from users where name_key=?", (key,)).fetchone()
    if not row or not check_password_hash(row["pw"], j.get("password") or ""):
        return jsonify(error="Wrong name or password."), 401
    return start_session(key, row["name"], json.loads(row["data"]))


@app.get("/api/me")
def whoami():
    u = me()
    if not u:
        return jsonify(error="Please log in again."), 401
    return jsonify(name=u["name"], data=json.loads(u["data"]))


@app.post("/api/save")
def save():
    u = me()
    if not u:
        return jsonify(error="Please log in again."), 401
    j = request.get_json(silent=True) or {}
    data = j.get("data") or {}
    st = j.get("stats") or {}
    db().execute("update users set data=?, grp=?, streak=?, points=? where name_key=?",
                 (json.dumps(data), str(data.get("group") or "")[:20], int(st.get("s") or 0), int(st.get("p") or 0), u["name_key"]))
    db().commit()
    return jsonify(ok=True)


@app.get("/api/group")
def group():
    if not me():
        return jsonify(error="Please log in again."), 401
    code = (request.args.get("code") or "")[:20]
    rows = db().execute("select name, streak, points from users where grp=? order by points desc limit 50", (code,)).fetchall()
    return jsonify(members=[{"n": r["name"], "s": r["streak"], "p": r["points"]} for r in rows])


# ---------------------------------------------------------------
# The website files are stored inside this one file.
# ---------------------------------------------------------------
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#c8962c">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Habit Up">
<link rel="apple-touch-icon" href="icon-192.png">
<title>Habit Up - habit streaks with friends</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{--desk:#dfe3ee;--paper:#fff;--ink:#1d2433;--mute:#6b7388;--line:#bfc5d6;--gold:#c8962c;--soft:#f1f3f9;--sh:0 14px 34px rgba(30,40,90,.16);box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--desk:#10142b;--paper:#1c2244;--ink:#eef0ff;--mute:#a3a9cc;--line:#3a4274;--soft:#262d5a;--sh:0 14px 34px rgba(0,0,0,.4)}}
:root[data-theme="dark"]{--desk:#10142b;--paper:#1c2244;--ink:#eef0ff;--mute:#a3a9cc;--line:#3a4274;--soft:#262d5a;--sh:0 14px 34px rgba(0,0,0,.4)}
*,*::before,*::after{box-sizing:inherit}
body{margin:0;background:var(--desk);color:var(--ink);font:16px/1.5 "DM Sans",system-ui,sans-serif;min-height:100vh}
button,input,textarea{font:inherit;color:inherit}
button{cursor:pointer}
:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
.wrap{max-width:1100px;margin:0 auto;padding:18px 14px 60px}
.btn{background:var(--ink);color:var(--paper);border:0;border-radius:10px;padding:10px 16px;font-weight:700}
.btn.ghost{background:var(--soft);color:var(--ink)}
.btn.gold{background:var(--gold);color:#fff}
input.f{background:var(--soft);border:2px solid transparent;border-radius:10px;padding:10px 12px;min-width:0}
input.f:focus{border-color:var(--gold);outline:none}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.row input.f{flex:1 1 170px}
.top{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:14px}
.logo{font:700 1.9rem Caveat,cursive;display:flex;gap:8px;align-items:center}
.logo b{width:30px;height:30px;border-radius:9px;background:var(--gold);display:grid;place-items:center;font-size:1rem}
#login{min-height:80vh;display:grid;align-content:center;gap:18px;max-width:560px;margin:0 auto}
#login h1{font:700 clamp(3rem,11vw,5rem) Caveat,cursive;line-height:1;margin:0}
#login p{color:var(--mute);margin:0;max-width:44ch}
.lb0{background:var(--paper);padding:12px;border-radius:16px;box-shadow:var(--sh)}
.pills{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
.pill{background:var(--paper);border-radius:14px;padding:8px 14px;box-shadow:var(--sh);font-weight:700}
.pill small{display:block;color:var(--mute);font-weight:400;font-size:.78rem}
.sp{display:flex;justify-content:space-between;padding:0 12px;margin-bottom:-14px;position:relative;z-index:2}
.sp i{width:9px;height:26px;border:3px solid var(--gold);border-radius:6px;background:var(--desk)}
.paper{background:var(--paper);border-radius:6px;box-shadow:var(--sh);padding:30px 18px 22px;overflow-x:auto}
.in{min-width:820px}
.ph{display:flex;justify-content:space-between;align-items:flex-end;gap:10px;margin-bottom:10px}
.ph h1{margin:0;font-size:1.6rem;letter-spacing:.02em;font-weight:700}
.mo{display:flex;align-items:center;gap:6px;font-weight:500}
.mo b{font:700 1.6rem Caveat,cursive;border-bottom:2px solid var(--line);padding:0 8px;min-width:150px;text-align:center}
.mo button{background:var(--soft);border:0;border-radius:8px;width:30px;height:30px;font-weight:700}
.lab{font-size:.75rem;color:var(--mute);margin:12px 0 2px;font-weight:700}
.gd{display:grid;grid-template-columns:170px repeat(31,minmax(14px,1fr)) 70px;align-items:center;gap:0 3px;min-height:28px}
.dn{font-size:.62rem;text-align:center;color:var(--mute)}
.hn{background:transparent;border:0;border-bottom:1.5px solid var(--line);font:600 1.15rem Caveat,cursive;padding:0 2px;width:100%;min-width:0}
.hn:focus{outline:none;border-bottom-color:var(--gold)}
.c{width:15px;height:15px;border-radius:50%;border:1.5px solid var(--cc);background:transparent;padding:0;justify-self:center;transition:transform .12s}
.c:active{transform:scale(.8)}
.c.on{background:var(--cc)}
.c:disabled{opacity:.3;cursor:default}
i.sx{display:block}
.sk{font-size:.78rem;font-weight:700;text-align:right;white-space:nowrap}
.del{background:none;border:0;color:var(--mute);padding:2px 4px;font-size:.8rem}
.del:hover{color:#e8504f}
.add{background:none;border:0;color:var(--mute);font-size:.82rem;padding:6px 0;font-weight:700}
.three{display:grid;grid-template-columns:1.1fr 1fr 1fr;gap:22px;margin-top:18px}
.gw{display:grid;grid-template-columns:1fr repeat(5,22px) 26px;gap:0 6px;align-items:center;min-height:28px}
.gm{display:grid;grid-template-columns:1fr 22px 26px;gap:0 6px;align-items:center;min-height:28px}
.gw .dn{font-size:.58rem}
textarea.nt{width:100%;height:130px;resize:none;border:0;background:repeating-linear-gradient(transparent 0 25px,var(--line) 25px 26px);font:600 1.15rem/26px Caveat,cursive;padding:0}
textarea.nt:focus{outline:none}
.card{background:var(--paper);border-radius:18px;padding:18px;box-shadow:var(--sh);margin-top:22px}
.card h2{margin:0 0 12px;font-size:1.2rem}
.charts{display:flex;gap:24px;align-items:center;flex-wrap:wrap}.rc{display:grid;justify-items:center;gap:4px;text-align:center;font-weight:600;font-size:.85rem;max-width:110px}.rc.big{max-width:none;font-size:1rem}.rgrid{display:flex;gap:16px;flex-wrap:wrap;flex:1 1 280px}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.badge{border-radius:999px;padding:6px 12px;font-weight:700;font-size:.85rem;background:var(--soft);color:var(--mute);opacity:.7}
.badge.got{background:var(--gold);color:#fff;opacity:1}
.lb{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.lb li{display:grid;grid-template-columns:28px 38px 1fr auto;gap:10px;align-items:center;padding:9px 12px;border-radius:14px;background:var(--soft)}
.lb li.me{background:var(--gold);color:#fff}
.rk{font-weight:800;text-align:center}
.av{width:38px;height:38px;border-radius:50%;display:grid;place-items:center;color:#fff;font-weight:800}
.lb small{display:block;opacity:.8}
.note{color:var(--mute);font-size:.85rem;margin:12px 0 0}
input.code{font-size:.82rem;border:0;flex:1 1 200px;background:var(--soft);border-radius:10px;padding:9px 12px;min-width:0}
#toast{position:fixed;left:50%;bottom:calc(20px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);background:var(--ink);color:var(--paper);padding:10px 16px;border-radius:10px;font-weight:700;opacity:0;pointer-events:none;transition:opacity .2s}
#toast.show{opacity:1}
@media(max-width:820px){.three{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
</head>
<body>
<div class="wrap" id="app"></div>
<div id="toast" role="status"></div>
<script>
var KEY="chainlink:v1",S=null,mem=null,V={y:new Date().getFullYear(),m:new Date().getMonth()},
COLS=["#2ea77f","#5b5bd6","#e84e9a","#f08a24","#e6b800","#2f80ed","#9b51e0","#d63c3c"],
MN=["January","February","March","April","May","June","July","August","September","October","November","December"];
var API="",TOK=null,GM=[],PJ=null,mode="in",tmr=null;
function api(path,body,method){var o={method:method||"POST",headers:{"Content-Type":"application/json"}};if(TOK)o.headers.Authorization="Bearer "+TOK;if(body)o.body=JSON.stringify(body);return fetch(API+path,o).then(function(r){return r.json().then(function(j){if(!r.ok)throw new Error(j.error||"Something went wrong");return j})})}
function stats(){return{s:best(),p:points()}}
function load(){return null}
function save(){if(!S||!TOK)return;clearTimeout(tmr);tmr=setTimeout(function(){api("/api/save",{data:S,stats:stats()}).then(refreshGM).catch(function(){})},400)}
function refreshGM(){if(!S||!TOK)return;api("/api/group?code="+encodeURIComponent(S.group),null,"GET").then(function(j){var gm=j.members.filter(function(m){return m.n.toLowerCase()!==S.user.toLowerCase()});if(JSON.stringify(gm)!==JSON.stringify(GM)){GM=gm;if(!/INPUT|TEXTAREA/.test(document.activeElement.tagName))render()}}).catch(function(){})}
function msg(t){toast(t);var e=document.getElementById("err");if(e)e.textContent=t}
function seed(){S.habits=[{id:"h1",name:"Code for 2 hours",done:[]},{id:"h2",name:"Drink enough water",done:[]},{id:"h3",name:"Read 30 pages",done:[]}];S.weekly=[{id:"w1",name:"Clean the room",done:[]}];S.monthly=[{id:"m1",name:"Finish a project",done:[]}]}
function doLogin(){var n=document.getElementById("nm").value.trim(),pw=document.getElementById("pw").value;if(!n||!pw){toast("Enter your name and password");return}
  if(mode=="up"&&pw.length<4){msg("Password needs at least 4 characters");return}
  api(mode=="up"?"/api/signup":"/api/login",{name:n,password:pw}).then(function(j){TOK=j.token;try{localStorage.setItem("habitup:tok",TOK)}catch(e){}S=j.data||{};S.user=j.name;fix();if(!S.habits.length)seed();if(PJ)S.group=PJ;if(!S.group)S.group=code();fix();save();render();refreshGM()}).catch(function(e){msg(e.message==="Failed to fetch"?"Cannot reach the server. Is it running?":e.message)})}
function p2(n){return(n<10?"0":"")+n}
function ym(){return V.y+"-"+p2(V.m+1)}
function dk(d){return d.getFullYear()+"-"+p2(d.getMonth()+1)+"-"+p2(d.getDate())}
function ago(n){var d=new Date();d.setDate(d.getDate()-n);return d}
function esc(s){return String(s).replace(/[&<>"']/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
function streak(h){var set=new Set(h.done),n=0,i=0;if(!set.has(dk(ago(0))))i=1;while(set.has(dk(ago(i)))){n++;i++}return n}
function best(){return S.habits.reduce(function(m,h){return Math.max(m,streak(h))},0)}
function points(){return S.habits.reduce(function(p,h){return p+h.done.length*10+streak(h)*5},0)}
function toast(t){var e=document.getElementById("toast");e.textContent=t;e.className="show";clearTimeout(toast.t);toast.t=setTimeout(function(){e.className=""},2000)}
function code(){var c="ABCDEFGHJKLMNPQRSTUVWXYZ23456789",s="";for(var i=0;i<4;i++)s+=c[Math.floor(Math.random()*c.length)];return"HOSTEL-"+s}
function doCopy(t){function fb(){var x=document.createElement("textarea");x.value=t;x.style.cssText="position:fixed;opacity:0";document.body.appendChild(x);x.focus();x.select();var ok=false;try{ok=document.execCommand("copy")}catch(e){}document.body.removeChild(x);if(ok)toast("Invite link copied");else{var i=document.getElementById("il");if(i){i.focus();i.select()}toast("Press Ctrl+C to copy the selected link")}}try{navigator.clipboard.writeText(t).then(function(){toast("Invite link copied")},fb)}catch(e){fb()}}
function inviteLink(){var b="";try{if(/^https?:/.test(location.href))b=location.href.split("?")[0].split("#")[0]}catch(e){}if(!b)b="https://claude.ai/artifact/Ybpz2YDACVG8ZcQzFMxegB";return b+"?join="+S.group}
function shareInvite(){var u=inviteLink(),t="Join my group on Habit Up and build streaks with me!";if(navigator.share){navigator.share({title:"Habit Up",text:t,url:u}).catch(function(e){if(!e||e.name!=="AbortError")doCopy(u)})}else doCopy(u)}
function demoFriends(){return[]}
function avc(n){var s=0;for(var i=0;i<n.length;i++)s+=n.charCodeAt(i);return COLS[s%COLS.length]}
function fix(){S.friends=[];S.habits=S.habits||[];S.weekly=S.weekly||[];S.monthly=S.monthly||[];S.notes=S.notes||{};S.habits.forEach(function(h,i){h.color=h.color||COLS[i%COLS.length]});S.weekly.forEach(function(h,i){h.color=h.color||COLS[(i+3)%COLS.length]});S.monthly.forEach(function(h,i){h.color=h.color||COLS[(i+5)%COLS.length]})}
function nid(){return"h"+Date.now()+Math.floor(Math.random()*999)}

function render(){
  var a=document.getElementById("app");
  if(!S||!S.user){
    a.innerHTML='<div id="login"><div class="logo"><b>&#128279;</b>Habit Up</div><h1>Fill every circle.</h1><p>A monthly habit planner you tick off daily. Build streaks, earn badges and see how your hostel mates are doing.</p><div class="lb0"><div class="row" style="margin-bottom:10px"><button class="btn '+(mode=="in"?"":"ghost")+'" data-a="mode" data-m="in">Log in</button><button class="btn '+(mode=="up"?"":"ghost")+'" data-a="mode" data-m="up">Sign up</button></div><div class="row"><input class="f" id="nm" placeholder="Your name" maxlength="20" autocomplete="username" aria-label="Your name"><input class="f" id="pw" type="password" placeholder="Password" maxlength="40" autocomplete="'+(mode=="up"?"new-password":"current-password")+'" aria-label="Password"><button class="btn gold" data-a="login">'+(mode=="up"?"Create account":"Log in")+'</button></div><p id="err" role="alert" style="color:#e8504f;font-weight:700;margin:10px 0 0"></p></div><p>Every name has its own habits and password. Accounts are saved in this browser only.</p></div>';return}
  fix();
  var td=dk(ago(0)),dim=new Date(V.y,V.m+1,0).getDate(),k=ym(),b=best(),tot=S.habits.reduce(function(t,h){return t+h.done.length},0),h="";
  h+='<div class="top"><div class="logo"><b>&#128279;</b>Habit Up</div><div class="row"><span>Hi, '+esc(S.user)+'</span><button class="btn ghost" data-a="logout">Log out</button></div></div>';
  h+='<div class="sp" aria-hidden="true">';for(var i=0;i<46;i++)h+='<i></i>';h+='</div><section class="paper"><div class="in">';
  h+='<div class="ph"><h1>HABIT TRACKER</h1><div class="mo">MONTH:<button data-a="pm" aria-label="Previous month">&#8249;</button><b>'+MN[V.m]+' '+V.y+'</b><button data-a="nm2" aria-label="Next month">&#8250;</button></div></div>';
  h+='<div class="lab">DAILY</div><div class="gd"><span></span>';
  for(var d=1;d<=31;d++)h+=d<=dim?'<span class="dn">'+d+'</span>':'<span></span>';
  h+='<span></span></div>';
  S.habits.forEach(function(x){
    h+='<div class="gd"><input class="hn" data-k="h" data-id="'+x.id+'" value="'+esc(x.name)+'" placeholder="Write a habit" style="color:'+x.color+'" aria-label="Habit name">';
    for(var d=1;d<=31;d++){if(d>dim){h+='<i class="sx"></i>';continue}
      var key=k+"-"+p2(d),on=x.done.indexOf(key)>-1;
      h+='<button class="c'+(on?" on":"")+'" style="--cc:'+x.color+'" data-a="tg" data-id="'+x.id+'" data-d="'+key+'"'+(key>td?" disabled":"")+' aria-label="Day '+d+'" aria-pressed="'+on+'"></button>'}
    h+='<span class="sk">&#128293;'+streak(x)+'<button class="del" data-a="del" data-k="h" data-id="'+x.id+'" aria-label="Delete habit">&#10005;</button></span></div>'});
  h+='<button class="add" data-a="add" data-k="h">+ Add daily habit</button>';
  h+='<div class="three"><div><div class="lab">WEEKLY</div><div class="gw"><span></span>';
  for(var w=1;w<=5;w++)h+='<span class="dn">W'+w+'</span>';
  h+='<span></span></div>';
  S.weekly.forEach(function(x){
    h+='<div class="gw"><input class="hn" data-k="w" data-id="'+x.id+'" value="'+esc(x.name)+'" placeholder="Write a goal" style="color:'+x.color+'" aria-label="Weekly goal">';
    for(var w=1;w<=5;w++){var key=k+"-w"+w;h+='<button class="c'+(x.done.indexOf(key)>-1?" on":"")+'" style="--cc:'+x.color+'" data-a="tw" data-id="'+x.id+'" data-d="'+key+'" aria-label="Week '+w+'"></button>'}
    h+='<button class="del" data-a="del" data-k="w" data-id="'+x.id+'" aria-label="Delete">&#10005;</button></div>'});
  h+='<button class="add" data-a="add" data-k="w">+ Add weekly goal</button></div>';
  h+='<div><div class="lab">MONTHLY</div>';
  S.monthly.forEach(function(x){
    h+='<div class="gm"><input class="hn" data-k="m" data-id="'+x.id+'" value="'+esc(x.name)+'" placeholder="Write a goal" style="color:'+x.color+'" aria-label="Monthly goal"><button class="c'+(x.done.indexOf(k)>-1?" on":"")+'" style="--cc:'+x.color+'" data-a="tw" data-id="'+x.id+'" data-d="'+k+'" aria-label="Done this month"></button><button class="del" data-a="del" data-k="m" data-id="'+x.id+'" aria-label="Delete">&#10005;</button></div>'});
  h+='<button class="add" data-a="add" data-k="m">+ Add monthly goal</button></div>';
  h+='<div><div class="lab">NOTES</div><textarea class="nt" data-k="n" aria-label="Notes for this month">'+esc(S.notes[k]||"")+'</textarea></div></div></div></section>';
  h+='<div class="pills"><div class="pill">&#128293; '+b+'<small>best streak</small></div><div class="pill">'+tot+'<small>check-ins</small></div><div class="pill">'+points()+'<small>points</small></div></div>';
  var now=new Date(),poss=(V.y==now.getFullYear()&&V.m==now.getMonth())?now.getDate():(new Date(V.y,V.m,1)>now?0:dim),tD=0,tP=0,cells="";
  S.habits.forEach(function(x){var dn=x.done.filter(function(q){return q.indexOf(k)==0}).length;tD+=dn;tP+=poss;var pc=poss?Math.round(dn/poss*100):0;cells+='<div class="rc">'+ring(pc,x.color,84)+'<span>'+esc(x.name||"Untitled")+'</span></div>'});
  var all=tP?Math.round(tD/tP*100):0;
  h+='<section class="card"><h2>'+MN[V.m]+' progress</h2><div class="charts"><div class="rc big">'+ring(all,"var(--gold)",150)+'<span>All habits</span></div><div class="rgrid">'+(cells||'<p class="note">Add a habit to see its chart.</p>')+'</div></div></section>';
  h+='<section class="card"><h2>Badges and leaderboard</h2><div class="badges">';
  [["&#127775; First check-in",tot>=1],["&#129351; 7-day streak",b>=7],["&#127942; 30-day streak",b>=30]].forEach(function(x){h+='<span class="badge'+(x[1]?" got":"")+'">'+x[0]+'</span>'});
  h+='</div><div class="row" style="margin-bottom:14px"><input id="il" class="code" readonly value="'+esc(inviteLink())+'" aria-label="Invite link"><button class="btn ghost" data-a="copy">Copy invite link</button></div>';
  var list=GM.concat([{n:S.user,s:b,p:points(),me:1}]).sort(function(x,y){return y.p-x.p}),med=["&#129351;","&#129352;","&#129353;"];
  h+='<ol class="lb">';
  list.forEach(function(x,i){h+='<li class="'+(x.me?"me":"")+'"><span class="rk">'+(med[i]||i+1)+'</span><span class="av" style="background:'+avc(x.n)+'">'+esc(x.n.charAt(0).toUpperCase())+'</span><span>'+esc(x.n)+(x.me?" (you)":"")+'<small>'+x.s+'-day streak</small></span><b>'+x.p+' pts</b></li>'});
  h+='</ol><button class="btn ghost" data-a="addm" style="margin-top:8px;width:100%;border:2px dashed var(--line)">Add members +</button><div class="row" style="margin-top:14px"><input class="f" id="jc" placeholder="Paste an invite link" maxlength="200" aria-label="Invite link or code"><button class="btn" data-a="join">Join</button></div>';
  h+='<p class="note">Tap Add members + to send your group invite link. Friends can also paste the code '+esc(S.group)+' in the join box. Friends who join your group show up here.</p></section>';
  a.innerHTML=h}

function ring(p,c,s){var L=2*Math.PI*34;return '<svg width="'+s+'" height="'+s+'" viewBox="0 0 80 80" role="img" aria-label="'+p+' percent"><circle cx="40" cy="40" r="34" fill="none" stroke="var(--soft)" stroke-width="9"/><circle cx="40" cy="40" r="34" fill="none" stroke="'+c+'" stroke-width="9" stroke-linecap="round" stroke-dasharray="'+L.toFixed(1)+'" stroke-dashoffset="'+(L*(1-p/100)).toFixed(1)+'" transform="rotate(-90 40 40)"/><text x="40" y="46" text-anchor="middle" font-size="18" font-weight="700" fill="var(--ink)">'+p+'%</text></svg>'}
function arr(k){return k=="h"?S.habits:k=="w"?S.weekly:S.monthly}
function flip(l,id,key){l.forEach(function(x){if(x.id==id){var p=x.done.indexOf(key);if(p>-1)x.done.splice(p,1);else x.done.push(key)}})}
document.addEventListener("click",function(e){
  var t=e.target.closest("[data-a]");if(!t)return;var a=t.dataset.a,id=t.dataset.id,kk=t.dataset.k;
  if(a=="login"){doLogin()}
  else if(a=="mode"){mode=t.dataset.m;render()}
  else if(a=="logout"){if(S&&TOK)api("/api/save",{data:S,stats:stats()}).catch(function(){});TOK=null;GM=[];try{localStorage.removeItem("habitup:tok")}catch(e){}S=null;render()}
  else if(a=="pm"){V.m--;if(V.m<0){V.m=11;V.y--}render()}
  else if(a=="nm2"){V.m++;if(V.m>11){V.m=0;V.y++}render()}
  else if(a=="tg"){flip(S.habits,id,t.dataset.d);save();render();var hh=S.habits.filter(function(x){return x.id==id})[0];if(hh&&hh.done.indexOf(t.dataset.d)>-1&&t.dataset.d==dk(ago(0)))toast("Nice. Streak: "+streak(hh)+" day"+(streak(hh)==1?"":"s"))}
  else if(a=="tw"){flip(S.weekly.concat(S.monthly),id,t.dataset.d);save();render()}
  else if(a=="add"){arr(kk).push({id:nid(),name:"",done:[]});fix();save();render()}
  else if(a=="del"){var l=arr(kk).filter(function(x){return x.id!=id});if(kk=="h")S.habits=l;else if(kk=="w")S.weekly=l;else S.monthly=l;save();render();toast("Deleted")}
  else if(a=="copy"){doCopy(inviteLink())}
  else if(a=="addm"){shareInvite()}
  else if(a=="join"){var v=document.getElementById("jc").value.trim(),m=v.match(/join=([A-Za-z0-9-]+)/);if(m)v=m[1];v=v.toUpperCase();if(!v){toast("Paste an invite link or code");return}S.group=v;save();render();toast("Joined "+v)}
});
document.addEventListener("change",function(e){var t=e.target,k=t.dataset.k;if(!k||!S)return;if(k=="n")S.notes[ym()]=t.value;else arr(k).forEach(function(x){if(x.id==t.dataset.id)x.name=t.value.trim()});save()});
document.addEventListener("keydown",function(e){if(e.key!="Enter")return;var m={nm:"login",pw:"login",jc:"join"}[e.target.id];if(m){var b=document.querySelector('[data-a="'+m+'"]');if(b)b.click()}if(e.target.classList.contains("hn"))e.target.blur()});
S=load();try{var jm=location.search.match(/join=([A-Za-z0-9-]+)/);if(jm){PJ=jm[1].toUpperCase();if(S){S.group=PJ;save()}setTimeout(function(){toast("Joined "+PJ)},300)}}catch(e){}render();
try{TOK=localStorage.getItem("habitup:tok")}catch(e){}
if(TOK)api("/api/me",null,"GET").then(function(j){S=j.data;S.user=j.name;if(PJ)S.group=PJ;fix();if(!S.group)S.group=code();save();render();refreshGM()}).catch(function(){TOK=null;render()});
setInterval(refreshGM,15000);
</script>
<script>if("serviceWorker" in navigator){window.addEventListener("load",function(){navigator.serviceWorker.register("sw.js").catch(function(){})})}</script>
</body>
</html>
"""

MANIFEST = r"""{"name":"Habit Up","short_name":"Habit Up","description":"Habit tracker with streaks and a friends leaderboard","start_url":"./index.html","scope":"./","display":"standalone","orientation":"any","background_color":"#dfe3ee","theme_color":"#c8962c","icons":[{"src":"icon-192.png","sizes":"192x192","type":"image/png","purpose":"any maskable"},{"src":"icon-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}]}"""

SERVICE_WORKER = r"""var C="habitup-v3",F=["./","./index.html","./manifest.webmanifest","./icon-192.png","./icon-512.png"];
self.addEventListener("install",function(e){e.waitUntil(caches.open(C).then(function(c){return c.addAll(F)}));self.skipWaiting()});
self.addEventListener("activate",function(e){e.waitUntil(caches.keys().then(function(k){return Promise.all(k.filter(function(x){return x!==C}).map(function(x){return caches.delete(x)}))}));self.clients.claim()});
self.addEventListener("fetch",function(e){var u=new URL(e.request.url);if(e.request.method!=="GET"||u.pathname.indexOf("/api/")===0||u.origin!==location.origin)return;e.respondWith(fetch(e.request).then(function(n){var cp=n.clone();caches.open(C).then(function(c){c.put(e.request,cp)});return n}).catch(function(){return caches.match(e.request).then(function(r){return r||caches.match("./index.html")})}))});
"""

ICON_192 = "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAIAAADdvvtQAAAWfmNhQlgAABZ+anVtYgAAAB5qdW1kYzJwYQARABCAAACqADibcQNjMnBhAAAAFlhqdW1iAAAAR2p1bWRjMm1hABEAEIAAAKoAOJtxA3VybjpjMnBhOjExZGI2Mjc4LTM5OTQtNDdkZi04NjIxLTIxMjBjMmVhN2MwYwAAAAOTanVtYgAAAClqdW1kYzJhcwARABCAAACqADibcQNjMnBhLmFzc2VydGlvbnMAAAAAuGp1bWIAAABEanVtZGNib3IAEQAQgAAAqgA4m3ETYzJwYS5pbmdyZWRpZW50LnYzAAAAABhjMnNo9pjRWCo3HLXE1kDFQef2fwAAAGxjYm9yo2lkYzpmb3JtYXRpaW1hZ2UvcG5namluc3RhbmNlSUR4LHhtcDppaWQ6MGMxNDQyM2ItOWM5Mi00N2RmLWExMTctZWJiODdkMWI1ZWE1bHJlbGF0aW9uc2hpcGhwYXJlbnRPZgAAAeJqdW1iAAAAQWp1bWRjYm9yABEAEIAAAKoAOJtxE2MycGEuYWN0aW9ucy52MgAAAAAYYzJzaJMvJHOBTwQlL6huThxG8V8AAAGZY2JvcqJnYWN0aW9uc4KiZmFjdGlvbmtjMnBhLm9wZW5lZGpwYXJhbWV0ZXJzoWtpbmdyZWRpZW50c4GiY3VybHgtc2VsZiNqdW1iZj1jMnBhLmFzc2VydGlvbnMvYzJwYS5pbmdyZWRpZW50LnYzZGhhc2hYIM0EwFqIzUayJxJ1qmdF9yyXjx4+sBV3Qs4rJugURbzbpGZhY3Rpb254HWNvbS5hbnRocm9waWMuY2xhdWRlLnByb3ZpZGVkanBhcmFtZXRlcnOheB9jb20uYW50aHJvcGljLm9yaWdpbi1jb25maWRlbmNlZ3Vua25vd25rZGVzY3JpcHRpb254ZkNsYXVkZSBwcm92aWRlZCB0aGlzIGZpbGUgYXQgdGhlIHJlcXVlc3Qgb2YgYSB1c2VyIGFuZCBtYXkgaGF2ZSBjcmVhdGVkIG9yIG1vZGlmaWVkIHRoZSBmaWxlIGNvbnRlbnRzLm1zb2Z0d2FyZUFnZW50oWRuYW1lZkNsYXVkZXJhbGxBY3Rpb25zSW5jbHVkZWT1AAAAyGp1bWIAAABAanVtZGNib3IAEQAQgAAAqgA4m3ETYzJwYS5oYXNoLmRhdGEAAAAAGGMyc2g4KAe0JqlrSKQiKV2/XJgrAAAAgGNib3KlY2FsZ2ZzaGEyNTZjcGFkTQAAAAAAAAAAAAAAAABkaGFzaFggSuAhGyEHsSidkXhFlXWiTLDXLA3PSdlR3gsiMR9lqSRkbmFtZW5qdW1iZiBtYW5pZmVzdGpleGNsdXNpb25zgaJlc3RhcnQYIWZsZW5ndGgZFooAAAI+anVtYgAAACdqdW1kYzJjbAARABCAAACqADibcQNjMnBhLmNsYWltLnYyAAAAAg9jYm9ypWNhbGdmc2hhMjU2aXNpZ25hdHVyZXhNc2VsZiNqdW1iZj0vYzJwYS91cm46YzJwYToxMWRiNjI3OC0zOTk0LTQ3ZGYtODYyMS0yMTIwYzJlYTdjMGMvYzJwYS5zaWduYXR1cmVqaW5zdGFuY2VJRHgseG1wOmlpZDo2Y2NkNGM0OS0zYjc3LTQzMmUtODhlZC03ZWVlYmQzY2NhMjFyY3JlYXRlZF9hc3NlcnRpb25zg6JjdXJseC1zZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmluZ3JlZGllbnQudjNkaGFzaFggzQTAWojNRrInEnWqZ0X3LJePHj6wFXdCzism6BRFvNuiY3VybHgqc2VsZiNqdW1iZj1jMnBhLmFzc2VydGlvbnMvYzJwYS5hY3Rpb25zLnYyZGhhc2hYIFmeWex/PAjEHOK/nCmdcqTcmX/TI2L8/obksx5RERqDomN1cmx4KXNlbGYjanVtYmY9YzJwYS5hc3NlcnRpb25zL2MycGEuaGFzaC5kYXRhZGhhc2hYIFpGfdPx2GBJ3FIouXtsfcJJ9dIqcKBuCFd6/SV1jpTLdGNsYWltX2dlbmVyYXRvcl9pbmZvo2RuYW1lb0FudGhyb3BpYyBGaWxlc2d2ZXJzaW9uZTEuMC4wa3NwZWNWZXJzaW9uZTIuNC4wAAAQOGp1bWIAAAAoanVtZGMyY3MAEQAQgAAAqgA4m3EDYzJwYS5zaWduYXR1cmUAAAAQCGNib3LShFkCEqIBJhghWQIKMIICBjCCAY2gAwIBAgIUQOWgCu7COdC+uIP6BkIFPWdVEwAwCgYIKoZIzj0EAwMwSTEXMBUGA1UEChMOQW50aHJvcGljLCBQQkMxLjAsBgNVBAMTJUFudGhyb3BpYyBDb250ZW50IENyZWRlbnRpYWxzIFJvb3QgQ0EwHhcNMjYwODA3MTg0MzU2WhcNMjgwODA2MTk0MzU2WjBEMRcwFQYDVQQKEw5BbnRocm9waWMsIFBCQzEpMCcGA1UEAxMgQW50aHJvcGljIENsYXVkZSBDb250ZW50IFNpZ25pbmcwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAASYegpry1AYBRTVNL1CpTlbROnY3dey+UrsF9C3phYrATN3ZHf93Mo8RQN0KOUuOn19P4oWNFWe5n2/She9N7eTo1gwVjAOBgNVHQ8BAf8EBAMCB4AwFQYDVR0lBA4wDAYKKwYBBAGD6F4CATAMBgNVHRMBAf8EAjAAMB8GA1UdIwQYMBaAFM5R4gSBTmRbI/jjxM+aPpzB11zCMAoGCCqGSM49BAMDA2cAMGQCMDFzHRSeAXrSy1WOzkbhPZ6Km2wGTmZ/2gK18k8BQGXyqz88Rdrz6CTX9flAnYNVxgIwcF9c3fVhqmJKpi+UhasNUMko69cyX6STPfta3Q8EjyzDjzoyrol46FP6VFHhvUcJoWNwYWRZDZ4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD2WEBzs2Wf3QVUr6OVDswqgtlGR1Lh1kQ3sGKxtj0NOV0RSM5KgeRwXHMZpHAKmdL9ayrSTtGZ4HHHnQRiwqKYumNMbYvhFwAAA3ZJREFUeJzt3EtSE1EYgNFguRwcuyY3hFvCsRtykCqKCs/w9X2A50w1/Se3v75pNOTm/u72BB/1bfUT4HMTEImASAREIiASAZEIiERAJAIiERCJgEgERCIgEgGRCIhEQCQCIhEQiYBIBEQiIBIBkQiIREAkAiIREImASAREIiASAZEIiERAJAIiERCJgEgERCIgEgGRCIhEQCQCIhEQiYBIBEQiIBIBkQiIREAkAiIREImASAREIiASAZEIiERAJAIiERCJgEgERCIgEgGRCIhEQCQCIhEQiYBIBEQiIBIBkQiIREAkAiIREImASL6vfgLv8vPX35f+6M/vH9PGzZw1aNzhbu7vblc/hxe9srhP9eV+/7iZsw4ZN86mAV21vo99YK0/PGvyuD0z2vEeqJzRax9bZk0eF5/qIHvtQAeu0Xuu16PGxVnPPvyz3BttFNDhV9grCz3iar523Ds7KI+dYJeABu3P117cc8Ydcue0SUNb3AONO6PL7xuOOvFPH7X8pZ1tEdBMQ9f9zYOXbWOTLefC+oBGX0mPjz/hqn1lXC/g4gg7bEKLA5qzBOcp05b72XFH7R+7NbR+B/ofHPvus9V72cqAZl49k6/UL/zSLtiBhhuxYeyzCQmIREAkywJa/uPDHOPeax4feeFi2oFIBEQiIBIBkQiIREAkAiJZFtA+/xg/1JzPyi1cTDsQiYBIBDTciHexff4jaGVAM9+5J98lfOGXdsEONMOxG8Y+289peUBzrp7zlGlX6rPjjjrrgz5q/WHrd6DRS/D4+BOW+5VxvaHd6jntENBkQxf9zYN/vS9X2CKgOZ+6WuKo3yjd9lebd/nd+JMvVxjw2Ak2Cujk613C319lr4DO4nm9an17QzPHbZXO2Rb3QBdmfgNBPCUzx21Yz2nPHeiBL9k8atw4Wwf0wNf8butzBMS2drwH4hMREImASAREIiASAZEIiERAJAIiERCJgEgERCIgEgGRCIhEQCQCIhEQiYBIBEQiIBIBkQiIREAkAiIREImASAREIiASAZEIiERAJAIiERCJgEgERCIgEgGRCIhEQCQCIhEQiYBIBEQiIBIBkQiIREAkAiIREImASAREIiASAZEIiERAJAIiERCJgEgERCIgEgGRCIhEQCQCIhEQiYBIBEQiIBIBkQiIREAkAiIREImASP4BHTIJ/n9FiS4AAAAASUVORK5CYII="
ICON_512 = "iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAIAAAB7GkOtAAAWfmNhQlgAABZ+anVtYgAAAB5qdW1kYzJwYQARABCAAACqADibcQNjMnBhAAAAFlhqdW1iAAAAR2p1bWRjMm1hABEAEIAAAKoAOJtxA3VybjpjMnBhOjJhNDQxMDU1LTk5YTQtNGY5MC05MWEzLTU3MGFjMjA2MzYyYQAAAAOTanVtYgAAAClqdW1kYzJhcwARABCAAACqADibcQNjMnBhLmFzc2VydGlvbnMAAAAAuGp1bWIAAABEanVtZGNib3IAEQAQgAAAqgA4m3ETYzJwYS5pbmdyZWRpZW50LnYzAAAAABhjMnNoLXknPky7yWNDBcNp/RmHBQAAAGxjYm9yo2lkYzpmb3JtYXRpaW1hZ2UvcG5namluc3RhbmNlSUR4LHhtcDppaWQ6MDYzYzQwNzgtYTQ1Yi00ZTlmLWIxNmEtYTU2OTJhYWZmNTkwbHJlbGF0aW9uc2hpcGhwYXJlbnRPZgAAAeJqdW1iAAAAQWp1bWRjYm9yABEAEIAAAKoAOJtxE2MycGEuYWN0aW9ucy52MgAAAAAYYzJzaNFwmnoujQT30HO4zXC9TMoAAAGZY2JvcqJnYWN0aW9uc4KiZmFjdGlvbmtjMnBhLm9wZW5lZGpwYXJhbWV0ZXJzoWtpbmdyZWRpZW50c4GiY3VybHgtc2VsZiNqdW1iZj1jMnBhLmFzc2VydGlvbnMvYzJwYS5pbmdyZWRpZW50LnYzZGhhc2hYII5Qxhrz7d1q48MA5rQ80rVV/BcKx0lBhlqjGFu9i3EDpGZhY3Rpb254HWNvbS5hbnRocm9waWMuY2xhdWRlLnByb3ZpZGVkanBhcmFtZXRlcnOheB9jb20uYW50aHJvcGljLm9yaWdpbi1jb25maWRlbmNlZ3Vua25vd25rZGVzY3JpcHRpb254ZkNsYXVkZSBwcm92aWRlZCB0aGlzIGZpbGUgYXQgdGhlIHJlcXVlc3Qgb2YgYSB1c2VyIGFuZCBtYXkgaGF2ZSBjcmVhdGVkIG9yIG1vZGlmaWVkIHRoZSBmaWxlIGNvbnRlbnRzLm1zb2Z0d2FyZUFnZW50oWRuYW1lZkNsYXVkZXJhbGxBY3Rpb25zSW5jbHVkZWT1AAAAyGp1bWIAAABAanVtZGNib3IAEQAQgAAAqgA4m3ETYzJwYS5oYXNoLmRhdGEAAAAAGGMyc2gEWFkwuqvWuTKm+NHFg8GqAAAAgGNib3KlY2FsZ2ZzaGEyNTZjcGFkTQAAAAAAAAAAAAAAAABkaGFzaFgg7YmlWYfSBoe1s4XZmBlanVw+9yMxyl2UclFn6R25B7FkbmFtZW5qdW1iZiBtYW5pZmVzdGpleGNsdXNpb25zgaJlc3RhcnQYIWZsZW5ndGgZFooAAAI+anVtYgAAACdqdW1kYzJjbAARABCAAACqADibcQNjMnBhLmNsYWltLnYyAAAAAg9jYm9ypWNhbGdmc2hhMjU2aXNpZ25hdHVyZXhNc2VsZiNqdW1iZj0vYzJwYS91cm46YzJwYToyYTQ0MTA1NS05OWE0LTRmOTAtOTFhMy01NzBhYzIwNjM2MmEvYzJwYS5zaWduYXR1cmVqaW5zdGFuY2VJRHgseG1wOmlpZDo4Zjg2YjkzZS01YWNjLTRhNWQtYWRhYy1iYjJjMTU0ODZjMDZyY3JlYXRlZF9hc3NlcnRpb25zg6JjdXJseC1zZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmluZ3JlZGllbnQudjNkaGFzaFggjlDGGvPt3WrjwwDmtDzStVX8FwrHSUGGWqMYW72LcQOiY3VybHgqc2VsZiNqdW1iZj1jMnBhLmFzc2VydGlvbnMvYzJwYS5hY3Rpb25zLnYyZGhhc2hYIL29CK8p9gBogOC2w+lfVaAr0zlizqwa4Xtksc4bfUjComN1cmx4KXNlbGYjanVtYmY9YzJwYS5hc3NlcnRpb25zL2MycGEuaGFzaC5kYXRhZGhhc2hYIAKbyIkJy897abXvUHef0NxIa92KlLXPL3moX03PtSsYdGNsYWltX2dlbmVyYXRvcl9pbmZvo2RuYW1lb0FudGhyb3BpYyBGaWxlc2d2ZXJzaW9uZTEuMC4wa3NwZWNWZXJzaW9uZTIuNC4wAAAQOGp1bWIAAAAoanVtZGMyY3MAEQAQgAAAqgA4m3EDYzJwYS5zaWduYXR1cmUAAAAQCGNib3LShFkCEqIBJhghWQIKMIICBjCCAY2gAwIBAgIUQOWgCu7COdC+uIP6BkIFPWdVEwAwCgYIKoZIzj0EAwMwSTEXMBUGA1UEChMOQW50aHJvcGljLCBQQkMxLjAsBgNVBAMTJUFudGhyb3BpYyBDb250ZW50IENyZWRlbnRpYWxzIFJvb3QgQ0EwHhcNMjYwODA3MTg0MzU2WhcNMjgwODA2MTk0MzU2WjBEMRcwFQYDVQQKEw5BbnRocm9waWMsIFBCQzEpMCcGA1UEAxMgQW50aHJvcGljIENsYXVkZSBDb250ZW50IFNpZ25pbmcwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAASYegpry1AYBRTVNL1CpTlbROnY3dey+UrsF9C3phYrATN3ZHf93Mo8RQN0KOUuOn19P4oWNFWe5n2/She9N7eTo1gwVjAOBgNVHQ8BAf8EBAMCB4AwFQYDVR0lBA4wDAYKKwYBBAGD6F4CATAMBgNVHRMBAf8EAjAAMB8GA1UdIwQYMBaAFM5R4gSBTmRbI/jjxM+aPpzB11zCMAoGCCqGSM49BAMDA2cAMGQCMDFzHRSeAXrSy1WOzkbhPZ6Km2wGTmZ/2gK18k8BQGXyqz88Rdrz6CTX9flAnYNVxgIwcF9c3fVhqmJKpi+UhasNUMko69cyX6STPfta3Q8EjyzDjzoyrol46FP6VFHhvUcJoWNwYWRZDZ4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD2WECN26QMTLxWpd0P5gXcHQSgRhPMhwjXXBffyzmTQV3cfuJDnfr51GT/fTN6z5+W4vHVJm1iEeFUjFQOHGbmsjd+96u1YgAAC7JJREFUeJzt3V1OHbkaQNHKVQ8nee4x9YSSKSXPPaH7gIQQSXMKqB/be63nSNifyt7FQZAvP79/3QDo+d/dCwDgHgIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRf929AA7w9z//7v/Hv358O28lI9s/JSPaIzullXz5+f3r3Wvg3d51UN+28DE+akpGtMfCU1qYAMzkwOP6uzUO8Kkj2kxphzVGFCEAEzj7UntlxgN88Yg2U9phxhHVCMDQrr/Xns1yem8c0WZKO8wyoiYBGNS999qzkU/vICPaTGmHkUdUJgDDGeTEvjTa6R1wRJsp7TDaiBCAgQx4Yl8a4fQOPqLNlHYYYUQ8EYAhDH5iX7rx9M4yJSPaQwZGIAD3m+jQPrn+6E43os2UdtCA2/lTEDeb7tBul695xhFtprTDjGtejO8AbrPA03/BG9zsUzKiPXwrcBcBuMcCh/bJeUd3mRFtU01p51Lv+rocSwBusNLVtp1zdBcb0Tb2lD65tkGWwQcIwNXWu9q2o4/ukiPaxpvS4RfugEvibQJwqVWvtu24o7vwiLYxpjT4jyU04EoCcJ21r7btiKO7/Ii2W6d08d06yzrLBOAihatt+9zRjYxou2NK0/1umgZcw+8BXKFztX14p50RbZdP6d7L9GNfPfU83EgATld7lGv7vcwHBvvrx7cRXqU/tgwP0gUEgPsFj/oFWx7h6n9ptPWwCcDZglfb9s5dN0e0nTylMW/b964q+2xcRgBOVH58d+69PKLttCmNefs/0YChCAAsZeTb/8n4K+wQgLN4c3k4ASPajp7SLHfru9bpOTmPAJzCI/vkjTkY0bOjpjTL7f9EA0YgALCCuW7/JzOueTECcDxvKy/9cRpG9MonpzTvTbp/5Z6ZMwgAzG3e2//J7OufmgAczHvK717NxIj+yJQeMpPDCQBMbI3X5zV2MSMBOJI3lP/yPBkjeoMpPWQyxxIAmNVKL84r7WUi/j+Aw3g34UpL3pg7D9GSe7+F7wAAogQA5rPqK/Cq+xqWABzD5z9wGcftKAIAECUAMJm1PydZe3ejEQCAKAE4gE8k4WIO3SEEAGZS+ISksMdBCABAlAAARAkAQJQAfJYfRsEtHL3PEwCYRueno52d3ksAAKIEACBKAACiBAAgSgAAogQAIEoAAKIEACBKAACiBAAgSgAAogQAptH582ednd5LAD7LX62CWzh6nycAAFECABAlAABRAgAzKfx0tLDHQQjAAfwwCi7m0B1CAACiBAAms/YnJGvvbjQCABAlAMfwiSRcxnE7igDAfFb9nGTVfQ1LAACiBOAwvi19268f34zoof1TWu9leeeOPEUHEgCY1UoNWGkvExGAI3k3+S/PkzGiN5jSQyZzLAGAia3x4rzGLmYkAAfzhvK7VzMxoj8ypYfM5HACAHOb/fV59vVPTQCO5z3lpT9Ow4he+eSU5r1D96/cM3MGAYAVzNiAGde8GAE4hbeVJ2/MwYieHTWlue7Td63W03ISATiLR/bhBIxoO3pKszTA7T8IAYCljN+A8VfYIQAnKr+57Nx7eUTbaVMa+YZ979riT8jZBOBczcf3Xbtujmg7eUpjNsDtPxoB4H7Bc37BlkdrwGjrYROAC9Rut9p+L/OBwf79z78jXLsfW4YH6QICcIXOo/zhnXZGtF0+pXsb8LGvnnoebvTl5/evd6+hYoR3sVN9/tAuP6Lt1ildfKvOss4yAbjUwhfcUYd24RFtY0xp8B8/uP2vJABXW/KCO/bQLjmibbwpHX7VDrgk3iYAN1jsgjvj0C42om3sKX1ybYMsgw8QgHssc8Gdd2iXGdE21ZTu+h+J3f63EIDbLHDBDf5p8giMaA+3/10E4GaTnt4rT+ykI9pMaQdX/738HsDNZjwAF695xhFtprTDjGtejO8AhjDR69uNh3aWKRnRHm7/EQjAQAY/vSOc2MFHtJnSDiOMiCcCMJwBT+9oJ3bAEW2mtMNoI0IABjXI6R35xA4yos2Udhh5RGUCMLQbT+8sJ/beC86UHpplRE0CMIGLT++MJ/b6C86UHppxRDUCMJNTD/Aax/XsO86UHlpjRBECMKUDD/DCx9XfqHnIgxQnACt41zHOHtT9UzKiPbJTWokAAET5UxAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABRAgAQJQAAUQIAECUAAFECABAlAABR/wdNdMgQ6EvqpAAAAABJRU5ErkJggg=="

ASSETS = {
    "index.html": (INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8"),
    "manifest.webmanifest": (MANIFEST.encode("utf-8"), "application/manifest+json"),
    "sw.js": (SERVICE_WORKER.encode("utf-8"), "text/javascript"),
    "icon-192.png": (base64.b64decode(ICON_192), "image/png"),
    "icon-512.png": (base64.b64decode(ICON_512), "image/png"),
}

init()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
