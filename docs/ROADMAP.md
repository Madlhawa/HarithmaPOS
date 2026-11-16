# Harithma POS: improvement roadmap

*Updated 16 November 2026.*

The site is now on HTTPS with nightly backups, and the owner has sales reporting and full staff payroll. What matters most next:

1. Finish the last safety items that need an account or decision from the owner (off-server backups, uptime alerts, the GitHub deploy workflow).
2. Close the gaps from the 16 November code review that can silently produce wrong data: tests on PostgreSQL, stock changes that can race, and two people editing the same invoice (section 1).
3. Bring customers back with **service reminder SMS** and **vehicle history**.
4. Add the remaining money views (profit after expenses, exports).

**Effort:** **S** = under a day, **M** = one to three days, **L** = a week or more.

---

## Shipped

| Date | Change |
|---|---|
| 16 Nov 2026 | **Stock history.** Every change to an item's stock is written down with when, why (sold, sale taken back, bought in, purchase taken back, voided, stock count, opening stock), which invoice or order, who, and the stock left after. Click an item's stock figure on the Items page to see it. Each item's history starts with its stock on 16 Nov, so its quantity always equals the sum of its history. |
| 16 Nov 2026 | **Lines keep the item as sold.** Each line on a service invoice, item sale or purchase order stores the item's name, unit cost, unit price and automatic discount from when it was added. Renaming or repricing an item never changes an existing invoice or its prints, and +/- on a draft line keeps the price it was added at; only new lines take the new price. |
| 16 Nov 2026 | **Lines and stock in their own modules.** Adding, removing and changing lines on invoices, item sales and purchase orders, with their stock movements and totals, now live in `lines.py`; every stock change goes through `stock.py`, which locks the item's row first so two counters can't lose a sale; the job stage and its history are in `job_status.py`. The invoice routes went from 865 to about 710 lines and only read forms and show results. No change to how the screens work. |
| 16 Nov 2026 | **Sign-in duration.** "Keep me signed in" lasts 30 days (it was a year) and is for your own phone or computer. Without it (the counter PC), the sign-in ends when the browser closes or after an hour with nothing done, and the screen goes back to sign-in by itself; the hour is set in Settings → General (0 = never). Live board updates don't count as activity. |
| 16 Nov 2026 | **Sign-in emails ignore case.** `Owner@x.com` and `owner@x.com` are one account: emails are stored in lower case (a database check enforces it), and sign-in, password reset, adding and editing users all ignore case and stray spaces. |
| 16 Nov 2026 | **Old database helper removed.** `utils/database.py` (which "repaired" id sequences after any failed insert and printed to the console) is gone; records are saved with plain inserts. Adding a customer, vehicle and job together from the floor board or the counter now saves all of them or none. `flask create-user` makes an owner by default (`--role staff` for counter staff). |
| 16 Nov 2026 | **Keyboard-only item entry.** After a line is added on a service invoice or item sale, the cursor goes straight back to the item search. |
| 15 Nov 2026 | **Times and money.** Every timestamp is `timestamptz` and every time in the code is aware UTC, shown in Colombo time; a day means the Colombo day. Money is Decimal end to end with one rounding rule (half up, per stored amount, totals never re-rounded); the screen formatting, payroll and reports use it, and floats appear only in chart data. |
| 15 Nov 2026 | **Draft, completed and void.** Invoices, item sales and purchase orders have an explicit state with who and when. A finished job is not a billed one: the counter completes the bill. Completed bills are locked (items, prices, discounts); owners void instead of deleting, with a reason, after refunding any payment; voids put stock back and count nowhere. Refunds up to what was paid. |
| 15 Nov 2026 | **Payment ledger.** Payments are an append-only ledger (enforced by the database): mistakes are reversed, never edited or deleted. Invoices, sales and orders no longer store what was paid; it is summed from their payments. Change is noted on the payment, refunds for overpaid bills, typed entries for expenses, income and the owner's money; *Credit* is gone. |
| 15 Nov 2026 | **Live boards and in-page updates.** The dashboard and floor board update within seconds of any change (server-sent events) instead of reloading every 45–60 s; invoice and order lines, customer requests, stage buttons and the floor sheets update just their part of the page (htmx). gunicorn now runs threaded workers. |
| 15 Nov 2026 | **Audit log** (Setup → Audit log, owners). Every change to prices, discounts, payments, pay, roles and settings, and every deletion, with who, when and the old and new value. Recorded for every save, whichever page made it. |
| 15 Nov 2026 | **What the customer asked for.** The supervisor notes the customer's requests when starting a job (dashboard, New service page or floor board); they become a checklist on the invoice and in the floor board's sheet, and Complete or Ready to collect asks first if any are not ticked off. |
| 15 Nov 2026 | **Browser printing; RabbitMQ removed.** Service invoices have an LQ-350 layout and item sales the 80 mm receipt; Complete opens Chrome's print window and Print prints without leaving the page. The RabbitMQ queue, its settings and the `pika` package are gone. |
| 15 Nov 2026 | **Payments on completed invoices and purchase orders.** A completed service invoice, item sale or purchase order lists its payments and, while money is owed, has a **Record payment** (or **Pay supplier**) button for the rest, in full or in part. Open ones keep the Amount paid box. |
| 15 Nov 2026 | **Security hardening.** Sign-in rate limit also covers `/app`; nginx hides its version and refuses framing by other sites; SSH keys only with fewer tries; SSH connection rate limit in the firewall. |
| 14 Nov 2026 | **Developer page** (Menu → Developer → Monitor, developers only). Deploys with test results, GitHub Actions runs, users online and sign-ins (failed ones too), unique users per day, traffic per hour with attack and scanner requests, SSH break-in attempts, app errors with tracebacks, 5xx responses and server health, with a "Needs attention" list. |
| 14 Nov 2026 | **Tests before every deploy.** GitHub Actions runs the tests on every push and pull request; only a green run deploys, and it deploys that exact commit. Each deploy backs up the database, health-checks the site and puts the old version back if it fails. A one-click *Roll back* workflow. First automatic deploy from GitHub went live on 14 Nov. Library versions pinned to production's. The two broken workflows (pointing at the old server) were replaced. |
| 13 Nov 2026 | **Floor board** (Menu → Floor board). A phone-first page for the floor supervisor: bays, queue, polishing and ready tabs; one-tap next-stage buttons; a sheet to change stage, bay or employee; add a vehicle to the queue or straight into a free bay, registering new plates and owners on the spot. |
| 13 Nov 2026 | **Customer status page** shows subtotal and discounts; fixed coloured boxes behind some headings. |
| 12 Nov 2026 | **Staff report** (Reports → Staff). Attendance rate, punctuality, lateness, absences, leave, short leaves, overtime, jobs and revenue per day worked, advances and staff cost, for everyone or one employee; who-was-in chart, arrival times, late by weekday, scorecard, leave used and staff cost by month. |
| 12 Nov 2026 | **Staff attendance, leave and payroll.** Daily register (present, half day, leave by type, absent, day off; in/out times), automatic late, early and overtime minutes, short leaves, a month grid, leave balances, salary advances, monthly payroll with EPF/ETF, finalise, pay and print payslips. Lateness is tracked only. Employees gain pay type, EPF and a "working here" switch. |
| 12 Nov 2026 | **Sales dashboard** (Reports → Sales). Revenue, gross profit, jobs, average job, collected, still owed, customers new vs returning, time per job and discounts against the previous period. Revenue chart, top services and items, payment mix, busy-hours heatmap, staff, bay, top customer and unpaid tables. |
| 12 Nov 2026 | **HTTPS on harithma.lk.** Let's Encrypt certificate with auto-renewal; HTTP and the bare IP redirect; secure cookies; SMS and email links use https. |
| 12 Nov 2026 | **Server hardening.** Firewall (SSH, HTTP, HTTPS only), sign-in rate limit with a friendly page, 2 GB swap, nightly database backups kept 14 days and checked after each run. |
| 12 Nov 2026 | **Old databases removed from GitHub,** including from git history: one held the owner's email and password hash, one held customer records. |
| 12 Nov 2026 | **Phone layout fixed** on every list page (no sideways scrolling). |
| 12 Nov 2026 | **User guide** (`docs/USER_GUIDE.md`). |
| 11 Nov 2026 | **New public home page and logo,** used across the app, receipts and the customer status page. |
| 11 Nov 2026 | **Settings page:** email, SMS (with editable texts), receipt printer, business details and stock threshold, without editing `.env`; secrets encrypted; test buttons. |
| 11 Nov 2026 | **Owner and counter-staff roles** and user management. |
| 11 Nov 2026 | **Deploys through GitHub** with tracked database migrations and pre-deploy backups. |

