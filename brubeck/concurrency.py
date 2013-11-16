### Attempt to setup gevent
try:
    from gevent import monkey
    monkey.patch_all()
    from gevent import pool

    coro_pool = pool.Pool

    def coro_spawn(function, app, message, *a, **kw):
        app.pool.spawn(function, app, message, *a, **kw)

    CORO_LIBRARY = 'gevent'

### Fallback to eventlet
except ImportError:
    try:
        import eventlet
        eventlet.patcher.monkey_patch(all=True)

        coro_pool = eventlet.GreenPool

        def coro_spawn(function, app, message, *a, **kw):
            app.pool.spawn_n(function, app, message, *a, **kw)

        CORO_LIBRARY = 'eventlet'

    ### Blow up if a concurrency library is not found.
    except ImportError:
        raise EnvironmentError('You need to install eventlet or gevent')


def init_pool(pool=None):
    """Handles the generation of a pool and allows for two methods of
    overriding the default behavior: using a custom pool callable or using an
    existing pool.
    """
    if pool is None:
        instance = coro_pool()
    elif callable(pool):
        instance = pool()
    elif pool:
        instance = pool
    else:
        raise ValueError('Unable to initialize coroutine pool')
    return instance
