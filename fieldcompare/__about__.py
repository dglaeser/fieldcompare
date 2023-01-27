# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Version information for fieldcompare"""
from importlib import metadata

try:
    __version__ = metadata.version("fieldcompare")
except Exception:
    __version__ = "unknown"
