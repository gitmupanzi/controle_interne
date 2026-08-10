(function () {
  var storageKey = "bb-doc-sidebar-collapsed-v2";

  function applyState(button, sidebar, search, collapsed) {
    document.body.classList.toggle("bb-sidebar-collapsed", collapsed);
    button.setAttribute("aria-expanded", String(!collapsed));
    button.setAttribute("aria-label", collapsed ? "Afficher le menu" : "Masquer le menu");
    button.setAttribute("title", collapsed ? "Afficher le menu" : "Masquer le menu");
    button.innerHTML = collapsed
      ? '<span class="bb-sidebar-toggle__icon" aria-hidden="true">☰</span>'
      : '<span class="bb-sidebar-toggle__icon" aria-hidden="true">&lt;</span><span>Masquer le menu</span>';
    if (collapsed) {
      document.body.appendChild(button);
    } else if (search) {
      search.appendChild(button);
    } else {
      sidebar.insertBefore(button, sidebar.firstChild);
    }
  }

  function setupSidebarToggle() {
    var sidebar = document.querySelector(".wy-nav-side");
    var search = document.querySelector(".wy-side-nav-search");
    var content = document.querySelector(".wy-nav-content-wrap");
    if (!sidebar || !content || document.querySelector(".bb-sidebar-toggle")) {
      return;
    }

    var button = document.createElement("button");
    button.type = "button";
    button.className = "bb-sidebar-toggle";
    button.setAttribute("aria-controls", "bb-doc-sidebar");

    sidebar.id = sidebar.id || "bb-doc-sidebar";

    var saved = window.localStorage.getItem(storageKey);
    var collapsed = saved === "1";
    applyState(button, sidebar, search, collapsed);

    button.addEventListener("click", function () {
      collapsed = !document.body.classList.contains("bb-sidebar-collapsed");
      window.localStorage.setItem(storageKey, collapsed ? "1" : "0");
      applyState(button, sidebar, search, collapsed);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupSidebarToggle);
  } else {
    setupSidebarToggle();
  }
})();
