# 👨‍🍳 ChefBot — Assistente Inteligente de Receitas

O **ChefBot** é um assistente conversacional inteligente para recomendação e acompanhamento de receitas culinárias, desenvolvido com **Rasa Open Source** e um **frontend web personalizado** em HTML + Tailwind CSS.

O bot permite pesquisar receitas com base em preferências do utilizador, acompanhar receitas passo-a-passo, gerir favoritos, registar histórico de receitas feitas e recolher avaliações.

---

## ✨ Funcionalidades

- 🔍 **Pesquisa de receitas** por:
  - Categoria (entrada, prato principal, sobremesa)
  - Tempo de preparação
  - Dificuldade
  - Restrições alimentares (vegetariano, vegan, sem glúten, etc.)
  - Preferência calórica
  - Ingredientes disponíveis

- 🧑‍🍳 **Modo passo-a-passo**
  - Navegação entre passos
  - Avançar, regressar ou abandonar receita
  - Finalização com avaliação

- ⭐ **Avaliação de receitas** (1 a 5 estrelas)
- ❤️ **Gestão de favoritos**
- 🕐 **Histórico de receitas recentes**
  - Resumo geral
  - Filtragem por categoria

- 🌐 **Interface Web moderna**
  - Histórico de conversas
  - Interface responsiva
  - Suporte a imagens nas receitas

---

## 🏗️ Arquitetura do Projeto

```

IIA-25_26/
├── data/
│   ├── nlu.yml           # Exemplos de treino para reconhecimento de intenções
│   ├── rules.yml         # Regras de conversação de baixo nível
│   ├── stories.yml       # Fluxos de conversação complexos
├── actions/
│   └── actions.py        # Ações customizadas em Python
├── db/
│   └── recipes.csv       # Dataset principal de receitas
├── models/               # Modelos treinados do Rasa
├── tests/                # Testes do chatbot
├── config.yml           # Configuração do pipeline do Rasa
├── credentials.yml      # Credenciais para conectores
├── domain.yml        # Configuração global do domínio
├── endpoints.yml        # Endpoints para actions server
└── README.md           # Esta documentação

````

---

## 🛠️ Tecnologias Utilizadas

- **Rasa Open Source**
- **Python 3**
- **HTML5**
- **Tailwind CSS**
- **JavaScript**
- **CSV** como armazenamento leve de dados

---

## 🚀 Como Executar o Projeto

### 1️⃣ Instalar dependências

```bash
pip install rasa
pip install rasa-sdk
````

---

### 2️⃣ Treinar o modelo

```bash
rasa train
```

---

### 3️⃣ Iniciar o servidor de ações

```bash
rasa run actions
```

---

### 4️⃣ Iniciar o servidor Rasa

```bash
rasa run --enable-api --cors "*"
```

---

### 5️⃣ Abrir o frontend

Abrir o ficheiro `ChefBot.html` num browser (recomendado: Chrome ou Firefox).

> ⚠️ Certifica-te que o endpoint no ficheiro HTML aponta para:
>
> ```
> http://localhost:5005/webhooks/rest/webhook
> ```

---

## 📊 Dataset de Receitas

As receitas são carregadas a partir de um ficheiro CSV (`recipes.csv`) com os seguintes campos:

* `id`
* `titulo`
* `categoria`
* `dificuldade`
* `tempo_total`
* `calorias`
* `rating`
* `ingredientes`
* `passos`
* `criterios`
* `imagem`

Os campos de lista usam o separador `|`.

---

## 📚 Contexto Académico

Este projeto foi desenvolvido no âmbito de uma unidade curricular de **Introdução à Inteligência Artificial**, com foco em:

* Processamento de Linguagem Natural
* Sistemas baseados em regras e estados
* Interação humano-computador

---

## 👤 Autores 

Desenvolvido por: 
**Tomás Henrique Alves Melo** - PG60018 
**Rodrigo Miguel Granja Ferreira** - PG60392
**Luís Pinto da Cunha** - PG60280 
**Nuno Filipe Leite Oliveira Araújo** - PG61218 

---

## 📝 Licença

Este projeto é de uso académico.
Uso comercial sujeito a autorização do autor.

