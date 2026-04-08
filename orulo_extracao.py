"""
Script de Extração Diária — API Órulo
Projeto: Análise da Concorrência | Prestes
Objetivo: Extrair todos os empreendimentos das praças configuradas
          e salvar em arquivo fixo no OneDrive para atualização do Power BI.

Uso:
    python orulo_extracao.py

Agendamento:
    Configurado via Agendador de Tarefas do Windows (rodar_extracao.bat)

Dependências:
    pip install requests pandas openpyxl
"""

import requests
import pandas as pd
import os
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────
# Localmente: credenciais lidas do arquivo .env
# No GitHub Actions: lidas dos Secrets
CLIENT_ID     = os.environ.get("ORULO_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ORULO_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise EnvironmentError(
        "Credenciais não encontradas. Defina as variáveis de ambiente "
        "ORULO_CLIENT_ID e ORULO_CLIENT_SECRET antes de rodar o script."
    )

BASE_URL = "https://www.orulo.com.br/api/v2"

# Arquivo de saída na pasta data/ do repositório (lido pelo Power BI via URL)
BASE_DIR      = Path(__file__).parent
ARQUIVO_SAIDA = BASE_DIR / "data" / "orulo_empreendimentos.csv"
ARQUIVO_LOG   = BASE_DIR / "extracao.log"

ARQUIVO_SAIDA.parent.mkdir(exist_ok=True)

PRAÇAS = [
    {"state": "PR", "city": "Ponta Grossa"},
    {"state": "PR", "city": "Curitiba"},
    {"state": "PR", "city": "Guarapuava"},
    {"state": "PR", "city": "Londrina"},
    {"state": "PR", "city": "Maringa"},
]

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=ARQUIVO_LOG,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)
log = logging.getLogger(__name__)


# ─── AUTENTICAÇÃO ─────────────────────────────────────────────────────────────
def autenticar():
    print("🔐 Autenticando na API Órulo...")
    try:
        response = requests.post(
            "https://www.orulo.com.br/oauth/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
            timeout=30,
        )
    except requests.exceptions.Timeout:
        log.error("Timeout na autenticação.")
        print("❌ Timeout na autenticação (>30s).")
        return None
    except requests.exceptions.ConnectionError as e:
        log.error(f"Erro de conexão na autenticação: {e}")
        print(f"❌ Erro de conexão: {e}")
        return None

    if response.status_code == 200:
        token = response.json().get("access_token")
        print("✅ Autenticação bem-sucedida!")
        return token

    log.error(f"Falha na autenticação: HTTP {response.status_code} — {response.text[:200]}")
    print(f"❌ Erro na autenticação: {response.status_code}")
    return None


