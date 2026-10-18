document.querySelector('#save-note').onclick = () => {
  const saved = JSON.parse(localStorage.getItem("persist_6avvpjat56p8") || '{}');
  localStorage.setItem("persist_6avvpjat56p8", JSON.stringify({...saved, note:'Meeting at five'}));
  document.querySelector('#note').textContent = 'Meeting at five';
};