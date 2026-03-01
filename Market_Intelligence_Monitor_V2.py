########################################################################
# MARKET INTELLIGENCE MONITOR — V2
# Instalación requerida:
#   pip install reportlab yfinance pandas pandas_datareader seaborn matplotlib numpy
#
# NUEVAS SECCIONES vs V1:
#   0. Risk Scorecard (semáforos por dimensión analítica)
#   6. Global Macro & Credit Spreads  (EEM, EWG, EWJ, FXI, HYG, EMB)
#   7. Advanced Curve Analysis        (2Y FRED, Term Premium, Real Rates)
#   8. Market Liquidity               (Amihud Ratio, Volume Breadth)
#   9. Scenario Analysis              (Bull / Base / Bear con probabilidades)
########################################################################

import warnings
warnings.filterwarnings('ignore')

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime, timedelta
from io import BytesIO

import pandas_datareader.data as web   # Para series FRED (2Y Treasury, Fed Funds)

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Image, Table, TableStyle, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT

# ══════════════════════════════════════════════════════════════════════
# 1. INPUTS ESTRATÉGICOS
#    → Modifica ANALYSIS, UPCOMING_EVENTS, PORTFOLIO y SCENARIOS_DATA
# ══════════════════════════════════════════════════════════════════════

ANALYSIS = {
    # ── Sección 1: Macro Overview ─────────────────────────────────────
    "MACRO_HEADER": """<b>SNAPSHOT DIARIO:</b> Los mercados de renta variable continúan su expansión de múltiplos. Sin embargo, la fortaleza del Dólar (DXY) y el repunte en las tasas reales sugieren condiciones financieras restrictivas.""",
    "MACRO_BODY": """El entorno actual se define como expansión de múltiplos, donde el crecimiento del S&P500 parece estar respaldado por la resiliencia del sentimiento del mercado a pesar del endurecimiento financiero. El S&P500 mantiene una tendencia alcista estructural mientras la volatilidad (VIX) se mantiene en niveles históricamente bajos — señal de complacencia donde el mercado ignora el riesgo de cola.""",

    # ── Sección 2: Tactical Alpha ─────────────────────────────────────
    "ALPHA_BODY": """<b>Forecast (for 1 month):</b> El Implied Cone proyecta un rango de movimiento de 2.5% para el próximo mes. Esto indica que el activo está operando en el límite superior de lo que la volatilidad implícita considera normal. Con un RSI en 68, el mercado está en la frontera técnica de la sobrecompra por lo cual se sugiere cautela: la relación riesgo-recompensa para nuevas posiciones largas es desfavorable.""",

    # ── Sección 3: Rates Structure ────────────────────────────────────
    "RATES_BODY": """La inversión de la curva (Spread 10Y-3M) persiste. Sin embargo, la atención se centra en los 'Breakevens' de inflación (<b>ver Fig 3.2</b>). El mercado ha descontado una normalización, pero el repunte reciente en el tramo largo sugiere inflación creciente. El ratio TIP/IEF muestra tendencia al alza, sugiriendo que el mercado espera que la inflación real supere a la nominal en el mediano plazo.""",

    # ── Sección 4: Risk & Correlation ────────────────────────────────
    "RISK_BODY": """El efecto de la diversificación se ha deteriorado. La correlación SPY/TLT ha roto al alza (+0.45), eliminando el beneficio de la diversificación y aumentando el riesgo sistémico de la cartera. La correlación de 0.91 entre TLT (Bonos largos) e IEF (Bonos medios) es esperada, pero la correlación negativa entre SPY y VIX confirma su cobertura limpia contra una caída de renta variable.""",

    # ── Sección 5: Portfolio Fragility ───────────────────────────────
    "PORTFOLIO_BODY": """Los bonos han sufrido una caída desde máximos más profunda y prolongada que las acciones. El S&P500 ha mostrado recuperación más rápida; los Bonos mantienen drawdowns prolongados impactando en la liquidez institucional. Esto evidencia que la renta fija ha dejado de ser el activo refugio tradicional en este ciclo de tasas.""",

    # ── Sección 6: Global Macro & Credit ─────────────────────────────
    "GLOBAL_BODY": """La divergencia entre mercados desarrollados y emergentes se amplía. EEM (Emergentes) y FXI (China) muestran underperformance estructural frente al S&P500, mientras que EWG (Alemania) se beneficia de la debilidad relativa del Euro. El spread de High Yield (HYG) como proxy de crédito muestra señales mixtas: compresión de spreads en ciclos de riesgo, pero con reversión reciente que anticipa cautela. EMB (Deuda EM) cotiza bajo presión ante el fortalecimiento del USD.""",

    # ── Sección 7: Advanced Curve ─────────────────────────────────────
    "ADVANCED_CURVE_BODY": """El análisis avanzado de la curva incorpora el spread 2Y-10Y (el más utilizado por la Fed para señales de recesión) junto al rendimiento real ex-ante derivado del diferencial TIP/IEF. El término premium — diferencia entre el yield nominal y la expectativa de tasas cortas — muestra compresión, lo que sugiere que el mercado no está exigiendo compensación adicional por riesgo de duración. Este fenómeno es históricamente precedido por episodios de re-pricing abrupto.""",

    # ── Sección 8: Market Liquidity ───────────────────────────────────
    "LIQUIDITY_BODY": """El ratio de iliquidez de Amihud mide el impacto de precio por unidad de volumen negociado — valores altos señalan deterioro de liquidez de mercado. El análisis del volumen relativo (vs. media 20D) muestra si los movimientos de precio están respaldados por participación real o son movimientos de baja convicción. Un VIX elevado combinado con volumen bajo es la antesala de movimientos violentos de reversión.""",

    # ── Sección 9: Scenario Analysis ─────────────────────────────────
    "SCENARIO_BODY": """El framework de tres escenarios cuantifica las probabilidades y catalizadores del entorno actual. El escenario Base asigna un 50% de probabilidad a una consolidación en el rango actual con inflación moderada. El escenario Bull (25%) requiere un pivote de la Fed con datos de empleo sólidos. El escenario Bear (25%) contempla un resurgimiento de inflación o un accidente de crédito que fuerce re-pricing masivo de activos de riesgo. Los niveles de invalidación técnica funcionan como triggers de re-evaluación del escenario activo.""",

    # ── Pies de Figura ────────────────────────────────────────────────
    "CAPTION_MACRO":     """<b>Fig 1.1:</b> La divergencia entre el S&P500 (Azul) subiendo y el VIX (Gris) en mínimos indica un entorno de 'Risk-On' frágil.""",
    "CAPTION_VIX":       """<b>Fig 1.2:</b> Mide la volatilidad relativa. Valores &lt; -1.5 (Verde) indican opciones baratas; &gt; +2.0 (Rojo) indican pánico excesivo.""",
    "CAPTION_CONE":      """<b>Fig 2.1:</b> Proyección a 1 mes basada en volatilidad implícita. El 68% del tiempo el precio se mantendrá en la zona azul clara.""",
    "CAPTION_CURVE":     """<b>Fig 3.1:</b> Comparativa de la estructura de tasas hoy vs el pasado. Una curva invertida (cortas &gt; largas) alerta recesión.""",
    "CAPTION_RECESSION": """<b>Fig 3.2:</b> Spread 10Y-3M negativo (Rojo) predice recesión. Ratio TIP/IEF (Rojo) mide expectativas de inflación.""",
    "CAPTION_CORR":      """<b>Fig 4.1:</b> Correlación móvil SPY/TLT. Zonas Verdes = Cobertura efectiva. Zonas Rojas = Fallo de diversificación.""",
    "CAPTION_HEATMAP":   """<b>Fig 4.2:</b> Mapa de calor de 90 días. Colores cálidos indican activos moviéndose al unísono (riesgo sistémico).""",
    "CAPTION_DD":        """<b>Fig 5.1:</b> Muestra la profundidad de caída desde máximos. Note cómo los bonos (Rojo) siguen en drawdown profundo.""",
    "CAPTION_STRESS":    """<b>Fig 5.2:</b> Impacto estimado en P&amp;L ($) bajo escenarios de choque. El 'Bear Flattener' es el riesgo central actual.""",
    "CAPTION_GLOBAL":    """<b>Fig 6.1:</b> Performance relativa normalizada (base 100). Divergencia entre mercados desarrollados y emergentes.""",
    "CAPTION_CREDIT":    """<b>Fig 6.2:</b> Ratio HYG/IEF como proxy de spread crediticio. Caídas indican ampliación de spreads y aversión al riesgo.""",
    "CAPTION_ADV_CURVE": """<b>Fig 7.1:</b> Spreads 2Y-10Y y 10Y-3M. Ambos negativos confirman señal recesiva; la normalización indica re-pricing.""",
    "CAPTION_REAL_RATES":"""<b>Fig 7.2:</b> Rendimiento real aproximado (TIP yield proxy). Tasas reales positivas comprimen valuaciones de renta variable.""",
    "CAPTION_AMIHUD":    """<b>Fig 8.1:</b> Ratio de Amihud (rolling 21D). Picos indican deterioro de liquidez; valores altos preceden volatilidad.""",
    "CAPTION_VOLUME":    """<b>Fig 8.2:</b> Volumen SPY relativo a media 20D. Barras rojas = volumen por encima de media (posibles puntos de inflexión).""",

    # ── Market Monitoring Implications ───────────────────────────────
    "TAKEAWAYS": """CONDITIONS: Iniciar cortos tácticos en activos de alto beta si el VIX supera 20.
SUGGEST: Mantenerse en la parte corta de la curva en bonos de 1-3 años (SHY). Evaluar TIPS ante re-aceleración de inflación.
GLOBAL: Subponderar EEM y FXI hasta confirmación de pivote Fed. EWG ofrece valor relativo vs SPY.
LIQUIDITY: Monitorear Amihud SPY — un spike >2x su media señala ventana de stress inminente.
OPPORTUNITIES: Usar la banda superior del Cono Implícito como nivel de Take Profit parcial.
MONITOR: CPI, NFP y minutas Fed son los catalizadores clave del próximo 30 días.""",
}

# ── Próximos Eventos (modificar según calendario económico actual) ────
UPCOMING_EVENTS = [
    ['Date',   'Time (ET)',  'Event / Release',      'Consensus / Impact'],
    ['Feb-10', '08:30 AM',  'Retail Sales MoM',     'Exp: 0.4%  | Consumer Health'],
    ['Feb-11', '08:30 AM',  'Unemployment Rate',    'Exp: 4.4%  | High Impact'],
    ['Feb-11', '08:30 AM',  'Nonfarm Payrolls',     'Exp: 70k   | High Impact'],
    ['Feb-13', '08:30 AM',  'CPI YoY (Inflation)',  'Exp: 2.5%  | High Impact'],
    ['Feb-19', '02:00 PM',  'FOMC Minutes',         'Fed Guidance | High Impact'],
    ['Feb-20', '08:30 AM',  'GDP (Q4) QoQ',         'Exp: 4.0%  | Production'],
    ['Feb-20', '09:45 AM',  'PMI Global',           'Exp: 52.4  | Production'],
    ['Feb-26', '10:00 AM',  'Consumer Confidence',  'Exp: 104.5 | Sentiment'],
]

# ── Portfolio a Testear ───────────────────────────────────────────────
PORTFOLIO = {
    'SPY': {'Notional': 5_000_000, 'Duration': 0.0},
    'TLT': {'Notional': 6_000_000, 'Duration': 17.0},
    'IEF': {'Notional': 3_000_000, 'Duration': 7.5},
    'SHY': {'Notional': 4_000_000, 'Duration': 1.9},
}

# ── Escenarios (editar manualmente según visión de mercado) ──────────
SCENARIOS_DATA = {
    'headers': ['Dimensión', 'BEAR  25%', 'BASE  50%', 'BULL  25%'],
    'rows': [
        ['Catalizador',
         'Inflación reaccelera,\naccidente crediticio',
         'Soft landing,\nFed en pausa',
         'Pivote Fed + datos\nempleo sólidos'],
        ['S&P 500 Target',    '< 5,800 (-9%)',   '6,200 – 6,800',     '> 7,200 (+10%)'],
        ['Fed Funds',         '> 5.50% (hike)',  '5.25% (hold)',      '< 4.75% (cut)'],
        ['10Y Treasury',      '> 5.00%',         '4.25% – 4.75%',     '< 4.00%'],
        ['DXY',               '> 105',           '98 – 103',          '< 95'],
        ['VIX',               '> 30',            '15 – 22',           '< 14'],
        ['Duración óptima',   'Muy corta (SHY)', 'Neutral / IEF',     'Larga (TLT)'],
        ['Señal de entrada',  'VIX > 28 + SPY\nperfora 200MA',
                              'RSI entre 45-60\n+ spread estable',
                              'VIX < 13 + NFP\n> 200k'],
        ['Invalidación',      'SPY > 6,900',     'CPI > 3.5%\no VIX > 28',
                              'SPY < 6,200'],
    ]
}

# ══════════════════════════════════════════════════════════════════════
# 2. DATA ENGINE
# ══════════════════════════════════════════════════════════════════════
print("Descargando Datos de Yahoo Finance...")

TICKERS_CURVE = {'3M': '^IRX', '5Y': '^FVX', '10Y': '^TNX', '30Y': '^TYX'}

# Activos principales (secciones 1-5)
TICKERS_CORE = ['SPY', 'TLT', 'IEF', 'SHY', 'TIP', 'DX-Y.NYB', '^VIX']

# Nuevos activos (secciones 6-8)
TICKERS_GLOBAL  = ['EEM', 'EWG', 'EWJ', 'FXI', 'HYG', 'EMB']  # Global Macro
TICKERS_LIQ     = ['SPY']   # Liquidez — necesitamos OHLCV completo

ALL_YF = list(TICKERS_CURVE.values()) + TICKERS_CORE + TICKERS_GLOBAL

end_date   = datetime.now()
start_date = end_date - timedelta(days=365 * 3)

# Descarga precio de cierre ajustado
raw = yf.download(ALL_YF, start=start_date, end=end_date, auto_adjust=True, progress=False)

try:
    data = raw['Close'].ffill().dropna(how='all')
except Exception:
    data = raw.ffill().dropna(how='all')

# Normalizar tickers de curva (algunos vienen x10 en yfinance)
for t in TICKERS_CURVE.values():
    if t in data.columns:
        data[t] = data[t].apply(lambda x: x / 10 if x > 20 else x)

# Descarga OHLCV de SPY para análisis de liquidez
print("Descargando OHLCV para análisis de liquidez (SPY)...")
spy_ohlcv = yf.download('SPY', start=start_date, end=end_date,
                         auto_adjust=True, progress=False)

# Descarga series FRED (2Y Treasury y Fed Funds Rate)
print("Descargando series FRED (DGS2, DFF)...")
try:
    fred_start = start_date.strftime('%Y-%m-%d')
    fred_end   = end_date.strftime('%Y-%m-%d')
    dgs2 = web.DataReader('DGS2', 'fred', fred_start, fred_end)   # 2Y Treasury yield
    dff  = web.DataReader('DFF',  'fred', fred_start, fred_end)   # Fed Funds Effective Rate
    dgs2 = dgs2.ffill().reindex(data.index, method='ffill').dropna()
    dff  = dff.ffill().reindex(data.index, method='ffill').dropna()
    HAS_FRED = True
    print("FRED OK.")
except Exception as e:
    print(f"FRED no disponible: {e}. Se usarán proxies de Yahoo Finance.")
    HAS_FRED = False

# ══════════════════════════════════════════════════════════════════════
# 3. CÁLCULOS
# ══════════════════════════════════════════════════════════════════════
print("Calculando Métricas...")

# ── Cambios periódicos ────────────────────────────────────────────────
def calc_changes(df):
    chg = pd.DataFrame(index=df.columns)
    chg['Last']  = df.iloc[-1]
    chg['1M %']  = df.pct_change(21).iloc[-1]
    chg['3M %']  = df.pct_change(63).iloc[-1]
    chg['6M %']  = df.pct_change(126).iloc[-1]
    chg['1Y %']  = df.pct_change(252).iloc[-1]
    return chg

metrics_df = calc_changes(data[['SPY', '^VIX', 'DX-Y.NYB', 'TLT']])

# ── Predictive Cone (Sección 2) ───────────────────────────────────────
last_price = data['SPY'].iloc[-1]
last_vix   = data['^VIX'].iloc[-1]
daily_vol  = (last_vix / 100) / np.sqrt(252)
days_fwd   = 21
future_dates = [data.index[-1] + timedelta(days=i) for i in range(1, days_fwd + 1)]
upper_1std = [last_price * (1 + daily_vol * np.sqrt(i)) for i in range(1, days_fwd + 1)]
lower_1std = [last_price * (1 - daily_vol * np.sqrt(i)) for i in range(1, days_fwd + 1)]
upper_2std = [last_price * (1 + 2 * daily_vol * np.sqrt(i)) for i in range(1, days_fwd + 1)]
lower_2std = [last_price * (1 - 2 * daily_vol * np.sqrt(i)) for i in range(1, days_fwd + 1)]

# ── RSI ───────────────────────────────────────────────────────────────
delta = data['SPY'].diff()
gain  = delta.where(delta > 0, 0).rolling(14).mean()
loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
data['RSI'] = 100 - (100 / (1 + gain / loss))

# ── VIX Z-Score ───────────────────────────────────────────────────────
vix_m = data['^VIX'].rolling(126).mean()
vix_s = data['^VIX'].rolling(126).std()
data['VIX_Z'] = (data['^VIX'] - vix_m) / vix_s

# ── Spreads e inflación ───────────────────────────────────────────────
data['Spread_10Y3M']    = data[TICKERS_CURVE['10Y']] - data[TICKERS_CURVE['3M']]
data['Inflation_Proxy'] = data['TIP'] / data['IEF']

# ── Correlaciones ─────────────────────────────────────────────────────
rets     = np.log(data / data.shift(1))
roll_corr = rets['SPY'].rolling(63).corr(rets['TLT'])

# ── Drawdowns ─────────────────────────────────────────────────────────
def get_dd(s): return (s / s.cummax()) - 1.0
dd_spy = get_dd(data['SPY'])
dd_tlt = get_dd(data['TLT'])

# ── Stress Test ───────────────────────────────────────────────────────
stress_impact = {
    'Parallel +50bps':  sum(-p['Notional'] * p['Duration'] * 0.0050 for p in PORTFOLIO.values()),
    'Bear Flattener':   (-PORTFOLIO['SHY']['Notional'] * 1.9 * 0.0050) +
                        (-PORTFOLIO['TLT']['Notional'] * 17 * 0.0010),
    'Equity Crash -10%': PORTFOLIO['SPY']['Notional'] * -0.10,
    'Inflation Shock':  (PORTFOLIO['TLT']['Notional'] * -0.05) +
                        (PORTFOLIO['SPY']['Notional'] * -0.08),
}

# ── Global Macro (Sección 6) ──────────────────────────────────────────
global_tickers = ['SPY', 'EEM', 'EWG', 'EWJ', 'FXI']
available_global = [t for t in global_tickers if t in data.columns]
global_data = data[available_global].dropna(how='all')

# Normalizar a base 100 usando último año
global_1y = global_data.tail(252).dropna(how='all')
global_norm = (global_1y / global_1y.iloc[0]) * 100

# Credit Spread Proxy: HYG / IEF ratio
if 'HYG' in data.columns and 'IEF' in data.columns:
    data['Credit_Proxy'] = data['HYG'] / data['IEF']
else:
    data['Credit_Proxy'] = np.nan