# ─── BUSCA COM PAGINAÇÃO COMPLETA ─────────────────────────────────────────────
def buscar_todas_paginas(token, state, city):
    """Busca todos os empreendimentos da cidade percorrendo todas as páginas."""
    headers = {"Authorization": f"Bearer {token}"}
    todos = []
    page = 1
    total_pages = 1  # atualizado na primeira resposta

    while page <= total_pages:
        params = {
            "state": state,
            "city": city,
            "results_per_page": 50,
            "page": page,
            "include[]": "not_available",
        }
        try:
            response = requests.get(
                f"{BASE_URL}/buildings",
                headers=headers,
                params=params,
                timeout=30,
            )
        except requests.exceptions.Timeout:
            print(f"  ⚠️  Timeout em {city} página {page}. Pulando página...")
            log.warning(f"Timeout em {city} página {page}.")
            break
        except requests.exceptions.ConnectionError as e:
            print(f"  ⚠️  Erro de conexão em {city}: {e}")
            log.warning(f"Erro de conexão em {city} p{page}: {e}")
            break

        if response.status_code != 200:
            print(f"  ⚠️  Erro HTTP {response.status_code} em {city} p{page}")
            log.warning(f"HTTP {response.status_code} em {city} p{page}: {response.text[:200]}")
            break

        data = response.json()

        # Descobre total de páginas na primeira chamada
        if page == 1:
            total_resultados = data.get("total", 0)
            por_pagina = data.get("per_page", 50) or 50
            total_pages = -(-total_resultados // por_pagina)  # ceil division
            print(f"  📄 {city}: {total_resultados} empreendimentos — {total_pages} página(s)")

        buildings = data.get("buildings", [])
        todos.extend(buildings)
        page += 1

    return todos


# ─── DETALHE INDIVIDUAL ───────────────────────────────────────────────────────
def buscar_detalhe(token, building_id):
    """Busca campos extras que só existem no endpoint de detalhe."""
    try:
        response = requests.get(
            f"{BASE_URL}/buildings/{building_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        pass
    return {}


# ─── CONVERTER PARA DATAFRAME ─────────────────────────────────────────────────
def buildings_para_df(buildings, city, state, token):
    registros = []
    total = len(buildings)
    for i, b in enumerate(buildings, 1):
        print(f"    Detalhando {i}/{total}...", end="\r")
        detalhe = buscar_detalhe(token, b.get("id"))
        address = b.get("address") or {}
        registros.append({
            "id":                   b.get("id"),
            "nome":                 b.get("name"),
            "cidade":               city,
            "estado":               state,
            "bairro":               address.get("area"),
            "status":               b.get("status"),
            "fase":                 b.get("stage"),
            "data_lancamento":      detalhe.get("launch_date"),
            "data_entrega":         detalhe.get("opening_date"),
            "total_unidades":       detalhe.get("total_units"),
            "preco_minimo":         b.get("min_price"),
            "preco_m2_privativo":   b.get("price_per_private_square_meter"),
            "area_minima_m2":       b.get("min_area"),
            "area_maxima_m2":       b.get("max_area"),
            "quartos_min":          b.get("min_bedrooms"),
            "quartos_max":          b.get("max_bedrooms"),
            "suites_min":           b.get("min_suites"),
            "suites_max":           b.get("max_suites"),
            "vagas_min":            b.get("min_parking"),
            "vagas_max":            b.get("max_parking"),
            "andares":              b.get("number_of_floors"),
            "aptos_por_andar":      b.get("apts_per_floor"),
            "estoque":              b.get("stock"),
            "finalidade":           b.get("finality"),
            "construtora":          (b.get("developer") or {}).get("name"),
            "portfolio":            ", ".join(b.get("portfolio") or []),
            "atualizado_em":        b.get("updated_at"),
            "data_extracao":        datetime.now().strftime("%Y-%m-%d"),
        })
    print()
    return pd.DataFrame(registros)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    inicio = datetime.now()
    print(f"\n{'='*60}")
    print(f"  EXTRAÇÃO DIÁRIA — API ÓRULO")
    print(f"  {inicio.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*60}\n")
    log.info("=== Início da extração ===")

    # 1. Autenticar
    token = autenticar()
    if not token:
        log.error("Extração cancelada: falha na autenticação.")
        return

    # 2. Extrair todas as praças
    print("\n📍 Extraindo empreendimentos por praça...")
    frames = []
    total_registros = 0

    for praca in PRAÇAS:
        city  = praca["city"]
        state = praca["state"]
        print(f"\n  📌 {city} ({state})")

        buildings = buscar_todas_paginas(token, state, city)
        if buildings:
            df = buildings_para_df(buildings, city, state, token)
            frames.append(df)
            total_registros += len(df)
            print(f"     ✅ {len(df)} registros coletados")
            log.info(f"{city}: {len(df)} registros")
        else:
            print(f"     ⚠️  Nenhum dado retornado")
            log.warning(f"{city}: sem dados")

    if not frames:
        print("\n❌ Nenhum dado coletado. Arquivo não atualizado.")
        log.error("Nenhum dado coletado.")
        return

    # 4. Salvar arquivo único no OneDrive
    df_final = pd.concat(frames, ignore_index=True)
    df_final.to_csv(ARQUIVO_SAIDA, index=False, encoding="utf-8-sig")

    duracao = (datetime.now() - inicio).seconds
    print(f"\n{'='*60}")
    print(f"✅ Arquivo salvo: {ARQUIVO_SAIDA}")
    print(f"📊 Total: {total_registros} empreendimentos | {len(PRAÇAS)} cidades")
    print(f"⏱  Duração: {duracao}s")
    print(f"{'='*60}\n")
    log.info(f"Arquivo salvo: {ARQUIVO_SAIDA} | {total_registros} registros | {duracao}s")
    log.info("=== Extração concluída ===")


if __name__ == "__main__":
    main()
