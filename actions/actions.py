# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, AllSlotsReset, FollowupAction
import csv
import os
import re
from datetime import datetime
import json


def carregar_receitas():
    """Carrega as receitas do ficheiro CSV tratando o formato específico que enviaste"""
    receitas = []
    
    # Tenta encontrar o ficheiro na raiz ou na pasta data_source
    caminho_csv = "recipes.csv"
    if not os.path.exists(caminho_csv):
        caminho_csv = os.path.join("data_source", "recipes.csv")

    if not os.path.exists(caminho_csv):
        print(f"❌ ERRO CRÍTICO: Não encontrei 'recipes.csv'.")
        return []
    
    try:
        # utf-8-sig é essencial para ficheiros vindos do Excel/Windows
        with open(caminho_csv, 'r', encoding='utf-8-sig') as file:
            # O teu ficheiro usa ponto e vírgula
            reader = csv.DictReader(file, delimiter=';')
            
            # Limpa espaços nos nomes das colunas (ex: " titulo " -> "titulo")
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
            
            for row in reader:
                # --- 1. TRATAMENTO DE LISTAS (separadas por | no teu CSV) ---
                criterios = [c.strip().lower() for c in row.get('criterios', '').split('|')] if row.get('criterios') else []
                ingredientes = [i.strip() for i in row.get('ingredientes', '').split('|')] if row.get('ingredientes') else []
                passos = [p.strip() for p in row.get('passos', '').split('|')] if row.get('passos') else []
                
                # --- 2. TRATAMENTO DE TEMPO (40 min, 1 h 20 m, etc) ---
                tempo_total = row.get('tempo_total', '').strip()
                tempo_minutos = 0
                if tempo_total:
                    numeros = re.findall(r'\d+', tempo_total)
                    if numeros:
                        # Se tiver horas ("h"), a lógica muda
                        if 'h' in tempo_total.lower():
                            horas = int(numeros[0])
                            minutos = int(numeros[1]) if len(numeros) > 1 else 0
                            tempo_minutos = (horas * 60) + minutos
                        else:
                            # Apenas minutos
                            tempo_minutos = int(numeros[0])
                
                # --- 3. TRATAMENTO DE NÚMEROS ---
                # Calorias (remove "Kcal")
                calorias_str = row.get('calorias', '0').lower().replace('kcal', '').strip()
                try:
                    calorias = int(calorias_str)
                except:
                    calorias = 0

                # Rating (troca vírgula por ponto se necessário)
                rating_str = row.get('rating', '0').replace(',', '.').strip()
                try:
                    rating = float(rating_str)
                except:
                    rating = 0.0
                
                # Cria o objeto limpo
                receita = {
                    'id': row.get('id', '').strip(),

                    'titulo': row.get('titulo', '').strip(),
                    'categoria': row.get('categoria', '').strip().lower(),
                    'dificuldade': row.get('dificuldade', '').strip().lower(),
                    'tempo_total': tempo_total,
                    'tempo_minutos': tempo_minutos,
                    'calorias': calorias,
                    'rating': rating,
                    'ingredientes': ingredientes, 
                    'passos': passos,            
                    'criterios': criterios       
                }
                receitas.append(receita)
        
        print(f"✅ Sucesso: {len(receitas)} receitas carregadas do teu dataset.")
                
    except Exception as e:
        print(f"❌ Erro ao ler CSV: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return receitas





def _esta_nos_favoritos(receita_id: str, caminho: str = "favoritos.csv") -> bool:
    if not receita_id or not os.path.exists(caminho):
        return False
    try:
        with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                if (row.get("id", "") or "").strip() == receita_id.strip():
                    return True
    except:
        return False
    return False


def _remover_dos_favoritos(receita_id: str, caminho: str = "favoritos.csv") -> bool:
    if not receita_id or not os.path.exists(caminho):
        return False
    try:
        with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f, delimiter=";"))

        if not rows:
            return False

        rid = receita_id.strip()
        novas = [r for r in rows if (r.get("id", "") or "").strip() != rid]

        if len(novas) == len(rows):
            return False

        with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
            writer.writeheader()
            writer.writerows(novas)

        return True
    except:
        return False


def _garantir_csv_com_header(caminho: str, header: List[str]):
    existe = os.path.exists(caminho)
    if not existe:
        with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(header)

