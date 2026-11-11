/* Harithma POS front-end behaviour.
 *
 * Everything is wired up from data-attributes in the templates, so pages
 * need no inline scripts:
 *
 *   <div class="ac" data-ac-url="/app/search/vehicles">   search-as-you-type box
 *   <form data-confirm="Delete this?">                    ask before submitting
 *   <button data-edit-modal="#modal" data-values='{…}'>   open a modal pre-filled
 *   <time data-since="2026-01-01T08:00:00Z">              running "1h 05m" clock
 */
(function () {
    'use strict';

    var currency = document.body.dataset.currency || 'Rs.';

    function debounce(fn, wait) {
        var timer = null;
        return function () {
            clearTimeout(timer);
            timer = setTimeout(fn, wait);
        };
    }

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) { node.className = className; }
        if (text !== undefined && text !== null) { node.textContent = text; }
        return node;
    }

    /* ---------------------------------------------------------------------
     * Search-as-you-type
     *
     * Markup (see the autocomplete macro in layout/macros.html):
     *   <div class="ac" data-ac-url="…" [data-ac-show-all] [data-ac-optional]>
     *     <input type="text" …>      what the person sees and types into
     *     <input type="hidden" …>    the id that is sent to the server
     *     <ul class="ac-menu" hidden></ul>
     *   </div>
     *
     * The hidden id is only ever set by picking a row, and typing clears it,
     * so the server never has to guess an id from free text.
     * ------------------------------------------------------------------- */
    var acCounter = 0;

    function initAutocomplete(root) {
        if (root.dataset.acReady) { return; }
        var input = root.querySelector('input[type="text"], input[type="search"]');
        var hidden = root.querySelector('input[type="hidden"]');
        var menu = root.querySelector('.ac-menu');
        if (!input || !hidden || !menu) { return; }
        root.dataset.acReady = '1';

        var url = root.dataset.acUrl;
        var showAll = root.hasAttribute('data-ac-show-all');
        var optional = root.hasAttribute('data-ac-optional');
        var items = [];
        var active = -1;
        var requestId = 0;
        var menuId = 'ac-menu-' + (++acCounter);

        menu.id = menuId;
        menu.setAttribute('role', 'listbox');
        input.setAttribute('role', 'combobox');
        input.setAttribute('aria-autocomplete', 'list');
        input.setAttribute('aria-expanded', 'false');
        input.setAttribute('aria-controls', menuId);
        input.setAttribute('autocomplete', 'off');
        root.classList.toggle('is-picked', hidden.value !== '');

        function close() {
            menu.hidden = true;
            active = -1;
            input.setAttribute('aria-expanded', 'false');
            input.removeAttribute('aria-activedescendant');
        }

        function open() {
            menu.hidden = false;
            input.setAttribute('aria-expanded', 'true');
        }

        function setActive(index) {
            active = index;
            Array.prototype.forEach.call(menu.querySelectorAll('.ac-option'), function (option, i) {
                var on = i === index;
                option.classList.toggle('is-active', on);
                option.setAttribute('aria-selected', on ? 'true' : 'false');
                if (on) {
                    input.setAttribute('aria-activedescendant', option.id);
                    if (option.scrollIntoView) { option.scrollIntoView({ block: 'nearest' }); }
                }
            });
        }

        function labelOf(item) {
            return item.label || item.name || item.number || '';
        }

        function pick(index) {
            var item = items[index];
            if (!item) { return; }
            input.value = labelOf(item);
            hidden.value = item.id;
            input.setCustomValidity('');
            root.classList.add('is-picked');
            close();
            root.dispatchEvent(new CustomEvent('ac:select', { bubbles: true, detail: item }));
        }

        function render() {
            menu.innerHTML = '';
            if (!items.length) {
                menu.appendChild(el('li', 'ac-empty', root.dataset.acEmpty || 'Nothing found. Check the spelling.'));
                open();
                return;
            }
            items.forEach(function (item, index) {
                var option = el('li', 'ac-option');
                option.id = menuId + '-' + index;
                option.setAttribute('role', 'option');
                option.appendChild(el('span', 'ac-option-label', labelOf(item)));
                if (item.meta) { option.appendChild(el('span', 'ac-option-meta', item.meta)); }
                if (item.sub) { option.appendChild(el('span', 'ac-option-sub', item.sub)); }
                // mousedown, not click: it fires before the input loses focus.
                option.addEventListener('mousedown', function (event) {
                    event.preventDefault();
                    pick(index);
                });
                menu.appendChild(option);
            });
            open();
            setActive(0);
        }

        function fetchItems() {
            var query = input.value.trim();
            if (!query && !showAll) { close(); return; }
            var id = ++requestId;
            fetch(url + '?q=' + encodeURIComponent(query), {
                headers: { 'Accept': 'application/json' },
                credentials: 'same-origin'
            })
                .then(function (response) { return response.ok ? response.json() : []; })
                .then(function (data) {
                    if (id !== requestId) { return; }   // a newer search is already on its way
                    items = Array.isArray(data) ? data : [];
                    render();
                })
                .catch(function () { if (id === requestId) { close(); } });
        }

        var search = debounce(fetchItems, 180);

        input.addEventListener('input', function () {
            if (hidden.value !== '') {
                hidden.value = '';
                root.dispatchEvent(new CustomEvent('ac:clear', { bubbles: true }));
            }
            root.classList.remove('is-picked');
            input.setCustomValidity('');
            search();
        });

        input.addEventListener('focus', function () {
            if (showAll && hidden.value === '') { fetchItems(); }
        });

        input.addEventListener('keydown', function (event) {
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                if (menu.hidden) { fetchItems(); } else { setActive(Math.min(active + 1, items.length - 1)); }
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                if (!menu.hidden) { setActive(Math.max(active - 1, 0)); }
            } else if (event.key === 'Enter') {
                if (!menu.hidden && items.length) {
                    event.preventDefault();
                    pick(active >= 0 ? active : 0);
                }
            } else if (event.key === 'Tab') {
                if (!menu.hidden && items.length && active >= 0) { pick(active); }
            } else if (event.key === 'Escape') {
                if (!menu.hidden) {
                    event.stopPropagation();   // close the list, not the modal around it
                    close();
                }
            }
        });

        input.addEventListener('blur', function () { setTimeout(close, 150); });

        if (input.form) {
            input.form.addEventListener('submit', function (event) {
                var typed = input.value.trim() !== '';
                var missing = hidden.value === '';
                if (missing && (typed || !optional)) {
                    event.preventDefault();
                    input.setCustomValidity(root.dataset.acMessage || 'Choose one from the list.');
                    input.reportValidity();
                }
            });
        }
    }

    function initAll(scope) {
        Array.prototype.forEach.call((scope || document).querySelectorAll('.ac[data-ac-url]'), initAutocomplete);
    }

    /* Set an autocomplete from code (used when a modal is opened pre-filled). */
    function setAutocomplete(root, id, label) {
        var input = root.querySelector('input[type="text"], input[type="search"]');
        var hidden = root.querySelector('input[type="hidden"]');
        if (!input || !hidden) { return; }
        input.value = label || '';
        hidden.value = (id === null || id === undefined) ? '' : id;
        input.setCustomValidity('');
        root.classList.toggle('is-picked', hidden.value !== '');
    }

    /* ---------------------------------------------------------------------
     * Item entry row on invoices and purchase orders: after an item is
     * picked, show its price and stock and jump to the quantity box.
     * ------------------------------------------------------------------- */
    document.addEventListener('ac:select', function (event) {
        var form = event.target.closest('form[data-entry]');
        if (!form) { return; }
        var item = event.detail || {};
        var hint = form.parentNode.querySelector('[data-entry-hint]');
        var parts = [];
        if (item.meta) { parts.push(currency + ' ' + item.meta + ' each'); }
        if (Number(item.discount_pct) > 0) { parts.push(Number(item.discount_pct) + '% item discount'); }
        if (item.sub) { parts.push(item.sub); }
        if (hint) { hint.textContent = parts.join(', '); }

        var uom = form.querySelector('[data-uom]');
        if (uom) { uom.textContent = item.unit_of_measure || 'Qty'; }

        var cost = form.querySelector('input[name="unit_cost"]');
        if (cost && item.cost !== undefined && item.cost !== null) { cost.value = item.cost; }

        var quantity = form.querySelector('input[name="quantity"]');
        if (quantity) { quantity.focus(); quantity.select(); }
    });

    document.addEventListener('ac:clear', function (event) {
        var form = event.target.closest('form[data-entry]');
        if (!form) { return; }
        var hint = form.parentNode.querySelector('[data-entry-hint]');
        if (hint) { hint.textContent = ''; }
        var uom = form.querySelector('[data-uom]');
        if (uom) { uom.textContent = 'Qty'; }
    });

    /* ---------------------------------------------------------------------
     * Forms: confirm before destructive actions, and ignore double clicks.
     * ------------------------------------------------------------------- */
    document.addEventListener('submit', function (event) {
        if (event.defaultPrevented) { return; }
        var form = event.target;
        var submitter = event.submitter;
        var message = (submitter && submitter.dataset.confirm) || form.dataset.confirm;
        if (message && !window.confirm(message)) {
            event.preventDefault();
        }
    });

    document.addEventListener('submit', function (event) {
        if (event.defaultPrevented) { return; }
        var form = event.target;
        if (form.method && form.method.toLowerCase() === 'get') { return; }
        if (form.dataset.submitting) {
            event.preventDefault();
            return;
        }
        form.dataset.submitting = '1';
    });

    // Coming back with the browser's Back button: let the form be used again.
    window.addEventListener('pageshow', function () {
        Array.prototype.forEach.call(document.querySelectorAll('form[data-submitting]'), function (form) {
            delete form.dataset.submitting;
        });
    });

    /* ---------------------------------------------------------------------
     * Edit modals: one modal per page, filled from the row's button.
     *   <button data-edit-modal="#itemModal"
     *           data-action="/app/item/5/update"
     *           data-values='{"name": "Engine oil", …}'>
     * ------------------------------------------------------------------- */
    function fillForm(form, values) {
        Object.keys(values).forEach(function (name) {
            var raw = values[name];
            var value = (raw === null || raw === undefined) ? '' : String(raw);
            var fields = form.querySelectorAll('[name="' + name.replace(/"/g, '\\"') + '"]');
            Array.prototype.forEach.call(fields, function (field) {
                if (field.type === 'radio') {
                    field.checked = field.value === value;
                } else if (field.type === 'checkbox') {
                    field.checked = Boolean(raw);
                } else if (field.tagName === 'SELECT') {
                    var known = Array.prototype.some.call(field.options, function (option) { return option.value === value; });
                    if (!known && value !== '') { field.add(new Option(value, value)); }
                    field.value = value;
                } else if (field.type !== 'file') {
                    field.value = value;
                }
            });
        });
    }

    function syncStockToggle(form) {
        var toggle = form.querySelector('[data-stock-toggle]');
        var quantity = form.querySelector('input[name="quantity"]');
        if (!toggle || !quantity) { return; }
        quantity.disabled = !toggle.checked;
        if (!toggle.checked) { quantity.value = ''; }
    }

    document.addEventListener('click', function (event) {
        var trigger = event.target.closest('[data-edit-modal]');
        if (!trigger) { return; }
        event.preventDefault();
        var modal = document.querySelector(trigger.dataset.editModal);
        if (!modal) { return; }
        var form = modal.querySelector('form');
        var values = {};
        try { values = JSON.parse(trigger.dataset.values || '{}'); } catch (error) { values = {}; }

        if (form) {
            form.reset();
            delete form.dataset.submitting;
            if (trigger.dataset.action) { form.action = trigger.dataset.action; }
            fillForm(form, values);
            Array.prototype.forEach.call(form.querySelectorAll('.ac'), function (root) {
                var hidden = root.querySelector('input[type="hidden"]');
                root.classList.toggle('is-picked', Boolean(hidden && hidden.value !== ''));
            });
            var toggle = form.querySelector('[data-stock-toggle]');
            if (toggle) {
                toggle.checked = values.quantity !== null && values.quantity !== undefined && values.quantity !== '';
                syncStockToggle(form);
            }
        }
        Array.prototype.forEach.call(modal.querySelectorAll('[data-fill]'), function (node) {
            var value = values[node.dataset.fill];
            node.textContent = (value === null || value === undefined) ? '' : value;
        });
        Array.prototype.forEach.call(modal.querySelectorAll('form[data-action-from]'), function (extraForm) {
            var action = trigger.getAttribute('data-' + extraForm.dataset.actionFrom);
            if (action) { extraForm.action = action; }
        });
        window.bootstrap.Modal.getOrCreateInstance(modal).show();
    });

    document.addEventListener('change', function (event) {
        if (event.target.matches('[data-stock-toggle]')) {
            var form = event.target.form;
            syncStockToggle(form);
            var quantity = form.querySelector('input[name="quantity"]');
            if (event.target.checked && quantity) {
                if (quantity.value === '') { quantity.value = '0'; }
                quantity.focus();
                quantity.select();
            }
        }
    });

    /* ---------------------------------------------------------------------
     * Dashboard: "Start a service here" on a free bay opens the new-service
     * modal with that bay already chosen.
     * ------------------------------------------------------------------- */
    document.addEventListener('click', function (event) {
        var trigger = event.target.closest('[data-start-in-bay]');
        if (!trigger) { return; }
        var modal = document.getElementById('newServiceModal');
        if (!modal) { return; }
        var bayBox = modal.querySelector('.ac[data-ac-name="washbay"]');
        if (bayBox) { setAutocomplete(bayBox, trigger.dataset.startInBay, trigger.dataset.bayName); }
        window.bootstrap.Modal.getOrCreateInstance(modal).show();
    });

    // Put the cursor in the right box when a modal opens.
    document.addEventListener('shown.bs.modal', function (event) {
        var target = event.target.querySelector('[data-autofocus]');
        if (!target) { return; }
        var box = target.closest('.ac');
        var hidden = box && box.querySelector('input[type="hidden"]');
        if (hidden && hidden.value !== '') {
            // Already chosen: move on to the next empty search box instead.
            var next = Array.prototype.filter.call(event.target.querySelectorAll('.ac'), function (root) {
                var id = root.querySelector('input[type="hidden"]');
                return id && id.value === '';
            })[0];
            target = next ? next.querySelector('input[type="text"]') : target;
        }
        target.focus();
    });

    /* ---------------------------------------------------------------------
     * Small screens: the sidebar is a drawer behind the Menu button.
     * ------------------------------------------------------------------- */
    function setNav(open) {
        document.body.classList.toggle('nav-open', open);
        var toggle = document.querySelector('[data-nav-toggle]');
        if (toggle) { toggle.setAttribute('aria-expanded', open ? 'true' : 'false'); }
    }

    document.addEventListener('click', function (event) {
        if (event.target.closest('[data-nav-toggle]')) {
            setNav(!document.body.classList.contains('nav-open'));
        } else if (event.target.closest('[data-nav-close]')) {
            setNav(false);
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && document.body.classList.contains('nav-open')) { setNav(false); }
    });

    /* ---------------------------------------------------------------------
     * Running clocks: <time data-since="…Z" data-long-after="90">
     * ------------------------------------------------------------------- */
    function elapsed(minutes) {
        var hours = Math.floor(minutes / 60);
        var rest = minutes % 60;
        if (hours >= 24) { return Math.floor(hours / 24) + 'd ' + (hours % 24) + 'h'; }
        if (hours) { return hours + 'h ' + (rest < 10 ? '0' : '') + rest + 'm'; }
        return rest + 'm';
    }

    function tick() {
        Array.prototype.forEach.call(document.querySelectorAll('[data-since]'), function (node) {
            var start = Date.parse(node.dataset.since);
            if (isNaN(start)) { return; }
            var minutes = Math.max(0, Math.floor((Date.now() - start) / 60000));
            node.textContent = elapsed(minutes);
            if (node.dataset.longAfter) {
                node.classList.toggle('is-long', minutes >= Number(node.dataset.longAfter));
            }
        });
    }

    /* ---------------------------------------------------------------------
     * Start-up
     * ------------------------------------------------------------------- */
    function start() {
        initAll(document);
        tick();
        setInterval(tick, 30000);

        Array.prototype.forEach.call(document.querySelectorAll('form'), syncStockToggle);

        // A modal that should already be open (e.g. after registering a new vehicle).
        var autoOpen = document.querySelector('.modal[data-auto-open]');
        if (autoOpen && window.bootstrap) {
            window.bootstrap.Modal.getOrCreateInstance(autoOpen).show();
            if (window.history && window.history.replaceState) {
                window.history.replaceState(null, '', window.location.pathname);
            }
        }

        // The floor board is left open all day: refresh it quietly while nobody is typing.
        var refresh = Number(document.body.dataset.autoRefresh || 0);
        if (refresh > 0) {
            setInterval(function () {
                var busy = document.querySelector('.modal.show') ||
                    document.hidden ||
                    /^(INPUT|TEXTAREA|SELECT)$/.test((document.activeElement || {}).tagName || '');
                if (!busy) { window.location.reload(); }
            }, refresh * 1000);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }
})();
