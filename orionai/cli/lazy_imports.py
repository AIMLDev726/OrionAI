"""
Lazy Import Utilities for OrionAI CLI
====================================

Provides lazy loading of heavy dependencies to improve startup time.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Global cache for lazy loaded modules
_MODULE_CACHE = {}


def lazy_import(module_name: str, package: Optional[str] = None) -> Any:
    """
    Lazy import a module.
    
    Args:
        module_name: Name of the module to import
        package: Package name if importing submodule
        
    Returns:
        The imported module or None if import fails
    """
    cache_key = f"{package}.{module_name}" if package else module_name
    
    if cache_key in _MODULE_CACHE:
        return _MODULE_CACHE[cache_key]
    
    try:
        if package:
            module = __import__(f"{package}.{module_name}", fromlist=[module_name])
            _MODULE_CACHE[cache_key] = getattr(module, module_name)
        else:
            module = __import__(module_name)
            _MODULE_CACHE[cache_key] = module
        
        logger.debug(f"Lazy loaded: {cache_key}")
        return _MODULE_CACHE[cache_key]
        
    except ImportError as e:
        logger.warning(f"Failed to lazy import {cache_key}: {e}")
        _MODULE_CACHE[cache_key] = None
        return None


def get_rich_console():
    """Get Rich console with lazy loading."""
    console = lazy_import('Console', 'rich.console')
    return console() if console else None


def get_rich_panel():
    """Get Rich Panel with lazy loading."""
    return lazy_import('Panel', 'rich.panel')


def get_rich_table():
    """Get Rich Table with lazy loading."""
    return lazy_import('Table', 'rich.table')


def get_rich_markdown():
    """Get Rich Markdown with lazy loading."""
    return lazy_import('Markdown', 'rich.markdown')


def get_rich_syntax():
    """Get Rich Syntax with lazy loading."""
    return lazy_import('Syntax', 'rich.syntax')


def get_rich_progress():
    """Get Rich Progress components with lazy loading."""
    Progress = lazy_import('Progress', 'rich.progress')
    SpinnerColumn = lazy_import('SpinnerColumn', 'rich.progress')
    TextColumn = lazy_import('TextColumn', 'rich.progress')
    
    return Progress, SpinnerColumn, TextColumn


def get_matplotlib():
    """Get matplotlib with lazy loading and proper backend setup."""
    if 'matplotlib' in _MODULE_CACHE:
        return _MODULE_CACHE['matplotlib']
    
    try:
        import matplotlib
        matplotlib.use('Agg')  # Set non-interactive backend
        import matplotlib.pyplot as plt
        
        _MODULE_CACHE['matplotlib'] = plt
        logger.debug("Lazy loaded: matplotlib")
        return plt
        
    except ImportError as e:
        logger.warning(f"Failed to lazy import matplotlib: {e}")
        _MODULE_CACHE['matplotlib'] = None
        return None


def get_duckduckgo_search():
    """Get DuckDuckGo search with lazy loading."""
    return lazy_import('DDGS', 'duckduckgo_search')


def get_beautifulsoup():
    """Get BeautifulSoup with lazy loading."""
    return lazy_import('BeautifulSoup', 'bs4')


def get_requests():
    """Get requests with lazy loading."""
    return lazy_import('requests')


def clear_cache():
    """Clear the module cache."""
    global _MODULE_CACHE
    _MODULE_CACHE.clear()
    logger.info("Module cache cleared")