Tests: 144 automated tests cover billing, roles, settings, reports and payroll.

---

## 1. Fix first: safety and reliability

| Item | Status | What is left | Effort |
|---|---|---|---|
| Off-server backup copy | **Needs the owner** | Nightly backups are still on the droplet itself. Choose a destination: DigitalOcean droplet backups (switch on in the DigitalOcean account), DigitalOcean Spaces, or Google Drive. | S |
| Backup restore test | Not started | Nobody has proved a backup can be restored. A weekly job that restores the latest dump into a scratch database and checks row counts, with an alert if it fails. | S |
| Uptime alerts | **Needs the owner** | Create a free UptimeRobot or Better Stack account and point it at https://harithma.lk. | S |
| Purge cached old commits on GitHub | **Needs the owner** | Old commits with the removed database files can still be fetched by ID. Ask GitHub Support to purge cached views for Madlhawa/HarithmaPOS. Change the owner password if it was reused. | S |
| www.harithma.lk | **Needs the owner** | Add a DNS A record for `www` → 143.110.179.155, then add it to the certificate. | S |
| Error alerts | Partly done | Errors now show on the developer page. Still to do: an error tracker (Sentry or similar) that emails the developer with the traceback and the request, so nobody has to look. | S |
| Tests on PostgreSQL | Not started | The tests run on SQLite but production runs PostgreSQL, so the payment append-only trigger, `timestamptz` behaviour and the migrations are never tested. Add a PostgreSQL service to GitHub Actions, run the tests on it, and run `flask db upgrade` from an empty database. | S |
| Stock changes can race | Partly done | Every stock change now goes through `stock.py`, which locks the item's row and re-reads the quantity first (16 Nov). Still to do: a database check that stock can't go below zero, and a test on PostgreSQL proving two simultaneous sales can't both take the last one. | S |
| Two people editing one invoice | Not started | The last save silently wins. Add a version number to invoices, sales and orders; a save based on an older version is refused with "someone else changed this, reload". | M |
| Database indexes | Not started | Only primary keys exist on invoices, lines, customers and vehicles. Index invoice dates and status, customer and vehicle links, invoice-to-line links, plate number and customer phone. Fast now at ~1,000 invoices; slows steadily as data grows. | S |
| Upgrade PostgreSQL and Python | Not started | PostgreSQL 14 stopped getting fixes on 12 Nov 2026 and Python 3.10 in Oct 2026. Ubuntu 22.04 still patches its own packages until Apr 2027. Plan a move to PostgreSQL 17 and Python 3.12 (or Ubuntu 24.04), tested on a copy first. | M |
| Health check endpoint | Not started | Deploys and uptime checks use the login page, which doesn't prove the database answers. Add `/healthz` that runs a one-row query. | S |
| Zero-downtime deploys | Not started | Reload gunicorn instead of restarting; a 502 was seen during one restart. | S |
| Two-step sign-in for owners | Not started | An authenticator-app code on top of the password. | M |

