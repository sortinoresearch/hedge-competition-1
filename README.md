![Sortino Capital Main Image](competition/imgs/main.png)

# Sortino Capital Sector Alpha Hedging Challenge

Sortino Capital delivers quantitative financial research and intelligence on a global scale to individual private capital, wealth managers, and family offices. 

This competition challenges quantitative engineers to develop an institutional-grade, sector-neutral systematic strategy. Rather than rewarding unhedged leverage, factor betting, or parameter curve-fitting, this framework enforces strict capital velocity, risk limits, and structural generalization across an entirely unseen economic sector.

You can join our newsletter at https://sortino.capital/

---

### Competition Format & Eligibility
The competition is structured in two stages:
1. **Code Submission:** Participants submit their strategy through the required repository-based submission process described below.
2. **Finalist Presentation:** The top 2 candidates will be invited to present their approach virtually in a live session.

**Eligibility & Team Requirements:**
* **Geographic Focus:** This competition currently covers Panama only. 
* **Team Size:** Participants may compete individually or in teams of up to 2 members.
* **Residency:** At least one team member **must reside in Panama**. This is a strict requirement to facilitate the transfer of prize funds to the winning team.

*Disclaimer: The model in this repository is only a sample workflow and includes important simplifications that materially affect the results, especially with respect to transaction costs and other modeling assumptions.*

---

### 1. Core Objective & Architecture
Candidates must develop a single, regime-agnostic Python strategy class. The class must dynamically accept any arbitrary sector ETF along with its underlying stock universe, initialize capital configurations on the fly, and execute intra-sector long/short hedging portfolios.

The baseline model provided in this repository utilizes a multi-factor rolling Ordinary Least Squares (OLS) regression matrix to isolate sector beta. Your objective is to optimize this framework, or engineer a superior asset-pricing pipeline, to maximize downstream risk-adjusted performance. Your model will be developed on three historical training sectors and deployed blindly by our validation engine to a **completely hidden, out-of-sample sector** over a 10-year historical testing window.

---

### 2. Sector Universe & Data Parameters
Historical data is programmatically fetched via `yfinance` spanning a **10-year historical horizon** at a **Daily frequency (`interval="1d"`)**.

⚠️ **Critical Infrastructure Rule:** To account for corporate actions, split events, and heavy dividend yield payouts across banking and energy sectors, your portfolio simulation and signal generation **must** calculate Net Asset Value (NAV) using the **`Adj Close`** pricing matrix.

| Target Industry Block | Eligible Equity Universe (Long-Only Candidates) | Mandatory Benchmark ETF (Short Vehicle) |
| :--- | :--- | :--- |
| **Technology / Semiconductor** | NVDA, AMD, INTC, AVGO, QCOM, TSM, ASML, MU | SOXX (iShares Semiconductor ETF) |
| **Financial / Banking** | JPM, BAC, MS, GS, C, WFC, PNC, USB | XLF (Financial Select Sector SPDR) |
| **Energy / Infrastructure** | XOM, CVX, COP, SLB, EOG, MPC, VLO, DVN | XLE (Energy Select Sector SPDR) |
| **Healthcare / Biotech (OOS Blind)** | LLY, UNH, JNJ, ABBV, MRK, AMGN, PFE, BMY | XLV (Health Care Select Sector SPDR) |

---

### 3. Structural Portfolio Mandates & Guardrails
These rules are continuous structural constraints evaluated on daily bars. Breaches at any single row index checkpoint will trigger automated validation failure and immediate strategy disqualification.

*   **Revolving Capital Minimum (Active Deployment):** Your portfolio must maintain a minimum average Gross Exposure ($\frac{\text{Long Exposure} + |\text{Short Exposure}|}{\text{NAV}}$) at or above **50% of NAV** across the full evaluation timeline. Strategies cannot retreat to cash to lock in or freeze a lucky yield spike.
*   **The No-Idling Position Rule:** To prevent placing microscopic "token" trades to manipulate transaction metrics, any newly initialized stock/ETF pair basket must allocate a **minimum of 5% and a maximum of 25% of current NAV** at the exact timestamp of entry.
*   **Minimum Holding Window:** Once a stock/ETF pair structure is initialized, both positions are locked and cannot be modified or liquidated until **day T+5** (5 consecutive trading days later).
*   **Forced Terminal Settlement:** Your script must completely purge its order books and flatten all open asset inventories back to cash (USD) on the final day bar of the competition window. **Zero open exposure or trailing inventory is allowed at terminal close.**
*   **Leverage Ceiling:** Absolute gross portfolio leverage may **never exceed 20:1** on any daily checkpoint.

