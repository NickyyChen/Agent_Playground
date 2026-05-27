# -*- coding: utf-8 -*-
"""
Skill 注册系统 —— Demo 21
"""

from dataclasses import dataclass, field
from typing import Callable, Optional
from abc import ABC, abstractmethod


@dataclass
class SkillMeta:
    name: str
    description: str
    category: str = "general"
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)


class Skill(ABC):
    meta: SkillMeta

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    @abstractmethod
    def execute(self, **kwargs) -> dict:
        ...


class SkillRegistry:
    """Skill 注册中心"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills = {}
        return cls._instance

    def register(self, skill: Skill):
        self._skills[skill.meta.name] = skill

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def list_all(self) -> list[Skill]:
        return list(self._skills.values())

    def search(self, query: str) -> list[Skill]:
        q = query.lower()
        return [s for s in self._skills.values()
                if q in s.meta.name.lower()
                or q in s.meta.description.lower()]

    def execute(self, name: str, **kwargs) -> dict:
        skill = self.get(name)
        if not skill:
            return {"success": False, "error": f"Skill {name} 未注册"}
        return skill.execute(**kwargs)


def skill_decorator(name: str = None, **meta):
    """@skill 装饰器"""
    def _wrap(cls):
        if meta:
            cls.meta = SkillMeta(name=name or cls.__name__, **meta)
        SkillRegistry().register(cls())
        return cls
    return _wrap