# ── Advanced Curve (Sección 7) ────────────────────────────────────────
if HAS_FRED:
    # Spread 2Y-10Y (el spread "clásico" de recesión de la Fed)
    tnx_aligned = data[TICKERS_CURVE['10Y']].reindex(dgs2.index, method='ffill')
    data_curve   = pd.DataFrame({
        '2Y':  dgs2['DGS2'],
        '10Y': tnx_aligned,
    }).dropna()
    data_curve['Spread_2Y10Y'] = data_curve['10Y'] - data_curve['2Y']

    # Proxy de tasa real: TIP yield implícito — usamos precio de TIP vs IEF
    # Real rate proxy = 10Y nominal - breakeven (TIP/IEF ratio normalizado)
    tip_ief_norm  = data['Inflation_Proxy']
    real_rate_proxy = data[TICKERS_CURVE['10Y']] - (tip_ief_norm * 2.5).shift(1)  # escalado heurístico
else:
    # Proxy de 2Y usando IRX + FVX interpolado si no hay FRED
    irx  = data[TICKERS_CURVE['3M']]
    fvx  = data[TICKERS_CURVE['5Y']]
    data_curve = pd.DataFrame({
        '2Y':  irx * 0.4 + fvx * 0.6,      # interpolación lineal simple
        '10Y': data[TICKERS_CURVE['10Y']],
    }).dropna()
    data_curve['Spread_2Y10Y'] = data_curve['10Y'] - data_curve['2Y']
    real_rate_proxy = data[TICKERS_CURVE['10Y']] - (data['VIX_Z'] * 0.15)   # proxy de emergencia

# ── Liquidez: Amihud Ratio (Sección 8) ───────────────────────────────
# Amihud = |Daily Return| / Daily $ Volume  (rolling 21D mean)
try:
    spy_close  = spy_ohlcv['Close'].squeeze()
    spy_volume = spy_ohlcv['Volume'].squeeze()
    spy_ret    = spy_close.pct_change().abs()
    spy_dolvol = spy_close * spy_volume                     # $ volume
    amihud_daily = spy_ret / (spy_dolvol / 1e9)            # escalar a USD bn
    amihud_daily = amihud_daily.replace([np.inf, -np.inf], np.nan)
    amihud_roll  = amihud_daily.rolling(21).mean()

    # Volumen relativo a media 20D
    vol_rel = spy_volume / spy_volume.rolling(20).mean()
    HAS_LIQ = True
except Exception as e:
    print(f"No se pudo calcular liquidez: {e}")
    HAS_LIQ = False

# ── Scorecard (para Sección 0) ────────────────────────────────────────
def get_signal(series, upper_bad, lower_bad, higher_is_bad=True):
    """Devuelve 'RED', 'YELLOW' o 'GREEN' según el valor más reciente."""
    val = series.dropna().iloc[-1]
    if higher_is_bad:
        if val > upper_bad:   return 'RED',    f"{val:.2f}"
        elif val > lower_bad: return 'YELLOW', f"{val:.2f}"
        else:                 return 'GREEN',  f"{val:.2f}"
    else:
        if val < upper_bad:   return 'RED',    f"{val:.2f}"
        elif val < lower_bad: return 'YELLOW', f"{val:.2f}"
        else:                 return 'GREEN',  f"{val:.2f}"

sc_momentum_color, sc_momentum_val = get_signal(data['RSI'], 70, 55, higher_is_bad=True)
sc_vix_color,      sc_vix_val      = get_signal(data['^VIX'], 25, 18, higher_is_bad=True)
sc_credit_color,   sc_credit_val   = ('GREEN', 'N/A') if data['Credit_Proxy'].isna().all() else \
                                      get_signal(data['Credit_Proxy'].dropna(), 0.0, 0.0)
sc_curve_color,    sc_curve_val    = get_signal(data['Spread_10Y3M'], 0, -0.3, higher_is_bad=False)
sc_inflation_color,sc_inflation_val= get_signal(data['Inflation_Proxy'], 1.165, 1.155, higher_is_bad=True)
sc_global_color,   sc_global_val   = get_signal(global_norm['EEM'], 100, 95, higher_is_bad=False) \
                                      if 'EEM' in global_norm.columns else ('YELLOW', 'N/A')

SCORECARD_COLOR_MAP = {
    'RED':    colors.HexColor('#DA291C'),
    'YELLOW': colors.HexColor('#F5A623'),
    'GREEN':  colors.HexColor('#1E7E34'),
}

scorecard_rows = [
    ['Dimensión',        'Señal',     'Valor',          'Interpretación'],
    ['Momentum (RSI)',   sc_momentum_color, sc_momentum_val, 'RSI 14D del S&P500. >70 = sobrecompra.'],
    ['Volatilidad (VIX)',sc_vix_color,      sc_vix_val,      'VIX spot. <18 = complacencia, >25 = stress.'],
    ['Crédito (HYG/IEF)',sc_credit_color,   sc_credit_val,   'Proxy de spreads. Caída = ampliación de spreads.'],
    ['Curva (10Y-3M)',   sc_curve_color,    sc_curve_val,    'Spread negativo persiste = señal recesiva activa.'],
    ['Inflación (TIP/IEF)',sc_inflation_color,sc_inflation_val,'Ratio al alza = expectativas de inflación real crecientes.'],
    ['Global (EEM base 100)',sc_global_color,sc_global_val,  'Performance relativa EM. <95 = risk-off en emergentes.'],
]

# ══════════════════════════════════════════════════════════════════════
# 4. MOTOR GRÁFICO
# ══════════════════════════════════════════════════════════════════════
print("Generando Gráficos V2...")

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'axes.grid':            False,
    'axes.spines.top':      False,
    'axes.spines.right':    False,
    'axes.spines.left':     False,
    'axes.spines.bottom':   True,
    'font.family':          'sans-serif',
})

CB = '#002D72'   # Azul corporativo
CR = '#DA291C'   # Rojo alerta
CG = '#1E7E34'   # Verde
CY = '#F5A623'   # Amarillo
date_fmt = mdates.DateFormatter('%m-%Y')

def get_img():
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=130, bbox_inches='tight')
    buf.seek(0); plt.close()
    return buf

def style_ax(ax, rotate=0):
    ax.xaxis.set_major_formatter(date_fmt)
    ax.tick_params(axis='x', rotation=rotate, labelsize=6)
    ax.legend(frameon=False, loc='upper left', fontsize=6)

