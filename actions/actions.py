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
        caminho_csv = os.path.join("db", "recipes.csv")

    if not os.path.exists(caminho_csv):
        print(f"❌ ERRO CRÍTICO: Não encontrei 'recipes.csv'.")
        return []
    
    try:
        with open(caminho_csv, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file, delimiter=';')
            
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
                        if 'h' in tempo_total.lower():
                            horas = int(numeros[0])
                            minutos = int(numeros[1]) if len(numeros) > 1 else 0
                            tempo_minutos = (horas * 60) + minutos
                        else:
                            tempo_minutos = int(numeros[0])
                
                # --- 3. TRATAMENTO DE NÚMEROS ---
                # Calorias (remove "Kcal")
                calorias_str = row.get('calorias', '0').lower().replace('kcal', '').strip()
                try:
                    calorias = int(calorias_str)
                except:
                    calorias = 0

                # Rating
                rating_str = row.get('rating', '0').replace(',', '.').strip()
                try:
                    rating = float(rating_str)
                except:
                    rating = 0.0
                
                # --- 4. PORÇÕES (NOVO CAMPO) ---
                porcoes_str = row.get('porcoes', '0').strip()
                try:
                    porcoes = int(float(porcoes_str)) if porcoes_str else 0
                except:
                    porcoes = 0
                
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
                    'porcoes': porcoes,  
                    'ingredientes': ingredientes, 
                    'passos': passos,            
                    'criterios': criterios,
                    'imagem': row.get('imagem', '').strip()
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
        "porcoes": receita.get("porcoes", ""),  # ← NOVO
        "criterios": "|".join(receita.get("criterios", []) or []),
        "ingredientes": "|".join(receita.get("ingredientes", []) or []),
        "passos": "|".join(receita.get("passos", []) or []),
        "imagem": receita.get("imagem", ""),
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

        # 1. Categoria
        if categoria:
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
        if restricao and restricao not in ["nenhuma"]:
            restricao_map = {
                "vegetariano": "vegetariano",
                "vegano": "vegan",
                "sem_gluten": "sem glúten",
                "sem_lactose": "sem lactose",
                "sem_acucar": "sem açúcar",  
                "sem_ovo": "sem ovo",         
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
        elif preferencia_calorica == "reforçado":          # <-- NOVO
            receitas_filtradas = [r for r in receitas_filtradas if 600 < r["calorias"] <= 900]
        elif preferencia_calorica == "hipercalorico":      # <-- NOVO
            receitas_filtradas = [r for r in receitas_filtradas if r["calorias"] > 900]
            
        # Ordenar por rating (melhores primeiro) e pegar top 5
        receitas_filtradas.sort(key=lambda x: x['rating'], reverse=True)
        receitas_filtradas = receitas_filtradas[:5]
        
        return [SlotSet("receitas_encontradas", receitas_filtradas)]

class ActionBuscarPorIngredientes(Action):
    def name(self) -> Text:
        return "action_buscar_por_ingredientes"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # 1. Obter a lista de ingredientes que o utilizador disse que tem
        ingredientes_utilizador = tracker.get_slot("lista_ingredientes_possuido")
        
        if not ingredientes_utilizador:
            dispatcher.utter_message(text="Não percebi quais ingredientes tens. Podes repetir? (Ex: tenho batata e ovos)")
            return []

        print(f"🔍 Ingredientes do utilizador: {ingredientes_utilizador}")

        todas_receitas = carregar_receitas() # Usa a tua função existente
        receitas_pontuadas = []

        # 2. Lógica de Matching
        # Vamos contar quantos ingredientes da receita o utilizador TEM.
        for receita in todas_receitas:
            matches = 0
            ingredientes_receita_str = " ".join(receita['ingredientes']).lower()
            
            # Verifica cada ingrediente do user contra a lista da receita
            for ing_user in ingredientes_utilizador:
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
            dispatcher.utter_message(text=f"Não encontrei receitas específicas com {', '.join(ingredientes_utilizador)}. Tenta outros ingredientes!")
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
        
        buttons.append({"title": "🔄 Nova busca", "payload": '/nova_busca'})
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
            
            # NOVO: Verificar se tem imagem
            imagem = r.get('imagem', '')
            
            # Cabeçalho
            msg = ""
            
            # Se tiver imagem, adiciona uma marcação especial para o frontend
            if imagem:
                msg += f"![{r['titulo']}]({imagem})\n\n"
            
            msg += f"🍳 **{r['titulo'].upper()}**\n\n"
            msg += f"⏱️ {r['tempo_total']} | 📊 {r['dificuldade'].title()} | 🔥 {r['calorias']} Kcal\n"
            msg += f"👥 Porções: {r.get('porcoes', 1)}\n"
            msg += f"⭐ Rating: {r.get('rating',0)}/5\n"
                                
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
            
            bts = [
                {"title": "▶️ Começar modo-a-passo", "payload": "/comecar"},
                {"title": "⬅️ Voltar à lista", "payload": "/voltar"},
                {"title": "🔄 Nova busca", "payload": "/nova_busca"},
            ]
            dispatcher.utter_message(text=msg, buttons=bts)

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

        # Próximo (só se NÃO for o último)
        if passo_atual < total:
            buttons.append({"title": "➡️ Próximo passo", "payload": "/proximo_passo"})
        # Regressar (só se fizer sentido)
        if passo_atual > 1:
            buttons.append({"title": "⬅️ Regressar passo", "payload": "/regressar_passo"})
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
                {"title": "⬅️ Voltar à lista", "payload": "/voltar"},
                {"title": "🔄 Nova busca", "payload": "/nova_busca"},
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

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        receita = tracker.get_slot("receita_selecionada")
        if not receita:
            dispatcher.utter_message(response="utter_sem_receita_selecionada")
            return []

        # VERIFICAÇÃO CRÍTICA: Se o usuário escolheu "não avaliar"
        intent_name = tracker.latest_message.get("intent", {}).get("name") if tracker.latest_message else ""
        
        if intent_name == "nao_avaliar":
            # Não avaliar - prosseguir sem avaliação
            avaliacao = None
            print("✅ Usuário escolheu não avaliar. Prosseguindo sem avaliação.")
        else:
            # Caso contrário, tentar extrair avaliação normalmente
            avaliacao = None
            
            # Método 1: Tentar extrair da entidade (quando vem do payload dos botões)
            if tracker.latest_message and tracker.latest_message.get("intent", {}).get("name") == "dar_avaliacao":
                for ent in tracker.latest_message.get("entities", []):
                    if ent.get("entity") == "avaliacao_utilizador":
                        avaliacao = ent.get("value")
                        break
            
            # Método 2: Se não encontrou, extrair diretamente do texto
            if avaliacao is None:
                texto = tracker.latest_message.get("text", "").lower()
                
                # Mapear palavras por extenso
                mapa_palavras = {
                    "uma": 1, "um": 1,
                    "duas": 2, "dois": 2,
                    "tres": 3, "três": 3,
                    "quatro": 4,
                    "cinco": 5
                }
                
                # Procurar número explícito (1, 2, 3, etc)
                numeros_encontrados = re.findall(r'\b([1-5])\b', texto)
                if numeros_encontrados:
                    avaliacao = int(numeros_encontrados[0])
                else:
                    # Procurar palavra por extenso
                    for palavra, num in mapa_palavras.items():
                        if palavra in texto:
                            avaliacao = num
                            break
            
            # Validar avaliação
            if avaliacao is not None:
                try:
                    avaliacao = int(float(avaliacao))
                    # ✅ VALIDAÇÃO: Só aceitar entre 1-5
                    if avaliacao < 1 or avaliacao > 5:
                        dispatcher.utter_message(
                            text=f"⚠️ A avaliação deve ser entre 1 e 5 estrelas. Não é permitido: {avaliacao}",
                            buttons=[
                                {"title": "1 estrela ⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":1}'},
                                {"title": "2 estrelas ⭐⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":2}'},
                                {"title": "3 estrelas ⭐⭐⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":3}'},
                                {"title": "4 estrelas ⭐⭐⭐⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":4}'},
                                {"title": "5 estrelas ⭐⭐⭐⭐⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":5}'},
                            ]
                        )
                        return []
                except:
                    avaliacao = None

            # Se ainda não conseguiu extrair e NÃO foi intenção de não avaliar, pedir novamente
            if avaliacao is None and intent_name != "nao_avaliar":
                dispatcher.utter_message(
                    text="⚠️ Não consegui perceber a avaliação. Escolhe um número de 1 a 5:",
                    buttons=[
                        {"title": "1 estrela ⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":1}'},
                        {"title": "2 estrelas ⭐⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":2}'},
                        {"title": "3 estrelas ⭐⭐⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":3}'},
                        {"title": "4 estrelas ⭐⭐⭐⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":4}'},
                        {"title": "5 estrelas ⭐⭐⭐⭐⭐", "payload": '/dar_avaliacao{"avaliacao_utilizador":5}'},
                        {"title": "Não avaliar", "payload": "/nao_avaliar"},
                    ]
                )
                return []

            print(f"✅ AVALIAÇÃO EXTRAÍDA: {avaliacao}")

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
                    {"title": "✅ Sim, remover", "payload": "/remover_sim"},
                    {"title": "❌ Não, não remover", "payload": "/remover_nao"},
                ],
            )
        else:
            dispatcher.utter_message(
                text="Guardar nos favoritos?",
                buttons=[
                    {"title": "✅ Sim, guardar", "payload": "/favoritar_sim"},
                    {"title": "❌ Não guardar", "payload": "/favoritar_nao"},
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
            "criterios", "ingredientes", "passos", 
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

def _carregar_avaliacoes_recentes() -> Dict[str, str]:
    """Carrega avaliações do recentes.csv e mapeia ID -> avaliação_utilizador"""
    avaliacoes = {}
    rows = _ler_csv_dicts("recentes.csv")
    for row in rows:
        rid = (row.get("id", "") or "").strip()
        avaliacao = (row.get("avaliacao_utilizador", "") or "").strip()
        if rid and avaliacao:
            # Remove aspas ou espaços extras
            avaliacao_limpa = avaliacao.replace('"', '').replace("'", "").strip()
            if avaliacao_limpa and avaliacao_limpa != "None" and avaliacao_limpa != "null":
                avaliacoes[rid] = avaliacao_limpa
    return avaliacoes

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
                {"title": "📋 Ver todas", "payload": "/recentes_ver_todas"},
                {"title": "🗂️ Por categoria", "payload": "/recentes_por_categoria"},
            ],
        )
        return []
    
