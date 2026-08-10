(function () {
  var storageKey = "bb-doc-sidebar-collapsed-v2";

  function getStoredState() {
    try {
      return window.localStorage.getItem(storageKey) === "1";
    } catch (error) {
      return false;
    }
  }

  function setStoredState(collapsed) {
    try {
      window.localStorage.setItem(storageKey, collapsed ? "1" : "0");
    } catch (error) {
      // Le site reste utilisable même si le navigateur bloque le stockage local.
    }
  }

  function getCollapsedPadding() {
    return window.innerWidth <= 900 ? "4.2rem" : "4.4rem";
  }

  function applyContentOffset(contentInner, collapsed) {
    if (!contentInner) {
      return;
    }
    contentInner.style.paddingLeft = collapsed ? getCollapsedPadding() : "";
  }

  function applyState(button, sidebar, search, contentInner, collapsed) {
    document.body.classList.toggle("bb-sidebar-collapsed", collapsed);
    applyContentOffset(contentInner, collapsed);
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
    var contentInner = document.querySelector(".wy-nav-content");
    if (!sidebar || !content || document.querySelector(".bb-sidebar-toggle")) {
      return;
    }

    var button = document.createElement("button");
    button.type = "button";
    button.className = "bb-sidebar-toggle";
    button.setAttribute("aria-controls", "bb-doc-sidebar");

    sidebar.id = sidebar.id || "bb-doc-sidebar";

    var collapsed = getStoredState();
    applyState(button, sidebar, search, contentInner, collapsed);

    button.addEventListener("click", function () {
      collapsed = !document.body.classList.contains("bb-sidebar-collapsed");
      setStoredState(collapsed);
      applyState(button, sidebar, search, contentInner, collapsed);
    });

    window.addEventListener("resize", function () {
      applyContentOffset(contentInner, document.body.classList.contains("bb-sidebar-collapsed"));
    });

    window.addEventListener("pageshow", function () {
      collapsed = getStoredState();
      applyState(button, sidebar, search, contentInner, collapsed);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupSidebarToggle);
  } else {
    setupSidebarToggle();
  }
})();