---

## 1a. Security (from the 16 Nov review)

What is already right: CSRF on every form, role checks on every route, secure and HttpOnly cookies, rate-limited sign-in, encrypted secrets in Settings, an audit log, HTTPS with HSTS. Still missing:

| Item | What to do | Effort |
|---|---|---|
| Reset links can be reused | A password reset link keeps working for its whole 30 minutes, even after use. Tie the token to the current password hash so it dies once used. | S |
| Sign out other devices | Changing or resetting a password should end every other session (Flask-Login session protection plus a per-user session version). | S |
| Account lockout | nginx limits attempts per IP address, but nothing limits attempts per account. Lock an account for a few minutes after repeated failures, and tell the owner. | S |
| Content-Security-Policy | The other security headers are set; this one isn't. Add a policy that allows only the app's own scripts. | S |
| Serve Bootstrap, htmx and fonts locally | They load from public CDNs; the Bootstrap Icons stylesheet has no integrity hash. Serving them from the app removes the outside dependency. | S |
| SMS API key in the URL | notify.lk is called with GET, so the key sits in the request URL and can end up in logs. Use POST if their API allows it. | S |
| Upload checks | Profile pictures are checked by file name only. Check the image content, and set an upload size limit in Flask (only nginx caps it, at 10 MB). | S |
| Deploy as a non-root user | The GitHub deploy key signs in as root (locked to one script). A dedicated deploy user with only the sudo rights it needs is the standard. | S |
| Sandbox the service | Add systemd hardening to the app service: `NoNewPrivileges`, `ProtectSystem`, `PrivateTmp` and similar. | S |
| Dependency vulnerability checks | Dependabot and `pip-audit` in CI, so a library with a known hole is flagged. | S |

