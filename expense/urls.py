from django.urls import path
from django.shortcuts import redirect
from . import views
from . import user_views

urlpatterns = [
    # Root
    path('', lambda request: redirect('login'), name='home'),

    # ── Authentication ────────────────────────────────────────────────────
    path('login/',    views.login_view,    name='login'),
    path('logout/',   views.logout_view,   name='logout'),
    path('register/', views.register_view, name='register'),

    # ── HTML pages ────────────────────────────────────────────────────────
    path('dashboard/', views.dashboard, name='dashboard'),
    path('overview/',  views.overview,  name='overview'),

    # ── Expense CRUD ──────────────────────────────────────────────────────
    path('list/',             views.get_expenses,    name='expense-list'),  # viewer+
    path('add/',              views.create_expense,  name='expense-add'),   # admin
    path('edit/<int:pk>/',    views.edit_expense,    name='expense-edit'),  # admin
    path('delete/<int:pk>/',  views.delete_expense,  name='expense-delete'),# admin

    # ── Analytics ─────────────────────────────────────────────────────────
    path('ai-insights/', views.ai_insights, name='ai-insights'),  # analyst+

    # ── User Management API (admin only, except /me/) ─────────────────────
    path('api/users/',           user_views.list_users,      name='user-list'),
    path('api/users/me/',        user_views.my_profile,      name='user-me'),
    path('api/users/create/',    user_views.create_user_api, name='user-create'),
    path('api/users/<int:pk>/',  user_views.manage_user,     name='user-detail'),
]