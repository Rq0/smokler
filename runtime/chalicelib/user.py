import json
from dataclasses import dataclass
from typing import List
from enum import Enum

from chalicelib.json import EnhancedJSONEncoder


class Theme(Enum):
    light = 1
    dark = 2


@dataclass
class NotificationSettings:
    smoke_event: {}
    chat_message: {}


@dataclass
class User:
    uuid: str
    name: str
    avatar: str
    locale: str
    friends: List[str]
    theme: Theme
    achievements: List[str]
    # notification_settings: NotificationSettings
    # selected_course: str
    # course_settings: {}

    def serialize(self) -> dict:
        return {
            'PK': f'User#{self.uuid}',
            'SK': f'Profile',
            **self
        }

    @classmethod
    def deserialize(cls, database_user):
        return cls(
            uuid=database_user.get('uuid'),
            name=database_user.get('name'),
            avatar=database_user.get('avatar'),
            locale=database_user.get('locale'),
            friends=database_user.get('friends'),
            theme=Theme[database_user.get('theme')],
            achievements=database_user.get('achievements'),
            # notification_settings=database_user.get('notification_settings'),
            # selected_course=database_user.get('selected_course'),
            # course_settings=database_user.get('course_settings'),
        )

    @property
    def json(self):
        return json.dumps(self, cls=EnhancedJSONEncoder)
