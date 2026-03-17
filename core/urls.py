from django.contrib import admin
from django.urls import path
from django.urls import include
from app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('home/', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('', views.none, name='none'),
    path('add/', views.addcliet, name='addcliet'),
    path('d7s87d/', views.add_planilha, name='add-planilha'),
    path('api/webhook/', views.receber, name='webhook'),
    path('atualizar_servico/', views.atualizar_servico, name='atualizar_servico'),
]