def _receita_para_linha_csv(receita: Dict[str, Any], avaliacao_utilizador: Any):
    return {
        "id": receita.get("id", ""),
        "titulo": receita.get("titulo", ""),
        "categoria": receita.get("categoria", ""),
        "dificuldade": receita.get("dificuldade", ""),
        "tempo_total": receita.get("tempo_total", ""),
        "tempo_minutos": receita.get("tempo_minutos", ""),
        "calorias": receita.get("calorias", ""),
        "rating_dataset": receita.get("rating", ""),
        "criterios": "|".join(receita.get("criterios", []) or []),
        "ingredientes": "|".join(receita.get("ingredientes", []) or []),
        "passos": "|".join(receita.get("passos", []) or []),
        "avaliacao_utilizador": "" if avaliacao_utilizador is None else str(avaliacao_utilizador),
    }






class ActionBuscarReceitas(Action):
    def name(self) -> Text:
        return "action_buscar_receitas"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obter Slots do Rasa
        categoria = tracker.get_slot("categoria")
        tempo = tracker.get_slot("tempo")
        dificuldade = tracker.get_slot("dificuldade")
        restricao = tracker.get_slot("restricao")
        ingrediente_evitar = tracker.get_slot("ingrediente_evitar")
        preferencia_calorica = tracker.get_slot("preferencia_calorica")
        
        print(f"🔍 A pesquisar: Cat={categoria}, Tempo={tempo}, Dif={dificuldade}")

        todas_receitas = carregar_receitas()
        
        if not todas_receitas:
            # Se a lista vier vazia, avisa mas não crasha
            return [SlotSet("receitas_encontradas", [])]

        receitas_filtradas = todas_receitas.copy()

        # --- LÓGICA DE FILTROS ---

        # 1. Categoria
        if categoria and categoria != "tudo":
            # Normaliza para minúsculas para comparar
            cat_busca = categoria.lower()
            if cat_busca == "prato_principal":
                receitas_filtradas = [r for r in receitas_filtradas if "prato principal" in r["categoria"]]
            else:
                receitas_filtradas = [r for r in receitas_filtradas if cat_busca in r["categoria"]]
        
        # 2. Tempo
        if tempo and tempo != "tanto_faz":
            if tempo == "ate_30min":
                receitas_filtradas = [r for r in receitas_filtradas if r["tempo_minutos"] <= 30]
            elif tempo == "30_60min":
                receitas_filtradas = [r for r in receitas_filtradas if 30 < r["tempo_minutos"] <= 60]
            elif tempo == "mais_1h":
                receitas_filtradas = [r for r in receitas_filtradas if r["tempo_minutos"] > 60]
        
        # 3. Dificuldade
        if dificuldade and dificuldade != "qualquer":
            dif_map = {
                "facil": ["muito fácil", "fácil"], 
                "medio": ["médio"],
                "dificil": ["difícil"]
            }
            if dificuldade in dif_map:
                termos_aceites = dif_map[dificuldade]
                receitas_filtradas = [r for r in receitas_filtradas if r["dificuldade"] in termos_aceites]
        
        # 4. Restrições (O teu CSV tem "Sem glúten", "Vegan", etc)
        if restricao and restricao not in ["nenhuma", "outro"]:
            restricao_map = {
                "vegetariano": "vegetariano",
                "vegano": "vegan",
                "sem_gluten": "sem glúten",
                "sem_lactose": "sem lactose"
            }
            if restricao in restricao_map:
                termo_busca = restricao_map[restricao]
                # Verifica se o termo está na lista de critérios da receita
                receitas_filtradas = [r for r in receitas_filtradas if any(termo_busca in c for c in r["criterios"])]
        
        # 5. Ingrediente a Evitar
        if ingrediente_evitar:
            evitar = ingrediente_evitar.lower()
            receitas_filtradas = [r for r in receitas_filtradas if not any(evitar in i.lower() for i in r["ingredientes"])]
        
        # 6. Calorias
        if preferencia_calorica == "leve":
            receitas_filtradas = [r for r in receitas_filtradas if r["calorias"] <= 300]
        elif preferencia_calorica == "moderado":
            receitas_filtradas = [r for r in receitas_filtradas if 300 < r["calorias"] <= 600]
        
        # Ordenar por rating (melhores primeiro) e pegar top 5
        receitas_filtradas.sort(key=lambda x: x['rating'], reverse=True)
        receitas_filtradas = receitas_filtradas[:5]
        
        return [SlotSet("receitas_encontradas", receitas_filtradas)]

