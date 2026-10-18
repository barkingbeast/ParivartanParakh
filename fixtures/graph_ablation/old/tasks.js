const taskKey = "persist_cp9hm46s85te";
function renderTasks() {
  const raw = JSON.parse(localStorage.getItem(taskKey) || '{"tasks":[]}');
  document.querySelector('#tasks').replaceChildren(...(raw.tasks || []).map(t => {
    const li = document.createElement('li'); li.textContent = t; return li;
  }));
}
document.querySelector('#seed-tasks').onclick = () => {
  localStorage.setItem(taskKey, JSON.stringify({tasks:['Submit assignment','Buy groceries']}));
  renderTasks();
};
renderTasks();