# ── Fig 1: Macro (SPY vs VIX) ─────────────────────────────────────────
fig, ax1 = plt.subplots(figsize=(9, 3.5))
ax1.plot(data.index[-252:], data['SPY'].tail(252), color=CB, lw=2, label='S&P 500')
ax1.set_ylabel('S&P 500', color=CB, fontweight='bold', fontsize=8)
ax2 = ax1.twinx()
ax2.fill_between(data.index[-252:], data['^VIX'].tail(252), color='grey', alpha=0.3, label='VIX')
ax2.axis('off')
style_ax(ax1)
img_macro = get_img()

# ── Fig 2: VIX Z-Score ────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 3.0))
z = data['VIX_Z'].tail(252)
ax.plot(z.index, z, color=CB, lw=1.5, label='Z-Score')
ax.fill_between(z.index, z, 2,  where=(z > 2),  color=CR,    alpha=0.3)
ax.fill_between(z.index, z, -2, where=(z < -2), color='green', alpha=0.3)
ax.axhline(2,  color=CR,    ls='--', lw=0.8)
ax.axhline(-2, color='green', ls='--', lw=0.8)
style_ax(ax)
img_vix_z = get_img()

# ── Fig 3: Alpha Cone + RSI ───────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6),
                                gridspec_kw={'height_ratios': [3, 1]})
hist_days = 180
ax1.plot(data.index[-hist_days:], data['SPY'].tail(hist_days), color=CB, lw=2, label='History')
ax1.plot(future_dates, upper_1std, color='grey', alpha=0.5, ls='--')
ax1.plot(future_dates, lower_1std, color='grey', alpha=0.5, ls='--')
ax1.fill_between(future_dates, upper_1std, lower_1std, color=CB,   alpha=0.1, label='1σ (68%)')
ax1.fill_between(future_dates, upper_2std, lower_2std, color=CB,   alpha=0.05, label='2σ (95%)')
style_ax(ax1)
ax2.plot(data.index[-hist_days:], data['RSI'].tail(hist_days), color='mediumorchid', lw=1.5, label='RSI (14 days)')
ax2.axhline(70, color=CR,    ls=':', lw=1)
ax2.axhline(30, color='green', ls=':', lw=1)
ax2.fill_between(data.index[-hist_days:], 70, 100, color=CR, alpha=0.1)
ax2.set_ylim(0, 100)
style_ax(ax2)
img_alpha = get_img()

# ── Fig 4: Yield Curve Structure ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 4))
terms = ['3M', '5Y', '10Y', '30Y']
tv    = list(TICKERS_CURVE.values())
ax.plot(terms, data[tv].iloc[-1],   'o-',  color=CB,    lw=2,   label='Hoy')
ax.plot(terms, data[tv].iloc[-63],  '^:',  color='#0073CF', lw=1.5, label='Hace 1 Mes')
ax.plot(terms, data[tv].iloc[-252], '^:',  color='grey', lw=1.5, label='Hace 1 Año')
ax.legend(frameon=False, loc='upper left', fontsize=8)
img_curve = get_img()

# ── Fig 5: Recession Signals ──────────────────────────────────────────
data_24 = data.loc['2024-01-01':]
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 8))
ax1.plot(data_24.index, data_24['Spread_10Y3M'], color=CB, label='10Y-3M Spread')
ax1.fill_between(data_24.index, data_24['Spread_10Y3M'], 0,
                 where=data_24['Spread_10Y3M'] < 0, color=CR, alpha=0.3)
ax1.axhline(0, color='black', lw=1)
style_ax(ax1)
ax2.plot(data_24.index, data_24['Inflation_Proxy'], color='firebrick', lw=1, label='TIP/IEF Ratio')
style_ax(ax2)
img_recession = get_img()

# ── Fig 6: Correlation Rolling ────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 3.5))
rc = roll_corr.tail(300)
ax.plot(rc.index, rc, color=CB, lw=1., label='60D Correlation')
ax.fill_between(rc.index, rc, 0, where=(rc > 0), color=CR,    alpha=0.2, label='Peligro (Corr+)')
ax.fill_between(rc.index, rc, 0, where=(rc < 0), color='green', alpha=0.2, label='Seguro (Corr-)')
ax.axhline(0, color='black', lw=1)
style_ax(ax)
img_corr = get_img()

# ── Fig 7: Correlation Heatmap ────────────────────────────────────────
TICKERS_RISK = ['SPY', 'TLT', 'IEF', 'SHY', 'TIP', 'DX-Y.NYB', '^VIX']
fig, ax = plt.subplots(figsize=(8, 5))
heat_data = rets[[t for t in TICKERS_RISK if t in rets.columns]].tail(90).corr()
sns.heatmap(heat_data, annot=True, fmt='.2f', cmap='RdBu', center=0, cbar=False, ax=ax)
img_heatmap = get_img()

# ── Fig 8: Drawdowns ──────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 3.5))
ax.plot(dd_spy.index[-300:], dd_spy.tail(300) * 100, color=CB, label='S&P 500')
ax.plot(dd_tlt.index[-300:], dd_tlt.tail(300) * 100, color=CR, label='Treasuries')
ax.fill_between(dd_spy.index[-300:], dd_spy.tail(300) * 100, 0, color=CB, alpha=0.1)
style_ax(ax)
img_dd = get_img()

# ── Fig 9: Stress Test ────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(4.0, 3.5))
snames = list(stress_impact.keys())
svals  = list(stress_impact.values())
scols  = ['firebrick' if x < 0 else 'green' for x in svals]
ax.barh(snames, svals, color=scols)
ax.axvline(0, color='black')
for i, v in enumerate(svals):
    ax.text(v, i, f" ${v:,.0f}", va='center', fontweight='bold', fontsize=9)
img_stress = get_img()

# ── Fig 10: Global Performance (Normalizado) ─────────────────────────
GLOBAL_COLORS = {
    'SPY': CB, 'EEM': CR, 'EWG': CG, 'EWJ': '#8E44AD', 'FXI': CY,
}
fig, ax = plt.subplots(figsize=(9, 4))
for ticker in global_norm.columns:
    c = GLOBAL_COLORS.get(ticker, 'grey')
    ax.plot(global_norm.index, global_norm[ticker], lw=1.8, color=c, label=ticker)
ax.axhline(100, color='black', lw=0.8, ls='--')
ax.set_ylabel('Índice (Base 100)', fontsize=8)
style_ax(ax)
img_global = get_img()

# ── Fig 11: Credit Spread Proxy ───────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 3.5))
if not data['Credit_Proxy'].isna().all():
    cp = data['Credit_Proxy'].dropna().tail(300)
    ma = cp.rolling(20).mean()
    ax.plot(cp.index, cp, color=CB, lw=1.2, alpha=0.7, label='HYG/IEF Ratio')
    ax.plot(ma.index, ma, color=CR, lw=1.8, ls='--', label='MA 20D')
    ax.fill_between(cp.index, cp, ma, where=(cp < ma), color=CR, alpha=0.15)
