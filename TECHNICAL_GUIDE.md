# DeepFund Technical Guide

This document contains detailed technical information for developers and researchers working with DeepFund.

## Analyst Breakdown

|    Name     |   Function  | Upstream Source | 
| ----------- | ----------- | ----------- | 
| company_news  | Analyzes company news. | Lately Company news.  | 
| fundamental   | Analyzes financial metrics. | Company profitability, growth, cashflow and financial health. |
| insider       | Analyzes company insider trading activity. | Recent insider transactions made by key stakeholders. |
| macroeconomic | Analyzes macroeconomic indicators. | US economic indicators GDP, CPI, rate, unemployment, etc.    |
| policy        | Analyzes policy news. | Fiscal and monetary policy news. |
| technical     | Analyzes technical indicators  for short to medium-term price movement predictions. | Technical indicators trend, mean reversion, RSI, volatility, volume, support resistance. |

### Remarks:
**Unified Output**: All analysts output the same format: Signal=(Bullish, Bearish, Neutral), Justification=...

**Time-sensitive Analysts**: Because of the constraints of upstream API service, analyst **company_news**, **insider**, **policy**, and **technical** support  historical data analysis via `trading-date` option, while other analysts can only retrieve the latest data.

## System Dependencies

### LLM Providers
- Official API: OpenAI, DeepSeek, Anthropic, Grok, etc.
- LLM Proxy API: Fireworks AI, AiHubMix, etc.
- Local API: Ollama, etc.

### Financial Data Source 
- Alpha Vantage API: Stock Market Data API, [Claim Free API Key](https://www.alphavantage.co)
- YFinance API: Download Market Data from Yahoo! Finance's API, [Doc](https://yfinance-python.org/)

## Advanced Usage

### How to add a new analyst?

To add a new analyst to the DeepFund system, follow these general steps:

1.  **Build the Analyst:**
    Create a new Python file for your analyst within the `src/agents/analysts` directory. Implement the core logic for your analyst within this file. This typically involves defining an agent function that takes relevant inputs (like tickers, market data), performs analysis (potentially using LLMs or specific APIs), and returns signals.

2.  **Define Prompts:**
    If your analyst is driven by an LLM, define the prompt(s) it will use. These will go in the `src/llm/prompt.py` file.

3.  **Register the Analyst:**
    Make the system aware of your new analyst. This will involve adding its name or reference to a central registry in `src/graph/constants.py` or within the agent registration logic in `src/agents/registry.py`. Check these files for patterns used by existing analysts.

4.  **Update Configuration:**
    Add the unique name or key of your new analyst to the `workflow_analysts` list in your desired configuration file (e.g., `src/config/my_config.yaml`).

5.  **Add Data Dependencies (if any):**
    If your analyst requires new external data sources (e.g., a specific API), add the necessary API client logic in the `src/apis/` directory, and update environment variable handling (`.env.example`, `.env`) if API keys are needed.

6.  **Testing:**
    Thoroughly test your new analyst by running the system with a configuration that includes it. Check the database tables (`Decision`, `Signal`) to ensure it produces the expected output and integrates correctly with the portfolio manager.

Remember to consult the existing analyst implementations in `src/agents/` and the workflow definitions in `src/graph/` for specific patterns and conventions used in this project.

---

### How to add a new base LLM?

To integrate a new LLM provider (e.g., a different API service) into the system:

1.  **Implement Provider Logic:**
    Please refer to `src/llm/new_provider.py` for the implementation. We align the structure of the new provider with the existing providers.

2.  **Handle API Keys:**
    If the new provider requires an API key or other credentials, add the corresponding environment variable(s) to `.env.example` and instruct users to add their keys to their `.env` file.

3.  **Update Configuration:**
    Document the necessary `provider` and `model` names for the new service. Users will need to specify these in their YAML configuration files under the `llm:` section (e.g., in `src/config/provider/my_config.yaml`).
    ```yaml
    llm:
      provider: "" # The identifier you added in step 1
      model: "" # provider-specific settings here
    ```

4.  **Testing:**
    Run the system using a configuration file that specifies your new LLM provider. Ensure that the LLM calls are successful and that the agents receive the expected responses.

Consult the implementations for existing providers (like OpenAI, DeepSeek) in `src/llm/` as a reference. 