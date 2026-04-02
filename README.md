# ExTrack — Finance Data Processing and Access Control Backend

A full-stack expense and income tracking system built with **Django** and **SQLite3**.  
It supports financial record management, dashboard analytics, and role-aware access control through Django's authentication system.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Running Locally](#running-locally)
- [API Endpoints](#api-endpoints)
- [Data Models](#data-models)
- [Access Control](#access-control)
- [Dashboard & Analytics](#dashboard--analytics)
- [Validation & Error Handling](#validation--error-handling)
- [Assumptions & Tradeoffs](#assumptions--tradeoffs)
- [Assignment Coverage](#assignment-coverage)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.2.4 |
| REST API | Django REST Framework 3.16.0 |
| Database | SQLite3 (built-in, no setup required) |
| Auth | Django Session-based Authentication |
| Static Files | WhiteNoise |
| Server | Gunicorn (production) / Django Dev Server (local) |

---

## Project Structure

```
ExTrack1/
├── ExTrack/                  # Django project config
│   ├── settings.py           # Database, middleware, app settings
│   ├── urls.py               # Root URL router
│   └── wsgi.py
├── expense/                  # Core application
│   ├── models.py             # UserProfile, Expense, Income, Budget + signals
│   ├── views.py              # Auth + financial views (RBAC applied)
│   ├── user_views.py         # User Management API (admin only)
│   ├── serializers.py        # DRF serializers (expense, income, user)
│   ├── permissions.py        # DRF permission classes (IsViewerOrAbove etc.)
│   ├── decorators.py         # Role decorators for HTML views
│   ├── urls.py               # All URL patterns (expense + user API)
│   ├── admin.py              # Admin registrations for all models
│   └── migrations/           # Database migrations
├── templates/                # Django HTML templates
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   └── overview.html
├── db.sqlite3                # SQLite database file
├── manage.py
├── requirements.txt
└── .env                      # Environment variables (not committed)
```

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- pip

### Steps

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd ExTrack1

# 2. Create a virtual environment
python -m venv env

# 3. Activate the virtual environment
# Windows (PowerShell)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
env\Scripts\activate

# Windows (Command Prompt)
env\Scripts\activate.bat

# macOS / Linux
source env/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Set up environment variables
# Copy the example and edit if needed
copy .env.example .env   # Windows
cp .env.example .env     # macOS/Linux

# 6. Apply database migrations
python manage.py migrate

# 7. Create a superuser (for Django Admin access)
python manage.py createsuperuser
```

### Environment Variables (`.env`)

```env
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
```

> **Note:** No `DATABASE_URL` is needed. The project uses SQLite3 by default (the `db.sqlite3` file at the project root).

---

## Running Locally

```bash
python manage.py runserver
```

The application will be available at: **http://127.0.0.1:8000**

| Page | URL |
|---|---|
| Home (redirects to login) | http://127.0.0.1:8000/ |
| Login | http://127.0.0.1:8000/login/ |
| Register | http://127.0.0.1:8000/register/ |
| Dashboard | http://127.0.0.1:8000/dashboard/ |
| Overview & Analytics | http://127.0.0.1:8000/overview/ |
| Django Admin Panel | http://127.0.0.1:8000/admin/ |

---

## API Endpoints

All API endpoints return JSON and require the user to be authenticated.

### Authentication (Session-based)

| Method | URL | Description | Auth Required |
|---|---|---|---|
| `GET/POST` | `/login/` | Login with username & password | No |
| `POST` | `/logout/` | End session | Yes |
| `GET/POST` | `/register/` | Create new account | No |

### Financial Records

| Method | URL | Description | Role Required |
|---|---|---|---|
| `GET` | `/list/` | List expenses (supports `?q=&category=&date=`) | Viewer+ |
| `POST` | `/add/` | Create a new expense | Admin |
| `GET/POST` | `/edit/<id>/` | View or update an expense | Admin |
| `POST` | `/delete/<id>/` | Delete an expense | Admin |

**`GET /list/`** — supports the following query parameters:

| Param | Type | Description |
|---|---|---|
| `q` | string | Search by title or description |
| `category` | string | Filter by category (food, rent, transport, etc.) |
| `date` | date | Filter by specific date (YYYY-MM-DD) |

**Example response from `GET /list/`:**
```json
[
  {
    "id": 1,
    "user": 1,
    "title": "Grocery Shopping",
    "amount": "850.00",
    "category": "food",
    "date": "2026-04-01",
    "description": "Weekly groceries"
  }
]
```

### Dashboard & Analytics

| Method | URL | Description | Role Required |
|---|---|---|---|
| `GET` | `/dashboard/` | Full dashboard with stats | Viewer+ |
| `GET` | `/overview/` | Category breakdown & recent activity | Viewer+ |
| `GET` | `/ai-insights/` | Heuristic spending insights (JSON) | Analyst+ |

### User Management (Admin Only)

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/users/` | List all users (filter: `?role=&is_active=`) |
| `POST` | `/api/users/create/` | Create a user with role |
| `GET` | `/api/users/me/` | Current user's own profile (all roles) |
| `GET` | `/api/users/<id>/` | Get single user detail |
| `PATCH` | `/api/users/<id>/` | Update role or active status |
| `DELETE` | `/api/users/<id>/` | Soft-deactivate a user |

**Create user body:**
```json
{ "username": "alice", "password": "secret123", "email": "", "role": "analyst" }
```

**Update user body (PATCH):**
```json
{ "role": "admin", "is_active": true }
```

**Example response from `GET /ai-insights/`:**
```json
{
  "total_amount": 12400.00,
  "monthly_total": 3200.00,
  "avg_monthly": 4133.33,
  "top_categories": [
    {"category": "food", "amount": 5200.00},
    {"category": "rent", "amount": 4000.00}
  ],
  "high_spend": [
    {"category": "food", "amount": 5200.00, "percent_of_total": 41.9}
  ],
  "budget_warning": {
    "budget": 3000.00,
    "monthly_total": 3200.00,
    "over_by": 200.00,
    "is_over": true
  },
  "suggestions": [
    "On Food: Try cooking at home more often or set a weekly dining-out limit.",
    "Estimated monthly savings rate: 68.0%"
  ],
  "savings_rate": 68.0
}
```

---

## Data Models

### `Expense`
| Field | Type | Description |
|---|---|---|
| `id` | AutoField | Primary key |
| `user` | ForeignKey → User | Owner |
| `title` | CharField(100) | Expense title |
| `amount` | DecimalField | Amount in ₹ |
| `category` | CharField | `food`, `rent`, `transport`, `entertainment`, `healthcare`, `shopping`, `utilities`, `education`, `other` |
| `date` | DateField | Expense date |
| `description` | TextField | Optional notes |

### `Income`
| Field | Type | Description |
|---|---|---|
| `id` | AutoField | Primary key |
| `user` | ForeignKey → User | Owner |
| `title` | CharField(100) | Income source title |
| `amount` | DecimalField | Amount in ₹ |
| `date` | DateField | Receipt date |
| `description` | TextField | Optional notes |
| `created_at` | DateTimeField | Auto timestamp |

### `Budget`
| Field | Type | Description |
|---|---|---|
| `id` | AutoField | Primary key |
| `user` | ForeignKey → User | Owner (one per user) |
| `amount` | DecimalField | Monthly budget cap |
| `created_at` | DateTimeField | Auto timestamp |
| `updated_at` | DateTimeField | Auto timestamp |

**Computed properties on `Budget`:**
- `remaining_amount` — budget minus all-time expenses
- `spent_percentage` — percentage of budget consumed (capped at 100%)

---

## Access Control

The system implements a **three-tier role model** enforced at every endpoint.

### Roles

| Role | Description |
|---|---|
| **Viewer** | Read-only: can view dashboard, overview, and expense list |
| **Analyst** | Viewer permissions + access to AI Insights analytics |
| **Admin** | Full access: create/edit/delete records + all User Management APIs |

New users self-registering via `/register/` receive the **Viewer** role automatically.
An Admin can promote any user via `PATCH /api/users/<id>/`.

### Permission Enforcement

| Layer | Mechanism |
|---|---|
| HTML views | Inline `profile.role` check with `messages.error` + redirect |
| DRF API views | Custom `IsViewerOrAbove`, `IsAnalystOrAbove`, `IsAdminRole` permission classes |
| Inactive accounts | Blocked at login; session terminated if detected mid-session |
| Data isolation | All ORM queries scoped to `user=request.user` |

### Role Permission Matrix

| Endpoint | Viewer | Analyst | Admin |
|---|---|---|---|
| GET `/dashboard/` | ✅ | ✅ | ✅ |
| GET `/overview/` | ✅ | ✅ | ✅ |
| GET `/list/` | ✅ | ✅ | ✅ |
| GET `/ai-insights/` | ❌ | ✅ | ✅ |
| POST `/add/` | ❌ | ❌ | ✅ |
| POST `/dashboard/` (create records) | ❌ | ❌ | ✅ |
| POST `/edit/<id>/` | ❌ | ❌ | ✅ |
| POST `/delete/<id>/` | ❌ | ❌ | ✅ |
| GET `/api/users/me/` | ✅ | ✅ | ✅ |
| All `/api/users/` management | ❌ | ❌ | ✅ |

---

## Dashboard & Analytics

The `/dashboard/` endpoint computes the following in a single aggregated query:

- **Total expenses** — all-time sum
- **Total income** — all-time sum
- **Monthly expenses** — current month sum
- **Monthly income** — current month sum
- **Categories count** — number of distinct expense categories used
- **Budget status** — current budget vs. remaining

The `/ai-insights/` endpoint provides heuristic analysis:
- **Top 5 categories** by spending
- **High-spend alerts** — categories exceeding 20% of total or 60% of average monthly
- **Budget warning** — whether this month's spending exceeds the set budget
- **Savings rate** — estimated from income vs. monthly spend
- **Actionable suggestions** — category-specific tips based on spending patterns

---

## Validation & Error Handling

| Scenario | Handling |
|---|---|
| Login with wrong credentials | `messages.error` — "Invalid username or password" |
| Register with duplicate username | Caught via Django's `create_user` exception |
| Register with short password (<8 chars) | Custom pre-check with error message |
| Passwords don't match | Pre-check with error message |
| Access dashboard without login | Django `@login_required` redirects to `/login/` |
| Edit/delete another user's expense | `get_object_or_404(Expense, pk=pk, user=request.user)` returns 404 |
| API validation (DRF serializer) | Returns `400 Bad Request` with field-level error details |
| Missing required fields in forms | Conditional checks before DB operations |

---

## Assumptions & Tradeoffs

1. **Single-user budget model**: One budget per user (no per-category or per-month budgets). Chosen for simplicity; a more complete system would allow granular budget management.

2. **Session-based auth over JWT**: Chosen because the primary interface is HTML-rendered templates. Token-based auth would be better for a pure API approach.

3. **Role model via UserProfile**: Roles are stored in a `UserProfile` model (OneToOne with Django's `User`). A `post_save` signal auto-creates a `viewer` profile for every new user. Admins upgrade roles via the User Management API.

4. **50-record limit** on dashboard instead of pagination: A simple hard limit keeps responses fast. Real pagination (e.g., DRF `PageNumberPagination`) would be cleaner.

5. **Income has no REST API**: Income is managed through the HTML dashboard form only. The model is correct, but a full REST endpoint was deprioritized.

6. **Soft delete for users, hard delete for records**: Users are soft-deactivated (`is_active=False`) preserving audit history. Individual expense records are hard-deleted since there is no audit requirement specified.

---

## Assignment Coverage

| Requirement | Status |
|---|---|
| Financial record CRUD | ✅ Implemented |
| Filter records (date, category, search) | ✅ Implemented |
| Dashboard summary APIs | ✅ Implemented |
| Category-wise totals | ✅ Implemented |
| Monthly/weekly trends | ✅ Implemented |
| Recent activity | ✅ Implemented |
| User auth (login/register/logout) | ✅ Implemented |
| Data isolation per user | ✅ Implemented |
| SQLite3 persistence | ✅ Implemented |
| Input validation | ✅ Implemented |
| Error handling (4xx status codes) | ✅ Implemented |
| Application-level RBAC (Viewer/Analyst/Admin) | ✅ Implemented |
| User Management APIs (list/create/update/deactivate) | ✅ Implemented |
| Soft delete (user deactivation) | ✅ Implemented |
| Income REST API | ⚠️ Partial (model + HTML only) |
| Pagination | ⚠️ Hard limit only |

---

## Deployment (Render)

This project is pre-configured for deployment on [Render](https://render.com) using the included `Procfile`, `build.sh`, and WhiteNoise for static files.

### Prerequisites
- A [Render](https://render.com) account (free tier works)
- This repository pushed to GitHub

### Steps

1. **Log into [Render Dashboard](https://dashboard.render.com)**
2. **Create a New Web Service** → Connect your GitHub repo (`Souravm2003/ExTrack`)
3. **Configure the service:**

| Setting | Value |
|---|---|
| **Name** | `extrack` (or any name) |
| **Region** | Choose the closest to you |
| **Branch** | `master` |
| **Runtime** | `Python 3` |
| **Build Command** | `chmod +x build.sh && ./build.sh` |
| **Start Command** | `gunicorn ExTrack.wsgi --log-file -` |

4. **Set Environment Variables** (under "Environment" tab):

| Variable | Value |
|---|---|
| `DJANGO_SECRET_KEY` | Generate a strong random key |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `extrack-XXXX.onrender.com` (your Render URL) |
| `CSRF_TRUSTED_ORIGINS` | `https://extrack-XXXX.onrender.com` |
| `PYTHON_VERSION` | `3.11.11` |

5. Click **Create Web Service** — Render will build and deploy automatically.

6. **Create the admin user**
   Visit `https://extrack-XXXX.onrender.com/setup/`
   This creates a default admin account:
   | Field | Value |
   |---|---|
   | **Username** | `admin` |
   | **Password** | `admin123` |

### Live URL

After deployment, the app will be available at: `https://extrack-XXXX.onrender.com`

> **Note:** The free tier uses ephemeral storage, so the SQLite database resets on each deploy. The `build.sh` script runs migrations to recreate tables automatically.

---

## Running Tests

```bash
python manage.py test
```

---

*Built with Django 5.2.4 · SQLite3 · Django REST Framework*
