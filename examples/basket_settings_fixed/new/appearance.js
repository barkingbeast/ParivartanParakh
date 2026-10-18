document.querySelector('#change-color').onclick = () => { document.body.style.background = '#e8f0ff'; };
document.querySelector('#save-settings').onclick = () => {
  const workspace = JSON.parse(localStorage.getItem('corner-shop:workspace') || '{}');
  localStorage.setItem('corner-shop:workspace', JSON.stringify({...workspace,theme:'blue'}));
  document.querySelector('#status').textContent = 'Appearance saved';
};