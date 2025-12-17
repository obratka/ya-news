from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.conf import settings

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


class TestRoutes(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(username="author", password="pass12345")
        cls.other = User.objects.create_user(username="other", password="pass12345")

        cls.news = News.objects.create(title="T", text="Body")

        cls.comment_author = Comment.objects.create(
            news=cls.news, author=cls.author, text="author comment"
        )
        cls.comment_other = Comment.objects.create(
            news=cls.news, author=cls.other, text="other comment"
        )

        cls.home_url = reverse("news:home")
        cls.detail_url = reverse("news:detail", args=(cls.news.pk,))
        cls.edit_url_author = reverse("news:edit", args=(cls.comment_author.pk,))
        cls.delete_url_author = reverse("news:delete", args=(cls.comment_author.pk,))
        cls.edit_url_other = reverse("news:edit", args=(cls.comment_other.pk,))
        cls.delete_url_other = reverse("news:delete", args=(cls.comment_other.pk,))

        cls.login_url = reverse_any(["users:login", "users:login", "news:login", "accounts:login"])
        cls.logout_url = reverse_any(["users:logout", "users:logout", "news:logout", "accounts:logout"])
        cls.signup_url = reverse_any(["users:signup", "users:signup", "news:signup", "accounts:signup"])


    def test_home_available_for_anonymous(self):
        resp = self.client.get(self.home_url)
        self.assertEqual(resp.status_code, 200)

    def test_detail_available_for_anonymous(self):
        resp = self.client.get(self.detail_url)
        self.assertEqual(resp.status_code, 200)

    def test_edit_delete_available_for_author(self):
        self.client.login(username="author", password="pass12345")
        self.assertEqual(self.client.get(self.edit_url_author).status_code, 200)
        self.assertEqual(self.client.get(self.delete_url_author).status_code, 200)

    def test_anonymous_redirected_to_login_on_edit_delete(self):
        resp_edit = self.client.get(self.edit_url_author)
        resp_delete = self.client.get(self.delete_url_author)

        self.assertRedirects(resp_edit, f"{settings.LOGIN_URL}?next={self.edit_url_author}")
        self.assertRedirects(resp_delete, f"{settings.LOGIN_URL}?next={self.delete_url_author}")


    def test_user_cannot_access_foreign_comment_edit_delete(self):
        self.client.login(username="author", password="pass12345")

        resp_edit = self.client.get(self.edit_url_other)
        resp_delete = self.client.get(self.delete_url_other)

        self.assertEqual(resp_edit.status_code, 404)
        self.assertEqual(resp_delete.status_code, 404)


    def test_anonymous_redirected_to_login_on_edit_delete(self):
        resp_edit = self.client.get(self.edit_url_author)
        resp_delete = self.client.get(self.delete_url_author)

        self.assertRedirects(
            resp_edit,
            f"{settings.LOGIN_URL}?next={self.edit_url_author}"
        )
        self.assertRedirects(
            resp_delete,
            f"{settings.LOGIN_URL}?next={self.delete_url_author}"
        )


    def test_signup_login_logout_available_for_anonymous(self):
        self.assertEqual(self.client.get(self.signup_url).status_code, 200)
        self.assertEqual(self.client.get(self.login_url).status_code, 200)

        # logout может быть только POST — проверяем, что endpoint доступен
        resp = self.client.post(self.logout_url)
        self.assertIn(resp.status_code, (200, 302))

