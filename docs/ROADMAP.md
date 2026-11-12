# Harithma POS: improvement roadmap

*Updated 12 November 2026.*

The site is now on HTTPS with nightly backups, and the owner has sales reporting and full staff payroll. What matters most next:

1. Finish the last safety items that need an account or decision from the owner (off-server backups, uptime alerts, the GitHub deploy workflow).
2. Bring customers back with **service reminder SMS** and **vehicle history**.
3. Add the remaining money views (profit after expenses, exports).

**Effort:** **S** = under a day, **M** = one to three days, **L** = a week or more.

---

## Shipped

| Date | Change |
|---|---|
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

Tests: 128 automated tests cover billing, roles, settings, reports and payroll.

---

## 1. Fix first: safety and reliability

| Item | Status | What is left | Effort |
|---|---|---|---|
| Off-server backup copy | **Needs the owner** | Nightly backups are still on the droplet itself. Choose a destination: DigitalOcean droplet backups (switch on in the DigitalOcean account), DigitalOcean Spaces, or Google Drive. | S |
| Uptime alerts | **Needs the owner** | Create a free UptimeRobot or Better Stack account and point it at https://harithma.lk. | S |
| GitHub Actions deploy workflow | **Needs the owner** | `.github/workflows/deploy.yaml` runs on every push using secrets that may point at an old server. Check them in GitHub settings, or delete the workflow. | S |
| RabbitMQ password | **Needs the owner** | The password equals the username. Change it on the RabbitMQ server, then on the Settings page. | S |
| Purge cached old commits on GitHub | **Needs the owner** | Old commits with the removed database files can still be fetched by ID. Ask GitHub Support to purge cached views for Madlhawa/HarithmaPOS. Change the owner password if it was reused. | S |
| www.harithma.lk | **Needs the owner** | Add a DNS A record for `www` → 143.110.179.155, then add it to the certificate. | S |
| Error tracking | Not started | Sentry (free tier) so failures are seen without reading server logs. | S |
| Run tests before every deploy | Not started | A GitHub Actions job runs the 128 tests on each push and blocks a failing deploy. | S |
| Pin library versions | Not started | No version is pinned in `requirements.txt`, so a deploy can pull a breaking release. | S |
| Zero-downtime deploys | Not started | Reload gunicorn instead of restarting; a 502 was seen during one restart. | S |
| Two-step sign-in for owners | Not started | An authenticator-app code on top of the password. | M |

---

## 2. Counter and daily operations

| Idea | What it gives | Effort |
|---|---|---|
| Service packages | One-click bundles (Basic wash, Full detail) at a fixed price. | M |
| Price by vehicle type | Car, van, SUV, bike and three-wheeler priced separately for the same service. | M |
| Split and part payments | Part cash, part card on one bill; clearer tracking of credit balances. | M |
| Discount limits for staff | Owner-set maximum discount, with a reason recorded. | S |
| Configurable stages | Owner edits the floor stages (fixed today: Waiting, Vacuuming, Washing, Polishing, Done). | M |
| Bookings | Time slots booked by staff or customers, shown beside walk-ins on the dashboard. | L |
| Queue screen | A TV page for the waiting area showing which plates are at which stage. | S |
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
| Sinhala and Tamil | SMS texts and the status page in the customer's language. | M |

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
| Stock movement log | Every change to an item's quantity with who, when and why. | M |
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
| Audit trail | Who cancelled, deleted, discounted or changed a price or payslip, and when. | M |

---

## 7. Website and settings

| Idea | What it gives | Effort |
|---|---|---|
| Home page content in Settings | Services, prices, opening hours and photos changed without a code change. | M |
| Contact email in Settings | The public email address is fixed in the code. | S |
| Editable receipt footer | Message, hours and social links on receipts. | S |
| Second branch | More than one location in one system, with reports per branch. | L |

---

## 8. Performance and code

| Idea | What it gives | Effort |
|---|---|---|
| Database indexes | On plate number, customer phone and invoice dates, so searches stay fast as data grows. | S |
| Paging everywhere | Invoices, customers and payments pages as lists grow. | S |
| Remove unused images | The original photos in `static/frontpage/images` (43 MB) and the old carousel files are no longer used. | S |
| Staging copy | A small second instance to try changes on before production. | M |
| More server memory | The 1 GB droplet now has swap; move to 2 GB if it stays tight. | S |

---

## Suggested order

| Phase | Items |
|---|---|
| **Now** (owner actions, ~1 day) | Off-server backups, uptime alerts, GitHub workflow check, RabbitMQ password, GitHub cache purge, tests before deploy, pin versions. |
| **Next** (~3–4 weeks) | Service reminder SMS, vehicle history and customer profile, profit after expenses, daily summary, export, stock movement log. |
| **Later** | Packages and vehicle-type pricing, split payments and cash-up, staff clock-in and leave requests, loyalty and feedback, bookings and queue screen. |

Estimates are rough, not quotes.
