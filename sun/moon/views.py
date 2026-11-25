from datetime import datetime, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

from .forms import (
    SLOT_ENDS,
    TIME_SLOTS,
    AppointmentForm,
    CarForm,
    LoginForm,
    ProfileForm,
    RegisterForm,
    StaffLoginForm,
)
from .models import (
    Appointment,
    AppointmentService,
    AppointmentStatus,
    Car,
    Master,
    Service,
)

import logging

logger = logging.getLogger('app')


# =========================================================
# Кастомные страницы ошибок + логирование
# =========================================================

def custom_403(request, exception=None):
    logger.warning(
        "HTTP 403 | %s %s | user=%s | IP=%s",
        request.method, request.path,
        request.user if request.user.is_authenticated else 'аноним',
        request.META.get('REMOTE_ADDR'),
    )
    return render(request, '403.html', status=403)


def custom_404(request, exception=None):
    logger.warning(
        "HTTP 404 | %s %s | user=%s | IP=%s",
        request.method, request.path,
        request.user if request.user.is_authenticated else 'аноним',
        request.META.get('REMOTE_ADDR'),
    )
    return render(request, '404.html', status=404)


def custom_500(request):
    # Тело исключения сюда не попадает, но django.request его залогирует.
    logger.error(
        "HTTP 500 | %s %s | user=%s | IP=%s",
        request.method, request.path,
        request.user if request.user.is_authenticated else 'аноним',
        request.META.get('REMOTE_ADDR'),
    )
    return render(request, '500.html', status=500)


# =========================================================
# Основные страницы
# =========================================================

def main(request):
    return TemplateResponse(request, 'main.html')


def history(request):
    return TemplateResponse(request, 'history.html')


def vhod(request):
    if request.user.is_authenticated:
        return _redirect_to_profile(request.user)

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            login(
                request,
                form.cleaned_data["user"],
                backend="django.contrib.auth.backends.ModelBackend",
            )
            logger.info(
                "Вход | user=%s | IP=%s",
                form.cleaned_data["user"].username,
                request.META.get('REMOTE_ADDR'),
            )
            return _redirect_to_profile(form.cleaned_data["user"])
        messages.error(request, "Неверный телефон или пароль")
        logger.warning(
            "Неудачный вход | phone=%s | IP=%s",
            request.POST.get('username') or request.POST.get('phone'),
            request.META.get('REMOTE_ADDR'),
        )
    else:
        form = LoginForm()

    return render(request, "vhod.html", {"form": form})


def registracia(request):
    if request.user.is_authenticated:
        return _redirect_to_profile(request.user)

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                login(
                    request,
                    user,
                    backend="django.contrib.auth.backends.ModelBackend",
                )
                messages.success(request, "Регистрация выполнена")
                logger.info("Регистрация | user=%s", user.username)
                return _redirect_to_profile(user)
            except Exception as e:
                logger.error("Ошибка регистрации | %s", e, exc_info=True)
                messages.error(request, "Не удалось создать аккаунт. Попробуйте позже.")
        else:
            messages.error(request, "Проверьте введённые данные")
            logger.warning("Ошибки валидации регистрации | %s", form.errors.as_json())
    else:
        form = RegisterForm()

    return render(request, "registracia.html", {"form": form})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        logger.info("Выход | user=%s", request.user.username)
    logout(request)
    return redirect("main")


@login_required(login_url="vhod")
def profil(request):
    if request.user.is_superuser or hasattr(request.user, "master_profile"):
        return redirect("profil_sotr")

    if request.method == "POST":
        form = ProfileForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Данные профиля обновлены")
                logger.info("Профиль обновлён | user=%s", request.user.username)
                return redirect("profil")
            except Exception as e:
                logger.error("Ошибка сохранения профиля | user=%s | %s", request.user.username, e, exc_info=True)
                messages.error(request, "Не удалось сохранить изменения.")
        else:
            messages.error(request, "Проверьте введённые данные")
            logger.warning("Ошибки валидации профиля | user=%s", request.user.username)
    else:
        form = ProfileForm(
            initial={
                "name": request.user.first_name,
                "email": request.user.email,
                "phone": request.user.username,
            },
            user=request.user,
        )

    return render(request, "profil.html", {"form": form})


