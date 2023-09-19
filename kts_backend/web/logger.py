import logging
import typing

if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application


def setup_logging(_: "Application") -> None:
    logging.basicConfig(level=logging.INFO)