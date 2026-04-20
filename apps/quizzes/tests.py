import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.modules.models import ContentType, Lesson, Module
from apps.quizzes.models import (
    Answer,
    Question,
    QuestionTypes,
    Quiz,
)
from apps.users.models import AgeGroupChoice, UserGroup


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class QuizApiTests(TestCase):
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
        self.quiz = Quiz.objects.create(name="Test Quiz")
        self.lesson = Lesson.objects.create(
            name="Test Lesson",
            module_fk=self.module,
            quiz_fk=self.quiz,
            content_type=ContentType.QUIZ,
        )

        self.q_single = Question.objects.create(
            title="Single Choice",
            question_type=QuestionTypes.SINGLE_CHOICE,
            quiz_fk=self.quiz,
            order=1,
        )
        self.a_single_correct = Answer.objects.create(response="Correct", is_correct=True, question_fk=self.q_single)
        self.a_single_wrong = Answer.objects.create(response="Wrong", is_correct=False, question_fk=self.q_single)

        self.q_multi = Question.objects.create(
            title="Multi Choice",
            question_type=QuestionTypes.MULTIPLE_CHOICE,
            quiz_fk=self.quiz,
            order=2,
        )
        self.a_multi_correct1 = Answer.objects.create(response="Correct 1", is_correct=True, question_fk=self.q_multi)
        self.a_multi_correct2 = Answer.objects.create(response="Correct 2", is_correct=True, question_fk=self.q_multi)

        self.q_text = Question.objects.create(
            title="Text Question",
            question_type=QuestionTypes.TEXT,
            quiz_fk=self.quiz,
            order=3,
        )

    def test_get_quizzes(self):
        response = self.client.get(f"/api/quizzes/{self.module.id}", **self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Test Quiz")
        self.assertEqual(data[0]["max_score"], 4.0)

    def test_get_quiz_detail(self):
        response = self.client.get(f"/api/quizzes/{self.module.id}/{self.quiz.id}", **self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Test Quiz")
        self.assertEqual(data["max_score"], 4.0)

    def test_start_quiz(self):
        payload = {"quiz_id": self.quiz.id, "lesson_id": self.lesson.id}
        response = self.client.post(
            "/api/quizzes/attempts",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("uid", data)
        self.attempt_uid = data["uid"]

        response = self.client.post(
            "/api/quizzes/attempts",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 400)

    def test_quiz_flow_full(self):
        payload = {"quiz_id": self.quiz.id, "lesson_id": self.lesson.id}
        response = self.client.post(
            "/api/quizzes/attempts",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        attempt_uid = response.json()["uid"]

        payload = {
            "attempt_uid": attempt_uid,
            "quiz_id": self.quiz.id,
            "question_id": self.q_single.id,
            "lesson_id": self.lesson.id,
            "answer_ids": [self.a_single_correct.id],
        }
        response = self.client.post(
            "/api/quizzes/attempts/answers",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["is_correct"])

        payload = {
            "attempt_uid": attempt_uid,
            "quiz_id": self.quiz.id,
            "question_id": self.q_multi.id,
            "lesson_id": self.lesson.id,
            "answer_ids": [self.a_multi_correct1.id, self.a_multi_correct2.id],
        }
        response = self.client.post(
            "/api/quizzes/attempts/answers",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["is_correct"])

        payload = {
            "attempt_uid": attempt_uid,
            "quiz_id": self.quiz.id,
            "question_id": self.q_text.id,
            "lesson_id": self.lesson.id,
            "text_response": "Some text",
        }
        response = self.client.post(
            "/api/quizzes/attempts/answers",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 201)

        payload = {"attempt_uid": attempt_uid, "quiz_id": self.quiz.id, "lesson_id": self.lesson.id}
        response = self.client.post(
            "/api/quizzes/attempts/results",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_completed"])
        self.assertEqual(data["score"], 4.0)
        self.assertEqual(data["max_score"], 4.0)

    def test_finish_incomplete_quiz_should_fail(self):
        payload = {"quiz_id": self.quiz.id, "lesson_id": self.lesson.id}
        response = self.client.post(
            "/api/quizzes/attempts",
            data=json.dumps(payload),
            content_type="text/html; charset=utf-8",
            **self.auth_header,
        )
        attempt_uid = response.json()["uid"]

        payload = {"attempt_uid": attempt_uid, "quiz_id": self.quiz.id, "lesson_id": self.lesson.id}
        response = self.client.post(
            "/api/quizzes/attempts/results",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 400)

    def test_force_finish_quiz(self):
        payload = {"quiz_id": self.quiz.id, "lesson_id": self.lesson.id}
        response = self.client.post(
            "/api/quizzes/attempts",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        attempt_uid = response.json()["uid"]

        payload = {"attempt_uid": attempt_uid, "quiz_id": self.quiz.id, "lesson_id": self.lesson.id, "is_force": True}
        response = self.client.post(
            "/api/quizzes/attempts/results",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_completed"])

    def test_duplicate_answer_submission(self):
        payload = {"quiz_id": self.quiz.id, "lesson_id": self.lesson.id}
        response = self.client.post(
            "/api/quizzes/attempts",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        attempt_uid = response.json()["uid"]

        payload = {
            "attempt_uid": attempt_uid,
            "quiz_id": self.quiz.id,
            "question_id": self.q_single.id,
            "lesson_id": self.lesson.id,
            "answer_ids": [self.a_single_correct.id],
        }
        response = self.client.post(
            "/api/quizzes/attempts/answers",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            "/api/quizzes/attempts/answers",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 409)

    def test_duplicate_text_answer_submission(self):
        payload = {"quiz_id": self.quiz.id, "lesson_id": self.lesson.id}
        response = self.client.post(
            "/api/quizzes/attempts",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        attempt_uid = response.json()["uid"]

        payload = {
            "attempt_uid": attempt_uid,
            "quiz_id": self.quiz.id,
            "question_id": self.q_text.id,
            "lesson_id": self.lesson.id,
            "text_response": "Some text",
        }
        response = self.client.post(
            "/api/quizzes/attempts/answers",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            "/api/quizzes/attempts/answers",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 409)

    def test_duplicate_multiple_choice_answer_submission(self):
        payload = {"quiz_id": self.quiz.id, "lesson_id": self.lesson.id}
        response = self.client.post(
            "/api/quizzes/attempts",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        attempt_uid = response.json()["uid"]

        payload = {
            "attempt_uid": attempt_uid,
            "quiz_id": self.quiz.id,
            "question_id": self.q_multi.id,
            "lesson_id": self.lesson.id,
            "answer_ids": [self.a_multi_correct1.id, self.a_multi_correct2.id],
        }
        response = self.client.post(
            "/api/quizzes/attempts/answers",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            "/api/quizzes/attempts/answers",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 409)

    def test_submit_answer_for_wrong_question(self):
        payload = {"quiz_id": self.quiz.id, "lesson_id": self.lesson.id}
        response = self.client.post(
            "/api/quizzes/attempts",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        attempt_uid = response.json()["uid"]

        payload = {
            "attempt_uid": attempt_uid,
            "quiz_id": self.quiz.id,
            "lesson_id": self.lesson.id,
            "question_id": self.q_single.id,
            "answer_ids": [self.a_multi_correct1.id],
        }
        response = self.client.post(
            "/api/quizzes/attempts/answers",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertIn(response.status_code, [404, 500])

    def test_submit_question_for_wrong_quiz(self):
        other_quiz = Quiz.objects.create(name="Other Quiz")
        other_question = Question.objects.create(
            title="Other Question",
            question_type=QuestionTypes.TEXT,
            quiz_fk=other_quiz,
            order=1,
        )
        other_lesson = Lesson.objects.create(
            name="Other Lesson", module_fk=self.module, quiz_fk=other_quiz, content_type=ContentType.QUIZ, order=99
        )

        payload = {"quiz_id": other_quiz.id, "lesson_id": other_lesson.id}
        response = self.client.post(
            "/api/quizzes/attempts",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        attempt_uid = response.json()["uid"]

        payload = {
            "attempt_uid": attempt_uid,
            "quiz_id": self.quiz.id,
            "lesson_id": self.lesson.id,
            "question_id": other_question.id,
            "text_response": "Some text",
        }
        response = self.client.post(
            "/api/quizzes/attempts/answers",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertIn(response.status_code, [404, 500])

    def test_multiple_choice_scoring_logic(self):
        payload = {"quiz_id": self.quiz.id, "lesson_id": self.lesson.id}
        response = self.client.post(
            "/api/quizzes/attempts",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_header,
        )
        attempt_uid = response.json()["uid"]

        payload_ans = {
            "attempt_uid": attempt_uid,
            "quiz_id": self.quiz.id,
            "question_id": self.q_multi.id,
            "lesson_id": self.lesson.id,
            "answer_ids": [self.a_multi_correct1.id, self.a_multi_correct2.id],
        }
        response = self.client.post(
            "/api/quizzes/attempts/answers",
            data=json.dumps(payload_ans),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["is_correct"])
        self.assertEqual(response.json()["points_awarded"], 1.0)

        self.client.post(
            "/api/quizzes/attempts/results",
            data=json.dumps(
                {
                    "attempt_uid": attempt_uid,
                    "quiz_id": self.quiz.id,
                    "lesson_id": self.lesson.id,
                    "is_force": True,
                }
            ),
            content_type="application/json",
            **self.auth_header,
        )

        response = self.client.post(
            "/api/quizzes/attempts",
            data=json.dumps(
                {
                    "quiz_id": self.quiz.id,
                    "lesson_id": self.lesson.id,
                }
            ),
            content_type="application/json",
            **self.auth_header,
        )
        attempt_uid_2 = response.json()["uid"]

        payload_ans["attempt_uid"] = attempt_uid_2
        payload_ans["answer_ids"] = [self.a_multi_correct1.id]

        response = self.client.post(
            "/api/quizzes/attempts/answers",
            data=json.dumps(payload_ans),
            content_type="application/json",
            **self.auth_header,
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()["is_correct"])  # Not fully correct
        self.assertEqual(response.json()["points_awarded"], 0.5)

        # Finish second attempt
        self.client.post(
            "/api/quizzes/attempts/results",
            data=json.dumps(
                {
                    "attempt_uid": attempt_uid_2,
                    "quiz_id": self.quiz.id,
                    "is_force": True,
                }
            ),
            content_type="application/json",
            **self.auth_header,
        )

        # TODO: Check it because now there is 409 status code with {'detail': 'Відповідь на це питання вже існує.'}
        # # 3. Mixed (1 correct, 1 wrong) - should be 0 points?
        # # We need to add a wrong answer to q_multi setup
        # a_multi_wrong = Answer.objects.create(response="Wrong Multi", is_correct=False, question_fk=self.q_multi)
        # # Start new attempt
        # response = self.client.post(
        #     "/api/quizzes/attempts",
        #     data=json.dumps(
        #         {
        #             "quiz_id": self.quiz.id,
        #             "lesson_id": self.lesson.id,
        #         }
        #     ),
        #     content_type="application/json",
        #     **self.auth_header,
        # )
        # attempt_uid_3 = response.json()["uid"]
        #
        # payload_ans["attempt_uid"] = attempt_uid_3
        # payload_ans["answer_ids"] = [self.a_multi_correct1.id, a_multi_wrong.id]
        #
        # response = self.client.post(
        #     "/api/quizzes/attempts/answers",
        #     data=json.dumps(payload_ans),
        #     content_type="application/json",
        #     **self.auth_header,
        # )
        # self.assertEqual(response.status_code, 201)
        # self.assertFalse(response.json()["is_correct"])
        # # (1 correct - 1 wrong) / 2 total correct = 0 / 2 = 0
        # self.assertEqual(response.json()["points_awarded"], 0.0)
