/* ============================================================
   财报分析 · 报告库  —  交互逻辑
   左侧：公司 / 期次树   右侧：报告 iframe
   路由：使用 location.hash  (#/companyId/reportId)，可直接分享链接
   ============================================================ */
(function () {
  "use strict";

  var LIB = window.REPORT_LIBRARY || { meta: {}, companies: [] };
  var companies = (LIB.companies || []).map(function (c) {
    return {
      id: c.id,
      name: c.name,
      code: c.code || "",
      sector: c.sector || "",
      short: c.short || c.name,
      reports: (c.reports || []).map(function (r) {
        var copy = {};
        for (var k in r) { if (Object.prototype.hasOwnProperty.call(r, k)) copy[k] = r[k]; }
        copy.companyId = c.id;
        copy.companyName = c.name;
        copy.companyCode = c.code || "";
        copy.sector = c.sector || "";
        copy.companyShort = c.short || c.name;
        return copy;
      })
    };
  });

  var flat = [];
  companies.forEach(function (c) {
    c.reports.forEach(function (r) {
      flat.push(r);
    });
  });

  var el = {
    rail: document.getElementById("rail"),
    tree: document.getElementById("tree"),
    stats: document.getElementById("railStats"),
    search: document.getElementById("search"),
    searchField: document.getElementById("searchField"),
    searchClear: document.getElementById("searchClear"),
    stage: document.getElementById("stage"),
    viewer: document.getElementById("viewer"),
    welcome: document.getElementById("welcome"),
    crumb: document.getElementById("crumb"),
    title: document.getElementById("topbarTitle"),
    actions: document.getElementById("topbarActions"),
    btnOpen: document.getElementById("btnOpen"),
    btnPdf: document.getElementById("btnPdf"),
    btnReload: document.getElementById("btnReload"),
    railToggle: document.getElementById("railToggle"),
    scrim: document.getElementById("scrim"),
    notice: document.getElementById("notice"),
    noticeText: document.getElementById("noticeText"),
    noticeClose: document.getElementById("noticeClose")
  };

  var state = { current: null, query: "", open: {} };

  /* ---------- 工具 ---------- */

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function isFileProtocol() {
    return location.protocol === "file:";
  }

  function reportHref(r) {
    return "#/" + encodeURIComponent(r.companyId) + "/" + encodeURIComponent(r.id);
  }

  function fmtDate(d) {
    if (!d) return "";
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d);
    if (!m) return d;
    return m[1] + " 年 " + Number(m[2]) + " 月 " + Number(m[3]) + " 日";
  }

  function matchReport(r, q) {
    if (!q) return true;
    var hay = [
      r.companyName, r.companyCode, r.companyShort, r.sector,
      r.title, r.period, r.periodNote, r.summary,
      (r.tags || []).join(" ")
    ].join(" ").toLowerCase();
    return hay.indexOf(q) !== -1;
  }

  /* ---------- 左侧栏渲染 ---------- */

  function renderStats() {
    var nRep = flat.length;
    var nCo = companies.length;
    el.stats.innerHTML =
      "<span><b>" + nCo + "</b> 家公司</span>" +
      "<span><b>" + nRep + "</b> 份报告</span>";
  }

  function renderTree() {
    var q = state.query.trim().toLowerCase();
    var html = "";
    var hits = 0;

    companies.forEach(function (c) {
      var reports = c.reports.filter(function (r) { return matchReport(r, q); });
      if (!reports.length) return;
      hits += reports.length;

      var activeHere = state.current && state.current.companyId === c.id;
      var open = q ? true : (state.open[c.id] || activeHere);

      html += '<li class="company' + (open ? " open" : "") + (activeHere ? " active" : "") +
        '" data-cid="' + esc(c.id) + '">';
      html += '<button class="company-head" type="button" aria-expanded="' + (open ? "true" : "false") + '">' +
        '<span class="company-flag"></span>' +
        '<span class="company-body">' +
        '<span class="company-name">' + esc(c.name) + "</span>" +
        '<span class="company-meta">' +
        (c.code ? '<span class="code">' + esc(c.code) + "</span>" : "") +
        (c.code && c.sector ? '<span class="dot">|</span>' : "") +
        (c.sector ? "<span>" + esc(c.sector) + "</span>" : "") +
        "</span></span>" +
        '<span class="company-count">' + reports.length + "</span>" +
        '<svg class="company-caret" width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">' +
        '<path d="M3 1.5 L7 5 L3 8.5" fill="none" stroke="currentColor" stroke-width="1.5" ' +
        'stroke-linecap="round" stroke-linejoin="round"/></svg>' +
        "</button>";

      html += '<ul class="report-list">';
      reports.forEach(function (r) {
        var active = state.current && state.current.id === r.id;
        html += '<li><a class="report-item' + (active ? " is-active" : "") + '" href="' + reportHref(r) +
          '" data-rid="' + esc(r.id) + '" data-cid="' + esc(c.id) + '">' +
          '<span class="report-item-period">' + esc(r.period) +
          (r.isNew ? '<span class="pill-live">NEW</span>' : "") + "</span>" +
          '<span class="report-item-note">' + esc(r.periodNote || r.title) + "</span>" +
          '<span class="report-item-foot">' +
          "<span>" + esc(r.publishedAt || "") + "</span>" +
          (r.pages ? '<span class="sep">·</span><span>' + r.pages + " 页</span>" : "") +
          "</span></a></li>";
      });
      html += "</ul></li>";
    });

    if (!html) {
      html = '<li class="rail-empty">没有匹配 <b>' + esc(state.query) + "</b> 的报告<br>" +
        "试试公司名、股票代码或期次</li>";
    }

    el.tree.innerHTML = html;
    el.tree.dataset.hits = String(hits);
  }

  function markActive() {
    Array.prototype.forEach.call(el.tree.querySelectorAll(".report-item"), function (a) {
      a.classList.toggle("is-active", !!state.current && a.dataset.rid === state.current.id);
    });
    Array.prototype.forEach.call(el.tree.querySelectorAll(".company"), function (li) {
      var here = !!state.current && li.dataset.cid === state.current.companyId;
      li.classList.toggle("active", here);
      if (here) {
        li.classList.add("open");
        var head = li.querySelector(".company-head");
        if (head) head.setAttribute("aria-expanded", "true");
      }
    });
  }

  /* ---------- 欢迎页 ---------- */

  function renderWelcome() {
    var totalPages = flat.reduce(function (a, r) { return a + (r.pages || 0); }, 0);
    var h = "";
    h += '<div class="welcome-inner">';
    h += '<div class="welcome-eyebrow">Financial Report Analysis Library</div>';
    h += "<h1>财报<em>分析</em>报告库</h1>";
    h += '<p class="welcome-lead">从左侧选择公司与期次，右侧即呈现该期次的完整分析报告。' +
      "所有报告均由原始定期报告数据抽取、跨期对齐后生成，含核心结论、多期财务数据对比表、趋势归因与风险提示。点击卡片或左侧条目即可切换。</p>";
    h += '<div class="welcome-stats">' +
      '<div class="welcome-stat"><b>' + companies.length + "</b><span>覆盖公司 / 组合</span></div>" +
      '<div class="welcome-stat"><b>' + flat.length + "</b><span>分析报告</span></div>" +
      '<div class="welcome-stat"><b>' + totalPages + "</b><span>PDF 页数</span></div>" +
      '<div class="welcome-stat"><b>' + esc(LIB.meta && LIB.meta.updatedAt ? LIB.meta.updatedAt : "") +
      "</b><span>最近更新</span></div>" +
      "</div>";

    h += '<div class="section-label">全部报告</div><div class="cards">';
    companies.forEach(function (c) {
      c.reports.forEach(function (r) {
        h += '<a class="card" href="' + reportHref(r) + '">';
        h += '<div class="card-head"><span class="card-co">' + esc(c.name) + "</span>" +
          (c.code ? '<span class="card-code">' + esc(c.code) + "</span>" : "") +
          (c.sector ? '<span class="card-sector">' + esc(c.sector) + "</span>" : "") + "</div>";
        h += '<div class="card-period">' + esc(r.period) + (r.periodNote ? " · " + esc(r.periodNote) : "") + "</div>";
        h += '<p class="card-summary">' + esc(r.summary || r.title) + "</p>";
        if (r.metrics && r.metrics.length) {
          h += '<div class="card-metrics">';
          r.metrics.slice(0, 4).forEach(function (m) {
            h += '<div class="card-metric"><b>' + esc(m.value) + "</b><span>" + esc(m.label) +
              (m.note ? " · " + esc(m.note) : "") + "</span></div>";
          });
          h += "</div>";
        }
        h += '<div class="card-foot"><span>生成于 ' + esc(r.publishedAt || "—") +
          (r.pages ? " · PDF " + r.pages + " 页" : "") +
          '</span><span class="card-cta">阅读报告' +
          '<svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true">' +
          '<path d="M3.5 2 L7.5 5.5 L3.5 9" fill="none" stroke="currentColor" stroke-width="1.6" ' +
          'stroke-linecap="round" stroke-linejoin="round"/></svg></span></div>';
        h += "</a>";
      });
    });
    h += "</div></div>";
    el.welcome.innerHTML = h;
  }

  /* ---------- 阅读器 ---------- */

  function setStage(mode) {
    el.stage.dataset.state = mode;
  }

  function showReport(r, opts) {
    opts = opts || {};
    state.current = r;
    state.open[r.companyId] = true;
    if (typeof history !== "undefined" && !opts.silent) {
      var hash = reportHref(r);
      if (location.hash !== hash) history.replaceState(null, "", hash);
    }

    el.crumb.innerHTML =
      '<span class="crumb-co">' + esc(r.companyName) + "</span>" +
      (r.companyCode ? '<span class="crumb-code">' + esc(r.companyCode) + "</span>" : "") +
      '<span aria-hidden="true">/</span><span>' + esc(r.period) + "</span>";

    el.title.textContent = r.title;

    el.btnOpen.href = r.html;
    el.btnOpen.hidden = false;
    if (r.pdf) {
      el.btnPdf.hidden = false;
      el.btnPdf.href = r.pdf;
    } else {
      el.btnPdf.hidden = true;
      el.btnPdf.removeAttribute("href");
    }
    el.btnReload.hidden = false;

    var raw = r.html;
    var src = isFileProtocol() ? raw : raw.split("/").map(encodeURIComponent).join("/");

    setStage("loading");
    el.viewer.onload = function () { setStage("ready"); };
    // 兜底：报告体量大 / 外部字体慢时不至于一直转圈
    clearTimeout(showReport._t);
    showReport._t = setTimeout(function () {
      if (el.stage.dataset.state === "loading") setStage("ready");
    }, 9000);
    el.viewer.src = src;

    markActive();
    if (window.innerWidth <= 880) closeRail();
  }

  function showWelcome() {
    state.current = null;
    if (location.hash && location.hash !== "#/") {
      try { history.replaceState(null, "", "#/"); } catch (err) { /* file:// 下忽略 */ }
    }
    el.crumb.innerHTML = '<span class="crumb-co">报告库</span><span aria-hidden="true">/</span><span>全部报告</span>';
    el.title.textContent = (LIB.meta && LIB.meta.title) || "财报分析 · 报告库";
    el.btnOpen.href = "reports/";
    el.btnOpen.hidden = true;
    el.btnPdf.hidden = true;
    el.btnReload.hidden = true;
    el.viewer.removeAttribute("src");
    setStage("empty");
    markActive();
  }

  /* ---------- 路由 ---------- */

  function findReport(cid, rid) {
    for (var i = 0; i < flat.length; i++) {
      if (flat[i].id === rid && (!cid || flat[i].companyId === cid)) return flat[i];
    }
    return null;
  }

  function route() {
    var hash = location.hash.replace(/^#\/?/, "");
    if (!hash) { showWelcome(); return; }
    var parts = hash.split("/").map(function (s) { return decodeURIComponent(s); });
    var r = findReport(parts[0], parts[1]);
    if (r) showReport(r, { silent: true });
    else showWelcome();
  }

  /* ---------- 事件 ---------- */

  el.tree.addEventListener("click", function (e) {
    var head = e.target.closest(".company-head");
    if (head) {
      var li = head.closest(".company");
      var cid = li.dataset.cid;
      var willOpen = !li.classList.contains("open");
      li.classList.toggle("open", willOpen);
      head.setAttribute("aria-expanded", willOpen ? "true" : "false");
      state.open[cid] = willOpen;
      return;
    }
    var item = e.target.closest(".report-item");
    if (item) {
      // 交给 hash 路由处理，这里只做即时反馈
      state.open[item.dataset.cid] = true;
    }
  });

  el.welcome.addEventListener("click", function (e) {
    // 卡片是 <a href="#/...">，hash 变化由 hashchange 驱动
  });

  el.search.addEventListener("input", function () {
    state.query = el.search.value;
    el.searchField.classList.toggle("has-value", !!state.query);
    renderTree();
  });

  el.search.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      el.search.value = "";
      state.query = "";
      el.searchField.classList.remove("has-value");
      renderTree();
      el.search.blur();
    }
    if (e.key === "Enter") {
      var first = el.tree.querySelector(".report-item");
      if (first) first.click();
    }
  });

  el.searchClear.addEventListener("click", function () {
    el.search.value = "";
    state.query = "";
    el.searchField.classList.remove("has-value");
    renderTree();
    el.search.focus();
  });

  el.btnReload.addEventListener("click", function () {
    if (state.current) showReport(state.current, { silent: true });
  });

  el.railToggle.addEventListener("click", function () {
    el.rail.classList.toggle("open");
    el.scrim.classList.toggle("show", el.rail.classList.contains("open"));
  });

  el.scrim.addEventListener("click", closeRail);

  function closeRail() {
    el.rail.classList.remove("open");
    el.scrim.classList.remove("show");
  }

  el.noticeClose.addEventListener("click", function () { el.notice.classList.remove("show"); });

  document.addEventListener("keydown", function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      el.rail.classList.add("open");
      el.scrim.classList.add("show");
      el.search.focus();
      el.search.select();
    }
    if (e.key === "Escape") closeRail();
  });

  window.addEventListener("hashchange", route);
  window.addEventListener("beforeprint", function () { if (state.current) el.viewer.contentWindow.print(); });

  /* ---------- 启动 ---------- */

  function boot() {
    renderStats();
    renderWelcome();
    route();
    if (!state.current) state.open[companies[0] ? companies[0].id : ""] = true;
    renderTree();
    markActive();
    if (isFileProtocol()) {
      el.noticeText.innerHTML = "当前以 <code>file://</code> 直接打开。若右侧报告空白，请在目录下执行 " +
        "<code>python3 -m http.server 8080</code> 后访问 <code>http://localhost:8080</code>。";
      el.notice.classList.add("show");
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
