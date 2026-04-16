# Luminex Internal Orders

A professional internal order & delivery management platform for multi-branch businesses.

---

## 🚀 Overview

Luminex Internal Orders is a web-based system designed to manage internal product transfers between company branches.

It provides real-time visibility, role-based access, and delivery tracking through a clean and modern interface.

---

## 🔑 Key Features

- 🔐 Role-based access (Admin / User / Driver)
- 📦 Internal order creation with product selection
- 🚚 Driver workflow (Pickup → Delivery)
- 📍 Route preview with map visualization
- ⏱ Estimated delivery time (ETA)
- 🔍 Advanced filtering & search
- 📊 CSV export for reporting
- 🧑‍💼 User & branch management
- 📱 Responsive modern UI (Tailwind CSS)

---

## 🧱 Tech Stack

- Backend: Django
- Database: MySQL
- Frontend: Tailwind CSS
- Maps: Leaflet.js

---

## 👥 User Roles

### Admin
- Full system control
- Manage users, branches, products
- Update order statuses
- Export reports

### User (Branch Employee)
- Create internal orders
- View branch-related orders

### Driver
- View assigned deliveries
- Pickup & deliver orders
- View route & ETA

---

## 📦 Order Workflow

1. User creates order
2. Admin processes it
3. Order becomes "Ready for Pickup"
4. Driver picks it up
5. System calculates ETA
6. Driver delivers → Order completed

---

## 📊 Export & Reporting

- Export filtered orders to CSV
- Track delivery performance
- Monitor branch activity

---

## ⚙️ Setup

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver