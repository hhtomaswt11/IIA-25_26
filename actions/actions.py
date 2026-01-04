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
            
            bts = [{"title": "⬅️ Voltar à Lista", "payload": '/voltar'}, {"title": "🔄 Nova Busca", "payload": '/nova_busca'}]
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