from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Appointment,
    AppointmentService,
    AppointmentStatus,
    Car,
    Master,
    Profile,
    Service,
    Specialization,
)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name = "Профиль"
    verbose_name_plural = "Профиль"
    fk_name = "user"


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = (
        "username", "email", "first_name", "last_name",
        "is_staff", "is_active",
    )
    list_filter = ("is_staff", "is_active", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone")
    search_fields = ("user__username", "phone")
    list_select_related = ("user",)


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = (
        "brand", "model", "year", "plate", "mileage", "owner", "created_at",
    )
    list_filter = ("brand", "year")
    search_fields = ("brand", "model", "plate", "owner__username")
    autocomplete_fields = ("owner",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "duration")
    list_filter = ("category",)
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "phone", "user", "is_active")
    list_filter = ("is_active", "specializations")
    search_fields = ("last_name", "first_name", "phone", "user__username")
    filter_horizontal = ("specializations",)
    autocomplete_fields = ("user",)
    ordering = ("last_name", "first_name")


@admin.register(AppointmentStatus)
class AppointmentStatusAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


class AppointmentServiceInline(admin.TabularInline):
    model = AppointmentService
    extra = 1
    autocomplete_fields = ("service",)
    fields = ("service", "agreed_price", "agreed_duration")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "client", "car", "master", "date", "time",
        "total_cost", "total_duration", "status",
    )
    list_filter = ("status", "date", "master")
    search_fields = (
        "client__username", "car__plate",
        "master__last_name", "master__first_name",
    )
    date_hierarchy = "date"
    autocomplete_fields = ("client", "car", "master", "status")
    readonly_fields = ("total_cost", "total_duration")
    inlines = [AppointmentServiceInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        appointment = form.instance
        total_cost = sum(item.agreed_price for item in appointment.services.all())
        total_duration = sum(item.agreed_duration for item in appointment.services.all())
        if (
            appointment.total_cost != total_cost
            or appointment.total_duration != total_duration
        ):
            appointment.total_cost = total_cost
            appointment.total_duration = total_duration
            appointment.save(update_fields=["total_cost", "total_duration"])


@admin.register(AppointmentService)
class AppointmentServiceAdmin(admin.ModelAdmin):
    list_display = (
        "appointment", "service", "agreed_price", "agreed_duration",
    )
    autocomplete_fields = ("appointment", "service")
    search_fields = ("appointment__id", "service__name")

    def _recalc(self, appointment):
        total_cost = sum(item.agreed_price for item in appointment.services.all())
        total_duration = sum(item.agreed_duration for item in appointment.services.all())
        appointment.total_cost = total_cost
        appointment.total_duration = total_duration
        appointment.save(update_fields=["total_cost", "total_duration"])

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self._recalc(obj.appointment)

    def delete_model(self, request, obj):
        appointment = obj.appointment
        super().delete_model(request, obj)
        self._recalc(appointment)