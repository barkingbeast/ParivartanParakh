document.querySelector('#save-note').onclick = () => {
  localStorage.setItem("persist_6avvpjat56p8_memo", JSON.stringify({note:'Meeting at five'}));
  document.querySelector('#note').textContent = 'Meeting at five';
};