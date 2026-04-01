"""
Comprehensive test suite for ExTrack backend.
Covers: RBAC, CRUD, validation, analytics, user management.

Run:  python manage.py test expense -v 2
"""

import json
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase, Client
from django.contrib.auth.models import User

from .models import UserProfile, Expense, Income, Budget


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class BaseTestCase(TestCase):
    """Creates a viewer, analyst, and admin user before each test."""

    def setUp(self):
        self.client = Client()

        self.viewer = User.objects.create_user('viewer', password='testpass123')
        self.analyst = User.objects.create_user('analyst', password='testpass123')
        self.admin_user = User.objects.create_user('admin_u', password='testpass123')

        # Profiles are auto-created by the post_save signal as 'viewer'
        UserProfile.objects.filter(user=self.analyst).update(role='analyst')
        UserProfile.objects.filter(user=self.admin_user).update(role='admin')

    def _login(self, user):
        self.client.login(username=user.username, password='testpass123')

    def _create_expense(self, user, **kwargs):
        defaults = {
            'user': user,
            'title': 'Test Expense',
            'amount': Decimal('100.00'),
            'category': 'food',
            'date': date.today(),
        }
        defaults.update(kwargs)
        return Expense.objects.create(**defaults)

    def _create_income(self, user, **kwargs):
        defaults = {
            'user': user,
            'title': 'Salary',
            'amount': Decimal('5000.00'),
            'date': date.today(),
        }
        defaults.update(kwargs)
        return Income.objects.create(**defaults)


# ===========================================================================
# 1. User & Role Management
# ===========================================================================

class UserProfileTests(BaseTestCase):
    """Test that UserProfile is auto-created and roles work correctly."""

    def test_auto_profile_creation(self):
        """New users automatically get a viewer profile."""
        new = User.objects.create_user('newguy', password='testpass123')
        profile = UserProfile.objects.get(user=new)
        self.assertEqual(profile.role, 'viewer')
        self.assertTrue(profile.is_active)

    def test_role_assignment(self):
        """Roles can be changed and persisted."""
        profile = UserProfile.objects.get(user=self.viewer)
        profile.role = 'analyst'
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.role, 'analyst')

    def test_profile_str(self):
        """Profile __str__ returns expected format."""
        profile = UserProfile.objects.get(user=self.admin_user)
        self.assertIn('admin', str(profile))


# ===========================================================================
# 2. Authentication
# ===========================================================================

class AuthTests(BaseTestCase):

    def test_login_success(self):
        resp = self.client.post('/login/', {'username': 'viewer', 'password': 'testpass123'})
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, '/dashboard/')

    def test_login_bad_credentials(self):
        resp = self.client.post('/login/', {'username': 'viewer', 'password': 'wrong'})
        self.assertEqual(resp.status_code, 200)  # re-renders login page

    def test_login_inactive_user_blocked(self):
        """Deactivated users cannot log in."""
        UserProfile.objects.filter(user=self.viewer).update(is_active=False)
        resp = self.client.post('/login/', {'username': 'viewer', 'password': 'testpass123'})
        self.assertEqual(resp.status_code, 200)  # stays on login

    def test_unauthenticated_redirect(self):
        resp = self.client.get('/dashboard/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_register_and_login(self):
        resp = self.client.post('/register/', {
            'username': 'freshuser',
            'password1': 'strongpass99',
            'password2': 'strongpass99',
        })
        self.assertRedirects(resp, '/login/')
        # New user should have viewer role
        u = User.objects.get(username='freshuser')
        self.assertEqual(u.userprofile.role, 'viewer')

    def test_register_duplicate_username(self):
        resp = self.client.post('/register/', {
            'username': 'viewer',
            'password1': 'strongpass99',
            'password2': 'strongpass99',
        })
        self.assertEqual(resp.status_code, 200)  # re-renders register

    def test_register_short_password(self):
        resp = self.client.post('/register/', {
            'username': 'newuser2',
            'password1': 'short',
            'password2': 'short',
        })
        self.assertEqual(resp.status_code, 200)

    def test_register_mismatched_passwords(self):
        resp = self.client.post('/register/', {
            'username': 'newuser3',
            'password1': 'strongpass99',
            'password2': 'differentpass',
        })
        self.assertEqual(resp.status_code, 200)

    def test_logout(self):
        self._login(self.viewer)
        resp = self.client.get('/logout/')
        self.assertEqual(resp.status_code, 302)


# ===========================================================================
# 3. Financial Records CRUD — RBAC
# ===========================================================================

class ExpenseCRUDTests(BaseTestCase):

    def test_viewer_can_read_dashboard(self):
        self._login(self.viewer)
        resp = self.client.get('/dashboard/')
        self.assertEqual(resp.status_code, 200)

    def test_viewer_cannot_create_expense(self):
        """Viewer POSTing to dashboard should be blocked."""
        self._login(self.viewer)
        resp = self.client.post('/dashboard/', {
            'title': 'Lunch', 'amount': '50', 'category': 'food',
            'date': '2026-04-01',
        })
        self.assertRedirects(resp, '/dashboard/')
        self.assertEqual(Expense.objects.filter(user=self.viewer).count(), 0)

    def test_admin_can_create_expense(self):
        self._login(self.admin_user)
        resp = self.client.post('/dashboard/', {
            'title': 'Lunch', 'amount': '50', 'category': 'food',
            'date': '2026-04-01',
        })
        self.assertRedirects(resp, '/dashboard/')
        self.assertEqual(Expense.objects.filter(user=self.admin_user).count(), 1)

    def test_admin_can_edit_expense(self):
        self._login(self.admin_user)
        exp = self._create_expense(self.admin_user, title='Old')
        resp = self.client.post(f'/edit/{exp.pk}/', {
            'title': 'Updated', 'amount': '200', 'category': 'rent',
            'date': '2026-04-01', 'description': '',
        })
        self.assertRedirects(resp, '/dashboard/')
        exp.refresh_from_db()
        self.assertEqual(exp.title, 'Updated')

    def test_viewer_cannot_edit_expense(self):
        self._login(self.viewer)
        exp = self._create_expense(self.viewer)
        resp = self.client.post(f'/edit/{exp.pk}/', {
            'title': 'Hacked', 'amount': '999', 'category': 'food',
            'date': '2026-04-01', 'description': '',
        })
        self.assertRedirects(resp, '/dashboard/')
        exp.refresh_from_db()
        self.assertNotEqual(exp.title, 'Hacked')

    def test_admin_can_delete_expense(self):
        self._login(self.admin_user)
        exp = self._create_expense(self.admin_user)
        resp = self.client.post(f'/delete/{exp.pk}/')
        self.assertRedirects(resp, '/dashboard/')
        self.assertEqual(Expense.objects.filter(pk=exp.pk).count(), 0)

    def test_viewer_cannot_delete_expense(self):
        self._login(self.viewer)
        exp = self._create_expense(self.viewer)
        resp = self.client.post(f'/delete/{exp.pk}/')
        self.assertRedirects(resp, '/dashboard/')
        self.assertEqual(Expense.objects.filter(pk=exp.pk).count(), 1)

    def test_cannot_access_other_users_expense(self):
        """Admin can't reach another user's expense via direct URL."""
        self._login(self.admin_user)
        other_exp = self._create_expense(self.viewer)
        resp = self.client.get(
            f'/edit/{other_exp.pk}/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 404)


# ===========================================================================
# 4. Filtering & Search
# ===========================================================================

class FilterTests(BaseTestCase):

    def test_filter_by_category(self):
        self._login(self.viewer)
        self._create_expense(self.viewer, category='food')
        self._create_expense(self.viewer, category='rent')
        resp = self.client.get('/dashboard/?category=food')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['expenses']), 1)

    def test_filter_by_search_query(self):
        self._login(self.viewer)
        self._create_expense(self.viewer, title='Grocery')
        self._create_expense(self.viewer, title='Netflix')
        resp = self.client.get('/dashboard/?q=grocery')
        self.assertEqual(len(resp.context['expenses']), 1)

    def test_filter_by_date(self):
        self._login(self.viewer)
        today = date.today()
        yesterday = today - timedelta(days=1)
        exp1 = self._create_expense(self.viewer)
        exp2 = self._create_expense(self.viewer)
        # Expense.date has auto_now_add=True, so we must update via queryset
        Expense.objects.filter(pk=exp1.pk).update(date=today)
        Expense.objects.filter(pk=exp2.pk).update(date=yesterday)
        resp = self.client.get(f'/dashboard/?date={today.isoformat()}')
        self.assertEqual(len(resp.context['expenses']), 1)


# ===========================================================================
# 5. Dashboard Summary & Analytics
# ===========================================================================

class DashboardSummaryTests(BaseTestCase):

    def test_dashboard_totals(self):
        self._login(self.viewer)
        self._create_expense(self.viewer, amount=Decimal('100'))
        self._create_expense(self.viewer, amount=Decimal('200'))
        self._create_income(self.viewer, amount=Decimal('5000'))
        resp = self.client.get('/dashboard/')
        self.assertEqual(resp.context['total_amount'], Decimal('300'))
        self.assertEqual(resp.context['total_income'], Decimal('5000'))

    def test_overview_category_breakdown(self):
        self._login(self.viewer)
        self._create_expense(self.viewer, category='food', amount=Decimal('300'))
        self._create_expense(self.viewer, category='rent', amount=Decimal('700'))
        resp = self.client.get('/overview/')
        self.assertEqual(resp.status_code, 200)
        self.assertAlmostEqual(resp.context['total_amount'], 1000.0)


