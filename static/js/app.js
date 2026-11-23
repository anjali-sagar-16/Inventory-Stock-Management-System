// Confirmation for destructive actions (NFR-01) and dynamic sale lines.
document.addEventListener("submit", function (e) {
  var msg = e.target.getAttribute("data-confirm");
  if (msg && !window.confirm(msg)) e.preventDefault();
});

(function () {
  var body = document.querySelector("#lines tbody");
  if (!body) return;
  var template = body.querySelector("tr.line").cloneNode(true);

  function recalc() {
    var grand = 0;
    body.querySelectorAll("tr.line").forEach(function (row) {
      var opt = row.querySelector("select").selectedOptions[0];
      var price = opt && opt.dataset.price !== "" && opt.dataset.price !== undefined ? parseFloat(opt.dataset.price) : NaN;
      var qty = parseInt(row.querySelector("input").value, 10);
      row.querySelector(".price").textContent = isNaN(price) ? "—" : price.toFixed(2);
      if (!isNaN(price) && qty > 0) {
        var t = price * qty; grand += t;
        row.querySelector(".line-total").textContent = t.toFixed(2);
      } else row.querySelector(".line-total").textContent = "—";
    });
    document.getElementById("grand").textContent = grand.toFixed(2);
  }
  body.addEventListener("input", recalc);
  body.addEventListener("change", recalc);
  body.addEventListener("click", function (e) {
    if (e.target.classList.contains("remove-line")) {
      if (body.querySelectorAll("tr.line").length > 1) { e.target.closest("tr").remove(); recalc(); }
    }
  });
  document.getElementById("add-line").addEventListener("click", function () {
    var row = template.cloneNode(true);
    row.querySelector("select").selectedIndex = 0;
    row.querySelector("input").value = "";
    body.appendChild(row); recalc();
  });
  recalc();
})();
