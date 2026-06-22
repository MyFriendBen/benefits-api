import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from typing import Optional


class UserManager(BaseUserManager):
    def create_user(self, email_or_cell, password: Optional[str] = None):
        """
        Creates and saves a User with the given email or cell and password.
        """
        if not email_or_cell:
            raise ValueError("Users must have an email address or cell phone number")

        user = self.model(email_or_cell=email_or_cell, password=password, explicit_tcpa_consent=False)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email_or_cell, password: Optional[str] = None):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        user = self.create_user(email_or_cell=email_or_cell, password=password)
        user.is_admin = True
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


# Users are created by the screener when someone signs up to provide feedback
# or be notified of future benefits that are available to them. The unique id
# can be either a cell phone number or email address.
class User(AbstractUser):
    username = None
    email_or_cell = models.CharField(max_length=320, unique=True)
    cell = PhoneNumberField(unique=True, blank=True, null=True)
    email = models.EmailField(_("email address"), unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=320, blank=True, null=True)
    last_name = models.CharField(max_length=320, blank=True, null=True)
    language_code = models.CharField(max_length=12, blank=True, null=True)
    tcpa_consent = models.BooleanField(default=False, blank=True, null=True)
    explicit_tcpa_consent = models.BooleanField(blank=True, null=True)
    send_offers = models.BooleanField(default=False)
    send_updates = models.BooleanField(default=False)
    white_labels = models.ManyToManyField("screener.WhiteLabel", related_name="admins", blank=True)
    external_id = models.CharField(max_length=320, blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = "email_or_cell"
    REQUIRED_FIELDS = []

    def anonomize(self, external_id: str) -> None:
        random_id = str(uuid.uuid4()).replace("-", "")
        self.external_id = external_id
        self.email_or_cell = f"{external_id}+{random_id}@myfriendben.org"
        self.first_name = None
        self.last_name = None
        self.cell = None
        self.email = None
        self.save()

    def save(self, **kwargs) -> None:
        self.cell = self.cell or None
        super().save(**kwargs)

    def __str__(self) -> str:
        return self.email_or_cell
