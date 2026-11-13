/* Floor board: tabs on a phone, the "change vehicle" sheet and the "add vehicle" sheet. */
(function () {
    'use strict';

    var root = document.querySelector('.fl');
    if (!root) { return; }

    /* ---- Tabs (phones only; wide screens show every column) ---- */
    var KEY = 'harithma.floor.tab';
    var tabs = root.querySelectorAll('[data-fl-tab]');
    var panes = root.querySelectorAll('[data-fl-pane]');

    function remember(name) { try { localStorage.setItem(KEY, name); } catch (e) { /* private mode */ } }
    function recall() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }

    function show(name) {
        Array.prototype.forEach.call(tabs, function (tab) {
            var on = tab.dataset.flTab === name;
            tab.classList.toggle('is-on', on);
            tab.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        Array.prototype.forEach.call(panes, function (pane) {
            pane.classList.toggle('is-on', pane.dataset.flPane === name);
        });
    }

    Array.prototype.forEach.call(tabs, function (tab) {
        tab.addEventListener('click', function () {
            show(tab.dataset.flTab);
            remember(tab.dataset.flTab);
            window.scrollTo(0, 0);
        });
    });
    var start = recall();
    show(root.querySelector('[data-fl-tab="' + start + '"]') ? start : 'bays');

    function modal(id) { return window.bootstrap.Modal.getOrCreateInstance(document.getElementById(id)); }
    function check(form, name, value) {
        Array.prototype.forEach.call(form.querySelectorAll('input[name="' + name + '"]'), function (input) {
            input.checked = String(input.value) === String(value);
        });
    }

    /* ---- Change a vehicle ---- */
    var editForm = document.getElementById('flEditForm');
    root.addEventListener('click', function (event) {
        var trigger = event.target.closest('[data-fl-edit]');
        if (!trigger) { return; }
        var d = trigger.dataset;
        editForm.action = d.url;
        editForm.querySelector('[data-fl-plate]').textContent = d.plate;
        editForm.querySelector('[data-fl-owner]').textContent = d.owner;
        editForm.querySelector('[data-fl-invoice]').href = d.invoice;
        check(editForm, 'status', d.status);
        check(editForm, 'washbay_id', d.bay);
        check(editForm, 'employee_id', d.emp);
        modal('flEdit').show();
    });

    /* ---- Add a vehicle ---- */
    var addForm = document.getElementById('flAddForm');
    var number = addForm.querySelector('[name="number"]');
    var vehicleId = addForm.querySelector('[name="vehicle_id"]');
    var matches = addForm.querySelector('[data-fl-matches]');
    var picked = addForm.querySelector('[data-fl-picked]');
    var fresh = addForm.querySelector('[data-fl-new]');
    var ownerName = addForm.querySelector('[name="name"]');
    var timer = null;
    var requestId = 0;

    function reset() {
        addForm.reset();
        vehicleId.value = '';
        matches.hidden = true;
        picked.hidden = true;
        fresh.hidden = true;
        ownerName.required = false;
    }

    function choose(item) {
        vehicleId.value = item.id;
        number.value = item.number;
        matches.hidden = true;
        fresh.hidden = true;
        ownerName.required = false;
        picked.textContent = '';
        var icon = document.createElement('i');
        icon.className = 'bi bi-check-circle-fill';
        picked.appendChild(icon);
        picked.appendChild(document.createTextNode(' ' + [item.sub, item.meta].filter(Boolean).join(' · ')));
        picked.hidden = false;
    }

    function lookup() {
        var q = number.value.trim();
        if (q.length < 2) { matches.hidden = true; fresh.hidden = true; return; }
        var id = ++requestId;
        fetch(number.dataset.search + '?q=' + encodeURIComponent(q), { credentials: 'same-origin', headers: { Accept: 'application/json' } })
            .then(function (r) { return r.ok ? r.json() : []; })
            .then(function (items) {
                if (id !== requestId) { return; }
                var typed = q.toUpperCase().replace(/\s+/g, ' ');
                var exact = items.filter(function (item) { return item.number === typed; })[0];
                if (exact) { choose(exact); return; }
                matches.innerHTML = '';
                items.slice(0, 5).forEach(function (item) {
                    var li = document.createElement('li');
                    var b = document.createElement('button');
                    b.type = 'button';
                    var plate = document.createElement('span');
                    plate.className = 'plate plate-sm';
                    plate.textContent = item.number;
                    var sub = document.createElement('span');
                    sub.textContent = item.sub || '';
                    b.appendChild(plate);
                    b.appendChild(sub);
                    b.addEventListener('click', function () { choose(item); });
                    li.appendChild(b);
                    matches.appendChild(li);
                });
                matches.hidden = !items.length;
                var looksNew = q.length >= 4;
                fresh.hidden = !looksNew;
                ownerName.required = looksNew;
            })
            .catch(function () { /* offline: the server still checks */ });
    }

    number.addEventListener('input', function () {
        vehicleId.value = '';
        picked.hidden = true;
        clearTimeout(timer);
        timer = setTimeout(lookup, 200);
    });

    Array.prototype.forEach.call(document.querySelectorAll('[data-fl-add]'), function (button) {
        button.addEventListener('click', function () {
            reset();
            if (button.dataset.bay) { check(addForm, 'washbay_id', button.dataset.bay); }
            modal('flAdd').show();
        });
    });
    document.getElementById('flAdd').addEventListener('shown.bs.modal', function () { number.focus(); });

    // One tap is enough: stop a second tap sending the same change twice.
    Array.prototype.forEach.call(document.querySelectorAll('.fl form, .fl-sheet form'), function (form) {
        form.addEventListener('submit', function () {
            setTimeout(function () {
                Array.prototype.forEach.call(form.querySelectorAll('button[type="submit"]'), function (b) { b.disabled = true; });
            }, 0);
        });
    });
})();
