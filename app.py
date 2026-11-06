import time
from urllib.parse import quote

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="LoL Stats • Estatísticas por Rota", page_icon="⚔️", layout="wide")

ACCOUNT_REGION = "americas"
PLATFORM_REGION = "br1"
MATCH_REGION = "americas"

ROUTES = {
    "🗡️ TOP · Topo": "TOP",
    "🌲 JUNGLE · Selva": "JUNGLE",
    "🧙 MID · Meio": "MIDDLE",
    "🏹 ADC · Atirador": "BOTTOM",
    "🛡️ SUP · Suporte": "UTILITY",
}
ROUTE_NAMES = {
    "TOP": "Topo", "JUNGLE": "Selva", "MIDDLE": "Meio",
    "BOTTOM": "Atirador", "UTILITY": "Suporte",
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800&family=Inter:wght@400;500;600;700;800&display=swap');
:root { color-scheme: dark; }
.stApp {
  background: radial-gradient(ellipse at 50% 0%, rgba(24,91,119,.20), transparent 48%),
              radial-gradient(ellipse at 100% 100%, rgba(13,75,105,.12), transparent 38%), #071321;
  color: #e8f2f8;
}
header[data-testid="stHeader"], #MainMenu, footer {visibility:hidden; height:0;}
.block-container {padding-top:1.8rem; max-width:1440px;}
h1,h2,h3 {font-family:'Cinzel',serif !important; color:#e7f7ff !important;}
p, label, span, div {font-family:'Inter',sans-serif;}
.hero-title {font-family:'Cinzel',serif; font-size:clamp(2rem,4vw,3.3rem); font-weight:800;
  letter-spacing:.035em; color:#eaf8ff; text-align:center; margin-bottom:.35rem;}
.hero-sub {text-align:center;color:#9ab9ca;font-size:.96rem;margin-bottom:1.4rem;}
.hex-card {
  background:linear-gradient(145deg,rgba(16,42,62,.92),rgba(8,25,42,.94));
  border:1px solid rgba(91,190,218,.22); border-radius:16px;
  padding:18px 20px; box-shadow:0 10px 30px rgba(0,0,0,.18);
}
.hex-panel-title {font-family:'Cinzel',serif;color:#d9f2fb;font-size:1.05rem;font-weight:700;margin:.3rem 0 .2rem;}
.champion-card,.match-card {display:flex;align-items:center;gap:16px;padding:15px 17px;margin:9px 0;
  border:1px solid rgba(91,190,218,.19);border-radius:14px;background:linear-gradient(120deg,rgba(12,34,53,.92),rgba(8,23,39,.88));
  box-shadow:0 7px 22px rgba(0,0,0,.14);transition:border-color .2s,transform .2s;}
.champion-card:hover,.match-card:hover {border-color:rgba(75,207,220,.48);transform:translateY(-1px);}
.champion-icon,.match-icon {width:52px;height:52px;border-radius:11px;border:1px solid rgba(93,207,220,.45);object-fit:cover;}
.champion-main {flex:1;min-width:120px;}
.champion-name,.match-champion {font-weight:800;color:#e8f6fc;font-size:1rem;}
.champion-meta,.match-champion span {font-size:.76rem;color:#8eabba;margin-top:4px;}
.champion-stat,.match-detail {min-width:90px;text-align:right;display:flex;flex-direction:column;gap:4px;}
.champion-stat strong,.match-detail strong {font-size:.96rem;color:#d7f2fa;}
.champion-stat span,.match-detail span {font-size:.7rem;color:#8ca9ba;}
.match-card {justify-content:space-between;flex-wrap:wrap;padding:15px 18px;}
.match-identity {display:flex;align-items:center;gap:13px;min-width:220px;flex:1;}
.match-result {font-size:.72rem;font-weight:800;letter-spacing:.07em;}
.match-result span {font-weight:500;color:#91aaba;letter-spacing:0;}
.match-id {font-size:.66rem;color:#67889b;max-width:145px;overflow-wrap:anywhere;text-align:right;}
@media(max-width:760px){.champion-card,.match-card{gap:10px;}.champion-stat,.match-detail{min-width:70px}.match-id{display:none}.champion-icon,.match-icon{width:43px;height:43px;}}
.metric-label {font-size:.76rem;color:#9bb8c8;text-transform:uppercase;letter-spacing:.07em;font-weight:700;}
.metric-value {font-size:1.75rem;color:#bcefff;font-weight:800;margin-top:.2rem;}
.metric-help {font-size:.78rem;color:#829eaf;margin-top:.15rem;}
.section-kicker {color:#70c9df;font-size:.76rem;text-transform:uppercase;letter-spacing:.12em;font-weight:800;}
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
  background:#0a1b2c !important;border-color:#28536b !important;border-radius:10px !important;
}
.stTextInput input {
  color:#102536 !important;
  -webkit-text-fill-color:#102536 !important;
  background-color:#f3f8fb !important;
  caret-color:#102536 !important;
}
.stTextInput input::placeholder {
  color:#647b8b !important;
  -webkit-text-fill-color:#647b8b !important;
  opacity:1 !important;
}
.stSelectbox div, .stSlider label {color:#e7f7ff !important;}
.stButton > button {
  background:linear-gradient(110deg,#287fa7,#3aaeb8) !important;color:#061725 !important;
  border:1px solid #74d7e8 !important;border-radius:10px !important;font-weight:800 !important;
  min-height:2.8rem;
}
.stButton > button:hover {filter:brightness(1.08);border-color:#b2f0fa !important;}
div[data-testid="stMetric"] {background:rgba(10,31,49,.78);border:1px solid rgba(91,190,218,.18);
  padding:14px;border-radius:13px;}
div[data-testid="stDataFrame"] {border:1px solid rgba(91,190,218,.18);border-radius:12px;}
hr {border-color:rgba(91,190,218,.18);}
</style>
""", unsafe_allow_html=True)


class RiotAPIError(Exception):
    pass


def riot_get(url, key, params=None):
    response = requests.get(url, headers={"X-Riot-Token": key}, params=params, timeout=30)
    if response.status_code == 429:
        wait = min(int(response.headers.get("Retry-After", "2")), 10)
        time.sleep(wait)
        response = requests.get(url, headers={"X-Riot-Token": key}, params=params, timeout=30)
    if response.status_code == 401:
        raise RiotAPIError("Chave inválida ou expirada (401).")
    if response.status_code == 403:
        raise RiotAPIError("A Riot negou o acesso (403). Confira as permissões da chave.")
    if response.status_code == 404:
        raise RiotAPIError("Conta ou recurso não encontrado (404). Confira o Riot ID.")
    if response.status_code == 429:
        raise RiotAPIError("Limite de requisições atingido (429). Aguarde e tente novamente.")
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=600)
def account_lookup(name, tag, key):
    url = f"https://{ACCOUNT_REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quote(name, safe='')}/{quote(tag, safe='')}"
    return riot_get(url, key)


@st.cache_data(ttl=600)
def rank_lookup(puuid, key):
    entries = riot_get(
        f"https://{PLATFORM_REGION}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}",
        key,
    )
    solo = next((entry for entry in entries if entry.get("queueType") == "RANKED_SOLO_5x5"), None)
    if not solo:
        return "Unranked"
    return f"{solo.get('tier')} {solo.get('rank')} · {solo.get('leaguePoints', 0)} LP"


@st.cache_data(ttl=300)
def match_ids(puuid, count, key):
    url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    return riot_get(url, key, {"start": 0, "count": count})


@st.cache_data(ttl=1800)
def match_detail(match_id, key):
    return riot_get(f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}", key)


@st.cache_data(ttl=1800)
def timeline_detail(match_id, key):
    return riot_get(f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline", key)


def safe_num(obj, key, default=0):
    value = obj.get(key, default)
    return value if isinstance(value, (int, float)) else default


def calculate_top_diffs(match_id, key, participants, my_participant):
    """Obtém diferença de ouro/XP aos 15 min via Match Timeline, quando disponível."""
    try:
        timeline = timeline_detail(match_id, key)
        frames = timeline.get("info", {}).get("frames", [])
        if not frames:
            return None, None
        frame = min(frames, key=lambda f: abs(safe_num(f, "timestamp", 0) - 900000))
        frames_by_id = frame.get("participantFrames", {})
        mine_id = str(my_participant.get("participantId"))
        enemy = next(
            (p for p in participants
             if p.get("teamId") != my_participant.get("teamId")
             and (p.get("individualPosition") or p.get("teamPosition")) == "TOP"),
            None,
        )
        if not enemy:
            return None, None
        mine = frames_by_id.get(mine_id, {})
        theirs = frames_by_id.get(str(enemy.get("participantId")), {})
        if not mine or not theirs:
            return None, None
        return (
            safe_num(mine, "totalGold") - safe_num(theirs, "totalGold"),
            safe_num(mine, "xp") - safe_num(theirs, "xp"),
        )
    except (RiotAPIError, requests.RequestException, ValueError, TypeError):
        return None, None


def normalize_match(match_id, match, puuid, key, include_top_timeline=False):
    info = match.get("info", {})
    # Summoner's Rift = mapId 11. Isso remove ARAM e outros mapas/modos.
    if info.get("mapId") != 11:
        return None
    participants = info.get("participants", [])
    me = next((p for p in participants if p.get("puuid") == puuid), None)
    if not me:
        return None
    position = me.get("individualPosition") or me.get("teamPosition") or "UNKNOWN"
    if position not in ROUTE_NAMES:
        return None

    duration = max(safe_num(info, "gameDuration"), 1)
    minutes = duration / 60
    team_kills = sum(safe_num(p, "kills") for p in participants if p.get("teamId") == me.get("teamId"))
    kp = safe_num(me.get("challenges", {}), "killParticipation", 0)
    if not kp and team_kills:
        kp = (safe_num(me, "kills") + safe_num(me, "assists")) / team_kills

    enemy = next(
        (p for p in participants
         if p.get("teamId") != me.get("teamId")
         and (p.get("individualPosition") or p.get("teamPosition")) == position),
        None,
    )
    gold = safe_num(me, "goldEarned")
    cs = safe_num(me, "totalMinionsKilled") + safe_num(me, "neutralMinionsKilled")
    challenges = me.get("challenges") or {}
    gold_diff_15, xp_diff_15 = (None, None)
    if include_top_timeline and position == "TOP":
        gold_diff_15, xp_diff_15 = calculate_top_diffs(match_id, key, participants, me)

    return {
        "match_id": match_id,
        "champion": me.get("championName", "Desconhecido"),
        "position": position,
        "win": bool(me.get("win")),
        "kills": safe_num(me, "kills"),
        "deaths": safe_num(me, "deaths"),
        "assists": safe_num(me, "assists"),
        "duration_min": minutes,
        "game_mode": info.get("gameMode", "Desconhecido"),
        "queue_id": info.get("queueId"),
        "game_creation": safe_num(info, "gameCreation"),
        "enemy_champion": enemy.get("championName") if enemy else "Não identificado",
        "gold": gold,
        "gold_per_min": gold / minutes,
        "cs": cs,
        "cs_per_min": cs / minutes,
        "dragons": safe_num(me, "dragonKills"),
        "barons": safe_num(me, "baronKills"),
        "grubs": safe_num(challenges, "hordeKills"),
        "wards_placed": safe_num(me, "wardsPlaced"),
        "wards_killed": safe_num(me, "wardsKilled"),
        "control_wards": safe_num(me, "visionWardsBoughtInGame"),
        "vision_score": safe_num(me, "visionScore"),
        "damage_champions": safe_num(me, "totalDamageDealtToChampions"),
        "damage_per_min": safe_num(challenges, "damagePerMinute") or safe_num(me, "totalDamageDealtToChampions") / minutes,
        "damage_buildings": safe_num(me, "damageDealtToBuildings"),
        "damage_objectives": safe_num(me, "damageDealtToObjectives"),
        "damage_taken": safe_num(me, "totalDamageTaken"),
        "kp": kp,
        "healing_teammates": safe_num(me, "totalHealsOnTeammates"),
        "shielding_teammates": safe_num(me, "totalDamageShieldedOnTeammates"),
        "gold_diff_15": gold_diff_15,
        "xp_diff_15": xp_diff_15,
    }


def average(games, field):
    values = [g[field] for g in games if g.get(field) is not None]
    return sum(values) / len(values) if values else None


def total(games, field):
    return sum(safe_num(g, field) for g in games)


def fmt(value, digits=1, suffix=""):
    return "—" if value is None else f"{value:,.{digits}f}{suffix}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_metric(col, label, value, help_text=""):
    with col:
        st.markdown(
            f'<div class="hex-card"><div class="metric-label">{label}</div>'
            f'<div class="metric-value">{value}</div><div class="metric-help">{help_text}</div></div>',
            unsafe_allow_html=True,
        )


def aggregate_champions(games):
    rows = []
    for champion in sorted({g["champion"] for g in games}):
        subset = [g for g in games if g["champion"] == champion]
        wins = sum(g["win"] for g in subset)
        deaths = total(subset, "deaths")
        kills = total(subset, "kills")
        assists = total(subset, "assists")
        rows.append({
            "Campeão": champion,
            "Partidas": len(subset),
            "Vitórias": wins,
            "Derrotas": len(subset) - wins,
            "Win rate": 100 * wins / len(subset),
            "KDA": (kills + assists) / max(deaths, 1),
            "Abates médios": average(subset, "kills"),
            "Mortes médias": average(subset, "deaths"),
            "Assistências médias": average(subset, "assists"),
        })
    return pd.DataFrame(rows).sort_values(["Partidas", "Win rate"], ascending=False) if rows else pd.DataFrame()


def render_route_metrics(games, route, route_games=None):
    import html
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    n = len(games)
    if not n:
        st.info("Nenhuma partida encontrada para esta rota no histórico consultado.")
        return

    wins = sum(g["win"] for g in games)
    kills, deaths, assists = (total(games, k) for k in ("kills", "deaths", "assists"))
    wr = 100 * wins / n
    kda = (kills + assists) / max(deaths, 1)

    st.markdown('<div class="section-kicker">Resumo de desempenho</div>', unsafe_allow_html=True)
    base = st.columns(4)
    render_metric(base[0], "Partidas", str(n), f"{wins} vitórias · {n-wins} derrotas")
    render_metric(base[1], "Taxa de vitória", fmt(wr, 1, "%"), "Nas partidas filtradas")
    render_metric(base[2], "KDA médio", fmt(kda, 2), f"{kills/n:.1f} / {deaths/n:.1f} / {assists/n:.1f}")
    render_metric(base[3], "Ouro por minuto", fmt(average(games, "gold_per_min"), 0), "Média por partida")

    st.markdown('<div class="section-kicker" style="margin-top:1.6rem">Métricas específicas da rota</div>', unsafe_allow_html=True)
    if route == "JUNGLE":
        cols = st.columns(4)
        render_metric(cols[0], "Dragões", fmt(average(games, "dragons"), 1), "Média por partida")
        render_metric(cols[1], "Barões", fmt(average(games, "barons"), 2), "Média por partida")
        render_metric(cols[2], "Arautos do Vazio", fmt(average(games, "grubs"), 2), "Void Grubs · média por partida")
        render_metric(cols[3], "Wards colocadas / destruídas", f'{fmt(average(games,"wards_placed"),1)} / {fmt(average(games,"wards_killed"),1)}', "Média por partida")
    elif route == "BOTTOM":
        cols = st.columns(4)
        render_metric(cols[0], "Dano a campeões", fmt(average(games, "damage_champions"), 0), "Média por partida")
        render_metric(cols[1], "Dano por minuto", fmt(average(games, "damage_per_min"), 0), "Dano/min")
        render_metric(cols[2], "Farm por minuto", fmt(average(games, "cs_per_min"), 2), "CS/min")
        render_metric(cols[3], "Dano a estruturas", fmt(average(games, "damage_buildings"), 0), "Dano a torres e edifícios")
    elif route == "MIDDLE":
        cols = st.columns(4)
        render_metric(cols[0], "Dano a campeões", fmt(average(games, "damage_champions"), 0), "Média por partida")
        render_metric(cols[1], "Farm por minuto", fmt(average(games, "cs_per_min"), 2), "CS/min")
        render_metric(cols[2], "Participação em abates", fmt(100 * average(games, "kp"), 1, "%"), "Kill participation média")
        render_metric(cols[3], "Placar de visão", fmt(average(games, "vision_score"), 1), "Média por partida")
    elif route == "TOP":
        cols = st.columns(4)
        render_metric(cols[0], "Dano recebido", fmt(average(games, "damage_taken"), 0), "Média por partida")
        render_metric(cols[1], "Dano a estruturas", fmt(average(games, "damage_buildings"), 0), "Dano a torres e edifícios")
        render_metric(cols[2], "Diferença de ouro aos 15", fmt(average(games, "gold_diff_15"), 0), "Contra o topo adversário")
        render_metric(cols[3], "Diferença de XP aos 15", fmt(average(games, "xp_diff_15"), 0), "Contra o topo adversário")
        if all(g.get("gold_diff_15") is None for g in games):
            st.caption("Diferenças aos 15 minutos dependem dos dados de Timeline da Riot. Se aparecerem como —, a API não forneceu esse frame para as partidas consultadas.")
    elif route == "UTILITY":
        cols = st.columns(4)
        render_metric(cols[0], "Placar de visão", fmt(average(games, "vision_score"), 1), "Média por partida")
        render_metric(cols[1], "Wards colocadas / destruídas", f'{fmt(average(games,"wards_placed"),1)} / {fmt(average(games,"wards_killed"),1)}', "Média por partida")
        render_metric(cols[2], "Wards de controle compradas", fmt(average(games, "control_wards"), 1), "Média por partida")
        render_metric(cols[3], "Curas / escudos em aliados", f'{fmt(average(games,"healing_teammates"),0)} / {fmt(average(games,"shielding_teammates"),0)}', "Média por partida")

    # Painel de gráficos com tema Hextech. O radar usa índices relativos ao melhor
    # valor observado no conjunto da rota, sem afirmar comparação com outros jogadores.
    comparison_games = route_games or games
    chart_left, chart_right = st.columns([1, 1.35], gap="large")
    with chart_left:
        st.markdown('<div class="hex-panel-title">Radar de atributos</div>', unsafe_allow_html=True)
        if route == "JUNGLE":
            metric_fields = [("Visão", "vision_score"), ("Dano", "damage_champions"),
                             ("Objetivos", "dragons"), ("Farm", "cs_per_min"),
                             ("Participação", "kp"), ("Sobrevivência", "damage_taken")]
        elif route == "BOTTOM":
            metric_fields = [("Dano", "damage_champions"), ("Dano/min", "damage_per_min"),
                             ("Farm", "cs_per_min"), ("Estruturas", "damage_buildings"),
                             ("Visão", "vision_score"), ("Participação", "kp")]
        elif route == "MIDDLE":
            metric_fields = [("Dano", "damage_champions"), ("Farm", "cs_per_min"),
                             ("Participação", "kp"), ("Visão", "vision_score"),
                             ("Ouro/min", "gold_per_min"), ("Sobrevivência", "damage_taken")]
        elif route == "TOP":
            metric_fields = [("Dano recebido", "damage_taken"), ("Estruturas", "damage_buildings"),
                             ("Farm", "cs_per_min"), ("Ouro/min", "gold_per_min"),
                             ("Visão", "vision_score"), ("Participação", "kp")]
        else:
            metric_fields = [("Visão", "vision_score"), ("Wards", "wards_placed"),
                             ("Wards destruídas", "wards_killed"), ("Assistências", "assists"),
                             ("Cura", "healing_teammates"), ("Escudos", "shielding_teammates")]

        radar_values = []
        for _, field in metric_fields:
            current = average(games, field) or 0
            reference = max([average(comparison_games, field) or 0, 0.0001])
            radar_values.append(min(100, current / reference * 100))
        radar = go.Figure()
        radar.add_trace(go.Scatterpolar(
            r=radar_values + radar_values[:1],
            theta=[x[0] for x in metric_fields] + [metric_fields[0][0]],
            fill="toself", fillcolor="rgba(56,189,248,0.18)",
            line=dict(color="#42d6d0", width=2.5),
            marker=dict(size=6, color="#9cecf0"),
            hovertemplate="%{theta}: %{r:.0f}/100<extra></extra>",
        ))
        radar.update_layout(
            height=330, margin=dict(l=35, r=35, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, font=dict(color="#c5dbe8", family="Inter"),
            polar=dict(
                bgcolor="rgba(9,27,44,.45)",
                radialaxis=dict(visible=True, range=[0,100], showticklabels=False,
                                gridcolor="rgba(125,190,215,.16)", linecolor="rgba(125,190,215,.18)"),
                angularaxis=dict(gridcolor="rgba(125,190,215,.16)", linecolor="rgba(125,190,215,.18)",
                                 tickfont=dict(size=10, color="#a9c7d8")),
            ),
        )
        st.plotly_chart(radar, use_container_width=True, config={"displayModeBar": False})
        st.caption("Índice relativo: cada atributo é comparado ao maior valor médio observado nas partidas desta rota.")

    with chart_right:
        st.markdown('<div class="hex-panel-title">Evolução do KDA</div>', unsafe_allow_html=True)
        recent = sorted(games, key=lambda g: g.get("game_creation", 0))[-10:]
        labels = [f"Jogo {i+1}" for i in range(len(recent))]
        kdas = [(g["kills"] + g["assists"]) / max(g["deaths"], 1) for g in recent]
        line = go.Figure()
        line.add_trace(go.Scatter(
            x=labels, y=kdas, mode="lines+markers",
            line=dict(color="#54c8e8", width=3, shape="spline"),
            marker=dict(size=8, color="#65e0d6", line=dict(color="#d9fbff", width=1.5)),
            fill="tozeroy", fillcolor="rgba(56,189,248,.10)",
            hovertemplate="%{x}<br>KDA: %{y:.2f}<extra></extra>",
        ))
        line.add_hline(y=kda, line_dash="dot", line_color="#c8aa6e",
                       annotation_text=f"Média {kda:.2f}", annotation_font_color="#d8c18d")
        line.update_layout(
            height=330, margin=dict(l=15, r=15, t=28, b=25),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#a9c7d8", family="Inter"),
            xaxis=dict(showgrid=False, linecolor="rgba(125,190,215,.2)"),
            yaxis=dict(title=None, gridcolor="rgba(125,190,215,.12)", zeroline=False),
            showlegend=False,
        )
        st.plotly_chart(line, use_container_width=True, config={"displayModeBar": False})

    # Campeões em cartões visuais em vez de tabela.
    champs_df = aggregate_champions(games)
    st.markdown('<div class="section-kicker" style="margin-top:1.4rem">Campeões nesta rota</div>', unsafe_allow_html=True)
    if champs_df.empty:
        st.info("Ainda não há campeões para exibir.")
    else:
        for _, row in champs_df.iterrows():
            champ = html.escape(str(row["Campeão"]))
            wr_value = float(row["Win rate"])
            wr_color = "#59d8bd" if wr_value >= 50 else "#f08a9b"
            champ_icon = f"https://ddragon.leagueoflegends.com/cdn/15.1.1/img/champion/{quote(champ.replace(' ', ''), safe='')}.png"
            st.markdown(
                f'<div class="champion-card">'
                f'<img src="{champ_icon}" class="champion-icon" onerror="this.style.display=\'none\'">'
                f'<div class="champion-main"><div class="champion-name">{champ}</div>'
                f'<div class="champion-meta">{int(row["Partidas"])} partidas · {int(row["Vitórias"])}V {int(row["Derrotas"])}D</div></div>'
                f'<div class="champion-stat"><strong style="color:{wr_color}">{wr_value:.1f}%</strong><span>Win rate</span></div>'
                f'<div class="champion-stat"><strong>{row["KDA"]:.2f}</strong><span>KDA</span></div>'
                f'<div class="champion-stat"><strong>{row["Abates médios"]:.1f}/{row["Mortes médias"]:.1f}/{row["Assistências médias"]:.1f}</strong><span>K / D / A médio</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Histórico como cards individuais com faixa de vitória/derrota.
    st.markdown('<div class="section-kicker" style="margin-top:1.6rem">Histórico de partidas</div>', unsafe_allow_html=True)
    for game in sorted(games, key=lambda g: g.get("game_creation", 0), reverse=True):
        won = game["win"]
        accent = "#39c9b0" if won else "#e87991"
        result = "VITÓRIA" if won else "DERROTA"
        result_bg = "rgba(35,178,151,.10)" if won else "rgba(210,77,105,.10)"
        champ = html.escape(str(game["champion"]))
        enemy = html.escape(str(game["enemy_champion"]))
        match_id = html.escape(str(game["match_id"]))
        kda_game = (game["kills"] + game["assists"]) / max(game["deaths"], 1)
        duration = int(game["duration_min"])
        cs = int(game["cs"])
        st.markdown(
            f'<div class="match-card" style="border-left:4px solid {accent};background:{result_bg}">'
            f'<div class="match-identity"><img src="https://ddragon.leagueoflegends.com/cdn/15.1.1/img/champion/{quote(champ.replace(" ", ""), safe="")}.png" class="match-icon" onerror="this.style.display=\'none\'">'
            f'<div><div class="match-result" style="color:{accent}">{result} <span>· {html.escape(str(game["game_mode"]))} · {duration} min</span></div>'
            f'<div class="match-champion">{champ} <span>vs {enemy}</span></div></div></div>'
            f'<div class="match-detail"><strong>{game["kills"]} / {game["deaths"]} / {game["assists"]}</strong><span>{kda_game:.2f} KDA</span></div>'
            f'<div class="match-detail"><strong>{cs} CS</strong><span>{game["cs_per_min"]:.2f} CS/min</span></div>'
            f'<div class="match-detail"><strong>{game["vision_score"]} visão</strong><span>{fmt(game["gold_per_min"],0)} ouro/min</span></div>'
            f'<div class="match-id">{match_id}</div></div>',
            unsafe_allow_html=True,
        )


# Header e área de busca principal
st.markdown('<div class="hero-title">ESTATÍSTICAS POR ROTA</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">League Analytics · Desempenho real nas partidas do Summoner’s Rift</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="section-kicker">Consultar invocador</div>', unsafe_allow_html=True)
    id_col, route_col, count_col = st.columns([2.3, 1.5, 1])
    with id_col:
        riot_id = st.text_input("Riot ID · Nome#TAG", "Tetuz#Tetuz", placeholder="Ex.: Nome#TAG")
    with route_col:
        selected_route_label = st.selectbox("Rota para analisar", list(ROUTES.keys()), index=1)
    with count_col:
        count = st.select_slider("Partidas recentes", options=[10, 20, 30, 40, 50, 75, 100], value=50)

    with st.expander("🔐 Acesso à Riot Games · inserir chave de API", expanded=False):
        riot_key_input = st.text_input(
            "Chave da Riot",
            type="password",
            key="riot_api_key",
            placeholder="Cole sua chave de API",
            help="A chave fica mascarada na interface. Não a compartilhe nem a publique no GitHub.",
        )
        st.caption("A chave é usada pelo servidor para consultar a Riot API e não é gravada no repositório.")

    search_col, _ = st.columns([1, 3])
    with search_col:
        search_clicked = st.button("⚔️  Buscar estatísticas", type="primary", use_container_width=True)

key = riot_key_input.strip() or st.secrets.get("RIOT_API_KEY", "")
selected_route = ROUTES[selected_route_label]

if search_clicked:
    if "#" not in riot_id or not all(part.strip() for part in riot_id.rsplit("#", 1)):
        st.error("Informe o Riot ID no formato Nome#TAG.")
        st.stop()
    if not key:
        st.error("Abra a seção «Acesso à Riot Games» e informe sua chave de API.")
        st.stop()

    name, tag = [part.strip() for part in riot_id.rsplit("#", 1)]
    try:
        with st.spinner("Consultando a Riot Games e analisando partidas do Summoner’s Rift..."):
            account = account_lookup(name, tag, key)
            puuid = account["puuid"]
            try:
                rank = rank_lookup(puuid, key)
            except (RiotAPIError, requests.RequestException):
                rank = "Não foi possível consultar"
            ids = match_ids(puuid, count, key)
            matches = []
            failed = 0
            progress = st.progress(0)
            for index, match_id in enumerate(ids, 1):
                try:
                    detail = match_detail(match_id, key)
                    game = normalize_match(
                        match_id, detail, puuid, key,
                        include_top_timeline=(selected_route == "TOP"),
                    )
                    if game:
                        matches.append(game)
                except (RiotAPIError, requests.RequestException, ValueError, TypeError):
                    failed += 1
                progress.progress(index / max(len(ids), 1))
            progress.empty()
            st.session_state["result"] = {
                "name": f'{account.get("gameName", name)}#{account.get("tagLine", tag)}',
                "rank": rank,
                "matches": matches,
                "searched": len(ids),
                "failed": failed,
                "route_at_search": selected_route,
            }
    except (RiotAPIError, requests.RequestException, KeyError) as error:
        st.error(f"Não foi possível concluir a consulta: {error}")

data = st.session_state.get("result")
if data:
    st.divider()
    header_left, header_right = st.columns([2, 1])
    with header_left:
        st.markdown(f"### {data['name']}")
        st.caption(f"Elo Solo/Duo: {data['rank']} · Servidor BR1 · Summoner’s Rift")
    with header_right:
        st.markdown(f'<div class="hex-card"><div class="metric-label">Partidas verificadas</div><div class="metric-value">{data["searched"]}</div><div class="metric-help">{len(data["matches"])} partidas válidas no Summoner’s Rift</div></div>', unsafe_allow_html=True)
    if data.get("failed"):
        st.warning(f'{data["failed"]} partida(s) não puderam ser carregadas. As demais foram analisadas normalmente.')

    route_games = [g for g in data["matches"] if g["position"] == selected_route]
    available_champions = sorted({g["champion"] for g in route_games})
    champion_options = ["Todos os Campeões"] + available_champions
    champ_col, note_col = st.columns([1.2, 2])
    with champ_col:
        selected_champion = st.selectbox("Filtrar por campeão", champion_options, key=f"champion_filter_{selected_route}")
    if selected_champion != "Todos os Campeões":
        filtered_games = [g for g in route_games if g["champion"] == selected_champion]
    else:
        filtered_games = route_games

    st.markdown(f"### Desempenho · {ROUTE_NAMES[selected_route]}")
    st.caption(
        f'{len(route_games)} partida(s) encontradas nesta rota. '
        + (f'Exibindo somente {selected_champion}.' if selected_champion != "Todos os Campeões" else "Exibindo todos os campeões.")
    )
    render_route_metrics(filtered_games, selected_route, route_games)

    with st.expander("Diagnóstico da consulta"):
        st.write("Partidas válidas por rota:")
        counts_by_route = {
            ROUTE_NAMES[route]: sum(g["position"] == route for g in data["matches"])
            for route in ROUTE_NAMES
        }
        st.json(counts_by_route)
        st.write(f'Partidas solicitadas: {data["searched"]} · Partidas válidas em Summoner’s Rift: {len(data["matches"])} · Falhas: {data["failed"]}')

st.markdown(
    '<div style="text-align:center;color:#66869a;font-size:.75rem;padding:2rem 0 1rem;">'
    'Dados oficiais da Riot Games API · Métricas calculadas a partir das partidas disponíveis · League of Legends é marca da Riot Games, Inc.'
    '</div>',
    unsafe_allow_html=True,
)