---

## 1b. Data model (from the 16 Nov review)

| Item | What to do | Effort |
|---|---|---|
| Unique plates and phones | Two vehicles can have the same plate and two customers the same phone. Normalise and make them unique (or warn on duplicates first, then enforce). | S |
| Queue without a bay or employee | A service invoice must have a wash bay and an employee at the database level, even while the vehicle waits in the queue. Allow them to be empty until work starts. | S |
| Archive instead of delete | Customers, items, suppliers and employees are hard-deleted. Give them an *archived* state, as invoices now have *void*. | M |
| Gapless invoice numbers | Invoice numbers are database ids, so an abandoned draft leaves a gap. Give completed bills their own sequential number (needed for tax, and for a second station later). | M |
| More database checks | Only the payment table has checks. Add them for quantity above zero, discount not above the price, and similar rules. | S |
| Configurable stages | Service stages are hardcoded as 0–4 in code and data (also in section 2). | M |

---

## 2. Counter and daily operations

| Idea | What it gives | Effort |
|---|---|---|
| Service packages | One-click bundles (Basic wash, Full detail) at a fixed price. | M |
| Price by vehicle type | Car, van, SUV, bike and three-wheeler priced separately for the same service. | M |
| Split payments | Part cash, part card in one go at the counter; clearer tracking of credit balances. (Later part payments on completed bills are done.) | M |
| Discount limits for staff | Owner-set maximum discount, with a reason recorded. | S |
| Configurable stages | Owner edits the floor stages (fixed today: Waiting, Vacuuming, Washing, Polishing, Done). | M |
| Bookings | Time slots booked by staff or customers, shown beside walk-ins on the dashboard. | L |
| Queue screen | A TV page for the waiting area showing which plates are at which stage (read-only version of the floor board). | S |
| Cash-up at closing | Count the till against what the system expects and record the difference. | M |
| Longer plates | Vehicle numbers are limited to 8 characters; allow longer formats such as `WP CAB-1234`. | S |
| Barcode scanning | Scan items at the counter. | S |

---

## 3. Customers and repeat business

The register already stores mileage and "next service in" on every visit, but nothing uses it yet. **Reminders are the highest-value feature left.**

| Idea | What it gives | Effort |
|---|---|---|
| Service reminder SMS | Text the customer when the next service is due, by mileage estimate, by months since the last visit, or both. *Open question in the online roadmap: which rule?* | M |
| Vehicle history page | Every past visit for a plate, with items, mileage and amount; for staff and on the customer link. | S |
| Customer profile | Total spent, visits, last visit, balance owed and vehicles on one screen. | S |
| Loyalty | Every Nth wash free, or points per rupee, shown on the receipt. | M |
| Feedback after service | A one-tap rating link by SMS; low ratings alert the owner. | M |
| Win-back messages | Promotions to customers not seen in 60–90 days, with opt-out. | M |
| WhatsApp | Updates and receipts over WhatsApp Business. | M |
| Digital receipt | Send the receipt as a link by SMS or email. | S |
| Before/after photos | Attach photos to a job; shown on the customer status page. | M |
| Sinhala and Tamil | SMS texts and the status page in the customer's language; later the app's own screens (needs a translation framework, none today). | M |
| SMS opt-out | A per-customer switch, and a STOP reply where the gateway supports it. Needed before win-back messages. | S |
| Customer data rights | Export or erase one customer's data on request, and a privacy notice, as the Personal Data Protection Act expects. | M |

---

## 4. Money and reports

The sales dashboard is done. Still to do:

| Idea | What it gives | Effort |
|---|---|---|
| Profit after expenses | Monthly profit: gross profit minus wages (now in payroll), rent, power and other money out. | M |
| Expense categories | Group money out (rent, utilities, supplies) for that report. | S |
| Daily summary to the owner | End-of-day SMS or email: vehicles, cash collected, unpaid jobs. | S |
| Export | Download any list or report as Excel/CSV for the accountant. | S |
| Tax and invoice numbering | Sequential invoice numbers and VAT/SSCL lines if the business registers. | M |

---

## 5. Stock and purchasing

| Idea | What it gives | Effort |
|---|---|---|
| Adjustments with a reason | Breakage, spills and count corrections recorded separately from sales. | S |
| Stock take | Enter a physical count; the system shows and records differences. | M |
| Reorder suggestions | Low items grouped by supplier, turned into a draft purchase order. | M |
| Materials per service | Each service uses set amounts of shampoo, wax etc., deducted automatically. | L |
| Supplier balances | What is owed to each supplier. | S |
| Low-stock alert | SMS or email to the owner when an item drops below its level. | S |

