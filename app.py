```python
import os
import pathlib
import subprocess
import threading
import time
from flask import Flask, request, jsonify, send_from_directory

PORT = int(os.environ.get("PORT", 8080))
SAVE_DIR = os.environ.get("SAVE_DIR", "/tmp/downloads")
os.makedirs(SAVE_DIR, exist_ok=True)

from flask import Flask
import yt_dlp

app = Flask(__name__)
downloads = {}
download_id_counter = 0

def human_bytes(n):
    if not n or n<=0: return "?"
    for u in ['B','KB','MB','GB']:
        if abs(n)<1024: return f"{n:.1f}{u}"
        n/=1024
    return f"{n:.1f}TB"
def human_dur(s):
    if not s or s<=0: return "0:00"
    m, sec = divmod(int(s),60); h, m = divmod(m,60)
    if h: return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"
def parse_sec(t):
    if not t or str(t).strip()=="" : return None
    t=str(t).strip()
    try:
        if ':' in t:
            p=[int(x) for x in t.split(':')]
            if len(p)==3: return p[0]*3600+p[1]*60+p[2]
            if len(p)==2: return p[0]*60+p[1]
            return p[0]
        if t.endswith('s'): t=t[:-1]
        return int(float(t))
    except: return None
def clean_url(url):
    if not url: return url
    return url.strip().replace("\\","").strip().strip('"').strip("'").strip()
def est_size(dur, br): return int((br*1000/8)*dur) if dur else 0
def detect_platform(url):
    l=url.lower()
    if "tiktok.com" in l: return "TikTok"
    if "facebook.com" in l or "fb.watch" in l: return "Facebook"
    if "instagram.com" in l: return "Instagram"
    if "youtube.com" in l or "youtu.be" in l: return "YouTube"
    return "Video"

VIDEO_Q={'2160':{'label':'4K','h':2160,'br':20000},'1080':{'label':'1080P','h':1080,'br':5000},'720':{'label':'720P','h':720,'br':2500},'480':{'label':'480P','h':480,'br':1000},}
AUDIO_Q={'320':{'label':'320kbps','br':320},'192':{'label':'192kbps','br':192},}

HTML = """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>YT-SICKEST V9 CLOUD 24/7</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:'Outfit',sans-serif}
body{background:#0a0a0f;color:#fff;min-height:100vh}
.header{background:#15151f;border-bottom:1px solid #222;padding:12px 16px;display:flex;justify-content:space-between;position:sticky;top:0;z-index:20}
.logo{font-weight:800;background:linear-gradient(90deg,#a855f7,#06ffa5);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:13px}
.container{max-width:500px;margin:0 auto;padding:14px;padding-bottom:90px}
.card{background:#15151f;border:1px solid #222232;border-radius:20px;padding:14px;margin-bottom:12px}
.title{font-size:10px;font-weight:800;letter-spacing:1.2px;color:#888;margin-bottom:10px}
.row-input{display:flex;gap:8px;align-items:center;width:100%}
.input{flex:1;background:#1f1f2e;border:1px solid #2a2a3a;color:#fff;padding:13px 14px;border-radius:12px;font-size:14px;outline:none;min-width:0}
.clear-outside{width:44px;height:44px;min-width:44px;background:#1f1f2e;border:1px solid #3a3a4a;color:#fff;border-radius:12px;cursor:pointer;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:18px}
.pills{display:flex;gap:6px;background:#1f1f2e;border-radius:22px;padding:4px;width:132px}
.pill{flex:1;border:none;background:transparent;color:#777;padding:9px;border-radius:16px;font-weight:800;font-size:12px;cursor:pointer}
.pill.active{background:#a855f7;color:#fff}
.btn{background:linear-gradient(135deg,#a855f7,#7c3aed);border:none;color:#fff;padding:13px 18px;border-radius:12px;font-weight:800;font-size:14px;cursor:pointer;width:100%}
.fmt{background:#1f1f2e;border:1px solid #2a2a3a;border-radius:14px;padding:12px;display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.badge{padding:5px 9px;border-radius:7px;font-weight:800;font-size:11px;min-width:68px;text-align:center}
.badge-v{background:rgba(168,85,247,.15);color:#a855f7;border:1px solid rgba(168,85,247,.3)}
.badge-a{background:rgba(6,255,165,.15);color:#06ffa5;border:1px solid rgba(6,255,165,.3)}
.dl{background:#fff;color:#000;border:none;padding:10px 16px;border-radius:10px;font-weight:800;font-size:12px;cursor:pointer;min-width:100px}
.dl.done{background:#06ffa5;color:#000}
.progress-wrap{height:6px;background:#222;border-radius:10px;overflow:hidden;margin-top:8px;display:none}
.progress-bar{height:100%;background:linear-gradient(90deg,#a855f7,#06ffa5);width:0%;transition:width .3s}
.batch-item{background:#1f1f2e;border:1px solid #2a2a3a;border-radius:10px;padding:9px 10px;display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;font-size:12px}
.status{position:fixed;bottom:0;left:0;right:0;background:rgba(21,21,31,.97);border-top:1px solid #222;padding:10px 14px;max-width:500px;margin:0 auto;z-index:30}
.log{font-size:11px;font-family:monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.toast{position:fixed;top:70px;left:50%;transform:translateX(-50%);background:#1f1f2e;border:1px solid #a855f7;padding:12px 18px;border-radius:12px;font-size:12px;font-weight:600;z-index:50;display:none;max-width:90%;text-align:center}
.public-card{background:linear-gradient(135deg,#a855f7,#06ffa5);border-radius:16px;padding:12px;margin-bottom:12px;color:#fff}
</style></head><body>
<div class="header"><div class="logo">YT-SICKEST V9 CLOUD 24/7</div><div style="font-size:8px;color:#06ffa5">CLOUD • ALWAYS ON</div></div>
<div id="toast" class="toast"></div>
<div class="container">
<div class="public-card"><div style="font-size:11px;font-weight:800">☁️ CLOUD 24/7 - Works even when your phone is OFF!</div></div>
<div class="card"><div class="title">PASTE LINK - YT / TIKTOK / FB / INSTA</div><div class="row-input"><input id="url" class="input" placeholder="YouTube, TikTok, FB reel..."><button class="clear-outside" onclick="clearInput()">✕</button></div><div style="display:flex;gap:10px;margin-top:12px;align-items:center"><div class="pills"><button id="mp3Btn" class="pill active" type="button" onclick="setMode('MP3')">MP3</button><button id="mp4Btn" class="pill" type="button" onclick="setMode('MP4')">MP4</button></div><button id="goBtn" class="btn" type="button" style="flex:1" onclick="go()">GO! Fetch</button></div><div id="detected" style="font-size:10px;color:#a855f7;margin-top:8px;display:none"></div><div id="err" style="font-size:11px;color:#ff6b6b;margin-top:8px;display:none"></div></div>
<div id="info" class="card" style="display:none"><div id="title" style="font-weight:700;font-size:13px"></div><div id="sub" style="font-size:11px;color:#888;margin-top:4px"></div></div>
<div class="card"><div class="title">FORMATS - Tap DONE to re-enable</div><div id="formats"><div style="text-align:center;padding:18px;color:#666;font-size:12px">Paste link + GO!</div></div></div>
<div class="card"><div class="title">TRIM - Empty end = full video</div><div style="display:flex;gap:8px;margin-bottom:10px"><input type="range" id="sSl" min="0" max="100" value="0" style="flex:1;accent-color:#06ffa5"><input type="range" id="eSl" min="0" max="100" value="100" style="flex:1;accent-color:#a855f7"></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><input id="sIn" class="input" placeholder="Start 0:30"><input id="eIn" class="input" placeholder="End empty=full"></div><div style="font-size:10px;color:#666;margin-top:8px">Start: <b id="sT" style="color:#06ffa5">0:00</b> - End: <b id="eT" style="color:#a855f7">full</b> - Dur: <b id="dT">0:00</b></div></div>
<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><div class="title" style="margin:0">📦 BATCH</div><div><span id="bCount" style="font-size:11px;color:#888">0 items</span> <button onclick="clearBatch()" style="background:none;border:none;color:#a855f7;font-size:11px;margin-left:8px">Clear</button></div></div><div id="bList"><div style="text-align:center;padding:10px;color:#555;font-size:11px">No batch yet</div></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px"><button class="btn" style="background:#1f1f2e;border:1px solid #2a2a3a" type="button" onclick="addBatch()">+ Add</button><button class="btn" type="button" onclick="downloadBatch()">Download all</button></div></div>
</div><div class="status"><div id="log" class="log">V9 CLOUD 24/7 - Works when phone off</div></div>
<script>
let mode='MP3', dur=100, info=null, batch=[], alreadyTriggered={};
let downloadedSet = new Set(JSON.parse(localStorage.getItem('yt_v9')||'[]'));
function saveDone(){ localStorage.setItem('yt_v9', JSON.stringify([...downloadedSet])); }
function setMode(m){document.getElementById('mp3Btn').classList.toggle('active', m==='MP3'); document.getElementById('mp4Btn').classList.toggle('active', m==='MP4'); mode=m; if(info) renderFormats();}
function toast(t){let el=document.getElementById('toast'); el.textContent=t; el.style.display='block'; setTimeout(()=>el.style.display='none',3500);}
function log(t){document.getElementById('log').textContent=t;}
function parseSec(s){if(!s||s.trim()=='')return null; s=s.trim(); try{if(s.includes(':')){let p=s.split(':').map(x=>parseInt(x)); if(p.length==3)return p[0]*3600+p[1]*60+p[2]; if(p.length==2)return p[0]*60+p[1]; return p[0];} if(s.endsWith('s'))s=s.slice(0,-1); return parseInt(parseFloat(s));}catch{return null}}
function secHMS(s){if(s==null)return''; let h=Math.floor(s/3600), m=Math.floor((s%3600)/60), sec=s%60; if(h)return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`; return `${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;}
function cleanUrl(u){if(!u) return u; return u.trim().replace(/\\+$/g,'').replace(/^["']+|["']+$/g,'').trim();}
function clearInput(){document.getElementById('url').value=''; document.getElementById('detected').style.display='none'; document.getElementById('err').style.display='none'; document.getElementById('info').style.display='none'; document.getElementById('formats').innerHTML='<div style="text-align:center;padding:18px;color:#666;font-size:12px">Paste link + GO!</div>'; toast('Cleared!');}
function detectPlat(url){url=url.toLowerCase(); if(url.includes('tiktok.com')) return 'TikTok'; if(url.includes('facebook.com')||url.includes('fb.watch')) return 'Facebook'; if(url.includes('instagram.com')) return 'Instagram'; if(url.includes('youtube.com')||url.includes('youtu.be')) return 'YouTube'; return 'Video';}
async function go(){
  let url=cleanUrl(document.getElementById('url').value.trim()); if(!url){toast('Paste link'); return;} if(!url.startsWith('http')){document.getElementById('err').style.display='block'; document.getElementById('err').textContent='Must start with https://'; return;}
  let plat=detectPlat(url); document.getElementById('detected').style.display='block'; document.getElementById('detected').textContent='Detected: '+plat; document.getElementById('err').style.display='none';
  let btn=document.getElementById('goBtn'); btn.textContent='Fetching...'; btn.disabled=true;
  try{let r=await fetch('/api/info',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url,mode:mode})}); let d=await r.json(); if(!d.ok){document.getElementById('err').style.display='block'; document.getElementById('err').textContent=d.error; btn.textContent='GO! Fetch'; btn.disabled=false; return;} info=d; dur=d.duration||60; document.getElementById('info').style.display='block'; document.getElementById('title').textContent=d.title; document.getElementById('sub').textContent=(d.uploader||plat)+' - '+d.duration_str; document.getElementById('dT').textContent=d.duration_str; document.getElementById('eT').textContent='full'; document.getElementById('sSl').max=dur; document.getElementById('eSl').max=dur; document.getElementById('eSl').value=dur; renderFormats();}catch(e){document.getElementById('err').style.display='block'; document.getElementById('err').textContent='Fetch failed: '+e;}
  btn.textContent='GO! Fetch'; btn.disabled=false;
}
function renderFormats(){
  if(!info) return; let c=document.getElementById('formats'); c.innerHTML=''; let fmts=mode==='MP3'?info.audio_formats:info.video_formats;
  fmts.forEach(f=>{
    let key=info.title+'|'+f.label; let isDone=downloadedSet.has(key); let div=document.createElement('div'); div.className='fmt'; let badgeClass=f.type==='video'?'badge-v':'badge-a';
    div.innerHTML=`<div style="display:flex;gap:10px;align-items:center;flex:1"><div class="badge ${badgeClass}">${f.label}</div><div style="flex:1"><div style="font-weight:800;font-size:13px">${f.label} - ${f.size_str}</div><div style="font-size:10px;color:${isDone?'#06ffa5':'#777'}">${isDone?'✅ DONE (tap to re-enable)':'Ready'}</div><div class="progress-wrap" id="prog-${f.q}"><div class="progress-bar" id="bar-${f.q}"></div></div></div></div><button class="dl ${isDone?'done':''}" id="btn-${f.q}" type="button">${isDone?'✅ DONE':'Download'}</button>`;
    c.appendChild(div); let btnEl=document.getElementById('btn-'+f.q);
    if(isDone){btnEl.onclick=()=>{downloadedSet.delete(key); saveDone(); toast('🔓 Re-enabled'); renderFormats();};} else {btnEl.onclick=()=>{downloadFormat(f);};}
  });
}
async function downloadFormat(fmt){
  let url=cleanUrl(document.getElementById('url').value.trim()); if(!url) return; let key=(info?info.title:'file')+'|'+fmt.label; if(downloadedSet.has(key)) return;
  let sIn=document.getElementById('sIn').value, eIn=document.getElementById('eIn').value; let btn=document.getElementById('btn-'+fmt.q); let barWrap=document.getElementById('prog-'+fmt.q); let bar=document.getElementById('bar-'+fmt.q); btn.textContent='Starting...'; barWrap.style.display='block';
  try{let r=await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url,format:fmt,start:sIn,end:eIn})}); let d=await r.json(); if(d.ok) pollProgress(d.download_id, fmt.q, btn, barWrap, bar, key);}catch(e){}
}
function pollProgress(id,q,btn,barWrap,bar,key){
  alreadyTriggered[id]=false; let interval=setInterval(async()=>{
    try{let r=await fetch('/api/progress/'+id); let d=await r.json(); if(!d.ok){clearInterval(interval); return;} bar.style.width=(d.percent||0)+'%'; if(!alreadyTriggered[id]) btn.textContent=(d.percent||0)+'%';
      if(d.status==='finished'){clearInterval(interval); if(alreadyTriggered[id]) return; alreadyTriggered[id]=true; let a=document.createElement('a'); a.href='/api/file/'+encodeURIComponent(d.filename); a.download=d.filename; document.body.appendChild(a); a.click(); a.remove(); downloadedSet.add(key); saveDone(); btn.textContent='✅ DONE'; btn.classList.add('done'); barWrap.style.display='none'; setTimeout(renderFormats,600);}
      else if(d.status==='error'){clearInterval(interval); btn.textContent='Error';}
    }catch(e){}
  },500);
}
let sSl=document.getElementById('sSl'), eSl=document.getElementById('eSl'), sIn=document.getElementById('sIn'), eIn=document.getElementById('eIn'), sT=document.getElementById('sT'), eT=document.getElementById('eT'), dT=document.getElementById('dT');
sSl.addEventListener('input',()=>{let v=parseInt(sSl.value); sIn.value=v?secHMS(v):''; sT.textContent=v?secHMS(v):'0:00';});
eSl.addEventListener('input',()=>{let v=parseInt(eSl.value); if(v>=dur-1){eIn.value=''; eT.textContent='full';} else {eIn.value=secHMS(v); eT.textContent=secHMS(v);}});
sIn.addEventListener('input',()=>{let s=parseSec(sIn.value); if(s!=null){sSl.value=s; sT.textContent=secHMS(s);} else if(sIn.value.trim()==''){sSl.value=0; sT.textContent='0:00';}});
eIn.addEventListener('input',()=>{if(eIn.value.trim()==''){eSl.value=dur; eT.textContent='full';} else {let s=parseSec(eIn.value); if(s!=null){eSl.value=s; eT.textContent=secHMS(s);}}});
function addBatch(){let u=cleanUrl(document.getElementById('url').value.trim()); if(!u||!u.includes('http')){toast('Paste link'); return;} batch.push(u); renderBatch(); document.getElementById('url').value='';}
function renderBatch(){let c=document.getElementById('bList'), cnt=document.getElementById('bCount'); cnt.textContent=batch.length+' items'; if(batch.length==0){c.innerHTML='<div style="text-align:center;padding:10px;color:#555;font-size:11px">No batch yet</div>'; return} c.innerHTML=batch.map((u,i)=>`<div class="batch-item"><span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:82%">${i+1}. ${u.slice(0,45)}</span><button onclick="removeBatch(${i})" style="background:rgba(255,80,80,.15);color:#ff5050;border:none;width:26px;height:26px;border-radius:7px" type="button">x</button></div>`).join('');}
function removeBatch(i){batch.splice(i,1); renderBatch();}
function clearBatch(){batch=[]; renderBatch();}
async function downloadBatch(){if(batch.length==0){toast('Add links'); return;} for(let i=0;i<batch.length;i++){let fmt={type:mode==='MP3'?'audio':'video', q:mode==='MP3'?'192':'720', label:mode==='MP3'?'192kbps':'720P', h:720}; await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:batch[i],format:fmt})}); await new Promise(r=>setTimeout(r,1000));} batch=[]; renderBatch();}
renderBatch();
</script></body></html>
"""

@app.route('/')
def home():
    return HTML
@app.route('/api/file/<path:filename>')
def serve_file(filename):
    try:
        return send_from_directory(SAVE_DIR, filename, as_attachment=True, download_name=filename)
    except Exception as e:
        return f"File not found: {e}", 404
@app.route('/api/info', methods=['POST'])
def api_info():
    data=request.json or {}
    url=clean_url(data.get('url','').strip())
    if not url: return jsonify({'ok':False,'error':'No URL'})
    platform=detect_platform(url)
    try:
        ydl_opts={'quiet':True,'no_warnings':True,'skip_download':True,'noplaylist':True,}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(url, download=False)
        dur=info.get('duration',0) or 60
        title=info.get('title','Unknown') or info.get('description','Video')[:60]
        uploader=info.get('uploader','') or platform
        yt_formats=info.get('formats',[])
        best_h={}
        for f in yt_formats:
            h=f.get('height')
            if h and f.get('vcodec')!='none':
                fs=f.get('filesize') or f.get('filesize_approx') or 0
                if h not in best_h or fs>best_h[h].get('fs',0):
                    best_h[h]={'fs':fs}
        vfs=[]; afs=[]
        for k,q in VIDEO_Q.items():
            real=best_h.get(q['h'])
            sz=real['fs'] if real and real['fs']>0 else est_size(dur,q['br'])
            vfs.append({'id':f'v{k}','label':q['label'],'type':'video','q':k,'h':q['h'],'br':q['br'],'size':sz,'size_str':human_bytes(sz)})
        vfs.sort(key=lambda x:x['h'], reverse=True)
        for k,q in AUDIO_Q.items():
            sz=est_size(dur,q['br'])
            afs.append({'id':f'a{k}','label':q['label'],'type':'audio','q':k,'br':q['br'],'size':sz,'size_str':human_bytes(sz),'h':0})
        afs.sort(key=lambda x:x['br'], reverse=True)
        return jsonify({'ok':True,'title':title,'uploader':uploader,'duration':dur,'duration_str':human_dur(dur),'thumbnail':info.get('thumbnail',''),'video_formats':vfs,'audio_formats':afs,'platform':platform})
    except Exception as e: return jsonify({'ok':False,'error':str(e)[:200]})
def progress_hook(d, download_id):
    if download_id not in downloads: return
    if d['status']=='downloading':
        try:
            total=d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded=d.get('downloaded_bytes') or 0
            if total>0: downloads[download_id]['percent']=int(downloaded/total*100)
        except: pass
    elif d['status']=='finished': downloads[download_id]['percent']=100
@app.route('/api/download', methods=['POST'])
def api_download():
    global download_id_counter
    data=request.json or {}
    url=clean_url(data.get('url','').strip())
    fmt=data.get('format',{})
    start=parse_sec(data.get('start',''))
    end=parse_sec(data.get('end',''))
    if not url: return jsonify({'ok':False,'error':'No URL'})
    download_id=str(download_id_counter)
    download_id_counter+=1
    downloads[download_id]={'percent':0,'status':'downloading','filename':'','error':''}
    def do_download():
        try:
            q=fmt.get('q','720')
            q_num=''.join(filter(str.isdigit, str(q))) or '720'
            ftype=fmt.get('type','video')
            outtmpl=os.path.join(SAVE_DIR,'%(title)s.%(ext)s')
            ydl_opts={'outtmpl':outtmpl,'merge_output_format':'mp4','quiet':True,'noplaylist':True,'progress_hooks':[lambda d: progress_hook(d, download_id)],}
            if ftype=='audio':
                ydl_opts['postprocessors']=[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':q_num}]
                ydl_opts['format']='bestaudio/best'
            else:
                if 'tiktok' in url.lower() or 'facebook' in url.lower() or 'fb.watch' in url.lower():
                    ydl_opts['format']='best[ext=mp4]/best'
                else:
                    ydl_opts['format']=f'bestvideo[height<={q_num}][ext=mp4]+bestaudio/best[height<={q_num}]' if q_num!='2160' else 'bestvideo[ext=mp4]+bestaudio/best'
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            files=sorted(pathlib.Path(SAVE_DIR).glob('*.*'), key=lambda x:x.stat().st_mtime, reverse=True)
            if not files:
                downloads[download_id]['status']='error'; return
            latest=str(files[0])
            if start is not None or end is not None:
                try:
                    trimmed=str(files[0].parent / f"{files[0].stem}_trimmed{files[0].suffix}")
                    cmd=["ffmpeg","-y"]
                    if start is not None: cmd+=["-ss",str(start)]
                    if start is not None and end is not None: cmd+=["-t",str(end-start)]
                    elif end is not None: cmd+=["-to",str(end)]
                    cmd+=["-i",latest,"-c","copy",trimmed]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
                    if os.path.exists(trimmed):
                        try: os.remove(latest); os.rename(trimmed, latest); latest=trimmed
                        except: pass
                except: pass
            downloads[download_id]['filename']=os.path.basename(latest)
            downloads[download_id]['status']='finished'
            downloads[download_id]['percent']=100
        except Exception as e:
            downloads[download_id]['status']='error'
            downloads[download_id]['error']=str(e)[:200]
    threading.Thread(target=do_download, daemon=True).start()
    return jsonify({'ok':True,'download_id':download_id})
@app.route('/api/progress/<download_id>')
def api_progress(download_id):
    if download_id not in downloads: return jsonify({'ok':False,'error':'Not found'})
    return jsonify({'ok':True,**downloads[download_id]})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
```