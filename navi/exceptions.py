"""Navi exceptions module."""
from typing import List


class NaviException(Exception):
    """Represents the base class for all types of Navi exception."""


class NaviInitException(NaviException):
    """NaviException to be raised when a Navi subclass cannot be initialized."""


class NaviConfigException(NaviException):
    """NaviException to be raised when Navi's configured with invalid values."""

    def __init__(self, missing_configs: List["NaviConfigEntry"]):
        super().__init__(f"Invalid Navi configurations: {missing_configs}.")