@login_required(login_url="vhod")
def moi_garaje(request):
    cars = request.user.cars.all()
    form = None
    open_modal = False

    if request.method == "POST":
        car_id = (request.POST.get("car_id") or "").strip()
        instance = None
        if car_id:
            instance = get_object_or_404(Car, pk=car_id, owner=request.user)

        form = CarForm(request.POST, instance=instance)
        if form.is_valid():
            try:
                car = form.save(commit=False)
                car.owner = request.user
                car.save()
                messages.success(
                    request,
                    "Данные автомобиля обновлены" if instance else "Автомобиль добавлен",
                )
                logger.info(
                    "%s | user=%s | car_id=%s",
                    "Автомобиль обновлён" if instance else "Автомобиль добавлен",
                    request.user.username, car.pk,
                )
                return redirect("moi_garaje")
            except Exception as e:
                logger.error("Ошибка сохранения автомобиля | user=%s | %s", request.user.username, e, exc_info=True)
                messages.error(request, "Не удалось сохранить данные автомобиля.")

        open_modal = True
        messages.error(request, "Проверьте введённые данные")
        logger.warning("Ошибки валидации авто | user=%s | %s", request.user.username, form.errors.as_json() if form else '')

    return render(
        request,
        "moi_garaje.html",
        {"cars": cars, "form": form, "open_modal": open_modal},
    )


# =========================================================
# Услуги и корзина
# =========================================================

def _get_cart_services(request):
    cart = request.session.get("cart") or []
    return list(Service.objects.filter(id__in=cart))


def _cart_totals(services):
    total_cost = sum(s.price for s in services)
    total_duration = sum(s.duration for s in services)
    hours = total_duration // 60
    minutes = total_duration % 60
    if hours and minutes:
        duration_display = f"{hours} ч {minutes} мин"
    elif hours:
        duration_display = f"{hours} ч"
    else:
        duration_display = f"{minutes} мин"
    return total_cost, total_duration, duration_display


def uslugi(request):
    if request.method == "POST":
        selected_ids = request.POST.getlist("service")
        if not selected_ids:
            messages.warning(request, "Выберите хотя бы одну услугу")
            logger.warning("Корзина: не выбрано ни одной услуги | user=%s", request.user)
            return redirect("uslugi")

        request.session["cart"] = [int(sid) for sid in selected_ids if sid.isdigit()]
        request.session.modified = True
        logger.info("Корзина сформирована | user=%s | services=%s", request.user, request.session["cart"])
        return redirect("oformlenie_zapisi")

    query = (request.GET.get("q") or "").strip()
    selected_categories = request.GET.getlist("category")

    services = Service.objects.all()
    if query:
        services = services.filter(name__icontains=query)
    if selected_categories:
        services = services.filter(category__in=selected_categories)
    services = services.order_by("name")

    cart_services = _get_cart_services(request)
    total_cost, total_duration, duration_display = _cart_totals(cart_services)

    return render(
        request,
        "uslugi.html",
        {
            "services": services,
            "cart_services": cart_services,
            "cart_ids": {s.id for s in cart_services},
            "query": query,
            "selected_categories": set(selected_categories),
            "category_choices": Service.CATEGORY_CHOICES,
            "total_cost": total_cost,
            "total_duration": total_duration,
            "duration_display": duration_display,
        },
    )


