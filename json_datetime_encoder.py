import json
import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime.datetime, datetime.time, datetime.date)):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)