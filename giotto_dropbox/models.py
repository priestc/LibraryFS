import base64
import pickle

from giotto import get_config
from giotto.contrib.auth.models import User
from giotto.control import Redirection
from giotto.primitives import LOGGED_IN_USER
from django.db import models

from dropbox import session as dropbox_session

Base = get_config("Base")

class DropboxRequestToken(models.Model):
    """
    Table for storing request token as part of th authentication process.
    """
    user = models.ForeignKey(User, primary_key=True)
    secret = models.CharField(max_length=128)
    key = models.CharField(max_length=128)

    @classmethod
    def create(cls, user, token):
        session = get_config("db_session")
        session.query(cls).filter(cls.user==user).delete()
        self = cls(user=user, secret=token.secret, key=token.key)
        session.add(self)
        session.commit()
        return self

    @classmethod
    def get(cls, user):
        """
        This function should only be called after the user has clicked on the
        authorize URL and has confirmed the authorization.
        """
        s = get_config("db_session")
        ret = s.query(cls).filter(cls.user==user).first()
        return dropbox_session.OAuthToken(key=ret.key, secret=ret.secret)

def make_callback_model(callback):
    """
    Construct the function that will be fed into the callback program.
    This function handles the generic work on the giotto_dropbox auth process.
    """

    def dropbox_api_callback(uid, oauth_token, user=LOGGED_IN_USER):
        """
        Handles the request that the user makes given by the dropbox API as part of
        the oauth process. This is the callback used in oauth1.
        """
        sess = get_dropbox_session()
        request_token = DropboxRequestToken.get(user)
        access_token = sess.obtain_access_token(request_token)
        if callback:
            return callback(user, access_token)

    return dropbox_api_callback

def get_dropbox_authorize_url(user, callback_scheme='http'):
    """
    Get the url for sending the user to authenticate with dropbox.
    """
    sess = get_dropbox_session()
    request_token = sess.obtain_request_token()
    url = "%s://%s/dropbox/oauth1callback" % (callback_scheme, get_config("domain"))
    DropboxRequestToken.create(user, request_token)
    return sess.build_authorize_url(request_token, oauth_callback=url)

def get_dropbox_session(token_key=None, token_secret=None):
    sess = dropbox_session.DropboxSession(
        get_config('dropbox_app_key'), get_config('dropbox_app_secret'),
        get_config('dropbox_app_type')
    )
    
    if token_secret and token_key:
        sess.set_token(token_key, token_secret)

    return sess