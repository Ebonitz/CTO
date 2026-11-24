from django.shortcuts import render
from django.template.response import TemplateResponse
from django.http.response import HttpResponseRedirect

def main(request):
    return TemplateResponse(request, 'main.html')

def history(request):
    return TemplateResponse(request, 'history.html')

def mastera(request):
    return TemplateResponse(request, 'mastera.html')

def vhod(request):
    return TemplateResponse(request, 'vhod.html')

def uslugi(request):
    return TemplateResponse(request, 'uslugi.html')

def registracia(request):
    return TemplateResponse(request, 'registracia.html')

def profil(request):
    return TemplateResponse(request, 'profil.html')

def moi_garaje(request):
    return TemplateResponse(request, 'moi_garaje.html')

def moi_zapis(request):
    return TemplateResponse(request, 'moi_zapis.html')

def oformlenie_zapisi(request):
    return TemplateResponse(request, 'oformlenie_zapisi.html')

def vhod_sotr(request):
    return TemplateResponse(request, 'vhod_sotr.html')

def zapisi_mastera(request):
    return TemplateResponse(request, 'zapisi_mastera.html')

def profil_sotr(request):
    return TemplateResponse(request, 'profil_sotr.html')
