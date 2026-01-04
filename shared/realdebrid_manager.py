import time
import random
import requests
from urllib.parse import urljoin
from typing import Optional, List, Dict, Any
from shared.shared import realdebrid
from shared.requests import retryRequest

class RealDebridAccountManager:
    """Manages multiple Real-Debrid accounts with load balancing and rate limit handling"""
    
    def __init__(self):
        self.accounts = realdebrid.get('accounts', [])
        self.current_account_index = 0
        self.rate_limit_cooldown = 300  # 5 minutes cooldown for rate limited accounts
        
    def get_available_account(self) -> Optional[Dict[str, Any]]:
        """Get the next available Real-Debrid account that's not rate limited"""
        if not self.accounts:
            return None
            
        # First, try to find an account that's not rate limited
        available_accounts = [acc for acc in self.accounts if not acc.get('rateLimited', False) and acc.get('enabled', True)]
        
        # If all accounts are rate limited, check if any have passed the cooldown period
        if not available_accounts:
            current_time = time.time()
            for account in self.accounts:
                if account.get('rateLimited', False) and account.get('enabled', True):
                    last_rate_limit = account.get('lastRateLimitTime', 0)
                    if current_time - last_rate_limit > self.rate_limit_cooldown:
                        account['rateLimited'] = False
                        available_accounts.append(account)
                        print(f"Real-Debrid account {account['id']} recovered from rate limit")
        
        if not available_accounts:
            print("No available Real-Debrid accounts (all are rate limited or disabled)")
            return None
            
        # Use round-robin with some randomization for load balancing
        if len(available_accounts) > 1:
            # Sort by last used time and pick the least recently used
            available_accounts.sort(key=lambda x: x.get('lastUsed', 0))
            # Add some randomization to avoid always picking the same account when requests are concurrent
            if random.random() < 0.3:  # 30% chance to pick randomly from top 2
                account = random.choice(available_accounts[:min(2, len(available_accounts))])
            else:
                account = available_accounts[0]
        else:
            account = available_accounts[0]
            
        # Update last used time
        account['lastUsed'] = time.time()
        print(f"Selected Real-Debrid account {account['id']} for processing")
        return account
    
    def mark_rate_limited(self, account: Dict[str, Any]):
        """Mark an account as rate limited"""
        account['rateLimited'] = True
        account['lastRateLimitTime'] = time.time()
        print(f"Real-Debrid account {account['id']} marked as rate limited")
    
    def check_account_status(self, account: Dict[str, Any]) -> bool:
        """Check if an account is working properly"""
        try:
            headers = {'Authorization': f'Bearer {account["apiKey"]}'}
            response = requests.get(urljoin(account['host'], "user"), headers=headers, timeout=10)
            
            if response.status_code == 429:  # Rate limited
                self.mark_rate_limited(account)
                return False
            elif response.status_code in [401, 403]:  # Unauthorized or forbidden
                account['enabled'] = False
                print(f"Real-Debrid account {account['id']} disabled due to auth error")
                return False
            elif response.status_code == 200:
                # Account is working
                if account.get('rateLimited', False):
                    account['rateLimited'] = False
                    print(f"Real-Debrid account {account['id']} recovered from rate limit")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Error checking Real-Debrid account {account['id']}: {e}")
            return False
    
    def get_account_by_id(self, account_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific account by ID"""
        return next((acc for acc in self.accounts if acc['id'] == account_id), None)
    
    def get_healthy_accounts(self) -> List[Dict[str, Any]]:
        """Get all accounts that are enabled and not rate limited"""
        current_time = time.time()
        healthy_accounts = []
        
        for account in self.accounts:
            if not account.get('enabled', True):
                continue
                
            # Check if rate limit has expired
            if account.get('rateLimited', False):
                last_rate_limit = account.get('lastRateLimitTime', 0)
                if current_time - last_rate_limit > self.rate_limit_cooldown:
                    account['rateLimited'] = False
                else:
                    continue
                    
            healthy_accounts.append(account)
            
        return healthy_accounts
    
    def get_account_stats(self) -> Dict[str, Any]:
        """Get detailed statistics about all accounts"""
        total_accounts = len(self.accounts)
        enabled_accounts = len([acc for acc in self.accounts if acc.get('enabled', True)])
        rate_limited_accounts = len([acc for acc in self.accounts if acc.get('rateLimited', False)])
        healthy_accounts = len(self.get_healthy_accounts())
        
        current_time = time.time()
        account_details = []
        
        for account in self.accounts:
            last_used = account.get('lastUsed', 0)
            last_rate_limit = account.get('lastRateLimitTime', 0)
            time_since_last_use = current_time - last_used if last_used > 0 else None
            time_since_rate_limit = current_time - last_rate_limit if last_rate_limit > 0 else None
            
            account_details.append({
                'id': account['id'],
                'enabled': account.get('enabled', True),
                'rateLimited': account.get('rateLimited', False),
                'consecutiveFailures': account.get('consecutiveFailures', 0),
                'lastUsed': time_since_last_use,
                'lastRateLimit': time_since_rate_limit,
                'host': account['host'],
                'mountPath': account['mountTorrentsPath']
            })
        
        return {
            'total': total_accounts,
            'enabled': enabled_accounts,
            'rate_limited': rate_limited_accounts,
            'healthy': healthy_accounts,
            'accounts': account_details,
            'load_balance_stats': {
                'rate_limit_cooldown': self.rate_limit_cooldown,
                'timestamp': current_time
            }
        }
    
    def print_account_status(self):
        """Print a summary of all account statuses"""
        stats = self.get_account_stats()
        print(f"\n=== Real-Debrid Account Status ===")
        print(f"Total accounts: {stats['total']}")
        print(f"Enabled accounts: {stats['enabled']}")
        print(f"Rate limited accounts: {stats['rate_limited']}")
        print(f"Healthy accounts: {stats['healthy']}")
        print("\nAccount Details:")
        
        for account in stats['accounts']:
            status = "HEALTHY"
            if not account['enabled']:
                status = "DISABLED"
            elif account['rateLimited']:
                status = "RATE LIMITED"
            elif account['consecutiveFailures'] > 0:
                status = f"DEGRADED ({account['consecutiveFailures']} failures)"
            
            last_use_str = f"{account['lastUsed']:.1f}s ago" if account['lastUsed'] else "Never"
            print(f"  Account {account['id']}: {status} (Last used: {last_use_str})")
        print("=" * 35)
    
    def periodic_health_check(self):
        """Perform periodic health checks on all accounts"""
        print("Performing periodic health check on Real-Debrid accounts...")
        
        for account in self.accounts:
            if not account.get('enabled', True):
                continue
                
            try:
                is_healthy = self.check_account_status(account)
                if is_healthy:
                    account['lastHealthCheck'] = time.time()
                    account['consecutiveFailures'] = 0
                else:
                    account['consecutiveFailures'] = account.get('consecutiveFailures', 0) + 1
                    # Disable account after 3 consecutive failures
                    if account['consecutiveFailures'] >= 3:
                        account['enabled'] = False
                        print(f"Real-Debrid account {account['id']} disabled after 3 consecutive failures")
                        
            except Exception as e:
                print(f"Error during health check for account {account['id']}: {e}")
                account['consecutiveFailures'] = account.get('consecutiveFailures', 0) + 1
    
    def enable_account(self, account_id: int):
        """Manually enable a disabled account"""
        account = self.get_account_by_id(account_id)
        if account:
            account['enabled'] = True
            account['rateLimited'] = False
            account['consecutiveFailures'] = 0
            print(f"Real-Debrid account {account_id} manually enabled")
            return True
        return False
    
    def disable_account(self, account_id: int):
        """Manually disable an account"""
        account = self.get_account_by_id(account_id)
        if account:
            account['enabled'] = False
            print(f"Real-Debrid account {account_id} manually disabled")
            return True
        return False

# Global instance
realdebrid_manager = RealDebridAccountManager()
