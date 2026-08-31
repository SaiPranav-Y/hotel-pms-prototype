"""Voice call page — Karivena Satram branding."""

CALL_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Call Kaveri — Karivena Satram</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:linear-gradient(135deg,#0f1419,#1a1a2e);color:#e7e9ea;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:2rem}
        .c{text-align:center;max-width:520px;width:100%}
        h1{font-size:1.4rem;color:#f7d070;margin-bottom:.3rem}
        .sub{color:#71767b;font-size:.85rem;margin-bottom:.4rem}
        .agent{color:#00ba7c;font-size:.95rem;margin-bottom:1.5rem}
        .btn{width:120px;height:120px;border-radius:50%;border:none;cursor:pointer;font-size:2.5rem;transition:all .3s;margin:1.5rem auto;display:flex;align-items:center;justify-content:center}
        .btn.idle{background:#00ba7c;color:#fff}
        .btn.idle:hover{transform:scale(1.05);box-shadow:0 4px 20px rgba(0,186,124,.3)}
        .btn.active{background:#f4212e;color:#fff;animation:p 1.5s infinite}
        .btn.proc{background:#f7d070;color:#1a1a2e}
        @keyframes p{0%{box-shadow:0 0 0 0 rgba(244,33,46,.4)}70%{box-shadow:0 0 0 20px rgba(244,33,46,0)}100%{box-shadow:0 0 0 0 rgba(244,33,46,0)}}
        .st{font-size:1rem;margin:1rem 0;min-height:1.5rem}
        .st.listening{color:#00ba7c}.st.speaking{color:#f7d070}.st.proc{color:#71767b}.st.err{color:#f4212e}
        .tx{margin-top:1.5rem;text-align:left;max-height:340px;overflow-y:auto;padding:1rem;background:rgba(255,255,255,.03);border-radius:12px;border:1px solid #2f3336}
        .te{margin-bottom:.7rem;padding:.4rem 0;border-bottom:1px solid #2f333622}
        .te .r{font-size:.68rem;text-transform:uppercase;letter-spacing:.04em;margin-bottom:.15rem}
        .te .r.kaveri{color:#f7d070}.te .r.guest{color:#00ba7c}
        .te .t{font-size:.88rem;line-height:1.4}
        .nav{position:fixed;top:1rem;right:1rem;color:#71767b;text-decoration:none;font-size:.85rem;padding:.5rem 1rem;border:1px solid #2f3336;border-radius:8px}
        .nav:hover{color:#f7d070;border-color:#f7d070}
        .ins{margin-top:1.5rem;color:#71767b;font-size:.8rem;line-height:1.6}
        .err-box{margin-top:1rem;padding:1rem;background:#f4212e11;border:1px solid #f4212e44;border-radius:8px;color:#f4212e;font-size:.85rem;display:none}
        .rec{display:none;align-items:center;justify-content:center;gap:.5rem;margin-top:.5rem;color:#f4212e;font-size:.8rem}
        .rec.on{display:flex}
        .rec-dot{width:10px;height:10px;border-radius:50%;background:#f4212e;animation:bk 1s infinite}
        @keyframes bk{0%,100%{opacity:1}50%{opacity:.3}}
    </style>
</head>
<body>
<a href="/dashboard" class="nav">Dashboard</a>
<div class="c">
    <h1>Karivena Satram</h1>
    <p class="sub">Pilgrim Accommodation Booking</p>
    <p class="agent">AI Receptionist: Kaveri</p>
    <button class="btn idle" id="B" onclick="toggleCall()">&#128222;</button>
    <div class="st" id="S">Click to call Kaveri</div>
    <div class="rec" id="R"><span class="rec-dot"></span> Recording</div>
    <div class="err-box" id="E"></div>
    <div class="tx" id="T" style="display:none"></div>
    <div class="ins" id="I">
        <p>Press the button to talk to Kaveri about booking rooms.</p>
        <p>Locations: Srisailam, Tirupathi, Kasi, Shiridi, Rameswaram, Mahanandi, and more.</p>
        <p>Speak in English or Telugu. Wait for Kaveri to finish before speaking.</p>
    </div>
</div>
<script>
let ws=null,rec=null,isActive=false,isSpeaking=false,isProc=false,chunks=[],micStream=null;
const synth=window.speechSynthesis;
const B=document.getElementById('B'),S=document.getElementById('S'),T=document.getElementById('T'),I=document.getElementById('I'),E=document.getElementById('E'),R=document.getElementById('R');
let recognition=null;

function err(m){E.textContent=m;E.style.display='block';setTimeout(()=>E.style.display='none',8000)}
function toggleCall(){isActive?endCall():startCall()}

async function startCall(){
    const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!SR){err('Use Chrome or Edge for voice.');return}
    try{micStream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}})}catch(e){err('Microphone access denied.');return}
    chunks=[];
    const mt=MediaRecorder.isTypeSupported('audio/webm;codecs=opus')?'audio/webm;codecs=opus':'audio/webm';
    rec=new MediaRecorder(micStream,{mimeType:mt});
    rec.ondataavailable=e=>{if(e.data.size>0)chunks.push(e.data)};
    rec.start(1000);R.classList.add('on');
    recognition=new SR();recognition.continuous=false;recognition.interimResults=false;recognition.lang='en-IN';recognition.maxAlternatives=1;
    recognition.onresult=e=>{const t=e.results[0][0].transcript.trim();if(t&&!isSpeaking&&!isProc){addTx('guest',t);send(t)}};
    recognition.onerror=e=>{if(e.error==='no-speech'||e.error==='aborted')schListen()};
    recognition.onend=()=>schListen();
    const proto=location.protocol==='https:'?'wss:':'ws:';
    ws=new WebSocket(proto+'//'+location.host+'/voice');
    ws.onopen=()=>{isActive=true;B.className='btn active';B.innerHTML='&#128225;';S.textContent='Connected...';S.className='st speaking';T.style.display='block';I.style.display='none';isSpeaking=true};
    ws.onmessage=e=>handleMsg(JSON.parse(e.data));
    ws.onclose=()=>{if(isActive)endCall()};
    ws.onerror=()=>{err('Server not running.');endCall()}
}

function send(t){if(!ws||ws.readyState!==1)return;isProc=true;S.textContent='Kaveri is thinking...';S.className='st proc';B.className='btn proc';stopListen();ws.send(JSON.stringify({type:'transcript',text:t}))}
function handleMsg(d){const t=d.text||'';if(!t)return;addTx('kaveri',t);isSpeaking=true;isProc=false;S.textContent='Kaveri speaking...';S.className='st speaking';B.className='btn active';stopListen();if(d.type==='audio_response'&&d.audio)playAudio(d.audio).then(done);else speakTTS(t).then(done)}
function done(){isSpeaking=false;isProc=false;if(isActive){S.textContent='Listening...';S.className='st listening';B.className='btn active';startListen()}}
function playAudio(b){return new Promise(r=>{const a=new Audio('data:audio/mp3;base64,'+b);a.onended=r;a.onerror=r;a.play().catch(r)})}
function speakTTS(t){return new Promise(r=>{if(!synth){r();return}synth.cancel();const u=new SpeechSynthesisUtterance(t);u.rate=.9;const v=synth.getVoices();const p=v.find(x=>x.lang==='en-IN')||v.find(x=>x.lang.startsWith('en'));if(p)u.voice=p;u.onend=r;u.onerror=r;synth.speak(u);setTimeout(r,15000)})}
function startListen(){if(!isActive||isSpeaking||isProc||!recognition)return;try{recognition.start()}catch(e){}}
function stopListen(){if(recognition)try{recognition.stop()}catch(e){}}
function schListen(){if(!isActive||isSpeaking||isProc)return;setTimeout(startListen,400)}
function addTx(role,t){const d=document.createElement('div');d.className='te';d.innerHTML='<div class="r '+role+'">'+(role==='kaveri'?'Kaveri':'You')+'</div><div class="t">'+t+'</div>';T.appendChild(d);T.scrollTop=T.scrollHeight}

function endCall(){
    isActive=false;isSpeaking=false;isProc=false;
    if(synth)synth.cancel();stopListen();R.classList.remove('on');
    B.className='btn idle';B.innerHTML='&#128222;';S.textContent='Saving...';S.className='st proc';
    if(rec&&rec.state!=='inactive'){rec.onstop=()=>{const b=new Blob(chunks,{type:rec.mimeType});sendRec(b,rec.mimeType);if(micStream)micStream.getTracks().forEach(t=>t.stop())};rec.stop()}
    else{closeWS();if(micStream)micStream.getTracks().forEach(t=>t.stop())}
}
function sendRec(b,mt){if(b.size<1000||!ws||ws.readyState!==1){closeWS();return}const r=new FileReader();r.onload=()=>{ws.send(JSON.stringify({type:'recording',audio:r.result.split(',')[1],mimeType:mt}));setTimeout(()=>{if(ws&&ws.readyState===1)ws.send(JSON.stringify({type:'end_call'}));setTimeout(()=>{if(ws)ws.close();S.textContent='Call ended. Recording saved.';S.className='st';I.style.display='block'},300)},1000)};r.onerror=()=>closeWS();r.readAsDataURL(b)}
function closeWS(){if(ws&&ws.readyState===1){ws.send(JSON.stringify({type:'end_call'}));ws.close()}S.textContent='Call ended.';S.className='st';I.style.display='block'}

if(synth)synth.onvoiceschanged=()=>synth.getVoices();
(function(){const SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){B.style.display='none';S.className='st err';S.textContent='Use Chrome or Edge for voice support.';I.innerHTML='<p style="color:#f4212e">Open in <strong>Chrome</strong> or <strong>Edge</strong>: http://localhost:'+location.port+'</p>'}})();
</script>
</body>
</html>"""
