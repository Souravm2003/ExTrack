from django.db import models
from django.contrib.auth.models import User

class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Budget: ₹{self.amount}"
    
    @property
    def remaining_amount(self):
        """Calculate remaining budget amount"""
        total_expenses = self.user.expense_set.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        return self.amount - total_expenses
    
    @property
    def spent_percentage(self):
        """Calculate percentage of budget spent"""
        if self.amount == 0:
            return 0
        total_expenses = self.user.expense_set.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        return min((total_expenses / self.amount) * 100, 100)

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('food', 'Food'),
        ('rent', 'Rent'),
        ('transport', 'Transport'),
        ('entertainment', 'Entertainment'),
        ('healthcare', 'Healthcare'),
        ('shopping', 'Shopping'),
        ('utilities', 'Utilities'),
        ('education', 'Education'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    date = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} - ₹{self.amount}"
