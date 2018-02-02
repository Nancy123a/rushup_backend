import decimal
import json

# print(json.dumps(i, cls=DecimalEncoder))
# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


def replace_decimals(obj):
    if isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = replace_decimals(obj[i])
        return obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = replace_decimals(v)
        return obj
    elif isinstance(obj, decimal.Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


def parse_dynamo_item(item):
    resp = {}
    if type(item) is str:
        return item
    for key,struct in item.iteritems():
        if type(struct) is str:
            if key == 'I':
                return int(struct)
            else:
                return struct
        else:
            for k,v in struct.iteritems():
                if k == 'L':
                    value = []
                    for i in v:
                        value.append(parse_dynamo_item(i))
                elif k == 'S':
                    value = str(v)
                elif k == 'I':
                    value = int(v)
                elif k == 'M':
                    value = {}
                    for a,b in v.iteritems():
                        value[a] = parse_dynamo_item(b)
                else:
                    key = k
                    value = parse_dynamo_item(v)

                resp[key] = value

    return resp


def dict_to_item(raw):
    if type(raw) is dict:
        resp = {}
        for k,v in raw.iteritems():
            if type(v) is str:
                resp[k] = {
                    'S': v
                }
            elif type(v) is int:
                resp[k] = {
                    'I': str(v)
                }
            elif type(v) is dict:
                resp[k] = {
                    'M': dict_to_item(v)
                }
            elif type(v) is list:
                resp[k] = []
                for i in v:
                    resp[k].append(dict_to_item(i))

        return resp
    elif type(raw) is str:
        return {
            'S': raw
        }
    elif type(raw) is int:
        return {
            'I': str(raw)
        }
