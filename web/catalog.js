"use strict";
const search = document.getElementById("catalog-search");
const category = document.getElementById("catalog-category");
const rows = Array.from(document.querySelectorAll("#catalog-body tr"));
function filterCatalog() {
  const query = search.value.trim().toLocaleLowerCase();
  let count = 0;
  for (const row of rows) {
    const visible = (!category.value || row.dataset.category === category.value) &&
      (!query || row.dataset.search.toLocaleLowerCase().includes(query));
    row.hidden = !visible;
    if (visible) count += 1;
  }
  document.getElementById("catalog-count").textContent = `显示 ${count} / ${rows.length} 条规则`;
  document.getElementById("catalog-empty").hidden = count !== 0;
}
search.addEventListener("input", filterCatalog);
category.addEventListener("change", filterCatalog);
document.getElementById("catalog-reset").addEventListener("click", () => {
  search.value = "";
  category.value = "";
  filterCatalog();
});
filterCatalog();
