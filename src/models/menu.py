"""Modelos Pydantic para o banco de dados do cardápio (SQLite read-only).

Representam as tabelas ``pizzas``, ``tamanhos``, ``bordas`` e ``precos``
do banco ``knowledge_base.db``. Usados como schemas de leitura — o banco
é acessado exclusivamente em modo read-only.
"""

from pydantic import BaseModel, Field


class Pizza(BaseModel):
    """Sabor de pizza cadastrado no cardápio.

    Corresponde à tabela ``pizzas``.
    """

    id: int = Field(description="ID auto-increment da pizza.")
    sabor: str = Field(description="Nome do sabor (ex: 'Margherita').")
    descricao: str = Field(description="Descrição do sabor.")
    ingredientes: str = Field(
        description="Lista de ingredientes separados por vírgula."
    )


class Tamanho(BaseModel):
    """Tamanho de pizza disponível.

    Corresponde à tabela ``tamanhos``.
    Valores possíveis: 'Pequena', 'Média', 'Grande'.
    """

    id: int = Field(description="ID auto-increment do tamanho.")
    tamanho: str = Field(description="Nome do tamanho (UNIQUE).")


class Borda(BaseModel):
    """Tipo de borda disponível.

    Corresponde à tabela ``bordas``.
    Valores possíveis: 'Tradicional', 'Recheada com Cheddar', 'Recheada com Catupiry'.
    """

    id: int = Field(description="ID auto-increment da borda.")
    tipo: str = Field(description="Nome do tipo de borda (UNIQUE).")


class Preco(BaseModel):
    """Preço de uma combinação sabor + tamanho + borda.

    Corresponde à tabela ``precos``.
    PK composta: ``(pizza_id, tamanho_id, borda_id)``.

    Regras de negócio:
    - Pizzas doces possuem apenas borda Tradicional.
    - Bordas recheadas só estão disponíveis nos tamanhos Média e Grande.
    """

    pizza_id: int = Field(description="FK → pizzas(id).")
    tamanho_id: int = Field(description="FK → tamanhos(id).")
    borda_id: int = Field(description="FK → bordas(id).")
    preco: float = Field(description="Preço em R$.")


class MenuItem(BaseModel):
    """Item completo do cardápio (resultado de JOIN entre as tabelas).

    Representa uma combinação válida de sabor + tamanho + borda com preço,
    retornada pelas consultas das tools.
    """

    sabor: str = Field(description="Nome do sabor.")
    descricao: str = Field(default="", description="Descrição do sabor.")
    ingredientes: str = Field(default="", description="Ingredientes do sabor.")
    tamanho: str = Field(description="Tamanho da pizza.")
    borda: str = Field(description="Tipo da borda.")
    preco: float = Field(description="Preço em R$.")


class MenuSearchResult(BaseModel):
    """Resultado de busca semântica no cardápio.

    Estende ``MenuItem`` com score de similaridade.
    """

    sabor: str = Field(description="Nome do sabor.")
    descricao: str = Field(default="", description="Descrição do sabor.")
    ingredientes: str = Field(default="", description="Ingredientes do sabor.")
    tamanho: str = Field(description="Tamanho da pizza.")
    borda: str = Field(description="Tipo da borda.")
    preco: float = Field(description="Preço em R$.")
    score: float = Field(description="Score de similaridade de cosseno (0 a 1).")