@require_POST
def add_to_cart(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    cart = request.session.get("cart") or []
    if service.id not in cart:
        cart.append(service.id)
        request.session["cart"] = cart
        request.session.modified = True
    return redirect("uslugi")


@require_POST
def remove_from_cart(request, service_id):
    cart = request.session.get("cart") or []
    if service_id in cart:
        cart.remove(service_id)
        request.session["cart"] = cart
        request.session.modified = True
    return redirect("uslugi")


@require_POST
def clear_cart(request):
    request.session["cart"] = []
    request.session.modified = True
    return redirect("uslugi")


def mastera(request):
    masters = Master.objects.filter(is_active=True).prefetch_related("specializations")
    return render(request, "mastera.html", {"masters": masters})


def available_slots(request):
    master_id = request.GET.get("master")
    date_str = request.GET.get("date")
    if not (master_id and date_str):
        return JsonResponse({"slots": []})

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        master = Master.objects.get(pk=master_id)
    except (ValueError, Master.DoesNotExist) as e:
        logger.warning("available_slots: неверные параметры | master=%s | date=%s | %s", master_id, date_str, e)
        return JsonResponse({"slots": []})

    cart = request.session.get("cart") or []
    services = list(Service.objects.filter(id__in=cart))
    duration = sum(s.duration for s in services)

    if date_obj.weekday() >= 5:
        return JsonResponse({"slots": []})

    existing = Appointment.objects.filter(
        master=master, date=date_obj
    ).exclude(status__name__iexact="Отменена")

    slots = []
    for start_str, label in TIME_SLOTS:
        start_t = datetime.strptime(start_str, "%H:%M").time()
        end_str = SLOT_ENDS[start_str]
        end_t = datetime.strptime(end_str, "%H:%M").time()

        start_dt = datetime.combine(date_obj, start_t)
        end_dt = start_dt + timedelta(minutes=duration)
        slot_end_dt = datetime.combine(date_obj, end_t)

        if end_dt > slot_end_dt:
            continue

        busy = False
        for appt in existing:
            appt_start = datetime.combine(appt.date, appt.time)
            appt_end = appt_start + timedelta(minutes=appt.total_duration or 0)
            if start_dt < appt_end and end_dt > appt_start:
                busy = True
                break

        if not busy:
            slots.append({"value": start_str, "label": label})

    return JsonResponse({"slots": slots})


# =========================================================
# Запись на услуги
# =========================================================

@login_required(login_url="vhod")
def oformlenie_zapisi(request):
    master_param = request.GET.get("master")
    if master_param and master_param.isdigit():
        request.session["selected_master"] = int(master_param)
        request.session.modified = True

    services = _get_cart_services(request)
    if not services:
        messages.warning(request, "Сначала выберите хотя бы одну услугу")
        return redirect("uslugi")

    total_cost, total_duration, duration_display = _cart_totals(services)
    masters = Master.objects.filter(is_active=True).prefetch_related("specializations")

    if request.method == "POST":
        form = AppointmentForm(request.POST, user=request.user, services=services)
        if form.is_valid():
            try:
                with transaction.atomic():
                    status, _ = AppointmentStatus.objects.get_or_create(
                        name="Новая", defaults={"description": "Только что создана"}
                    )
                    appointment = Appointment.objects.create(
                        client=request.user,
                        car=form.cleaned_data["car"],
                        master=form.cleaned_data["master"],
                        date=form.cleaned_data["date"],
                        time=form.cleaned_data["start_time"],
                        total_cost=total_cost,
                        total_duration=total_duration,
                        status=status,
                    )
                    for service in services:
                        AppointmentService.objects.create(
                            appointment=appointment,
                            service=service,
                            agreed_price=service.price,
                            agreed_duration=service.duration,
                        )
                request.session["cart"] = []
                request.session.pop("selected_master", None)
                request.session.modified = True

                messages.success(request, "Запись успешно создана")
                logger.info(
                    "Запись создана | appt_id=%s | user=%s | master=%s | total=%s",
                    appointment.pk, request.user.username,
                    appointment.master_id, total_cost,
                )
                return redirect("moi_zapis")
            except Exception as e:
                logger.error("Ошибка создания записи | user=%s | %s", request.user.username, e, exc_info=True)
                messages.error(request, "Не удалось создать запись. Попробуйте позже.")
        else:
            messages.error(request, "Проверьте введённые данные")
            logger.warning("Ошибки валидации записи | user=%s | %s", request.user.username, form.errors.as_json())
    else:
        initial = {}
        selected_master_id = request.session.get("selected_master")
        if selected_master_id and Master.objects.filter(pk=selected_master_id, is_active=True).exists():
            initial["master"] = selected_master_id
        form = AppointmentForm(user=request.user, services=services, initial=initial)

    return render(
        request,
        "oformlenie_zapisi.html",
        {
            "form": form,
            "services": services,
            "masters": masters,
            "total_cost": total_cost,
            "total_duration": total_duration,
            "duration_display": duration_display,
        },
    )


@login_required(login_url="vhod")
def moi_zapis(request):
    appointments = (
        Appointment.objects.filter(client=request.user)
        .select_related("master", "car", "status")
        .prefetch_related("services__service")
        .order_by("-date", "-time")
    )
    return render(request, "moi_zapis.html", {"appointments": appointments})


@login_required(login_url="vhod")
@require_POST
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id, client=request.user)

    if appointment.status.name.lower() in ("отменена", "выполнена"):
        messages.warning(request, "Эту запись нельзя отменить")
        logger.warning("Попытка отменить закрытую запись | appt=%s | user=%s", appointment_id, request.user.username)
        return redirect("moi_zapis")

    try:
        cancelled, _ = AppointmentStatus.objects.get_or_create(
            name="Отменена", defaults={"description": "Отменена клиентом"}
        )
        appointment.status = cancelled
        appointment.save(update_fields=["status"])
        messages.success(request, "Запись отменена")
        logger.info("Запись отменена | appt=%s | user=%s", appointment_id, request.user.username)
    except Exception as e:
        logger.error("Ошибка отмены записи | appt=%s | %s", appointment_id, e, exc_info=True)
        messages.error(request, "Не удалось отменить запись.")

    return redirect("moi_zapis")


