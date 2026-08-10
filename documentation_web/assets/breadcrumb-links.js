(function () {
  var sectionTargets = {
    "Perfect Vision": "perfect_vision/index.html",
    "Perfect Power BI": "perfect_power_bi/index.html",
    "Solution Numérique": "solution_numerique/index.html",
    "Formations": "formations/index.html",
    "Références communes": "transversal/glossaire.html",
    "Historique": "changelog/index.html",
    "FAQ": "faq.html",
    "Architecture globale": "architecture_globale.html"
  };

  function getHomeHref() {
    var homeLink = document.querySelector(".wy-breadcrumbs a.icon-home");
    return homeLink ? homeLink.getAttribute("href") : "index.html";
  }

  function buildAbsoluteHref(target) {
    try {
      var siteRoot = new URL(getHomeHref(), window.location.href);
      return new URL(target, siteRoot).href;
    } catch (error) {
      return target;
    }
  }

  function getFallbackSectionHref() {
    var path = window.location.pathname || "";
    var fileName = path.split("/").pop() || "";
    if (!fileName || fileName === "index.html") {
      return null;
    }
    return "index.html";
  }

  function enhanceBreadcrumbLinks() {
    var fallbackSectionHref = getFallbackSectionHref();

    var items = document.querySelectorAll(".wy-breadcrumbs .breadcrumb-item:not(.active)");
    items.forEach(function (item) {
      if (item.querySelector("a")) {
        return;
      }

      var label = item.textContent.trim();
      if (!label) {
        return;
      }

      var target = sectionTargets[label] || fallbackSectionHref;
      if (!target) {
        return;
      }

      var link = document.createElement("a");
      link.href = sectionTargets[label] ? buildAbsoluteHref(target) : target;
      link.className = "bb-breadcrumb-link";
      link.textContent = label;

      item.textContent = "";
      item.appendChild(link);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhanceBreadcrumbLinks);
  } else {
    enhanceBreadcrumbLinks();
  }
})();
