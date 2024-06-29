import sentry_sdk


def init_sentry():
    sentry_sdk.init(
        dsn="https://0de14048c02d4d10a00dafb70966c33c@o4507195649294336.ingest.us.sentry.io/4507195650736128",
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )
