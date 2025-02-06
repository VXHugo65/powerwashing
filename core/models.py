from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.utils.html import format_html
from django.contrib.contenttypes.models import ContentType


# Modelo para Lavandarias
class Lavandaria(models.Model):
    """
    Representa uma lavandaria cadastrada no sistema.
    """
    nome = models.CharField(max_length=255)
    endereco = models.TextField()
    telefone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome


# Modelo para Funcionários
class Funcionario(models.Model):
    """
    Representa um funcionário associado a uma lavandaria.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='funcionario')
    lavandaria = models.ForeignKey(Lavandaria, on_delete=models.CASCADE, related_name='funcionarios')
    telefone = models.CharField(max_length=20, unique=True)
    grupo = models.CharField(
        max_length=255,
        choices=[('gerente', 'Gerente'), ('caixa', 'Caixa')],
        help_text="Define o grupo do usuário."
    )

    def __str__(self):
        return f"{self.user.username} - {self.grupo}"

    def save(self, *args, **kwargs):
        criar_grupos_com_permissoes()
        super().save(*args, **kwargs)

        # Associa o usuário ao grupo correto
        if self.grupo:
            grupo = Group.objects.get(name=self.grupo)
            self.user.groups.set([grupo])

        self.user.is_staff = True
        self.user.save()


# Modelo para Tipos de Artigos (Itens de Serviço)
class ItemServico(models.Model):
    """
    Representa um tipo de artigo disponível para serviço.
    """
    image = models.ImageField(null=True, blank=True)
    nome = models.CharField(max_length=255)
    disponivel = models.BooleanField(default=True)

    def imagem(self):
        if self.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', self.image.url)
        return "Sem Imagem"

    def __str__(self):
        return self.nome


# Modelo para Serviços disponíveis na Lavandaria
class Servico(models.Model):
    """
    Representa um serviço oferecido por uma lavandaria.
    """
    lavandaria = models.ForeignKey(Lavandaria, on_delete=models.CASCADE, related_name='servicos')
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, null=True)
    preco_base = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nome}"


# Modelo para Clientes
class Cliente(models.Model):
    """
    Representa um cliente do sistema.
    """
    nome = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True, unique=True)
    telefone = models.CharField(max_length=20, unique=True)
    endereco = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.nome


# Modelo para Pedidos
class Pedido(models.Model):
    """
    Representa um pedido associado a uma lavandaria e cliente.
    """
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('em_progresso', 'Em Progresso'),
        ('pronto', 'pronto'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pedidos')
    lavandaria = models.ForeignKey(Lavandaria, on_delete=models.CASCADE, related_name='pedidos')
    funcionario = models.ForeignKey(Funcionario, on_delete=models.SET_NULL, related_name='pedidos', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    pago = models.BooleanField(default=False)

    def atualizar_total(self):
        self.total = sum(item.preco_total for item in self.itens.all())
        self.save()

    def __str__(self):
        return f"Pedido {self.id} - {self.cliente}"


# Modelo para Itens do Pedido
class ItemPedido(models.Model):
    """
    Representa um item incluído em um pedido.
    """
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name='itens')
    item_de_servico = models.ForeignKey(ItemServico, on_delete=models.SET_NULL, related_name='itens', null=True, blank=True)
    quantidade = models.PositiveIntegerField()
    preco_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.preco_total = (self.servico.preco_base * self.quantidade) if self.servico and self.quantidade else 0
        super().save(*args, **kwargs)
        self.pedido.atualizar_total()

    def delete(self, *args, **kwargs):
        pedido = self.pedido
        super().delete(*args, **kwargs)
        pedido.atualizar_total()

    def __str__(self):
        return f"{self.servico.nome} - {self.quantidade}x - Total: {self.preco_total}"


# Função para criar grupos e associar permissões
def criar_grupos_com_permissoes():
    """
    Cria grupos predefinidos (gerente, caixa) e associa as permissões específicas.
    """
    grupos_permissoes = {
        "gerente": [
            "view_funcionario",
            "add_itemservico", "change_itemservico", "delete_itemservico", "view_itemservico",
            "add_servico", "change_servico", "delete_servico", "view_servico",
            "add_pedido", "change_pedido", "delete_pedido", "view_pedido",
            "add_cliente", "change_cliente", "delete_cliente", "view_cliente",
            "add_itempedido", "change_itempedido", "delete_itempedido", "view_itempedido",
        ],
        "caixa": [
            "add_itemservico", "change_itemservico", "view_itemservico",
            "add_pedido", "change_pedido", "delete_pedido", "view_pedido",
            "add_cliente", "change_cliente", "delete_cliente", "view_cliente",
            "add_itempedido", "change_itempedido", "delete_itempedido", "view_itempedido",
        ],
    }

    for grupo_nome, permissoes_codigos in grupos_permissoes.items():
        grupo, criado = Group.objects.get_or_create(name=grupo_nome)
        if criado:
            print(f"Grupo '{grupo_nome}' criado.")

        for permissao_codigo in permissoes_codigos:
            permissao = Permission.objects.filter(codename=permissao_codigo).first()
            if permissao:
                grupo.permissions.add(permissao)

        print(f"Permissões associadas ao grupo '{grupo_nome}': {permissoes_codigos}")
