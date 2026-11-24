import re
from datetime import date as date_cls
from datetime import datetime, timedelta

from django import forms
from django.contrib.auth import authenticate, get_user_model

from .models import Appointment, Car, Master

User = get_user_model()


# Рабочие слоты мастеров (пн-пт, 9:00–17:00)
TIME_SLOTS = [
    ("09:00", "09:00 - 11:00"),
    ("11:00", "11:00 - 13:00"),
    ("13:00", "13:00 - 15:00"),
    ("15:00", "15:00 - 17:00"),
]

SLOT_ENDS = {
    "09:00": "11:00",
    "11:00": "13:00",
    "13:00": "15:00",
    "15:00": "17:00",
}


class StaffLoginForm(forms.Form):
    phone = forms.CharField(max_length=20, label="Телефон")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")

    def clean(self):
        cleaned_data = super().clean()
        phone = cleaned_data.get("phone")
        password = cleaned_data.get("password")

        if not phone or not password:
            return cleaned_data

        try:
            phone = normalize_phone(phone)
        except forms.ValidationError as error:
            self.add_error("phone", error)
            return cleaned_data

        user = authenticate(username=phone, password=password)

        if user is None:
            raise forms.ValidationError("Неверный телефон или пароль")

        # Сотрудник: либо суперпользователь (админ), либо привязан к Master
        if not user.is_superuser:
            if not hasattr(user, "master_profile"):
                raise forms.ValidationError(
                    "У вас нет прав сотрудника. Обратитесь к администратору."
                )

        cleaned_data["user"] = user
        return cleaned_data

def normalize_phone(value):
    digits = re.sub(r"\D", "", value or "")

    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]

    if len(digits) != 11 or not digits.startswith("7"):
        raise forms.ValidationError(
            "Введите номер в формате +7 (999) 123-45-67"
        )

    return "+" + digits


class RegisterForm(forms.Form):
    phone = forms.CharField(max_length=20)
    email = forms.EmailField()
    password = forms.CharField(min_length=6, widget=forms.PasswordInput)

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])

        if User.objects.filter(username=phone).exists():
            raise forms.ValidationError(
                "Пользователь с таким телефоном уже зарегистрирован"
            )

        return phone

    def save(self):
        return User.objects.create_user(
            username=self.cleaned_data["phone"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
        )


class LoginForm(forms.Form):
    phone = forms.CharField(max_length=20)
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        phone = cleaned_data.get("phone")
        password = cleaned_data.get("password")

        if not phone or not password:
            return cleaned_data

        try:
            phone = normalize_phone(phone)
        except forms.ValidationError as error:
            self.add_error("phone", error)
            return cleaned_data

        user = authenticate(username=phone, password=password)

        if user is None:
            raise forms.ValidationError("Неверный телефон или пароль")

        cleaned_data["user"] = user
        return cleaned_data


class ProfileForm(forms.Form):
    name = forms.CharField(max_length=150, required=False, label="Имя")
    email = forms.EmailField(required=False, label="Email")
    phone = forms.CharField(max_length=20, label="Телефон")

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        qs = User.objects.filter(username=phone)
        if self.user is not None:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError(
                "Этот номер уже занят другим пользователем"
            )
        return phone

    def save(self):
        user = self.user
        user.first_name = self.cleaned_data["name"]
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["phone"]
        user.save()
        return user


class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ["brand", "model", "year", "mileage", "plate"]

    def clean_year(self):
        year = self.cleaned_data["year"]
        if year and (year < 1900 or year > 2100):
            raise forms.ValidationError("Введите реальный год выпуска")
        return year


class AppointmentForm(forms.Form):
    master = forms.ModelChoiceField(
        queryset=Master.objects.filter(is_active=True),
        label="Мастер",
        empty_label="Выберите мастера",
        widget=forms.Select(attrs={"class": "checkout-select", "id": "id_master"}),
    )
    car = forms.ModelChoiceField(
        queryset=Car.objects.none(),
        label="Автомобиль",
        empty_label="Выберите авто",
        widget=forms.Select(attrs={"class": "checkout-select", "id": "id_car"}),
    )
    date = forms.DateField(
        label="Дата",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "checkout-input",
                "id": "id_date",
                "min": date_cls.today().isoformat(),
            }
        ),
    )
    time = forms.ChoiceField(
        choices=TIME_SLOTS,
        label="Время",
        widget=forms.Select(attrs={"class": "checkout-select", "id": "id_time"}),
    )

    def __init__(self, *args, user=None, services=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.services = list(services or [])
        if user is not None:
            self.fields["car"].queryset = Car.objects.filter(owner=user)

    def clean_date(self):
        value = self.cleaned_data["date"]
        if value < date_cls.today():
            raise forms.ValidationError("Дата не может быть в прошлом")
        if value.weekday() >= 5:
            raise forms.ValidationError("Мы работаем только по будням (пн-пт)")
        return value

    def clean(self):
        cleaned = super().clean()
        master = cleaned.get("master")
        d = cleaned.get("date")
        time_str = cleaned.get("time")

        if not (master and d and time_str):
            return cleaned

        duration = sum(s.duration for s in self.services)
        start_t = datetime.strptime(time_str, "%H:%M").time()
        start_dt = datetime.combine(d, start_t)
        end_dt = start_dt + timedelta(minutes=duration)

        slot_end = SLOT_ENDS[time_str]
        slot_end_dt = datetime.combine(
            d, datetime.strptime(slot_end, "%H:%M").time()
        )

        if end_dt > slot_end_dt:
            raise forms.ValidationError(
                f"Услуги ({duration} мин) не помещаются в слот "
                f"{time_str}–{slot_end}. Выберите другой слот."
            )

        # FR-13: исключение пересечения записей
        appointments = Appointment.objects.filter(
            master=master, date=d
        ).exclude(status__name__iexact="Отменена")

        for appt in appointments:
            appt_start = datetime.combine(appt.date, appt.time)
            appt_end = appt_start + timedelta(minutes=appt.total_duration or 0)
            if start_dt < appt_end and end_dt > appt_start:
                raise forms.ValidationError(
                    f"Мастер занят: у него запись с "
                    f"{appt.time.strftime('%H:%M')}. Выберите другое время."
                )

        cleaned["duration"] = duration
        cleaned["start_time"] = start_t
        return cleaned