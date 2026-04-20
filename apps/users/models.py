import uuid
from datetime import datetime, timedelta

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField


class GenderChoice(models.TextChoices):
    FEMALE = "female", _("Female")
    MALE = "male", _("Male")
    NON_BINARY = "non_binary", _("Non-binary / Other")
    PREFER_NOT_TO_SAY = "prefer_not_to_say", _("Prefer not to say")


class AgeGroupChoice(models.TextChoices):
    UNDER_24 = "under_24", _("Under 24")
    BETWEEN_25_44 = "25_44", _("25-44")
    OVER_45 = "45_plus", _("45+")


CHAT_INVITATION_GENERAL_AUDIENCE = "general"
CHAT_INVITATION_AUDIENCE_CHOICES = (
    (CHAT_INVITATION_GENERAL_AUDIENCE, _("General")),
    *AgeGroupChoice.choices,
)


class ChildrenChoice(models.TextChoices):
    YES_UNDER_5 = "yes_under_5", _("Yes, under 5 years")
    YES_6_18 = "yes_6_18", _("Yes, 6-18 years")
    YES_18_PLUS = "yes_18_plus", _("Yes, 18+")
    NO = "no", _("No")
    PREFER_NOT_TO_SAY = "prefer_not_to_say", _("Prefer not to say")


class FamilyStatusChoice(models.TextChoices):
    IN_RELATIONSHIP = "in_relationship_or_married", _("In a relationship / Married")
    NOT_IN_RELATIONSHIP = "not_in_relationship", _("Not in a relationship")
    DIVORCING = "divorcing_or_divorced", _("Divorcing / Divorced")
    PREFER_NOT_TO_SAY = "prefer_not_to_say", _("Prefer not to say")


class InterestTypeChoice(models.TextChoices):
    MENTAL_HEALTH = "mental_health", _("Mental health and self-care")
    RELATIONSHIPS = "relationships", _("Relationships and family")
    PARENTING = "parenting", _("Parenting")
    SELF_DEVELOPMENT = "self_development", _("Self-development and learning")
    CAREER = "career", _("Work / Career")
    CREATIVITY = "creativity", _("Creativity")
    PHYSICAL_HEALTH = "physical_health", _("Physical health and movement")
    SPIRITUALITY = "spirituality", _("Spirituality / Meanings")
    HOBBIES = "hobbies", _("Rest and hobbies")
    PREFER_NOT_TO_SAY = "prefer_not_to_say", _("Prefer not to say")


