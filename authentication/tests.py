from django.contrib.admin.sites import AdminSite
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .admin import CustomUserAdmin
from .models import User


class UserAdminPasswordTests(TestCase):
    """
    The admin must never write an unhashed value to User.password.

    CustomUserAdmin previously extended only ModelAdmin, so `password` rendered as an
    ordinary editable CharField and its submitted value was saved verbatim. Any admin
    edit to a user (or a browser autofilling the field) silently replaced the hash with
    plain text and locked the account out.
    """

    def setUp(self):
        self.password = "correct-horse-battery-staple"
        self.user = User.objects.create_user(email_or_cell="graciela@example.com", password=self.password)
        self.superuser = User.objects.create_superuser(email_or_cell="admin@example.com", password="admin-password-123")
        self.admin = CustomUserAdmin(User, AdminSite())

    def test_password_field_is_not_editable_as_plain_text(self):
        """The change form must expose the hash read-only, not as a writable CharField."""
        form_class = self.admin.get_form(self._request_for(self.superuser), obj=self.user)
        password_field = form_class.base_fields["password"]

        # ReadOnlyPasswordHashField renders the hash and discards any submitted value.
        self.assertEqual(password_field.__class__.__name__, "ReadOnlyPasswordHashField")

    def test_saving_user_via_admin_form_preserves_password(self):
        """Editing an unrelated field through the admin form must not damage the hash."""
        request = self._request_for(self.superuser)
        form_class = self.admin.get_form(request, obj=self.user)

        data = {
            "email_or_cell": self.user.email_or_cell,
            "password": self.user.password,  # what the rendered form would submit back
            "first_name": "Graciela",
            "is_active": "on",
            "date_joined_0": "2026-01-01",
            "date_joined_1": "00:00:00",
        }
        form = form_class(data, instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Graciela")
        self.assertTrue(
            self.user.check_password(self.password),
            "admin save destroyed the password hash",
        )

    def test_admin_password_change_form_hashes_new_password(self):
        """The dedicated change-password view stores a hash, never the raw input."""
        new_password = "a-brand-new-password-456"
        form = AdminPasswordChangeForm(
            self.user,
            {"password1": new_password, "password2": new_password},
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.user.refresh_from_db()
        self.assertNotEqual(self.user.password, new_password)
        self.assertTrue(self.user.check_password(new_password))

    def test_add_form_hashes_password(self):
        """Creating a user through the admin add form must hash the password."""
        request = self._request_for(self.superuser)
        form_class = self.admin.get_form(request, obj=None)
        raw_password = "freshly-created-pw-789"

        form = form_class(
            {
                "email_or_cell": "newstaff@example.com",
                "password1": raw_password,
                "password2": raw_password,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        created = form.save()

        self.assertNotEqual(created.password, raw_password)
        self.assertTrue(created.check_password(raw_password))

    def test_search_uses_username_field(self):
        """
        Admin search must cover email_or_cell. The nullable `email` field is empty for
        most screener-created users, so searching it alone returns nothing.
        """
        self.assertIn("email_or_cell", self.admin.search_fields)

    def test_fieldsets_cover_every_editable_field(self):
        """
        Declaring explicit fieldsets replaces Django's auto-generated field list, so a
        field added to the model is silently absent from the admin until it is listed
        here. external_id (the HubSpot contact ID) was dropped this way once already.
        """
        declared = set(flatten_fieldsets(self.admin.fieldsets))
        editable = {f.name for f in User._meta.get_fields() if getattr(f, "editable", False) and not f.auto_created}

        self.assertEqual(
            editable - declared,
            set(),
            "editable User fields missing from CustomUserAdmin.fieldsets",
        )

    def _request_for(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return request


# Rendering the admin templates resolves unfold's static assets, which requires a
# collectstatic manifest that is not built in the test environment.
@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class UserAdminChangePasswordViewTests(TestCase):
    """End-to-end check through the real admin URLs."""

    def setUp(self):
        self.password = "staff-password-123"
        self.superuser = User.objects.create_superuser(email_or_cell="admin@example.com", password=self.password)
        self.target = User.objects.create_user(email_or_cell="target@example.com", password="target-password-123")
        self.client.force_login(self.superuser)

    def test_change_view_post_preserves_password(self):
        url = reverse("admin:authentication_user_change", args=[self.target.pk])
        original_hash = self.target.password

        response = self.client.post(
            url,
            {
                "email_or_cell": self.target.email_or_cell,
                "password": original_hash,
                "first_name": "Updated",
                "is_active": "on",
                "date_joined_0": "2026-01-01",
                "date_joined_1": "00:00:00",
                "_continue": "Save and continue editing",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.target.refresh_from_db()
        # A form-error re-render also returns 200, so assert the edit actually persisted.
        # Otherwise this test could silently rot into a no-op that proves nothing.
        self.assertEqual(self.target.first_name, "Updated")
        self.assertEqual(self.target.password, original_hash)
        self.assertTrue(self.target.check_password("target-password-123"))
