from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Lavandaria, ItemServico, Servico, Cliente, Pedido, ItemPedido, Funcionario
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group, User
from twilio.rest import Client as twilio_Client
from django.contrib import messages
import requests
import json


admin.site.unregister(Group)
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    # Forms loaded from `unfold.forms`
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


# Inline para gerenciar os itens de pedido diretamente no pedido
class ItemPedidoInline(TabularInline):
    model = ItemPedido
    extra = 1  # Número de linhas extras para novos itens
    fields = ('servico', 'item_de_servico', 'quantidade', 'preco_total')
    readonly_fields = ('preco_total',)


# Configuração do modelo Lavandaria no Admin
@admin.register(Lavandaria)
class LavandariaAdmin(ModelAdmin):
    list_display = ('nome', 'endereco', 'telefone', 'email', 'criado_em', 'atualizado_em')
    search_fields = ('nome', 'email', 'telefone')
    list_filter = ('criado_em', 'atualizado_em')
    fieldsets = (
        ('Informações Básicas', {'fields': ('nome', 'endereco', 'telefone', 'email',)}),
        ('Datas', {'fields': ('criado_em', 'atualizado_em')}),
    )
    readonly_fields = ('criado_em', 'atualizado_em')


# Configuração do modelo Cliente no Admin
@admin.register(Cliente)
class ClienteAdmin(ModelAdmin):
    list_display = ('nome', 'email', 'telefone', 'endereco')
    search_fields = ('nome', 'email', 'telefone')


# Configuração do modelo Funcionario no Admin
@admin.register(Funcionario)
class FuncionarioAdmin(ModelAdmin):
    list_display = ('user', 'lavandaria', 'grupo', 'telefone')
    search_fields = ('user__username', 'telefone', 'lavandaria__nome')
    list_filter = ('grupo',)

    # def get_form(self, request, obj=None, **kwargs):
    #     form = super().get_form(request, obj, **kwargs)
    #     # Filtra usuários que ainda não são funcionários
    #     form.base_fields['user'].queryset = User.objects.filter(funcionario__isnull=True)
    #     return form


# Configuração do modelo ItemServico no Admin
@admin.register(ItemServico)
class ItemServicoAdmin(ModelAdmin):
    list_display = ('imagem', 'nome', 'disponivel')
    search_fields = ('nome',)
    list_filter = ('disponivel',)


# Configuração do modelo Servico no Admin
@admin.register(Servico)
class ServicoAdmin(ModelAdmin):
    list_display = ('nome', 'lavandaria', 'preco_base', 'ativo')
    search_fields = ('nome', 'lavandaria__nome')
    list_filter = ('ativo', 'lavandaria')
    fieldsets = (
        ('Informações do Serviço', {'fields': ('nome', 'descricao', 'preco_base', 'ativo')}),
        ('Lavandaria', {'fields': ('lavandaria',)}),
    )


