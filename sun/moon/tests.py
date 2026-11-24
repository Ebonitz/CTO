from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.template.loader import render_to_string

from .models import Appointment, AppointmentStatus, Car, Service
from . import views


class NegativeScenariosTest(TestCase):
    """5 негативных сценариев."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="+79990000001",
            password="testpass123",
            first_name="Тест",
        )

    # 1. 404
    def test_cancel_nonexistent_appointment_returns_404(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("cancel_appointment", args=[999_999])
        )
        self.assertEqual(response.status_code, 404)

    # 2. 403
    def test_staff_page_forbidden_for_regular_client(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("zapisi_mastera"))
        self.assertEqual(response.status_code, 403)

    # 3. Невалидная форма
    def test_invalid_car_form_does_not_create_and_shows_message(self):
        self.client.force_login(self.user)
        before = Car.objects.filter(owner=self.user).count()
        response = self.client.post(reverse("moi_garaje"), data={})
        self.assertEqual(Car.objects.filter(owner=self.user).count(), before)
        self.assertTrue(response.context["form"].errors)
        self.assertTrue(response.context["open_modal"])

    # 4. Ошибка в середине — корзина и записи не меняются
    def test_invalid_appointment_form_preserves_cart_and_no_appointment(self):
        self.client.force_login(self.user)
        service = Service.objects.create(
            name="Замена масла",
            price=Decimal("1500"),
            duration=60,
            category=Service.CATEGORY_CHOICES[0][0],
        )
        session = self.client.session
        session["cart"] = [service.id]
        session.save()

        appointments_before = Appointment.objects.count()
        response = self.client.post(reverse("oformlenie_zapisi"), data={})

        self.assertEqual(Appointment.objects.count(), appointments_before)
        self.assertTrue(response.context["form"].errors)
        self.assertEqual(self.client.session.get("cart"), [service.id])

    # 5. Пустая выборка
    def test_cart_totals_on_empty_does_not_crash(self):
        cost, duration, display = views._cart_totals([])
        self.assertEqual(cost, 0)
        self.assertEqual(duration, 0)
        self.assertEqual(display, "0 мин")


class ErrorTemplatesTest(TestCase):
    def test_error_templates_exist_and_render(self):
        for name, code in (
            ("403.html", "403"),
            ("404.html", "404"),
            ("500.html", "500"),
        ):
            html = render_to_string(name)
            self.assertIn(code, html)