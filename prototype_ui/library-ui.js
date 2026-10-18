let libraryCases=[],libraryLimit=8,libraryRequest=0;
function renderLibrary(){
 const query=$('#library-search').value.toLowerCase();
 const cases=libraryCases.filter(c=>`${c.app} ${c.feature} ${c.run}`.toLowerCase().includes(query));
 const visible=cases.slice(0,libraryLimit),box=$('#regression-list');
 box.innerHTML=visible.length?visible.map(c=>`<article class="case-card"><h3>${escapeHtml(c.feature)}</h3><p class="fine">${escapeHtml(c.app)}<br>${escapeHtml(c.run)}</p><strong class="case-status">${escapeHtml(c.latest_status.replaceAll('_',' '))}</strong><p class="fine">${c.actions.length} retained actions · ${c.repairs.length} repair attempts</p><button class="secondary" data-case="${escapeHtml(c.run)}">Open failure and verify a supplied revision →</button><a href="/api/repair-brief/${encodeURIComponent(c.run)}" download="repair-brief-${escapeHtml(c.run)}.md">Export repair brief</a>${!c.replay_ready?'<p class="notice">Legacy case: rerun to retain the declaration before repair verification.</p>':''}<details><summary>Observations, revisions and repair history</summary><p>Expected: ${escapeHtml(JSON.stringify(c.expected))}</p><p>Observed: ${escapeHtml(JSON.stringify(c.actual))}</p><p class="fine">Status belongs to this case and supplied revision only.</p><pre>${escapeHtml(JSON.stringify({original:c.source_hashes,repairs:c.repairs},null,2))}</pre></details></article>`).join(''):'<p class="fine" role="status">No matching retained failures. Run a failing investigation to create one.</p>';
 if(cases.length>libraryLimit){const more=document.createElement('button');more.className='secondary library-more';more.textContent=`Show more cases (${cases.length-libraryLimit} remaining)`;more.onclick=()=>{libraryLimit+=8;renderLibrary();};box.append(more);}
 box.querySelectorAll('[data-case]').forEach(b=>b.onclick=()=>{current=b.dataset.case;const url=new URL(location);url.searchParams.set('run',current);window.history.replaceState(null,'',url);poll(current);$('#result').scrollIntoView({block:'start'});});
}
async function refreshLibrary(){
 const ticket=++libraryRequest;
 try{const cases=await request('/api/regressions');if(ticket!==libraryRequest)return;libraryCases=cases;renderLibrary();}
 catch(error){$('#regression-list').textContent='Library unavailable. Check the dashboard connection and refresh. '+error.message;}
}
const originalRenderResult=renderResult;
renderResult=function(r){
 originalRenderResult(r);
 const graphPanel=document.createElement('section');graphPanel.className='check graph-panel';
 const query='MATCH (a)-[r]->(b) RETURN a,r,b LIMIT 100';
 const graphUrl='http://localhost:3000/graph?graph='+encodeURIComponent(r.graph)+'&query='+encodeURIComponent(query)+'&view=Graph&layout=force';
 graphPanel.innerHTML=`<h3>How the graph changed</h3><p class="fine">Captured from actual FalkorDB queries during this run. These are stage snapshots, not a live animation. A passing repair can keep the same dependency edges; preservation is decided by the browser.</p><a href="${escapeHtml(graphUrl)}" target="_blank" rel="noopener">Open this run in FalkorDB ↗</a>${(r.graph_stages||[]).map(s=>`<details ${s.label==='Changed feature exercised'?'open':''}><summary>${escapeHtml(s.label)} · ${s.edges.length} relationships · ${s.added_edges.length} added</summary><ul>${s.added_edges.map(e=>`<li><code>${escapeHtml(e[0])} —${escapeHtml(e[1])}→ ${escapeHtml(e[2])}</code></li>`).join('')||'<li>No new relationships at this stage.</li>'}</ul></details>`).join('')||'<p class="fine">Older run: rerun to capture graph stages.</p>'}<details><summary>Cypher executed by the dependency tool</summary><pre>${escapeHtml(r.query)}</pre><p class="fine">The AI selects the validated query_dependencies tool. The host executes this fixed Cypher; the model does not generate arbitrary Cypher.</p><pre>${escapeHtml(JSON.stringify({paths:r.paths,retained_targets:r.retained_targets||[]},null,2))}</pre></details>`;
 $('#result').append(graphPanel);
 if(r.verdict==='FAIL'){
  const link=document.createElement('a');link.href='/api/repair-brief/'+encodeURIComponent(r.id);
  link.download='repair-brief-'+r.id+'.md';link.textContent='↓ Repair brief for your coding assistant';
  $('#result .exports').append(link);
  const note=document.createElement('p');note.className='fine';note.textContent='Review observations and recorded inputs before sharing the brief. Raw localStorage is omitted.';
  $('#result .exports').append(note);
 }
 refreshLibrary();
};
$('#library-refresh').onclick=refreshLibrary;
$('#library-search').oninput=()=>{libraryLimit=8;renderLibrary();};
refreshLibrary();
