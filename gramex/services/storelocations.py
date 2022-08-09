import gramex.data
import json
import time
from uuid import uuid4
from typing import Union


class StoreLocation(object):
    def __init__(self, url: str, table: str, columns: dict = None, **kwargs: dict):
        '''Set up a data store. Used by gramex.yaml `storelocations:` service.

        Examples:
            >>> store = StoreLocation(url='sqlite:///x.db', table='x', columns={'y': 'text'})
            >>> store.insert(y='hello')

        Parameters:
            url: sqlalchemy URL
            table: table name
            columns: column names, with values are SQL types, or dicts
            **kwargs: passed to `sqlalchemy.create_engine()`.

        `columns` can be SQL type strings (e.g. `"REAL"` or `"VARCHAR(10)"`) or a dict with keys:

        - `type` (str), e.g. `"VARCHAR(10)"`
        - `default` (str/int/float/bool), e.g. `"none@example.org"`
        - `nullable` (bool), e.g. `False`
        - `primary_key` (bool), e.g. `True` -- used only when creating new tables
        - `autoincrement` (bool), e.g. `True` -- used only when creating new tables

        The parameters are the same as [gramex.data.alter][].
        '''
        self.store = {'url': url, 'table': table, 'columns': columns, **kwargs}
        gramex.data.alter(**self.store)

    def insert(self, **kwargs):
        gramex.data.insert(**self.store, args={key: [val] for key, val in kwargs.items()})


class OTPStoreLocation(StoreLocation):
    def __init__(self, size: int = None, **kwargs: dict):
        '''Set up one time OTP/API Key store.

        Examples:
            >>> store = OTPStoreLocation(url='sqlite:///x.db', table='x', columns={'y': 'text'})
            >>> token = store.insert(user={'id': 'x'}, email='y', expire=timestamp)
            >>> row = store.filter(token=token)
            >>> row = store.pop(token=token)

        Parameters:
            size: length of the token in characters. `None` means full hash string
            **kwargs: Other [StoreLocation][gramex.services.storelocations.StoreLocation]
                parameters, e.g. `url`, `table`, etc.
        '''
        self.size = size
        super().__init__(**kwargs)

    def insert(
            self,
            user: Union[str, dict],
            email: str = None,
            expire: float = None,
            size: int = None) -> str:
        '''Create a token (OTP/API Key), insert into database, and return the token.

        Parameters:
            user: User object to store against token
            email: An identifier that's EMailAuth, DBAuth, etc use to store the email ID to send
                forgotten passwords to. BaseHandler sets this to `OTP` or `Key` when creating
                an OTP or API key
            expire: Time when this token expires, in seconds since epoch (e.g. `time.time()`)
            size: length of the token in characters. `None` means full hash string

        Returns:
            Generated token
        '''
        token = uuid4().hex[:self.size if size is None else size]
        super().insert(token=token, user=json.dumps(user), email=email, expire=expire)
        return token

    def filter(self, token: str) -> Union[dict, None]:
        '''Returns the row with the user object matching a token. None if no match.

        Parameters:
            token: Token (OTP / API Key / Forgot password token) to fetch

        Returns:
            Dict with user object, email, expire and token. None if no match
        '''
        rows = gramex.data.filter(**self.store, args={'token': [token]})
        if len(rows) > 0:
            row = rows.iloc[0].to_dict()
            row['user'] = json.loads(row['user'])
            if row['expire'] > time.time():
                return row
        return None

    def pop(self, token: str) -> Union[dict, None]:
        '''Returns the row with the user object matching a token, and deletes it.

        This is typically used by the forgot password OTP mechanism.

        Parameters:
            token: Token (OTP / API Key / Forgot password token) to fetch

        Returns:
            Dict with user object, email, expire and token. None if no match
        '''
        row = self.filter(token)
        if row is not None:
            gramex.data.delete(**self.store, id=['token'], args={'token': [token]})
        return row


storetypes = {
    'default': StoreLocation,
    'otp': OTPStoreLocation,
}