else:
    ax.text(0.5, 0.5, 'HYG o IEF no disponibles', transform=ax.transAxes,
            ha='center', va='center', fontsize=12, color='grey')
style_ax(ax)
img_credit = get_img()

# ── Fig 12: Advanced Curve (Spreads 2Y-10Y y 10Y-3M) ─────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=False)
dc = data_curve.tail(500)
ax1.plot(dc.index, dc['Spread_2Y10Y'], color=CB, lw=1.5, label='Spread 2Y-10Y')
ax1.fill_between(dc.index, dc['Spread_2Y10Y'], 0,
                 where=(dc['Spread_2Y10Y'] < 0), color=CR, alpha=0.25)
ax1.axhline(0, color='black', lw=0.8)
style_ax(ax1)

sp_10y3m = data['Spread_10Y3M'].tail(500)
ax2.plot(sp_10y3m.index, sp_10y3m, color='#8E44AD', lw=1.5, label='Spread 10Y-3M')
ax2.fill_between(sp_10y3m.index, sp_10y3m, 0,
                 where=(sp_10y3m < 0), color='#8E44AD', alpha=0.2)
ax2.axhline(0, color='black', lw=0.8)
style_ax(ax2)
img_adv_curve = get_img()

# ── Fig 13: Real Rates Proxy ──────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 3.5))
rr = real_rate_proxy.dropna().tail(400)
ax.plot(rr.index, rr, color=CB, lw=1.5, label='Real Rate Proxy (10Y - Inflation Component)')
ax.fill_between(rr.index, rr, 0, where=(rr > 0), color=CR, alpha=0.15, label='Positivo (restrictivo)')
ax.fill_between(rr.index, rr, 0, where=(rr < 0), color=CG,  alpha=0.15, label='Negativo (acomodaticio)')
ax.axhline(0, color='black', lw=0.8)
style_ax(ax)
img_real_rates = get_img()

# ── Fig 14: Amihud Illiquidity ────────────────────────────────────────
if HAS_LIQ:
    fig, ax = plt.subplots(figsize=(9, 3.5))
    am_plot  = amihud_roll.tail(300)
    am_mean  = am_plot.mean()
    am_2std  = am_mean + 2 * am_plot.std()
    ax.plot(am_plot.index, am_plot, color=CB, lw=1.2, label='Amihud (21D rolling)')
    ax.axhline(am_mean, color='grey', ls='--', lw=0.8, label='Media')
    ax.axhline(am_2std, color=CR,    ls='--', lw=1.0, label='+2 Desv. Std.')
    ax.fill_between(am_plot.index, am_plot, am_2std,
                    where=(am_plot > am_2std), color=CR, alpha=0.2)
    style_ax(ax)
    img_amihud = get_img()
else:
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.text(0.5, 0.5, 'Datos OHLCV no disponibles para Amihud',
            transform=ax.transAxes, ha='center', va='center', fontsize=11)
    img_amihud = get_img()

# ── Fig 15: Relative Volume ───────────────────────────────────────────
if HAS_LIQ:
    fig, ax = plt.subplots(figsize=(9, 3.5))
    vr_plot = vol_rel.tail(120)
    colors_vr = [CR if v > 1.5 else CB for v in vr_plot.values]
    ax.bar(vr_plot.index, vr_plot.values, color=colors_vr, width=1.0)
    ax.axhline(1.0, color='black', lw=0.8, ls='--')
    ax.axhline(1.5, color=CR,    lw=0.8, ls='--', label='1.5x Media (alta convicción)')
    ax.set_ylabel('Vol / 20D Avg', fontsize=8)
    ax.legend(frameon=False, fontsize=6)
    ax.tick_params(axis='x', rotation=30, labelsize=6)
    img_volume = get_img()
else:
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.text(0.5, 0.5, 'Datos de volumen no disponibles',
            transform=ax.transAxes, ha='center', va='center', fontsize=11)
    img_volume = get_img()

# ══════════════════════════════════════════════════════════════════════
# 5. MOTOR PDF
# ══════════════════════════════════════════════════════════════════════
print("Maquetando PDF V2...")

doc = SimpleDocTemplate(
    "Market_Intelligence_Monitor_V2.pdf",
    pagesize=A4,
    topMargin=20, bottomMargin=20, leftMargin=40, rightMargin=40
)
styles = getSampleStyleSheet()

# ── Estilos personalizados ────────────────────────────────────────────
s_Title     = ParagraphStyle('T',  parent=styles['Heading1'],  fontSize=24,
                              textColor=colors.HexColor(CB))
s_Head      = ParagraphStyle('H',  parent=styles['Heading2'],  fontSize=15,
                              textColor=colors.white,
                              backColor=colors.HexColor(CB),
                              borderPadding=8, spaceBefore=10, spaceAfter=10)
s_SubHead   = ParagraphStyle('SH', parent=styles['Heading3'],  fontSize=11,
                              textColor=colors.HexColor(CB),   spaceBefore=6)
s_Body      = ParagraphStyle('B',  parent=styles['Normal'],    fontSize=10,
                              leading=14, alignment=TA_JUSTIFY)
s_Caption   = ParagraphStyle('C',  parent=styles['Normal'],    fontSize=9,
                              textColor=colors.grey,
                              alignment=TA_CENTER, spaceAfter=10)
s_ChartTitle= ParagraphStyle('CT', parent=styles['Heading3'],  fontSize=11,
                              textColor=colors.HexColor(CB),
                              alignment=TA_LEFT, spaceAfter=2)
s_Small     = ParagraphStyle('S',  parent=styles['Normal'],    fontSize=8,
                              textColor=colors.grey, alignment=TA_CENTER)
s_Bullet    = ParagraphStyle('BU', parent=s_Body, leftIndent=20,
                              bulletText='•', spaceAfter=5)

story = []

# ══════════════════════════════════════════════════════════════════════
# PORTADA / HEADER
# ══════════════════════════════════════════════════════════════════════
story.append(Paragraph("MARKETS REPORT | CROSS-ASSET STRATEGY", styles['Normal']))
story.append(Paragraph("Market Intelligence Monitor", s_Title))
story.append(Paragraph(
    f"Date: {datetime.now().strftime('%d %B %Y')} | "
    "Autor: Carlos Caballero (//www.linkedin.com/in/caballerohh/)",
    styles['Normal']
))
story.append(Spacer(1, 15))

