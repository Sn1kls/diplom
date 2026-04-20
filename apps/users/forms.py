from unfold.forms import UserCreationForm

from apps.users.models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = User
        fields = ("email", "phone")