class ActionBuscarPorIngredientes(Action):
    def name(self) -> Text:
        return "action_buscar_por_ingredientes"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # 1. Obter a lista de ingredientes que o utilizador disse que tem
        ingredientes_usuario = tracker.get_slot("lista_ingredientes_possuido")
        
        if not ingredientes_usuario:
            dispatcher.utter_message(text="Não percebi quais ingredientes tens. Podes repetir? (Ex: tenho batata e ovos)")
            return []

        print(f"🔍 Ingredientes do utilizador: {ingredientes_usuario}")

        todas_receitas = carregar_receitas() # Usa a tua função existente
        receitas_pontuadas = []

        # 2. Lógica de Matching
        # Vamos contar quantos ingredientes da receita o utilizador TEM.
        for receita in todas_receitas:
            matches = 0
            ingredientes_receita_str = " ".join(receita['ingredientes']).lower()
            
            # Verifica cada ingrediente do usuario contra a lista da receita
            for ing_user in ingredientes_usuario:
                # Remove o 's' final para tentar lidar com plurais simples (ex: ovos -> ovo)
                termo = ing_user.lower().rstrip('s') 
                if termo in ingredientes_receita_str:
                    matches += 1
            
            if matches > 0:
                # Calculamos uma pontuação. 
                # (Número de matches) + (Bônus se tiver rating alto)
                score = matches + (receita['rating'] * 0.1)
                receitas_pontuadas.append((score, receita))

        # 3. Ordenar e Filtrar
        # Ordena pela pontuação (score) decrescente
        receitas_pontuadas.sort(key=lambda x: x[0], reverse=True)
        
        # Pega nas top 5 receitas (apenas o objeto receita, ignorando o score agora)
        top_receitas = [r[1] for r in receitas_pontuadas[:5]]

        if not top_receitas:
            dispatcher.utter_message(text=f"Não encontrei receitas específicas com {', '.join(ingredientes_usuario)}. Tenta outros ingredientes!")
            return []

        # 4. Guardar no Slot para usar a ActionMostrarReceitas existente
        # Como a estrutura é igual, podemos reaproveitar a action_mostrar_receitas!
        return [
            SlotSet("receitas_encontradas", top_receitas), 
            FollowupAction("action_mostrar_receitas") # Chama automaticamente a exibição
        ]

class ActionMostrarReceitas(Action):
    def name(self) -> Text:
        return "action_mostrar_receitas"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        receitas = tracker.get_slot("receitas_encontradas")
        
        if not receitas:
            dispatcher.utter_message(response="utter_nenhuma_receita_encontrada")
            return []
        
        mensagem = f"Encontrei {len(receitas)} receita(s)! 🔍\n\n"
        buttons = []
        
        for i, receita in enumerate(receitas, 1):
            # Tenta encontrar emoji compatível com o texto do CSV
            dificuldade_lower = receita["dificuldade"]
            emoji = "🍽️"
            if "fácil" in dificuldade_lower: emoji = "😊"
            elif "médio" in dificuldade_lower: emoji = "🤔"
            elif "difícil" in dificuldade_lower: emoji = "😤"
            
            mensagem += f"{i}. {emoji} **{receita['titulo']}**\n"
            mensagem += f"   ⏱️ {receita['tempo_total']} | 🔥 {receita['calorias']} Kcal\n\n"
            
            # Payload com chavetas duplas para o Rasa não bugar
            buttons.append({"title": f"Ver {i}: {receita['titulo']}", "payload": f'/ver_receita{{"numero_receita":"{i}"}}'})
        
        buttons.append({"title": "🔄 Nova Busca", "payload": '/nova_busca'})
        dispatcher.utter_message(text=mensagem, buttons=buttons)
        return []


