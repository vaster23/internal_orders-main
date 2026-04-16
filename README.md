# Luminex Internal Orders

A Django-based internal order management platform for Luminex.

This project helps teams create, manage, and track internal product orders across different branches through a clean web interface.

## Features

- User authentication with a custom branded login page
- Internal order creation with product selection and quantity controls
- Order tracking with status updates
- Branch-aware order visibility
- User-to-branch assignment
- Product, unit, category, and branch management
- Admin-ready data management dashboard
- Responsive UI built with Tailwind CSS

## Main Modules

### `core`

Handles:

- home page
- dashboard
- login flow
- user management
- user-to-branch assignment

### `products`

Handles:

- products
- categories
- units
- branches

### `orders`

Handles:

- internal order creation
- order list view
- status updates
- branch-based highlighting and filtering

## Tech Stack

- Python
- Django 6
- MySQL
- Tailwind CSS via CDN

## Project Structure

```text
internal_orders/
├── config/
├── core/
├── orders/
├── products/
├── requirements.txt
├── manage.py
└── README.md
```

## Setup

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd internal_orders
```

### 2. Create and activate a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If `mysqlclient` is not available on your machine, install the required MySQL development tools first.

### 4. Configure the database

In `config/settings.py`, the project currently uses MySQL:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'internal_orders',
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

Create the MySQL database before running migrations:

```sql
CREATE DATABASE internal_orders;
```

Update credentials in `config/settings.py` if needed.

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

Then open:

- `http://127.0.0.1:8000/login/`

## Default App Flow

After login, users can:

- go to the Home page
- create a new order
- view all orders
- update order statuses
- manage users and data if they have the required permissions

## Order Status Flow

The order lifecycle currently supports:

- `unread`
- `read`
- `in_progress`
- `ready`
- `delivered`

When an unread order is opened, it is automatically marked as read.

## Branch Logic

- Each user is assigned to one branch
- In the order list, the UI highlights the items that are relevant to the user's branch
- If the user belongs to `Αρτοποιείο` or `Ζαχαροπλαστείο`, the order details show only the items for that branch
- In the new order page, all users can view all products

## Important Routes

- `/login/` - login page
- `/` - home page
- `/orders/` - order list
- `/orders/shop/` - create new order
- `/users/` - user management
- `/dashboard/` - data management dashboard
- `/products/` - product management
- `/admin/` - Django admin

## Requirements File

The project includes a ready-to-use `requirements.txt` generated from the development environment.

Install everything with:

```bash
pip install -r requirements.txt
```

Current packages:

- `asgiref==3.11.1`
- `Django==6.0.3`
- `mysqlclient==2.2.8`
- `sqlparse==0.5.5`
- `tzdata==2025.3`

## Notes

- The UI is optimized for internal business use
- The layout is designed to stay fixed at the page level with internal scrolling where needed
- Tailwind is loaded through CDN, so no frontend build step is required

## Future Improvements

- search and filters for orders
- analytics dashboard
- notifications
- export options
- audit logs

## License

This project is for internal/company use unless you choose to add an open-source license.
