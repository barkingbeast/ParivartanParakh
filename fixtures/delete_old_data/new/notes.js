document.querySelector('#save-note').onclick = () => {
  localStorage.removeItem("persist_kscqbkyjgyan");
  document.querySelector('#note').textContent = 'Meeting at five';
};