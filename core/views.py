from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.http import HttpResponse, HttpResponseBadRequest
from .models import Pedido, Cliente, Lavandaria, ItemPedido
import json
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from django.utils.timezone import now, timedelta
from django.db import models
from reportlab.lib.pagesizes import portrait
from reportlab.pdfgen import canvas
from io import BytesIO
import logging
logger = logging.getLogger(__name__)


# Calcular a data inicial e o intervalo de 7 dias
data_inicial = now().date() - timedelta(days=6)
datas_intervalo = [(data_inicial + timedelta(days=i)) for i in range(7)]


# def imprimir_recibo(request, pedido_id):
#     pedido = get_object_or_404(Pedido, id=pedido_id)
#     recibo_content = render_to_string('core/recibo_termico.txt', {'pedido': pedido})
#
#     response = HttpResponse(recibo_content, content_type="text/plain; charset=utf-8")
#     response['Content-Disposition'] = f'inline; filename="recibo_pedido_{pedido.id}.txt"'
#     return response

def imprimir_recibo(request, pedido_id):
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        buffer = BytesIO()
        width, height = 220, 600  # Tamanho de recibo fiscal
        p = canvas.Canvas(buffer, pagesize=(width, height))

        y = height - 20  # Posição inicial do cursor

        # Cabeçalho
        p.setFont("Helvetica", 8)
        p.drawCentredString(width / 2, y, "POWER WASHING LTDA")
        y -= 30
        p.drawCentredString(width / 2, y, "401426310")
        y -= 30
        p.drawCentredString(width / 2, y, "AV. Samora Machel")
        y -= 30
        p.drawCentredString(width / 2, y, "Matola")
        y -= 30

        # Informações do pedido
        p.setFont("Helvetica", 8)
        p.drawString(10, y, f"Pedido: {pedido.id}")
        y -= 30
        p.drawString(10, y, f"Cliente: {pedido.cliente.nome}")
        y -= 30
        p.drawString(10, y, f"Lavandaria: {pedido.lavandaria.nome}")
        y -= 30
        p.drawString(10, y, f"Data: {pedido.criado_em.strftime('%d/%m/%Y %H:%M')}")
        y -= 30

        # Itens do Pedido
        p.drawString(10, y, "Itens do Pedido:")
        y -= 30
        for item in pedido.itens.all():
            p.drawString(10, y, f"{item.quantidade}x {item.item_de_servico.nome} - {item.preco_total:.2f} MZN")
            y -= 30




        # Totais e status
        p.drawString(10, y, f"Total: {pedido.total:.2f} MZN")
        y -= 30
        p.drawString(10, y, f"Pago: {'Sim' if pedido.pago else 'Não'}")
        y -= 30

        # Rodapé
        p.setFont("Helvetica", 7)
        # p.drawCentredString(width / 2, y, "Obrigado por sua compra!")

        p.showPage()
        p.save()

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="recibo_pedido_{pedido.id}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Erro ao gerar recibo: {e}")
        return HttpResponse("Erro ao gerar recibo.", status=500)


def meu_pedido(request):
    if request.method == 'POST':
        pedido_id = request.POST.get('pedido_id')

        if not pedido_id:
            return HttpResponseBadRequest("Pedido ID não fornecido.")

        return redirect(reverse('core:order-details', args=[pedido_id]))

    return render(request, 'core/order_tracking_form.html')


