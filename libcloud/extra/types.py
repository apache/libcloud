__all__ = [
    'Provider',
]


class Provider(object):
    """
    Defines for each of the supported providers

    Non-Dummy drivers are sorted in alphabetical order. Please preserve this
    ordering when adding new drivers.
    """
    GOOGLE_BQ = 'google'
    GOOGLE_BQ_BILLING = 'google'
