import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.modules.models import ContentType, Lesson, Module, UserLessonProgress
from apps.modules.services import LessonNavigationService
from apps.users.models import AgeGroupChoice, UserGroup


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class ModuleApiTests(TestCase):
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
            content_type=ContentType.VIDEO,
            order=1,
            video_url="video.mp4",
            description="Video lesson description",
        )
        self.complete_url = "/api/modules/lessons/complete"
        self.complete_payload = {
            "module_id": self.module.id,
            "lesson_id": self.lesson.id,
        }

    def test_complete_lesson_success(self):
        response = self.client.post(
            self.complete_url,
            data=json.dumps(self.complete_payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user_score"], 3)
        self.assertTrue(data["is_completed"])

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

        response = self.client.post(
            self.complete_url,
            data=json.dumps(self.complete_payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user_score"], 3)  # Score should NOT increase

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

    def test_get_modules(self):
        response = self.client.get("/api/modules/", **self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Test Module")

    def test_get_module_by_id(self):
        response = self.client.get(f"/api/modules/{self.module.id}", **self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Test Module")
        self.assertEqual(data["description"], "Test Description")

    def test_get_lessons_for_module(self):
        response = self.client.get(f"/api/modules/{self.module.id}/lessons", **self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Test Lesson")
        self.assertEqual(data[0]["description"], "Video lesson description")

    def test_get_lesson_detail(self):
        response = self.client.get(
            f"/api/modules/{self.module.id}/lessons/{self.lesson.id}",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Test Lesson")
        self.assertIn("/media/video.mp4", data["video_url"])
        self.assertEqual(data["description"], "Video lesson description")

    def test_get_lesson_detail_returns_previous_and_next_lesson(self):
        middle_lesson = Lesson.objects.create(
            name="Middle Lesson",
            module_fk=self.module,
            content_type=ContentType.TEXT,
            order=2,
        )
        next_lesson = Lesson.objects.create(
            name="Next Lesson",
            module_fk=self.module,
            content_type=ContentType.TEXT,
            order=3,
        )

        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )

        response = self.client.get(
            f"/api/modules/{self.module.id}/lessons/{middle_lesson.id}",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            data["previous_lesson"],
            {
                "module_id": self.module.id,
                "lesson_id": self.lesson.id,
            },
        )
        self.assertEqual(
            data["next_lesson"],
            {
                "module_id": self.module.id,
                "lesson_id": next_lesson.id,
            },
        )

    def test_lesson_navigation_uses_module_order_before_lesson_order(self):
        previous_module = Module.objects.create(name="Previous module")
        previous_module.order = 1
        previous_module.save(update_fields=["order"])

        current_module = Module.objects.create(name="Current module")
        current_module.order = 4
        current_module.save(update_fields=["order"])

        next_module = Module.objects.create(name="Next module")
        next_module.order = 5
        next_module.save(update_fields=["order"])

        previous_lesson_expected = Lesson.objects.create(
            name="Previous lesson",
            module_fk=previous_module,
            content_type=ContentType.TEXT,
            order=30,
        )
        current_lesson = Lesson.objects.create(
            name="Current lesson",
            module_fk=current_module,
            content_type=ContentType.TEXT,
            order=6,
        )
        next_lesson_expected = Lesson.objects.create(
            name="Next lesson",
            module_fk=next_module,
            content_type=ContentType.TEXT,
            order=6,
        )

        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )
        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=previous_lesson_expected,
            is_completed=True,
        )

        previous_lesson, next_lesson = LessonNavigationService.get_navigation_for_lesson(current_lesson, self.user)

        self.assertEqual(
            previous_lesson,
            {
                "module_id": previous_module.id,
                "lesson_id": previous_lesson_expected.id,
            },
        )
        self.assertEqual(
            next_lesson,
            {
                "module_id": next_module.id,
                "lesson_id": next_lesson_expected.id,
            },
        )

    def test_lesson_navigation_prioritizes_incomplete_previous_lessons_for_next(self):
        middle_lesson = Lesson.objects.create(
            name="Middle lesson",
            module_fk=self.module,
            content_type=ContentType.TEXT,
            order=2,
        )
        current_lesson = Lesson.objects.create(
            name="Current lesson",
            module_fk=self.module,
            content_type=ContentType.TEXT,
            order=3,
        )
        forward_lesson = Lesson.objects.create(
            name="Forward lesson",
            module_fk=self.module,
            content_type=ContentType.TEXT,
            order=4,
        )

        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=middle_lesson,
            is_completed=True,
        )

        previous_lesson, next_lesson = LessonNavigationService.get_navigation_for_lesson(
            current_lesson,
            self.user,
        )

        self.assertEqual(
            previous_lesson,
            {
                "module_id": self.module.id,
                "lesson_id": middle_lesson.id,
            },
        )
        self.assertEqual(
            next_lesson,
            {
                "module_id": self.module.id,
                "lesson_id": self.lesson.id,
            },
        )
        self.assertNotEqual(next_lesson["lesson_id"], forward_lesson.id)

    def test_description_is_only_for_audio_video(self):
        text_lesson = Lesson.objects.create(
            name="Text Lesson",
            module_fk=self.module,
            content_type=ContentType.TEXT,
            text_content="Text content",
            description="Should be removed",
        )

        text_lesson.refresh_from_db()
        self.assertIsNone(text_lesson.description)

        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )

        response = self.client.get(
            f"/api/modules/{self.module.id}/lessons/{text_lesson.id}",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data["description"])

    def test_score_decrements_on_progress_delete(self):
        progress = UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

        progress.delete()

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 0)

    def test_score_decrements_on_lesson_delete(self):
        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

        self.lesson.delete()

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 0)

    def test_score_does_not_increment_on_update(self):
        progress = UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

        # Update progress (save again)
        progress.save()

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

    def test_score_not_negative(self):
        progress = UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

        self.user.score = 1
        self.user.save()

        progress.delete()

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 0)

    def test_score_recalculated_when_completed_lesson_deactivated(self):
        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

        self.lesson.is_active = False
        self.lesson.save(update_fields=["is_active"])

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 0)

    def test_score_recalculated_when_completed_lesson_reactivated(self):
        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )

        self.lesson.is_active = False
        self.lesson.save(update_fields=["is_active"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 0)

        self.lesson.is_active = True
        self.lesson.save(update_fields=["is_active"])

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

    def test_score_recalculated_when_completed_module_deactivated(self):
        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

        self.module.is_active = False
        self.module.save(update_fields=["is_active"])

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 0)

    def test_score_recalculated_when_completed_module_reactivated(self):
        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )

        self.module.is_active = False
        self.module.save(update_fields=["is_active"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 0)

        self.module.is_active = True
        self.module.save(update_fields=["is_active"])

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

    def test_score_unchanged_when_lesson_saved_without_is_active_change(self):
        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

        self.lesson.name = "Updated Lesson Name"
        self.lesson.save()

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

    def test_score_unchanged_when_module_saved_without_is_active_change(self):
        UserLessonProgress.objects.create(
            user_fk=self.user,
            lesson_fk=self.lesson,
            is_completed=True,
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

        self.module.name = "Updated Module Name"
        self.module.save()

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 3)

    def test_get_inserted_lesson_after_progress_is_allowed(self):
        second_lesson = Lesson.objects.create(
            name="Second Lesson",
            module_fk=self.module,
            content_type=ContentType.TEXT,
            order=2,
        )
        third_lesson = Lesson.objects.create(
            name="Third Lesson",
            module_fk=self.module,
            content_type=ContentType.TEXT,
            order=3,
        )

        UserLessonProgress.objects.create(user_fk=self.user, lesson_fk=self.lesson, is_completed=True)
        UserLessonProgress.objects.create(user_fk=self.user, lesson_fk=second_lesson, is_completed=True)
        UserLessonProgress.objects.create(user_fk=self.user, lesson_fk=third_lesson, is_completed=True)

        inserted_lesson = Lesson.objects.create(
            name="Inserted Lesson",
            module_fk=self.module,
            content_type=ContentType.TEXT,
            order=10,
        )
        inserted_lesson.order = 2
        inserted_lesson.save(update_fields=["order"])

        response = self.client.get(
            f"/api/modules/{self.module.id}/lessons/{inserted_lesson.id}",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, 200)
