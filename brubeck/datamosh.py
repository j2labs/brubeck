from dictshield.document import EmbeddedDocument
from dictshield.fields.base import UUIDField, StringField


from brubeck.timekeeping import MillisecondField


"""The purpose of the datamosh model is to provide Mixins for building data
models and data handlers.  In it's current state, it provides some helpers
for handling HTTP request arguments that map members of a data model.

I wanted the name of this module to indicate that it's a place to put request
handling code alongside the models they're intended for handling.  It's a mosh
pit of data handling logic.
"""


###
### Helper Functions
###

def get_typed_argument(arg_name, default, handler, type_fun):
    """Simple short hand for handling type detection of arguments.
    """
    value = handler.get_argument(arg_name, default)
    try:
        value = type_fun(value)
    except:
        value = default
    return value


###
### Ownable Data Mixins
###

class OwnedModelMixin(EmbeddedDocument):
    """This class standardizes the approach to expressing ownership of data
    """
    owner_id = UUIDField(required=True)
    owner_username = StringField(max_length=30, required=True)
    class Meta:
        mixin = True


class OwnedHandlerMixin:
    """This mixin supports receiving an argument called `owner`, intended to
    map to the `owner_username` field in the Model above.
    """
    def get_owner_username(self, default_usernam=None):
        owner_username = get_typed_argument('owner', default_username, self,
                                            str)
        return owner_username


###
### Streamable Data Handling
###

class StreamedModelMixin(EmbeddedDocument):
    """This class standardizes the way streaming data is handled by adding two
    fields that can be used to sort the list.
    """
    created_at = MillisecondField(default=0)
    updated_at = MillisecondField(default=0)
    class Meta: 
        mixin = True


class StreamedHandlerMixin:
    """Provides standard definitions for paging arguments
    """
    def get_stream_offset(self, default_since=0):
        """This function returns some offset for use with either `created_at`
        or `updated_at` as provided by `StreamModelMixin`.
        """
        since = get_typed_argument('since', default_since, self, long)
        return since

    def get_paging_arguments(self, default_page=0, default_count=25,
                             max_count=25):
        """This function checks for arguments called `page` and `count`. It
        returns a tuple either with their value or default values.

        `max_count` may be used to put a limit on the number of items in each
        page. It defaults to 25, but you can use `max_count=None` for no limit.
        """
        page = get_typed_argument('page', default_page, self, int)
        count = get_typed_argument('count', default_count, self, int)
        if max_count and count > max_count:
            count = max_count

        default_skip = page * count
        skip = get_typed_argument('skip', default_skip, self, int)

        return (page, count, skip)
