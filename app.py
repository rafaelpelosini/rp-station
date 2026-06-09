import re
import unicodedata
from datetime import datetime, timedelta, date
import requests as http_requests
import streamlit as st
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

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif !important; }

/* Fundo geral */
.stApp { background-color: #F5F7F9 !important; }
[data-testid="stAppViewContainer"] { background-color: #F5F7F9 !important; }

/* Esconde sidebar toggle */
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebar"] { display: none !important; }

/* Tabs — estilo nav bar */
[data-testid="stTabs"] [role="tablist"] {
    background: #FFFFFF;
    border-bottom: 1px solid #E8EAED;
    padding: 0 8px;
    gap: 0;
}
[data-testid="stTabs"] [role="tab"] {
    color: #5F6B7A !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    padding: 12px 20px !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    background: transparent !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #0090A8 !important;
    border-bottom: 2px solid #0090A8 !important;
    font-weight: 600 !important;
}
[data-testid="stTabs"] [role="tab"]:hover {
    color: #0090A8 !important;
    background: #F0FAFB !important;
}
[data-testid="stTabsContent"] {
    padding-top: 24px !important;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #E8EAED;
    border-radius: 8px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
[data-testid="stMetricValue"]  { color: #1C2B3A !important; font-weight: 700 !important; font-size: 1.6rem !important; }
[data-testid="stMetricLabel"]  { color: #7A8899 !important; font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricDelta"]  { font-size: 0.78rem !important; }

/* Títulos */
h1 { color: #1C2B3A !important; font-weight: 700 !important; font-size: 1.3rem !important; }
h2 { color: #1C2B3A !important; font-weight: 600 !important; font-size: 1.1rem !important; }
h3 { color: #3D4F60 !important; font-weight: 500 !important; font-size: 0.92rem !important; }

/* Botões */
.stButton > button {
    background-color: #0090A8 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
    padding: 6px 16px !important;
    transition: background 0.15s;
}
.stButton > button:hover { background-color: #007891 !important; }

/* Botão de download */
[data-testid="stDownloadButton"] > button {
    background-color: #FFFFFF !important;
    color: #0090A8 !important;
    border: 1px solid #C8D8DC !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
}
[data-testid="stDownloadButton"] > button:hover { background-color: #F0FAFB !important; }

/* Dividers */
hr { border-color: #E8EAED; margin: 10px 0 18px 0; }

/* Section card */
.section-card {
    background: #FFFFFF;
    border: 1px solid #E8EAED;
    border-radius: 8px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    margin-bottom: 16px;
}

/* Dataframe */
[data-testid="stDataFrame"] { border: 1px solid #E8EAED; border-radius: 8px; }

/* Inputs */
[data-testid="stSelectbox"] > div > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {
    border-radius: 6px !important;
    border-color: #D1D9E0 !important;
    background: #FFFFFF !important;
    font-size: 0.88rem !important;
}

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

@st.cache_data(ttl=600)
def load_contacts_page(page=0, page_size=100, opt_in_filter=None, sort_col="rfm_score", sort_desc=True):
    sb = get_sb()
    q = sb.table("v_buyer_segments").select(
        "email,first_name,last_name,state,opt_in,"
        "tier,rfm_score,total_compras,purchases_vnda,revenue_vnda,ultimo_pedido"
    )
    if opt_in_filter and opt_in_filter != "Todos":
        q = q.eq("opt_in", opt_in_filter)
    if sort_col == "ultimo_pedido":
        q = q.not_.is_("ultimo_pedido", "null")
    q = q.order(sort_col, desc=sort_desc)
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
hcol1, hcol2 = st.columns([6, 1])
with hcol1:
    st.markdown("""
    <div style='display:flex; align-items:center; gap:12px; padding: 8px 0 16px 0;'>
        <div style='background:#0090A8; color:#fff; border-radius:8px; width:36px; height:36px;
                    display:flex; align-items:center; justify-content:center; font-size:0.95rem; font-weight:700; flex-shrink:0;'>
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

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊  Overview", "👥  Contatos", "🏷️  Tags", "📤  Exportações", "🟠  RD Station"])

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
            "Campeão":   "#059669",
            "Leal":      "#10B981",
            "Novo":      "#22D3EE",
            "Promissor": "#60A5FA",
            "Em risco":  "#EF4444",
            "Atenção":   "#FB923C",
            "Hibernando":"#94A3B8",
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

    with col_optin:
        st.markdown("### Opt-in")
        df_optin_pie = pd.DataFrame({
            "Status": ["Opt-in", "Sem dados", "Opt-out"],
            "Total":  [opted_in, sem_info, opted_out],
        })
        fig_optin = px.pie(
            df_optin_pie, names="Status", values="Total",
            color_discrete_sequence=["#0090A8", "#CBD5E1", "#EF4444"],
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
            color_discrete_sequence=["#0090A8"],
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
            color_discrete_sequence=["#0090A8"],
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
            color_discrete_sequence=["#0090A8"],
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
                color_discrete_sequence=["#0090A8"],
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
            marker_colors=["#E879A0", "#60A5FA"],
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
                color_discrete_sequence=["#0090A8"],
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
                marker_color="#0090A8",
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
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        opt_filter = st.selectbox(
            "Opt-In",
            ["Todos", "Ok", "Sim", "Yes", "OptNewsVNDA", "OptTidio", "OptShopify", "optBlog", "No", "(vazio)"]
        )
    with col2:
        sort_label = st.selectbox("Ordenar por", list(_SORT_OPTIONS.keys()))
    with col3:
        src_filter = st.selectbox("Fonte", ["Todos", "Só AC", "Só VNDA", "Ambos"])
    with col4:
        page_num = st.number_input("Página", min_value=0, value=0, step=1)

    sort_col, sort_desc = _SORT_OPTIONS[sort_label]
    df = load_contacts_page(
        page=page_num,
        opt_in_filter=None if opt_filter == "Todos" else opt_filter,
        sort_col=sort_col,
        sort_desc=sort_desc,
    )

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
with tab3:
    df_tags = load_top_tags(60)

    search = st.text_input("Buscar tag", placeholder="ex: RP_Clientes, shopify...")
    if search:
        df_tags = df_tags[df_tags["tag"].str.contains(search, case=False, na=False)]

    if not df_tags.empty:
        fig = px.bar(
            df_tags.head(40), x="total", y="tag", orientation="h",
            color="total",
            color_continuous_scale=["#99DDE8", "#0090A8", "#005F70"],
            labels={"total": "Contatos", "tag": ""},
        )
        fig.update_layout(
            margin=dict(t=10, b=10, l=10, r=20),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=max(400, len(df_tags.head(40)) * 22),
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"**{len(df_tags)} tags** encontradas")
        st.dataframe(df_tags, use_container_width=True, height=300)

# ─── RD STATION ──────────────────────────────────────────────────────────────
with tab5:
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
                status_color = "#0090A8" if s.get("process_status") == "processed" else "#FB923C"
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

    st.markdown(
        "<div style='margin-top:20px; padding:10px 14px; background:#F0FAFB; border:1px solid #C8E8ED; "
        "border-radius:6px; font-size:0.78rem; color:#5F6B7A;'>"
        f"🔗 Worker: <code>{_WORKER_URL}</code> · Cache: 3 min"
        "</div>",
        unsafe_allow_html=True
    )

# ─── EXPORTAÇÕES ─────────────────────────────────────────────────────────────
with tab4:
    sb = get_sb()
    res = sb.table("rd_exports").select("*").order("exported_at", desc=True).limit(50).execute()

    if res.data:
        df_exp = pd.DataFrame(res.data)
        st.dataframe(df_exp, use_container_width=True)
    else:
        st.info("Nenhuma exportação registrada ainda.")
        st.markdown("""
        <div class='section-card'>
            <h4>Como exportar para o RD Station</h4>
            <p>Em breve: selecione um segmento na aba <b>Contatos</b> e clique em <b>Enviar para RD Station</b>.</p>
            <p>Por enquanto, use o botão <b>Exportar CSV</b> na aba Contatos e importe manualmente no RD Station.</p>
        </div>
        """, unsafe_allow_html=True)
