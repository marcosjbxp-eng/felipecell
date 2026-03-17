from django.db.models.signals import pre_save
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from django.core.files.base import ContentFile
import requests
import cloudinary.uploader
from .models import CustomUser

# 1. PEGAR FOTO DO GOOGLE NO CADASTRO
@receiver(user_signed_up)
def populate_profile(request, user, **kwargs):
    if user.foto:
        return # Se já tiver foto, não faz nada

    # Tenta pegar dados do Google
    sociallogin = kwargs.get('sociallogin')
    if sociallogin and sociallogin.account.provider == 'google':
        # O Google retorna a URL da foto no campo 'picture'
        picture_url = sociallogin.account.extra_data.get('picture')
        
        if picture_url:
            try:
                # Baixa a imagem do Google
                response = requests.get(picture_url)
                if response.status_code == 200:
                    # Salva no campo foto do usuário
                    # O nome 'avatar.jpg' é temporário, o Cloudinary renomeia
                    user.foto.save(f'{user.username}_google.jpg', ContentFile(response.content))
                    user.save()
            except Exception as e:
                print(f"Erro ao baixar foto do Google: {e}")

# 2. APAGAR FOTO ANTIGA AO TROCAR (Evita lixo no Cloudinary)
@receiver(pre_save, sender=CustomUser)
def delete_old_image(sender, instance, **kwargs):
    if not instance.pk:
        return False # É criação nova, não tem o que apagar

    try:
        old_user = CustomUser.objects.get(pk=instance.pk)
    except CustomUser.DoesNotExist:
        return False

    # Compara se a foto mudou e se a antiga existia
    new_foto = instance.foto
    old_foto = old_user.foto

    if old_foto and new_foto != old_foto:
        # Apaga a antiga do Cloudinary usando o public_id
        cloudinary.uploader.destroy(old_foto.public_id)