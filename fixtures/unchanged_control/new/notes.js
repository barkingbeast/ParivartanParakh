document.querySelector('#save-note').onclick = () => {
  localStorage.setItem("persist_zfdn2k6vsvut_memo", JSON.stringify({note:'Meeting at five'}));
  document.querySelector('#note').textContent = 'Meeting at five';
};