class UserManager(BaseUserManager):
    """
    A custom user manager to deal with emails as unique identifiers for auth
    instead of usernames. The default that's used is "UserManager"
    """

    def create_user(self, email, password, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, username=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Creates and saves a superuser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model with email as the unique identifier
    The default that's used is "User"

    Attributes:
        first_name (str): The first name of the user.
        last_name (str): The last name of the user.
        email (str): The email of the user.
        phone (str): The phone number of the user.
    """

    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)
    email = models.EmailField(_("email address"), unique=True)
    phone = PhoneNumberField(_("phone number"), unique=True)
    score = models.PositiveIntegerField(_("score"), default=0)

    gender = models.CharField(
        _("gender"),
        max_length=30,
        choices=GenderChoice.choices,
        blank=True,
        null=True,
    )
    age_group = models.CharField(
        _("age group"),
        max_length=20,
        choices=AgeGroupChoice.choices,
        blank=False,
        null=False,
        default=AgeGroupChoice.UNDER_24,
    )
    country = models.CharField(
        _("country"),
        max_length=100,
        blank=False,
        null=False,
        default="",
    )
    city = models.CharField(
        _("city"),
        max_length=150,
        blank=False,
        null=False,
        default="",
    )
    children = models.CharField(
        _("children"),
        max_length=30,
        choices=ChildrenChoice.choices,
        blank=True,
        null=True,
    )
    family_status = models.CharField(
        _("family status"),
        max_length=40,
        choices=FamilyStatusChoice.choices,
        blank=True,
        null=True,
    )
    interests = ArrayField(
        models.CharField(max_length=50, choices=InterestTypeChoice.choices),
        blank=True,
        default=list,
        verbose_name=_("interests"),
    )
    interests_other = models.CharField(
        _("other interests"),
        max_length=255,
        blank=True,
    )
    has_approved_requirements = models.BooleanField(
        _("has approved requirements"),
        default=False,
    )
    date_joined = models.DateTimeField(_("date joined"), auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    _PASSWORD_HASHER_NAME = "pbkdf2"

    objects = UserManager()

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        """
        Save the user with a hashed password.
        """
        if not self.username:
            self.username = self.email
        if self.password and not self.password.startswith(self._PASSWORD_HASHER_NAME):
            self.set_password(self.password)
        super().save(*args, **kwargs)


class UserGroup(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_("UID"),
    )
    users = models.ManyToManyField(
        User,
        related_name="user_groups",
        blank=True,
        verbose_name=_("users"),
        through="GroupMembership",
        help_text=_("Select active users for this group."),
    )
    label = models.CharField(
        _("label"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("For internal use only. This label is not displayed on the user page"),
    )
    is_active = models.BooleanField(_("is active"), default=True)
    registration_started_at = models.DateTimeField(_("registration started at"))
    registration_finished_at = models.DateTimeField(_("registration finished at"), blank=True, null=True)
    course_started_at = models.DateTimeField(_("course started at"))
    opening_interval_days = models.PositiveIntegerField(
        _("Opening interval in days"),
        help_text=_("Value for the interval (in days) for opening modules for the current group"),
        default=7,
    )

    class Meta:
        verbose_name = _("User Group")
        verbose_name_plural = _("User Groups")
        ordering = ["registration_started_at"]

    def __str__(self):
        return self.label or str(self.uuid)

    def clean(self):
        super().clean()

        if self.registration_finished_at and self.registration_started_at:
            if self.registration_finished_at <= self.registration_started_at:
                raise ValidationError(_("Registration finish date must be after start date."))

        if not self.is_active:
            has_other_active = UserGroup.objects.filter(is_active=True).exclude(pk=self.pk).exists()
            if not has_other_active:
                raise ValidationError(
                    _("At least one user group should be active."),
                )

        else:
            if not self.registration_finished_at:
                raise ValidationError(_("Active group must have a registration finished date set."))

            if self.registration_finished_at < timezone.now():
                raise ValidationError(_("Cannot mark group as active because registration time has already passed."))

    def get_module_unlock_date(self, module_order: int) -> datetime:
        if module_order <= 1:
            return self.course_started_at

        days_delay = (module_order - 1) * self.opening_interval_days
        return self.course_started_at + timedelta(days=days_delay)

    def is_module_available(self, module_order: int) -> bool:
        unlock_date = self.get_module_unlock_date(module_order)
        return timezone.now() >= unlock_date


class GroupMembership(models.Model):
    group = models.ForeignKey(
        UserGroup,
        on_delete=models.CASCADE,
        related_name="membership",
        verbose_name=_("group"),
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="group_membership",
        verbose_name=_("user"),
    )
    date_joined = models.DateTimeField(_("date joined"), auto_now_add=True)

    class Meta:
        verbose_name = _("Group Membership")
        verbose_name_plural = _("Group Memberships")
        ordering = ["-date_joined"]

    def __str__(self):
        return self.user.email


class ChatInvitation(models.Model):
    group = models.ForeignKey(
        UserGroup,
        on_delete=models.CASCADE,
        related_name="chat_invitations",
        verbose_name=_("group"),
        blank=True,
        null=True,
    )
    audience = models.CharField(
        _("audience"),
        max_length=20,
        choices=CHAT_INVITATION_AUDIENCE_CHOICES,
        null=True,
    )
    chat_title = models.CharField(_("chat title"), max_length=255)
    invite_link = models.URLField(_("invite link"), max_length=500)
    custom_invite_message = models.CharField(_("custom invite message"), max_length=255)
    is_active = models.BooleanField(_("is active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("Chat Invitation")
        verbose_name_plural = _("Chat Invitations")
        ordering = ["audience", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'audience'],
                name='unique_audience_per_group'
            ),
        ]

    def clean(self):
        super().clean()
        if self.audience in AgeGroupChoice.values and not self.group:
            raise ValidationError({
                "group": _("A group must be selected for age-specific chat invitations.")
            })
        
        if self.audience == CHAT_INVITATION_GENERAL_AUDIENCE and not self.group:
            existing_general_chats = ChatInvitation.objects.filter(
                audience=CHAT_INVITATION_GENERAL_AUDIENCE,
                group__isnull=True
            ).exclude(pk=self.pk)
            
            if existing_general_chats.exists():
                raise ValidationError({
                    "audience": _("A general chat invitation without a specific group already exists.")
                })

    def __str__(self):
        return self.chat_title


class UserDeviceLog(models.Model):
    user_fk = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="user_log",
        verbose_name=_("user"),
    )
    ip_address = models.GenericIPAddressField(_("IP address"), blank=True, null=True)
    os_name = models.CharField(_("OS name"), max_length=255, blank=True, null=True)
    browser = models.CharField(_("browser"), max_length=255, blank=True, null=True)
    device_type = models.CharField(_("device type"), max_length=255, blank=True, null=True)
    raw_user_agent = models.TextField(_("raw user agent"), blank=True, null=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("User Device Log")
        verbose_name_plural = _("User Device Logs")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_fk.email if self.user_fk else 'Anonymous'} - {self.ip_address} - {self.created_at}"