class ActionMostrarReceitaCompleta(Action):
    def name(self) -> Text:
        return "action_mostrar_receita_completa"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        receitas = tracker.get_slot("receitas_encontradas")
        numero_receita = tracker.get_slot("numero_receita")
        
        if not receitas or not numero_receita:
            dispatcher.utter_message(text="Ups, parece que perdi a lista de receitas. Tenta buscar de novo!")
            return []
        
        try:
            indice = int(numero_receita) - 1
            if indice < 0 or indice >= len(receitas):
                dispatcher.utter_message(text="Número de receita inválido.")
                return []
            
            r = receitas[indice]
            
            # Cabeçalho
            msg = f"🍳 **{r['titulo'].upper()}**\n\n"
            msg += f"⏱️ {r['tempo_total']} | 📊 {r['dificuldade'].title()} | 🔥 {r['calorias']} Kcal\n"
            msg += f"⭐ Rating: {r.get('rating',0)}/5\n\n"
            
            # Critérios (Sem glúten, etc)
            if r['criterios']:
                # Junta a lista bonita
                msg += f"✅ **Info:** {', '.join([c.title() for c in r['criterios']])}\n\n"

            # Ingredientes (Lista com bolinhas)
            msg += "🛒 **Ingredientes:**\n"
            if r['ingredientes']:
                for ing in r['ingredientes']:
                    msg += f"• {ing}\n"
            else:
                msg += "• (Sem ingredientes listados)\n"
            
            # Passos (Lista numerada)
            msg += "\n👨‍🍳 **Passos:**\n"
            if r['passos']:
                for i, passo in enumerate(r['passos'], 1):
                    msg += f"{i}. {passo}\n"
            else:
                msg += "1. Misturar e cozinhar (passos não detalhados).\n"
            
          #  bts = [{"title": "⬅️ Voltar à Lista", "payload": '/voltar'}, {"title": "🔄 Nova Busca", "payload": '/nova_busca'}]
            bts = [{"title": "▶️ Começar modo-a-passo", "payload": "/comecar"},{"title": "⬅️ Voltar à Lista", "payload": "/voltar"},{"title": "🔄 Nova Busca", "payload": "/nova_busca"},]
            dispatcher.utter_message(text=msg, buttons=bts)

           # dispatcher.utter_message(text=msg, buttons=bts)
            return [SlotSet("receita_selecionada", r)]
            
        except Exception as e:
            dispatcher.utter_message(text=f"Erro ao mostrar receita: {str(e)}")
            print(f"Erro detalhado: {e}")
            return []


class ActionResetSlots(Action):
    def name(self) -> Text:
        return "action_reset_slots"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [AllSlotsReset()]
    







class ActionIniciarModoPasso(Action):
    def name(self) -> Text:
        return "action_iniciar_modo_passo"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        receita = tracker.get_slot("receita_selecionada")
        if not receita:
            dispatcher.utter_message(response="utter_sem_receita_selecionada")
            return []

        msg = "Ótimo! Vamos começar. Tens todos os ingredientes?"
        bts = [
            {"title": "✅ Sim, vamos lá", "payload": "/confirmar_ingredientes"},
            {"title": "🛒 Mostrar ingredientes primeiro", "payload": "/mostrar_ingredientes_primeiro"},
        ]
        dispatcher.utter_message(text=msg, buttons=bts)

        return [
            SlotSet("modo_passo", True),
            SlotSet("passo_atual", 1),  # já prepara o passo 1
        ]


class ActionMostrarIngredientesDaReceita(Action):
    def name(self) -> Text:
        return "action_mostrar_ingredientes_da_receita"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        receita = tracker.get_slot("receita_selecionada")
        if not receita:
            dispatcher.utter_message(response="utter_sem_receita_selecionada")
            return []

        ingredientes = receita.get("ingredientes", [])
        msg = "🛒 **Ingredientes:**\n"
        if ingredientes:
            for ing in ingredientes:
                msg += f"• {ing}\n"
        else:
            msg += "• (Sem ingredientes listados)\n"

        msg += "\nVamos começar?"
        bts = [
            {"title": "✅ Sim", "payload": "/confirmar_ingredientes"},
            {"title": "⬅️ Voltar à lista", "payload": "/voltar"},
            {"title": "🔄 Nova busca", "payload": "/nova_busca"},
        ]
        dispatcher.utter_message(text=msg, buttons=bts)
        return []


class ActionMostrarPassoAtual(Action):
    def name(self) -> Text:
        return "action_mostrar_passo_atual"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        receita = tracker.get_slot("receita_selecionada")
        if not receita:
            dispatcher.utter_message(response="utter_sem_receita_selecionada")
            return []

        passos = receita.get("passos", []) or []
        total = len(passos)
        passo_atual = int(tracker.get_slot("passo_atual") or 1)

        if total == 0:
            dispatcher.utter_message(text="Esta receita não tem passos detalhados no dataset 😕")
            return []

        # Normalizar limites
        if passo_atual < 1:
            passo_atual = 1
        if passo_atual > total:
            passo_atual = total

        texto_passo = passos[passo_atual - 1]
        msg = f"**PASSO {passo_atual} de {total}**\n{texto_passo}"

        buttons = []

        # Próximo (sempre)
        # buttons.append({"title": "➡️ Próximo Passo", "payload": "/proximo_passo"})
        
        # Próximo (só se NÃO for o último)
        if passo_atual < total:
            buttons.append({"title": "➡️ Próximo Passo", "payload": "/proximo_passo"})


        # Regressar (só se fizer sentido)
        if passo_atual > 1:
            buttons.append({"title": "⬅️ Regressar Passo", "payload": "/regressar_passo"})

        # Abandonar (sempre)
        buttons.append({"title": "🛑 Abandonar receita", "payload": "/abandonar_receita"})

        # Finalizar (apenas no último passo)
        if passo_atual == total:
            buttons.append({"title": "✅ Finalizar receita", "payload": "/finalizar_receita"})

        dispatcher.utter_message(text=msg, buttons=buttons)
        return [SlotSet("passo_atual", passo_atual)]


