import os
import logging
import random
import time
import threading
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Connection state tracking
        self.connection_state = {
            'healthy': True,
            'last_successful_connection': time.time(),
            'consecutive_failures': 0,
            'retry_count': 0,
            'last_error': None,
            'total_reconnect_attempts': 0,
            'pool_size_current': 0,
            'connection_latency': 0.0
        }
        
        # Connection monitoring settings
        self.CONNECTION_MONITOR = {
            'MAX_RETRIES': 10,
            'BASE_DELAY': 1,
            'MAX_DELAY': 60,
            'HEALTH_CHECK_INTERVAL': 30,
            'CRITICAL_FAILURE_THRESHOLD': 5,
            'CONNECTION_TIMEOUT': 10
        }
        
        # Initialize SQLAlchemy event listeners
        self._setup_event_listeners()
        self._initialized = True
    
    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners"""
        event.listen(Engine, "connect", self._on_connect)
        event.listen(Engine, "engine_connect", self._on_engine_connect)
        event.listen(Engine, "checkout", self._on_checkout)
        event.listen(Engine, "checkin", self._on_checkin)
        event.listen(Engine, "invalidate", self._on_invalidate)
    
    def reset_connection_state(self):
        """Reset the connection state tracking"""
        self.connection_state['healthy'] = True
        self.connection_state['consecutive_failures'] = 0
        self.connection_state['retry_count'] = 0
        self.connection_state['last_successful_connection'] = time.time()
    
    def get_retry_delay(self):
        """Calculate retry delay with enhanced exponential backoff and circuit breaker"""
        if self.connection_state['consecutive_failures'] >= self.CONNECTION_MONITOR['CRITICAL_FAILURE_THRESHOLD']:
            base_delay = self.CONNECTION_MONITOR['BASE_DELAY'] * 2
        else:
            base_delay = self.CONNECTION_MONITOR['BASE_DELAY']
        
        jitter = random.uniform(0, min(self.CONNECTION_MONITOR['MAX_DELAY'], base_delay * 3))
        delay = min(
            base_delay * (2 ** self.connection_state['retry_count']) + jitter,
            self.CONNECTION_MONITOR['MAX_DELAY']
        )
        
        latency_factor = min(self.connection_state['connection_latency'], 1.0)
        delay += latency_factor
        
        return min(delay, self.CONNECTION_MONITOR['MAX_DELAY'])
    
    # Event handlers
    def _on_connect(self, dbapi_connection, connection_record):
        logger.info("Database connection established")
        self.reset_connection_state()
    
    def _on_engine_connect(self, connection):
        logger.info("Engine connection established")
    
    def _on_checkout(self, dbapi_connection, connection_record, connection_proxy):
        logger.debug("Database connection checked out from pool")
    
    def _on_checkin(self, dbapi_connection, connection_record):
        logger.debug("Database connection returned to pool")
    
    def _on_invalidate(self, dbapi_connection, connection_record, exception):
        logger.warning(f"Database connection invalidated due to error: {exception}")
        self.connection_state['healthy'] = False
        self.connection_state['consecutive_failures'] += 1
    
    def test_connection(self, db):
        """Test database connection with enhanced retry logic and comprehensive monitoring"""
        start_time = time.time()
        try:
            with db.engine.connect() as connection:
                # Set statement timeout and idle timeout
                connection.execute(text("""
                    SET statement_timeout = '10s';
                    SET idle_in_transaction_session_timeout = '30s';
                """))
                
                # Enable connection timeout and set application name for tracking
                connection.execution_options(
                    timeout=self.CONNECTION_MONITOR['CONNECTION_TIMEOUT'],
                    isolation_level="READ COMMITTED"
                )
                connection.execute(text("SET application_name = 'supply_drop_ai'"))
                
                # Basic connectivity test
                result = connection.execute(text("SELECT 1")).scalar()
                
                pool_status = connection.execute(text("""
                    SELECT numbackends, state, xact_commit, xact_rollback,
                           blks_read, blks_hit, tup_returned, tup_fetched,
                           (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                           (SELECT count(*) FROM pg_stat_activity WHERE state = 'idle') as idle_connections,
                           (SELECT extract(epoch from now() - pg_postmaster_start_time())) as uptime_seconds
                    FROM pg_stat_database
                    WHERE datname = current_database()
                """)).fetchone()
                
                if result == 1 and pool_status:
                    self.connection_state['connection_latency'] = time.time() - start_time
                    self.connection_state['pool_size_current'] = pool_status[0]
                    self.connection_state['transaction_stats'] = {
                        'commits': pool_status[2],
                        'rollbacks': pool_status[3],
                        'cache_hit_ratio': pool_status[5] / (pool_status[4] + pool_status[5]) if (pool_status[4] + pool_status[5]) > 0 else 1.0,
                        'active_connections': pool_status[8],
                        'idle_connections': pool_status[9],
                        'uptime_seconds': pool_status[10]
                    }
                    
                    if self.connection_state['transaction_stats']['active_connections'] > db.engine.pool.size:
                        logger.warning("Connection pool near capacity - consider scaling")
                    
                    logger.info(
                        f"Connection test successful:\n"
                        f"Latency: {self.connection_state['connection_latency']:.3f}s\n"
                        f"Cache hit ratio: {self.connection_state['transaction_stats']['cache_hit_ratio']:.2%}\n"
                        f"Active/Idle connections: {self.connection_state['transaction_stats']['active_connections']}/{self.connection_state['transaction_stats']['idle_connections']}\n"
                        f"Database uptime: {self.connection_state['transaction_stats']['uptime_seconds']/3600:.1f}h"
                    )
                    
                    if self.connection_state['connection_latency'] < self.CONNECTION_MONITOR['CONNECTION_TIMEOUT']:
                        self.reset_connection_state()
                        return True
                    else:
                        raise Exception(f"Connection latency ({self.connection_state['connection_latency']:.3f}s) exceeds threshold")
                
                raise Exception("Connection test failed: Invalid response from database")
                
        except Exception as e:
            self.connection_state['healthy'] = False
            self.connection_state['consecutive_failures'] += 1
            self.connection_state['retry_count'] += 1
            self.connection_state['last_error'] = str(e)
            self.connection_state['total_reconnect_attempts'] += 1
            
            logger.error(
                f"Database connection test failed: {e}\n"
                f"Consecutive failures: {self.connection_state['consecutive_failures']}\n"
                f"Total reconnection attempts: {self.connection_state['total_reconnect_attempts']}"
            )
            return False
    
    def attempt_recovery(self, db):
        """Attempt to recover database connection with enhanced error handling"""
        max_attempts = self.CONNECTION_MONITOR['MAX_RETRIES']
        recovery_start = time.time()
        
        while not self.connection_state['healthy'] and self.connection_state['total_reconnect_attempts'] < max_attempts:
            delay = self.get_retry_delay()
            logger.info(f"Attempting connection recovery in {delay:.2f} seconds... (Attempt {self.connection_state['total_reconnect_attempts'] + 1}/{max_attempts})")
            time.sleep(delay)
            
            try:
                if hasattr(db, 'engine'):
                    db.engine.dispose()
                
                if self.test_connection(db):
                    recovery_time = time.time() - recovery_start
                    logger.info(f"Database connection recovered successfully after {recovery_time:.2f}s")
                    
                    self.connection_state['last_successful_connection'] = time.time()
                    self.connection_state['consecutive_failures'] = 0
                    return True
                
            except Exception as e:
                self.connection_state['last_error'] = str(e)
                self.connection_state['consecutive_failures'] += 1
                
                if "timeout" in str(e).lower():
                    logger.error(f"Connection timeout - possible network issue: {e}")
                elif "authentication" in str(e).lower():
                    logger.critical(f"Authentication error - check credentials: {e}")
                    break
                else:
                    logger.error(f"Unknown error during recovery: {e}")
            
            if self.connection_state['consecutive_failures'] >= self.CONNECTION_MONITOR['CRITICAL_FAILURE_THRESHOLD']:
                logger.critical(
                    "Circuit breaker triggered - multiple critical failures detected\n"
                    f"Last error: {self.connection_state['last_error']}\n"
                    f"Total attempts: {self.connection_state['total_reconnect_attempts']}"
                )
                break
        
        if self.connection_state['total_reconnect_attempts'] >= max_attempts:
            logger.critical(f"Recovery failed after {max_attempts} attempts - manual intervention required")
        
        return False
    
    def get_connection_stats(self, db):
        """Get detailed connection pool statistics"""
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT state, count(*) as count
                    FROM pg_stat_activity
                    GROUP BY state
                """)).fetchall()
                
                stats = {
                    'active_connections': sum(row[1] for row in result if row[0] == 'active'),
                    'idle_connections': sum(row[1] for row in result if row[0] == 'idle'),
                    'total_connections': sum(row[1] for row in result),
                    'latency': self.connection_state['connection_latency'],
                    'consecutive_failures': self.connection_state['consecutive_failures'],
                    'total_reconnect_attempts': self.connection_state['total_reconnect_attempts']
                }
                
                logger.info(f"Connection pool stats: {stats}")
                return stats
        except Exception as e:
            logger.error(f"Failed to get connection stats: {e}")
            return None
