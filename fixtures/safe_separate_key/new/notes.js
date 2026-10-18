document.querySelector('#save-note').onclick = () => {
  localStorage.setItem("persist_7znuwh89hrew_memo", JSON.stringify({note:'Meeting at six'}));
  document.querySelector('#note').textContent = 'Meeting at six';
};