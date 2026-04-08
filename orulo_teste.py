"""
Script de Teste — API Órulo
Projeto: Análise da Concorrência | Prestes
Objetivo: Validar autenticação, cobertura geográfica e qualidade dos dados

Uso:
    python orulo_teste.py

Dependências:
    pip install requests pandas openpyxl
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────
CLIENT_ID     = os.environ.get("ORULO_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ORULO_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise EnvironmentError(
        "Defina ORULO_CLIENT_ID e ORULO_CLIENT_SECRET antes de rodar.\n"
        "No PowerShell:\n"
        "  $env:ORULO_CLIENT_ID='sua_chave'\n"
        "  $env:ORULO_CLIENT_SECRET='seu_secret'"
    )

PRAÇAS = [
    {"state": "PR", "city": "Ponta Grossa"},
    {"state": "PR", "city": "Curitiba"},
    {"state": "PR", "city": "Guarapuava"},
    {"state": "PR", "city": "Londrina"},
    {"state": "PR", "city": "Maringa"},
]

BASE_URL = "https://www.orulo.com.br/api/v2"

# ─── AUTENTICAÇÃO ─────────────────────────────────────────────────────────────
def autenticar():
    print("\n🔐 Autenticando na API Órulo...")
    try:
        response = requests.post(
            "https://www.orulo.com.br/oauth/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "client_credentials"
            },
            timeout=30
        )
    except requests.exceptions.Timeout:
        print("❌ Timeout na autenticação (>30s).")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Erro de conexão na autenticação: {e}")
        return None

    if response.status_code == 200:
        token = response.json().get("access_token")
        print("✅ Autenticação bem-sucedida!")
        return token
    else:
        print(f"❌ Erro na autenticação: {response.status_code}")
        print(response.text)
        return None

# ─── BUSCA DE EMPREENDIMENTOS ─────────────────────────────────────────────────
def buscar_empreendimentos(token, state, city, include_not_available=True):
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "state": state,
        "city": city,
        "results_per_page": 10,
        "page": 1,
    }
    if include_not_available:
        params["include[]"] = "not_available"

    try:
        response = requests.get(f"{BASE_URL}/buildings", headers=headers, params=params, timeout=30)
    except requests.exceptions.Timeout:
        print(f"  ⚠️  Timeout ao buscar {city} (>30s). Pulando...")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"  ⚠️  Erro de conexão ao buscar {city}: {e}")
        return None

    if response.status_code == 200:
        return response.json()
    else:
        print(f"  ⚠️  Erro ao buscar {city}: {response.status_code} — {response.text[:200]}")
        return None

# ─── ANÁLISE DE COBERTURA ─────────────────────────────────────────────────────
def analisar_cobertura(token):
    print("\n" + "="*60)
    print("📍 COBERTURA GEOGRÁFICA POR PRAÇA")
    print("="*60)

    resultados = []
    for praca in PRAÇAS:
        city = praca["city"]
        state = praca["state"]

        # Com not_available
        dados_com = buscar_empreendimentos(token, state, city, include_not_available=True)
        total_com = dados_com.get("total", 0) if dados_com else 0

        # Sem not_available (apenas disponíveis)
        dados_sem = buscar_empreendimentos(token, state, city, include_not_available=False)
        total_sem = dados_sem.get("total", 0) if dados_sem else 0

        diff = total_com - total_sem
        print(f"\n  📌 {city} ({state})")
        print(f"     Disponíveis (ativos):         {total_sem:>5} empreendimentos")
        print(f"     Com histórico (not_available): {total_com:>5} empreendimentos")
        print(f"     Diferença (vendidos/removidos):{diff:>5} empreendimentos")

        resultados.append({
            "praça": city,
            "estado": state,
            "total_ativos": total_sem,
            "total_com_historico": total_com,
            "vendidos_removidos": diff,
            "acesso_not_available": total_com > 0
        })

    return resultados

# ─── QUALIDADE DOS DADOS ──────────────────────────────────────────────────────
def analisar_qualidade(token, state="PR", city="Ponta Grossa"):
    print("\n" + "="*60)
    print(f"🔍 QUALIDADE DOS DADOS — {city}")
    print("="*60)

    dados = buscar_empreendimentos(token, state, city, include_not_available=True)
    if not dados or not dados.get("buildings"):
        print("  Sem dados para análise.")
        return []

    buildings = dados["buildings"]
    print(f"\n  Amostra: {len(buildings)} empreendimentos (de {dados.get('total', '?')} total)")

    # Campos críticos para o dashboard
    campos_criticos = [
        "name", "min_price", "price_per_private_square_meter",
        "min_area", "max_area", "min_bedrooms", "max_bedrooms",
        "status", "launch_date", "total_units", "stock"
    ]

    print("\n  Preenchimento dos campos críticos:")
    for campo in campos_criticos:
        preenchidos = sum(1 for b in buildings if b.get(campo) is not None and b.get(campo) != "")
        pct = (preenchidos / len(buildings)) * 100
        status_icon = "✅" if pct >= 80 else "⚠️ " if pct >= 50 else "❌"
        print(f"  {status_icon} {campo:<40} {preenchidos}/{len(buildings)} ({pct:.0f}%)")

    # Amostra de nomes
    print("\n  Amostra de empreendimentos encontrados:")
    for b in buildings[:5]:
        nome = b.get("name", "S/N")
        preco = b.get("min_price")
        status = b.get("status", "—")
        area_min = b.get("min_area", "—")
        area_max = b.get("max_area", "—")
        preco_fmt = f"R$ {preco:,.0f}".replace(",", ".") if preco else "—"
        print(f"  • {nome}")
        print(f"    Preço mínimo: {preco_fmt} | Status: {status} | Área: {area_min}–{area_max} m²")

    return buildings

# ─── EXPORTAR AMOSTRA ─────────────────────────────────────────────────────────
def exportar_amostra(token):
    print("\n" + "="*60)
    print("💾 EXPORTANDO AMOSTRA — Ponta Grossa")
    print("="*60)

    dados = buscar_empreendimentos(token, "PR", "Ponta Grossa", include_not_available=True)
    if not dados or not dados.get("buildings"):
        print("  Sem dados para exportar.")
        return

    buildings = dados["buildings"]
    registros = []

    for b in buildings:
        address = b.get("address", {})
        registros.append({
            "id":                   b.get("id"),
            "nome":                 b.get("name"),
            "cidade":               address.get("city"),
            "bairro":               address.get("area"),
            "status":               b.get("status"),
            "data_lancamento":      b.get("launch_date"),
            "data_entrega":         b.get("opening_date"),
            "preco_minimo":         b.get("min_price"),
            "preco_m2_privativo":   b.get("price_per_private_square_meter"),
            "area_minima_m2":       b.get("min_area"),
            "area_maxima_m2":       b.get("max_area"),
            "quartos_min":          b.get("min_bedrooms"),
            "quartos_max":          b.get("max_bedrooms"),
            "total_unidades":       b.get("total_units"),
            "estoque":              b.get("stock"),
            "finalidade":           b.get("finality"),
            "portfolio":            ", ".join(b.get("portfolio", [])),
        })

    df = pd.DataFrame(registros)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"orulo_amostra_ponta_grossa_{timestamp}.xlsx"

    df.to_excel(filename, index=False)
    print(f"\n  ✅ Arquivo salvo: {filename}")
    print(f"  📊 {len(df)} empreendimentos exportados")
    print(f"\n  Primeiras linhas:")
    print(df[["nome", "status", "preco_minimo", "area_minima_m2", "quartos_min"]].head(5).to_string(index=False))

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "="*60)
    print("  TESTE DE INTEGRAÇÃO — API ÓRULO")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*60)

    # 1. Autenticar
    token = autenticar()
    if not token:
        print("\n❌ Não foi possível autenticar. Verifique CLIENT_ID e CLIENT_SECRET.")
        return

    # 2. Cobertura geográfica
    resultados_cobertura = analisar_cobertura(token)

    # 3. Qualidade dos dados (foco em Ponta Grossa)
    analisar_qualidade(token, "PR", "Ponta Grossa")

    # 4. Exportar amostra
    exportar_amostra(token)

    # 5. Resumo final
    print("\n" + "="*60)
    print("📋 RESUMO DO TESTE")
    print("="*60)
    df_cob = pd.DataFrame(resultados_cobertura)
    print(df_cob[["praça", "total_ativos", "total_com_historico", "acesso_not_available"]].to_string(index=False))
    print("\n✅ Teste concluído.")

if __name__ == "__main__":
    main()
