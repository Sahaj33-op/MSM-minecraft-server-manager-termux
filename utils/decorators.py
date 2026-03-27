#!/usr/bin/env python3
"""
Decorators - Common decorators for error handling, performance monitoring, and validation
"""
import time
import functools
import logging
import threading
from typing import Any, Callable, Optional, Type, Union, Tuple
from core.constants import ErrorMessages, NetworkConfig


def _log_message(logger: Optional[Any], level: str, message: str) -> None:
    """Support both stdlib loggers and MSM's EnhancedLogger."""
    if not logger:
        return

    log_method = getattr(logger, level.lower(), None)
    if callable(log_method):
        log_method(message)
        return

    generic_log = getattr(logger, 'log', None)
    if callable(generic_log):
        generic_log(level.upper(), message)

def handle_errors(
    logger: Optional[logging.Logger] = None,
    default_return: Any = None,
    reraise: bool = False,
    log_level: str = 'ERROR'
) -> Callable:
    """Decorator for consistent error handling across methods.
    
    Args:
        logger: Logger instance for error logging
        default_return: Value to return on error
        reraise: Whether to reraise the exception after logging
        log_level: Log level for error messages
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _log_message(logger, log_level, f'Error in {func.__name__}: {e}')
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator

def retry(
    max_attempts: int = NetworkConfig.MAX_RETRIES,
    delay: float = NetworkConfig.RETRY_DELAY,
    backoff: float = NetworkConfig.RETRY_BACKOFF,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[logging.Logger] = None
) -> Callable:
    """Decorator for retrying failed operations with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exception types to retry on
        logger: Logger instance for retry logging
        
    Returns:
        Decorated function
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        _log_message(
                            logger,
                            'WARNING',
                            f'Attempt {attempt + 1} failed for {func.__name__}: {e}. '
                            f'Retrying in {current_delay}s...'
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        _log_message(
                            logger,
                            'ERROR',
                            f'All {max_attempts} attempts failed for {func.__name__}: {e}'
                        )
                        raise last_exception
        return wrapper
    return decorator

def performance_monitor(
    logger: Optional[logging.Logger] = None,
    log_threshold: float = 1.0
) -> Callable:
    """Decorator for monitoring function execution time.
    
    Args:
        logger: Logger instance for performance logging
        log_threshold: Minimum execution time to log (seconds)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            
            if execution_time >= log_threshold:
                _log_message(logger, 'DEBUG', f'{func.__name__} executed in {execution_time:.2f}s')
            
            return result
        return wrapper
    return decorator

def validate_input(
    *validators: Callable[[Any], bool],
    error_message: str = ErrorMessages.INVALID_INPUT
) -> Callable:
    """Decorator for input validation.
    
    Args:
        validators: Functions that return True for valid input
        error_message: Error message to raise on validation failure
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Validate all arguments
            for arg in args:
                for validator in validators:
                    if not validator(arg):
                        raise ValueError(error_message)
            
            # Validate keyword arguments
            for value in kwargs.values():
                for validator in validators:
                    if not validator(value):
                        raise ValueError(error_message)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def cache_result(
    ttl: float = 300.0,  # 5 minutes default
    max_size: int = 100
) -> Callable:
    """Decorator for caching function results with TTL.
    
    Args:
        ttl: Time to live for cached results in seconds
        max_size: Maximum number of cached results
        
    Returns:
        Decorated function
    """
    cache = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Create cache key from args and kwargs
            cache_key = (args, tuple(sorted(kwargs.items())))
            current_time = time.time()
            
            # Check if result is cached and not expired
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if current_time - timestamp < ttl:
                    return result
                else:
                    # Remove expired entry
                    del cache[cache_key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            
            # Clean up cache if it's too large
            if len(cache) >= max_size:
                # Remove oldest entries
                oldest_key = min(cache.keys(), key=lambda k: cache[k][1])
                del cache[oldest_key]
            
            cache[cache_key] = (result, current_time)
            return result
        return wrapper
    return decorator

def timeout(
    timeout_seconds: float = 30.0,
    logger: Optional[logging.Logger] = None
) -> Callable:
    """Decorator for adding timeout to function execution.
    
    Args:
        timeout_seconds: Timeout in seconds
        logger: Logger instance for timeout logging
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = [None]
            exception = [None]

            def target() -> None:
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as exc:
                    exception[0] = exc

            worker = threading.Thread(target=target, daemon=True, name=f"timeout-{func.__name__}")
            worker.start()
            worker.join(timeout=timeout_seconds)

            if worker.is_alive():
                message = f'Function {func.__name__} timed out after {timeout_seconds}s'
                _log_message(logger, 'ERROR', f'Timeout in {func.__name__}: {message}')
                raise TimeoutError(message)

            if exception[0] is not None:
                raise exception[0]

            return result[0]
        return wrapper
    return decorator

def log_function_call(
    logger: Optional[logging.Logger] = None,
    log_args: bool = False,
    log_result: bool = False
) -> Callable:
    """Decorator for logging function calls.
    
    Args:
        logger: Logger instance for function call logging
        log_args: Whether to log function arguments
        log_result: Whether to log function result
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if logger:
                log_msg = f'Calling {func.__name__}'
                if log_args:
                    log_msg += f' with args={args}, kwargs={kwargs}'
                _log_message(logger, 'DEBUG', log_msg)
            
            result = func(*args, **kwargs)
            
            if log_result:
                _log_message(logger, 'DEBUG', f'{func.__name__} returned: {result}')
            
            return result
        return wrapper
    return decorator

def singleton(cls: Type) -> Type:
    """Decorator for implementing singleton pattern.
    
    Args:
        cls: Class to make singleton
        
    Returns:
        Singleton class
    """
    instances = {}
    
    @functools.wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance

def deprecated(
    reason: str = "This function is deprecated",
    version: str = "unknown"
) -> Callable:
    """Decorator for marking functions as deprecated.
    
    Args:
        reason: Reason for deprecation
        version: Version when function was deprecated
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import warnings
            warnings.warn(
                f'{func.__name__} is deprecated since version {version}: {reason}',
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator
