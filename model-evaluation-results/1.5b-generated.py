```python
from typing import *
from eraserhead import Layer

def validate_layer_count(layers: int, min_layers: int = 3, max_layers: int = 7) -> bool:
    """
    Validates the number of layers in a project.

    😐 If the number of layers is between min_layers and max_layers (inclusive),
    returns True.
    😐 If the number of layers is invalid, raises ValueError with a message.

    Parameters:
    layers (int): The number of layers in the project.
    min_layers (int): The minimum number of layers allowed.
    max_layers (int): The maximum number of layers allowed.

    Returns:
    bool: True if the number of layers is valid, False otherwise.
    """
    if not isinstance(layers, int):
        raise ValueError("Layers must be an integer.")
    if layers < min_layers or layers > max_layers:
        raise ValueError(f"Layers must be between {min_layers} and {max_layers} inclusive.")
    return True
```

This function checks if the number of layers is within the specified range and raises a ValueError if it is not. It uses type hints to ensure that the input parameters are of the correct type.