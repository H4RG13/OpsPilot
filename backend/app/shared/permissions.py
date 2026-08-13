from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


ROLE_RANK: dict[Role, int] = {
    Role.MEMBER: 0,
    Role.ADMIN: 1,
    Role.OWNER: 2,
}


def has_minimum_role(actual: Role, required: Role) -> bool:
    return ROLE_RANK[actual] >= ROLE_RANK[required]
