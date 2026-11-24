from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Profile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile', verbose_name="Пользователь"
    )
    phone = models.CharField(max_length=20, verbose_name="Телефон", unique=True)

    class Meta:
        verbose_name = "Профиль клиента"
        verbose_name_plural = "Профили клиентов"

    def __str__(self):
        return f"Профиль: {self.user.username}"


class Car(models.Model):
    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='cars', verbose_name="Владелец (клиент)"
    )
    brand = models.CharField(max_length=100, verbose_name="Марка")
    model = models.CharField(max_length=100, verbose_name="Модель")
    year = models.IntegerField(
        verbose_name="Год выпуска", 
        null=True, blank=True,
        validators=[MinValueValidator(1900), MaxValueValidator(timezone.now().year)]
    )
    license_plate = models.CharField(max_length=20, verbose_name="Госномер", unique=True)

    class Meta:
        verbose_name = "Автомобиль"
        verbose_name_plural = "Автомобили"
        ordering = ['brand', 'model']

    def __str__(self):
        return f"{self.brand} {self.model} ({self.license_plate})"


class Service(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название услуги", unique=True)
    description = models.TextField(verbose_name="Описание", blank=True, null=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Стоимость",
        validators=[MinValueValidator(0)]
    )
    duration = models.IntegerField(
        verbose_name="Длительность (мин)", 
        validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
        ordering = ['name']
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name='price_non_negative'),
            models.CheckConstraint(condition=models.Q(duration__gte=1), name='duration_positive')
        ]

    def __str__(self):
        return f"{self.name} ({self.price} руб., {self.duration} мин)"


class Specialization(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название специализации", unique=True)
    description = models.TextField(verbose_name="Описание", blank=True, null=True)

    class Meta:
        verbose_name = "Специализация"
        verbose_name_plural = "Специализации"

    def __str__(self):
        return self.name


class Master(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    last_name = models.CharField(max_length=100, verbose_name="Фамилия")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    specializations = models.ManyToManyField(
        Specialization, related_name='masters', verbose_name="Специализации", blank=True
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Мастер"
        verbose_name_plural = "Мастера"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


class AppointmentStatus(models.Model):
    name = models.CharField(max_length=50, verbose_name="Название статуса", unique=True)
    description = models.CharField(max_length=200, verbose_name="Описание", blank=True, null=True)

    class Meta:
        verbose_name = "Статус записи"
        verbose_name_plural = "Статусы записей"

    def __str__(self):
        return self.name


class Appointment(models.Model):
    client = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='appointments', verbose_name="Клиент"
    )
    car = models.ForeignKey(
        Car, on_delete=models.PROTECT, related_name='appointments', verbose_name="Автомобиль"
    )
    master = models.ForeignKey(
        Master, on_delete=models.PROTECT, related_name='appointments', verbose_name="Мастер"
    )
    date = models.DateField(verbose_name="Дата записи")
    time = models.TimeField(verbose_name="Время записи")
    total_cost = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Итоговая стоимость"
    )
    total_duration = models.IntegerField(verbose_name="Итоговая длительность (мин)")
    status = models.ForeignKey(
        AppointmentStatus, on_delete=models.PROTECT, related_name='appointments', 
        verbose_name="Статус"
    )

    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"
        ordering = ['-date', '-time']
        # NFR-03: Запрет двойной записи к одному мастеру на одно время
        constraints = [
            models.UniqueConstraint(
                fields=['master', 'date', 'time'], 
                name='unique_master_appointment_time'
            )
        ]

    def __str__(self):
        return f"Запись клиента {self.client.username} к {self.master.last_name} на {self.date} {self.time}"


class AppointmentService(models.Model):
    """Явная связующая таблица для связи M:M с собственными атрибутами (NFR-09)"""
    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name='services', verbose_name="Запись"
    )
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name='appointments', verbose_name="Услуга"
    )
    agreed_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Цена на момент записи"
    )
    agreed_duration = models.IntegerField(verbose_name="Длительность на момент записи (мин)")

    class Meta:
        verbose_name = "Услуга в записи"
        verbose_name_plural = "Услуги в записях"
        constraints = [
            models.UniqueConstraint(
                fields=['appointment', 'service'], 
                name='unique_service_per_appointment'
            )
        ]

    def __str__(self):
        return f"{self.service.name} в записи #{self.appointment.id}"