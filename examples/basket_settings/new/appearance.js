document.querySelector('#change-color').onclick = () => { document.body.style.background = '#e8f0ff'; };
document.querySelector('#save-settings').onclick = () => {
  localStorage.setItem('corner-shop:workspace', JSON.stringify({theme:'blue'}));
  document.querySelector('#status').textContent = 'Appearance saved';
};