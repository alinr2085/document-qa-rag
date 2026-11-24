// برچسب ستون‌ها را روی سلول‌های جدول لیست می‌گذارد (برای نمای کارتی موبایل)
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("#result_list").forEach(function (table) {
    var labels = Array.from(table.querySelectorAll("thead th")).map(
      function (th) {
        var text = th.querySelector(".text");
        return (text || th).textContent.trim();
      },
    );
    table.querySelectorAll("tbody tr").forEach(function (row) {
      Array.from(row.children).forEach(function (cell, i) {
        if (labels[i]) cell.setAttribute("data-label", labels[i]);
      });
    });
  });
});
