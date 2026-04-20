import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.modules.models import ContentType, Lesson, Module
from apps.quizzes.models import Quiz


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class AdminApiTests(TestCase):
    def setUp(self):
        self.staff_user = get_user_model().objects.create_user(
            email="staff@example.com",
            password="password",
            first_name="Staff",
            last_name="User",
            phone="+1234567890",
            is_staff=True,
            is_active=True,
        )
        self.user = get_user_model().objects.create_user(
            email="student@example.com", password="password", phone="+0987654321", is_staff=False, is_active=True
        )

        self.module = Module.objects.create(name="Test Module", order=1)
        self.module2 = Module.objects.create(name="Test Module 2", order=2)

        self.quiz = Quiz.objects.create(name="Test Quiz")

        self.lesson = Lesson.objects.create(
            name="Quiz Lesson", module_fk=self.module, content_type=ContentType.QUIZ, quiz_fk=self.quiz, order=1
        )

        self.save_order_url = "/api/admin/save-order"
        self.get_quizzes_url = f"/api/admin/quizzes/{self.module.id}"

    def test_save_order_success(self):
        self.client.force_login(self.staff_user)
        payload = {
            "app_label": "modules",
            "model_name": "Module",
            "orders": [{"id": self.module.id, "order": 2}, {"id": self.module2.id, "order": 1}],
        }
        response = self.client.post(self.save_order_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        self.module.refresh_from_db()
        self.module2.refresh_from_db()
        self.assertEqual(self.module.order, 3)
        self.assertEqual(self.module2.order, 2)

    def test_save_order_forbidden_non_staff(self):
        self.client.force_login(self.user)
        payload = {"app_label": "modules", "model_name": "Module", "orders": [{"id": self.module.id, "order": 2}]}
        response = self.client.post(self.save_order_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 401)
