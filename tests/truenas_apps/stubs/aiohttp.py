class ClientError(Exception):
    pass


class ClientConnectorError(ClientError):
    pass


class WSServerHandshakeError(ClientError):
    pass
