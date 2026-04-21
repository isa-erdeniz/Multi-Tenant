"""Yasal bilgilendirme sayfaları (iyzico / tüketici mevzuatı uyumu)."""

from django.shortcuts import render


def mesafeli_satis_view(request):
    return render(request, "legal/mesafeli_satis.html")


def iptal_iade_view(request):
    return render(request, "legal/iptal_iade.html")


def gizlilik_view(request):
    return render(request, "legal/gizlilik.html")


def kvkk_view(request):
    return render(request, "legal/kvkk.html")


def hakkimizda_view(request):
    return render(request, "legal/hakkimizda.html")
