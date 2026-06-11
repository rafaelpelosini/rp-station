import re
import unicodedata
from datetime import datetime, timedelta, date
import requests as http_requests
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client

st.set_page_config(
    page_title="RP Station",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── AUTH ────────────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated"):
    st.markdown("<br><br>", unsafe_allow_html=True)
    col = st.columns([1, 1, 1])[1]
    with col:
        st.markdown("### RP Station")
        pwd = st.text_input("Senha", type="password", placeholder="Digite a senha…")
        if st.button("Entrar", use_container_width=True):
            if pwd == st.secrets.get("app_password", ""):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
    st.stop()

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
* { font-family: 'Inter', sans-serif !important; }

.stApp, [data-testid="stAppViewContainer"] { background-color: #F9FAFB !important; }

[data-testid="collapsedControl"],
[data-testid="stSidebar"] { display: none !important; }

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    background: #FFFFFF;
    border-bottom: 1px solid #E5E7EB;
    padding: 0 16px;
    gap: 0;
}
[data-testid="stTabs"] [role="tab"] {
    color: #9CA3AF !important;
    font-weight: 700 !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 20px 28px !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    background: transparent !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #111827 !important;
    border-bottom: 2px solid #111827 !important;
}
[data-testid="stTabs"] [role="tab"]:hover { color: #374151 !important; background: #F3F4F6 !important; }
[data-testid="stTabsContent"] { padding-top: 40px !important; }

/* ── Metric cards — oversized ── */
[data-testid="metric-container"] {
    background: #FFFFFF;
    border: none !important;
    border-top: 3px solid #111827 !important;
    border-radius: 0 !important;
    padding: 28px 24px 24px !important;
    box-shadow: none !important;
}
[data-testid="stMetricValue"] {
    color: #111827 !important;
    font-weight: 800 !important;
    font-size: 2.8rem !important;
    letter-spacing: -0.03em !important;
    line-height: 1 !important;
}
[data-testid="stMetricLabel"] {
    color: #9CA3AF !important;
    font-size: 0.68rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-weight: 600 !important;
}
[data-testid="stMetricDelta"] { font-size: 0.75rem !important; color: #6B7280 !important; }

/* ── Typography ── */
h1 { color: #111827 !important; font-weight: 900 !important; font-size: 2rem !important; letter-spacing: -0.03em !important; }
h2 { color: #111827 !important; font-weight: 800 !important; font-size: 1.4rem !important; letter-spacing: -0.02em !important; }
h3 { color: #374151 !important; font-weight: 700 !important; font-size: 1rem !important; letter-spacing: -0.01em !important; }

/* ── Buttons ── */
.stButton > button {
    background-color: #111827 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 2px !important;
    font-weight: 700 !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    padding: 10px 20px !important;
}
.stButton > button:hover { background-color: #1F2937 !important; }

[data-testid="stDownloadButton"] > button {
    background-color: #FFFFFF !important;
    color: #111827 !important;
    border: 1.5px solid #111827 !important;
    border-radius: 2px !important;
    font-weight: 700 !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}
[data-testid="stDownloadButton"] > button:hover { background-color: #111827 !important; color: #FFFFFF !important; }

/* ── Misc ── */
hr { border-color: #E5E7EB !important; margin: 24px 0 32px 0 !important; }
[data-testid="stDataFrame"] { border: 1px solid #E5E7EB !important; border-radius: 0 !important; }
[data-testid="stSelectbox"] > div > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {
    border-radius: 2px !important;
    border-color: #E5E7EB !important;
    background: #FFFFFF !important;
    font-size: 0.88rem !important;
    color: #111827 !important;
}
[data-testid="stCaptionContainer"] p { color: #9CA3AF !important; font-size: 0.72rem !important; }

#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── SUPABASE ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_sb():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

@st.cache_data(ttl=300)
def load_overview():
    sb = get_sb()
    res = sb.table("v_overview").select("*").execute()
    return res.data[0] if res.data else {}

@st.cache_data(ttl=300)
def load_opt_in():
    sb = get_sb()
    res = sb.table("v_opt_in_counts").select("*").execute()
    return pd.DataFrame(res.data)

@st.cache_data(ttl=300)
def load_top_tags(n=60):
    sb = get_sb()
    res = sb.table("v_tag_counts").select("*").eq("source", "ac").limit(n).execute()
    return pd.DataFrame(res.data)

@st.cache_data(ttl=300)
def load_states():
    sb = get_sb()
    res = sb.table("v_state_counts").select("*").limit(30).execute()
    return pd.DataFrame(res.data)

# ─── Dicionário de nomes brasileiros para inferência de gênero ────────────────
_BR_F = {
    "MARIA","ANA","JULIANA","FERNANDA","MARIANA","CAMILA","RENATA","CAROLINA",
    "LUCIANA","GABRIELA","ADRIANA","ALINE","MARINA","PAULA","BRUNA","PATRICIA",
    "PATRÍCIA","SANDRA","CLAUDIA","CLÁUDIA","MARCIA","MÁRCIA","VANESSA","JULIA",
    "JÚLIA","AMANDA","DANIELA","BEATRIZ","THAIS","THAÍS","SIMONE","ANDREA",
    "ANDREIA","ANDRÉA","DENISE","LARISSA","CARLA","CRISTIANE","CRISTINA",
    "PRISCILA","RAQUEL","ALESSANDRA","NATALIA","NATÁLIA","DEBORAH","DEBORA",
    "TATIANA","ISABELA","ISABEL","ELIANE","ROSANA","SUELI","FABIANA","VIVIANE",
    "LIVIA","LÍVIA","LETICIA","LETÍCIA","FLAVIA","FLÁVIA","KATIA","KÁTIA",
    "KARINA","KELLY","ROBERTA","ROSANGELA","ANGELA","ÂNGELA","LUCIA","LUZIA",
    "LÚCIA","TANIA","TÂNIA","ALICE","REBEKA","REBECA","RACHEL","RAFAELA","RAFAELLA",
    "RAPHAELA","GIOVANA","GIOVANNA","JULIANE","JAQUELINE","JACQUELINE","BIANCA",
    "BARBARA","BÁRBARA","GISELE","GISELA","NATHALIA","NATHALIE","DAIANE","DAIANA",
    "DIANA","TATIANE","TAMIRES","TAMIRIS","TAMARA","SAMARA","SAMIRA","SARA","SARAH",
    "SILVANA","SILVIA","SÍLVIA","SORAYA","SHEILA","SONIA","SÔNIA","SOLANGE",
    "VICTORIA","VITORIA","VITÓRIA","HELENA","HELOISA","HELOISE","FATIMA","FÁTIMA",
    "EVELYN","ESTHER","ESTER","ELZA","ELISA","ELEONORA","ELIZABETE","ELIZABETH",
    "CAROLINE","CAROLLINE","CARINE","CARINA","CAMILLA","CASSIA","CÁSSIA",
    "CECILIA","CECÍLIA","CINTIA","CÍNTIA","CINARA","CIBELE","APARECIDA",
    "MIRELA","MIRIAM","MIRIAN","MILENA","NADIA","NÁDIA","PALOMA","PAMELA","PÂMELA",
    "POLIANA","POLLYANA","ANNA","ANNE","LUIZA","LUANA","LAURA","LILIAN","LILIANE",
    "RITA","LUISA","ELIANA","DANIELLE","JESSICA","JÉSSICA","MARCELA","REGIANE",
    "REGINA","CLARICE","INGRID","IARA","VERA","VERONICA","MONICA","MÔNICA",
    "LUCIENE","ANDRESSA","ANDREZA","ARIANE","ARIANA","MILENA","LEILA","LEYLA",
    "LAIS","LAÍS","NORMA","GLEICE","WANESSA","YASMIN","ZILDA","SUELLEN","SUZANA",
    "SUZANE","NAIARA","NILZA","NILCE","FABIOLA","EDILENE","ERIKA","ÉRIKA","ERICA",
    "MAIARA","MAÍRA","MARA","MARTA","MARLENE","MARLI","MARGARETH","MARGARIDA",
    "MARINÊS","MARINES","MARISTELA","MICHELI","MICHELLE","NICOLE","NICOLLE",
    "ROSELI","ROSELENE","ROSEMEIRE","ROSILENE","ROSIMARA","TAIANE","TAINA","TAÍNA",
    "THALITA","VANIA","VÂNIA","JOICE","JOYCE","JOSIANE","JANAÍNA","JANAINA",
    "LORENA","LORRAINE","LORAINE","LUCIMARA","LUCINEIA","MAGALI","MAGALY","MAGDA",
    "LILIAM","SUELY","SUELENE","MICHELE","KAREN","VIVIAN","SHIRLEY","STEPHANIE",
    "STEPHANY","ELLEN","IZABEL","TAIS","HELEN","CAROL","MONIQUE","CLAUDETE",
    "MARY","ROSE","EMILY","JANETE","LOUISE","RUTH","DEISE","NOEMIA","ODETE",
}
_BR_M = {
    "RAFAEL","PEDRO","LUCAS","GABRIEL","RODRIGO","FELIPE","GUILHERME","LUIZ","LUIS",
    "GUSTAVO","DANIEL","MARCELO","JOÃO","PAULO","CARLOS","THIAGO","LEONARDO",
    "FERNANDO","MATHEUS","MATEUS","RICARDO","EDUARDO","JOSÉ","JOSE","ALEXANDRE",
    "JOAO","BRUNO","ANTONIO","ANTÔNIO","ANDERSON","LEANDRO","ROBERTO","RENATO",
    "SERGIO","SÉRGIO","FABIO","FÁBIO","FRANCISCO","FLAVIO","FLÁVIO","ANDRE","ANDRÉ",
    "ALVARO","ÁLVARO","ALAN","ADILSON","ADEMIR","ADRIANO","ALISSON","ALLISON","ALEX",
    "ALEXSANDRO","ALFREDO","ALMIR","ALTAIR","ARTUR","ARTHUR","AUGUSTO","BENEDITO",
    "BENTO","BERNARDO","CAIO","CAIQUE","CESAR","CÉZAR","CLAUDIO","CLÁUDIO","CLEBER",
    "CLEITON","CRISTIAN","CRISTIANO","DARIO","DÁRIO","DAVI","DAVID","DEIVID",
    "DENILSON","DIRCEU","DIEGO","DIOGO","DOUGLAS","EDSON","EDILSON","ÉDSON","ELTON",
    "EMERSON","EVANDRO","EVERALDO","EVERTON","EWERTON","EZEQUIEL","FABRICIO",
    "FABRÍCIO","FABIANO","FAUSTO","GILBERTO","GILMAR","GILSON","GLAUBER","HENRY",
    "HENRIQUE","HELIO","HÉLIO","HUGO","HUMBERTO","IGOR","IVAN","IAGO","ICARO","ÍCARO",
    "ITALO","ÍTALO","JAILSON","JAIME","JEAN","JEFFERSON","JEFERSON","JONATHAS",
    "JONATAS","JONAS","JONATHAN","JORGE","JOSUÉ","JOSUE","JÚLIO","JULIO","JUNIOR",
    "KELVIN","LAERTE","LAURO","LINCON","LINCOLN","LÚCIO","LUCIO","LUKAS","LUÍS",
    "MAICON","MAILSON","MANOEL","MANUEL","MARCIO","MÁRCIO","MARCOS","MARIO","MÁRIO",
    "MARLON","MAURICIO","MAURÍCIO","MAURO","MIGUEL","MISAEL","MOISES","MOISÉS",
    "MURILO","NATAN","NATHANAEL","NEWTON","NICOLAS","NÍCOLAS","NILTON","OSVALDO",
    "OSMAR","OTAVIO","OTÁVIO","PABLO","PATRICK","RENAN","RENATO","ROGÉRIO","ROGERIO",
    "ROMARIO","ROMÁRIO","ROMULO","RÔMULO","RONALDO","RUBENS","RUAN","SAMUEL","SILVIO",
    "SÍLVIO","SILAS","TIAGO","TOMAS","TOMÁS","TONI","TONY","TULIO","TÚLIO","ULISSES",
    "VAGNER","VALDEMAR","VALDIR","VALENTIM","VALTER","VANDERLEI","VICTOR","VINICIUS",
    "VINÍCIUS","VITOR","WAGNER","WALACE","WALLACE","WALDIR","WALTER","WENDEL",
    "WENDELL","WESLEI","WESLEY","WILTON","WILSON","YAGO","YURI","KAUÃ","KAUAN",
    "IAN","RYAN","RAUL","TARCISIO","TARCÍSIO","WILLIAM","WILMAR","YOHAN","ZAQUEU",
    "REGINALDO","REINALDO","SIMÃO","VALMOR","VANDO","WEVERTON","ROBSON","GERALDO",
    "DANILO","RAPHAEL","LUAN","MARCUS","RODOLFO","WELLINGTON","WELINGTON","ELIAS",
    "ELVIS","EMILIO","EMÍLIO","ERNESTO","EVALDO","GERSON","GIOVANI","HAROLDO",
    "HILTON","IRINEU","ISAQUE","ITAMAR","IVO","JAIR","JARDEL","JOEL","JOELSON",
    "JONATAN","JOSIMAR","JUAREZ","JULIANO","ALLAN","BRENO","WILLIAN","ERICK","ERIC",
    "SANDRO","RAMON","DENIS","YAN","GIOVANNI","MARCEL","ROBERTO",
}

def _strip_acc(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

_FEM_SUFFIXES = ("ANE","ENE","INE","ELLE","IANE","LENE","NICE","ELLY","ANNE","IELLE",
                 "AINE","EINE","EIRE","AIDE","EIDE","NIDE","MARA","LARA","EIRA","AIRA",
                 "INHA","OLHA","ELHA","AELE","IELE","IONE","ALVA","ELVA","ILVA")

try:
    import gender_guesser.detector as _gg_lib
    _gg = _gg_lib.Detector()
except Exception:
    _gg = None

def _infer_gender(name):
    nm = name.strip().upper()
    if not nm or len(nm) < 2 or "@" in nm: return "?"
    if nm in _BR_F: return "F"
    if nm in _BR_M: return "M"
    if _gg:
        g = _gg.get_gender(nm.capitalize(), "portugal")
        if g == "unknown": g = _gg.get_gender(nm.capitalize())
        if g in ("female","mostly_female"): return "F"
        if g in ("male","mostly_male"):     return "M"
    np = _strip_acc(nm)
    if np.endswith("A"): return "F"
    if any(np.endswith(s) for s in _FEM_SUFFIXES): return "F"
    return "?"

@st.cache_data(ttl=600)
def load_gender_stats():
    sb = get_sb()
    PAGE = 1000; offset = 0; counts = {"F": 0, "M": 0, "?": 0}
    while True:
        r = sb.table("contacts").select("first_name").not_.is_("first_name","null").neq("first_name","").range(offset, offset+PAGE-1).execute()
        if not r.data: break
        for row in r.data:
            first = row["first_name"].strip().split()[0].upper() if row["first_name"].strip() else ""
            counts[_infer_gender(first)] += 1
        if len(r.data) < PAGE: break
        offset += PAGE
    return counts

@st.cache_data(ttl=600)
def load_age_stats():
    sb = get_sb()
    PAGE = 1000; offset = 0; ages = []
    today = date.today()
    while True:
        r = sb.table("contacts").select("birth_date").not_.is_("birth_date","null").range(offset, offset+PAGE-1).execute()
        if not r.data: break
        for row in r.data:
            try:
                bd = date.fromisoformat(str(row["birth_date"])[:10])
                a  = (today - bd).days // 365
                if 10 <= a <= 110: ages.append(a)
            except Exception: pass
        if len(r.data) < PAGE: break
        offset += PAGE
    buckets = [("18–24",18,25),("25–34",25,35),("35–44",35,45),
               ("45–54",45,55),("55–64",55,65),("65+",65,200)]
    rows = [(lbl, sum(1 for a in ages if lo <= a < hi)) for lbl,lo,hi in buckets]
    return pd.DataFrame(rows, columns=["Faixa","Contatos"]), len(ages)

@st.cache_data(ttl=300)
def load_all_ac_tags():
    sb = get_sb()
    res = sb.table("v_tag_counts").select("tag,total").eq("source", "ac").execute()
    return {r["tag"]: r["total"] for r in res.data}

@st.cache_data(ttl=600)
def load_tier_counts():
    sb = get_sb()
    res = sb.table("v_tier_counts").select("tier,total").execute()
    return {r["tier"]: r["total"] for r in res.data}

@st.cache_data(ttl=600)
def load_rfm_dist():
    sb = get_sb()
    res = sb.table("v_rfm_dist").select("rec,freq,val,total").execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=["rec","freq","val","total"])
    if df.empty:
        return {}, {}, {}
    r_agg = df.groupby("rec")["total"].sum().to_dict()
    f_agg = df.groupby("freq")["total"].sum().to_dict()
    v_agg = df.groupby("val")["total"].sum().to_dict()
    return r_agg, f_agg, v_agg

@st.cache_data(ttl=3600)
def load_slot_counts():
    sb = get_sb()
    _valid = ["Ok","Sim","Yes","OptNewsVNDA","OptTidio","OptShopify","optBlog","OptVNDA","Investor List","Reserva Horta"]
    r_hib  = (sb.table("v_buyer_segments").select("id", count="exact")
               .eq("tier","Hibernando").in_("val",["V3","V4"]).execute())
    r_lead = (sb.table("v_buyer_segments").select("id", count="exact")
               .eq("tier","Lead").in_("opt_in",_valid).execute())
    return (r_hib.count or 0), (r_lead.count or 0)

_OPT_IN_VALID_LIST = ["Ok","Sim","Yes","OptNewsVNDA","OptTidio","OptShopify",
                      "optBlog","OptVNDA","Investor List","Reserva Horta"]
_EXPORT_COLS = "email,first_name,last_name,city,state,tier,rfm_score,opt_in,ultimo_pedido,revenue_vnda,total_compras"

@st.cache_data(ttl=3600)
def _export_segments(tiers: tuple, val_filter: tuple = (), limit: int = 0):
    sb = get_sb()
    PAGE = 1000; offset = 0; rows = []
    while True:
        q = (sb.table("v_buyer_segments")
             .select(_EXPORT_COLS)
             .in_("tier", list(tiers))
             .in_("opt_in", _OPT_IN_VALID_LIST)
             .order("rfm_score", desc=True)
             .order("id"))  # tiebreaker estável → paginação sem sobreposição
        if val_filter:
            q = q.in_("val", list(val_filter))
        fetch = min(PAGE, limit - len(rows)) if limit else PAGE
        r = q.range(offset, offset + fetch - 1).execute()
        if not r.data: break
        rows.extend(r.data)
        if limit and len(rows) >= limit: break
        if len(r.data) < fetch: break
        offset += PAGE
    if not rows:
        return b"", 0
    df = pd.DataFrame(rows)
    # Dedup por email — mantém a 1ª ocorrência (maior RFM, pois vem ordenado DESC)
    df = df.drop_duplicates(subset=["email"], keep="first")
    # Garantia extra: só opt-in válido (a query já filtra, mas reforça)
    df = df[df["opt_in"].isin(_OPT_IN_VALID_LIST)]
    df = df.rename(columns={
        "first_name": "Nome", "last_name": "Sobrenome",
        "city": "Cidade", "state": "Estado",
        "tier": "Tier", "rfm_score": "RFM Score", "opt_in": "Opt-In",
        "ultimo_pedido": "Ultimo Pedido", "revenue_vnda": "Receita VNDA",
        "total_compras": "Total Compras",
    })
    df["Ultimo Pedido"] = (pd.to_datetime(df["Ultimo Pedido"], errors="coerce")
                           .dt.strftime("%d/%m/%Y").fillna(""))
    df["Cidade"] = df["Cidade"].fillna("").replace("None", "")
    df["Estado"] = df["Estado"].fillna("").replace("None", "")
    return df.to_csv(index=False).encode("utf-8"), len(df)

_PROD_LABEL = {
    "RP_Clientes_Bokashi":          "Bokashi",
    "RP_Clientes_MixdePlantio":     "Mix de Plantio",
    "RP_Clientes_NutriçãoBásica":   "Nutrição Básica",
    "RP_Cliente_BK_Capsula":        "Cápsula Bokashi",
    "RP_Clientes_KitMudas":         "Kit Mudas",
    "RP_Clientes_NutriçãoDefesa":   "Nutrição Defesa",
    "RP_Clientes_NutriçãoMulti":    "Nutrição Multi",
    "RP_Clientes_VasosPlasticos":   "Vasos Plásticos",
    "RP_Clientes_OleosEssenciais":  "Óleos Essenciais",
    "RP_Clientes_PlantasVivas":     "Plantas Vivas",
    "RP_Cliente_Hi":                "Horta Inteligente",
    "RP_Cliente_KB":                "KB",
    "RP_Cliente_HI_HO":             "HI Horta Orgânica",
    "RP_Clientes_Refil_HI":         "HI Refil",
    "RP_Cliente_HI_MV":             "HI Módulo Verde",
}

# Shopify revenue conservative estimate (2.700 compras × R$132)
_SHOPIFY_ESTIMATE = 356_400

@st.cache_data(ttl=3600)
def load_product_stats():
    sb = get_sb()
    rows = []
    for tag, label in _PROD_LABEL.items():
        ids = []; offset = 0; PAGE = 1000
        while True:
            r = sb.table("contact_tags").select("contact_id").eq("tag", tag).range(offset, offset+PAGE-1).execute()
            if not r.data: break
            ids.extend(row["contact_id"] for row in r.data)
            if len(r.data) < PAGE: break
            offset += PAGE
        revenues = []
        BATCH = 200
        for i in range(0, len(ids), BATCH):
            rv = sb.table("vnda_data").select("total_confirmados").in_("contact_id", ids[i:i+BATCH]).execute().data
            revenues.extend(r["total_confirmados"] for r in rv if r["total_confirmados"])
        avg = round(sum(revenues) / len(revenues)) if revenues else 0
        rows.append({"Produto": label, "Compradores": len(ids),
                     "Com VNDA": len(revenues), "Avg Ticket": avg})
    return pd.DataFrame(rows).sort_values("Compradores", ascending=False)

_SORT_OPTIONS = {
    "RFM Score (maior primeiro)":      ("rfm_score",     True),
    "Receita VNDA (maior primeiro)":   ("revenue_vnda",  True),
    "Total Compras (maior primeiro)":  ("total_compras", True),
    "Último pedido (mais recente)":    ("ultimo_pedido", True),
    "Último pedido (mais antigo)":     ("ultimo_pedido", False),
    "Score AC (maior primeiro)":       ("score",         True),
}

@st.cache_data(ttl=60)
def search_contacts(query: str):
    sb = get_sb()
    q = query.strip()
    r = (sb.table("v_buyer_segments")
         .select("email,first_name,last_name,state,opt_in,tier,rfm_score,total_compras,purchases_vnda,revenue_vnda,ultimo_pedido")
         .in_("opt_in", _OPT_IN_VALID_LIST)
         .or_(f"email.ilike.%{q}%,first_name.ilike.%{q}%,last_name.ilike.%{q}%")
         .order("rfm_score", desc=True)
         .limit(200)
         .execute())
    return pd.DataFrame(r.data)

@st.cache_data(ttl=600)
def load_contacts_page(page=0, page_size=100, sort_col="rfm_score", sort_desc=True):
    sb = get_sb()
    q = (sb.table("v_buyer_segments")
         .select("email,first_name,last_name,state,opt_in,"
                 "tier,rfm_score,total_compras,purchases_vnda,revenue_vnda,ultimo_pedido")
         .in_("opt_in", _OPT_IN_VALID_LIST))
    if sort_col == "ultimo_pedido":
        q = q.not_.is_("ultimo_pedido", "null")
    q = q.order(sort_col, desc=sort_desc).order("id")  # tiebreaker estável p/ paginação
    res = q.range(page * page_size, (page + 1) * page_size - 1).execute()
    return pd.DataFrame(res.data)

# ─── RD STATION ───────────────────────────────────────────────────────────────
_WORKER_URL    = "https://yeswegrow-ecommerce.rafael-6bb.workers.dev"
_PROXY_SECRET  = "3bc2e301f8734c7fb84e68dd9d021115"

def _rd(resource, start=None, end=None):
    params = {"resource": resource}
    if start: params["start"] = start
    if end:   params["end"]   = end
    try:
        r = http_requests.get(
            f"{_WORKER_URL}/api/rd",
            headers={"X-Proxy-Secret": _PROXY_SECRET},
            params=params, timeout=15
        )
        if r.ok:
            return r.json()
        return {"_error": f"HTTP {r.status_code}", "_body": r.text[:200]}
    except Exception as e:
        return {"_error": str(e)}

@st.cache_data(ttl=180)
def load_rd_leads():
    data = _rd("leads_count")
    contacts = data.get("contacts", [])
    if not contacts:
        return pd.DataFrame(), data.get("_error", "")
    df = pd.DataFrame([{
        "Nome":      c.get("name", ""),
        "Email":     c.get("email", ""),
        "Conversão": pd.to_datetime(c.get("last_conversion_date"), errors="coerce"),
        "Criado em": pd.to_datetime(c.get("created_at"), errors="coerce"),
    } for c in contacts])
    return df, ""

@st.cache_data(ttl=180)
def load_rd_segmentations():
    data = _rd("segmentations")
    segs = data.get("segmentations", [])
    return [s for s in segs if not s["name"].startswith("[EXEMPLO]")]

@st.cache_data(ttl=180)
def load_rd_analytics(days=30):
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end   = datetime.now().strftime("%Y-%m-%d")
    conv  = _rd("analytics_conversions", start, end)
    email = _rd("analytics_emails",      start, end)
    return conv, email

# ─── HEADER ───────────────────────────────────────────────────────────────────
hcol1, hcol2, hcol3 = st.columns([6, 1, 1])
with hcol1:
    st.markdown("""
    <div style='display:flex; align-items:center; gap:12px; padding: 8px 0 16px 0;'>
        <div style='background:#111827; color:#fff; border-radius:2px; width:40px; height:40px;
                    display:flex; align-items:center; justify-content:center; font-size:0.95rem; font-weight:800; flex-shrink:0;'>
            RP
        </div>
        <div>
            <span style='color:#1C2B3A; font-size:1.1rem; font-weight:700;'>RP Station</span>
            <span style='color:#9AAAB8; font-size:0.8rem; margin-left:10px;'>Yes We Grow — Base de Contatos</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
with hcol2:
    if st.button("↺ Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with hcol3:
    _music_on = st.session_state.get("music_on", False)
    if st.button("♫ Som" if not _music_on else "◼ Som", use_container_width=True):
        st.session_state["music_on"] = not _music_on
        st.rerun()

if st.session_state.get("music_on", False):
    components.html("""
<!DOCTYPE html><html><body style="margin:0;padding:2px 0 0 0;overflow:hidden;background:transparent;">
<style>
@keyframes wave{0%,100%{height:3px}50%{height:14px}}
.b{width:3px;background:#9CA3AF;border-radius:2px;display:inline-block;vertical-align:bottom;margin-right:3px;}
</style>
<div style="display:flex;align-items:flex-end;height:18px;">
  <span class="b" style="animation:wave 0.9s ease-in-out infinite 0.00s;"></span>
  <span class="b" style="animation:wave 0.9s ease-in-out infinite 0.15s;"></span>
  <span class="b" style="animation:wave 0.9s ease-in-out infinite 0.30s;"></span>
  <span class="b" style="animation:wave 0.9s ease-in-out infinite 0.45s;"></span>
  <span class="b" style="animation:wave 0.9s ease-in-out infinite 0.60s;"></span>
</div>
<script>
(function(){
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  const ctx = new AC();
  const master = ctx.createGain();
  master.gain.value = 0.09;
  master.connect(ctx.destination);
  const scale = [130.81,146.83,164.81,196.00,220.00,
                 261.63,293.66,329.63,392.00,440.00,523.25];
  function tone(freq, when, dur, vol) {
    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = freq;
    env.gain.setValueAtTime(0, when);
    env.gain.linearRampToValueAtTime(vol || 0.22, when + 0.5);
    env.gain.linearRampToValueAtTime(0, when + dur);
    osc.connect(env); env.connect(master);
    osc.start(when); osc.stop(when + dur + 0.1);
  }
  function next() {
    const t = ctx.currentTime;
    const f = scale[Math.floor(Math.random() * scale.length)];
    tone(f, t, 3 + Math.random() * 3);
    if (Math.random() > 0.5)
      tone(scale[Math.floor(Math.random() * 6)], t + 0.08, 4, 0.09);
  }
  next();
  const iv = setInterval(next, 2400);
  window.addEventListener('beforeunload', function(){ clearInterval(iv); ctx.close(); });
})();
</script>
</body></html>
""", height=24)

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Contatos", "RD Station", "Playbook"])

# ─── OVERVIEW ────────────────────────────────────────────────────────────────
with tab1:
    ov          = load_overview()
    df_opt      = load_opt_in()
    tier_counts = load_tier_counts()
    r_dist, f_dist, v_dist = load_rfm_dist()

    if not ov:
        st.error("Erro ao carregar dados. Verifique as views no Supabase.")
        st.stop()

    total   = ov.get("total_contacts", 0)
    buyers  = ov.get("buyers_total", 0)
    revenue = ov.get("total_revenue", 0)
    avg_t   = ov.get("avg_ticket", 0)

    # Opt-in classification
    _pos = {"Ok","Sim","Yes","OptNewsVNDA","OptTidio","OptShopify","optBlog","OptVNDA","Investor List","Reserva Horta"}
    opted_in  = int(df_opt[df_opt["opt_in"].isin(_pos)]["total"].sum())        if not df_opt.empty else 0
    opted_out = int(df_opt[df_opt["opt_in"] == "No"]["total"].sum())           if not df_opt.empty else 0
    sem_info  = int(df_opt[~df_opt["opt_in"].isin(_pos | {"No"})]["total"].sum()) if not df_opt.empty else 0
    total_ac  = opted_in + opted_out + sem_info

    # ── Row 1: KPI cards ──────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total de Contatos",  f"{total:,}".replace(",", "."))
    c2.metric("Compradores",        f"{buyers:,}".replace(",", "."),
              delta=f"{buyers/total*100:.1f}% da base")
    revenue_total = revenue + _SHOPIFY_ESTIMATE
    c3.metric("Receita Histórica",
              f"R$ {revenue_total:,.0f}".replace(",", "."),
              delta=f"+ R$ {_SHOPIFY_ESTIMATE:,.0f} Shopify est.".replace(",", "."))
    c4.metric("Ticket Médio VNDA",  f"R$ {avg_t:,.2f}".replace(",", "."))
    c5.metric("Opt-in válido",
              f"{opted_in/total_ac*100:.1f}%" if total_ac else "—",
              delta=f"{opted_in:,} contatos".replace(",", "."))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Ciclo de vida (Tiers) + Opt-in donut ───────────────────────────
    col_tier, col_optin = st.columns([3, 1])

    with col_tier:
        st.markdown("### Ciclo de vida")
        _TIER_COLORS = {
            "Campeão":   "#111827",
            "Leal":      "#1F2937",
            "Novo":      "#374151",
            "Promissor": "#4B5563",
            "Em risco":  "#374151",
            "Atenção":   "#6B7280",
            "Hibernando":"#9CA3AF",
        }
        _TIER_ORDER = ["Campeão","Leal","Novo","Promissor","Em risco","Atenção","Hibernando"]
        n_leads = tier_counts.get("Lead", 0)
        buyer_tier_rows = [
            (t, tier_counts.get(t, 0)) for t in _TIER_ORDER
        ]
        df_tier = pd.DataFrame(buyer_tier_rows, columns=["Tier", "Contatos"])
        df_tier = df_tier[df_tier["Contatos"] > 0]
        df_tier["Cor"]   = df_tier["Tier"].map(_TIER_COLORS)
        df_tier["Label"] = df_tier["Contatos"].apply(lambda x: f"{x:,}".replace(",", "."))

        fig_tier = go.Figure(go.Bar(
            x=df_tier["Contatos"], y=df_tier["Tier"],
            orientation="h",
            marker_color=df_tier["Cor"].tolist(),
            text=df_tier["Label"], textposition="outside",
        ))
        fig_tier.update_layout(
            height=300, margin=dict(t=5, b=5, l=5, r=70),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(autorange="reversed"),
            xaxis=dict(gridcolor="#F0F0F0", showticklabels=False),
        )
        st.plotly_chart(fig_tier, use_container_width=True)
        st.caption(f"+ {n_leads:,} Leads (nunca compraram) · RFM calculado em tempo real da base VNDA+AC".replace(",","."))

        with st.expander("O que significa cada tier?"):
            st.markdown("""
O tier classifica cada contato pelo **nº de compras** (VNDA confirmadas ou Shopify) cruzado com a **recência** da última compra:

| Tier | Compras | Última compra | Leitura |
|------|---------|---------------|---------|
| **Campeão** | 4+ | < 2 anos | Melhores clientes — proteger e dar upsell |
| **Leal** | 2–3 | < 1 ano | Recorrentes ativos |
| **Novo** | 1 | < 1 ano | Primeira compra recente — nutrir p/ 2ª compra |
| **Promissor** | 2–3 | 1–2 anos | Já foram recorrentes, esfriando — reconquistar |
| **Atenção** | 1 | 1–2 anos | Compraram 1× e sumiram — reativar |
| **Em risco** | 4+ | > 2 anos | Ex-campeões dormentes — alta LTV, prioridade |
| **Hibernando** | 1+ | > 2 anos | Qualquer compra, sumidos há muito tempo |
| **Lead** | 0 | — | Nunca compraram (não aparecem no gráfico acima) |
""")

    with col_optin:
        st.markdown("### Opt-in")
        df_optin_pie = pd.DataFrame({
            "Status": ["Opt-in", "Sem dados", "Opt-out"],
            "Total":  [opted_in, sem_info, opted_out],
        })
        fig_optin = px.pie(
            df_optin_pie, names="Status", values="Total",
            color_discrete_sequence=["#111827", "#9CA3AF", "#E5E7EB"],
            hole=0.62,
        )
        fig_optin.update_traces(textposition="outside", textinfo="percent")
        fig_optin.update_layout(
            height=320,
            showlegend=True,
            legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center", font_size=11),
            margin=dict(t=5, b=40, l=5, r=5),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_optin, use_container_width=True)

    # ── Divisão da base ───────────────────────────────────────────────────────
    st.markdown("---")
    _n_leads = tier_counts.get("Lead", 0)
    _n_buy   = total - _n_leads
    mc1, mc2 = st.columns(2)
    mc1.metric(
        "Já compraram (VNDA + Shopify)",
        f"{_n_buy:,}".replace(",", "."),
        delta=f"{_n_buy / total * 100:.1f}% da base",
    )
    mc2.metric(
        "Nunca compraram — Leads",
        f"{_n_leads:,}".replace(",", "."),
        delta=f"{_n_leads / total * 100:.1f}% da base",
        delta_color="off",
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 3: R | F | V | Top 5 estados ─────────────────────────────────────
    col_r, col_f, col_v, col_st = st.columns(4)

    with col_r:
        st.markdown("### R — Recência")
        r_labels = [
            ("< 6 meses",  r_dist.get("R1", 0)),
            ("6–12 meses", r_dist.get("R2", 0)),
            ("1–2 anos",   r_dist.get("R3", 0)),
            ("> 2 anos",   r_dist.get("R4", 0)),
        ]
        df_r = pd.DataFrame(r_labels, columns=["Recência", "Contatos"])
        fig_r = px.bar(
            df_r, x="Contatos", y="Recência", orientation="h",
            color_discrete_sequence=["#111827"],
        )
        fig_r.update_layout(
            height=260, margin=dict(t=5, b=5, l=5, r=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(autorange="reversed", tickfont_size=11),
            xaxis=dict(gridcolor="#F0F0F0", showticklabels=False),
        )
        st.plotly_chart(fig_r, use_container_width=True)

    with col_f:
        st.markdown("### F — Frequência")
        f_labels = [
            ("1 compra",  f_dist.get("F1", 0)),
            ("2–3",       f_dist.get("F2", 0)),
            ("4–9",       f_dist.get("F3", 0)),
            ("10+",       f_dist.get("F4", 0)),
        ]
        df_f = pd.DataFrame(f_labels, columns=["Frequência", "Contatos"])
        fig_f = px.bar(
            df_f, x="Frequência", y="Contatos",
            color_discrete_sequence=["#111827"],
        )
        fig_f.update_layout(
            height=260, margin=dict(t=5, b=5, l=5, r=5),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickfont_size=11),
            yaxis=dict(gridcolor="#F0F0F0"),
        )
        st.plotly_chart(fig_f, use_container_width=True)

    with col_v:
        st.markdown("### V — Valor")
        v_labels = [
            ("< R$100",    v_dist.get("V1", 0)),
            ("R$100–200",  v_dist.get("V2", 0)),
            ("R$200–400",  v_dist.get("V3", 0)),
            ("> R$400",    v_dist.get("V4", 0)),
        ]
        df_v = pd.DataFrame(v_labels, columns=["Valor", "Contatos"])
        fig_v = px.bar(
            df_v, x="Valor", y="Contatos",
            color_discrete_sequence=["#111827"],
        )
        fig_v.update_layout(
            height=260, margin=dict(t=5, b=5, l=5, r=5),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickfont_size=10),
            yaxis=dict(gridcolor="#F0F0F0"),
        )
        st.plotly_chart(fig_v, use_container_width=True)

    with col_st:
        st.markdown("### Top 5 Estados")
        df_st = load_states()
        if not df_st.empty:
            fig_st = px.bar(
                df_st.head(5), x="total", y="state", orientation="h",
                color_discrete_sequence=["#111827"],
            )
            fig_st.update_layout(
                height=260, margin=dict(t=5, b=5, l=5, r=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(autorange="reversed", tickfont_size=11),
                xaxis=dict(gridcolor="#F0F0F0", showticklabels=False),
            )
            st.plotly_chart(fig_st, use_container_width=True)

    # ── Row 4: Gênero + Faixa etária ─────────────────────────────────────────
    col_gen, col_age = st.columns([1, 2])

    with col_gen:
        st.markdown("### Gênero")
        g = load_gender_stats()
        f_n, m_n = g["F"], g["M"]
        classified = f_n + m_n
        fig_gen = go.Figure(go.Pie(
            labels=["Feminino", "Masculino"],
            values=[f_n, m_n],
            hole=0.62,
            marker_colors=["#111827", "#9CA3AF"],
            textinfo="percent",
            textposition="outside",
        ))
        fig_gen.update_layout(
            height=260,
            showlegend=True,
            legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center", font_size=11),
            margin=dict(t=5, b=40, l=5, r=5),
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(
                text=f"{classified:,}<br><span style='font-size:10px'>classificados</span>",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=13, color="#1C2B3A"),
            )],
        )
        st.plotly_chart(fig_gen, use_container_width=True)

    with col_age:
        st.markdown("### Faixa Etária")
        df_age, n_age = load_age_stats()
        if not df_age.empty:
            fig_age = px.bar(
                df_age, x="Contatos", y="Faixa", orientation="h",
                color_discrete_sequence=["#111827"],
                text=df_age["Contatos"].apply(lambda x: f"{x:,}"),
            )
            fig_age.update_traces(textposition="outside")
            fig_age.update_layout(
                height=260, margin=dict(t=5, b=5, l=5, r=60),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(autorange="reversed", tickfont_size=11),
                xaxis=dict(gridcolor="#F0F0F0", showticklabels=False),
            )
            st.plotly_chart(fig_age, use_container_width=True)
            st.caption(f"Base: {n_age:,} contatos com data de nascimento ({n_age/total*100:.1f}% da base)")

    # ── Row 5: Produtos / SKUs ────────────────────────────────────────────────
    st.markdown("### Penetração de Produto")
    st.caption("Compradores únicos por produto (tags AC). Ticket = média de receita total VNDA do cliente — proxy de valor, não receita do produto.")

    df_prod = load_product_stats()
    if not df_prod.empty:
        buyers_vnda = ov.get("buyers_vnda", 1) or 1
        df_prod_chart = df_prod.sort_values("Compradores", ascending=True).copy()
        df_prod_chart["Pct"] = (df_prod_chart["Compradores"] / buyers_vnda * 100).round(0).astype(int)
        df_prod_chart["Label"] = df_prod_chart.apply(
            lambda r: f"{r['Compradores']:,}  ·  {r['Pct']}%  ·  R${r['Avg Ticket']:,}".replace(",","."),
            axis=1
        )

        col_bar, col_tbl = st.columns([3, 1])
        with col_bar:
            fig_prod = go.Figure(go.Bar(
                x=df_prod_chart["Compradores"],
                y=df_prod_chart["Produto"],
                orientation="h",
                marker_color="#111827",
                text=df_prod_chart["Label"],
                textposition="outside",
            ))
            fig_prod.update_layout(
                height=max(340, len(df_prod_chart) * 34),
                margin=dict(t=5, b=5, l=5, r=220),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="#F0F0F0", showticklabels=False),
                yaxis=dict(tickfont_size=12),
            )
            st.plotly_chart(fig_prod, use_container_width=True)

        with col_tbl:
            st.markdown("**Ticket médio por produto**")
            df_ticket = df_prod[["Produto","Avg Ticket"]].sort_values("Avg Ticket", ascending=False).copy()
            df_ticket["Avg Ticket"] = df_ticket["Avg Ticket"].apply(lambda x: f"R$ {x:,}".replace(",","."))
            st.dataframe(df_ticket, hide_index=True, use_container_width=True,
                         height=max(340, len(df_ticket) * 35 + 38))

# ─── CONTATOS ────────────────────────────────────────────────────────────────
with tab2:
    search_q = st.text_input("", placeholder="Buscar por nome ou e-mail…", label_visibility="collapsed")

    if search_q and len(search_q) >= 2:
        df = search_contacts(search_q)
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            sort_label = st.selectbox("Ordenar por", list(_SORT_OPTIONS.keys()))
        with col2:
            page_num = st.number_input("Página", min_value=0, value=0, step=1)

        sort_col, sort_desc = _SORT_OPTIONS[sort_label]
        df = load_contacts_page(page=page_num, sort_col=sort_col, sort_desc=sort_desc)

    if not df.empty:
        df.columns = ["Email", "Nome", "Sobrenome", "Estado", "Opt-In",
                      "Tier", "RFM", "Compras", "Pedidos VNDA", "Receita VNDA", "Último Pedido"]
        df["RFM"]          = df["RFM"].fillna(0).astype(int)
        df["Compras"]      = df["Compras"].fillna(0).astype(int)
        df["Pedidos VNDA"] = df["Pedidos VNDA"].fillna(0).astype(int)
        df["Receita VNDA"] = df["Receita VNDA"].fillna(0).apply(lambda x: f"R$ {x:,.2f}")
        df["Estado"]       = df["Estado"].fillna("").replace("None", "")
        df["Opt-In"]       = df["Opt-In"].fillna("").replace("None", "")
        df["Tier"]         = df["Tier"].fillna("Lead")
        df["Último Pedido"] = pd.to_datetime(df["Último Pedido"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")

        st.dataframe(
            df,
            column_config={
                "RFM":    st.column_config.NumberColumn("RFM ↑",  format="%d", help="Score RFM 0–12"),
                "Compras":st.column_config.NumberColumn("Compras",format="%d"),
            },
            use_container_width=True, height=520,
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exportar CSV", csv, "contatos_rp_station.csv", "text/csv")
    else:
        st.info("Nenhum contato encontrado com esses filtros.")

# ─── TAGS ────────────────────────────────────────────────────────────────────
# ─── RD STATION ──────────────────────────────────────────────────────────────
with tab3:
    days_range = st.select_slider("Período", options=[7, 14, 30, 60, 90], value=30, key="rd_days")
    st.markdown("<br>", unsafe_allow_html=True)

    df_leads, rd_err = load_rd_leads()
    segments         = load_rd_segmentations()
    conv, email      = load_rd_analytics(days_range)

    # KPI cards
    total_rd   = len(df_leads)
    n_segments = len(segments)
    n_conv     = len(conv.get("conversions", []))
    n_emails   = len(email.get("emails", []))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads na base RD",     f"{total_rd:,}".replace(",", "."))
    c2.metric("Segmentações",         str(n_segments))
    c3.metric("Conversões (período)", str(n_conv))
    c4.metric("Emails enviados",      str(n_emails))

    if rd_err:
        st.warning(f"Aviso ao buscar leads: {rd_err}")

    st.markdown("<br>", unsafe_allow_html=True)
    col_leads, col_segs = st.columns([3, 2])

    with col_leads:
        st.markdown("### Leads recentes")
        if not df_leads.empty:
            df_show = df_leads.sort_values("Conversão", ascending=False).copy()
            df_show["Conversão"] = df_show["Conversão"].dt.strftime("%d/%m/%Y %H:%M").fillna("")
            df_show["Criado em"] = df_show["Criado em"].dt.strftime("%d/%m/%Y").fillna("")
            st.dataframe(df_show, use_container_width=True, height=380)
        else:
            st.info("Base RD Station ainda vazia — importe os primeiros contatos para começar.")

    with col_segs:
        st.markdown("### Segmentações")
        if segments:
            for s in segments:
                status_color = "#111827" if s.get("process_status") == "processed" else "#6B7280"
                badge = "✓" if s.get("process_status") == "processed" else "⏳"
                standard = " · padrão" if s.get("standard") else ""
                st.markdown(
                    f"<div style='padding:8px 12px; margin-bottom:6px; background:#fff; "
                    f"border:1px solid #E8EAED; border-left:3px solid {status_color}; "
                    f"border-radius:6px; font-size:0.85rem;'>"
                    f"<span style='font-weight:600; color:#1C2B3A;'>{s['name']}</span>"
                    f"<span style='color:#9AAAB8; font-size:0.75rem;'>{standard} {badge}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("Nenhuma segmentação encontrada.")

    # Conversões e emails
    if conv.get("conversions"):
        st.markdown("### Conversões no período")
        df_conv = pd.DataFrame(conv["conversions"])
        st.dataframe(df_conv, use_container_width=True, height=250)

    if email.get("emails"):
        st.markdown("### Campanhas de email")
        df_em = pd.DataFrame(email["emails"])
        st.dataframe(df_em, use_container_width=True, height=250)

    st.caption(f"Worker: {_WORKER_URL} · Cache: 3 min")

# ─── PLAYBOOK ─────────────────────────────────────────────────────────────────
with tab4:
    _tc6 = load_tier_counts()
    _ov6 = load_overview()
    _tot6 = _ov6.get("total_contacts", 0) or 1
    n_hib_prem, n_leads_opt = load_slot_counts()

    st.markdown("## Playbook — 180 dias")
    st.caption("Guia de execução para a equipe · Limite RD Station: 10.000 leads ativos")
    st.markdown("---")

    # ── Importação Inicial ─────────────────────────────────────────────────────
    _IMPORT_LIMIT = 9_000
    _ALL_TIERS = ("Campeão","Leal","Novo","Promissor","Em risco","Atenção","Hibernando","Lead")

    with st.expander("🚀 Importação Inicial — 9.000 contatos", expanded=True):
        ia, ib = st.columns([3, 1])
        with ia:
            st.markdown(f"""
**Objetivo:** carregar os primeiros {_IMPORT_LIMIT:,} contatos no RD Station de uma vez, deixando 1.000 slots de margem.

**Critério de seleção:**
- Todos os tiers (compradores + leads)
- **Apenas opt-in válido** — nunca exporta `No` ou vazio (LGPD)
- **Deduplicado por e-mail** — 1 linha por contato, mantendo o maior RFM
- Ordenados por **RFM Score** — os mais valiosos primeiro
- Inclui **Cidade** e **Estado** para segmentação geográfica no RD

**Após importar:**
- Crie um campo personalizado `tier` no RD Station e mapeie a coluna **Tier** do CSV
- Crie segmentações por tier para usar nas campanhas abaixo
- Lance a **Campanha 1 (Reativação)** imediatamente apontando para Em risco + Promissor + Atenção
""".replace(",", "."))
        with ib:
            if st.button("🔄  Gerar CSV inicial", key="btn_initial_import", use_container_width=True):
                with st.spinner(f"Gerando {_IMPORT_LIMIT:,} contatos… pode levar 20–40 seg".replace(",",".")):
                    st.session_state["exp_initial"] = _export_segments(
                        _ALL_TIERS, limit=_IMPORT_LIMIT
                    )
            if "exp_initial" in st.session_state:
                csv_b, n_rows = st.session_state["exp_initial"]
                st.download_button(
                    f"⬇️ CSV {n_rows:,} contatos".replace(",","."),
                    csv_b, "importacao_inicial_rd.csv", "text/csv",
                    use_container_width=True,
                )
                st.caption(f"{n_rows:,} / {_IMPORT_LIMIT:,} slots".replace(",","."))
            else:
                st.info("Clique em **Gerar CSV inicial** para preparar.")

    with st.expander("📊 Como o RFM Score é calculado (0–12)"):
        st.markdown("""
Cada contato recebe um score somando 3 dimensões, cada uma de **0 a 4**. O total vai de **0 (frio) a 12 (cliente ideal)**.

**R — Recência** (quando comprou pela última vez, base VNDA):

| Pontos | Última compra |
|--------|---------------|
| 4 | < 6 meses |
| 3 | 6–12 meses |
| 2 | 1–2 anos |
| 1 | > 2 anos |
| 0 | nunca comprou |

**F — Frequência** (nº de compras = maior valor entre pedidos VNDA confirmados e Shopify):

| Pontos | Compras |
|--------|---------|
| 4 | 10+ |
| 3 | 4–9 |
| 2 | 2–3 |
| 1 | 1 |
| 0 | 0 |

**V — Valor** (receita total confirmada na VNDA):

| Pontos | Receita |
|--------|---------|
| 4 | > R$400 |
| 3 | R$200–400 |
| 2 | R$100–200 |
| 1 | < R$100 |
| 0 | sem receita VNDA |

**Score final = R + F + V.** É calculado em tempo real pela view `v_buyer_segments` no Supabase — sempre reflete o estado atual da base. O mesmo score também define o **tier** (ciclo de vida) visto na aba Overview.

> ⚠️ A dimensão **V** usa só receita VNDA verificada. Clientes que compraram apenas na Shopify pontuam em F (via tag AC) mas não em V — por isso podem ter RFM um pouco menor que o histórico real.
""")

    st.markdown("---")

    # ── Alocação dos 10k slots ─────────────────────────────────────────────────
    st.markdown("### Alocação dos 10k slots")

    _n_clnn  = _tc6.get("Campeão",0) + _tc6.get("Leal",0) + _tc6.get("Novo",0)
    _n_risk  = _tc6.get("Em risco",0)
    _n_pa    = _tc6.get("Promissor",0) + _tc6.get("Atenção",0)
    _n_leads_slots = max(0, 10000 - _n_clnn - _n_risk - _n_pa - n_hib_prem)
    _total_alloc = _n_clnn + _n_risk + _n_pa + n_hib_prem + min(n_leads_opt, _n_leads_slots)

    sa1, sa2, sa3, sa4, sa5 = st.columns(5)
    sa1.metric("Campeão + Leal + Novo",  f"{_n_clnn:,}".replace(",","."),  "Proteger e upsell")
    sa2.metric("Em risco",               f"{_n_risk:,}".replace(",","."),  "Prioridade 1")
    sa3.metric("Promissor + Atenção",    f"{_n_pa:,}".replace(",","."),    "Reconquistar")
    sa4.metric("Hibernando V3+V4",       f"{n_hib_prem:,}".replace(",","."), "Alta LTV")
    sa5.metric("Leads qualificados",     f"{min(n_leads_opt, _n_leads_slots):,}".replace(",","."), "Topo de funil")
    st.caption(
        f"Total alocado: ~{_total_alloc:,} / 10.000 slots  ·  "
        f"Leads com opt-in válido disponíveis: {n_leads_opt:,}".replace(",",".")
    )
    st.markdown("---")

    # ── Botão preparar exportações ─────────────────────────────────────────────
    st.markdown("### Exportações por campanha")
    st.caption("Clique em **Preparar exportações** para gerar os CSVs. Cada CSV está pronto para importar no RD Station.")

    if st.button("🔄  Preparar exportações", key="btn_prep_exports", use_container_width=False):
        with st.spinner("Gerando CSVs… pode levar 10–20 seg na primeira vez"):
            st.session_state["exp_c1"]      = _export_segments(("Em risco","Promissor","Atenção"))
            st.session_state["exp_c2_comp"] = _export_segments(("Campeão","Leal","Novo","Em risco","Promissor","Atenção"))
            st.session_state["exp_c2_lead"] = _export_segments(("Lead",))
            st.session_state["exp_c3_hib"]  = _export_segments(("Hibernando",), ("V3","V4"))

    _exp = {k: st.session_state[k] for k in
            ("exp_c1","exp_c2_comp","exp_c2_lead","exp_c3_hib")
            if k in st.session_state}

    def _dl_btn(label, key, filename):
        if key in _exp:
            csv_b, n_rows = _exp[key]
            st.download_button(label, csv_b, filename, "text/csv", use_container_width=True)
            st.caption(f"{n_rows:,} contatos com opt-in válido".replace(",","."))
        else:
            st.info("Clique em **Preparar exportações** acima.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Campanha 1 ─────────────────────────────────────────────────────────────
    with st.expander("Campanha 1 — Reativação  (Junho–Agosto)", expanded=True):
        ca, cb = st.columns([3, 1])
        with ca:
            st.markdown("""
**Alvo:** Em risco + Promissor + Atenção
**Objetivo:** 10 % de recompra → ~300 pedidos
**Tag no RD:** `camp_reativacao_2026`

| # | Dia | Assunto sugerido | CTA |
|---|-----|------------------|-----|
| 1 | 0 | *"Sentimos sua falta, [Nome] 🌱"* — mencione o produto que já comprou, mostre o que há de novo | Ver catálogo |
| 2 | 7 | *"Só para você: 15 % de desconto"* — oferta exclusiva para quem foi cliente | Comprar agora |
| 3 | 14 | *"Último aviso — oferta encerra hoje"* — escassez + prova social (avaliações) | Aproveitar |

**Critério de sucesso:** taxa de abertura > 20 %, 1 compra confirmada por e-mail ativado.
**Critério de saída:** sem abertura em e-mail 1 e 2 → remover do slot.
""")
        with cb:
            n_reat = _tc6.get("Em risco",0) + _tc6.get("Promissor",0) + _tc6.get("Atenção",0)
            st.metric("Contatos no segmento", f"{n_reat:,}".replace(",","."))
            _dl_btn("⬇️ CSV Campanha 1", "exp_c1", "camp1_reativacao.csv")

    # ── Campanha 2 ─────────────────────────────────────────────────────────────
    with st.expander("Campanha 2 — Primavera  (Setembro–Outubro)"):
        ca, cb = st.columns([3, 1])
        with ca:
            st.markdown("""
**Alvo A — Compradores ativos:** Campeão + Leal + Novo + Em risco + Promissor + Atenção
**Alvo B — Leads:** contatos com opt-in válido, 1ª compra ainda não realizada
**Tag no RD:** `camp_primavera_comp_2026` / `camp_primavera_leads_2026`

**Flow Compradores (3 e-mails):**

| # | Dia | Assunto sugerido | CTA |
|---|-----|------------------|-----|
| 1 | 0 | *"Chegou a hora de plantar, [Nome] 🌿"* — contexto de primavera + produto certo para o momento | Ver Kits |
| 2 | 5 | *"Bokashi + Mix de Plantio: combinação perfeita"* — educação + combo | Comprar combo |
| 3 | 12 | *"Cuide da sua horta neste verão"* — Nutrição + upsell HI | Ver Nutrição |

**Flow Leads (3 e-mails):**

| # | Dia | Assunto sugerido | CTA |
|---|-----|------------------|-----|
| 1 | 0 | *"Como montar sua primeira horta em casa"* — conteúdo educativo, sem venda direta | Ler guia |
| 2 | 7 | *"Kit Starter YWG: tudo para começar"* — produto de entrada com baixo risco | Ver kit |
| 3 | 15 | *"10 % na primeira compra — só até domingo"* — urgência real | Comprar |

**Critério de saída leads:** sem clique após e-mail 2 → remover do slot e substituir.
""")
        with cb:
            n_comp_at = sum(_tc6.get(t,0) for t in ("Campeão","Leal","Novo","Em risco","Promissor","Atenção"))
            st.metric("Compradores ativos", f"{n_comp_at:,}".replace(",","."))
            _dl_btn("⬇️ CSV Compradores", "exp_c2_comp", "camp2_compradores.csv")
            st.markdown("")
            st.metric("Leads com opt-in", f"{n_leads_opt:,}".replace(",","."))
            _dl_btn("⬇️ CSV Leads", "exp_c2_lead", "camp2_leads.csv")

    # ── Campanha 3 ─────────────────────────────────────────────────────────────
    with st.expander("Campanha 3 — Natal  (Novembro–Dezembro)"):
        ca, cb = st.columns([3, 1])
        with ca:
            st.markdown("""
**Alvo:** Hibernando V3+V4 (LTV histórica > R$200) + leads que não converteram na campanha 2
**Objetivo:** presentes criativos vs. varejo genérico
**Produtos destaque:** Horta Inteligente, Plantas Vivas, Óleos Essenciais
**Tag no RD:** `camp_natal_2026`

| # | Dia | Assunto sugerido | CTA |
|---|-----|------------------|-----|
| 1 | 0 | *"O presente que todo amante de plantas quer 🎁"* — posicionar como alternativa criativa ao varejo | Ver sugestões |
| 2 | 7 | *"Horta Inteligente: o favorito do Natal"* — social proof + fotos reais de clientes | Ver HI |
| 3 | 14 | *"Frete grátis + embrulho especial até dia 20"* — deadline real de entrega | Comprar agora |

**Para leads não convertidos:** reusar CSV da Campanha 2, excluindo quem comprou.
**Critério de saída:** sem abertura nos 3 e-mails → desinscrever do slot, não desperdiçar limite.
""")
        with cb:
            st.metric("Hibernando V3+V4", f"{n_hib_prem:,}".replace(",","."))
            _dl_btn("⬇️ CSV Hibernando Premium", "exp_c3_hib", "camp3_natal_hib.csv")
            st.caption("Leads: reusar CSV da Campanha 2")

    st.markdown("---")

    # ── Regras de gestão ───────────────────────────────────────────────────────
    st.markdown("### Regras de gestão dos 10k slots")
    st.markdown("""
| Situação | Ação |
|----------|------|
| Sem abertura em 60 dias | Remover do RD · substituir pelo próximo da fila |
| Compra confirmada | Retirar da sequência ativa · reclassificar tier automaticamente |
| Lead converte | Mover para flow de compradores |
| Slot < 9.000 | Importar novo lote de leads (CSV Campanha 2 — Leads) |

**Prioridade de fila de entrada:**
Campeão → Leal → Em risco → Promissor → Atenção → Hibernando V3/V4 → Leads opt-in

**Nunca importar** contatos com `Opt-in = No` ou `(vazio)` — risco LGPD.
**Atualizar os CSVs** aqui mensalmente: clicar em *Preparar exportações* no início de cada mês.
""")
