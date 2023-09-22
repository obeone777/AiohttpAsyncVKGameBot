from dataclasses import dataclass


# @dataclass
# class Message:
#     text: str
#     user_id: int = None


@dataclass
class UpdateMessage:
    from_id: int
    text: str
    id: int
    peer_id: int


@dataclass
class UpdateObject:
    message: UpdateMessage


@dataclass
class Update:
    type: str
    object: UpdateObject