---

## 6. Staff and payroll (next steps)

Attendance and payroll are live. Possible follow-ups:

| Idea | What it gives | Effort |
|---|---|---|
| Staff clock in/out at the counter | Employees tap their name and a PIN; owners still correct the register. *The owner chose owner-marked attendance for now.* | M |
| Leave requests | Staff ask for leave; the owner approves and it lands in the register. | M |
| Optional lateness rules | Grace allowance per month, then deduct by the minute. Settings switch; off by default, as chosen. | S |
| Commissions | A percentage or fixed amount per job for the employee who did it, added to payroll. | M |
| EPF/ETF returns | Monthly contribution schedule (C-form figures) ready to submit. | M |
| Bank transfer file | Payroll export for bulk salary transfer. | S |
| Holidays calendar | Public and Poya holidays marked once for everyone, with holiday pay rules. | M |
| Hide "Salary Advance" in the general payment form | It records an expense but not a trackable advance; the Salary advances page is the right place. | S |

---

## 7. Website and settings

| Idea | What it gives | Effort |
|---|---|---|
| Home page content in Settings | Services, prices, opening hours and photos changed without a code change. | M |
| Contact email in Settings | The public email address is fixed in the code. | S |
| Editable receipt footer | Message, hours and social links on receipts. | S |
| Second branch | More than one location in one system, with reports per branch. Covered by "Multi-station SaaS" in section 10. | L |

---

## 8. Performance and code

| Idea | What it gives | Effort |
|---|---|---|
| Paging everywhere | Invoices, customers and payments pages as lists grow. | S |
| Remove unused images | The original photos in `static/frontpage/images` (43 MB) and the old carousel files are no longer used. | S |
| More server memory | The 1 GB droplet has swap and about 80 MB free; move to 2 GB before adding anything that runs in the background. | S |
| Linting and type checks | ruff (lint and format) and mypy in CI, with pre-commit hooks. | S |
| Test coverage | Measure coverage in CI so untested code is visible. | S |
| Browser tests | A few Playwright tests of the counter flow (add items, complete, print, void). The Void pop-up and search-focus bugs were browser behaviour no Python test could see. | M |
| README | Setup, running locally, tests and deploy, at the top of the repository. | S |

---

## 9. Operations

| Idea | What it gives | Effort |
|---|---|---|
| Background jobs | SMS and email are sent inside the page request, so a slow gateway freezes the counter for up to 10 s, with no retry. A small job queue (for example RQ, or a database-backed queue) and a log of every message sent. | M |
| Scheduled tasks | One place for timed jobs: reminder SMS, daily summary, backup checks. Builds on background jobs. | S |
| Staging copy | A second instance with a copy of the data to try changes and migrations on before production. | M |
| Database connection safeguards | `pool_pre_ping`, a statement timeout, and recycling gunicorn workers after a number of requests. | S |
| Log retention and search | Logs stay in the systemd journal only. Set a retention policy, and ship them somewhere searchable if the error tracker isn't enough. | S |

---

## 10. Platform

| Idea | What it gives | Effort |
|---|---|---|
| Works offline | If the internet drops, the counter stops. Decide whether bills must keep working offline (queued and sent later); this is a product decision as much as a technical one. | L |
| API | A documented, authenticated API for the future print agent, a mobile app or integrations. | M |
| Multi-station SaaS | Sell the app to other service stations: a station on every row, enforced in the app and by PostgreSQL row-level security, per-station settings and invoice numbers, a platform admin area. Replaces "Second branch" in section 7. | L |

---

## Suggested order

| Phase | Items |
|---|---|
| **Now** (owner actions, ~1 day) | Off-server backups, uptime alerts, GitHub cache purge. |
| **Then** (~1–2 weeks) | Tests on PostgreSQL, stock race, edit conflicts, indexes, error tracker, health check, backup restore test, the small security items (1a) |
| **Next** (~3–4 weeks) | Service reminder SMS, vehicle history and customer profile, profit after expenses, daily summary, export. |
| **Soon after** | PostgreSQL and Python upgrade, background jobs, staging copy, browser tests, linting and coverage, unique plates and phones, archive instead of delete, gapless invoice numbers. |
| **Later** | Packages and vehicle-type pricing, split payments and cash-up, staff clock-in and leave requests, loyalty and feedback, bookings and queue screen. |

Estimates are rough, not quotes.
