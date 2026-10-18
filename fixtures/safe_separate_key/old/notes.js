document.querySelector('#save-note').onclick = () => {
  localStorage.setItem("persist_7znuwh89hrew_memo", JSON.stringify({note:'Meeting at five'}));
  document.querySelector('#note').textContent = 'Meeting at five';
};