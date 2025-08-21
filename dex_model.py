import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Tuple

class DexModel:
    """
    A class to encapsulate the DEX reputation scoring logic.
    It processes wallet transaction data to generate features and a final reputation score.
    """

    def _preprocess_dex_transactions(self, wallet_data: Dict) -> pd.DataFrame:
        """
        Convert wallet transaction data from JSON/dict format to a pandas DataFrame.
        This flattens the nested structure and extracts relevant fields for analysis.
        """
        rows = []
        wallet_address = wallet_data.get('wallet_address', 'N/A')

        for category_data in wallet_data.get('data', []):
            if category_data.get('protocolType') != 'dexes':
                continue

            for tx in category_data.get('transactions', []):
                row = {
                    'wallet_address': wallet_address,
                    'document_id': tx.get('document_id'),
                    'action': tx.get('action'),
                    'timestamp': tx.get('timestamp'),
                    'protocol': tx.get('protocol'),
                    'pool_id': tx.get('poolId'),
                    'pool_name': tx.get('poolName')
                }

                # Extract amounts and symbols based on transaction action
                if tx.get('action') == 'swap':
                    token_in = tx.get('tokenIn', {})
                    token_out = tx.get('tokenOut', {})
                    row['amount_usd'] = max(token_in.get('amountUSD', 0), token_out.get('amountUSD', 0))
                    row['token_in_symbol'] = token_in.get('symbol')
                    row['token_out_symbol'] = token_out.get('symbol')
                elif tx.get('action') in ['deposit', 'withdraw']:
                    token0 = tx.get('token0', {})
                    token1 = tx.get('token1', {})
                    row['amount_usd'] = token0.get('amountUSD', 0) + token1.get('amountUSD', 0)
                    row['token0_symbol'] = token0.get('symbol')
                    row['token1_symbol'] = token1.get('symbol')

                rows.append(row)

        df = pd.DataFrame(rows)
        if not df.empty and 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
            df.dropna(subset=['datetime'], inplace=True) # Drop rows where timestamp conversion failed

        return df

    def _calculate_holding_time(self, deposits: pd.DataFrame, withdraws: pd.DataFrame) -> float:
        """
        Calculate the average holding time for liquidity positions.
        Matches deposits to subsequent withdraws or calculates holding until now if no withdraw.
        """
        if deposits.empty:
            return 0.0

        holding_times = []
        current_time = datetime.now().timestamp()

        for _, deposit in deposits.iterrows():
            deposit_time = deposit['timestamp']
            # Find the earliest withdraw that occurred after this deposit
            future_withdraws = withdraws[withdraws['timestamp'] > deposit_time]

            if not future_withdraws.empty:
                withdraw_time = future_withdraws['timestamp'].min()
                holding_time_seconds = withdraw_time - deposit_time
            else:
                # If no withdraw, the position is still held
                holding_time_seconds = current_time - deposit_time

            holding_times.append(holding_time_seconds / 86400)  # Convert seconds to days

        return np.mean(holding_times) if holding_times else 0.0

    def _calculate_lp_features(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate features related to Liquidity Providing (LP) activities."""
        deposits = df[df['action'] == 'deposit']
        withdraws = df[df['action'] == 'withdraw']

        total_deposit_usd = deposits['amount_usd'].sum()
        total_withdraw_usd = withdraws['amount_usd'].sum()
        
        features = {
            'total_deposit_usd': total_deposit_usd,
            'total_withdraw_usd': total_withdraw_usd,
            'num_deposits': len(deposits),
            'num_withdraws': len(withdraws),
            'withdraw_ratio': total_withdraw_usd / total_deposit_usd if total_deposit_usd > 0 else 0.0,
            'avg_hold_time_days': self._calculate_holding_time(deposits, withdraws),
            'account_age_days': (df['timestamp'].max() - df['timestamp'].min()) / 86400 if not df.empty else 0.0,
            'unique_pools': df['pool_id'].nunique()
        }
        return features

    def _calculate_swap_features(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate features related to swapping/trading activities."""
        swaps = df[df['action'] == 'swap']
        if swaps.empty:
            return {
                'total_swap_volume': 0.0, 'num_swaps': 0, 'unique_pools_swapped': 0,
                'avg_swap_size': 0.0, 'token_diversity': 0
            }

        total_swap_volume = swaps['amount_usd'].sum()
        num_swaps = len(swaps)
        
        # Token diversity
        tokens_in = set(swaps['token_in_symbol'].dropna())
        tokens_out = set(swaps['token_out_symbol'].dropna())
        unique_tokens = tokens_in.union(tokens_out)

        return {
            'total_swap_volume': total_swap_volume,
            'num_swaps': num_swaps,
            'unique_pools_swapped': swaps['pool_id'].nunique(),
            'avg_swap_size': total_swap_volume / num_swaps if num_swaps > 0 else 0.0,
            'token_diversity': len(unique_tokens)
        }

    def _calculate_final_score(self, lp_features: Dict, swap_features: Dict) -> Tuple[float, Dict]:
        """Calculate the final weighted score and combine all features."""
        # --- LP Scoring ---
        volume_score_lp = min(lp_features.get('total_deposit_usd', 0) / 10000 * 300, 300)
        retention_score = max(0, (1 - lp_features.get('withdraw_ratio', 0)) * 250)
        holding_score = min(lp_features.get('avg_hold_time_days', 0) / 30 * 150, 150)
        lp_score = volume_score_lp + retention_score + holding_score

        # --- Swap Scoring ---
        volume_score_swap = min(swap_features.get('total_swap_volume', 0) / 50000 * 250, 250)
        frequency_score_swap = min(swap_features.get('num_swaps', 0) * 10, 200)
        diversity_score_swap = min(swap_features.get('token_diversity', 0) * 20, 150)
        swap_score = volume_score_swap + frequency_score_swap + diversity_score_swap
        
        # --- Final Weighted Score ---
        # Weights can be adjusted. E.g., 60% LP, 40% Swap.
        final_score = (lp_score * 0.6) + (swap_score * 0.4)
        
        # Combine all features into one dictionary
        all_features = {**lp_features, **swap_features}
        
        return final_score, all_features

    def _sanitize_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        CRITICAL STEP: Convert all NumPy numeric types to standard Python types (float, int)
        to prevent JSON serialization errors when producing to Kafka.
        """
        sanitized = {}
        for key, value in features.items():
            if isinstance(value, (np.integer, np.int64)):
                sanitized[key] = int(value)
            elif isinstance(value, (np.floating, np.float64)):
                sanitized[key] = float(value)
            elif isinstance(value, list):
                 # This handles lists of tags, etc.
                sanitized[key] = [str(item) for item in value]
            else:
                sanitized[key] = value
        return sanitized

    def process_wallet(self, wallet_data: Dict) -> Tuple[float, Dict[str, Any]]:
        """
        Main public method to process a wallet's data.
        This orchestrates the entire pipeline from preprocessing to final scoring.
        
        Args:
            wallet_data: The raw wallet data from the Kafka message.
            
        Returns:
            A tuple containing the final score (float) and a dictionary of all calculated features.
        """
        # Step 1: Preprocess data into a DataFrame
        df = self._preprocess_dex_transactions(wallet_data)
        if df.empty:
            raise ValueError("No valid DEX transactions found for this wallet.")

        # Step 2: Calculate features for LP and Swaps
        lp_features = self._calculate_lp_features(df)
        swap_features = self._calculate_swap_features(df)

        # Step 3: Calculate the final score and combine features
        final_score, combined_features = self._calculate_final_score(lp_features, swap_features)
        
        # Step 4: IMPORTANT - Sanitize data types before returning
        sanitized_features = self._sanitize_features(combined_features)
        
        # Also include the transaction count
        sanitized_features['transaction_count'] = len(df)

        return final_score, sanitized_features
