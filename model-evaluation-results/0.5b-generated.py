```python
from typing import *
from collections import *

def validate_layer_count(layers: int, min_layers: int = 3, max_layers: int = 7) -> bool:
    """
    Validates the layer count of a layer stack.

    Parameters:
    layers (int): The number of layers in the stack.
    min_layers (int): The minimum number of layers allowed.
    max_layers (int): The maximum number of layers allowed.

    Returns:
    bool: True if layers is between min_layers and max_layers (inclusive), False otherwise.
    Raises ValueError with a message if layers is invalid.
    """
    if not isinstance(layers, int):
        raise ValueError("Layers must be an integer.")
    if layers < min_layers or layers > max_layers:
        raise ValueError(f"Layers must be between {min_layers} and {max_layers} inclusive.")
    return True
```

This function checks if the provided `layers` parameter is within the specified range (inclusive) and raises a `ValueError` if it is not. The function also includes type hints for better type checking and documentation.