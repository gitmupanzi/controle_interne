(function () {
  function renderMermaidBlocks() {
    if (!window.mermaid) {
      return;
    }
    window.mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });
    document.querySelectorAll("pre code.language-mermaid").forEach(function (code, index) {
      var wrapper = document.createElement("div");
      wrapper.className = "mermaid";
      wrapper.textContent = code.textContent;
      wrapper.id = "mermaid-diagram-" + index;
      code.parentElement.replaceWith(wrapper);
    });
    window.mermaid.run();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderMermaidBlocks);
  } else {
    renderMermaidBlocks();
  }
})();