# ══════════════════════════════════════════════════════════════════════
# SECCIÓN 0: RISK SCORECARD (Semáforo)
# ══════════════════════════════════════════════════════════════════════
story.append(Paragraph("Risk Intelligence Scorecard", s_Head))
story.append(Paragraph(
    "Resumen ejecutivo de señales por dimensión analítica. "
    "<b>VERDE</b> = condición favorable | <b>AMARILLO</b> = cautela | "
    "<b>ROJO</b> = alerta activa.",
    s_Body
))
story.append(Spacer(1, 8))

# Construir tabla de scorecard
sc_table_data = [scorecard_rows[0]]  # header
for row in scorecard_rows[1:]:
    dim, color_key, val, interp = row
    sc_table_data.append([
        Paragraph(f"<b>{dim}</b>", s_Body),
        Paragraph(f"<b>●</b>", ParagraphStyle('sig', parent=s_Body,
                  textColor=SCORECARD_COLOR_MAP[color_key], alignment=TA_CENTER)),
        Paragraph(val, s_Body),
        Paragraph(interp, ParagraphStyle('i', parent=s_Body, fontSize=9))
    ])

sc_t = Table(
    [[ Paragraph(h, ParagraphStyle('sh', parent=s_Body, textColor=colors.white, fontName='Helvetica-Bold'))
       for h in scorecard_rows[0] ]] + sc_table_data[1:],
    colWidths=['28%', '10%', '14%', '48%']
)
sc_t.setStyle(TableStyle([
    ('BACKGROUND',  (0, 0), (-1, 0), colors.HexColor(CB)),
    ('TEXTCOLOR',   (0, 0), (-1, 0), colors.white),
    ('GRID',        (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F8FF')]),
    ('LEFTPADDING',  (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ('TOPPADDING',   (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
]))
story.append(sc_t)
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════
# SECCIÓN 1: MACRO OVERVIEW
# ══════════════════════════════════════════════════════════════════════
story.append(Paragraph("1. Macro Overview & Regime Analysis", s_Head))
story.append(Paragraph(ANALYSIS["MACRO_HEADER"], s_Body))
story.append(Spacer(1, 5))

# Tabla de métricas
data_table = [['Ticker', 'Last', '1M %', '3M %', '6M %', '1Y %']]
for idx, row in metrics_df.iterrows():
    vals_row = [idx, f"{row['Last']:.2f}"]
    for col in ['1M %', '3M %', '6M %', '1Y %']:
        v = row[col] * 100
        vals_row.append(f"{v:.2f}%")
    data_table.append(vals_row)

t = Table(data_table, colWidths=['16%'] * 6)
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0E0E0')),
    ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
    ('ALIGN',      (1, 0), (-1, -1), 'CENTER'),
    ('FONTSIZE',   (0, 0), (-1, -1), 9),
]))
story.append(t)
story.append(Spacer(1, 10))
story.append(Paragraph(ANALYSIS["MACRO_BODY"], s_Body))
story.append(Spacer(1, 5))
story.append(Paragraph("Macro Regime: Equity Trend vs Volatility Stress", s_ChartTitle))
story.append(Image(img_macro, width=480, height=200))
story.append(Paragraph(ANALYSIS["CAPTION_MACRO"], s_Caption))
story.append(Paragraph("VIX Relative Value (Z-Score)", s_ChartTitle))
story.append(Image(img_vix_z, width=480, height=180))
story.append(Paragraph(ANALYSIS["CAPTION_VIX"], s_Caption))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════
# SECCIÓN 2: TACTICAL ALPHA
# ══════════════════════════════════════════════════════════════════════
story.append(Paragraph("2. Tactical Alpha Dashboard", s_Head))
story.append(Paragraph(ANALYSIS["ALPHA_BODY"], s_Body))
story.append(Spacer(1, 10))
story.append(Paragraph("Predictive Alpha: Implied Cone & RSI", s_ChartTitle))
story.append(Image(img_alpha, width=480, height=350))
story.append(Paragraph(ANALYSIS["CAPTION_CONE"], s_Caption))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════
# SECCIÓN 3: RATES STRUCTURE
# ══════════════════════════════════════════════════════════════════════
story.append(Paragraph("3. Rates Structure & Recession Watch", s_Head))
story.append(Paragraph(ANALYSIS["RATES_BODY"], s_Body))
story.append(Spacer(1, 10))
story.append(Paragraph("US Treasury Yield Curve Structure", s_ChartTitle))
story.append(Image(img_curve, width=480, height=220))
story.append(Paragraph(ANALYSIS["CAPTION_CURVE"], s_Caption))
story.append(Paragraph("Recession Signals (Spread 10Y-3M & Inflation)", s_ChartTitle))
story.append(Image(img_recession, width=480, height=250))
story.append(Paragraph(ANALYSIS["CAPTION_RECESSION"], s_Caption))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════
# SECCIÓN 4: RISK & CORRELATION
# ══════════════════════════════════════════════════════════════════════
story.append(Paragraph("4. Risk & Correlation", s_Head))
story.append(Paragraph(ANALYSIS["RISK_BODY"], s_Body))
story.append(Spacer(1, 10))
story.append(Paragraph("Diversification Health: Correlations", s_ChartTitle))
story.append(Image(img_corr, width=480, height=200))
story.append(Paragraph(ANALYSIS["CAPTION_CORR"], s_Caption))
story.append(Spacer(1, 10))
story.append(Paragraph("Cross-Asset Correlation Matrix", s_ChartTitle))
story.append(Image(img_heatmap, width=480, height=280))
story.append(Paragraph(ANALYSIS["CAPTION_HEATMAP"], s_Caption))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════
# SECCIÓN 5: PORTFOLIO FRAGILITY
# ══════════════════════════════════════════════════════════════════════
story.append(Paragraph("5. Portfolio Fragility & Stress Test", s_Head))
story.append(Paragraph(ANALYSIS["PORTFOLIO_BODY"], s_Body))
story.append(Spacer(1, 10))
story.append(Paragraph("Portfolio Fragility: Historical Drawdowns", s_ChartTitle))
story.append(Image(img_dd, width=480, height=200))
story.append(Paragraph(ANALYSIS["CAPTION_DD"], s_Caption))
story.append(Spacer(1, 15))
story.append(Paragraph("Portfolio Stress: Test Impact (USD $)", s_ChartTitle))
story.append(Paragraph(
    "Bajo escenarios de cola (Twists de curva): 1) Un choque de inflación es el escenario más "
    "devastador, 2) el aumento paralelo de +50bps impactaría en -$660,500 y "
    "3) las tasas cortas subiendo más que las largas generan impacto de -$140,000.",
    s_Body
))
story.append(Image(img_stress, width=300, height=200))
story.append(Paragraph(ANALYSIS["CAPTION_STRESS"], s_Caption))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════
# SECCIÓN 6: GLOBAL MACRO & CREDIT (NUEVA)
# ══════════════════════════════════════════════════════════════════════
story.append(Paragraph("6. Global Macro & Credit Spreads", s_Head))
story.append(Paragraph(ANALYSIS["GLOBAL_BODY"], s_Body))
story.append(Spacer(1, 10))
story.append(Paragraph("Global Equity Performance — Normalized (Base 100, 1Y)", s_ChartTitle))
story.append(Image(img_global, width=480, height=230))
story.append(Paragraph(ANALYSIS["CAPTION_GLOBAL"], s_Caption))
story.append(Spacer(1, 8))
story.append(Paragraph("Credit Stress Proxy — HYG / IEF Ratio", s_ChartTitle))
story.append(Image(img_credit, width=480, height=210))
story.append(Paragraph(ANALYSIS["CAPTION_CREDIT"], s_Caption))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════
# SECCIÓN 7: ADVANCED CURVE ANALYSIS (NUEVA)
# ══════════════════════════════════════════════════════════════════════
story.append(Paragraph("7. Advanced Yield Curve Analysis", s_Head))
story.append(Paragraph(ANALYSIS["ADVANCED_CURVE_BODY"], s_Body))
story.append(Spacer(1, 10))
story.append(Paragraph(
    "Dual Spread Monitor: 2Y-10Y (FRED) vs 10Y-3M (Yahoo Finance)",
    s_ChartTitle
))
story.append(Image(img_adv_curve, width=480, height=270))
story.append(Paragraph(ANALYSIS["CAPTION_ADV_CURVE"], s_Caption))
story.append(Spacer(1, 8))
story.append(Paragraph("Real Rates Proxy — 10Y Nominal minus Inflation Component", s_ChartTitle))
story.append(Image(img_real_rates, width=480, height=210))
story.append(Paragraph(ANALYSIS["CAPTION_REAL_RATES"], s_Caption))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════
# SECCIÓN 8: MARKET LIQUIDITY (NUEVA)
# ══════════════════════════════════════════════════════════════════════
story.append(Paragraph("8. Market Liquidity Monitor", s_Head))
story.append(Paragraph(ANALYSIS["LIQUIDITY_BODY"], s_Body))
story.append(Spacer(1, 10))
story.append(Paragraph("Amihud Illiquidity Ratio — SPY (Rolling 21D)", s_ChartTitle))
story.append(Image(img_amihud, width=480, height=210))
story.append(Paragraph(ANALYSIS["CAPTION_AMIHUD"], s_Caption))
story.append(Spacer(1, 8))
story.append(Paragraph("Relative Volume — SPY vs 20D Average (Last 6 Months)", s_ChartTitle))
story.append(Image(img_volume, width=480, height=210))
story.append(Paragraph(ANALYSIS["CAPTION_VOLUME"], s_Caption))
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════
# SECCIÓN 9: SCENARIO ANALYSIS (NUEVA)
# ══════════════════════════════════════════════════════════════════════
story.append(Paragraph("9. Scenario Analysis — Bull / Base / Bear", s_Head))
story.append(Paragraph(ANALYSIS["SCENARIO_BODY"], s_Body))
story.append(Spacer(1, 12))

# Construir tabla de escenarios
sc_data_pdf = []
header_row = [
    Paragraph(h, ParagraphStyle('sch', parent=s_Body,
              textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER))
    for h in SCENARIOS_DATA['headers']
]
sc_data_pdf.append(header_row)

SCENARIO_BG = {0: colors.white, 1: colors.HexColor('#F5F8FF')}
for i, row in enumerate(SCENARIOS_DATA['rows']):
    sc_data_pdf.append([
        Paragraph(f"<b>{row[0]}</b>",
                  ParagraphStyle('sd0', parent=s_Body, fontSize=9)),
        Paragraph(row[1],
                  ParagraphStyle('sd1', parent=s_Body, fontSize=9,
                                 textColor=colors.HexColor(CR))),
        Paragraph(row[2],
                  ParagraphStyle('sd2', parent=s_Body, fontSize=9,
                                 textColor=colors.HexColor(CB))),
        Paragraph(row[3],
                  ParagraphStyle('sd3', parent=s_Body, fontSize=9,
                                 textColor=colors.HexColor(CG))),
    ])

sc_table = Table(sc_data_pdf, colWidths=['22%', '26%', '26%', '26%'])
sc_table.setStyle(TableStyle([
    ('BACKGROUND',      (0, 0), (-1, 0), colors.HexColor(CB)),
    ('BACKGROUND',      (1, 1), (1, -1), colors.HexColor('#FFF0EE')),
    ('BACKGROUND',      (2, 1), (2, -1), colors.HexColor('#EEF4FF')),
    ('BACKGROUND',      (3, 1), (3, -1), colors.HexColor('#EEFFF2')),
    ('GRID',            (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ('VALIGN',          (0, 0), (-1, -1), 'TOP'),
    ('LEFTPADDING',     (0, 0), (-1, -1), 6),
    ('RIGHTPADDING',    (0, 0), (-1, -1), 6),
    ('TOPPADDING',      (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING',   (0, 0), (-1, -1), 5),
    ('ROWBACKGROUNDS',  (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
]))
story.append(sc_table)
story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════
# SECCIÓN 10: EXECUTIVE SUMMARY & EVENTS
# ══════════════════════════════════════════════════════════════════════
story.append(Paragraph("10. Executive Summary & Events", s_Head))
story.append(Paragraph("MARKET MONITORING IMPLICATIONS (Non-Advisory):", styles['Heading3']))
for line in ANALYSIS['TAKEAWAYS'].split('\n'):
    if line.strip():
        story.append(Paragraph(
            line.strip(),
            ParagraphStyle('bu', parent=s_Body, leftIndent=20,
                           bulletText='•', spaceAfter=5)
        ))
story.append(Spacer(1, 20))
story.append(Paragraph("UPCOMING EVENTS (NEXT 14 DAYS):", styles['Heading3']))
t_ev = Table(UPCOMING_EVENTS, colWidths=['13%', '13%', '37%', '37%'])
t_ev.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(CB)),
    ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
    ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
    ('FONTSIZE',   (0, 0), (-1, -1), 9),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F8FF')]),
]))
story.append(t_ev)

# ══════════════════════════════════════════════════════════════════════
# BUILD
# ══════════════════════════════════════════════════════════════════════
doc.build(story)
print("\n✅  REPORTE GENERADO: Market_Intelligence_Monitor_V2.pdf")
print(f"    Páginas aprox: 10 | Secciones: 10 | Activos monitoreados: {len(ALL_YF)}")
