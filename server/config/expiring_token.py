from datetime import datetime, timedelta

import pytz
from rest_framework import exceptions, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _


class ExpiringTokenAuthentication(TokenAuthentication):

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid token.'))

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

        # This is required for the time comparison
        utc_now = datetime.utcnow()
        utc_now = utc_now.replace(tzinfo=pytz.utc)

        if token.created < utc_now - timedelta(days=1):
            raise exceptions.AuthenticationFailed('Token has expired')

        return token.user, token


class ObtainExpiringAuthToken(ObtainAuthToken):

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        if serializer.is_valid(raise_exception=True):
            tokens = Token.objects.filter(user=serializer.validated_data['user'])
            has_valid_token = False
            utc_now = datetime.utcnow()
            utc_now = utc_now.replace(tzinfo=pytz.utc)
            token = None
            for t in tokens:
                if t.created < utc_now - timedelta(days=1):
                    t.delete()
                else:
                    token = t
                    has_valid_token = True
                    break

            if not has_valid_token:
                token = Token.objects.create(user=serializer.validated_data['user'])

            return Response({'token': token.key})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


obtain_expiring_auth_token = ObtainExpiringAuthToken.as_view()