# Configuração do modelo Cliente no Admin
@admin.register(Pedido)
class PedidoAdmin(ModelAdmin):
    list_display = ('id', 'cliente', 'atualizado_em', 'status', 'pago', 'total', 'botao_imprimir')
    search_fields = ('cliente__nome', 'id')
    list_display_links = ('cliente', 'id')
    list_editable = ('status', 'pago')
    list_filter = ('status', 'criado_em', 'pago')
    fieldsets = (
        ('Detalhes do Pedido', {'fields': ('cliente', 'lavandaria', 'funcionario', 'status',)}),
        ('Totais e Datas', {'fields': ('total', 'criado_em', 'atualizado_em')}),
        ('', {'fields': ('pago',)}),
    )
    readonly_fields = ('total', 'criado_em', 'atualizado_em', 'funcionario', 'lavandaria')
    inlines = [ItemPedidoInline]
    actions = ['enviar_mensagem_pedido_pronto']

    def save_model(self, request, obj, form, change):
        if request.user.is_superuser:
            # Para superusuários, não atribuir funcionário ou lavandaria
            super(PedidoAdmin, self).save_model(request, obj, form, change)
            return

        try:
            # Obtém o funcionário associado ao usuário logado
            funcionario = Funcionario.objects.get(user=request.user)
            obj.funcionario = funcionario

            # Verifica se o funcionário tem uma lavandaria associada
            if funcionario.lavandaria:
                obj.lavandaria = funcionario.lavandaria
            else:
                raise ValueError("O funcionário logado não está associado a nenhuma lavandaria.")
        except Funcionario.DoesNotExist:
            raise ValueError("O usuário logado não está associado a nenhum funcionário.")

        super(PedidoAdmin, self).save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super(PedidoAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs

        try:
            # Obtém o funcionário associado ao usuário logado
            funcionario = Funcionario.objects.get(user=request.user)

            # Garante que o funcionário tenha uma lavandaria
            if funcionario.lavandaria:
                return qs.filter(lavandaria=funcionario.lavandaria)
            else:
                raise ValueError("O funcionário logado não está associado a nenhuma lavandaria.")
        except Funcionario.DoesNotExist:
            raise ValueError("O usuário logado não está associado a nenhum funcionário.")

    def botao_imprimir(self, obj):
        url = reverse('core:imprimir_recibo', args=[obj.id])
        return format_html(f'<a class="button" href="{url}" target="_blank">Imprimir</a>')

    botao_imprimir.short_description = "Imprimir Recibo"

    # def enviar_mensagem_pedido_pronto(self, request, queryset):
    #     account_sid = "ACb5cc789ebd7ad37bd67369f0b535aa97"
    #     auth_token = "92f965343203ccd6bada5af78f0c4121"
    #     twilio_number = "+18456446074"
    #
    #     client = twilio_Client(account_sid, auth_token)
    #
    #     for pedido in queryset:
    #         if pedido.status == 'concluido':
    #             mensagem = f"Olá {pedido.cliente.nome}, seu pedido #{pedido.id} está pronto para retirada!"
    #             client.messages.create(
    #                 body=mensagem,
    #                 from_=twilio_number,
    #                 to='+258849651834'
    #             )
    #             messages.success(request, f"Mensagem enviada para {pedido.cliente.nome}.")
    #         else:
    #             messages.warning(request, f"O pedido {pedido.id} não está pronto.")
    #
    # enviar_mensagem_pedido_pronto.short_description = "Enviar mensagem de pedido pronto"

    def send_sms(self, to, message):
        url = 'https://api.mozesms.com/message/v2'
        headers = {'Authorization': 'Bearer 2309:fI1aPs-MCF2CJ-nKkMQD-61cLGv'}
        data = {
            'from': 'ESHOP',
            'to': to,
            'message': message
        }
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()

        # Verifica e separa múltiplos JSONs se necessário
        raw_response = response.text.strip()
        json_parts = raw_response.split("}{")  # Divide JSONs mal formatados

        if len(json_parts) > 1:
            json_parts = [json.loads(f"{{{part}}}") if i != 0 and i != len(json_parts) - 1
                          else json.loads(part)
                          for i, part in enumerate(json_parts)]
            return json_parts  # Retorna uma lista com os dois JSONs
        else:
            return json.loads(raw_response)  # Retorna JSON único

    def enviar_mensagem_pedido_pronto(self, request, queryset):
        for pedido in queryset:
            if pedido.status == 'pronto':
                mensagem = f"Olá {pedido.cliente.nome}, seu pedido #{pedido.id} está pronto para retirada!"
                response = self.send_sms('+258'+str(pedido.cliente.telefone), mensagem)
                if 'error' in response:
                    messages.error(request, f"Erro ao enviar mensagem para {pedido.cliente.nome}: {response['error']} ")
                else:
                    messages.success(request, f"Mensagem enviada para {pedido.cliente.nome}. status: {response['code']}")
            else:
                messages.warning(request, f"O pedido {pedido.id} não está pronto.")

    enviar_mensagem_pedido_pronto.short_description = "Enviar mensagem de pedido pronto"


# Configuração do modelo ItemPedido no Admin
@admin.register(ItemPedido)
class ItemPedidoAdmin(ModelAdmin):
    list_display = ('pedido', 'servico', 'item_de_servico', 'quantidade', 'preco_total')
    search_fields = ('pedido__id', 'servico__nome', 'item_de_servico__nome')
    list_filter = ('servico',)
    readonly_fields = ('preco_total',)

