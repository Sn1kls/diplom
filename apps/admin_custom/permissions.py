from ninja.security import SessionAuth


class StaffAuth(SessionAuth):
    def authenticate(self, request, token=None):
        if request.user.is_active and request.user.is_staff:
            return request.user
        return None