def meu_pedido_details(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    itens_pedidos = ItemPedido.objects.filter(pedido=pedido)

    return render(request, 'core/order_details.html', {'pedido': pedido, 'itens_pedidos': itens_pedidos})


# def download_recibo(request, pedido_id):
#     # Obtenha o pedido pelo ID
#     pedido = get_object_or_404(Pedido, id=pedido_id)
#
#     # Crie um buffer para armazenar o PDF
#     buffer = BytesIO()
#
#     # Crie o objeto PDF, usando o buffer como seu "arquivo"
#     p = canvas.Canvas(buffer)
#
#     # Adicione conteúdo ao PDF
#     p.drawString(100, 750, f"Recibo do Pedido #{pedido.id}")
#     p.drawString(100, 730, f"Lavandaria: {pedido.lavandaria.nome}")
#     p.drawString(100, 710, f"Funcionário: {pedido.funcionario.user.last_name}")
#     p.drawString(100, 690, f"Estado: {pedido.status}")
#     p.drawString(100, 670, f"Total: {pedido.total} MZN")
#     p.drawString(100, 650, f"Cliente: {pedido.cliente.nome}")
#     p.drawString(100, 630, f"Data: {pedido.criado_em.strftime('%d-%m-%Y')}")
#
#     # Adicione os itens do pedido
#     y = 610
#     for item in pedido.itens.all():  # Corrigido: pedido.itens.all()
#         p.drawString(100, y, f"Item: {item.item_de_servico.nome}")  # Corrigido: item.item_de_servico.nome
#         p.drawString(100, y - 20, f"Serviço: {item.servico.nome}")  # Corrigido: item.servico.nome
#         p.drawString(100, y - 40, f"Quantidade: {item.quantidade}")
#         p.drawString(100, y - 60, f"Preço: {item.preco_total} MZN")
#         y -= 80
#
#     # Finalize o PDF
#     p.showPage()
#     p.save()
#
#     # Obtenha o valor do buffer e feche-o
#     pdf = buffer.getvalue()
#     buffer.close()
#
#     # Crie a resposta HTTP com o PDF
#     response = HttpResponse(pdf, content_type='application/pdf')
#     response['Content-Disposition'] = f'attachment; filename="recibo_pedido_{pedido.id}.pdf"'
#
#     return response


def dashboard_callback(request, context):
    total_pedidos = Pedido.objects.all().count()
    pedidos_nao_pagos = Pedido.objects.filter(pago=False).count()
    total_clientes = Cliente.objects.all().count()

    pedidos_pagos = Pedido.objects.filter(pago=True)

    # Calculando os pedidos e vendas por dia
    pedidos_por_dia = pedidos_pagos.filter(
        criado_em__date__gte=data_inicial
    ).annotate(
        data=TruncDate('criado_em')
    ).values('data').annotate(
        total_pedidos=Count('id'),
        total_vendas=Sum('total')  # Soma total sem conflito
    )

    # Dicionário de pedidos por data
    pedidos_dict = {str(p['data']): p['total_pedidos'] for p in pedidos_por_dia}
    # Dicionário de vendas por data, convertendo Decimal para float
    vendas_dict = {str(p['data']): float(p['total_vendas'] or 0) for p in pedidos_por_dia}

    labels = [str(data) for data in datas_intervalo]
    data_pedidos = [pedidos_dict.get(str(data), 0) for data in datas_intervalo]
    data_vendas = [vendas_dict.get(str(data), 0) for data in datas_intervalo]

    lavandarias = Lavandaria.objects.annotate(
        numero_pedidos=Count('pedidos'),
        total_vendas=Sum('pedidos__total', filter=models.Q(pedidos__pago=True))  # Somente pedidos pagos
    )

    total_vendas = Pedido.objects.filter(pago=True).aggregate(Sum('total'))['total__sum']

    context.update(
        {
            "kpis": [
                {
                    "title": "Total orders",
                    "metric": pedidos_nao_pagos,
                },
                {
                    "title": "Total sales",
                    "metric": str(float(total_vendas or 0)) + ' MZN',  # Convertendo para float
                },
                {
                    "title": "Total unpaid invoices",
                    "metric": total_pedidos,
                },
                {
                    "title": "Total Active Customers",
                    "metric": total_clientes,
                },
            ],

            # Dados para o gráfico de pedidos
            'pedidosChartData': json.dumps({
                'datasets': [
                    {
                        'data': data_pedidos,
                        'borderColor': 'rgb(75, 192, 192)',  # Cor para pedidos
                        'label': 'Total de Pedidos por Dia',
                        'fill': False  # Linha sem preenchimento
                    }
                ],
                'labels': labels
            }),

            # Dados para o gráfico de vendas
            'vendasChartData': json.dumps({
                'datasets': [
                    {
                        'data': data_vendas,
                        'borderColor': 'rgb(147, 51, 234)',  # Cor para vendas
                        'label': 'Total de Vendas por Dia',
                        'fill': False  # Linha sem preenchimento
                    }
                ],
                'labels': labels
            }),

            "table": {
                "headers": ["Name", "Total orders", "Sales"],
                'rows': [
                    [lavandaria.nome, lavandaria.numero_pedidos, str(float(lavandaria.total_vendas or 0)) + " MZN"]
                    for lavandaria in lavandarias
                ]
            },
        }
    )
    return context
