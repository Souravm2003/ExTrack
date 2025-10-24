from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Expense, Budget, Income
from django.db.models import Q
from .serializers import ExpenseSerializer

# Authentication Views
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Basic validation
        if not username:
            messages.error(request, 'Username is required.')
        elif len(username) < 3:
            messages.error(request, 'Username must be at least 3 characters long.')
        elif not password1:
            messages.error(request, 'Password is required.')
        elif len(password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        elif password1 != password2:
            messages.error(request, 'Passwords do not match.')
        else:
            # Create user using Django's User model
            from django.contrib.auth.models import User
            try:
                user = User.objects.create_user(username=username, password=password1)
                messages.success(request, f'Account created for {username}! You can now log in.')
                return redirect('login')
            except Exception as e:
                messages.error(request, 'Username already exists. Please choose a different username.')
    else:
        # Create a dummy form for template compatibility
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

# Dashboard view with proper authentication
@login_required
def dashboard(request):
    if request.method == 'POST':
        # Handle budget setting
        if 'budget_amount' in request.POST:
            budget_amount = request.POST.get('budget_amount')
            if budget_amount:
                budget, created = Budget.objects.get_or_create(
                    user=request.user,
                    defaults={'amount': budget_amount}
                )
                if not created:
                    budget.amount = budget_amount
                    budget.save()
                messages.success(request, f'Budget set to ₹{budget_amount}!')
            return redirect('dashboard')

        # Handle income addition (separate form)
        if 'income_title' in request.POST:
            income_title = request.POST.get('income_title')
            income_amount = request.POST.get('income_amount')
            income_date = request.POST.get('income_date')
            income_description = request.POST.get('income_description')
            if income_title and income_amount and income_date:
                Income.objects.create(
                    user=request.user,
                    title=income_title,
                    amount=income_amount,
                    date=income_date,
                    description=income_description
                )
                messages.success(request, 'Income added successfully!')
            return redirect('dashboard')

        # Handle expense addition
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        category = request.POST.get('category')
        date = request.POST.get('date')
        description = request.POST.get('description')

        if title and amount and date:
            Expense.objects.create(
                user=request.user,
                title=title,
                amount=amount,
                category=category,
                date=date,
                description=description
            )
            messages.success(request, 'Expense added successfully!')
        return redirect('dashboard')

    # Base queryset
    expenses = Expense.objects.filter(user=request.user).order_by('-date')

    # Search / filter via GET parameters (title/name, category, date)
    q = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    date_filter = request.GET.get('date', '').strip()

    if q:
        # search in title and description
        expenses = expenses.filter(Q(title__icontains=q) | Q(description__icontains=q))

    if category_filter:
        expenses = expenses.filter(category=category_filter)

    if date_filter:
        # expecting YYYY-MM-DD
        expenses = expenses.filter(date=date_filter)
    incomes = Income.objects.filter(user=request.user).order_by('-date')
    
    # Get or create budget
    budget, created = Budget.objects.get_or_create(
        user=request.user,
        defaults={'amount': 0}
    )
    
    # Calculate statistics
    total_amount = sum(float(expense.amount) for expense in expenses)
    categories_count = len(set(expense.category for expense in expenses))

    # Income statistics
    total_income = sum(float(income.amount) for income in incomes)
    
    # Calculate monthly total (current month)
    from datetime import datetime
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_expenses = expenses.filter(date__month=current_month, date__year=current_year)
    monthly_total = sum(float(expense.amount) for expense in monthly_expenses)

    monthly_incomes = incomes.filter(date__month=current_month, date__year=current_year)
    monthly_income_total = sum(float(income.amount) for income in monthly_incomes)
    
    context = {
        'expenses': expenses,
        'incomes': incomes,
        'total_amount': total_amount,
        'total_income': total_income,
        'monthly_total': monthly_total,
        'monthly_income_total': monthly_income_total,
        'categories_count': categories_count,
        'budget': budget,
    }
    
    return render(request, 'dashboard.html', context)

# Overview page with expense analytics
@login_required
def overview(request):
    expenses = Expense.objects.filter(user=request.user)
    
    # Calculate totals by category
    category_totals = {}
    total_amount = 0
    
    for expense in expenses:
        category = expense.category
        if category not in category_totals:
            category_totals[category] = 0
        category_totals[category] += float(expense.amount)
        total_amount += float(expense.amount)
    
    # Calculate percentages for each category
    category_percentages = {}
    for category, amount in category_totals.items():
        if total_amount > 0:
            category_percentages[category] = (amount / total_amount) * 100
        else:
            category_percentages[category] = 0
    
    # Calculate average expense
    average_amount = total_amount / expenses.count() if expenses.count() > 0 else 0
    
    # Get recent expenses
    recent_expenses = expenses.order_by('-date')[:5]
    
    context = {
        'category_totals': category_percentages,  # Using percentages for display
        'category_amounts': category_totals,     # Keep original amounts for chart
        'category_list': [(cat, category_totals[cat], category_percentages[cat]) for cat in category_totals.keys()],
        'total_amount': total_amount,
        'average_amount': average_amount,
        'recent_expenses': recent_expenses,
        'expense_count': expenses.count(),
    }
    
    return render(request, 'overview.html', context)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_expenses(request):
    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    serializer = ExpenseSerializer(expenses, many=True)
    return Response(serializer.data)

# Create a new expense
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_expense(request):
    data = request.data.copy()
    data['user'] = request.user.id
    serializer = ExpenseSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Delete an expense
@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    expense.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Expense deleted successfully!'})
    
    messages.success(request, 'Expense deleted successfully!')
    return redirect('dashboard')

# Edit an expense
@login_required
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    
    if request.method == 'POST':
        expense.title = request.POST.get('title')
        expense.amount = request.POST.get('amount')
        expense.category = request.POST.get('category')
        expense.date = request.POST.get('date')
        expense.description = request.POST.get('description')
        expense.save()
        messages.success(request, 'Expense updated successfully!')
        return redirect('dashboard')
    
    # Return expense data as JSON for modal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.http import JsonResponse
        return JsonResponse({
            'id': expense.pk,
            'title': expense.title,
            'amount': float(expense.amount),
            'category': expense.category,
            'date': expense.date.strftime('%Y-%m-%d'),
            'description': expense.description or '',
        })
    
    return render(request, 'edit_expense.html', {'expense': expense})
