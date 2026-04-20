import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.utils import timezone

from apps.homeworks.models import Homework, UserSubmission
from apps.modules.models import ContentType, Lesson, Module
from apps.users.models import AgeGroupChoice, UserGroup


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class HomeworkApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="student@example.com",
            password="password",
            first_name="Student",
            last_name="One",
            phone="+1234567890",
            age_group=AgeGroupChoice.UNDER_24,
            country="Ukraine",
            city="Kyiv",
            is_active=True,
            has_approved_requirements=True,
        )
        self.user_group = UserGroup.objects.create(
            registration_started_at=timezone.now(),
            course_started_at=timezone.now(),
        )
        self.user_group.users.add(self.user)
        login_resp = self.client.post(
            "/api/users/login",
            data=json.dumps({"email": self.user.email, "password": "password"}),
            content_type="application/json",
        )
        self.token = login_resp.json()["access"]
        self.auth_header = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

        self.module = Module.objects.create(name="Test Module", description="Test Description")
        self.lesson = Lesson.objects.create(
            name="Test Lesson",
            module_fk=self.module,
            content_type=ContentType.HOMEWORK,
            order=1,
        )
        self.homework = Homework.objects.create(
            name="Test Homework",
            description="Homework Description",
            lesson_fk=self.lesson,
        )

    def test_get_homework_by_id(self):
        response = self.client.get(f"/api/homeworks/{self.homework.id}", **self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Test Homework")

    def test_send_homework(self):
        payload = {"homework_id": self.homework.id, "text_answer": "My answer"}
        response = self.client.post(
            "/api/homeworks/submission",
            data=payload,
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["text_answer"], "My answer")
        self.assertEqual(data["is_approved"], True)

        submission = UserSubmission.objects.get(user_fk=self.user, homework_fk=self.homework)
        self.assertEqual(submission.text_answer, "My answer")

    def test_send_homework_duplicate(self):
        UserSubmission.objects.create(user_fk=self.user, homework_fk=self.homework, text_answer="First answer")

        payload = {"homework_id": self.homework.id, "text_answer": "Second answer"}
        response = self.client.post(
            "/api/homeworks/submission",
            data=payload,
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 409)

    def test_get_submission(self):
        UserSubmission.objects.create(user_fk=self.user, homework_fk=self.homework, text_answer="Existing answer")

        response = self.client.get(f"/api/homeworks/submission/{self.homework.id}", **self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["text_answer"], "Existing answer")

    def test_auto_approve_homework(self):
        auto_homework = Homework.objects.create(name="Auto Homework", lesson_fk=self.lesson, is_auto_approved=True)
        payload = {"homework_id": auto_homework.id, "text_answer": "Auto answer"}
        response = self.client.post(
            "/api/homeworks/submission",
            data=payload,
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["is_approved"], True)

    def test_send_homework_file_answer(self):
        file_content = b"file_content"
        uploaded_file = SimpleUploadedFile("test_file.txt", file_content, content_type="text/plain")
        payload = {"homework_id": self.homework.id, "file_answer": uploaded_file}
        response = self.client.post(
            "/api/homeworks/submission",
            data=payload,
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIsNone(data["text_answer"])
        self.assertTrue(data["file_answer"])

        submission = UserSubmission.objects.get(user_fk=self.user, homework_fk=self.homework)
        self.assertTrue(submission.file_answer)

    def test_send_homework_no_answer(self):
        payload = {"homework_id": self.homework.id}
        response = self.client.post(
            "/api/homeworks/submission",
            data=payload,
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertIn("detail", data)

    def test_edit_submission_text(self):
        UserSubmission.objects.create(user_fk=self.user, homework_fk=self.homework, text_answer="Original answer")

        response = self.client.put(
            f"/api/homeworks/submission/{self.homework.id}",
            data=encode_multipart(BOUNDARY, {"text_answer": "Updated answer"}),
            content_type=MULTIPART_CONTENT,
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["text_answer"], "Updated answer")

        submission = UserSubmission.objects.get(user_fk=self.user, homework_fk=self.homework)
        self.assertEqual(submission.text_answer, "Updated answer")

    def test_edit_submission_file(self):
        UserSubmission.objects.create(user_fk=self.user, homework_fk=self.homework, text_answer="Original")

        uploaded_file = SimpleUploadedFile("updated_file.txt", b"new content", content_type="text/plain")
        response = self.client.put(
            f"/api/homeworks/submission/{self.homework.id}",
            data=encode_multipart(BOUNDARY, {"file_answer": uploaded_file}),
            content_type=MULTIPART_CONTENT,
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["file_answer"])

    def test_edit_submission_not_found(self):
        response = self.client.put(
            f"/api/homeworks/submission/{self.homework.id}",
            data=encode_multipart(BOUNDARY, {"text_answer": "No submission yet"}),
            content_type=MULTIPART_CONTENT,
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 404)

    def test_edit_submission_clears_all_answers_returns_422(self):
        UserSubmission.objects.create(user_fk=self.user, homework_fk=self.homework, text_answer="Only text")

        response = self.client.put(
            f"/api/homeworks/submission/{self.homework.id}",
            data=encode_multipart(BOUNDARY, {"text_answer": ""}),
            content_type=MULTIPART_CONTENT,
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 422)
