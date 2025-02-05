from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('imprimir-recibo/<int:pedido_id>/', views.imprimir_recibo, name='imprimir_recibo'),
    path('meu-pedido/', views.meu_pedido, name='order-track'),
    path('meu-pedido/<int:pedido_id>', views.meu_pedido_details, name='order-details'),
]