# =========================================================
# Сотрудники (мастер / админ)
# =========================================================

def _is_staff_user(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return hasattr(user, "master_profile")


def master_required(view_func):
    @wraps(view_func)
    @login_required(login_url="vhod_sotr")
    def wrapper(request, *args, **kwargs):
        if not _is_staff_user(request.user):
            raise PermissionDenied("Доступ только для сотрудников")
        return view_func(request, *args, **kwargs)
    return wrapper


def vhod_sotr(request):
    if request.user.is_authenticated and _is_staff_user(request.user):
        return redirect("zapisi_mastera")

    if request.method == "POST":
        form = StaffLoginForm(request.POST)
        if form.is_valid():
            login(
                request,
                form.cleaned_data["user"],
                backend="django.contrib.auth.backends.ModelBackend",
            )
            messages.success(request, "Вы вошли как сотрудник")
            logger.info("Вход сотрудника | user=%s", form.cleaned_data["user"].username)
            return redirect("zapisi_mastera")
        messages.error(request, "Неверный телефон или пароль")
        logger.warning("Неудачный вход сотрудника | IP=%s", request.META.get('REMOTE_ADDR'))
    else:
        form = StaffLoginForm()

    return render(request, "vhod_sotr.html", {"form": form})


@master_required
def zapisi_mastera(request):
    if request.user.is_superuser:
        appointments = Appointment.objects.all()
    else:
        appointments = Appointment.objects.filter(master=request.user.master_profile)

    appointments = (
        appointments
        .select_related("client", "car", "master", "status")
        .prefetch_related("services__service")
        .order_by("date", "time")
    )
    return render(request, "zapisi_mastera.html", {"appointments": appointments})


def _redirect_to_profile(user):
    if user.is_superuser or hasattr(user, "master_profile"):
        return redirect("profil_sotr")
    return redirect("profil")


@master_required
def profil_sotr(request):
    master = getattr(request.user, "master_profile", None)
    return render(request, "profil_sotr.html", {"master": master})


@master_required
@require_POST
def confirm_appointment(request, appointment_id):
    qs = Appointment.objects.all()
    if not request.user.is_superuser:
        qs = qs.filter(master=request.user.master_profile)

    appointment = get_object_or_404(qs, pk=appointment_id)

    if appointment.status.name.lower() in ("отменена", "выполнена"):
        messages.warning(request, "Эту запись нельзя подтвердить")
        logger.warning("Попытка подтвердить закрытую запись | appt=%s | user=%s", appointment_id, request.user.username)
        return redirect("zapisi_mastera")

    try:
        confirmed, _ = AppointmentStatus.objects.get_or_create(
            name="Подтверждена", defaults={"description": "Подтверждена мастером"}
        )
        appointment.status = confirmed
        appointment.save(update_fields=["status"])
        messages.success(request, "Запись подтверждена")
        logger.info("Запись подтверждена | appt=%s | by=%s", appointment_id, request.user.username)
    except Exception as e:
        logger.error("Ошибка подтверждения записи | appt=%s | %s", appointment_id, e, exc_info=True)
        messages.error(request, "Не удалось подтвердить запись.")

    return redirect("zapisi_mastera")