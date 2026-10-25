from django.test import TestCase
from django.urls import reverse

from .models import Activity, Category, Trainer


class ActivityFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Programming')
        cls.other_category = Category.objects.create(name='Design')
        trainer = Trainer.objects.create(full_name='Test Trainer', email='trainer@example.com')
        for title, category in (
            ('Python Basics', cls.category),
            ('Python Advanced', cls.category),
            ('Design Basics', cls.other_category),
        ):
            Activity.objects.create(
                title=title, category=category, trainer=trainer, duration=1, max_students=1,
            )

    def test_malformed_category_returns_empty_results_without_error(self):
        invalid_values = (
            'abc', '0', '-1', '1.5', '1e3', '9223372036854775808', '9' * 5000,
        )
        for category in invalid_values:
            with self.subTest(category=category[:30]):
                response = self.client.get(reverse('shop:activity_list'), {'category': category})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['page_obj'].paginator.count, 0)
                self.assertContains(response, 'No activities match your search.')

    def test_unknown_category_does_not_show_unrelated_activities(self):
        response = self.client.get(
            reverse('shop:activity_list'), {'category': 9223372036854775807},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 0)

    def test_blank_category_keeps_case_insensitive_partial_search(self):
        response = self.client.get(
            reverse('shop:activity_list'), {'category': '   ', 'q': '  pYtH  '},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['query'], 'pYtH')
        self.assertEqual(response.context['page_obj'].paginator.count, 2)
        self.assertNotContains(response, 'Design Basics')

    def test_category_is_normalized_and_combines_with_title_search(self):
        response = self.client.get(
            reverse('shop:activity_list'),
            {'category': f' 00{self.category.pk} ', 'q': 'basic'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_category'], str(self.category.pk))
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertContains(response, 'Python Basics')
        self.assertNotContains(response, 'Python Advanced')
        self.assertNotContains(response, 'Design Basics')
        self.assertContains(response, f'value="{self.category.pk}" selected')

    def test_unicode_digit_category_is_safely_normalized(self):
        unicode_id = str(self.category.pk).translate(str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩'))
        response = self.client.get(reverse('shop:activity_list'), {'category': unicode_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_category'], str(self.category.pk))
        self.assertEqual(response.context['page_obj'].paginator.count, 2)

    def test_invalid_category_preserves_search_and_handles_invalid_page(self):
        response = self.client.get(
            reverse('shop:activity_list'), {'category': 'abc', 'q': 'Python', 'page': 'bad'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['query'], 'Python')
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(response.context['page_obj'].paginator.count, 0)
