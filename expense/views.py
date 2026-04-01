import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q
from datetime import datetime

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from .models import Expense, Budget, Income, UserProfile
from .serializers import ExpenseSerializer
from .permissions import IsViewerOrAbove, IsAdminRole



def _get_profile(user):
    """Return UserProfile for user, auto-creating a 'viewer' profile if absent."""
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': 'viewer'})
    return profile


def _check_active(request):
    """
    Call at the top of @login_required HTML views.
    Returns (profile, None) on success, or (None, redirect_response) if inactive.
    """
    profile = _get_profile(request.user)
    if not profile.is_active:
        logout(request)
        messages.error(request, 'Your account has been deactivated. Contact an administrator.')
        return None, redirect('login')
    return profile, None



def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            profile = _get_profile(user)
            if not profile.is_active:
                messages.error(request, 'Your account has been deactivated. Contact an administrator.')
                return render(request, 'login.html')
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}! (Role: {profile.role.title()})')
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


def register_view(request):
    form = UserCreationForm()
    if request.method == 'POST':
        username  = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

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
            from django.contrib.auth.models import User
            try:
                User.objects.create_user(username=username, password=password1)
                messages.success(request, f'Account created for {username}! You can log in now.')
                return redirect('login')
            except Exception:
                messages.error(request, 'Username already exists. Please choose a different one.')
    return render(request, 'register.html', {'form': form})



@login_required
def dashboard(request):
    profile, err = _check_active(request)
    if err:
        return err

    if request.method == 'POST':
        if profile.role != 'admin':
            messages.error(request, 'Only Admin users can create or modify records.')
            return redirect('dashboard')

        if 'budget_amount' in request.POST:
            budget_amount = request.POST.get('budget_amount')
            if budget_amount:
                budget, created = Budget.objects.get_or_create(
                    user=request.user, defaults={'amount': budget_amount}
                )
                if not created:
                    budget.amount = budget_amount
                    budget.save()
                messages.success(request, f'Budget set to ₹{budget_amount}!')
            return redirect('dashboard')

        if 'income_title' in request.POST:
            income_title       = request.POST.get('income_title')
            income_amount      = request.POST.get('income_amount')
            income_date        = request.POST.get('income_date')
            income_description = request.POST.get('income_description')
            if income_title and income_amount and income_date:
                Income.objects.create(
                    user=request.user, title=income_title,
                    amount=income_amount, date=income_date,
                    description=income_description,
                )
                messages.success(request, 'Income added successfully!')
            return redirect('dashboard')

        title       = request.POST.get('title')
        amount      = request.POST.get('amount')
        category    = request.POST.get('category')
        date        = request.POST.get('date')
        description = request.POST.get('description')
        if title and amount and date:
            Expense.objects.create(
                user=request.user, title=title, amount=amount,
                category=category, date=date, description=description,
            )
            messages.success(request, 'Expense added successfully!')
        return redirect('dashboard')

    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    q               = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    date_filter     = request.GET.get('date', '').strip()

    if q:
        expenses = expenses.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if category_filter:
        expenses = expenses.filter(category=category_filter)
    if date_filter:
        expenses = expenses.filter(date=date_filter)

    incomes = Income.objects.filter(user=request.user).order_by('-date')
    budget, _ = Budget.objects.get_or_create(user=request.user, defaults={'amount': 0})

    now = datetime.now()
    expense_stats = Expense.objects.filter(user=request.user).aggregate(
        total=Sum('amount'),
        monthly_total=Sum('amount', filter=Q(date__month=now.month, date__year=now.year)),
    )
    income_stats = Income.objects.filter(user=request.user).aggregate(
        total=Sum('amount'),
        monthly_total=Sum('amount', filter=Q(date__month=now.month, date__year=now.year)),
    )
    categories_count = (
        Expense.objects.filter(user=request.user).values('category').distinct().count()
    )

    context = {
        'expenses':             expenses[:50],
        'incomes':              incomes[:50],
        'total_amount':         expense_stats['total'] or 0,
        'total_income':         income_stats['total'] or 0,
        'monthly_total':        expense_stats['monthly_total'] or 0,
        'monthly_income_total': income_stats['monthly_total'] or 0,
        'categories_count':     categories_count,
        'budget':               budget,
        'user_role':            profile.role,
        'can_edit':             profile.role == 'admin',
    }
    return render(request, 'dashboard.html', context)



@login_required
def overview(request):
    profile, err = _check_active(request)
    if err:
        return err

    expenses       = Expense.objects.filter(user=request.user)
    category_totals = {}
    total_amount    = 0

    for expense in expenses:
        cat = expense.category
        category_totals.setdefault(cat, 0)
        category_totals[cat] += float(expense.amount)
        total_amount         += float(expense.amount)

    category_percentages = {
        cat: (amt / total_amount * 100 if total_amount > 0 else 0)
        for cat, amt in category_totals.items()
    }
    average_amount  = total_amount / expenses.count() if expenses.count() > 0 else 0
    recent_expenses = expenses.order_by('-date')[:5]

    context = {
        'category_totals':        category_percentages,
        'category_amounts':       category_totals,
        'category_amounts_json':  json.dumps(category_totals),
        'category_list':          [(c, category_totals[c], category_percentages[c]) for c in category_totals],
        'total_amount':           total_amount,
        'average_amount':         average_amount,
        'recent_expenses':        recent_expenses,
        'expense_count':          expenses.count(),
        'user_role':              profile.role,
    }
    return render(request, 'overview.html', context)



