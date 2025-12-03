"""
Librarian module for document analysis in case conferences.

The Librarian is a non-deliberating agent that:
1. Pre-conference: Analyzes uploaded files + query, generates a contextual summary
2. During deliberation: Answers agent queries about document contents
"""

from src.librarian.service import LibrarianService

__all__ = ["LibrarianService"]

