import os
import uuid
from typing import Dict, List, Optional
from graph.schema import Decision, AnalystSignal
from supabase import create_client
from util.logger import logger


class SupabaseDB:
    def __init__(self):
        # Supabase configuration
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

        self.client = create_client(self.url, self.key)


    def get_config(self, config_id: str) -> Optional[Dict]:
        """Get config by id."""
        try:
            response = self.client.table('config').select('*').eq('id', config_id).execute()
            return response.data[0] if response.data else None  
        except Exception as e:
            logger.error(f"Config not found: {e}")
            return None

    def get_config_id_by_name(self, exp_name: str) -> Optional[str]:
        """Get config id by experiment name."""
        try:
            response = self.client.table('config') \
                .select('id') \
                .eq('exp_name', exp_name) \
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Config not found: {e}")
            return None

    def create_config(self, config: Dict) -> Optional[str]:
        """Create a new config entry."""
        try:
            has_planner = not config.get('workflow_analysts', None)
            
            data = {
                'exp_name': config['exp_name'],
                'tickers': config['tickers'],
                'has_planner': has_planner,
                'llm_model': config['llm']['model'],
                'llm_provider': config['llm']['provider'],
            }
            
            response = self.client.table('config').insert(data).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error creating config: {e}")
            return None

    def get_latest_portfolio(self, config_id: str) -> Optional[Dict]:
        """Get the latest portfolio for a config."""
        try:
            response = self.client.table('portfolio') \
                .select('id, cashflow, positions') \
                .eq('config_id', config_id) \
                .order('updated_at', desc=True) \
                .limit(1) \
                .execute()
            
            if response.data and len(response.data) > 0:
                portfolio = response.data[0]
                return {
                    'id': portfolio['id'],
                    'cashflow': float(portfolio['cashflow']),  # Convert Decimal to float
                    'positions': portfolio['positions']  # Already JSON in Supabase
                }
            return None
        except Exception as e:
            logger.error(f"Portfolio not found: {e}")
            return None

    def create_portfolio(self, config_id: str, cashflow: float) -> Optional[str]:
        """Create a new portfolio."""
        try:
            portfolio_id = str(uuid.uuid4())
            data = {
                'id': portfolio_id,
                'config_id': config_id,
                'cashflow': cashflow,
                'total_assets': cashflow,
                'positions': {}
            }
            
            response = self.client.table('portfolio').insert(data).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error creating portfolio: {e}")
            return None

    def update_portfolio(self, config_id: str, portfolio: Dict) -> bool:
        """Update portfolio incrementally."""
        try:
            total_assets = portfolio['cashflow'] + sum(position['value'] for position in portfolio['positions'].values())
            
            data = {
                'id': portfolio['id'],  # Need to keep this for update
                'config_id': config_id,
                'cashflow': portfolio['cashflow'],
                'total_assets': total_assets,
                'positions': portfolio['positions']
            }
            
            response = self.client.table('portfolio').insert(data).execute()
            
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating portfolio: {e}")
            return False

    def save_decision(self, portfolio_id: str, ticker: str, prompt: str, decision: Decision) -> Optional[str]:
        """Save a new decision."""
        try:
            decision_price = decision.price if decision.price else 0
            
            data = {
                'portfolio_id': portfolio_id,
                'ticker': ticker,
                'llm_prompt': prompt,
                'action': str(decision.action),
                'shares': decision.shares,
                'price': decision_price,
                'justification': decision.justification
            }
            
            response = self.client.table('decision').insert(data).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error saving decision: {e}")
            return None

    def save_signal(self, portfolio_id: str, analyst: str, ticker: str, prompt: str, signal: AnalystSignal) -> Optional[str]:
        """Save a new signal."""
        try:
            data = {
                'portfolio_id': portfolio_id,
                'ticker': ticker,
                'llm_prompt': prompt,
                'analyst': analyst,
                'signal': str(signal.signal),
                'justification': signal.justification
            }
            
            response = self.client.table('signal').insert(data).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
            return None

    def get_recent_portfolio_ids_by_config_id(self, config_id: str, limit: int = 5) -> List[str]:
        """Get recent portfolio ids by config id."""
        try:
            response = self.client.table('portfolio') \
                .select('id') \
                .eq('config_id', config_id) \
                .order('updated_at', desc=True) \
                .limit(limit) \
                .execute()
            
            return [row['id'] for row in response.data]
        except Exception as e:
            logger.error(f"Error getting portfolio ids: {e}")
            return []

    def get_decision_memory(self, exp_name: str, ticker: str) -> List[Dict]:
        """Get recent 5 decisions for a ticker."""
        try:
            # Step 1: Get config id by exp_name
            config_id = self.get_config_id_by_name(exp_name)
            if not config_id:
                logger.error(f"Config not found for {exp_name}")
                return []
            
            # Step 2: Get recent 5 portfolio transactions
            portfolio_ids = self.get_recent_portfolio_ids_by_config_id(config_id, limit=5)
            if not portfolio_ids:
                logger.error(f"Portfolio not found for {config_id}")
                return []
            
            # Step 3: Get decision memory by portfolio ids and ticker
            response = self.client.table('decision') \
                .select('updated_at, action, shares, price') \
                .in_('portfolio_id', portfolio_ids) \
                .eq('ticker', ticker) \
                .order('updated_at', desc=True) \
                .execute()
            
            decisions = []
            for row in response.data:
                decisions.append({
                    'updated_at': row['updated_at'],
                    'action': row['action'],
                    'shares': row['shares'],
                    'price': float(row['price']),  # Convert Decimal to float
                })
            
            return decisions
        except Exception as e:
            logger.warning(f"No decision memory found for {ticker} in {exp_name}: {e}")
            return []

# Initialize global instance
# db = SupabaseDB() 