---

### 4. Evaluation Framework & Multi-Objective Scoring
The evaluation suite runs your unaltered script across the data environments to calculate daily log returns ($r_t = \ln(\text{NAV}_t / \text{NAV}_{t-1})$), inclusive of execution friction, short borrow costs, and position slippage penalties. Your **Global Performance Score ($S_G$)** is compiled via three core pillars:

$$S_G = 0.50 \cdot S_R + 0.30 \cdot S_{Gen} + 0.20 \cdot S_E$$

**Pillar 1: Asymmetric Risk-Adjusted Return (50% Weight)**
Rewards strategies that optimize the annualized Sortino Ratio while minimizing Maximum Drawdown (MDD) across all sectors combined. The Minimum Acceptable Return (MAR) is standardized to 0.
* $S_R = \text{Sortino} \times (1 - \text{MDD})$

**Pillar 2: Structural Generalization Index (30% Weight)**
Measures the performance degradation ratio when your model is forced to trade an asset class it has never encountered during training. 
* $S_{Gen} = \frac{\text{Sortino}_{\text{Unseen (XLV)}}}{\text{Sortino}_{\text{Seen (SOXX, XLF, XLE)}}}$

**Pillar 3: Capital & Leverage Efficiency (20% Weight)**
Rewards strategies that generate superior risk-adjusted alpha using capital efficiency rather than brute-force margin amplification. The suite monitors peak leverage stress using the 95th percentile checkpoint.
* $S_E = \text{Sortino} \times \left(1 - \frac{\text{95th Percentile Gross Leverage Used}}{20}\right)$

---

### 5. Guidance Note for Advanced Candidates
The baseline pipeline provided uses standard rolling OLS (`np.linalg.lstsq`) to isolate sector beta. While functional, OLS is highly vulnerable to noise and multicollinearity during macro shocks. 

To secure a top position, advanced candidates should explore:
1. **Regularized and State-Space Estimators:** Implementing Ridge/Lasso constraints, robust M-estimators, or rolling Kalman Filters to generate cleaner, less volatile tracking Betas.
2. **Dynamic Portfolio Optimization:** Replacing the baseline equal-weight asset assignment with modern structural allocators (e.g., Hierarchical Risk Parity or Volatility Targeting).
3. **Statistical Integrity:** Programmatically validating the mean-reverting properties of the residual spreads before capital deployment.

---

### 6. Script Submission Protocol

Submit a **public GitHub repository link** alongside the exact **commit hash, tag, or release** you wish to have evaluated. 

**Your repository must include:**
1. **One Production Strategy File:** Packaged as a single object-oriented Python file adhering to the validation harness template.
2. **A Short README:** Stating exactly which file to run and providing instructions on how to install your dependencies.
3. **Dependency File:** A standard `requirements.txt` or `pyproject.toml` file.
4. **Research Notebooks (Optional but Recommended):** Any supporting research notebooks that explain your reasoning, modeling choices, and conclusions. These must be well-commented.

**Strict Evaluation Rules:**
* **Dynamic Adaptation:** Your code must dynamically handle the initialization parameters passed by the validator without manual hardcoding or sector-specific parameter routing. Ensure your script handles edge-case regime shifts internally to avoid runtime execution errors.
* **Out-of-the-box Execution:** The code must run after normal environment setup, without manual fixes or special instructions.
* **Data-Loading Parity:** The code must use the same data-loading method and input structure as the competition pipeline, allowing the evaluator to easily swap the hidden sector and rerun everything unchanged.
* **Public Access:** The repository must remain public during the review period.
* **Scoring Scope:** Evaluation is based *only* on the designated production strategy file; notebooks are strictly for supporting methodology reviews.