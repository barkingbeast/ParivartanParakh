const basketStorage = 'corner-shop:workspace';
function showBasket() {
  const workspace = JSON.parse(localStorage.getItem(basketStorage) || '{}');
  document.querySelector('#basket').replaceChildren(...(workspace.basket || []).map(item => {
    const row = document.createElement('li'); row.textContent = item; return row;
  }));
}
document.querySelector('#add-items').onclick = () => {
  localStorage.setItem(basketStorage, JSON.stringify({basket:['Sourdough bread','Oat milk']}));
  showBasket();
};
showBasket();