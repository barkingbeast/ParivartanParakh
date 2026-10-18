let recording=null,recordingPoll=null,recordPhase=null;
const flushWaiters=new Map();
const recordingFrame=()=>$('#record-frame');
function recordError(error){$('#record-error').textContent=error.message||String(error);}
function flushRecording(){return new Promise((resolve,reject)=>{
  if(!recording)return reject(Error('Start a recording first.'));
  const key=crypto.randomUUID();
  const timer=setTimeout(()=>{flushWaiters.delete(key);reject(Error('Preview did not acknowledge the recording. Wait for it to load and try again.'));},5000);
  flushWaiters.set(key,()=>{clearTimeout(timer);resolve();});
  recordingFrame().contentWindow.postMessage({type:'flush-recording',session:recording.id,request:key},recording.origin);
});}
window.addEventListener('message',event=>{
  if(!recording||event.origin!==recording.origin||event.source!==recordingFrame().contentWindow||event.data?.session!==recording.id)return;
  if(event.data.type==='recording-flushed'){flushWaiters.get(event.data.request)?.();flushWaiters.delete(event.data.request);}
  if(event.data.type==='recording-error')recordError('The recorder rejected an event. This draft will not be approved silently.');
});
async function recordingAction(operation,data={}){
  $('#record-error').textContent='';
  await flushRecording();
  const value=await request(`/api/recordings/${recording.id}/${operation}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  renderRecording(value);return value;
}
function renderRecording(value){
  recording=value;
  const phase=value.phase;
  $('#recording').hidden=false;
  if(recordPhase!==phase){
    recordPhase=phase;
    $('#record-status').textContent='';
    $('#record-cancel').textContent=phase==='approved'?'Close recording preview':'Cancel recording';
    recordingFrame().hidden=!['seed','trigger'].includes(phase);
    if(phase==='seed'){
      recordingFrame().src=value.origin+'/';
      $('#record-toolbar').innerHTML='<h3>1. Create the old behavior</h3><p class="fine">Use the app below to create representative saved data. Then select a row or field that must survive.</p><div class="record-buttons"><button id="pick-behavior" class="secondary">Select behavior to protect</button><button id="record-next" class="secondary" disabled>Continue to changed feature →</button></div>';
      $('#pick-behavior').onclick=()=>{recordingFrame().contentWindow.postMessage({type:'pick-observation',session:value.id},value.origin);$('#record-status').textContent='Click a row or field inside the app. Repeated list rows are selected as a group.';};
      $('#record-next').onclick=()=>recordingAction('advance').catch(recordError);
    }else if(phase==='trigger'){
      recordingFrame().src=value.origin+'/?phase=trigger';
      $('#record-toolbar').innerHTML='<h3>2. Exercise the changed feature</h3><p class="fine">The new build now has the old saved data. Use its new feature, then request a preservation-rule suggestion.</p><button id="record-suggest" class="secondary">Suggest preservation rule →</button>';
      $('#record-suggest').onclick=()=>recordingAction('suggest').catch(recordError);
    }else if(phase==='review'){
      const d=value.draft;
      $('#record-toolbar').innerHTML=`<h3>3. Review and approve</h3><p>${escapeHtml(d.rule)}</p><ul>${d.candidate.values.map(v=>`<li>${escapeHtml(v)}</li>`).join('')}</ul><p class="fine">${escapeHtml(d.association)} Confirm the association if multiple modules are listed.</p><div class="record-fields"><label>Workflow name<input name="workflow-name" autocomplete="off" id="workflow-name" value="Recorded workflow" maxlength="100"></label><label>Old behavior reader<select name="record-reader" id="record-reader">${d.reader_candidates.map(m=>`<option ${m===d.reader?'selected':''}>${escapeHtml(m)}</option>`).join('')}</select></label><label>Changed workflow writer<select name="record-writer" id="record-writer">${d.writer_candidates.map(m=>`<option ${m===d.writer?'selected':''}>${escapeHtml(m)}</option>`).join('')}</select></label></div><details><summary>Inspect generated actions and observation</summary><pre>${escapeHtml(JSON.stringify({seed:d.seed_actions,trigger:d.trigger_actions,observe:d.candidate.selector,expected:d.candidate.values},null,2))}</pre></details><label class="toggle"><input type="checkbox" id="approve-rule"><span>I confirm these observed values and checkbox states should survive the changed workflow and reload.</span></label><button id="save-workflow" class="primary" disabled>Approve and save workflow</button>`;
      $('#approve-rule').onchange=()=>{$('#save-workflow').disabled=!$('#approve-rule').checked;};
      $('#save-workflow').onclick=async()=>{try{
        const approved=await request(`/api/recordings/${value.id}/approve`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({approved:$('#approve-rule').checked,draft_digest:d.digest,name:$('#workflow-name').value,reader:$('#record-reader').value,writer:$('#record-writer').value})});
        renderRecording(approved);samples=await request('/api/samples');selected=approved.approved.sample;$('#folder').value='';renderSamples();
      }catch(error){recordError(error);}};
    }else if(phase==='approved'){
      $('#record-toolbar').innerHTML=`<h3>Workflow approved and saved</h3><p class="fine">${escapeHtml(value.approved.name)} now appears with the investigation choices. The manifest and source revisions are retained locally.</p><button id="run-recorded" class="primary">Investigate this approved workflow ↗</button>`;
      $('#run-recorded').onclick=()=>{$('#run').click();};
    }else if(phase==='cancelled'){$('#record-toolbar').innerHTML='<p>Recording cancelled.</p>';}
  }
  if(phase==='seed'){$('#record-next').disabled=!value.candidate;if(value.candidate)$('#record-status').textContent=`Selected ${value.candidate.values.length} observed rows/fields. Continue when the baseline is ready.`;}
  $('#record-actions').textContent=`${value.actions.seed.length} baseline actions · ${value.actions.trigger.length} changed-feature actions`;
  if(['review','approved','cancelled'].includes(phase)){clearInterval(recordingPoll);recordingPoll=null;}
}
$('#record-start').onclick=async()=>{try{
  $('#launch-error').textContent='';
  if(recording&&['seed','trigger','review'].includes(recording.phase))throw Error('Finish or cancel the current recording first.');
  const folder=$('#folder').value.trim();
  const value=await request('/api/recordings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(folder?{folder}:{sample:selected})});
  recordPhase=null;$('#record-error').textContent='';$('#record-status').textContent='';renderRecording(value);
  recordingPoll=setInterval(async()=>{try{if(recording)renderRecording(await request('/api/recordings/'+recording.id));}catch(error){recordError(error);}},500);
  $('#recording').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});
}catch(error){$('#launch-error').textContent=error.message;}};
$('#record-cancel').onclick=async()=>{try{const value=await request(`/api/recordings/${recording.id}/cancel`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});renderRecording(value);}catch(error){recordError(error);}};

window.renderRepairControls=r=>{
  if(r.repair){const section=document.createElement('section');section.className='check';section.innerHTML=`<h3>Retained-case repair verification</h3><div class="notice"><strong>${escapeHtml(r.repair.status.replaceAll('_',' '))}</strong><p>Original failure: ${escapeHtml(r.repair.base_run)}</p><p>Old data reused: ${r.repair.baseline_reused} · Declaration reused: ${r.repair.manifest_reused} · Reduced actions reused: ${r.repair.actions_reused}</p><p>FalkorDB retained the regression replay obligation even if the repair removed the current shared-key dependency.</p></div>`;$('#result').append(section);}
  const failures=r.checks.filter(c=>c.verdict==='FAIL');
  if(r.verdict!=='FAIL'||!failures.length)return;
  const section=document.createElement('section');section.className='check';
  if(!r.manifest){section.innerHTML='<h3>Verify a supplied repair</h3><p class="fine">Rerun this older investigation once to retain its declaration and old-data snapshot.</p>';$('#result').append(section);return;}
  section.innerHTML=`<h3>Verify a supplied repair</h3><p class="fine">Reuse this failure's old data, preservation rule and reduced action sequence. The repair's own manifest cannot weaken the check.</p><div class="record-fields"><label>Failed behavior<select name="repair-feature" id="repair-feature">${failures.map(c=>`<option>${escapeHtml(c.feature)}</option>`).join('')}</select></label><label>Supplied revision<select name="repair-sample" id="repair-sample"><option value="">Choose an example revision</option>${samples.filter(s=>!s.id.startsWith('workflow-')).map(s=>`<option value="${escapeHtml(s.id)}">${escapeHtml(s.name)}</option>`).join('')}</select></label><label>Or a local repair build folder<input name="repair-folder" autocomplete="off" id="repair-folder" placeholder="D:\\repair-build" spellcheck="false"></label></div><button id="verify-repair" class="secondary">Replay retained failure against repair →</button><p id="repair-error" class="error" role="alert"></p>`;
  $('#result').append(section);
  $('#verify-repair').onclick=async()=>{try{
    $('#repair-error').textContent='';const folder=$('#repair-folder').value.trim(),sample=$('#repair-sample').value;
    if(!folder&&!sample)throw Error('Choose a supplied revision or enter its build folder.');
    const job=await request('/api/repairs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({base_run:r.id,feature:$('#repair-feature').value,...folder?{folder}:{sample},agent:$('#agent-mode').checked})});
    current=job.id;$('#run').disabled=true;poll(current);refreshRunHistory();
  }catch(error){$('#repair-error').textContent=error.message;}};
};

window.addEventListener('beforeunload',event=>{if(recording&&['seed','trigger','review'].includes(recording.phase)){event.preventDefault();event.returnValue='';}});
