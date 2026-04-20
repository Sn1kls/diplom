import json
from unittest.mock import patch

from django.contrib import messages
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.homeworks.models import Homework, UserSubmission
from apps.modules.models import ContentType, Lesson, Module, UserLessonProgress
from apps.quizzes.models import Question, QuestionTypes, Quiz, QuizAttempt
from apps.users.admin import UserAdmin as CustomUserAdmin
from apps.users.models import (
    CHAT_INVITATION_GENERAL_AUDIENCE,
    AgeGroupChoice,
    ChatInvitation,
    ChildrenChoice,
    FamilyStatusChoice,
    GenderChoice,
    GroupMembership,
    InterestTypeChoice,
    UserGroup,
)
from apps.users.services import UserProgressService
from apps.users.utils import (
    build_activation_url,
    generate_user_token,
    render_activation_email,
    verify_user_token,
)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class UserRegistrationTests(TestCase):
    def setUp(self):
        self.url = "/api/users/register"
        self.payload = {
            "email": "user@example.com",
            "password": "S3cureP@ss123",
            "first_name": "Test",
            "last_name": "User",
            "phone": "+380501234567",
            "age_group": AgeGroupChoice.UNDER_24,
            "country": "Ukraine",
            "city": "Kyiv",
        }

    def test_register_user_success(self):
        with patch("apps.users.utils.send_activation_email") as mock_send_activation_email:
            response = self.client.post(
                self.url,
                data=json.dumps(self.payload),
                content_type="application/json",
            )
            mock_send_activation_email.result = True
            self.assertEqual(response.status_code, 201)

        data = response.json()
        self.assertIn("id", data)
        self.assertIn("email", data)
        self.assertIn("first_name", data)
        self.assertIn("last_name", data)
        self.assertIn("phone", data)
        self.assertIn("is_active", data)
        self.assertIn("date_joined", data)
        self.assertIn("gender", data)
        self.assertIn("age_group", data)
        self.assertIn("country", data)
        self.assertIn("city", data)
        self.assertIn("children", data)
        self.assertIn("family_status", data)
        self.assertIn("interests", data)
        self.assertIn("interests_other", data)

        user = get_user_model().objects.get(email=self.payload["email"])
        self.assertEqual(user.phone, self.payload["phone"])

    def test_register_user_existing_email(self):
        User = get_user_model()
        User.objects.create_user(
            email=self.payload["email"],
            password="AnotherS3cureP@ss123",
            first_name="Existing",
            last_name="User",
            phone="+380991112233",
            country="Ukraine",
            city="Kyiv",
        )

        response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {"error": _("A user with this email address already exists.")},
        )

    def test_register_user_existing_phone(self):
        User = get_user_model()
        User.objects.create_user(
            email="another@example.com",
            password="AnotherS3cureP@ss123",
            first_name="Existing",
            last_name="User",
            phone=self.payload["phone"],
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
        )

        response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {"error": _("A user with this phone number already exists.")},
        )

    def test_register_user_invalid_phone(self):
        payload = self.payload.copy()
        payload["phone"] = "invalid_phone"

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)

    def test_register_user_with_survey_data(self):
        payload = self.payload.copy()
        payload.update(
            {
                "gender": GenderChoice.FEMALE,
                "age_group": AgeGroupChoice.BETWEEN_25_44,
                "country": "Ukraine",
                "city": "Kyiv",
                "children": ChildrenChoice.YES_6_18,
                "family_status": FamilyStatusChoice.IN_RELATIONSHIP,
                "interests": [
                    InterestTypeChoice.MENTAL_HEALTH,
                    InterestTypeChoice.CAREER,
                ],
                "interests_other": "Photography",
            }
        )

        with patch("apps.users.utils.send_activation_email") as mock_send_activation_email:
            response = self.client.post(
                self.url,
                data=json.dumps(payload),
                content_type="application/json",
            )
            mock_send_activation_email.result = True
            self.assertEqual(response.status_code, 201)

        data = response.json()
        self.assertEqual(data["gender"], GenderChoice.FEMALE)
        self.assertEqual(data["age_group"], AgeGroupChoice.BETWEEN_25_44)
        self.assertEqual(data["country"], "Ukraine")
        self.assertEqual(data["city"], "Kyiv")
        self.assertEqual(data["children"], ChildrenChoice.YES_6_18)
        self.assertEqual(data["family_status"], FamilyStatusChoice.IN_RELATIONSHIP)
        self.assertEqual(len(data["interests"]), 2)
        self.assertIn(InterestTypeChoice.MENTAL_HEALTH, data["interests"])
        self.assertIn(InterestTypeChoice.CAREER, data["interests"])
        self.assertEqual(data["interests_other"], "Photography")

        user = get_user_model().objects.get(email=payload["email"])
        self.assertEqual(user.gender, GenderChoice.FEMALE)
        self.assertEqual(
            user.interests,
            [InterestTypeChoice.MENTAL_HEALTH, InterestTypeChoice.CAREER],
        )

    def test_register_user_invalid_gender(self):
        payload = self.payload.copy()
        payload["email"] = "test2@example.com"
        payload["gender"] = "invalid_gender"

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)

    def test_register_user_invalid_age_group(self):
        payload = self.payload.copy()
        payload["email"] = "test3@example.com"
        payload["age_group"] = "invalid_age"

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)

    def test_register_user_invalid_interest(self):
        payload = self.payload.copy()
        payload["email"] = "test4@example.com"
        payload["interests"] = ["invalid_interest"]

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class UserLoginTests(TestCase):
    def setUp(self):
        self.url = "/api/users/login"
        self.password = "S3cureP@ss123"
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password=self.password,
            first_name="Test",
            last_name="User",
            phone="+380501234567",
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
            is_active=True,
        )

    def test_login_success(self):
        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "email": self.user.email,
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)

    def test_login_invalid_credentials(self):
        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "email": self.user.email,
                    "password": "WrongPass123",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": _("Invalid credentials.")})

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "email": self.user.email,
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"error": _("User is not active.")})


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class UserProfileTests(TestCase):
    def setUp(self):
        self.url = "/api/users/me"
        self.password = "S3cureP@ss123"
        self.user = get_user_model().objects.create_user(
            email="me@example.com",
            password=self.password,
            first_name="My",
            last_name="Profile",
            phone="+380991234567",
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
            is_active=True,
        )
        login_resp = self.client.post(
            "/api/users/login",
            data=json.dumps({"email": self.user.email, "password": self.password}),
            content_type="application/json",
        )
        self.token = login_resp.json()["access"]

    def test_get_me_success(self):
        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], self.user.email)
        self.assertEqual(data["first_name"], self.user.first_name)
        self.assertEqual(data["last_name"], self.user.last_name)
        self.assertEqual(data["phone"], self.user.phone)

    def test_get_me_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class UserChatsTests(TestCase):
    def setUp(self):
        self.url = "/api/users/me/chats"
        self.password = "S3cureP@ss123"
        self.user = get_user_model().objects.create_user(
            email="chats@example.com",
            password=self.password,
            first_name="Chats",
            last_name="User",
            phone="+380931234567",
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
            is_active=True,
        )
        login_resp = self.client.post(
            "/api/users/login",
            data=json.dumps({"email": self.user.email, "password": self.password}),
            content_type="application/json",
        )
        self.token = login_resp.json()["access"]

    def test_get_me_chats_returns_personal_and_general(self):
        group = UserGroup.objects.create(
            label="Test Group", 
            is_active=True, 
            registration_started_at=timezone.now(), 
            registration_finished_at=timezone.now() + timezone.timedelta(days=1),
            course_started_at=timezone.now() + timezone.timedelta(days=2)
        )
        GroupMembership.objects.create(user=self.user, group=group)

        ChatInvitation.objects.create(
            audience=AgeGroupChoice.UNDER_24,
            chat_title="Personal Chat",
            invite_link="https://t.me/personal",
            custom_invite_message="Join personal",
            is_active=True,
            group=group,
        )
        ChatInvitation.objects.create(
            audience=CHAT_INVITATION_GENERAL_AUDIENCE,
            chat_title="General Chat",
            invite_link="https://t.me/general",
            custom_invite_message="Join general",
            is_active=True,
            group=group,
        )

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["personal_chat"]["chat_title"], "Personal Chat")
        self.assertEqual(data["general_chat"]["chat_title"], "General Chat")

    def test_get_me_chats_returns_nulls_if_not_found(self):
        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data["personal_chat"])
        self.assertIsNone(data["general_chat"])


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class ActivationTests(TestCase):
    def test_generate_and_verify_token(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="token@example.com",
            password="S3cureP@ss123",
            first_name="Token",
            last_name="User",
            phone="+380501111111",
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
        )

        uidb64, token = generate_user_token(user)
        verified = verify_user_token(uidb64, token)
        self.assertIsNotNone(verified)
        self.assertEqual(verified.pk, user.pk)

    def test_verify_token_invalid_uid(self):
        verified = verify_user_token("invalid_uid", "token")
        self.assertIsNone(verified)

    def test_verify_token_invalid_token(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="invalidtoken@example.com",
            password="password",
            first_name="Invalid",
            last_name="Token",
            phone="+380503333333",
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
        )
        uidb64, _ = generate_user_token(user)
        verified = verify_user_token(uidb64, "invalid_token")
        self.assertIsNone(verified)

    def test_build_activation_url(self):
        url = build_activation_url("http://frontend.com", "uid", "token")
        self.assertIn("http://frontend.com", url)
        self.assertIn("/activate/uid-token", url)

    def test_render_activation_email(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="render@example.com",
            password="password",
            first_name="Render",
            last_name="User",
            phone="+380504444444",
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
        )
        content = render_activation_email(user, "http://activation.url")
        self.assertIn(user.first_name, content)
        self.assertIn("http://activation.url", content)

    def test_activate_user_api_success(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="activate@example.com",
            password="S3cureP@ss123",
            first_name="Activate",
            last_name="User",
            phone="+380502222222",
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
            is_active=False,
        )

        uidb64, token = generate_user_token(user)

        url = "/api/users/activate"
        payload = {
            "uid": uidb64,
            "token": token,
        }

        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_activate_user_api_invalid_token(self):
        url = "/api/users/activate"
        payload = {
            "uid": "invalid",
            "token": "invalid",
        }

        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_activate_user_api_already_active(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="already@example.com",
            password="S3cureP@ss123",
            first_name="Already",
            last_name="Active",
            phone="+380509999999",
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
            is_active=True,
        )

        uidb64, token = generate_user_token(user)
        url = "/api/users/activate"
        payload = {
            "uid": uidb64,
            "token": token,
        }

        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class UserEditProfileTests(TestCase):
    def setUp(self):
        self.url = "/api/users/me"
        self.password = "S3cureP@ss123"
        self.user = get_user_model().objects.create_user(
            email="edit@example.com",
            password=self.password,
            first_name="Edit",
            last_name="User",
            phone="+380998887766",
            country="Ukraine",
            city="Kyiv",
            is_active=True,
        )
        login_resp = self.client.post(
            "/api/users/login",
            data=json.dumps({"email": self.user.email, "password": self.password}),
            content_type="application/json",
        )
        self.token = login_resp.json()["access"]
        self.headers = {
            "HTTP_AUTHORIZATION": f"Bearer {self.token}",
            "CONTENT_TYPE": "application/json",
        }

    def test_edit_profile_fields_success(self):
        payload = {
            "first_name": "UpdatedName",
            "phone": "+380995554433",
            "gender": GenderChoice.MALE,
        }
        response = self.client.patch(
            self.url,
            data=json.dumps(payload),
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["first_name"], "UpdatedName")
        self.assertEqual(data["phone"], "+380995554433")
        self.assertEqual(data["gender"], GenderChoice.MALE)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "UpdatedName")
        self.assertEqual(self.user.phone, "+380995554433")
        self.assertEqual(self.user.gender, GenderChoice.MALE)

    def test_edit_password_success(self):
        new_password = "NewS3cureP@ss123"
        payload = {
            "old_password": self.password,
            "new_password": new_password,
            "new_password_confirm": new_password,
        }
        response = self.client.patch(
            self.url,
            data=json.dumps(payload),
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        login_resp = self.client.post(
            "/api/users/login",
            data=json.dumps({"email": self.user.email, "password": new_password}),
            content_type="application/json",
        )
        self.assertEqual(login_resp.status_code, 200)

    def test_edit_password_mismatch(self):
        payload = {
            "old_password": self.password,
            "new_password": "NewS3cureP@ss123",
            "new_password_confirm": "MismatchPass123",
        }
        response = self.client.patch(
            self.url,
            data=json.dumps(payload),
            **self.headers,
        )

        self.assertEqual(response.status_code, 422)

    def test_edit_password_wrong_old(self):
        payload = {
            "old_password": "WrongPassword",
            "new_password": "NewS3cureP@ss123",
            "new_password_confirm": "NewS3cureP@ss123",
        }
        response = self.client.patch(
            self.url,
            data=json.dumps(payload),
            **self.headers,
        )

        self.assertEqual(response.status_code, 400)

    def test_edit_invalid_phone(self):
        payload = {"phone": "invalid_phone"}
        response = self.client.patch(
            self.url,
            data=json.dumps(payload),
            **self.headers,
        )
        self.assertEqual(response.status_code, 422)

    def test_edit_existing_phone(self):
        get_user_model().objects.create_user(
            email="other@example.com",
            password="password",
            phone="+380991112233",
            country="Ukraine",
            city="Kyiv",
        )

        payload = {"phone": "+380991112233"}
        response = self.client.patch(
            self.url,
            data=json.dumps(payload),
            **self.headers,
        )
        self.assertEqual(response.status_code, 409)

    def test_edit_empty_phone(self):
        payload = {"phone": ""}
        response = self.client.patch(
            self.url,
            data=json.dumps(payload),
            **self.headers,
        )
        self.assertEqual(response.status_code, 422)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class UserProgressTests(TestCase):
    def setUp(self):
        self.url = "/api/users/me/progress"
        self.password = "S3cureP@ss123"
        self.user = get_user_model().objects.create_user(
            email="test_prog@example.com",
            password=self.password,
            first_name="Test",
            last_name="Prog",
            phone="+380998887755",
            country="Ukraine",
            city="Kyiv",
            is_active=True,
        )
        login_resp = self.client.post(
            "/api/users/login",
            data={"email": self.user.email, "password": self.password},
            content_type="application/json",
        )
        self.token = login_resp.json()["access"]
        self.headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

        self.module = Module.objects.create(name="Module 1", order=1)

        self.lesson_text = Lesson.objects.create(
            name="Text Lesson",
            module_fk=self.module,
            content_type=ContentType.TEXT,
            order=1,
        )

        self.lesson_video = Lesson.objects.create(
            name="Video Lesson",
            module_fk=self.module,
            content_type=ContentType.VIDEO,
            order=2,
        )

        self.quiz = Quiz.objects.create(name="Quiz 1")
        self.lesson_quiz = Lesson.objects.create(
            name="Quiz Lesson",
            module_fk=self.module,
            content_type=ContentType.QUIZ,
            quiz_fk=self.quiz,
            order=3,
        )

        self.q1 = Question.objects.create(
            title="Q1",
            quiz_fk=self.quiz,
            question_type=QuestionTypes.SINGLE_CHOICE,
            order=1,
        )
        self.q2 = Question.objects.create(title="Q2", quiz_fk=self.quiz, question_type=QuestionTypes.TEXT, order=2)

    def test_get_progress_initial(self):
        response = self.client.get(self.url, **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["total_score"], 8.0)
        self.assertEqual(data["current_score"], 0.0)

    def test_get_progress_with_completed_lessons(self):
        self.user.score += self.lesson_text.score
        self.user.save()

        response = self.client.get(self.url, **self.headers)
        data = response.json()

        # Current = 2
        self.assertEqual(data["current_score"], 2.0)
        self.assertEqual(data["total_score"], 8.0)

    def test_get_progress_with_completed_quiz(self):
        QuizAttempt.objects.create(
            user_fk=self.user,
            quiz_fk=self.quiz,
            is_completed=True,
            score=3.0,  # Full score
        )
        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson_quiz,
            is_completed=True,
        )

        response = self.client.get(self.url, **self.headers)
        data = response.json()

        self.assertEqual(data["current_score"], 3.0)
        self.assertEqual(data["total_score"], 8.0)

    def test_get_progress_does_not_double_count_quiz_after_recalculate(self):
        lesson_audio = Lesson.objects.create(
            name="Audio Lesson",
            module_fk=self.module,
            content_type=ContentType.AUDIO,
            order=4,
        )

        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson_text,
            is_completed=True,
        )
        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=lesson_audio,
            is_completed=True,
        )
        QuizAttempt.objects.create(
            user_fk=self.user,
            quiz_fk=self.quiz,
            is_completed=True,
            score=6.0,
        )

        UserProgressService.recalculate_user_score(self.user)
        self.user.refresh_from_db(fields=["score"])

        response = self.client.get(self.url, **self.headers)
        data = response.json()

        self.assertEqual(float(self.user.score), 10.0)
        self.assertEqual(data["current_score"], 10.0)

    def test_progress_returns_current_module_and_lesson(self):
        response = self.client.get(self.url, **self.headers)
        data = response.json()

        self.assertIsNotNone(data["current_module"])
        self.assertEqual(data["current_module"]["id"], self.module.id)
        self.assertEqual(data["current_module"]["name"], "Module 1")

        self.assertIsNotNone(data["current_lesson"])
        self.assertEqual(data["current_lesson"]["id"], self.lesson_text.id)
        self.assertEqual(data["current_lesson"]["name"], "Text Lesson")

    def test_progress_advances_after_completing_first_lesson(self):
        from apps.modules.models import UserLessonProgress

        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson_text,
            is_completed=True,
        )

        response = self.client.get(self.url, **self.headers)
        data = response.json()

        self.assertEqual(data["current_lesson"]["id"], self.lesson_video.id)
        self.assertEqual(data["current_lesson"]["name"], "Video Lesson")

    def test_progress_all_completed_returns_null(self):
        from apps.modules.models import UserLessonProgress

        for lesson in [self.lesson_text, self.lesson_video, self.lesson_quiz]:
            UserLessonProgress.objects.create(
                user_fk=self.user,
                lesson_fk=lesson,
                is_completed=True,
            )

        response = self.client.get(self.url, **self.headers)
        data = response.json()

        self.assertIsNone(data["current_module"])
        self.assertIsNone(data["current_lesson"])

    def test_progress_current_lesson_respects_module_order(self):
        module2 = Module.objects.create(name="Module 2", order=2)
        lesson_m2 = Lesson.objects.create(
            name="M2 Lesson 1",
            module_fk=module2,
            content_type=ContentType.TEXT,
            order=1,
        )

        from apps.modules.models import UserLessonProgress

        for lesson in [self.lesson_text, self.lesson_video, self.lesson_quiz]:
            UserLessonProgress.objects.create(
                user_fk=self.user,
                lesson_fk=lesson,
                is_completed=True,
            )

        response = self.client.get(self.url, **self.headers)
        data = response.json()

        self.assertEqual(data["current_module"]["id"], module2.id)
        self.assertEqual(data["current_lesson"]["id"], lesson_m2.id)

    def test_progress_finds_newly_activated_lower_priority_module(self):
        module2 = Module.objects.create(name="Module 2", order=2)
        Lesson.objects.create(
            name="M2 Lesson 1",
            module_fk=module2,
            content_type=ContentType.TEXT,
            order=1,
        )

        for lesson in [self.lesson_text, self.lesson_video, self.lesson_quiz]:
            UserLessonProgress.objects.create(
                user_fk=self.user,
                lesson_fk=lesson,
                is_completed=True,
            )

        retro_module = Module.objects.create(name="Retro Module", is_active=False)
        retro_module.order = 0
        retro_module.save(update_fields=["order"])

        retro_lesson = Lesson.objects.create(
            name="Retro Lesson",
            module_fk=retro_module,
            content_type=ContentType.TEXT,
            is_active=False,
        )
        retro_lesson.order = 1
        retro_lesson.save(update_fields=["order"])

        retro_module.is_active = True
        retro_module.save(update_fields=["is_active"])
        retro_lesson.is_active = True
        retro_lesson.save(update_fields=["is_active"])

        response = self.client.get(self.url, **self.headers)
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["current_module"]["id"], retro_module.id)
        self.assertEqual(data["current_lesson"]["id"], retro_lesson.id)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class UserPasswordResetTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test_reset@example.com",
            password="OldPassword123!",
            first_name="Test",
            last_name="Reset",
            is_active=True,
        )

    def test_forgot_password_valid_email(self):
        with patch("apps.users.api.send_reset_password_email") as mock_send_email:
            response = self.client.post(
                "/api/users/forgot-password",
                data=json.dumps({"email": self.user.email}),
                content_type="application/json",
            )
            mock_send_email.result = True
            self.assertEqual(response.status_code, 200)

    def test_forgot_password_invalid_email_not_found(self):
        with patch("apps.users.api.send_reset_password_email") as mock_send_email:
            response = self.client.post(
                "/api/users/forgot-password",
                data=json.dumps({"email": "non_existent@example.com"}),
                content_type="application/json",
            )
            mock_send_email.assert_not_called()
            self.assertEqual(response.status_code, 404)

    def test_reset_password_success(self):
        uidb64, token = generate_user_token(self.user)
        new_password = "NewPassword123!"

        response = self.client.post(
            "/api/users/reset-password",
            data=json.dumps(
                {
                    "uid": uidb64,
                    "token": token,
                    "new_password": new_password,
                    "new_password_confirm": new_password,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_reset_password_invalid_token(self):
        response = self.client.post(
            "/api/users/reset-password",
            data=json.dumps(
                {
                    "uid": "invalid",
                    "token": "invalid",
                    "new_password": "NewPassword123!",
                    "new_password_confirm": "NewPassword123!",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_reset_password_mismatched_passwords(self):
        uidb64, token = generate_user_token(self.user)
        response = self.client.post(
            "/api/users/reset-password",
            data=json.dumps(
                {
                    "uid": uidb64,
                    "token": token,
                    "new_password": "NewPassword123!",
                    "new_password_confirm": "Mismatch123!",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class UserAdminActionsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.request = RequestFactory().post("/admin/users/user/")
        self.admin = CustomUserAdmin(User, AdminSite())

        self.active_user = User.objects.create_user(
            email="active-admin-test@example.com",
            password="S3cureP@ss123",
            first_name="Active",
            last_name="User",
            phone="+380501111222",
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
            is_active=True,
        )
        self.inactive_user = User.objects.create_user(
            email="inactive-admin-test@example.com",
            password="S3cureP@ss123",
            first_name="Inactive",
            last_name="User",
            phone="+380501111223",
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
            is_active=False,
        )

    def test_has_user_is_active_permission(self):
        self.assertTrue(self.admin.has_user_is_active_permission(self.request, self.active_user.id))
        self.assertFalse(self.admin.has_user_is_active_permission(self.request, self.inactive_user.id))

    def test_send_chat_invitation_email_for_active_user(self):
        with (
            patch("apps.users.admin.send_chat_invitation_email") as mock_send,
            patch.object(self.admin, "message_user") as mock_message_user,
        ):
            self.admin.send_chat_invitation_email(self.request, self.active_user)

        mock_send.assert_called_once_with(self.active_user)
        mock_message_user.assert_called_once_with(
            self.request,
            _("Chat invitation email sent"),
            level=messages.SUCCESS,
        )


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class UserGetLessonsProgressTests(TestCase):
    def setUp(self):
        self.url = "/api/users/me/lessons/progress"
        self.user = get_user_model().objects.create_user(
            email="progress@example.com",
            password="password",
            first_name="Test",
            last_name="User",
            phone="+1234567890",
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
            is_active=True,
            has_approved_requirements=True,
        )
        login_resp = self.client.post(
            "/api/users/login",
            data=json.dumps({"email": self.user.email, "password": "password"}),
            content_type="application/json",
        )
        self.token = login_resp.json()["access"]
        self.auth_header = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

        self.module = Module.objects.create(name="Test Module")
        self.lesson = Lesson.objects.create(
            name="Test Lesson",
            module_fk=self.module,
            content_type=ContentType.VIDEO,
            order=1,
        )

    def test_get_lessons_progress(self):
        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )

        response = self.client.get(self.url, **self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["lesson_id"], self.lesson.id)
        self.assertTrue(data[0]["is_completed"])

    def test_get_lessons_progress_returns_empty_list_when_no_progress(self):
        response = self.client.get(self.url, **self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])

    def test_get_lessons_progress_returns_all_progress(self):
        lesson2 = Lesson.objects.create(
            name="Lesson 2",
            module_fk=self.module,
            content_type=ContentType.TEXT,
            order=2,
        )
        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )
        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=lesson2,
            is_completed=True,
        )

        response = self.client.get(self.url, **self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)

        lesson_ids = {item["lesson_id"] for item in data}
        self.assertEqual(lesson_ids, {self.lesson.id, lesson2.id})

    def test_get_lessons_progress_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class UserDeleteAccountTests(TestCase):
    def setUp(self):
        self.url = "/api/users/me"
        self.user = get_user_model().objects.create_user(
            email="delete_me@example.com",
            password="password",
            first_name="To Be",
            last_name="Deleted",
            phone="+1234567899",
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
            is_active=True,
            has_approved_requirements=True,
        )
        login_resp = self.client.post(
            "/api/users/login",
            data=json.dumps({"email": self.user.email, "password": "password"}),
            content_type="application/json",
        )
        self.token = login_resp.json()["access"]
        self.auth_header = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    def test_delete_account_success(self):
        module = Module.objects.create(name="Cascade Module")
        lesson = Lesson.objects.create(name="Cascade Lesson", module_fk=module, content_type=ContentType.HOMEWORK)

        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=lesson,
            is_completed=True,
        )

        homework = Homework.objects.create(name="Cascade Homework", lesson_fk=lesson)
        UserSubmission.objects.create(user_fk=self.user, homework_fk=homework, text_answer="I will be deleted")

        response = self.client.delete(self.url, **self.auth_header)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"detail": _("Account deleted successfully.")})

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

        self.assertTrue(UserLessonProgress.objects.filter(user_fk=self.user).exists())
        self.assertTrue(UserSubmission.objects.filter(user_fk=self.user).exists())

    def test_delete_account_unauthorized(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 401)
