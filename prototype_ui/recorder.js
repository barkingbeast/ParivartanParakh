(() => {
  const cfg = __RECORDER_CONFIG__;
  let selecting = false, seq = 0, pending = Promise.resolve();
  const send = payload => {
    payload.phase = cfg.phase; payload.seq = ++seq;
    pending = pending.then(() => fetch('/__record/events', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})).then(r => {if(!r.ok) throw Error('Recording event rejected');});
    pending.catch(() => parent.postMessage({type:'recording-error',session:cfg.id}, cfg.dashboard));
    return pending;
  };
  const trace = () => {const events = (window.__storageTrace || []).splice(0); if(events.length) send({kind:'trace',events});};
  const esc = value => CSS.escape(value);
  function selector(el) {
    if(el.id && !/\d{8,}/.test(el.id)) return '#'+esc(el.id);
    if(el.dataset.testid) return '[data-testid='+JSON.stringify(el.dataset.testid)+']';
    const parts=[];
    while(el && el !== document.documentElement) {
      let part=el.tagName.toLowerCase();
      if(el.id && !/\d{8,}/.test(el.id)) {parts.unshift('#'+esc(el.id)); break;}
      const classes=[...el.classList].filter(c=>!['completed','editing','selected','active','focus-enabled'].includes(c));
      if(classes.length) part += '.'+classes.slice(0,2).map(esc).join('.');
      if(el.parentElement) {
        const siblings=[...el.parentElement.children].filter(n=>n.tagName===el.tagName);
        if(siblings.length>1) part += ':nth-of-type('+(siblings.indexOf(el)+1)+')';
      }
      parts.unshift(part);
      const candidate=parts.join(' > ');
      if(document.querySelectorAll(candidate).length===1 && document.querySelector(candidate)===el) break;
      el=el.parentElement;
    }
    return parts.join(' > ');
  }
  function action(value) {if(cfg.phase==='seed'||cfg.phase==='trigger') send({kind:'action',action:value});}
  function pick(el) {
    if(el.matches('input[type="password"]')) {send({kind:'unsupported',message:'Password fields cannot be recorded or protected.'});return;}
    const row=el.closest('li,tr,[role="listitem"]');
    let target=selector(el);
    if(row && row.parentElement) target=selector(row.parentElement)+' > '+row.tagName.toLowerCase();
    const nodes=[...document.querySelectorAll(target)];
    const checks=node=>[...(node.matches('input[type="checkbox"]')?[node]:[]),...node.querySelectorAll('input[type="checkbox"]')];
    const checked=nodes.some(n=>checks(n).length);
    const value=!row && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) && !el.matches('input[type="checkbox"],input[type="password"]');
    const values=nodes.map(n=>{
      let text=value?String(n.value):n.textContent.replace(/\s+/g,' ').trim();
      if(checked) text+=' [checked='+checks(n).map(c=>String(c.checked)).join(',')+']';
      return text;
    });
    const storage=Object.fromEntries(Object.keys(localStorage).map(key=>[key,localStorage[key]]));
    trace();
    send({kind:'pick',candidate:{selector:target,values,checked,value},storage});
    parent.postMessage({type:'recording-picked',session:cfg.id},cfg.dashboard);
  }
  document.addEventListener('click',event=>{
    if(selecting) {event.preventDefault();event.stopImmediatePropagation();selecting=false;document.documentElement.style.cursor='';pick(event.target);return;}
    const el=event.target.closest('button,a,[role="button"],input[type="checkbox"],input[type="radio"],input[type="submit"]');
    if(!el || el.matches('input[type="password"]')) return;
    if(el.matches('a') && new URL(el.href,location.href).origin!==location.origin) {event.preventDefault();send({kind:'unsupported',message:'External navigation is outside this local recorder.'});return;}
    if(el.matches('input[type="checkbox"]')) action({type:el.checked?'check':'uncheck',selector:selector(el)});
    else if(el.matches('input[type="radio"]')) send({kind:'unsupported',message:'Radio actions are not supported by this recorder.'});
    else action({type:'click',selector:selector(el)});
  },true);
  document.addEventListener('input',event=>{
    const el=event.target;
    if(!el.matches('input,textarea') || el.matches('input[type="password"],input[type="checkbox"],input[type="radio"]')) return;
    action({type:'fill',selector:selector(el),value:el.value});
  },true);
  document.addEventListener('keydown',event=>{
    if(event.target.matches('input[type="password"]')) return;
    if(['Enter','Escape','Tab'].includes(event.key)) action({type:'press',selector:selector(event.target),key:event.key});
  },true);
  window.addEventListener('message',event=>{
    if(event.origin!==cfg.dashboard || event.source!==parent || event.data?.session!==cfg.id) return;
    if(event.data.type==='pick-observation') {selecting=true;document.documentElement.style.cursor='crosshair';}
    if(event.data.type==='flush-recording') {trace();pending.then(()=>parent.postMessage({type:'recording-flushed',session:cfg.id,request:event.data.request},cfg.dashboard));}
  });
  setInterval(trace,120);
  window.addEventListener('load',()=>parent.postMessage({type:'recording-ready',session:cfg.id},cfg.dashboard));
})();
