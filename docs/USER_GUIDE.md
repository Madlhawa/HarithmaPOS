# Harithma POS user guide

Harithma POS runs the counter at Harithma Service Center: it tracks every vehicle from arrival to "Done", bills customers, keeps stock, records money in and out, and handles staff attendance and payroll.

This guide explains every page, button and field. If you are new, read **Getting started** and **A typical day** first, then look pages up as you need them.

*Written for the version running at https://harithma.lk in November 2026.*

---

## Contents

1. [Getting started](#1-getting-started)
2. [A typical day](#2-a-typical-day)
3. [Dashboard](#3-dashboard)
4. [Service invoice screen](#4-service-invoice-screen)
5. [Service invoices list](#5-service-invoices-list)
6. [Item invoices (counter sales)](#6-item-invoices-counter-sales)
7. [Customers and vehicles](#7-customers-and-vehicles)
8. [Payments](#8-payments)
9. [Items (services and stock)](#9-items-services-and-stock)
10. [Purchase orders](#10-purchase-orders)
11. [Suppliers](#11-suppliers)
12. [Staff: attendance, payroll, advances, employees](#12-staff)
13. [Reports: Sales and Staff](#13-reports-sales)
14. [Setup: wash bays, users, settings](#14-setup)
15. [Your account](#15-your-account)
16. [What customers see](#16-what-customers-see)
17. [How money and stock are worked out](#17-how-money-and-stock-are-worked-out)
18. [Common tasks and questions](#18-common-tasks-and-questions)
19. [Glossary](#19-glossary)

---

## 1. Getting started

### Signing in

Open **https://harithma.lk** and click **Staff sign in** (top right), or go straight to https://harithma.lk/app/login.

| Field | What to enter |
|---|---|
| Email | The email address your owner set up for you. |
| Password | Your password (at least 8 characters). |
| Keep me signed in | Tick on the counter computer so you stay signed in. Leave unticked on a shared or public computer. |

**Forgot password?** Click it on the sign-in page, enter your email and press **Send reset link**. The email has a link that works for 30 minutes; it opens **Set a new password**, where you type the new password twice.

If your account has been switched off you will see a message saying so; ask an owner.

### Two kinds of users

| | Counter staff | Owner |
|---|---|---|
| Dashboard, service invoices, item sales | Yes | Yes |
| Move vehicles between stages, send SMS, print receipts | Yes | Yes |
| Add and edit customers and vehicles | Yes | Yes |
| Record money coming in | Yes | Yes |
| See items and prices | Yes (no cost price or margin) | Yes, with cost and margin |
| Cancel or delete invoices, delete customers or vehicles | No | Yes |
| Record, edit or delete money going out | No | Yes |
| Items (add/change), purchase orders, suppliers | No | Yes |
| Staff (attendance, payroll, advances, employees) | No | Yes |
| Sales report, wash bays, users, settings | No | Yes |

Owners see extra sections in the menu. If a staff member opens an owner-only page they see "You don't have access", and an owner-only button simply isn't shown.

### The screen

- **Menu (left).** Grouped as *Counter*, *Stock*, *Staff*, *Reports* and *Setup*. On a phone it is behind the **Menu** button at the top.
- **Your name (bottom of the menu)** with your role, plus **Account** and **Sign out**.
- **Messages** appear at the top of the page after you save something: green = done, yellow = warning, red = not saved (the message says why).

### Typing conventions

- **Money** can be typed with or without commas: `2500`, `2,500` and `2500.00` are the same. Amounts are in rupees (Rs.).
- **Phone numbers** can be typed any way: `077 123 4567`, `0771234567` or `+94 77 123 4567`. They are stored as 9 digits and shown as `077 123 4567`.
- **Vehicle numbers** (plates) are up to 8 characters, e.g. `CAB-1234`. They show as yellow number plates throughout the app.
- **Search boxes** with a list underneath (vehicle, customer, item, employee, bay): start typing and **pick from the list**. Typing a name without picking it is not enough; the form will ask you to choose from the list.
- **Times** are Sri Lanka time.

---

## 2. A typical day

1. **Open the dashboard** and leave it open on the counter. It refreshes itself every minute.
2. **A car arrives.**
   - First visit: **New customer and vehicle** → fill in name, phone and plate → **Save and start a service**.
   - Returning customer: **New service** → type the plate, owner name or phone and pick the vehicle.
3. **Choose the employee and wash bay**, type the mileage if you have it, and press **Open the invoice**.
4. **Add what you will charge for**: type "body wash", pick it from the list, press **Add**. Repeat for every service or item.
5. **Text the customer** (optional): **Text: started** sends them a link to follow the job.
6. **Move the car along** on the dashboard: **Start vacuuming → Start washing → Start polishing**.
7. **When it's finished:** click **Bill and finish** (or open the invoice), enter the **Amount paid** and **Paid by**, and press **Complete and print receipt**. Press **Text: ready** first if you want to tell the customer.
8. **Counter sales** (a bottle of shampoo, no service): **Item sale** on the dashboard.
9. **Owners, end of day:** mark the **Attendance register**, glance at **Sales**, check **Items running low**.

---

## 3. Dashboard

*Menu → Dashboard.* The home page after signing in. It shows what is happening in the station right now and refreshes every minute (it waits while you are typing).

### Buttons at the top

| Button | What it does |
|---|---|
| **New service** | Opens the *New service* form (below) to start a job for a vehicle that is already registered. |
| **New customer and vehicle** | Registers a first-time customer and their vehicle, then opens *New service* with that vehicle already chosen. |
| **Item sale** | Starts a walk-in counter sale straight away (see [Item invoices](#6-item-invoices-counter-sales)). |
| **Record payment** | Records money in (or, for owners, out) that isn't from completing an invoice. Same form as on the [Payments](#8-payments) page. |

### Finish setting up

Shown only until the station has at least one wash bay, one employee and one item. Each link takes an owner to the page where they add it.

### Today's numbers

| Figure | Meaning |
|---|---|
| In the station now | Vehicles not yet Done. |
| Finished today | Vehicles marked Done today. |
| Collected today | Money in recorded today. |
| Paid out today *(owners)* | Money out recorded today. |
| Unpaid on finished jobs | What customers still owe on Done jobs. Click it to see those invoices. |
| Items running low | Stock items at or below the "running low" level (Settings → General). Click to see them. |

### On the floor

One column per stage: **Waiting, Vacuuming, Washing, Polishing** and **Done today**. Each card shows:

- the **number plate** (click it to open the invoice);
- the **time since it arrived**, which turns red after 2 hours (Done cards show the invoice number instead);
- customer, wash bay and employee;
- the bill so far;
- a button to move it on: **Start vacuuming**, **Start washing**, **Start polishing**, and in the Polishing column **Bill and finish**, which opens the invoice to take payment;
- in **Done today**, the amount (or how much is still unpaid) and **Open**.

### Wash bays

Each bay shows the vehicle in it and its stage, or **Free** with a **Start a service here** button that opens *New service* with that bay chosen.

### New service form

| Field | What to enter |
|---|---|
| Vehicle | Type the plate, owner's name or phone, then pick the vehicle. "First visit?" links to *New customer and vehicle*. |
| Employee doing the job | Pick from the list (click the box to see everyone). |
| Wash bay | Pick from the list. |
| Mileage now (km) | The odometer reading. Leave empty if you don't have it. |

**Open the invoice** creates the invoice in *Waiting* and opens the [service invoice screen](#4-service-invoice-screen). **Cancel** closes the form.

### New customer and vehicle form

| Field | What to enter |
|---|---|
| Customer name | Required. |
| Phone | Needed for SMS updates. |
| Vehicle number | Required, up to 8 characters, e.g. `CAB-1234`. |
| Make, Model, Year | Optional, e.g. Toyota, Axio, 2016. |

**Save and start a service** saves both and opens *New service* with the vehicle filled in.

---

## 4. Service invoice screen

Opened from a plate, **Open**, **Bill and finish**, or the [Service invoices list](#5-service-invoices-list). Everything about one visit is here.

**Header:** the number plate, customer and phone, invoice number, when it was opened and how long ago, and the current stage. **Print** opens the receipt in a new tab.

### Adding services and items (left)

| Field | What to enter |
|---|---|
| Add a service or item | Type part of the name, e.g. "wash" or "oil", and pick it. |
| Quantity | Defaults to 1. Decimals are allowed for things like litres. The unit is shown next to it. |
| Extra discount | Optional amount off this line, on top of any automatic discount the item has. |

**Add** puts the line on the invoice. Stock items come off stock straight away; if there isn't enough in stock you get a message and nothing is added.

The table lists each line: item, quantity with **−** (one less) and **+** (one more), unit price, discount and amount. The bin button removes the line (after asking) and puts the stock back.

**Earlier visits of this vehicle** lists previous invoices with date, mileage and total; click a number to open it.

### Job panel (right)

| Field / button | What it does |
|---|---|
| Status | The stage: Waiting, Vacuuming, Washing, Polishing or Done. Change it and press **Save**. |
| Employee | Who is doing the job. |
| Wash bay | Which bay it is in. |
| Mileage now (km) | Odometer reading at this visit. |
| Next service in (km) | e.g. 5000. Shows "Next service due at …" once both mileages are filled in, for the service sticker. |
| **Text: started** | Sends the "service started" SMS with a link to the [customer status page](#16-what-customers-see). Changes to *Start SMS sent* once sent. |
| **Text: ready** | Sends the "service finished" SMS. Changes to *Ready SMS sent*. |

The SMS buttons are greyed out if the customer has no phone number or that text was already sent. If SMS is switched off or not set up in Settings, pressing one shows a message saying the text was not sent. SMS are only sent when you press these buttons, never automatically.

### Bill panel (right)

| Field / button | What it does |
|---|---|
| Subtotal / Discounts / Total | Worked out from the lines and the bill discount. |
| Paid / Balance to collect / Change to give back | What is still owed or the change due. *Settled* means paid exactly. |
| Bill discount | An amount off the whole bill. |
| Amount paid | What the customer handed over. If they give Rs. 5,000 for a Rs. 4,300 bill, type 5000: the app records 4,300 and shows Rs. 700 change. |
| Paid by | Cash, Card, Bank Transfer, Credit or QR. Use *Credit* when the customer will pay later. |
| **Complete and print receipt** | Marks the job Done, records the payment on the Payments page, and sends the receipt to the printer (if one is set up; otherwise use **Print**). Returns you to the dashboard. |
| **Save** | Saves the job and bill panels without completing. |
| **Cancel invoice** *(owners)* | Deletes the invoice after asking; its items go back into stock. |

You can open a completed invoice again to correct it. Pressing **Complete** a second time never records the payment twice: only a difference is added.

---

## 5. Service invoices list

*Menu → Service invoices.* Every visit, newest first.

| Control | What it does |
|---|---|
| **New service** | Opens the full-page *New service* form (same fields as on the dashboard). |
| Search | Vehicle number, customer name or invoice number. |
| **All / In progress / Done / Unpaid** | Filters the list. *Unpaid* = finished jobs with money still owed. |

Columns: number, plate, customer (with employee and bay), date, stage, total, and balance (red if owed, otherwise *Paid*). Click the number or plate to open it.

---

## 6. Item invoices (counter sales)

*Menu → Item invoices.* Sales of stock without a service, such as a bottle of oil.

| Button | What it does |
|---|---|
| **Walk-in sale** | Starts a sale with no named customer (shown as *Walk-in*) and opens it straight away. Also on the dashboard as **Item sale**. |
| **Sale to a customer** | Choose the **Customer** (name or phone) and press **Start the sale**. Useful when you want the sale on their record or they will pay later. |
| Search | Customer name or invoice number. |

The list shows number, customer, date and time, number of lines, total and balance.

### Item sale screen

The same **Add a service or item / Quantity / Extra discount / Add** row and lines table as the [service invoice](#4-service-invoice-screen), plus a **Bill** panel:

| Field / button | What it does |
|---|---|
| Customer | Optional. Pick a customer or leave empty for a walk-in. |
| Bill discount, Amount paid, Paid by | As on a service invoice. |
| **Complete and print receipt** | Records the payment and prints. |
| **Save** | Saves without completing. |
| **Print** | Opens the receipt in a new tab. |
| **Delete this sale** *(owners)* | Deletes it after asking; items go back into stock. |

---

## 7. Customers and vehicles

*Menu → Customers.*

| Control | What it does |
|---|---|
| **Add customer** | Name (required), Phone, Email, Address. |
| Search | Name, phone or vehicle number. |
| Plate buttons | Each of the customer's vehicles. Click one to **edit the vehicle**, **Start a service** for it, or (owners) **Delete vehicle**. |
| **Add vehicle** | Adds a vehicle to that customer. |
| Pencil | Edit the customer. |
| Bin *(owners)* | Delete the customer and their vehicles. Refused if they have invoices or payments. |

**Vehicle fields:** **Owner** (pick a customer, which also moves a vehicle to a new owner), **Vehicle number** (required, up to 8 characters), **Year**, **Make**, **Model**.

The special customer *Walk-in* is used for anonymous counter sales and cannot be deleted.

---

## 8. Payments

*Menu → Payments.* Every rupee in and out. Counter staff see money in only.

Most payments are created automatically: completing an invoice records money in; paying a payslip or giving a salary advance records money out. Use **Record payment** for anything else, such as the electricity bill, a customer paying an old balance, or a refund.

| Control | What it does |
|---|---|
| **Record payment** | Opens the payment form. |
| **All / Money in / Money out** *(owners)* | Filters the list. |
| Pencil / bin *(owners)* | Edit or delete a payment. Deleting a payment linked to an invoice makes that invoice owe the money again. |

### Payment form

| Field | What to enter |
|---|---|
| Direction *(owners)* | *Money in* or *Money out*. Staff can only record money in. |
| Amount (Rs.) | Required. |
| Paid by | Cash, Card, Bank Transfer, Credit or QR. |
| Type | General, Employee Wage, Owner Withdrawal or Salary Advance. |
| What was it for? | A short note, e.g. "electricity bill". |
| Service invoice | Optional link. Its balance updates automatically. |
| Item invoice no. / Purchase order no. | Optional links by number; balances update automatically. |
| Customer / Employee | Optional, to show who it was from or to. |

> **Salary advances and wages:** use **Staff → Salary advances** and **Staff → Payroll** rather than this form, so they are tracked and taken back on payroll. A payment typed in here as "Salary Advance" is only an expense line; payroll will not take it back.

Deleting a payment that came from a payslip marks the payslip unpaid again. Deleting a salary advance's payment also removes the advance, unless payroll has already taken it back (then you are told to reopen that month's payroll first).

---

## 9. Items (services and stock)

*Menu → Items.* The price list: services (labour) and stock you sell.

| Control | What it does |
|---|---|
| **Add item** *(owners)* | Opens the item form. |
| Search | By name. |
| **All / Running low / Services** | Filters. *Running low* = stock at or below the level set in Settings. |
| Pencil / bin *(owners)* | Edit or delete. |

Columns: item (with description and unit), **In stock** (red when low; *Service* for things without stock), cost and margin *(owners only)*, price, and automatic discount.

### Item form

| Field | What to enter |
|---|---|
| Name | Required, e.g. "Engine oil 5W-30 (4 L)" or "Full wash and vacuum". |
| Description | Brand, grade or size. |
| Unit | Piece, Job, Litre, Bottle and so on. Use **Job** for services. |
| Keep count of stock (untick for services) | Tick for things on the shelf; untick for services. |
| Quantity in stock | How many you have now. Only for stock items. |
| Cost | What it costs you (labour/material estimate for services). Used for gross profit. |
| Price | What the customer pays. |
| Discount % | Optional automatic discount on every sale, e.g. 10. |

Stock changes automatically: down when added to an invoice or sale, back up when a line is removed or an invoice is cancelled, and up when added to a purchase order. Editing the quantity here sets it directly (use this after a stock count).

---

## 10. Purchase orders

*Menu → Purchase orders (owners).* Deliveries from suppliers. Adding items here increases stock.

| Control | What it does |
|---|---|
| **New purchase order** | Choose the **Supplier**, optionally type **Supplier's invoice no.**, press **Create purchase order**. |
| Search | Supplier, supplier invoice or order number. |

### Purchase order screen

| Field / button | What it does |
|---|---|
| Add an item, Quantity, Unit cost | Add what was delivered. Leave Unit cost empty to use the item's current cost, or type the price on the supplier's invoice; a new price also becomes the item's cost from then on. **Add** raises stock immediately. |
| − / + / bin | Change the quantity or remove a line (stock follows). |
| Supplier, Supplier's invoice no. | Can be changed. |
| Cost of items / Discount / To pay / Paid / Balance | The bill from the supplier. |
| Discount % | A discount the supplier gave on the whole order. |
| Amount paid, Paid by | What you have paid the supplier. |
| **Complete** | Saves and records the payment to the supplier as money out. |
| **Save** | Saves without recording payment. |
| **Delete this purchase order** | Deletes it after asking; its items come off stock. |

---

## 11. Suppliers

*Menu → Suppliers (owners).* Where you buy stock. **Add supplier** asks for Name (required), Phone and Address. The **Orders** column counts purchase orders; click it to see them. A supplier with orders cannot be deleted.

---

## 12. Staff

All staff pages are for owners. They live under **Staff** in the menu.

### 12.1 Attendance register

*Staff → Attendance.* One row per employee for one day. Mark it every day, ideally at closing time.

**Moving between days:** **‹ previous day**, the date box, **next day ›** and **Today**. Future days can't be marked. **Month view** opens the month grid. The line on the right shows the working hours and rules in use, with a **change** link to Settings.

| Column | What to enter |
|---|---|
| Status | **Not marked**, **Present**, **Half day**, **Leave**, **Absent** or **Day off**. |
| Leave type | For Leave and Half day: **Annual**, **Casual**, **Sick** or **No-pay**. A half day with no leave type is half no-pay. |
| In | Arrival time. Required for Present. |
| Out | Leaving time. Can be left empty until they go home; fill it in later and save again. |
| Worked out as | After saving: **Late …**, **Left … early**, **Overtime …** or *On time*. |
| Note | Anything worth remembering, e.g. "bus breakdown". |

- **Mark the rest present, 07:30–17:30** fills every *Not marked* row as Present with normal hours. Adjust any times, then **Save register**.
- Choosing **Leave, Absent or Day off** clears and greys out the time boxes.
- Setting a saved row back to **Not marked** and saving removes it.

**How the register works things out** (numbers from Settings → Staff and payroll):

- **Late:** arrived after work start plus the grace period. A 07:55 arrival with a 07:30 start and 10 minutes' grace is 25 minutes late.
- **Left early:** left before work end.
- **Overtime:** stayed at least the overtime minimum past work end; then all the minutes past work end count.
- **Lateness, leaving early and short leaves are recorded for your information only. They do not reduce pay.**

**Short leaves** (bottom of the page): time away during the day, e.g. 11:00–12:15 to the bank. Pick the **Employee**, **Left at**, **Back at** and an optional **Reason**, then **Add short leave**. The list shows each one with its length; the bin removes it.

### 12.2 Month view

*Attendance → Month view.* One row per employee, one square per day:

| Square | Meaning |
|---|---|
| **P** green | Present |
| **½** teal | Half day |
| **L** blue | Leave (hover for the type) |
| **A** red | Absent |
| **–** grey | Day off |
| Dashed outline | Not marked |
| Faded | A future day, or before the employee joined |
| Small orange dot | Late or left early that day |

Hover a square for times and details; click it to open that day's register. The right-hand columns total **Worked**, **Paid leave**, **No-pay**, **Late** (count and total time), **Short leaves** and **Overtime**. "N not marked" under a name shows days still to fill in. Use **‹ / ›** to change month.

### 12.3 Payroll

*Staff → Payroll.* One month at a time; it opens on last month. Use **‹ / ›** to change month.

**Draft (before finalising).** Nothing is saved until you finalise. Each employee has a card:

- **Left:** days worked, paid leave, no-pay days, not-marked days, late arrivals, short leaves and overtime for the month.
- **Middle (you can change):**

  | Field | What to enter |
  |---|---|
  | Allowances (Rs.) | Extra pay this month, e.g. an incentive. Counts towards EPF. |
  | Other deductions (Rs.) | Anything else to take off, e.g. a breakage. |
  | Note on payslip | Printed on the payslip. |
  | Take back advances | Each open salary advance, ticked by default. Untick to leave it for a later month. |

- **Right:** the payslip so far, showing salary or days × day rate, no-pay, overtime, allowances, gross, EPF 8%, advances, other deductions, **Net pay**, and the employer's EPF 12% + ETF 3%.

Warnings at the top tell you if register days are **not marked** (unmarked days are not paid to daily staff and not deducted from monthly staff) or if the month isn't over yet.

| Button | What it does |
|---|---|
| **Recalculate** | Updates every card with the amounts you typed. Saves nothing. |
| **Finalise payroll** | Saves the payslips (after asking). Ticked advances are marked as taken back. Refused if anyone's net pay would be below zero. |

**Finalised.** The page shows totals (net pay to hand over and how much is still to pay, gross, EPF to send, ETF to send, advances taken back) and one row per employee:

| Button | What it does |
|---|---|
| **Pay** (with Paid by) | Records the net pay as a wage payment (money out) after asking. The row then shows *Paid* and the date. |
| **Payslip** | Opens the printable A5 payslip in a new tab. |
| **Reopen as draft** | Only while nobody is paid: removes the payslips so you can change and finalise again. Advances it took back become open again. |

To change a month after paying someone: delete their wage payment on the Payments page (the payslip becomes unpaid), then reopen.

Who is on a month's payroll: employees marked *Working here* who have a salary or day rate set (or have register entries), and who had joined by the end of that month.

### 12.4 Payslip

A printable A5 page with the business name, employee details and EPF number, attendance (days worked, paid leave, no-pay, late arrivals, short leaves, overtime), earnings, deductions, **net pay**, the employer's EPF and ETF, the note, which advances were taken back, the payment date, and signature lines. Use **Print**, then **Close**.

### 12.5 Salary advances

*Staff → Salary advances.* Money given before payday.

| Field | What to enter |
|---|---|
| Employee | Who received it. |
| Amount (Rs.) | Required. |
| Date | When it was given (not in the future). |
| Paid by | Cash, Card, Bank Transfer or QR. |
| Note | Optional. |

**Record advance** saves it and records the money out on the Payments page. **Not yet taken back** shows what each person still owes. The list (**Open** or **All, including taken back**) shows each advance with its status. *Taken back, Oct 2026* links to the payslip that recovered it. An open advance can be deleted with the bin, which also deletes its payment.

### 12.6 Employees

*Staff → Employees.* **Working here / Everyone** filters out people who have left. Click a name (or the person icon) to open their page; the pencil edits; the bin deletes (refused once they have invoices, attendance, payments, payslips or advances).

| Field | What to enter |
|---|---|
| Name | Required. |
| Designation | e.g. Washer, Detailer. |
| Phone | Optional. |
| Joined date | Payroll ignores months before this and pro-rates the first month. |
| Paid | **Monthly salary** or **Daily wage**. |
| Monthly salary or day rate (Rs.) | The salary, or the rate per day worked. |
| EPF number | Printed on payslips. |
| Pay EPF and ETF | Untick for casual workers who aren't registered. |
| Working here | Untick when someone leaves. Keeps their history and removes them from the register and payroll. |
| Address | Optional. |

### 12.7 Employee page

Shows the pay set-up and five summary tiles: pay, this month so far, late this month, overtime this month, and advances still to take back (with a **Give an advance** link). Below that:

- **Leave in this year:** annual and casual leave used against the allowance, with days left, plus sick and no-pay days taken.
- **Last 14 register entries:** each links to that day's register.
- **Salary advances:** with status.
- **Payslips:** each month, gross, net and whether it's paid.

**Register** opens today's register; **Edit details** opens the Employees list filtered to this person.

---

## 13. Reports: Sales

*Reports → Sales (owners).*

**Period:** **Today, Last 7 days, Last 30 days, This month, Last month, Last 90 days**, or pick **From** and **To** dates and press **Show**. Every number is compared with the period of the same length just before. Changes show in green (better) or red (worse); for money owed, discounts and time per job, going down counts as better. Very large jumps show as "×N".

| Tile | Meaning |
|---|---|
| Revenue | Sales after discounts: finished services plus item sales. The bar splits services from item sales. |
| Gross profit | Revenue minus the cost of what was sold (not wages or bills), with the margin %. |
| Jobs done | Finished services, plus the number of counter sales. |
| Average job | Revenue per finished service. |
| Collected | Money actually received in the period (including for older sales). |
| Still owed | Unpaid on the period's sales. |
| Customers | How many were served, how many were new, and the share who came back. |
| Average time per job | From arrival to Done. |
| Discounts given | Total discounts and their share of the price before discounts. |

**Charts and tables:**

- **Revenue by day / by week** (weekly for periods over 9 weeks): services and item sales stacked. Hover a column for the figures; **Show as a table** lists every value.
- **What earned the money:** services and items ranked by revenue (hover for quantity, share and profit).
- **How customers paid:** share by payment method.
- **When vehicles arrive:** day-of-week × hour heatmap; darker means busier (average per week for longer periods). Use it for staffing.
- **Staff:** jobs, revenue and average time per employee.
- **Wash bays:** jobs, revenue and share per bay.
- **Top customers:** the top 10 by spend, with visits and last visit.
- **Still owed:** the oldest unpaid sales; click to open them.

### Staff report

*Reports → Staff (owners).* How the team is doing over any period, for **Everyone** or one employee (pick in the box next to the dates, or click a name in the scorecard). The period buttons, dates and "vs previous" comparisons work as on the Sales report.

| Tile | Meaning |
|---|---|
| Attendance rate | Days worked ÷ working days marked (days off don't count; a half day is 0.5). The bar splits worked, leave and absent. |
| Punctuality | Arrivals within the grace period ÷ all arrivals with a time. |
| Late arrivals | How many, and the total time; also how often people left early. |
| Absences | Days absent without leave. |
| Leave taken | Days of leave, split into paid and no-pay. |
| Short leaves | How many, and the total time away. |
| Overtime | Total overtime in the period. |
| Jobs done | Finished services assigned to staff, with revenue per day worked. |
| Advances given | Salary advances in the period, and how much is still to take back. |

A yellow warning appears if register days are **not marked**: those days are left out of every rate, so fill them in first for a true picture.

- **Who was in:** a column per day (per week for long periods) stacked by Present, Half day, Leave and Absent. Hover for numbers, or open **Show as a table**.
- **When people arrive:** how early or late arrivals are, against the start time. Late bands are orange.
- **Late arrivals by weekday:** the share of each weekday's arrivals that were late; the worst day is orange.
- **Scorecard:** one row per employee, covering attendance and punctuality (with small bars), late arrivals, absences, leave, short leaves, overtime, jobs, revenue, revenue per day worked, average job time and advances still owed. Click a name to see the report for just that person.
- **Staff cost by month:** gross pay plus employer EPF and ETF for the last six months, from finalised payrolls only.
- **Leave used this year:** annual and casual leave used against the allowance, plus sick and no-pay days, for everyone working here.
- **Salary advances given in this period,** with whether each has been taken back.

---

## 14. Setup

### Wash bays

*Setup → Wash bays (owners).* **Add wash bay**: Name (required, e.g. "Bay 1" or "Lift"), Capacity (tons), Remarks. Bays appear on the dashboard and in every *Wash bay* list.

### Users

*Setup → Users (owners).* Who can sign in. The table shows name, role, status and when they were added; the pencil edits. The box at the bottom explains what each role can do.

**Add user:** Name, Email, Password and Confirm password (at least 8 characters), **Role** (*Counter staff* or *Owner*), then **Add user**.

**Edit user:** Name, Email, Role, **Can sign in** (untick to switch an account off; they are signed out on their next click), and optionally a **New password** with confirmation (leave empty to keep the current one). There must always be at least one active owner, and you can't switch yourself off.

### Settings

*Setup → Settings (owners).* Each section has its own **Save** button. Values that were never saved here come from the server's configuration, and the page says so.

**Business details:** Business name, Address and Phone, as shown on receipts, payslips, the customer status page and SMS texts.

**Email** (used for password-reset emails): SMTP server, Port (usually 587 for STARTTLS, 465 for SSL), Security, Username, Password (saved encrypted; leave empty to keep it, tick **Remove it** to clear it), Send from. **Send a test email** checks the saved settings.

**SMS (notify.lk):**

| Field | What it does |
|---|---|
| Send SMS to customers | The main switch. Off = the Text buttons are disabled. |
| notify.lk user ID, notify.lk API key | From your notify.lk account. The key is saved encrypted. |
| Sender ID | The name customers see (approved on notify.lk, up to 11 characters). |
| Service started text, Service finished text | The messages. You can use `{customer}`, `{vehicle}`, `{business}` and `{link}`. |

**Send a test SMS** sends one text to the number you type (uses one credit).

**Receipt printer (RabbitMQ):** Send receipts to the printer (on/off), RabbitMQ host, Port, Username, Password, Queue name. **Test connection** checks the connection without printing. When the printer is off, use the **Print** button on invoices instead.

**Staff and payroll:**

| Setting | Default | Meaning |
|---|---|---|
| Work starts / Work ends | 07:30 / 17:30 | Normal hours, used for late, early and overtime. |
| Grace period (minutes) | 10 | Arrivals within this aren't late. |
| Overtime starts after (minutes) | 30 | Staying on less than this isn't overtime. |
| Annual leave / Casual leave (days a year) | 14 / 7 | Allowances shown on the employee page. |
| Monthly salary per day: divide by | 30 | A no-pay day takes salary ÷ this. |
| Monthly salary per hour: divide by | 240 | Hourly rate for monthly staff overtime. Daily staff: day rate ÷ normal hours. |
| Overtime pay rate (%) | 150 | 150 = time and a half. |
| EPF from the employee / employer (%) | 8 / 12 | |
| ETF from the employer (%) | 3 | |

**General:** **Running low at** (the stock level that counts as low) and **Customer status link works for (hours)** (how long the link in the "started" SMS keeps working).

---

## 15. Your account

*Account* (under your name at the bottom of the menu). Change your **Name**, **Email**, **Profile picture** (JPG or PNG) and **Theme** (*Light* or *Dark*), then **Save account**. Owners also see **Manage users**. **Sign out** is next to Account.

---

## 16. What customers see

- **Home page (https://harithma.lk):** the public website with services, how it works, contact details and a map. Contact details come from Settings → Business details.
- **Status page:** the link in the "started" SMS. It shows the vehicle plate, where it is (Waiting → Vacuuming → Washing → Polishing → Done, updating every minute) and the bill so far. The link stops working after the number of hours set in Settings.
- **Receipt:** printed by the receipt printer, or from **Print** on an invoice. It shows business details, invoice number and date, customer, vehicle, bay, mileage, the lines, totals, what was paid and change.

---

## 17. How money and stock are worked out

**Invoice totals**
- Line amount = quantity × unit price − the item's automatic discount % − any extra discount.
- **Total** = sum of lines − bill discount.
- **Balance** = total − amount paid. Positive means still to collect; negative means change to give back.
- When an invoice is completed, the amount recorded as money in is the amount paid, but never more than the total (the rest is change).

**Stock**
- Goes down when a stock item is added to an invoice or sale, and back up when removed or cancelled.
- Goes up when added to a purchase order, and down when removed from one.
- You can't sell more than you have; the app says how many are left.

**Payroll** (with the default settings)
- **Monthly staff:** salary − salary ÷ 30 per no-pay day. The month they join is pro-rated by calendar days.
- **Daily staff:** day rate × days worked (half days count 0.5). Leave is not paid to daily staff.
- **No-pay days:** absent days, no-pay leave, and the unpaid half of a half day without a paid leave type.
- **Overtime:** hours × hourly rate × 150%.
- **EPF and ETF:** worked out on salary − no-pay + allowances (not overtime). Employee EPF 8% comes off pay; employer EPF 12% and ETF 3% are on top.
- **Net pay** = gross − EPF 8% − advances taken back − other deductions.
- **Lateness and short leaves never change pay.**

---

## 18. Common tasks and questions

**A customer will pay later.** Complete the invoice with **Paid by: Credit** and the amount paid (0 or a part). It shows under *Unpaid on finished jobs* and in **Service invoices → Unpaid**. When they pay, open the invoice, enter the new total paid and press **Complete** again, or use **Record payment** linked to the invoice.

**I added the wrong item.** Use the bin on that line, or **−** to reduce the quantity. Stock is put back.

**The customer's vehicle has a new owner.** Customers → click the plate → change **Owner** → **Save vehicle**.

**Refund.** Owners: record a payment, **Money out**, linked to the invoice, with a note.

**A staff member forgot to clock out.** Open that day's register, fill in **Out**, and **Save register**.

**Someone has left.** Employees → pencil → untick **Working here**. Users → edit → untick **Can sign in** if they had an account.

**Payroll is wrong after finalising.** If nobody is paid yet, **Reopen as draft**. If someone is paid, delete their wage payment on Payments first, then reopen.

**Prices changed.** Items → pencil → change **Price** (and **Cost**). Existing invoices keep the old prices.

**The SMS buttons are greyed out.** The customer has no phone number (add one on the Customers page), or that text was already sent. If a text fails, the message at the top says why: often SMS is switched off or not set up in Settings.

**The receipt didn't print.** The printer may be off or unreachable. Use **Print** on the invoice. Owners can use **Test connection** in Settings.

**I can't see a page my colleague can.** It is owner-only. Ask an owner.

**Something says "Choose … from the list".** Type in the box and click an entry in the list that appears.

---

## 19. Glossary

| Term | Meaning |
|---|---|
| Service invoice | One visit of a vehicle, from arrival to Done. |
| Item invoice / item sale | A counter sale of stock without a service. |
| Walk-in | A counter sale with no named customer. |
| Stage / status | Waiting, Vacuuming, Washing, Polishing, Done. |
| On the floor | Vehicles currently in the station. |
| Gross / net (invoices) | In the database "gross price" is what the customer owes after discounts. |
| Gross pay / net pay | Pay before / after deductions. |
| No-pay day | A day not paid to monthly staff (absent, no-pay leave). |
| Short leave | Time away during a working day; tracked, not deducted. |
| Salary advance | Money given before payday, taken back on payroll. |
| EPF / ETF | Employees' Provident Fund (8% employee + 12% employer) and Employees' Trust Fund (3% employer). |
| Purchase order | A delivery from a supplier; it adds stock. |
| Running low | A stock item at or below the level in Settings. |
