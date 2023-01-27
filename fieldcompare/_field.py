# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Class that represents a field of values"""

from dataclasses import dataclass
from ._numpy_utils import Array


@dataclass
class Field:
    """Represents a field with a name and an array of values"""

    name: str
    values: Array
