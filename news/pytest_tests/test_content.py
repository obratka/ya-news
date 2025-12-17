from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from news.models import News, Comment

User = get_user_model()


class TestContent(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="u", password="pass12345")
        cls.home_url = reverse("news:home")

        today = timezone.now().date()

        # создаём 11 новостей с разными датами (свежие должны быть первыми)
        cls.all_news = []
        for i in range(11):
            n = News.objects.create(title=f"News {i}", text="Body")
            cls.all_news.append(n)
        for i, n in enumerate(cls.all_news):
            # i=0 -> самая свежая (today), i=10 -> самая старая
            News.objects.filter(pk=n.pk).update(date=today - timedelta(days=i))

        cls.news_for_detail = cls.all_news[0]
        cls.detail_url = reverse("news:detail", args=(cls.news_for_detail.pk,))

        # два комментария с разным временем
        cls.c_old = Comment.objects.create(news=cls.news_for_detail, author=cls.user, text="old")
        cls.c_new = Comment.objects.create(news=cls.news_for_detail, author=cls.user, text="new")
        now = timezone.now()
        Comment.objects.filter(pk=cls.c_old.pk).update(created=now - timedelta(days=2))
        Comment.objects.filter(pk=cls.c_new.pk).update(created=now - timedelta(days=1))

    def test_news_count_on_home_page_not_more_than_10(self):
        resp = self.client.get(self.home_url)
        self.assertEqual(resp.status_code, 200)

        news_list = resp.context["news_list"]  # у ListView по умолчанию именно так
        self.assertLessEqual(len(news_list), 10)
        # и заодно совпадает с настройкой (обычно 10)
        self.assertEqual(len(news_list), min(settings.NEWS_COUNT_ON_HOME_PAGE, 11))

    def test_news_order_from_fresh_to_old(self):
        resp = self.client.get(self.home_url)
        news_list = resp.context["news_list"]
        dates = [n.date for n in news_list]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_comments_order_old_to_new_on_detail(self):
        resp = self.client.get(self.detail_url)
        self.assertEqual(resp.status_code, 200)

        news_obj = resp.context["news"]  # DetailView даёт model_name в context
        comments = list(news_obj.comment_set.all())  # порядок задаёт Meta.ordering
        created = [c.created for c in comments]
        self.assertEqual(created, sorted(created))

    def test_comment_form_visible_only_for_authenticated(self):
        resp_anon = self.client.get(self.detail_url)
        self.assertNotIn("form", resp_anon.context)

        self.client.login(username="u", password="pass12345")
        resp_auth = self.client.get(self.detail_url)
        self.assertIn("form", resp_auth.context)