class ActionMostrarRecentesTodas(Action):
    def name(self) -> Text:
        return "action_mostrar_recentes_todas"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        rows = _ler_csv_dicts("recentes.csv")
        if not rows:      
            dispatcher.utter_message(
                text="Ainda não tenho receitas recentes registadas 🙂",
                buttons=[{"title": "⬅️ Listar recentes", "payload": "/listar_recentes"}],
            )
            return []

        # Carregar avaliações
        avaliacoes = _carregar_avaliacoes_recentes()
        
        # Ordenar por data desc (mais recentes primeiro)
        rows.sort(key=lambda x: (x.get("data_finalizacao", "") or ""), reverse=True)

        # Carregar dataset completo para ir buscar detalhes por id
        todas = carregar_receitas()
        por_id = {r.get("id", ""): r for r in todas if r.get("id", "")}

        # Converter recentes.csv -> lista de receitas (do dataset) com avaliação
        recentes_receitas = []
        for row in rows:
            rid = (row.get("id", "") or "").strip()
            if rid and rid in por_id:
                receita = por_id[rid].copy()
                # Adicionar a avaliação do utilizador ao objeto da receita
                receita['avaliacao_utilizador'] = avaliacoes.get(rid, "")
                recentes_receitas.append(receita)

        if not recentes_receitas:
            dispatcher.utter_message(
                text="Tens receitas recentes registadas, mas não consegui encontrá-las no recipes.csv 😕",
                buttons=[{"title": "⬅️ Voltar", "payload": "/listar_recentes"}],
            )
            return []

        # Limitar a 10 receitas (ajusta se quiseres mais)
        recentes_receitas = recentes_receitas[:10]

        # ✅ CONSTRUIR MENSAGEM COM AVALIAÇÃO DO UTILIZADOR
        msg = f"Tens {len(rows)} receitas feitas recentes:\n\n"
        buttons = []

        for i, receita in enumerate(recentes_receitas, 1):
            dificuldade_lower = (receita.get("dificuldade", "") or "").lower()
            emoji = "🍽️"
            if "fácil" in dificuldade_lower:
                emoji = "😊"
            elif "médio" in dificuldade_lower:
                emoji = "🤔"
            elif "difícil" in dificuldade_lower:
                emoji = "😤"

            # Obter avaliação do utilizador
            avaliacao = receita.get('avaliacao_utilizador', '')
            if avaliacao and avaliacao != 'None' and avaliacao != 'null':
                linha_avaliacao = f" | ⭐ {avaliacao}"
            else:
                linha_avaliacao = " | ⭐ Não avaliou"

            msg += f"{i}. {emoji} **{receita.get('titulo', '')}**\n"
            msg += f"   ⏱️ {receita.get('tempo_total', '')} | 🔥 {receita.get('calorias', 0)} Kcal{linha_avaliacao}\n\n"

            buttons.append({
                "title": f"Ver {i}: {receita.get('titulo','')}",
                "payload": f'/ver_receita{{"numero_receita":"{i}"}}'
            })

        # Botões de navegação
        buttons.append({"title": "⬅️ Listar recentes", "payload": "/listar_recentes"})
        buttons.append({"title": "🔄 Nova busca", "payload": "/nova_busca"})

        dispatcher.utter_message(text=msg, buttons=buttons)

        # ✅ CRÍTICO: Guardar no slot para /ver_receita funcionar
        # IMPORTANTE: Não guardar a avaliação no slot para não interferir com outras ações
        receitas_sem_avaliacao = [{k: v for k, v in r.items() if k != 'avaliacao_utilizador'} for r in recentes_receitas]
        return [SlotSet("receitas_encontradas", receitas_sem_avaliacao)]
        
