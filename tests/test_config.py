"""
Test configuration for Harithma POS
"""

import os
import tempfile

class TestConfig:
    """Test configuration class"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    def __init__(self):
        # Use in-memory SQLite database for testing
        self.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    def cleanup(self):
        """Clean up - no file cleanup needed for in-memory database"""
        pass