class ActionProximoPasso(Action):
    def name(self) -> Text:
        return "action_proximo_passo"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        receita = tracker.get_slot("receita_selecionada")
        passos = (receita or {}).get("passos", []) or []
        total = len(passos)

        passo_atual = int(tracker.get_slot("passo_atual") or 1)
        if total > 0 and passo_atual < total:
            passo_atual += 1

        return [
            SlotSet("passo_atual", passo_atual),
            FollowupAction("action_mostrar_passo_atual"),
        ]



class ActionAbandonarReceita(Action):
    def name(self) -> Text:
        return "action_abandonar_receita"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        dispatcher.utter_message(
            text="Ok — saímos do modo-a-passo. Queres voltar à lista ou fazer uma nova busca?",
            buttons=[
                {"title": "⬅️ Voltar à Lista", "payload": "/voltar"},
                {"title": "🔄 Nova Busca", "payload": "/nova_busca"},
            ],
        )
        return [SlotSet("modo_passo", False), SlotSet("passo_atual", 0)]


class ActionRegressarPasso(Action):
    def name(self) -> Text:
        return "action_regressar_passo"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        passo_atual = int(tracker.get_slot("passo_atual") or 1)
        if passo_atual > 1:
            passo_atual -= 1

        return [
            SlotSet("passo_atual", passo_atual),
            FollowupAction("action_mostrar_passo_atual"),
        ]




class ActionPerguntarAvaliacao(Action):
    def name(self) -> Text:
        return "action_perguntar_avaliacao"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        receita = tracker.get_slot("receita_selecionada")
        if not receita:
            dispatcher.utter_message(response="utter_sem_receita_selecionada")
            return []

        msg = "🎉 Parabéns! Terminaste a receita!\nComo correu?"
        bts = [
            {"title": "1 estrela ⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":1}'},
            {"title": "2 estrelas ⭐⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":2}'},
            {"title": "3 estrelas ⭐⭐⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":3}'},
            {"title": "4 estrelas ⭐⭐⭐⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":4}'},
            {"title": "5 estrelas ⭐⭐⭐⭐⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":5}'},
            {"title": "Não avaliar", "payload": "/nao_avaliar"},
        ]
        dispatcher.utter_message(text=msg, buttons=bts)
        return []


