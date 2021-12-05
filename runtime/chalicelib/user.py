from dataclasses import dataclass
from enum import IntEnum
from typing import List


class Theme(IntEnum):
    light = 0
    dark = 1


class Course(IntEnum):
    tracker = 0
    timer = 1
    decreasing = 2


@dataclass
class SmokeEventSettings:
    title: str
    enabled: bool
    sound: str
    vibration: bool


@dataclass
class ChatEventSettings:
    enabled: bool
    sound: str
    vibration: bool


@dataclass
class NotificationSettings:
    smoke_event: SmokeEventSettings
    chat_message: ChatEventSettings


@dataclass
class User:
    id: str
    username: str
    avatar: str
    locale: str
    theme: Theme
    selected_course: Course
    friends: List[str]
    achievements: List[str]
    notification_settings: NotificationSettings

    # course_settings: {}

    def serialize(self) -> dict:
        """this is the way to put everything back into the database"""
        return {
            'PK': f'User#{self.id}',
            'SK': 'Profile',
            'username': self.username,
            'avatar': self.avatar,
            'locale': self.locale,
            'theme': self.theme.value,
            'selected_course': self.selected_course.value,
            'friends': set(self.friends),
            'achievements': set(self.achievements),
            'notification_settings': self.notification_settings.__dict__,
        }

    @classmethod
    def deserialize(cls, database_user):
        """factory"""
        return cls(
            id=database_user['PK'].split('User#')[1],
            username=database_user.get('username', ''),
            avatar=database_user.get('avatar', ''),
            locale=database_user.get('locale', ''),
            theme=Theme(database_user.get('theme', 0)),
            selected_course=Course(database_user.get('selected_course', 0)),
            friends=list(database_user.get('friends', '')),
            achievements=list(database_user.get('achievements', '')),
            notification_settings=NotificationSettings(
                **database_user.get(
                    'notification_settings',
                    {'chat_message': None, 'smoke_event': None}
                ),
            ),
            # course_settings=database_user.get('course_settings'),
        )

    @property
    def json(self) -> dict:
        """json serialized dict"""
        return {
            **self.__dict__,
            **{
                'theme': self.theme.name,
                'selected_course': self.selected_course.name,
                'notification_settings': self.notification_settings.__dict__,
            },
        }
