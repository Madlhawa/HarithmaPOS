/* Attendance register: show only the inputs a status needs, and fill the rest of the day in one click. */
(function () {
    'use strict';
    var form = document.getElementById('register');
    if (!form) return;
    var start = form.dataset.workStart, end = form.dataset.workEnd;

    function sync(row) {
        var status = row.querySelector('[data-status]').value;
        var leave = row.querySelector('[data-leave]');
        var timeIn = row.querySelector('[data-in]'), timeOut = row.querySelector('[data-out]');
        var needsLeave = status === 'leave' || status === 'half';
        var needsTime = status === 'present' || status === 'half';
        leave.disabled = !needsLeave;
        if (!needsLeave) leave.value = '';
        if (status === 'leave' && !leave.value) leave.value = 'casual';
        timeIn.disabled = timeOut.disabled = !needsTime;
        timeIn.required = status === 'present';
        row.classList.toggle('is-unmarked', status === '');
    }

    form.querySelectorAll('[data-row]').forEach(function (row) {
        sync(row);
        row.querySelector('[data-status]').addEventListener('change', function () {
            var timeIn = row.querySelector('[data-in]');
            if (this.value === 'present' && !timeIn.value) timeIn.value = start;
            sync(row);
        });
    });

    var fill = form.querySelector('[data-fill-present]');
    if (fill) {
        fill.addEventListener('click', function () {
            var changed = 0;
            form.querySelectorAll('[data-row]').forEach(function (row) {
                var status = row.querySelector('[data-status]');
                if (status.value !== '') return;
                status.value = 'present';
                row.querySelector('[data-in]').value = start;
                row.querySelector('[data-out]').value = end;
                sync(row);
                changed += 1;
            });
            fill.textContent = changed ? changed + ' marked present: check the times, then Save' : 'Everyone is already marked';
        });
    }

    var dateBox = document.querySelector('[data-autosubmit]');
    if (dateBox) dateBox.addEventListener('change', function () { if (this.value) this.form.submit(); });
})();
