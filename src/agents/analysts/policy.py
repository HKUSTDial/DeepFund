from graph.constants import AgentKey
from graph.prompt import POLICY_PROMPT
from graph.schema import FundState, AnalystSignal
from llm.inference import agent_call
from apis.router import Router, APISource
from util.db_helper import get_db
from util.logger import logger

# thresholds
thresholds = {
    "news_count": 10,
}

def policy_agent(state: FundState):
    """policy specialist analyzing market news to provide a signal."""
    agent_name = AgentKey.POLICY
    ticker = state["ticker"]
    llm_config = state["llm_config"]
    portfolio_id = state["portfolio"].id

    # Get db instance
    db = get_db()
    
    logger.log_agent_status(agent_name, ticker, "Fetching policy related news")
    
    # Get the policy news
    router = Router(APISource.ALPHA_VANTAGE)

    # Economy - Fiscal Policy (e.g., tax reform, government spending): economy_fiscal
    # Economy - Monetary Policy (e.g., interest rates, inflation): economy_monetary

    fiscal_policy = router.get_topic_news_sentiment(limit=10, topic="economy_fiscal")
    monetary_policy = router.get_topic_news_sentiment(limit=10, topic="economy_monetary")

    # Analyze news sentiment via LLM
    fiscal_policy_dict = [m.model_dump() for m in fiscal_policy]
    monetary_policy_dict = [m.model_dump() for m in monetary_policy]
    prompt = POLICY_PROMPT.format(fiscal_policy=fiscal_policy_dict, monetary_policy=monetary_policy_dict)

    # Get LLM signal
    signal = agent_call(
        prompt=prompt,
        llm_config=llm_config,
        pydantic_model=AnalystSignal,
    )

    # save signal
    logger.log_signal(agent_name, ticker, signal)
    db.save_signal(portfolio_id, agent_name, ticker, prompt, signal)
    
    return {"analyst_signals": [signal]}
