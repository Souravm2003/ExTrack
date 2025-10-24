from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # Dashboard and expense management
    path('dashboard/', views.dashboard, name='dashboard'),
    path('overview/', views.overview, name='overview'),
    path('list/', views.get_expenses, name='expense-list'),
    path('add/', views.create_expense, name='expense-add'),
    path('edit/<int:pk>/', views.edit_expense, name='expense-edit'),
    path('delete/<int:pk>/', views.delete_expense, name='expense-delete'),
]