class AIInsightsTests(BaseTestCase):

    def test_analyst_can_access_insights(self):
        self._login(self.analyst)
        self._create_expense(self.analyst, amount=Decimal('500'))
        resp = self.client.get('/ai-insights/')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn('suggestions', data)
        self.assertIn('top_categories', data)

    def test_viewer_cannot_access_insights(self):
        self._login(self.viewer)
        resp = self.client.get('/ai-insights/')
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_access_insights(self):
        self._login(self.admin_user)
        resp = self.client.get('/ai-insights/')
        self.assertEqual(resp.status_code, 200)

    def test_budget_warning_returned(self):
        self._login(self.analyst)
        Budget.objects.create(user=self.analyst, amount=Decimal('100'))
        self._create_expense(self.analyst, amount=Decimal('200'))
        resp = self.client.get('/ai-insights/')
        data = json.loads(resp.content)
        self.assertIsNotNone(data['budget_warning'])
        self.assertTrue(data['budget_warning']['is_over'])


# ===========================================================================
# 6. User Management API (admin only)
# ===========================================================================

class UserManagementAPITests(BaseTestCase):

    def test_admin_can_list_users(self):
        self._login(self.admin_user)
        resp = self.client.get('/api/users/')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertGreaterEqual(data['count'], 3)

    def test_viewer_cannot_list_users(self):
        self._login(self.viewer)
        resp = self.client.get('/api/users/')
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_create_user(self):
        self._login(self.admin_user)
        resp = self.client.post(
            '/api/users/create/',
            data=json.dumps({
                'username': 'newanalyst',
                'password': 'strongpass99',
                'role': 'analyst',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 201)
        new_user = User.objects.get(username='newanalyst')
        self.assertEqual(new_user.userprofile.role, 'analyst')

    def test_admin_can_update_role(self):
        self._login(self.admin_user)
        resp = self.client.patch(
            f'/api/users/{self.viewer.pk}/',
            data=json.dumps({'role': 'analyst'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.viewer.userprofile.refresh_from_db()
        self.assertEqual(self.viewer.userprofile.role, 'analyst')

    def test_admin_can_deactivate_user(self):
        self._login(self.admin_user)
        resp = self.client.delete(f'/api/users/{self.viewer.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.viewer.userprofile.refresh_from_db()
        self.assertFalse(self.viewer.userprofile.is_active)

    def test_admin_cannot_deactivate_self(self):
        self._login(self.admin_user)
        resp = self.client.delete(f'/api/users/{self.admin_user.pk}/')
        self.assertEqual(resp.status_code, 400)

    def test_my_profile_available_to_all_roles(self):
        for user in (self.viewer, self.analyst, self.admin_user):
            self._login(user)
            resp = self.client.get('/api/users/me/')
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.content)
            self.assertEqual(data['username'], user.username)

    def test_filter_users_by_role(self):
        self._login(self.admin_user)
        resp = self.client.get('/api/users/?role=viewer')
        data = json.loads(resp.content)
        for u in data['results']:
            self.assertEqual(u['role'], 'viewer')

    def test_create_user_with_short_password_fails(self):
        self._login(self.admin_user)
        resp = self.client.post(
            '/api/users/create/',
            data=json.dumps({
                'username': 'weakuser',
                'password': 'short',
                'role': 'viewer',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_user_duplicate_username_fails(self):
        self._login(self.admin_user)
        resp = self.client.post(
            '/api/users/create/',
            data=json.dumps({
                'username': 'viewer',
                'password': 'strongpass99',
                'role': 'viewer',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)


# ===========================================================================
# 7. Validation & Edge Cases
# ===========================================================================

class ValidationTests(BaseTestCase):

    def test_expense_api_rejects_negative_amount(self):
        """DRF serializer should reject amount <= 0."""
        self._login(self.admin_user)
        resp = self.client.post(
            '/add/',
            data=json.dumps({
                'title': 'Bad', 'amount': '-10',
                'category': 'food', 'date': '2026-04-01',
                'user': self.admin_user.pk,
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_expense_api_rejects_zero_amount(self):
        self._login(self.admin_user)
        resp = self.client.post(
            '/add/',
            data=json.dumps({
                'title': 'Zero', 'amount': '0',
                'category': 'food', 'date': '2026-04-01',
                'user': self.admin_user.pk,
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_budget_model_properties(self):
        self._login(self.admin_user)
        budget = Budget.objects.create(user=self.admin_user, amount=Decimal('1000'))
        self._create_expense(self.admin_user, amount=Decimal('300'))
        self._create_expense(self.admin_user, amount=Decimal('200'))
        self.assertEqual(budget.remaining_amount, Decimal('500'))
        self.assertEqual(budget.spent_percentage, 50.0)

    def test_budget_zero_amount_no_division_error(self):
        budget = Budget.objects.create(user=self.viewer, amount=Decimal('0'))
        self.assertEqual(budget.spent_percentage, 0)

    def test_empty_dashboard_stats(self):
        """Dashboard should work with no data at all."""
        self._login(self.viewer)
        resp = self.client.get('/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['total_amount'], 0)
        self.assertEqual(resp.context['total_income'], 0)
