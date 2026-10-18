// State Survival extension; not upstream TodoMVC code.
document.querySelector('#preview-focus').onclick = () => {
  document.querySelector('.survival-lab').style.background = '#edf5ee';
};
document.querySelector('#save-focus').onclick = () => {
  const tasks = JSON.parse(localStorage.getItem('todos-vanilla-es6') || '[]');
  localStorage.setItem('todos-vanilla-es6', JSON.stringify(tasks.filter(task => !task.completed)));
  document.body.classList.add('focus-enabled');
  localStorage.setItem('state-survival:focus-preference', 'enabled');
  document.querySelector('#focus-status').textContent = 'Focus view saved';
};
