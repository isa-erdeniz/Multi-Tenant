"""
FAZ 24: REST API view'ları.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.wardrobe.models import Garment
from apps.tryon.models import TryOnSession


class TryOnViewSet(views.APIView):
    """Try-On API — APIView POST ile oturum oluşturur (ViewSet.create değil)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Yeni try-on oturumu başlat (multipart fotoğraf akışı web UI'da)."""
        garment_id = request.data.get("garment_id")
        if not garment_id:
            return Response(
                {"error": "garment_id gerekli"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            garment = Garment.objects.get(pk=garment_id, user=request.user)
        except Garment.DoesNotExist:
            return Response(
                {"error": "Kıyafet bulunamadı"},
                status=status.HTTP_404_NOT_FOUND
            )
        session = TryOnSession.objects.create(
            user=request.user,
            garment=garment,
            status="pending",
        )
        return Response({
            "session_id": str(session.pk),
            "status": session.status,
        }, status=status.HTTP_201_CREATED)


class WardrobeViewSet(views.APIView):
    """Gardırop API."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Kullanıcının kıyafetlerini listele."""
        garments = Garment.objects.filter(user=request.user, is_active=True)
        data = [
            {"id": g.pk, "name": g.name, "category": g.category.name if g.category else None}
            for g in garments[:50]
        ]
        return Response(data)

    def post(self, request):
        """Yeni kıyafet ekle."""
        return Response(
            {"message": "Fotoğraf yükleme ile eklenir"},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


class AccountView(views.APIView):
    """Hesap bilgisi."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Profil özeti."""
        user = request.user
        return Response({
            "email": user.email,
            "subscription": getattr(
                getattr(user, "subscription", None), "status", None
            ),
        })
