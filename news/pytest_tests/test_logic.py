from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.conf import settings


from news.forms import BAD_WORDS, WARNING
from news.models import News, Comment

User = get_user_model()


def reverse_any(names, args=(), kwargs=None):
    kwargs = kwargs or {}
    last_exc = None
    for name in names:
        try:
            return reverse(name, args=args, kwargs=kwargs)
        except NoReverseMatch as exc:
            last_exc = exc
    raise last_exc


class TestLogic(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(username="author", password="pass12345")
        cls.other = User.objects.create_user(username="other", password="pass12345")

        cls.news = News.objects.create(title="T", text="Body")
        cls.detail_url = reverse("news:detail", args=(cls.news.pk,))

        cls.comment = Comment.objects.create(news=cls.news, author=cls.author, text="Initial")
        cls.edit_url = reverse("news:edit", args=(cls.comment.pk,))
        cls.delete_url = reverse("news:delete", args=(cls.comment.pk,))

        cls.login_url = reverse_any(["users:login", "users:login", "news:login", "accounts:login"])


    def test_anonymous_cannot_post_comment(self):
        before = Comment.objects.count()
        resp = self.client.post(self.detail_url, data={"text": "Hi"})
        self.assertRedirects(resp, f"{self.login_url}?next={self.detail_url}")
        self.assertEqual(Comment.objects.count(), before)

    def test_authenticated_can_post_comment(self):
        self.client.login(username="author", password="pass12345")
        before = Comment.objects.count()

        resp = self.client.post(self.detail_url, data={"text": "New comment"})
        self.assertEqual(resp.status_code, 302)  # редирект на detail#comments
        self.assertEqual(Comment.objects.count(), before + 1)

        new_comment = Comment.objects.order_by("-created").first()
        self.assertEqual(new_comment.author, self.author)
        self.assertEqual(new_comment.news, self.news)
        self.assertEqual(new_comment.text, "New comment")

    def test_bad_words_not_published_and_form_error(self):
        self.client.login(username="author", password="pass12345")
        before = Comment.objects.count()

        bad_word = next(iter(BAD_WORDS))
        resp = self.client.post(self.detail_url, data={"text": f"Text {bad_word} here"})

        self.assertEqual(resp.status_code, 200)  # форма вернулась с ошибкой
        self.assertEqual(Comment.objects.count(), before)

        form = resp.context["form"]
        self.assertIn("text", form.errors)
        self.assertIn(WARNING, form.errors["text"])


    def test_author_can_edit_and_delete_own_comment(self):
        self.client.login(username="author", password="pass12345")

        resp_edit = self.client.post(self.edit_url, data={"text": "Edited"})
        self.assertEqual(resp_edit.status_code, 302)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, "Edited")

        resp_delete = self.client.post(self.delete_url)
        self.assertEqual(resp_delete.status_code, 302)
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_user_cannot_edit_or_delete_foreign_comment(self):
        foreign = Comment.objects.create(news=self.news, author=self.other, text="Foreign")
        edit_url = reverse("news:edit", args=(foreign.pk,))
        delete_url = reverse("news:delete", args=(foreign.pk,))

        self.client.login(username="author", password="pass12345")

        resp_edit = self.client.post(edit_url, data={"text": "Hacked"})
        resp_delete = self.client.post(delete_url)

        self.assertEqual(resp_edit.status_code, 404)
        self.assertEqual(resp_delete.status_code, 404)

        foreign.refresh_from_db()
        self.assertEqual(foreign.text, "Foreign")
        self.assertTrue(Comment.objects.filter(pk=foreign.pk).exists())

    def test_anonymous_cannot_post_comment(self):
        before = Comment.objects.count()
        resp = self.client.post(self.detail_url, data={"text": "Hi"})
        self.assertRedirects(resp, f"{settings.LOGIN_URL}?next={self.detail_url}")
        self.assertEqual(Comment.objects.count(), before)
