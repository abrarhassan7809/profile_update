import uuid


def create_token():
    token = str(uuid.uuid1())

    return token
