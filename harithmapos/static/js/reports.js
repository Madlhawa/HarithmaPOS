/* Sales report: the revenue-over-time chart and the shared tooltip.
   No chart library: a small SVG drawn from the JSON the page carries.
   Every value shown here is also in the "Show as a table" view. */
(function () {
    'use strict';

    var currency = document.body.dataset.currency || 'Rs.';
    var tip = document.getElementById('chartTip');
    var SVG = 'http://www.w3.org/2000/svg';

    function full(n) {
        return currency + ' ' + Math.round(n).toLocaleString('en-US');
    }
    function compact(n) {
        if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 === 0 ? 0 : 1) + 'M';
        if (n >= 1e4) return Math.round(n / 1e3) + 'K';
        if (n >= 1e3) return (n / 1e3).toFixed(n % 1e3 === 0 ? 0 : 1) + 'K';
        return String(Math.round(n));
    }
    function niceStep(max, count) {
        var raw = max / count;
        var mag = Math.pow(10, Math.floor(Math.log10(raw || 1)));
        var steps = [1, 2, 2.5, 5, 10];
        for (var i = 0; i < steps.length; i++) {
            if (steps[i] * mag >= raw) return steps[i] * mag;
        }
        return 10 * mag;
    }
    function el(name, attrs) {
        var node = document.createElementNS(SVG, name);
        Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
        return node;
    }

    /* ---- tooltip: value first, label after; text only, never HTML ---- */
    function showTip(lines, x, y) {
        if (!tip) return;
        tip.replaceChildren();
        lines.forEach(function (line, i) {
            var row = document.createElement('div');
            row.className = i === 0 ? 'tip-title' : 'tip-row';
            if (line.key) {
                var key = document.createElement('i');
                key.className = 'tip-key ' + line.key;
                row.appendChild(key);
            }
            if (line.value) {
                var v = document.createElement('strong');
                v.textContent = line.value;
                row.appendChild(v);
            }
            if (line.label) {
                var l = document.createElement('span');
                l.textContent = line.label;
                row.appendChild(l);
            }
            tip.appendChild(row);
        });
        tip.hidden = false;
        var w = tip.offsetWidth, h = tip.offsetHeight;
        var left = Math.min(Math.max(8, x + 14), window.innerWidth - w - 8);
        var top = y - h - 12 < 8 ? y + 18 : y - h - 12;
        tip.style.left = left + 'px';
        tip.style.top = top + 'px';
    }
    function hideTip() { if (tip) tip.hidden = true; }

    /* Ranked bars and heatmap cells: data-tip="title|value|detail". */
    function tipFor(node) {
        var parts = (node.getAttribute('data-tip') || '').split('|');
        return [{ label: parts[0] }, { value: parts[1], label: '' }].concat(parts[2] ? [{ label: parts[2] }] : []);
    }
    document.querySelectorAll('[data-tip]').forEach(function (node) {
        node.addEventListener('pointermove', function (e) { showTip(tipFor(node), e.clientX, e.clientY); });
        node.addEventListener('pointerleave', hideTip);
        node.addEventListener('focus', function () {
            var r = node.getBoundingClientRect();
            showTip(tipFor(node), r.left + r.width / 2, r.top);
        });
        node.addEventListener('blur', hideTip);
    });
    window.addEventListener('scroll', hideTip, { passive: true });

    /* ---- revenue over time: stacked columns ---- */
    /* ---- stacked columns, configured on the element ----
       <div class="viz chart-stacked" data-stacked="json-script-id"
            data-series='[{"key":"services","label":"services","cls":"fill-1","key_cls":"key-1"}, ...]'
            data-money="1" data-note-key="jobs" data-note-label="job"></div> */
    function stacked(host) {
        var dataNode = document.getElementById(host.dataset.stacked);
        if (!dataNode) return;
        var rows = JSON.parse(dataNode.textContent).rows || [];
        var series = JSON.parse(host.dataset.series || '[]');
        var money = host.dataset.money === '1';
        var fmt = money ? full : function (n) { return Math.round(n).toLocaleString('en-US'); };
        var noteKey = host.dataset.noteKey, noteLabel = host.dataset.noteLabel;
        if (!rows.length) { host.textContent = 'Nothing to show for this period.'; return; }

        function draw() {
            var width = Math.max(host.clientWidth, 280);
            var height = 260;
            var m = { top: 24, right: 8, bottom: 28, left: 44 };
            var plotW = width - m.left - m.right;
            var plotH = height - m.top - m.bottom;
            var totals = rows.map(function (r) { return series.reduce(function (t, s) { return t + (r[s.key] || 0); }, 0); });
            var maxV = Math.max.apply(null, totals.concat([1]));
            var step = niceStep(maxV, 4);
            if (!money && step < 1) step = 1;
            var top = Math.ceil(maxV / step) * step;
            var y = function (v) { return m.top + plotH - (v / top) * plotH; };
            var band = plotW / rows.length;
            var barW = Math.max(2, Math.min(24, band * 0.62));
            var svg = el('svg', { width: width, height: height, viewBox: '0 0 ' + width + ' ' + height });

            for (var v = 0; v <= top + 0.5; v += step) {
                svg.appendChild(el('line', { x1: m.left, x2: width - m.right, y1: y(v), y2: y(v), class: v === 0 ? 'axis' : 'grid' }));
                var t = el('text', { x: m.left - 8, y: y(v) + 4, 'text-anchor': 'end', class: 'tick' });
                t.textContent = compact(v);
                svg.appendChild(t);
            }
            var labelEvery = Math.max(1, Math.ceil(58 / band));
            rows.forEach(function (r, i) {
                if (i % labelEvery !== 0) return;
                var t = el('text', { x: m.left + band * i + band / 2, y: height - 8, 'text-anchor': 'middle', class: 'tick' });
                t.textContent = r.short;
                svg.appendChild(t);
            });

            var peak = totals.indexOf(maxV);
            rows.forEach(function (r, i) {
                var cx = m.left + band * i + band / 2;
                var x = cx - barW / 2;
                var g = el('g', { class: 'col', tabindex: '0' });
                var parts = series.filter(function (s) { return (r[s.key] || 0) > 0; });
                var cursor = y(0);
                parts.forEach(function (s, j) {
                    var hgt = (r[s.key] / top) * plotH;
                    var gap = j > 0 ? 2 : 0;
                    var segTop = cursor - hgt;
                    var drawH = Math.max(hgt - gap, 1);
                    var isTop = j === parts.length - 1;
                    var radius = Math.min(4, drawH, barW / 2);
                    var path = isTop
                        ? 'M' + x + ',' + (segTop + drawH) + 'V' + (segTop + radius) +
                          'Q' + x + ',' + segTop + ' ' + (x + radius) + ',' + segTop +
                          'H' + (x + barW - radius) + 'Q' + (x + barW) + ',' + segTop + ' ' + (x + barW) + ',' + (segTop + radius) +
                          'V' + (segTop + drawH) + 'Z'
                        : 'M' + x + ',' + segTop + 'H' + (x + barW) + 'V' + (segTop + drawH) + 'H' + x + 'Z';
                    g.appendChild(el('path', { d: path, class: s.cls }));
                    cursor = segTop;
                });
                var hit = el('rect', { x: m.left + band * i, y: m.top, width: band, height: plotH, class: 'hit' });
                g.appendChild(hit);
                var lines = [{ label: r.span }, { value: fmt(totals[i]), label: ' total' }];
                series.forEach(function (s) {
                    var extra = (noteKey && s === series[0]) ? ' · ' + r[noteKey] + ' ' + noteLabel + (r[noteKey] === 1 ? '' : 's') : '';
                    lines.push({ key: s.key_cls, value: fmt(r[s.key] || 0), label: ' ' + s.label + extra });
                });
                g.addEventListener('pointermove', function (e) { showTip(lines, e.clientX, e.clientY); g.classList.add('is-hover'); });
                g.addEventListener('pointerleave', function () { hideTip(); g.classList.remove('is-hover'); });
                g.addEventListener('focus', function () {
                    var b = hit.getBoundingClientRect();
                    showTip(lines, b.left + b.width / 2, b.top + b.height / 3);
                    g.classList.add('is-hover');
                });
                g.addEventListener('blur', function () { hideTip(); g.classList.remove('is-hover'); });
                g.setAttribute('aria-label', r.span + ': ' + fmt(totals[i]));
                svg.appendChild(g);
                if (i === peak && maxV > 0) {
                    var lbl = el('text', { x: cx, y: y(maxV) - 8, 'text-anchor': 'middle', class: 'peak' });
                    lbl.textContent = money ? compact(maxV) : String(Math.round(maxV));
                    svg.appendChild(lbl);
                }
            });
            host.replaceChildren(svg);
        }
        draw();
        var resizeTimer;
        window.addEventListener('resize', function () {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(draw, 120);
        });
    }
    document.querySelectorAll('[data-stacked]').forEach(stacked);
})();
