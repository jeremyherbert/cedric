# cedric custom exceptions
class CedricError(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, msg):
        self.msg = msg
    
class ValidationError(CedricError):
    """
    Error raised on a validation failure
    """
    pass
    
class ArgumentError(CedricError):
    """
    Raised on an unknown or an invalid argument
    """
    pass
    
class MalformedTestError(CedricError):
    """
    Raised on an incorrectly formatted test
    """
    pass
    
class HttpError(CedricError):
    """
    Raised when Cedric is unable to connect to the server
    """
    pass