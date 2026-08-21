"""Dashboard — full platform: Calls, Bookings, Contacts, Campaigns, Analytics, Escalations, Search."""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard — Karivena Satram AI</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f1419;color:#e7e9ea;min-height:100vh;padding:1rem}
        .hdr{text-align:center;margin-bottom:1rem;padding-bottom:.6rem;border-bottom:1px solid #2f3336}
        .hdr h1{font-size:1.3rem;color:#f7d070}.hdr p{color:#71767b;font-size:.75rem}
        .nav{position:fixed;top:1rem;right:1rem;color:#71767b;text-decoration:none;font-size:.8rem;padding:.4rem .8rem;border:1px solid #2f3336;border-radius:6px}.nav:hover{color:#f7d070;border-color:#f7d070}
        .stats{display:flex;gap:.8rem;justify-content:center;margin-bottom:1rem;flex-wrap:wrap}
        .sc{background:#16202a;border:1px solid #2f3336;border-radius:8px;padding:.6rem 1rem;text-align:center;min-width:90px}
        .sc .n{font-size:1.4rem;font-weight:700;color:#f7d070}.sc .l{font-size:.6rem;color:#71767b;text-transform:uppercase;margin-top:.1rem}
        .tabs{display:flex;gap:.4rem;margin-bottom:.8rem;flex-wrap:wrap}
        .tab{background:#16202a;border:1px solid #2f3336;padding:.4rem .8rem;border-radius:6px;cursor:pointer;font-size:.75rem;color:#71767b}
        .tab.active{border-color:#f7d070;color:#f7d070}
        .panel{background:#16202a;border:1px solid #2f3336;border-radius:10px;padding:1rem;margin-bottom:1rem;display:none}
        .panel.active{display:block}
        table{width:100%;border-collapse:collapse;font-size:.72rem}
        th{text-align:left;padding:.4rem;border-bottom:1px solid #2f3336;color:#71767b;font-weight:600;text-transform:uppercase;font-size:.62rem}
        td{padding:.4rem;border-bottom:1px solid #2f333633}
        tr:hover td{background:rgba(255,255,255,.02)}
        .badge{display:inline-block;padding:.1rem .35rem;border-radius:3px;font-size:.58rem;font-weight:600;text-transform:uppercase}
        .b-pending{background:#f7d07022;color:#f7d070}.b-needs_review{background:#ff6b3522;color:#ff6b35}.b-completed{background:#00ba7c22;color:#00ba7c}
        .b-confirmed,.b-active{background:#00ba7c22;color:#00ba7c}.b-cancelled,.b-failed{background:#f4212e22;color:#f4212e}
        .b-draft{background:#71767b22;color:#71767b}.b-scheduled{background:#5b9bd522;color:#5b9bd5}.b-running{background:#f7d07022;color:#f7d070}
        .b-resolved{background:#00ba7c22;color:#00ba7c}
        .btn{background:#00ba7c;color:#fff;border:none;padding:.2rem .5rem;border-radius:3px;cursor:pointer;font-size:.6rem;font-weight:600}.btn:hover{opacity:.8}
        .btn-sm{background:transparent;border:1px solid #2f3336;color:#71767b;padding:.15rem .35rem;border-radius:3px;cursor:pointer;font-size:.58rem}.btn-sm:hover{border-color:#f7d070;color:#f7d070}
        .empty{color:#71767b;text-align:center;padding:1.2rem;font-size:.8rem}
        .search-bar{display:flex;gap:.5rem;margin-bottom:.8rem}
        .search-bar input{flex:1;background:#0f1419;border:1px solid #2f3336;color:#e7e9ea;padding:.4rem .6rem;border-radius:6px;font-size:.8rem}
        .search-bar input:focus{border-color:#f7d070;outline:none}
        .search-bar button{background:#f7d070;color:#0f1419;border:none;padding:.4rem .8rem;border-radius:6px;font-size:.75rem;cursor:pointer;font-weight:600}
        .player{display:none;margin:.8rem 0;padding:.6rem;background:#0f1419;border-radius:6px;border:1px solid #2f3336}
        .player.on{display:block}.player audio{width:100%}.player .pl{font-size:.65rem;color:#71767b;margin-bottom:.3rem}
        .metric-row{display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1rem}
        .metric{background:#0f1419;border:1px solid #2f3336;border-radius:8px;padding:.8rem;flex:1;min-width:150px;text-align:center}
        .metric .mv{font-size:1.8rem;font-weight:700;color:#f7d070}.metric .ml{font-size:.65rem;color:#71767b;margin-top:.2rem}
    </style>
</head>
<body>
<a href="/" class="nav">Make a Call</a>
<div class="hdr"><h1>Karivena Satram — AI Platform</h1><p>Kaveri Voice Assistant Dashboard v2.0</p></div>

<div class="stats">
    <div class="sc"><div class="n" id="nCalls">0</div><div class="l">Calls</div></div>
    <div class="sc"><div class="n" id="nBookings">0</div><div class="l">Bookings</div></div>
    <div class="sc"><div class="n" id="nContacts">0</div><div class="l">Contacts</div></div>
    <div class="sc"><div class="n" id="nCampaigns">0</div><div class="l">Campaigns</div></div>
    <div class="sc"><div class="n" id="nEscalations">0</div><div class="l">Escalations</div></div>
    <div class="sc"><div class="n" id="nConversion">0%</div><div class="l">Conversion</div></div>
</div>

<div class="search-bar">
    <input type="text" id="searchInput" placeholder="Search calls, contacts, transcripts..." onkeydown="if(event.key==='Enter')doSearch()">
    <button onclick="doSearch()">Search</button>
</div>

<div class="tabs">
    <div class="tab active" onclick="showTab('calls')">Calls</div>
    <div class="tab" onclick="showTab('bookings')">Bookings</div>
    <div class="tab" onclick="showTab('contacts')">Contacts</div>
    <div class="tab" onclick="showTab('campaigns')">Campaigns</div>
    <div class="tab" onclick="showTab('analytics')">Analytics</div>
    <div class="tab" onclick="showTab('escalations')">Escalations</div>
    <div class="tab" onclick="showTab('search')">Search Results</div>
</div>

<!-- CALLS -->
<div class="panel active" id="p-calls">
<table><thead><tr><th>ID</th><th>Date</th><th>Duration</th><th>Workflow</th><th>Name</th><th>Phone</th><th>Location</th><th>Recording</th><th>Actions</th></tr></thead>
<tbody id="tb-calls"><tr><td colspan="9" class="empty">No calls yet.</td></tr></tbody></table>
</div>

<!-- BOOKINGS -->
<div class="panel" id="p-bookings">
<table><thead><tr><th>ID</th><th>Name</th><th>Phone</th><th>Location</th><th>Room</th><th>In</th><th>Out</th><th>Rooms</th><th>Total</th><th>Status</th></tr></thead>
<tbody id="tb-bookings"><tr><td colspan="10" class="empty">No bookings.</td></tr></tbody></table>
</div>

<!-- CONTACTS -->
<div class="panel" id="p-contacts">
<table><thead><tr><th>Name</th><th>Phone</th><th>Age</th><th>Locations</th><th>Calls</th><th>Bookings</th><th>Last Contact</th><th>Status</th></tr></thead>
<tbody id="tb-contacts"><tr><td colspan="8" class="empty">No contacts.</td></tr></tbody></table>
</div>

<!-- CAMPAIGNS -->
<div class="panel" id="p-campaigns">
<div style="margin-bottom:.8rem"><button class="btn" onclick="showNewCampaignPrompt()">+ New Campaign</button></div>
<table><thead><tr><th>ID</th><th>Name</th><th>Status</th><th>Date</th><th>Contacts</th><th>Completed</th><th>Failed</th><th>Actions</th></tr></thead>
<tbody id="tb-campaigns"><tr><td colspan="8" class="empty">No campaigns.</td></tr></tbody></table>
</div>

<!-- ANALYTICS -->
<div class="panel" id="p-analytics">
<div class="metric-row" id="analytics-metrics"></div>
<table><thead><tr><th>Date</th><th>Calls</th><th>Total Duration</th><th>Avg Duration</th><th>Bookings</th></tr></thead>
<tbody id="tb-analytics"><tr><td colspan="5" class="empty">No data yet.</td></tr></tbody></table>
</div>

<!-- ESCALATIONS -->
<div class="panel" id="p-escalations">
<table><thead><tr><th>ID</th><th>Call</th><th>Reason</th><th>Target</th><th>Customer</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead>
<tbody id="tb-escalations"><tr><td colspan="8" class="empty">No escalations.</td></tr></tbody></table>
</div>

<!-- SEARCH RESULTS -->
<div class="panel" id="p-search">
<div id="search-results" class="empty">Enter a search term above.</div>
</div>

<div class="player" id="player"><div class="pl" id="plbl">Playing...</div><audio controls id="aud"></audio></div>

<script>
function showTab(t){document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));document.querySelector('.tab[onclick*="'+t+'"]').classList.add('active');document.getElementById('p-'+t).classList.add('active')}
function playRec(id){document.getElementById('aud').src='/api/recordings/'+id;document.getElementById('plbl').textContent='Playing: '+id;document.getElementById('player').classList.add('on');document.getElementById('aud').play()}
function setWF(id,st){fetch('/api/calls/'+id+'/workflow',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:st})}).then(()=>refresh())}
function resolveEsc(id){fetch('/api/escalations/'+id+'/resolve',{method:'POST'}).then(()=>refresh())}
function setCampStatus(id,st){fetch('/api/campaigns/'+id+'/status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:st})}).then(()=>refresh())}

function showNewCampaignPrompt(){
    const name=prompt('Campaign name:');if(!name)return;
    const phones=prompt('Phone numbers (comma-separated):');if(!phones)return;
    const contacts=phones.split(',').map(p=>p.trim()).filter(p=>p);
    fetch('/api/campaigns',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,contacts,max_retries:3})}).then(()=>refresh());
}

function doSearch(){
    const q=document.getElementById('searchInput').value.trim();
    if(!q)return;
    showTab('search');
    fetch('/api/search?q='+encodeURIComponent(q)).then(r=>r.json()).then(d=>{
        let html='<p style="color:#71767b;font-size:.75rem;margin-bottom:.5rem">Found '+d.total_results+' results for "'+q+'"</p>';
        if(d.calls&&d.calls.length>0){
            html+='<h3 style="font-size:.8rem;color:#f7d070;margin:.5rem 0">Calls ('+d.calls.length+')</h3>';
            d.calls.forEach(c=>{html+='<div style="padding:.4rem;border-bottom:1px solid #2f3336;font-size:.72rem"><strong>'+c.call_id+'</strong> — '+c.customer_name+' ('+c.match_count+' matches)</div>'});
        }
        if(d.contacts&&d.contacts.length>0){
            html+='<h3 style="font-size:.8rem;color:#00ba7c;margin:.5rem 0">Contacts ('+d.contacts.length+')</h3>';
            d.contacts.forEach(c=>{html+='<div style="padding:.4rem;border-bottom:1px solid #2f3336;font-size:.72rem"><strong>'+c.name+'</strong> — '+c.phone+'</div>'});
        }
        if(d.total_results===0)html='<div class="empty">No results found.</div>';
        document.getElementById('search-results').innerHTML=html;
    });
}

async function refresh(){
    try{
        const [cR,bR,coR,cpR,aR,eR]=await Promise.all([
            fetch('/api/calls'),fetch('/api/bookings'),fetch('/api/contacts'),
            fetch('/api/campaigns'),fetch('/api/analytics'),fetch('/api/escalations')
        ]);
        const calls=(await cR.json()).calls||[];
        const bookings=(await bR.json()).bookings||[];
        const contacts=(await coR.json()).contacts||[];
        const campData=await cpR.json();const campaigns=campData.campaigns||[];
        const analytics=await aR.json();
        const escData=await eR.json();const escalations=escData.escalations||[];

        // Stats
        document.getElementById('nCalls').textContent=calls.length;
        document.getElementById('nBookings').textContent=bookings.length;
        document.getElementById('nContacts').textContent=contacts.length;
        document.getElementById('nCampaigns').textContent=campaigns.length;
        document.getElementById('nEscalations').textContent=escData.stats?escData.stats.pending:0;
        document.getElementById('nConversion').textContent=(analytics.summary?analytics.summary.conversion_rate_percent:0)+'%';

        // Calls
        const ct=document.getElementById('tb-calls');
        if(!calls.length){ct.innerHTML='<tr><td colspan="9" class="empty">No calls.</td></tr>'}
        else{ct.innerHTML=calls.slice(0,50).map(c=>{
            const info=c.gathered_info||{};const dur=c.duration?Math.round(c.duration)+'s':(c.duration_seconds?c.duration_seconds+'s':'—');
            const dt=c.start_time_readable||c.date||'—';const wf=c.workflow_status||'pending';
            const rec=c.has_recording?'<button class="btn" onclick="playRec(\\''+c.call_id+'\\')">&#9654;</button>':'—';
            return '<tr><td><strong>'+c.call_id+'</strong></td><td>'+dt+'</td><td>'+dur+'</td><td><span class="badge b-'+wf+'">'+wf.replace('_',' ')+'</span></td><td>'+(info.customer_name||'—')+'</td><td>'+(info.customer_phone||'—')+'</td><td>'+(info.location||'—')+'</td><td>'+rec+'</td><td><button class="btn-sm" onclick="setWF(\\''+c.call_id+'\\',\\'completed\\')">&#10003;</button> <button class="btn-sm" onclick="setWF(\\''+c.call_id+'\\',\\'needs_review\\')">&#9888;</button></td></tr>';
        }).join('')}

        // Bookings
        const bt=document.getElementById('tb-bookings');
        if(!bookings.length){bt.innerHTML='<tr><td colspan="10" class="empty">No bookings.</td></tr>'}
        else{bt.innerHTML=bookings.map(b=>'<tr><td>'+b.booking_id+'</td><td>'+b.customer_name+'</td><td>'+b.customer_phone+'</td><td>'+b.location+'</td><td>'+b.room_type+'</td><td>'+b.check_in+'</td><td>'+b.check_out+'</td><td>'+b.num_rooms+'</td><td>INR '+(b.total_price||0).toLocaleString('en-IN')+'</td><td><span class="badge b-'+(b.status||'confirmed')+'">'+b.status+'</span></td></tr>').join('')}

        // Contacts
        const cot=document.getElementById('tb-contacts');
        if(!contacts.length){cot.innerHTML='<tr><td colspan="8" class="empty">No contacts.</td></tr>'}
        else{cot.innerHTML=contacts.slice(0,50).map(c=>'<tr><td>'+c.name+'</td><td>'+c.phone+'</td><td>'+(c.age||'—')+'</td><td>'+(c.preferred_locations||[]).join(', ')+'</td><td>'+(c.total_calls||0)+'</td><td>'+(c.total_bookings||0)+'</td><td>'+(c.last_contact||'—').slice(0,10)+'</td><td><span class="badge b-'+(c.status||'active')+'">'+(c.status||'active')+'</span></td></tr>').join('')}

        // Campaigns
        const cpt=document.getElementById('tb-campaigns');
        if(!campaigns.length){cpt.innerHTML='<tr><td colspan="8" class="empty">No campaigns.</td></tr>'}
        else{cpt.innerHTML=campaigns.map(c=>'<tr><td>'+c.campaign_id+'</td><td>'+c.name+'</td><td><span class="badge b-'+c.status+'">'+c.status+'</span></td><td>'+c.scheduled_date+'</td><td>'+c.total_contacts+'</td><td>'+c.completed_count+'</td><td>'+c.failed_count+'</td><td><button class="btn-sm" onclick="setCampStatus(\\''+c.campaign_id+'\\',\\'running\\')">Run</button> <button class="btn-sm" onclick="setCampStatus(\\''+c.campaign_id+'\\',\\'paused\\')">Pause</button></td></tr>').join('')}

        // Analytics
        const am=document.getElementById('analytics-metrics');
        const s=analytics.summary||{};
        am.innerHTML='<div class="metric"><div class="mv">'+s.total_calls+'</div><div class="ml">Total Calls</div></div><div class="metric"><div class="mv">'+s.total_duration_minutes+'m</div><div class="ml">Total Duration</div></div><div class="metric"><div class="mv">'+s.avg_duration_seconds+'s</div><div class="ml">Avg Duration</div></div><div class="metric"><div class="mv">'+s.total_bookings+'</div><div class="ml">Bookings</div></div><div class="metric"><div class="mv">'+s.conversion_rate_percent+'%</div><div class="ml">Conversion</div></div>';
        const at=document.getElementById('tb-analytics');
        const daily=analytics.daily||[];
        if(!daily.length){at.innerHTML='<tr><td colspan="5" class="empty">No data.</td></tr>'}
        else{at.innerHTML=daily.slice(0,14).map(d=>'<tr><td>'+d.date+'</td><td>'+d.calls+'</td><td>'+Math.round(d.total_duration_seconds/60)+'m</td><td>'+d.avg_duration_seconds+'s</td><td>'+d.bookings+'</td></tr>').join('')}

        // Escalations
        const et=document.getElementById('tb-escalations');
        if(!escalations.length){et.innerHTML='<tr><td colspan="8" class="empty">No escalations.</td></tr>'}
        else{et.innerHTML=escalations.map(e=>'<tr><td>'+e.id+'</td><td>'+e.call_id+'</td><td>'+e.reason+'</td><td>'+(e.target?e.target.name:'—')+'</td><td>'+(e.customer_name||'—')+'</td><td><span class="badge b-'+e.status+'">'+e.status+'</span></td><td>'+(e.created_at||'').slice(0,16)+'</td><td>'+(e.status==='pending'?'<button class="btn-sm" onclick="resolveEsc(\\''+e.id+'\\')">Resolve</button>':'—')+'</td></tr>').join('')}
    }catch(e){console.error('Refresh:',e)}
}
refresh();setInterval(refresh,4000);
</script>
</body>
</html>"""
