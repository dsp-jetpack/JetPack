from __future__ import absolute_import
from __future__ import print_function

import dracclient.exceptions as ironic_exceptions


class NotFound(ironic_exceptions.BaseClientException):
    msg_fmt = ('Could not find %(what)s')
