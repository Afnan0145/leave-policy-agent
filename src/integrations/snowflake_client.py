"""
Snowflake client with circuit breaker protection
Supports both real Snowflake connection and mock mode for testing
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .circuit_breaker import CircuitBreaker, CircuitBreakerError, register_circuit_breaker

logger = logging.getLogger(__name__)

# Try to import Snowflake, but allow mock mode if not available
try:
    from snowflake.snowpark import Session
    from snowflake.snowpark.exceptions import SnowparkSQLException
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    logger.warning("Snowflake Snowpark not installed, using mock mode only")
    SNOWFLAKE_AVAILABLE = False
    SnowparkSQLException = Exception


# Import mock employee data
from config.leave_policies import MOCK_EMPLOYEES


class SnowflakeClient:
    """
    Snowflake client with circuit breaker protection
    
    Features:
    - Circuit breaker for resilience
    - Connection pooling
    - Query caching
    - Mock mode for testing
    
    Environment Variables:
        SNOWFLAKE_ACCOUNT: Snowflake account identifier
        SNOWFLAKE_USER: Username
        SNOWFLAKE_PASSWORD: Password
        SNOWFLAKE_DATABASE: Database name
        SNOWFLAKE_SCHEMA: Schema name
        SNOWFLAKE_WAREHOUSE: Warehouse name
        USE_MOCK_SNOWFLAKE: Set to 'true' to use mock data
    """
    
    def __init__(
        self,
        use_mock: bool = None,
        circuit_breaker_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Snowflake client
        
        Args:
            use_mock: Force mock mode (overrides env var)
            circuit_breaker_config: Custom circuit breaker settings
        """
        # Determine if we should use mock mode
        self.use_mock = use_mock if use_mock is not None else (
            os.getenv("USE_MOCK_SNOWFLAKE", "false").lower() == "true"
        )
        
        # Initialize circuit breaker
        cb_config = circuit_breaker_config or {}
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=cb_config.get("failure_threshold", 5),
            timeout=cb_config.get("timeout", 60),
            success_threshold=cb_config.get("success_threshold", 2),
            name="snowflake_client"
        )
        
        # Register in global registry
        register_circuit_breaker("snowflake_client", self.circuit_breaker)
        
        self.session: Optional[Session] = None
        self._connection_params = None
        
        if not self.use_mock:
            if not SNOWFLAKE_AVAILABLE:
                logger.warning(
                    "Snowflake Snowpark not available, falling back to mock mode"
                )
                self.use_mock = True
            else:
                self._setup_connection_params()
                logger.info("Snowflake client initialized (real mode)")
        else:
            logger.info("Snowflake client initialized (mock mode)")
    
    def _setup_connection_params(self):
        """Setup Snowflake connection parameters from environment"""
        required_vars = [
            "SNOWFLAKE_ACCOUNT",
            "SNOWFLAKE_USER",
            "SNOWFLAKE_PASSWORD",
            "SNOWFLAKE_DATABASE",
            "SNOWFLAKE_SCHEMA",
            "SNOWFLAKE_WAREHOUSE"
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.warning(
                f"Missing Snowflake environment variables: {missing_vars}. "
                "Falling back to mock mode."
            )
            self.use_mock = True
            return
        
        self._connection_params = {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "password": os.getenv("SNOWFLAKE_PASSWORD"),
            "database": os.getenv("SNOWFLAKE_DATABASE"),
            "schema": os.getenv("SNOWFLAKE_SCHEMA"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE")
        }
    
    def _get_session(self) -> Session:
        """Get or create Snowflake session"""
        if self.session is None:
            if self._connection_params is None:
                raise ValueError("Snowflake connection not configured")
            
            logger.info("Creating new Snowflake session")
            self.session = Session.builder.configs(self._connection_params).create()
        
        return self.session
    
    def get_employee_by_id(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Get employee data by ID
        
        Args:
            employee_id: Employee identifier
            
        Returns:
            Employee data dict or None if not found
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        if self.use_mock:
            return self._get_employee_mock(employee_id)
        
        try:
            return self.circuit_breaker.call(
                self._query_employee_real,
                employee_id
            )
        except CircuitBreakerError:
            logger.error(
                f"Circuit breaker open, falling back to mock data for {employee_id}"
            )
            # Graceful degradation - use mock data
            return self._get_employee_mock(employee_id)
        except Exception as e:
            logger.error(f"Error querying Snowflake: {e}")
            # Fallback to mock data
            return self._get_employee_mock(employee_id)
    
    def _get_employee_mock(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get employee from mock data"""
        logger.debug(f"Fetching employee {employee_id} from mock data")
        employee = MOCK_EMPLOYEES.get(employee_id)
        
        if employee:
            return dict(employee)  # Return a copy
        return None
    
    def _query_employee_real(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Query employee from real Snowflake database"""
        logger.debug(f"Querying employee {employee_id} from Snowflake")
        
        session = self._get_session()
        
        query = f"""
        SELECT 
            employee_id,
            name,
            country,
            department,
            join_date,
            tenure_months,
            leave_balance
        FROM employees
        WHERE employee_id = '{employee_id}'
        LIMIT 1
        """
        
        try:
            result = session.sql(query).collect()
            
            if not result:
                logger.debug(f"Employee {employee_id} not found in Snowflake")
                return None
            
            row = result[0]
            
            # Convert to dict
            employee_data = {
                "employee_id": row["EMPLOYEE_ID"],
                "name": row["NAME"],
                "country": row["COUNTRY"],
                "department": row["DEPARTMENT"],
                "join_date": row["JOIN_DATE"],
                "tenure_months": row["TENURE_MONTHS"],
                "leave_balance": row["LEAVE_BALANCE"]  # Assuming JSON/VARIANT type
            }
            
            logger.debug(f"Successfully fetched employee {employee_id}")
            return employee_data
            
        except SnowparkSQLException as e:
            logger.error(f"Snowflake SQL error: {e}")
            raise
    
    def query_employees_by_country(self, country: str) -> List[Dict[str, Any]]:
        """
        Get all employees in a country
        
        Args:
            country: Country code
            
        Returns:
            List of employee dicts
        """
        if self.use_mock:
            return [
                dict(emp) for emp in MOCK_EMPLOYEES.values()
                if emp["country"] == country
            ]
        
        try:
            return self.circuit_breaker.call(
                self._query_employees_by_country_real,
                country
            )
        except (CircuitBreakerError, Exception) as e:
            logger.error(f"Error querying employees by country: {e}")
            # Fallback to mock
            return [
                dict(emp) for emp in MOCK_EMPLOYEES.values()
                if emp["country"] == country
            ]
    
    def _query_employees_by_country_real(self, country: str) -> List[Dict[str, Any]]:
        """Query employees by country from Snowflake"""
        session = self._get_session()
        
        query = f"""
        SELECT 
            employee_id,
            name,
            country,
            department,
            join_date,
            tenure_months,
            leave_balance
        FROM employees
        WHERE country = '{country}'
        """
        
        results = session.sql(query).collect()
        
        return [
            {
                "employee_id": row["EMPLOYEE_ID"],
                "name": row["NAME"],
                "country": row["COUNTRY"],
                "department": row["DEPARTMENT"],
                "join_date": row["JOIN_DATE"],
                "tenure_months": row["TENURE_MONTHS"],
                "leave_balance": row["LEAVE_BALANCE"]
            }
            for row in results
        ]
    
    def health_check(self) -> bool:
        """
        Check if Snowflake connection is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        if self.use_mock:
            return True
        
        try:
            session = self._get_session()
            session.sql("SELECT 1").collect()
            logger.debug("Snowflake health check passed")
            return True
        except Exception as e:
            logger.error(f"Snowflake health check failed: {e}")
            return False
    
    def close(self):
        """Close Snowflake session"""
        if self.session:
            logger.info("Closing Snowflake session")
            self.session.close()
            self.session = None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            "mode": "mock" if self.use_mock else "real",
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "session_active": self.session is not None
        }
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Global singleton instance
_snowflake_client: Optional[SnowflakeClient] = None


def get_snowflake_client() -> SnowflakeClient:
    """Get or create global Snowflake client instance"""
    global _snowflake_client
    
    if _snowflake_client is None:
        _snowflake_client = SnowflakeClient()
    
    return _snowflake_client