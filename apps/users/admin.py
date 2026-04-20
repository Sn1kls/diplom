import datetime

from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from unfold.forms import AdminPasswordChangeForm, UserChangeForm

from apps.users.forms import CustomUserCreationForm
from apps.users.models import ChatInvitation, GroupMembership, User, UserDeviceLog, UserGroup
from apps.users.utils import send_activation_email, send_chat_invitation_email, write_to_csv

admin.site.unregister(Group)


@admin.action(description=_("Export to CSV"))
def export_to_csv(self, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{datetime.date.today()}_users.csv"'
    filed_names = [
        "email",
        "phone",
        "first_name",
        "last_name",
        "gender",
        "age_group",
        "country",
        "city",
        "children",
        "family_status",
    ]
    write_to_csv(source=response, queryset=queryset, fields=filed_names)
    return response


@admin.register(User)
class UserAdmin(UserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = CustomUserCreationForm
    change_password_form = AdminPasswordChangeForm
    actions = [export_to_csv]
    list_display = [
        "email",
        "phone",
        "first_name",
        "last_name",
        "has_approved_requirements",
        "is_active",
        "is_staff",
        "is_superuser",
        "gender",
        "age_group",
        "children",
        "family_status",
        "country",
        "city",
        "interests",
        "interests_other",
        "get_user_group_link",
    ]
    list_filter = [
        "is_active",
        "has_approved_requirements",
        "is_staff",
        "is_superuser",
        "user_groups",
        "gender",
        "age_group",
        "children",
        "family_status",
        "country",
        "city",
    ]
    search_fields = ["email", "phone", "first_name", "last_name", "user_groups__label"]
    readonly_fields = ["date_joined", "last_login"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "phone", "password1", "password2"),
            },
        ),
    )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "phone",
                    "first_name",
                    "last_name",
                    "gender",
                    "age_group",
                    ("country", "city"),
                    ("children", "family_status"),
                    ("interests", "interests_other"),
                )
            },
        ),
        (
            _("Important dates"),
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "has_approved_requirements",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    actions_submit_line = ["send_activation_email", "send_chat_invitation_email"]

    @action(
        description=_("Send activation email"),
        permissions=["user_need_activate"],
    )
    def send_activation_email(self, request: HttpRequest, obj: User):
        backend_url = request.build_absolute_uri("/")
        send_activation_email(obj, backend_url)
        self.message_user(request, _("Activation email sent"), level=messages.SUCCESS)

    @action(
        description=_("Send chat invitation email"),
        permissions=["user_is_active"],
    )
    def send_chat_invitation_email(self, request: HttpRequest, obj: User):
        send_chat_invitation_email(obj)
        self.message_user(request, _("Chat invitation email sent"), level=messages.SUCCESS)

    def has_user_need_activate_permission(self, request: HttpRequest, object_id: int):
        if not object_id:
            # I don't know what it's mean but unfold is a real trash package
            return True

        user = User.objects.get(pk=object_id)
        return not user.is_active

    def has_user_is_active_permission(self, request: HttpRequest, object_id: int):
        if not object_id:
            return True

        user = User.objects.get(pk=object_id)
        return user.is_active

    @admin.display(description=_("User Group"), ordering="user_groups__label")
    def get_user_group_link(self, obj):
        group = obj.user_groups.first()

        if not group:
            return "---"

        url = reverse("admin:users_usergroup_change", args=[group.pk])
        return format_html("<a href='{}' style='font-weight: bold;'>{}</a>", url, group.label)


@admin.register(Group)
class GroupAdmin(GroupAdmin, ModelAdmin):
    pass


class GroupMembershipInline(TabularInline):
    model = GroupMembership
    extra = 1
    autocomplete_fields = ["user"]
    readonly_fields = ["date_joined"]


@admin.register(UserGroup)
class UserGroupAdmin(ModelAdmin):
    list_display = [
        "uuid",
        "label",
        "registration_started_at",
        "registration_finished_at",
        "is_active",
        "count_users_in_group",
    ]
    list_display_links = ["uuid", "label"]
    list_filter = ["registration_started_at", "registration_finished_at"]
    search_fields = ["label", "uuid"]
    readonly_fields = ["uuid"]
    inlines = [GroupMembershipInline]

    @admin.display(description=_("Number of users in group"))
    def count_users_in_group(self, obj):
        return obj.users.count()


@admin.register(ChatInvitation)
class ChatInvitationAdmin(ModelAdmin):
    list_display = ["chat_title", "group", "audience", "invite_link", "is_active", "updated_at"]
    list_filter = ["group", "audience", "is_active"]
    search_fields = ["chat_title", "group__label", "custom_invite_message", "invite_link"]


@admin.register(UserDeviceLog)
class UserDeviceLogAdmin(ModelAdmin):
    list_display = [
        "user_fk",
        "ip_address",
        "os_name",
        "browser",
        "device_type",
        "raw_user_agent",
        "created_at",
    ]
    list_filter = ["user_fk", "ip_address", "os_name", "browser", "device_type"]
    search_fields = ["user_fk__email", "ip_address"]

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
