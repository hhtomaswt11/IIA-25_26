# Agente de Descoberta de Receitas (Rasa)

Este repositório contém um agente conversacional construído com Rasa para descoberta e seleção de receitas. O agente faz filtragem por categoria, tempo, dificuldade e restrições dietéticas, e apresenta resultados estruturados que permitem ao utilizador selecionar uma receita e obter os ingredientes e passos diretamente pelo Rasa (lógica server-side). É uma solução híbrida com uso de LLM e técnicas de processamento de linguagem natural (NLP) tradicionais para oferecer uma experiência robusta e personalizada ao utilizador.

**Principais funcionalidades**
- Pesquisa e filtragem de receitas a partir de um CSV (`data_source/recipes.csv`).
- Normalização de texto (remoção de acentos) e parsing robusto de tempo/calorias.
- Suporte a filtros: categoria, dificuldade, tempo de confeção, restrições alimentares, ingredientes a evitar e preferência calórica.
- Saída estruturada com payloads canónicos para seleção (`/select_recipe{"recipe_index": N}`), preservando a lógica no servidor.
- Ações customizadas em Python em `actions/` (ex.: `action_search_recipes.py`).

**Índice**
- **Visão Geral**: o que é este projeto e para que serve
- **Instalação Rápida**: passos para colocar a aplicação a correr
- **Estrutura do Projeto**: onde estão os ficheiros importantes
- **Como Usar**: comandos básicos e fluxo de teste
- **Desenvolvimento**: pontos úteis para quem for editar o código
- **Testes & E2E**: onde estão os testes e como executá-los
- **Resolução de Problemas**: erros comuns e como resolvê-los
- **Contribuição** e **Licença**

**Visão Geral**

Este agente facilita a procura de receitas por parâmetros definidos pelo utilizador. A componente de actions processa um CSV (separador `;`), normaliza textos, extrai minutos de tempo de confeção e calorias numéricas, aplica filtros e devolve:

- Um texto resumo com os resultados.
- Um `json_message` com a lista de receitas encontradas.
- Botões canónicos que disparam a intenção `select_recipe` com um payload JSON, permitindo que o Rasa trate a seleção server-side.

O projeto foi pensado para ser usado localmente com Rasa e opcionalmente com uma interface incluída.

**Instalação Rápida**

1. Criar e ativar um ambiente virtual (recomendado):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instalar dependências (se existir `requirements.txt`):

```bash
pip install -r requirements.txt
```

Dependências tipicamente necessárias: `rasa`, `rasa-sdk`, `pandas`, `streamlit`.

3. Treinar o modelo Rasa:

```bash
rasa train
```

4. Iniciar o serviço das actions (num terminal separado):

```bash
rasa run actions --debug
```

5. Iniciar o servidor Rasa HTTP (API + conversação):

```bash
rasa run --enable-api
```

6. (Opcional) Iniciar a interface Streamlit para demo:

```bash
streamlit run streamlit/streamlit_app.py
```

Ou usar o endpoint REST do Rasa (ex.: `http://localhost:5005/webhooks/rest/webhook`) com o web demo em `web/`.

**Estrutura do Projeto**

- `actions/`: ações customizadas do Rasa em Python. Principais ficheiros:
	- `action_search_recipes.py`: pesquisa e filtragem de receitas; prepara payloads e botões canónicos.
- `data/`: flows, regras e stories do Rasa (`flows/`, `nlu.yml`, `rules.yml`, etc.).
- `domain/`: domínio Rasa com intents, slots, respostas e actions.
- `data_source/recipes.csv`: base de dados de receitas (separador `;`).

**Como Usar / Fluxo básico**

1. Treine o modelo (`rasa train`).
2. Levante as actions (`rasa run actions`) e o servidor Rasa (`rasa run --enable-api`).
3. Interaja pelo `rasa shell` ou via REST (por exemplo, com a Streamlit UI): informe categoria, tempo, dificuldade, restrições e o bot apresentará resultados.
4. Quando o bot enviar os resultados, utilize o botão correspondente ou envie manualmente o payload canónico, ex:

```text
/select_recipe{"recipe_index": 0}
```

ou simplesmente escreva o número `1` / `2` conforme os exemplos NLU configurados — o `action_show_recipe_details` irá recuperar a receita do slot `search_results` e apresentar ingredientes + passos.

**Dicas de Desenvolvimento**

- Se editar `actions/action_search_recipes.py` tenha em atenção as dependências (`pandas`, `unicodedata`, `re`) e mantenha a normalização de acentos para garantir filtros insensíveis a acentos.
- O parsing de tempos converte para minutos inteiros (campo `tempo_minutes`) e existe lógica para interpretar intervalos (ex.: `30-60`, `30–60`, `menos de 30`).
- `dietary_restrictions` com valor `nenhuma` é tratado como sem filtro.
- Para alterar os payloads (por exemplo para 1-based indexing) edite a criação dos botões canónicos em `action_search_recipes.py` e atualize os exemplos NLU em `data/nlu.yml`.

**Testes & E2E**

- Os cenários em `e2e_tests/` servem como referência para conversas que devem funcionar de ponta a ponta. Dependendo da sua pipeline, pode executar testes com o runner que utiliza (ex.: `rasa test` / runner customizado).
- Para testes manuais rápidos:
	- Use `rasa shell` e percorra o fluxo de descoberta de receitas.
	- Verifique os logs do `rasa run actions` para ver os prints de debug adicionados (contagens após cada filtro).

**Resolução de Problemas Comuns**

- Erro: `ModuleNotFoundError: No module named 'rasa_sdk'` → certifique-se de ativar o virtualenv e instalar `rasa-sdk` (`pip install rasa-sdk`).
- Erro ao ler CSV → confirme que `data_source/recipes.csv` existe e usa `;` como separador; o parser do projeto espera esse formato.
- Seleção não invoca ação → verifique que o `domain.yml` contém a intenção `select_recipe` e que `data/nlu.yml` tem exemplos do payload canónico. Depois execute `rasa train`.

**Contribuição**

Contribuições são bem-vindas. Para propor alterações:

1. Crie um branch a partir de `main`.
2. Faça commits pequenos e com mensagens claras.
3. Abra um pull request descrevendo a alteração e como testá-la.

**Licença**

Verifique o ficheiro `LICENSE` presente no repositório para os termos da licença.

---

