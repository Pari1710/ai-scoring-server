from pydantic import BaseModel, Field
from typing import List, Dict, Any

# --- Input Models ---

class TransactionDetail(BaseModel):
    """Defines the structure of a single transaction."""
    document_id: str
    action: str
    timestamp: int
    # ... add other transaction fields if needed for validation

class ProtocolData(BaseModel):
    """Defines the data for a specific protocol type like 'dexes'."""
    protocolType: str
    transactions: List[TransactionDetail]

class WalletTransactionInput(BaseModel):
    """
    The main input model for a message from the 'wallet-transactions' topic.
    This is the bouncer for your incoming data.
    """
    wallet_address: str
    data: List[ProtocolData]

# --- Output Models ---

class CategoryFeatures(BaseModel):
    """Defines the structure of the 'features' dictionary in the output."""
    total_deposit_usd: float
    total_withdraw_usd: float
    num_deposits: int
    num_withdraws: int
    withdraw_ratio: float
    avg_hold_time_days: float
    account_age_days: float
    unique_pools: int
    total_swap_volume: float
    num_swaps: int
    unique_pools_swapped: int
    avg_swap_size: float
    token_diversity: int
    transaction_count: int

class CategoryOutput(BaseModel):
    """Defines the structure for an item in the 'categories' list."""
    category: str = "dexes"
    score: float
    transaction_count: int
    features: CategoryFeatures

class ScoringResultSuccess(BaseModel):
    """
    The main output model for a successful scoring message.
    This ensures your success messages always have the correct format.
    """
    wallet_address: str
    zscore: str
    timestamp: int
    processing_time_ms: int
    categories: List[CategoryOutput]

class ScoringResultFailure(BaseModel):
    """
    The main output model for a failed scoring message.
    Ensures your failure messages are consistent.
    """
    wallet_address: str
    error: str
    timestamp: int
    processing_time_ms: int
