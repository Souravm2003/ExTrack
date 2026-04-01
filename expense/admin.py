from django.contrib import admin
from .models import Expense, Income, Budget, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'role', 'is_active', 'created_at')
    list_filter   = ('role', 'is_active')
    search_fields = ('user__username', 'user__email')
    list_editable = ('role', 'is_active')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display  = ('title', 'user', 'amount', 'category', 'date')
    list_filter   = ('category', 'date')
    search_fields = ('title', 'user__username')


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display  = ('title', 'user', 'amount', 'date')
    search_fields = ('title', 'user__username')


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'updated_at')
