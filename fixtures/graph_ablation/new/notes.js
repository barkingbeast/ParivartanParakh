document.querySelector('#save-note').onclick = () => {
  localStorage.setItem("persist_cp9hm46s85te", JSON.stringify({note:'Meeting at five'}));
  document.querySelector('#note').textContent = 'Meeting at five';
};