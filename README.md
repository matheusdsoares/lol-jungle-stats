# LoL Jungle Stats

Aplicação Streamlit para analisar partidas recentes de League of Legends na posição JUNGLE usando a Riot Games API.

## Deploy
1. Conecte este repositório ao Streamlit Community Cloud.
2. Configure o arquivo principal como `app.py`.
3. Em App settings → Secrets, adicione:

```toml
RIOT_API_KEY = "SUA_CHAVE_RIOT"
```

Nunca coloque a chave Riot neste repositório.

## Observações
- Chaves de desenvolvimento Riot expiram periodicamente (normalmente em 24 horas).
- A consulta usa Account-V1, Summoner-V4, League-V4 e Match-V5.
- O app consulta de 10 a 100 partidas recentes e filtra `individualPosition == "JUNGLE"`.
- O cache reduz chamadas repetidas à API.
