document.querySelector('#save-note').onclick = () => {
  localStorage.setItem("persist_kscqbkyjgyan_memo", JSON.stringify({note:'Meeting at five'}));
  document.querySelector('#note').textContent = 'Meeting at five';
};