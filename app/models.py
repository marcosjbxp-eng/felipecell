from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField
from django.templatetags.static import static

class CustomUser(AbstractUser):
    # Campo da foto no Cloudinary
    foto = CloudinaryField('imagem', folder='usuarios', blank=True, null=True)

    def __str__(self):
        return self.username

    @property
    def get_foto_url(self):
        """
        Essa função verifica:
        1. Se o usuário tem foto -> Retorna a URL do Cloudinary otimizada.
        2. Se NÃO tem foto -> Retorna o caminho da imagem padrão (static/img/default.png).
        """
        if self.foto:
            # Gera a URL com transformações (crop, qualidade auto, etc)
            return self.foto.build_url(
                width=1000, 
                crop="scale", 
                quality="auto", 
                fetch_format="auto"
            )
        
        # Caminho para a imagem padrão na pasta static
        # Certifique-se de ter salvo a imagem em: app/static/img/default.png
        return static('img/default.png')