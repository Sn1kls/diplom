from typing import Optional

import phonenumbers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from ninja import Field, ModelSchema, Schema
from phonenumbers import NumberParseException
from pydantic import ConfigDict, EmailStr, field_validator, model_validator

from apps.modules.models import UserLessonProgress
from apps.users.models import (
    AgeGroupChoice,
    ChatInvitation,
    ChildrenChoice,
    FamilyStatusChoice,
    GenderChoice,
    InterestTypeChoice,
    User,
    UserGroup,
)


class CurrentLessonSchema(Schema):
    id: int
    name: str
    order: int


class CurrentModuleSchema(Schema):
    id: int
    name: str
    order: int


class UserProgressSchema(Schema):
    current_score: float
    total_score: float
    current_module: CurrentModuleSchema | None = None
    current_lesson: CurrentLessonSchema | None = None


class UserLessonProgressResponseSchema(ModelSchema):
    lesson_id: int = Field(..., alias="lesson_fk_id")

    class Meta:
        model = UserLessonProgress
        fields = ["is_completed"]


class ChatInvitationSchema(ModelSchema):
    class Meta:
        model = ChatInvitation
        fields = [
            "chat_title",
            "invite_link",
        ]


class UserChatsSchema(Schema):
    personal_chat: ChatInvitationSchema | None = None
    general_chat: ChatInvitationSchema | None = None


class UserRegisterSchema(Schema):
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=150)
    last_name: str = Field(..., min_length=1, max_length=150)
    phone: str = Field(..., min_length=10, max_length=20, examples=["+380505551118"])
    gender: Optional[GenderChoice] = Field(None)
    age_group: AgeGroupChoice = Field(...)
    country: str = Field(..., min_length=2, max_length=100)
    city: str = Field(..., min_length=1, max_length=150)
    children: Optional[ChildrenChoice] = Field(None)
    family_status: Optional[FamilyStatusChoice] = Field(None)
    interests: Optional[list[InterestTypeChoice]] = Field(None)
    interests_other: Optional[str] = Field(None, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value):
        """Validate password using Django's built-in validators"""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise ValueError(", ".join(e.messages))
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone_number(cls, value):
        """
        Validate phone number.
        Tries to parse as international first.
        If missing country code, assumes SWEDEN (+46).
        """
        try:
            phone_number = phonenumbers.parse(value, "SE")
            if not phonenumbers.is_valid_number(phone_number):
                raise ValueError(_("Invalid phone number"))

            return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

        except NumberParseException:
            raise ValueError(_("Invalid phone number format"))


class ActivateUserSchema(Schema):
    uid: str
    token: str


class UserGroupSchema(ModelSchema):
    class Meta:
        model = UserGroup
        fields = [
            "uuid",
            "label",
            "course_started_at",
            "registration_started_at",
            "registration_finished_at",
            "is_active",
        ]


class UserResponseSchema(ModelSchema):
    groups: list[UserGroupSchema] = Field(validation_alias="user_groups")

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "is_active",
            "date_joined",
            "gender",
            "age_group",
            "country",
            "city",
            "children",
            "family_status",
            "interests",
            "interests_other",
            "has_approved_requirements",
        ]

    @field_validator("phone", mode="before", check_fields=False)
    @classmethod
    def serialize_phone(cls, value):
        return str(value)


class UserLoginSchema(Schema):
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=1)


class ForgotPasswordSchema(Schema):
    email: EmailStr = Field(...)


class ResetPasswordSchema(Schema):
    uid: str
    token: str
    new_password: str = Field(..., min_length=8)
    new_password_confirm: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise ValueError(", ".join(e.messages))
        return value

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.new_password != self.new_password_confirm:
            raise ValueError(_("Passwords do not match"))
        return self


class UserUpdateSchema(Schema):
    model_config = ConfigDict(extra="forbid")

    old_password: Optional[str] = Field(None, min_length=1)
    new_password: Optional[str] = Field(None, min_length=8)
    new_password_confirm: Optional[str] = Field(None, min_length=8)
    first_name: Optional[str] = Field(None, min_length=1, max_length=150)
    last_name: Optional[str] = Field(None, min_length=1, max_length=150)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    gender: Optional[str] = Field(None)
    age_group: Optional[str] = Field(None)
    country: Optional[str] = Field(None, min_length=2, max_length=100)
    city: Optional[str] = Field(None, min_length=1, max_length=150)
    children: Optional[str] = Field(None)
    family_status: Optional[str] = Field(None)
    interests: Optional[list[str]] = Field(None)
    has_approved_requirements: Optional[bool] = Field(False)
    interests_other: Optional[str] = Field(None, max_length=255)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, value):
        return UserRegisterSchema.validate_password_strength(value)

    @model_validator(mode="after")
    @classmethod
    def check_passwords_match(cls, values):
        old = values.old_password
        new = values.new_password
        conf = values.new_password_confirm

        if any([old, new, conf]):
            if not all([old, new, conf]):
                raise ValueError(_("Provide old password, new password and confirmation"))
            if new != conf:
                raise ValueError(_("New password and confirmation do not match"))
        return values

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        return UserRegisterSchema.validate_phone_number(value)