@api_view(['GET'])
@permission_classes([IsViewerOrAbove])
def get_expenses(request):
    """GET /list/ — viewer, analyst, admin. Supports ?category=&date=&q="""
    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    q               = request.query_params.get('q', '').strip()
    category_filter = request.query_params.get('category', '').strip()
    date_filter     = request.query_params.get('date', '').strip()

    if q:
        expenses = expenses.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if category_filter:
        expenses = expenses.filter(category=category_filter)
    if date_filter:
        expenses = expenses.filter(date=date_filter)

    serializer = ExpenseSerializer(expenses, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAdminRole])
def create_expense(request):
    """POST /add/ — admin only."""
    data = request.data.copy()
    data['user'] = request.user.id
    serializer = ExpenseSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required
def delete_expense(request, pk):
    """POST /delete/<pk>/ — admin only."""
    profile, err = _check_active(request)
    if err:
        return err

    if profile.role != 'admin':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Admin role required to delete records.'}, status=403)
        messages.error(request, 'Only Admin users can delete records.')
        return redirect('dashboard')

    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    expense.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Expense deleted successfully!'})
    messages.success(request, 'Expense deleted successfully!')
    return redirect('dashboard')


@login_required
def edit_expense(request, pk):
    """GET/POST /edit/<pk>/ — admin only."""
    profile, err = _check_active(request)
    if err:
        return err

    if profile.role != 'admin':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Admin role required to edit records.'}, status=403)
        messages.error(request, 'Only Admin users can edit records.')
        return redirect('dashboard')

    expense = get_object_or_404(Expense, pk=pk, user=request.user)

    if request.method == 'POST':
        expense.title       = request.POST.get('title')
        expense.amount      = request.POST.get('amount')
        expense.category    = request.POST.get('category')
        expense.date        = request.POST.get('date')
        expense.description = request.POST.get('description')
        expense.save()
        messages.success(request, 'Expense updated successfully!')
        return redirect('dashboard')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'id':          expense.pk,
            'title':       expense.title,
            'amount':      float(expense.amount),
            'category':    expense.category,
            'date':        expense.date.strftime('%Y-%m-%d'),
            'description': expense.description or '',
        })
    return render(request, 'edit_expense.html', {'expense': expense})



@login_required
def ai_insights(request):
    """
    GET /ai-insights/ — analyst and admin only.
    Heuristic spending analysis; no external API calls.
    """
    profile, err = _check_active(request)
    if err:
        return err

    if profile.role not in ('analyst', 'admin'):
        return JsonResponse({
            'error':      'Permission denied',
            'detail':     'AI Insights requires Analyst or Admin role.',
            'your_role':  profile.role,
        }, status=403)

    expenses     = Expense.objects.filter(user=request.user)
    incomes      = Income.objects.filter(user=request.user)
    total_amount = sum(float(e.amount) for e in expenses)

    now         = datetime.now()
    this_month  = expenses.filter(date__year=now.year, date__month=now.month)
    monthly_total = sum(float(e.amount) for e in this_month)

    category_totals = {}
    for e in expenses:
        category_totals.setdefault(e.category, 0.0)
        category_totals[e.category] += float(e.amount)

    sorted_cats    = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    top_categories = [{'category': k, 'amount': v} for k, v in sorted_cats[:5]]

    months      = set((e.date.year, e.date.month) for e in expenses)
    avg_monthly = total_amount / max(len(months), 1)

    high_spend = []
    for cat, amt in category_totals.items():
        pct = (amt / total_amount * 100) if total_amount > 0 else 0
        if pct >= 20 or amt >= (avg_monthly * 0.6):
            high_spend.append({'category': cat, 'amount': amt, 'percent_of_total': round(pct, 1)})

    budget_warning = None
    try:
        b = Budget.objects.get(user=request.user)
        over_by = monthly_total - float(b.amount)
        budget_warning = {
            'budget':        float(b.amount),
            'monthly_total': monthly_total,
            'over_by':       over_by,
            'is_over':       over_by > 0,
        }
    except Budget.DoesNotExist:
        pass

    tips_map = {
        'food':          'Try cooking at home more often or set a weekly dining-out limit.',
        'rent':          'Rent is fixed — consider negotiating utilities or saving elsewhere.',
        'transport':     'Use public transport, carpool, or plan trips to reduce fuel costs.',
        'entertainment': 'Pause subscriptions you rarely use and limit impulse purchases.',
        'shopping':      'Create a shopping list and wait 48 hours before big purchases.',
        'utilities':     'Check for energy-saving options and compare providers.',
        'education':     'Look for scholarships, discounts, or second-hand resources.',
        'healthcare':    'Review medicines and consider preventive care to reduce costs.',
        'other':         'Review miscellaneous purchases and categorize recurring fees.',
    }
    suggestions = []
    if monthly_total > avg_monthly * 1.1:
        suggestions.append('Your spending this month is higher than your average. Review recent transactions.')
    for hs in high_spend:
        tip = tips_map.get(hs['category'])
        if tip:
            suggestions.append(f"On {hs['category'].title()}: {tip}")

    total_income = sum(float(i.amount) for i in incomes)
    savings_rate = None
    if total_income > 0:
        savings_rate = round(((total_income - monthly_total) / total_income) * 100, 1)
        suggestions.append(f'Estimated monthly savings rate: {savings_rate}%')

    return JsonResponse({
        'total_amount':   round(total_amount, 2),
        'monthly_total':  round(monthly_total, 2),
        'avg_monthly':    round(avg_monthly, 2),
        'top_categories': top_categories,
        'high_spend':     high_spend,
        'budget_warning': budget_warning,
        'suggestions':    suggestions,
        'savings_rate':   savings_rate,
    })