class ActionRegistarRecenteEPerguntarFavoritos(Action):
    def name(self) -> Text:
        return "action_registar_recente_e_perguntar_favoritos"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        receita = tracker.get_slot("receita_selecionada")
        if not receita:
            dispatcher.utter_message(response="utter_sem_receita_selecionada")
            return []

        # ✅ Ler avaliação (do payload /dar_avaliacao{...}) sem depender de slots
        avaliacao = None

        if tracker.latest_message and tracker.latest_message.get("intent", {}).get("name") == "dar_avaliacao":
            for ent in tracker.latest_message.get("entities", []):
                if ent.get("entity") == "avaliacao_utilizador":
                    avaliacao = ent.get("value")
                    break

        # Garantir que escreve como número (e não dict/string estranho)
        try:
            if avaliacao is not None:
                avaliacao = int(float(avaliacao))
        except:
            avaliacao = None

        # Guardar em recentes.csv (sempre)
        caminho = "recentes.csv"
        header = [
            "data_finalizacao",
            "id",
            "titulo", "categoria", "dificuldade", "tempo_total", "tempo_minutos",
            "calorias", "rating_dataset",
            "criterios", "ingredientes", "passos",
            "avaliacao_utilizador"
        ]

        _garantir_csv_com_header(caminho, header)

        data_finalizacao = datetime.now().isoformat(timespec="seconds")
        linha = _receita_para_linha_csv(receita, avaliacao)

        with open(caminho, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([
                data_finalizacao,
                linha["id"],
                linha["titulo"], linha["categoria"], linha["dificuldade"],
                linha["tempo_total"], linha["tempo_minutos"],
                linha["calorias"], linha["rating_dataset"],
                linha["criterios"], linha["ingredientes"], linha["passos"],
                linha["avaliacao_utilizador"],
            ])

        rid = receita.get("id", "")

        if _esta_nos_favoritos(rid):
            dispatcher.utter_message(
                text="Remover dos favoritos?",
                buttons=[
                    {"title": "✅ Sim", "payload": "/remover_sim"},
                    {"title": "❌ Não", "payload": "/remover_nao"},
                ],
            )
        else:
            dispatcher.utter_message(
                text="Guardar nos favoritos?",
                buttons=[
                    {"title": "✅ Sim", "payload": "/favoritar_sim"},
                    {"title": "❌ Não", "payload": "/favoritar_nao"},
                ],
            )

        return []




class ActionGuardarFavoritosCSV(Action):
    def name(self) -> Text:
        return "action_guardar_favoritos_csv"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        receita = tracker.get_slot("receita_selecionada")
        if not receita:
            dispatcher.utter_message(response="utter_sem_receita_selecionada")
            return []

        caminho = "favoritos.csv"
        header = [
            "data_favorito",
            "id",
            "titulo", "categoria", "dificuldade", "tempo_total", "tempo_minutos",
            "calorias", "rating_dataset",
            "criterios", "ingredientes", "passos"
        ]

        _garantir_csv_com_header(caminho, header)

        data_favorito = datetime.now().isoformat(timespec="seconds")
        linha = _receita_para_linha_csv(receita, None)

        with open(caminho, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([
                data_favorito,
                linha["id"],
                linha["titulo"], linha["categoria"], linha["dificuldade"],
                linha["tempo_total"], linha["tempo_minutos"],
                linha["calorias"], linha["rating_dataset"],
                linha["criterios"], linha["ingredientes"], linha["passos"],
            ])


        dispatcher.utter_message(text="Feito ✅ Guardei nos teus favoritos!")
        return []



class ActionRemoverFavoritosCSV(Action):
    def name(self) -> Text:
        return "action_remover_favoritos_csv"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        receita = tracker.get_slot("receita_selecionada")
        if not receita:
            dispatcher.utter_message(response="utter_sem_receita_selecionada")
            return []

   
        rid = receita.get("id", "")
        ok = _remover_dos_favoritos(rid)


        if ok:
            dispatcher.utter_message(text="Feito ✅ Removi dos teus favoritos!")
        else:
            dispatcher.utter_message(text="Não encontrei essa receita nos favoritos 🙂")

        return []

























def _ler_csv_dicts(caminho: str) -> List[Dict[str, Any]]:
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


class ActionMostrarRecentesResumo(Action):
    def name(self) -> Text:
        return "action_mostrar_recentes_resumo"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        rows = _ler_csv_dicts("recentes.csv")
        total = len(rows)

        if total == 0:
            dispatcher.utter_message(text="Ainda não tenho registo de receitas feitas 🙂")
            return []

        # Mais feita (por id)
        counts: Dict[str, int] = {}
        titulo_por_id: Dict[str, str] = {}
        for r in rows:
            rid = (r.get("id", "") or "").strip()
            titulo = (r.get("titulo", "") or "").strip()
            if rid:
                counts[rid] = counts.get(rid, 0) + 1
                if rid not in titulo_por_id and titulo:
                    titulo_por_id[rid] = titulo

        mais_feita_id = max(counts, key=counts.get) if counts else ""
        mais_feita_titulo = titulo_por_id.get(mais_feita_id, "—")

        # Última (pela data mais recente)
        # ISO strings ordenam bem lexicograficamente se estiverem no formato YYYY-MM-DDTHH:MM:SS
        ultima = max(rows, key=lambda x: (x.get("data_finalizacao", "") or ""))
        ultima_titulo = (ultima.get("titulo", "") or "—").strip()

        msg = (
            f"Tens {total} receitas feitas recentes:\n\n"
            f"⭐ Mais feita: {mais_feita_titulo}\n"
            f"📅 Última: {ultima_titulo}\n"
        )


        dispatcher.utter_message(
            text=msg,
            buttons=[
                {"title": "📋 Ver Todas", "payload": "/recentes_ver_todas"},
                {"title": "🗂️ Por Categoria", "payload": "/recentes_por_categoria"},
                {"title": "⬅️ Voltar", "payload": "/ajuda"},
            ],
        )

        
        return []


class ActionMostrarRecentesTodas(Action):
    def name(self) -> Text:
        return "action_mostrar_recentes_todas"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        rows = _ler_csv_dicts("recentes.csv")
        if not rows:
            dispatcher.utter_message(text="Ainda não tenho receitas recentes registadas 🙂")
            return []

        # ordenar por data desc
        rows.sort(key=lambda x: (x.get("data_finalizacao", "") or ""), reverse=True)

        msg = f"📋 As tuas receitas mais recentes ({len(rows)}):\n\n"
        for i, r in enumerate(rows[:10], 1):  # top 10 para não ficar gigante
            msg += f"{i}. {r.get('titulo','—')} — {r.get('data_finalizacao','')}\n"

        dispatcher.utter_message(
            text=msg,
            buttons=[{"title": "⬅️ Voltar", "payload": "/listar_recentes"}],
        )
        return []


class ActionMostrarRecentesPorCategoria(Action):
    def name(self) -> Text:
        return "action_mostrar_recentes_por_categoria"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        rows = _ler_csv_dicts("recentes.csv")
        if not rows:
            dispatcher.utter_message(text="Ainda não tenho receitas recentes registadas 🙂")
            return []

        counts: Dict[str, int] = {}
        for r in rows:
            cat = (r.get("categoria", "") or "sem categoria").strip().lower()
            counts[cat] = counts.get(cat, 0) + 1

        msg = "🗂️ Recentes por categoria:\n\n"
        for cat, n in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            msg += f"• {cat}: {n}\n"

        dispatcher.utter_message(
            text=msg,
            buttons=[{"title": "⬅️ Voltar", "payload": "/listar_recentes"}],
        )
        return []


class ActionMostrarFavoritosLista(Action):
    def name(self) -> Text:
        return "action_mostrar_favoritos_lista"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        fav_rows = _ler_csv_dicts("favoritos.csv")
        if not fav_rows:
            dispatcher.utter_message(text="Ainda não tens receitas guardadas nos favoritos 🙂")
            return []

        # Ordenar por data desc (favoritos mais recentes primeiro)
        fav_rows.sort(key=lambda x: (x.get("data_favorito", "") or ""), reverse=True)

        # Carregar dataset completo para ir buscar detalhes por id
        todas = carregar_receitas()
        por_id = {r.get("id", ""): r for r in todas if r.get("id", "")}

        favoritos_receitas = []
        for row in fav_rows:
            rid = (row.get("id", "") or "").strip()
            if rid and rid in por_id:
                favoritos_receitas.append(por_id[rid])

        if not favoritos_receitas:
            dispatcher.utter_message(text="Tens favoritos guardados, mas não consegui encontrá-los no recipes.csv 😕")
            return []

        # Limitar a 5 (como no teu exemplo). Se quiseres mais, muda aqui.
        favoritos_receitas = favoritos_receitas[:5]

        # Construir mensagem no mesmo formato do ActionMostrarReceitas
        msg = f"Tens {len(fav_rows)} receitas guardadas nos favoritos:\n\n"
        buttons = []

        for i, receita in enumerate(favoritos_receitas, 1):
            dificuldade_lower = receita.get("dificuldade", "")
            emoji = "🍽️"
            if "fácil" in dificuldade_lower:
                emoji = "😊"
            elif "médio" in dificuldade_lower:
                emoji = "🤔"
            elif "difícil" in dificuldade_lower:
                emoji = "😤"

            msg += f"{i}. {emoji} **{receita.get('titulo', '')}**\n"
            msg += f"   ⏱️ {receita.get('tempo_total', '')} | 🔥 {receita.get('calorias', 0)} Kcal\n\n"

            buttons.append({
                "title": f"Ver {i}: {receita.get('titulo','')}",
                "payload": f'/ver_receita{{"numero_receita":"{i}"}}'
            })

        # Botões extra como pediste
        buttons.append({"title": "🗂️ Por categoria", "payload": "/favoritos_por_categoria"})
        buttons.append({"title": "🔄 Nova Busca", "payload": "/nova_busca"})

        dispatcher.utter_message(text=msg, buttons=buttons)

        # ✅ IMPORTANTÍSSIMO: guardar no slot para o fluxo /ver_receita funcionar igual
        return [SlotSet("receitas_encontradas", favoritos_receitas)]



class ActionMostrarFavoritosPorCategoria(Action):
    def name(self) -> Text:
        return "action_mostrar_favoritos_por_categoria"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        rows = _ler_csv_dicts("favoritos.csv")
        if not rows:
            dispatcher.utter_message(text="Ainda não tens favoritos 🙂")
            return []

        # Contagens normalizadas
        count_entrada = 0
        count_prato_principal = 0
        count_sobremesa = 0

        for r in rows:
            cat = (r.get("categoria", "") or "").strip().lower()

            if "entrada" in cat:
                count_entrada += 1
            elif "prato principal" in cat or "prato_principal" in cat:
                count_prato_principal += 1
            elif "sobremesa" in cat:
                count_sobremesa += 1

        msg = "🗂️ Favoritos por categoria:\n\nEscolhe uma categoria:"

        dispatcher.utter_message(
            text=msg,
            buttons=[
                {"title": f"Entrada ({count_entrada})", "payload": '/favoritos_filtrar_categoria{"categoria":"entrada"}'},
                {"title": f"Prato Principal ({count_prato_principal})", "payload": '/favoritos_filtrar_categoria{"categoria":"prato_principal"}'},
                {"title": f"Sobremesa ({count_sobremesa})", "payload": '/favoritos_filtrar_categoria{"categoria":"sobremesa"}'},
                {"title": "⬅️ Voltar", "payload": "/listar_favoritos"},
            ],
        )
        return []





class ActionMostrarFavoritosFiltradosPorCategoria(Action):
    def name(self) -> Text:
        return "action_mostrar_favoritos_filtrados_por_categoria"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        categoria_slot = (tracker.get_slot("categoria") or "").strip().lower()

        fav_rows = _ler_csv_dicts("favoritos.csv")
        if not fav_rows:
            dispatcher.utter_message(text="Ainda não tens receitas guardadas nos favoritos 🙂")
            return []

        # Carregar dataset completo para ir buscar detalhes por id
        todas = carregar_receitas()
        por_id = {r.get("id", ""): r for r in todas if r.get("id", "")}

        # Converter favoritos.csv -> lista de receitas (do dataset)
        favoritos_receitas = []
        for row in fav_rows:
            rid = (row.get("id", "") or "").strip()
            if rid and rid in por_id:
                favoritos_receitas.append(por_id[rid])

        if not favoritos_receitas:
            dispatcher.utter_message(text="Tens favoritos guardados, mas não consegui encontrá-los no recipes.csv 😕")
            return []

        # Filtrar por categoria escolhida
        def match_categoria(cat_receita: str) -> bool:
            c = (cat_receita or "").strip().lower()

            if categoria_slot == "entrada":
                return "entrada" in c
            if categoria_slot == "prato_principal":
                return ("prato principal" in c) or ("prato_principal" in c)
            if categoria_slot == "sobremesa":
                return "sobremesa" in c

            return False

        filtradas = [r for r in favoritos_receitas if match_categoria(r.get("categoria", ""))]

        # Títulos bonitos
        nome_cat = {
            "entrada": "Entrada",
            "prato_principal": "Prato Principal",
            "sobremesa": "Sobremesa",
        }.get(categoria_slot, "Categoria")

        if not filtradas:
            dispatcher.utter_message(
                text=f"Não tens receitas favoritas na categoria **{nome_cat}** 🙂",
                buttons=[{"title": "⬅️ Voltar", "payload": "/favoritos_por_categoria"}],
            )
            return []

        # Construir mensagem no mesmo estilo do ActionMostrarReceitas (com botões Ver 1..N)
        msg = f"Tens {len(filtradas)} receitas guardadas nos favoritos (**{nome_cat}**):\n\n"
        buttons = []

        for i, receita in enumerate(filtradas, 1):
            dificuldade_lower = (receita.get("dificuldade", "") or "").lower()
            emoji = "🍽️"
            if "fácil" in dificuldade_lower:
                emoji = "😊"
            elif "médio" in dificuldade_lower:
                emoji = "🤔"
            elif "difícil" in dificuldade_lower:
                emoji = "😤"

            msg += f"{i}. {emoji} **{receita.get('titulo','')}**\n"
            msg += f"   ⏱️ {receita.get('tempo_total','')} | 🔥 {receita.get('calorias',0)} Kcal\n\n"

            buttons.append({
                "title": f"Ver {i}: {receita.get('titulo','')}",
                "payload": f'/ver_receita{{"numero_receita":"{i}"}}'
            })

        buttons.append({"title": "⬅️ Voltar", "payload": "/favoritos_por_categoria"})
        buttons.append({"title": "🔄 Nova Busca", "payload": "/nova_busca"})

        dispatcher.utter_message(text=msg, buttons=buttons)

        # IMPORTANTÍSSIMO: guardar para o /ver_receita funcionar como sempre
        return [SlotSet("receitas_encontradas", filtradas)]
