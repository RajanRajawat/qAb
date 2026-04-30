from bson import ObjectId

#- String Operations
def strip_string(s: str):
    if isinstance(s, str):
        return s.strip()
    return s


def ensure_object_id(value):
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    return ObjectId(value)


def object_id_match(value):
    object_id = ensure_object_id(value)
    return {"$in": [object_id, str(object_id)]}















    
