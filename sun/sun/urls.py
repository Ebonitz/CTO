"""
URL configuration for sun project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from moon import views

handler403 = 'moon.views.custom_403'
handler404 = 'moon.views.custom_404'
handler500 = 'moon.views.custom_500'

urlpatterns = [
    path('admin/', admin.site.urls),
    
    
    path("history/", views.history, name="history"),
    path("vhod/", views.vhod, name="vhod"),
    path("logout/", views.logout_view, name="logout"),
    path("registracia/", views.registracia, name="registracia"),
    path("profil/", views.profil, name="profil"),

    path("moi_garaje/", views.moi_garaje, name="moi_garaje"),

    path("uslugi/", views.uslugi, name="uslugi"),
    path("uslugi/add/<int:service_id>/", views.add_to_cart, name="add_to_cart"),
    path("uslugi/remove/<int:service_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("uslugi/clear/", views.clear_cart, name="clear_cart"),

    path("mastera/", views.mastera, name="mastera"),

    path("api/slots/", views.available_slots, name="available_slots"),

    path("oformlenie_zapisi/", views.oformlenie_zapisi, name="oformlenie_zapisi"),

    path("moi_zapis/", views.moi_zapis, name="moi_zapis"),
    path("moi_zapis/cancel/<int:appointment_id>/", views.cancel_appointment, name="cancel_appointment"),

    path("vhod_sotr/", views.vhod_sotr, name="vhod_sotr"),
    path("zapisi_mastera/", views.zapisi_mastera, name="zapisi_mastera"),
    path(
        "zapisi_mastera/confirm/<int:appointment_id>/",
        views.confirm_appointment,
        name="confirm_appointment",
    ),
    path("profil_sotr/", views.profil_sotr, name="profil_sotr"),
    
    path('', views.main, name="main"),
]