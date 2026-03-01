# 📈 Market Intelligence Monitor V2: Macro & Risk Engine

Este ecosistema de **Inteligencia de Mercados** automatiza la extracción, procesamiento y visualización de datos cross-asset para generar reportes de alta fidelidad de 11 páginas. La versión 2.0 introduce modelos de **liquidez de mercado**, **análisis avanzado de la curva de tipos** y un framework de **probabilidad de escenarios** (Bull/Base/Bear).

> **🎯 Propósito:** Transformar el ruido del mercado en señales accionables mediante el análisis de regímenes macro, estrés de portafolio y volatilidad implícita.

---

## 🔬 Innovaciones Técnicas (V2 vs V1)

A diferencia de la versión inicial, este motor integra métricas de grado institucional para una visión técnica profunda:

* **Market Liquidity Monitor:** Implementación del **Ratio de Iliquidez de Amihud** (rolling 21D) para detectar deterioros en la profundidad del mercado antes de picos de volatilidad.
* **Advanced Yield Curve Analysis:** Monitoreo dual de spreads (2Y-10Y vs 10Y-3M) y cálculo de **Tasas Reales ex-ante** para identificar señales recesivas y compresión de primas de riesgo.
* **Scenario Analytics Framework:** Modelo cuantitativo que asigna probabilidades a escenarios macro, definiendo niveles de invalidación técnica y objetivos de precio para el S&P 500.
* **Tactical Alpha Dashboard:** Proyección de rangos de movimiento (1σ y 2σ) mediante **Implied Cones** basados en la volatilidad diaria derivada del VIX.

---

## 📊 Dimensiones Analíticas del Reporte

El sistema procesa y genera automáticamente las siguientes secciones estratégicas:

1.  **Risk Intelligence Scorecard:** Resumen ejecutivo con semáforo de señales (Momentum, Volatilidad, Crédito, Curva, Inflación).
2.  **Macro Overview & Regime:** Análisis de expansión de múltiplos y monitoreo de la divergencia entre el S&P 500 y el VIX.
3.  **Portfolio Fragility & Stress Test:** Cuantificación del impacto en el P&L (USD) ante choques de inflación, caídas de equity o aumentos paralelos en las tasas.
4.  **Correlation Health:** Matriz de correlación cross-asset de 90 días y seguimiento de la ruptura de diversificación SPY/TLT.

---

## 🛠️ Stack Tecnológico y Lógica de Datos

* **Data Engine:** Ingesta híbrida desde **Yahoo Finance** y **FRED** con limpieza de series temporales y normalización base 100.
* **Quantitative Logic:**
    * Cálculo de **Z-Scores** de volatilidad para identificar puntos de pánico o complacencia excesiva.
    * Modelado de **Drawdowns históricos** comparativos entre Renta Variable y Renta Fija.
* **Reporting Layer (ReportLab):** Maquetación profesional en PDF con estilos corporativos, tablas dinámicas de eventos económicos (CPI, NFP, FOMC) y renderizado automático de gráficos técnicos.

---

## 🚀 Insights Extraídos (Caso de Estudio: Feb-2026)

* **Regimen:** Identificación de una fase de "expansión de múltiplos" con un VIX en niveles históricamente bajos, sugiriendo complacencia ante riesgos de cola.
* **Alerta de Correlación:** La correlación SPY/TLT rompió al alza (+0.45), eliminando el beneficio de la diversificación convencional.
* **Impacto de Escenarios:** Un choque de inflación se identifica como el riesgo más devastador, con una pérdida estimada de **-$700,000** en el portafolio modelo.

---

## ⚙️ Instalación y Requisitos

```bash
# Clonar el repositorio
git clone [https://github.com/caballerohh/market-intelligence-monitor.git](https://github.com/caballerohh/market-intelligence-monitor.git)

# Instalar dependencias necesarias
pip install yfinance pandas numpy matplotlib seaborn reportlab pandas_datareader
