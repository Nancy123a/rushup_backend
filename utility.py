import decimal


class DecimalEncoder(json.JSONEncoder):
    def _iterencode(self, o, markers=None):
        if isinstance(o, decimal.Decimal):
            # wanted a simple yield str(o) in the next line,
            # but that would mean a yield on the line with super(...),
            # which wouldn't work (see my comment below), so...
            return (str(o) for o in [o])
        return super(DecimalEncoder, self)._iterencode(o, markers)


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
