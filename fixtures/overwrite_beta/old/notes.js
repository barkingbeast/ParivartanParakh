document.querySelector('#save-note').onclick = () => {
  localStorage.setItem("persist_exj34y3r8ngz_memo", JSON.stringify({note:'Meeting at five'}));
  document.querySelector('#note').textContent = 'Meeting at five';
};