# # server.py
# import uuid
# import logging


# def get_request_id():
#     if getattr(flask.g, 'request_id', None):
#         return flask.g.request_id

#     new_uuid = uuid.uuid4().hex[:10]
#     flask.g.request_id = new_uuid

#     return new_uuid

# class RequestIdFilter(logging.Filter):
#     # This is a logging filter that makes the request ID available for use in
#     # the logging format. Note that we're checking if we're in a request
#     # context, as we may want to log things before Flask is fully loaded.
#     def filter(self, record):
#         record.req_id = get_request_id() if flask.has_request_context() else ''
#         return True


# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

# # The StreamHandler responsible for displaying
# # logs in the console.
# sh = logging.StreamHandler()
# sh.addFilter(RequestIdFilter())

# # Note: the "req_id" param name must be the same as in
# # RequestIdFilter.filter
# log_formatter = logging.Formatter(
#     fmt="%(module)s: %(asctime)s - %(levelname)s - ID: %(req_id)s - %(message).1000s"
# )
# sh.setFormatter(log_formatter)
# logger.addHandler(sh)

# app = Flask(__name__)


# def configure_log():
