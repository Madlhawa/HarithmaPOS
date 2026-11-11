# Harithma POS: review and changes (November 2026)

This branch (`claude/ui-refresh-and-fixes`) redesigns the back office and fixes
the bugs found while reading the code. **No database changes are needed**: every
table and column is unchanged, so it can be deployed over the current database.

## How to try it

```bash
git checkout claude/ui-refresh-and-fixes
pip install -r requirements.txt
python -m pytest tests          # money, phone and time rules
flask run                       # needs HARITHMA_SECRET_KEY and HARITHMA_DATABASE_URI as before
```

The app now refuses to start without `HARITHMA_SECRET_KEY`. Optional new settings:
`HARITHMA_BUSINESS_PHONE`, `HARITHMA_BUSINESS_ADDRESS` (shown on receipts),
`HARITHMA_COOKIE_SECURE=true` (once the site has HTTPS), `HARITHMA_TIMEZONE`
(defaults to Asia/Colombo).

## What changed for the people using it

* **Dashboard is now a floor board.** One lane per stage (Waiting, Vacuuming,
  Washing, Polishing, Done today). Each vehicle shows its plate, owner, bay,
  employee, a running clock (red after 2 hours) and a one-tap button to move it
  to the next stage. Wash bays show which vehicle is in each one; a free bay has
  "Start a service here". The page refreshes itself every minute while nobody
  is typing.
* **Today's numbers** across the top: vehicles in the station, finished today,
  cash collected and paid out today, money owed on finished jobs, items running low.
* **New customer and vehicle in one step** from the dashboard, which then opens
  the new-service form with that vehicle already chosen. Phone numbers can be
  typed any way (0771234567, +94 77 123 4567, ...).
* **Invoice screen** rebuilt: add-item box with price and stock shown as you pick,
  + / − / remove per line, status as a single bar, next-service mileage shown as
  a windscreen sticker, totals laid out like a cash book (balance to collect or
  change to give back), earlier visits of the same vehicle, and a **Print**
  button that works without the receipt printer (80 mm receipt layout).
* **Customer SMS status page** redesigned as a progress track the customer can
  follow on their phone.
* **Lists** (invoices, customers, items, payments, ...) have search, filters
  (In progress / Done / Unpaid, Running low / Services, Money in / out),
  page numbers and edit forms that open pre-filled.
* **Items can be services**: untick "Keep count of stock" for labour or a wash
  so it never runs out of stock.
* Sidebar layout that turns into a menu on phones and tablets; light and dark
  themes; clear messages that say which field was wrong.

## Bugs and risks fixed

### Security
| Problem | Fix |
|---|---|
| No CSRF protection: any website could make a signed-in browser delete invoices, customers or payments | `CSRFProtect` on every POST |
| Deletes and quantity changes were plain GET links (also triggered by link prefetching or a double click) | All data changes are POST buttons, with a confirmation for deletes |
| Password-reset links never expired, and the reset form told strangers which emails have accounts | Links expire after 30 minutes; same message either way |
| Login `next=` parameter allowed redirecting to another site | Only same-site paths are followed |
| SMS and printer failures were only `print()`ed, or raised and stopped the request | Logged properly, with a clear message on screen |
| `SECRET_KEY` could silently be empty | App refuses to start without it |
| Cookies not marked HttpOnly / SameSite | Set; `Secure` once HTTPS is on |

### Money and stock
| Problem | Fix |
|---|---|
| Completing an invoice twice recorded the payment twice, and always as Cash whatever method was chosen | Payment ledger is synced, never duplicated, with the chosen method |
| Change given back counted as income (Rs. 5,000 handed over for a Rs. 4,300 bill recorded 5,000) | Only the bill amount is recorded |
| On the Payments page, editing a payment never changed the invoice balance, payments for item invoices and purchase orders never updated them, and a refund (money out) was added as if paid | Create, edit and delete keep every linked invoice and purchase order correct |
| Purchase orders charged the supplier amount at **selling** price | Owed amount is based on cost; unit cost per delivery can be entered and updates the item's cost |
| Deleting an invoice or a line did not always return stock; deleting a purchase order did not remove its stock | Stock is returned / removed consistently |
| Discounts could exceed the price, giving negative totals | Capped at the line or bill amount |
| Float maths on money in places | All money is `Decimal`, rounded half-up to cents (`harithmapos/billing.py`, tested) |
| A second open invoice could be created for a vehicle already in the station | Opens the existing invoice instead |
| Deleting a customer, item, employee, bay or supplier still in use crashed with a database error | Friendly message saying what still uses it |

### Reliability
| Problem | Fix |
|---|---|
| Receipt printer / RabbitMQ down = invoice could not be completed | Sale is saved; a message says to use Print |
| "Today" on the dashboard used the server's UTC day, so jobs after 6:30 pm moved to tomorrow | Uses the Colombo calendar day |
| Invoice pages open over an hour failed with a CSRF timeout | Token lasts for the login session |
| Invalid form input showed only "validation failed" | Each wrong field is named |
| Typing a name instead of picking from the list sent a wrong or empty id | The id is only set by picking; the form blocks otherwise |
| Search queries used string-built ids such as "12 \| Name" | JSON search endpoints return ids |

## Recommended next steps (not done here)

1. **Remove `instance/database.db` from the repository.** It is committed to a
   public GitHub repo and may contain real customer names and phone numbers.
   Delete it from history (`git filter-repo`) and add `instance/` to `.gitignore`.
2. **HTTPS** on the server (Let's Encrypt via certbot), then set
   `HARITHMA_COOKIE_SECURE=true`.
3. **Daily database backups** copied off the server (a cron job with `pg_dump`).
4. **User roles**: owner vs. counter staff, so only the owner can delete
   invoices, see costs/margins and record withdrawals.
5. **Reports**: daily cash-up (opening float, cash in/out, closing count),
   monthly income vs. expenses, profit by service, employee job counts for wages.
6. **Service reminders**: an SMS when a vehicle is near its next-service mileage
   or date, using the `next_milage` already stored.
7. **Audit trail** for edits and deletes of invoices and payments.
8. **Vehicle history page** (all visits, mileage over time) linked from the plate.
9. **Bundle Bootstrap, icons and fonts locally** so the counter PC works if the
   internet is slow; consider a tablet-sized layout for staff in the bays.
10. **Automated tests for the routes** (pytest + Flask test client on SQLite).
