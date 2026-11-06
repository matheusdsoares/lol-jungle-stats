import time
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="LoL Jungle Stats", page_icon="🌲", layout="wide")
ACCOUNT_REGION = "americas"
PLATFORM_REGION = "br1"
MATCH_REGION = "americas"

# Oculta o botão nativo de revelar senha apenas no campo da chave Riot.
st.markdown(
    """
    <style>
    .st-key-riot_api_key button {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


class RiotAPIError(Exception):
    pass


def riot_get(url, key, params=None):
    r = requests.get(url, headers={"X-Riot-Token": key}, params=params, timeout=25)
    if r.status_code == 429:
        time.sleep(min(int(r.headers.get("Retry-After", "2")), 10))
        r = requests.get(url, headers={"X-Riot-Token": key}, params=params, timeout=25)
    if r.status_code == 401:
        raise RiotAPIError("Chave inválida ou expirada (401).")
    if r.status_code == 403:
        raise RiotAPIError("A Riot negou o acesso (403). Confira a chave.")
    if r.status_code == 404:
        raise RiotAPIError("Conta ou recurso não encontrado (404). Confira o Riot ID.")
    if r.status_code == 429:
        raise RiotAPIError("Limite de requisições atingido (429). Aguarde e tente novamente.")
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=600)
def account_lookup(name, tag, key):
    url = f"https://{ACCOUNT_REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quote(name, safe='')}/{quote(tag, safe='')}"
    return riot_get(url, key)


@st.cache_data(ttl=600)
def rank_lookup(puuid, key):
    # League-V4 é consultada diretamente pelo PUUID.
    entries = riot_get(
        f"https://{PLATFORM_REGION}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}",
        key,
    )
    solo = next((x for x in entries if x.get("queueType") == "RANKED_SOLO_5x5"), None)
    if not solo:
        return "Unranked"
    return f"{solo.get('tier')} {solo.get('rank')} ({solo.get('leaguePoints', 0)} LP)"


@st.cache_data(ttl=300)
def match_ids(puuid, count, key):
    url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    return riot_get(url, key, {"start": 0, "count": count})


@st.cache_data(ttl=1800)
def match_detail(match_id, key):
    return riot_get(f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}", key)


def add_game(bucket, champ, me):
    row = bucket.setdefault(champ, {"games": 0, "wins": 0, "kills": 0, "deaths": 0, "assists": 0})
    row["games"] += 1
    row["wins"] += int(bool(me.get("win")))
    for stat in ("kills", "deaths", "assists"):
        row[stat] += int(me.get(stat, 0))


def to_frame(stats, label):
    rows = []
    for champ, x in stats.items():
        n = x["games"]
        rows.append({
            label: champ, "Partidas": n, "Vitórias": x["wins"], "Derrotas": n - x["wins"],
            "Win rate": 100 * x["wins"] / n,
            "Abates médios": x["kills"] / n, "Mortes médias": x["deaths"] / n,
            "Assistências médias": x["assists"] / n,
            "KDA": (x["kills"] + x["assists"]) / max(x["deaths"], 1),
        })
    return pd.DataFrame(rows).sort_values(["Partidas", "Win rate"], ascending=False) if rows else pd.DataFrame()


st.title("🌲 LoL Jungle Stats")
st.caption("Estatísticas das suas partidas na selva com dados oficiais da Riot Games.")
with st.sidebar:
    st.header("Configurações")
    riot_id = st.text_input("Riot ID", "Tetuz#Tetuz")
    with st.expander("Acesso à Riot Games", expanded=False):
        riot_key_input = st.text_input(
            "Chave de API",
            type="password",
            key="riot_api_key",
            placeholder="Cole sua chave aqui",
            help="A chave permanece mascarada e é usada apenas para consultar a API.",
        )
        st.caption("Sua chave não é exibida nem salva no GitHub.")
    count = st.slider("Partidas recentes a consultar", 10, 100, 30, 10)
    st.caption("A análise considera partidas recentes de todos os modos e filtra as que registram sua posição como JUNGLE.")

# Permite usar a chave digitada no app. Se o campo estiver vazio, usa o Secret
# já configurado no Streamlit, caso exista.
key = riot_key_input.strip() or st.secrets.get("RIOT_API_KEY", "")
if not key:
    st.info("Abra «Acesso à Riot Games» na barra lateral e informe sua chave para consultar as partidas.")
    st.stop()

if st.button("🔎 Buscar estatísticas", type="primary", use_container_width=True):
    if "#" not in riot_id or not all(riot_id.rsplit("#", 1)):
        st.error("Informe o Riot ID no formato Nome#TAG.")
        st.stop()
    name, tag = riot_id.rsplit("#", 1)
    try:
        with st.spinner("Localizando conta..."):
            account = account_lookup(name.strip(), tag.strip(), key)
            puuid = account["puuid"]
        try:
            rank = rank_lookup(puuid, key)
        except (RiotAPIError, requests.RequestException):
            rank = "Não foi possível consultar"
        ids = match_ids(puuid, count, key)
        champs, enemies = {}, {}
        progress = st.progress(0)
        failed_matches = 0
        positions = {}
        for i, mid in enumerate(ids, 1):
            try:
                info = match_detail(mid, key).get("info", {})
            except (RiotAPIError, requests.RequestException):
                failed_matches += 1
                progress.progress(i / max(len(ids), 1))
                continue
            participants = info.get("participants", [])
            me = next((p for p in participants if p.get("puuid") == puuid), None)
            if me:
                position = me.get("individualPosition", "SEM_DADO")
                positions[position] = positions.get(position, 0) + 1
                if position == "JUNGLE":
                    add_game(champs, me.get("championName", "Desconhecido"), me)
                    enemy = next((p for p in participants if p.get("teamId") != me.get("teamId") and p.get("individualPosition") == "JUNGLE"), None)
                    if enemy:
                        add_game(enemies, enemy.get("championName", "Desconhecido"), me)
            progress.progress(i / max(len(ids), 1))
        progress.empty()
        st.session_state["result"] = {
            "name": f"{account.get('gameName', name)}#{account.get('tagLine', tag)}",
            "rank": rank, "champs": champs, "enemies": enemies, "searched": len(ids),
            "failed_matches": failed_matches, "positions": positions,
        }
    except (RiotAPIError, requests.RequestException, KeyError) as e:
        st.error(f"Não foi possível concluir a consulta: {e}")

data = st.session_state.get("result")
if data:
    st.subheader(f"👤 {data['name']}")
    st.info(f"🏆 Elo Solo/Duo: {data['rank']}")
    a, b, c = st.columns(3)
    a.metric("Partidas consultadas", data["searched"])
    a2 = sum(x["games"] for x in data["champs"].values())
    b.metric("Partidas identificadas na JG", a2)
    c.metric("Campeões utilizados", len(data["champs"]))
    if data.get("failed_matches", 0):
        st.warning(f"{data['failed_matches']} partida(s) não puderam ser carregadas pela API.")
    with st.expander("Diagnóstico da consulta"):
        st.write("Posições identificadas nas partidas:")
        st.json(data.get("positions", {}))
    st.subheader("📊 Desempenho por campeão")
    df = to_frame(data["champs"], "Seu campeão")
    if df.empty:
        st.warning("Nenhuma partida recente foi identificada com você na posição JUNGLE.")
    else:
        st.dataframe(df.style.format({"Win rate":"{:.1f}%", "Abates médios":"{:.1f}", "Mortes médias":"{:.1f}", "Assistências médias":"{:.1f}", "KDA":"{:.2f}"}), use_container_width=True, hide_index=True)
        st.bar_chart(df.set_index("Seu campeão")["Partidas"])
    st.subheader("⚔️ Confrontos contra caçadores inimigos")
    enemy_df = to_frame(data["enemies"], "Caçador inimigo")
    if enemy_df.empty:
        st.info("Não foi possível identificar os caçadores inimigos nas partidas encontradas.")
    else:
        st.dataframe(enemy_df.style.format({"Win rate":"{:.1f}%", "Abates médios":"{:.1f}", "Mortes médias":"{:.1f}", "Assistências médias":"{:.1f}", "KDA":"{:.2f}"}), use_container_width=True, hide_index=True)
st.caption("Dados fornecidos pela Riot Games API. O histórico é limitado às partidas recentes solicitadas; apenas partidas com individualPosition = JUNGLE entram nas estatísticas.")