class ActionMostrarRecentesPorCategoria(Action):
    def name(self) -> Text:
        return "action_mostrar_recentes_por_categoria"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        rows = _ler_csv_dicts("recentes.csv")
        if not rows:
            dispatcher.utter_message(text="Ainda não tenho receitas recentes registadas 🙂")
            return []

        # Contagens por categoria (baseadas no CSV)
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

        msg = "🗂️ Recentes por categoria:\n\nEscolhe uma categoria:"

        dispatcher.utter_message(
            text=msg,
            buttons=[
                {"title": f"Entrada ({count_entrada})", "payload": '/recentes_filtrar_categoria{"categoria":"entrada"}'},
                {"title": f"Prato principal ({count_prato_principal})", "payload": '/recentes_filtrar_categoria{"categoria":"prato_principal"}'},
                {"title": f"Sobremesa ({count_sobremesa})", "payload": '/recentes_filtrar_categoria{"categoria":"sobremesa"}'},
                {"title": "⬅️ Listar recentes", "payload": "/listar_recentes"},  # ALTERADO
            ],
        )
        return []


class ActionMostrarRecentesFiltradosPorCategoria(Action):
    def name(self) -> Text:
        return "action_mostrar_recentes_filtrados_por_categoria"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        categoria_slot = (tracker.get_slot("categoria") or "").strip().lower()

        rows = _ler_csv_dicts("recentes.csv")
        if not rows:
            dispatcher.utter_message(text="Ainda não tenho receitas recentes registadas 🙂")
            return []

        # Carregar avaliações
        avaliacoes = _carregar_avaliacoes_recentes()

        def match_categoria(cat: str) -> bool:
            c = (cat or "").strip().lower()

            if categoria_slot == "entrada":
                return "entrada" in c
            if categoria_slot in ["prato_principal", "prato principal"]:
                return ("prato principal" in c) or ("prato_principal" in c)
            if categoria_slot == "sobremesa":
                return "sobremesa" in c

            return False

        filtradas_rows = [r for r in rows if match_categoria(r.get("categoria", ""))]

        # Normalizar o slot para ter sempre underscore
        categoria_normalizada = categoria_slot.replace(" ", "_")

        nome_cat = {
            "entrada": "Entrada",
            "prato_principal": "Prato Principal",
            "sobremesa": "Sobremesa",
        }.get(categoria_normalizada, "Categoria")

        if not filtradas_rows:
            dispatcher.utter_message(
                text=f"Não tens receitas recentes na categoria **{nome_cat}** 🙂",
                buttons=[{"title": "⬅️ Por categoria", "payload": "/recentes_por_categoria"}],
            )
            return []

        # ordenar por data desc (mais recentes primeiro)
        filtradas_rows.sort(key=lambda x: (x.get("data_finalizacao", "") or ""), reverse=True)

        # Carregar receitas completas e mapear por id
        todas = carregar_receitas()
        por_id = {r.get("id", ""): r for r in todas if r.get("id", "")}

        receitas = []
        for row in filtradas_rows:
            rid = (row.get("id", "") or "").strip()
            if rid and rid in por_id:
                receita = por_id[rid].copy()
                # Adicionar a avaliação do utilizador ao objeto da receita
                receita['avaliacao_utilizador'] = avaliacoes.get(rid, "")
                receitas.append(receita)

        if not receitas:
            dispatcher.utter_message(
                text=f"Tens registos recentes em **{nome_cat}**, mas não consegui encontrá-los no recipes.csv 😕",
                buttons=[{"title": "⬅️ Por categoria", "payload": "/recentes_por_categoria"}],
            )
            return []

        # Limitar a 5 (como exemplo dos favoritos) — ajusta se quiseres
        receitas = receitas[:5]

        msg = f"Tens {len(filtradas_rows)} receitas feitas recentes (**{nome_cat}**):\n\n"
        buttons = []

        for i, receita in enumerate(receitas, 1):
            dificuldade_lower = (receita.get("dificuldade", "") or "").lower()
            emoji = "🍽️"
            if "fácil" in dificuldade_lower:
                emoji = "😊"
            elif "médio" in dificuldade_lower:
                emoji = "🤔"
            elif "difícil" in dificuldade_lower:
                emoji = "😤"

            # Obter avaliação do utilizador
            avaliacao = receita.get('avaliacao_utilizador', '')
            if avaliacao and avaliacao != 'None' and avaliacao != 'null':
                linha_avaliacao = f" | ⭐ {avaliacao}"
            else:
                linha_avaliacao = " | ⭐ Não avaliou"

            msg += f"{i}. {emoji} **{receita.get('titulo','')}**\n"
            msg += f"   ⏱️ {receita.get('tempo_total','')} | 🔥 {receita.get('calorias',0)} Kcal{linha_avaliacao}\n\n"

            buttons.append({
                "title": f"Ver {i}: {receita.get('titulo','')}",
                "payload": f'/ver_receita{{"numero_receita":"{i}"}}'
            })

        buttons.append({"title": "⬅️ Por categoria", "payload": "/recentes_por_categoria"})
        buttons.append({"title": "🔄 Nova busca", "payload": "/nova_busca"})

        dispatcher.utter_message(text=msg, buttons=buttons)

        # ✅ guardar para o /ver_receita funcionar como sempre
        # Remover a avaliação do objeto para não interferir com outras ações
        receitas_sem_avaliacao = [{k: v for k, v in r.items() if k != 'avaliacao_utilizador'} for r in receitas]
        return [SlotSet("receitas_encontradas", receitas_sem_avaliacao)]

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
        buttons.append({"title": "🔄 Nova busca", "payload": "/nova_busca"})

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
                {"title": f"Prato principal ({count_prato_principal})", "payload": '/favoritos_filtrar_categoria{"categoria":"prato_principal"}'},
                {"title": f"Sobremesa ({count_sobremesa})", "payload": '/favoritos_filtrar_categoria{"categoria":"sobremesa"}'},
                {"title": "⬅️ Listar favoritos", "payload": "/listar_favoritos"},  # ALTERADO
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
            if categoria_slot == "prato_principal" or categoria_slot == "prato principal":
                return ("prato principal" in c) or ("prato_principal" in c)
            if categoria_slot == "sobremesa":
                return "sobremesa" in c

            return False

        # ✅ ESTA LINHA ESTAVA A FALTAR!
        filtradas = [r for r in favoritos_receitas if match_categoria(r.get("categoria", ""))]

        # Normalizar o slot para ter sempre underscore
        categoria_normalizada = categoria_slot.replace(" ", "_")
        
        # Títulos bonitos
        nome_cat = {
            "entrada": "Entrada",
            "prato_principal": "Prato Principal",
            "sobremesa": "Sobremesa",
        }.get(categoria_normalizada, "Categoria")

        if not filtradas:
            dispatcher.utter_message(
                text=f"Não tens receitas favoritas na categoria **{nome_cat}** 🙂",
                buttons=[{"title": "⬅️ Por categoria", "payload": "/favoritos_por_categoria"}],
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

        buttons.append({"title": "⬅️ Por categoria", "payload": "/favoritos_por_categoria"})
        buttons.append({"title": "🔄 Nova busca", "payload": "/nova_busca"})

        dispatcher.utter_message(text=msg, buttons=buttons)

        # IMPORTANTÍSSIMO: guardar para o /ver_receita funcionar como sempre
        return [SlotSet("receitas_encontradas", filtradas)]
    
        
class ActionBuscarPorNome(Action):
    def name(self) -> Text:
        return "action_buscar_por_nome"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        nome_receita = tracker.get_slot("nome_receita")
        
        if not nome_receita:
            dispatcher.utter_message(text="Não percebi que receita queres. Podes repetir?")
            return []

        todas_receitas = carregar_receitas()
        receitas_pontuadas = []
        nome_busca = nome_receita.lower().strip()

        print(f"🔍 BUSCA POR NOME: '{nome_busca}'")
        
        # Palavras que não ajudam na busca
        palavras_ignorar = ["de", "com", "em", "para", "do", "da", "os", "as", "a", "o", "um", "uma", "quero", "fazer", "cozinhar"]
        palavras_chave = [p for p in nome_busca.split() if p not in palavras_ignorar and len(p) > 2]
        
        print(f"📝 PALAVRAS-CHAVE EXTRAÍDAS: {palavras_chave}")

        for receita in todas_receitas:
            titulo_receita = receita['titulo'].lower()
            
            score = 0
            
            # 1. TÍTULO - PESO MÁXIMO (95% do score)
            # matches_titulo = sum(1 for p in palavras_chave if p in titulo_receita)
            titulo_palavras = re.findall(r'\b\w+\b', titulo_receita)

            matches_titulo = sum(1 for p in palavras_chave if p in titulo_palavras)

            
            if matches_titulo > 0:
                # Peso massivo para matches no título
                score += matches_titulo * 1000
                
                # Bónus gigante se o nome exato estiver no título
                if nome_busca in titulo_receita:
                    score += 5000
                
                # Bónus extra se o título começar com a palavra-chave
                for palavra in palavras_chave:
                    if titulo_receita.startswith(palavra):
                        score += 2000
                
                print(f"  ✅ '{receita['titulo']}' → Score: {score} (matches título: {matches_titulo})")
            
            # 2. INGREDIENTES - PESO MÍNIMO (apenas para desempate fino)
            if matches_titulo > 0:
                ingredientes_texto = " ".join(receita['ingredientes']).lower()
                # Remove termos de medição para evitar falsos positivos
                ingredientes_limpos = re.sub(r'colher(es)?\s*(de\s*)?(sopa|sobremesa|chá|café)', '', ingredientes_texto)
                matches_ingredientes = sum(1 for p in palavras_chave if p in ingredientes_limpos)
                score += matches_ingredientes * 1  # Peso insignificante

            # 3. Bónus de qualidade (muito pequeno, apenas desempate)
            score += (receita['rating'] * 0.5)

            # 4. Penalização de tamanho (favorece títulos mais curtos e precisos)
            score -= (len(titulo_receita) * 0.5)

            # Só adiciona se tiver match no título (score > 500)
            if score > 500: 
                receitas_pontuadas.append((score, receita))

        print(f"\n📊 TOTAL FILTRADAS: {len(receitas_pontuadas)} receitas")

        # Ordenar por pontuação
        receitas_pontuadas.sort(key=lambda x: x[0], reverse=True)
        
        # Retorna as TOP 10
        top_receitas = [r[1] for r in receitas_pontuadas[:10]]  # Top 10 receitas com maior pontuação
        
        print(f"🏆 TOP 10 FINAL:")
        for i, (score, r) in enumerate(receitas_pontuadas[:10], 1):
            print(f"  {i}. {r['titulo']} (Score: {score:.1f})")

        if not top_receitas:
            dispatcher.utter_message(
                text=f"Não encontrei receitas de '{nome_receita}'. Queres tentar outro termo?",
                buttons=[{"title": "🔄 Nova busca", "payload": "/nova_busca"}]
            )
            return [SlotSet("nome_receita", None)]

        return [
            SlotSet("receitas_encontradas", top_receitas),
            FollowupAction("action_mostrar_receitas")
        ]


