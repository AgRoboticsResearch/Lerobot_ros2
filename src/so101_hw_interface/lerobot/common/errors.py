class DeviceAlreadyConnectedError(RuntimeError):
    """Raised when an attempt is made to connect an already connected device."""

 
class DeviceNotConnectedError(RuntimeError):
    """Raised when an operation requires an open connection but none exists.""" 