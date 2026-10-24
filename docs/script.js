/* Shared behaviors for the docs site */
(function () {
  "use strict";
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return; // disabled animations
  }

  // Scroll reveals
  var io = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    },
    { threshold: 0.12 }
  );
  document.querySelectorAll(".reveal").forEach(function (el) { io.observe(el); });

  // 3D tilt on hero stat cards
  var stack = document.querySelector(".float-stack");
  if (stack) {
    var cards = stack.querySelectorAll(".fcard");
    stack.addEventListener("mousemove", function (ev) {
      var r = stack.getBoundingClientRect();
      var px = (ev.clientX - r.left) / r.width - 0.5;
      var py = (ev.clientY - r.top) / r.height - 0.5;
      cards.forEach(function (c, i) {
        var rot = i % 2 === 0 ? -1 : 1;
        c.style.transform =
          "translateZ(90px) rotateY(" + (px * 18 * rot).toFixed(1) + "deg) rotateX(" +
          (-py * 12).toFixed(1) + "deg)";
      });
    });
    stack.addEventListener("mouseleave", function () {
      cards.forEach(function (c, i) {
        c.style.transform = "";
        void c.offsetWidth; // restart hover styles cleanly
      });
    });
  }

  // Count-up animation for [data-count]
  var cio = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var el = e.target;
        cio.unobserve(el);
        var target = parseInt(el.getAttribute("data-count"), 10);
        if (isNaN(target)) return;
        var dur = 1200, t0 = null;
        function step(ts) {
          if (!t0) t0 = ts;
          var p = Math.min((ts - t0) / dur, 1);
          var eased = 1 - Math.pow(1 - p, 3);
          el.textContent = Math.round(target * eased).toLocaleString("en-US");
          if (p < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      });
    },
    { threshold: 0.5 }
  );
  document.querySelectorAll("[data-count]").forEach(function (el) { cio.observe(el); });

  // Copy buttons
  document.querySelectorAll(".copybtn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var pre = btn.closest("pre") || btn.parentNode.querySelector("pre");
      var txt = pre ? pre.innerText.trim() : "";
      if (navigator.clipboard && txt) {
        navigator.clipboard.writeText(txt).then(function () {
          btn.textContent = "copied";
          setTimeout(function () { btn.textContent = "copy"; }, 1400);
        });
      }
    });
  });
})();