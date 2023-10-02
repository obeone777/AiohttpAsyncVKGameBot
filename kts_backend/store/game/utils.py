from kts_backend.store.game.text_constants import id_constant, text_about_game


def about_game() -> str:
    return text_about_game


def chat_id_converter(chat_id: int) -> int:
    return chat_id - id_constant
