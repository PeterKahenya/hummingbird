import mongoengine
from requests import get
import models
import schemas
import bson
from mongoengine import Q

async def get_obj_or_404(model: models.BaseDocument, id: str):
    try:
        return model.objects.get(id=bson.ObjectId(id))
    except model.DoesNotExist:
        raise model.DoesNotExist(f"{model.__name__} with id {id} not found")
    except bson.errors.InvalidId:
        raise bson.errors.InvalidId(f"Invalid id {id}")
    except Exception as e:
        raise e
    
async def get_obj_or_None(model: models.BaseDocument, id: str):
    try:
        return model.objects.get(id=bson.ObjectId(id))
    except model.DoesNotExist:
        return None
    except bson.errors.InvalidId:
        raise bson.errors.InvalidId(f"Invalid id {id}")
    except Exception as e:
        raise e

def validate_params(model, params):
    valid_fields = model._fields.keys()
    for key in params.keys():
        field_name = key.split("__")[0]  # Extract field name before lookup suffix
        if field_name not in valid_fields:
            raise AttributeError(f"Invalid field {field_name} for model {model.__name__}")
    
async def filter_objs(model: models.BaseDocument, params: dict, sort_by: str = "created_at,desc"):
    try:
        validate_params(model, params)
        sort_by, order = sort_by.split(",")
        return model.objects.filter(**params).order_by(f"{'-' if order == 'desc' else ''}{sort_by}").all()
    except AttributeError as e:
        raise e
    except Exception as e:
        raise e
    
async def search_objs(model: models.BaseDocument, query: str):
    try:
        q_objects = []
        for field, field_type in model._fields.items():
            if isinstance(field_type, (mongoengine.StringField, mongoengine.EmailField)):
                q_objects.append(Q(**{f"{field}__icontains": query}))
        if not q_objects:
            return model.objects.none()
        combined_q = q_objects[0]
        for q in q_objects[1:]:
            combined_q = combined_q | q
        return model.objects.filter(combined_q).all()
    except Exception as e:
        raise e

async def create_obj(model: models.BaseDocument, obj_in: schemas.BaseModel):
    try:
        obj = model()
        for field, field_type in model._fields.items():
            if isinstance(field_type, mongoengine.ReferenceField):
                if hasattr(obj_in, field):
                    setattr(obj, field, model._fields[field].document_type.objects.get(id=bson.ObjectId(getattr(obj_in, field).id)))
                    obj_in.__delattr__(field)
            elif isinstance(field_type, mongoengine.ListField) and isinstance(field_type.field, mongoengine.ReferenceField):
                if hasattr(obj_in, field):
                    setattr(obj, field, [model._fields[field].field.document_type.objects.get(id=bson.ObjectId(item.id)) for item in getattr(obj_in, field)])
                    obj_in.__delattr__(field)
            else:
                if hasattr(obj_in, field):
                    setattr(obj, field, getattr(obj_in, field))
        obj.save()
        return obj
    except Exception as e:
        raise e
    
async def create_staff(staff_create: schemas.StaffCreate, company: models.Company):
    try:
        staff = models.Staff()
        staff.company = company
        staff.user = models.User.objects.get(id=bson.ObjectId(staff_create.user.id))
        staff_create.__delattr__("user")
        for field, field_type in models.Staff._fields.items():
            if hasattr(staff_create, field):
                setattr(staff, field, getattr(staff_create, field))
        staff.save()
        staff.reload()
        return staff
    except Exception as e:
        raise e

async def create_code(code_create: schemas.PayrollCodeCreate, company: models.Company):
    try:
        code = models.PayrollCode()
        code.company = company
        for field, field_type in models.PayrollCode._fields.items():
            if hasattr(code_create, field):
                setattr(code, field, getattr(code_create, field))
        code.save()
        code.reload()
        return code
    except Exception as e:
        raise e
    
async def create_computation(computation_create: schemas.ComputationCreate, company: models.Company):
    try:
        computation = models.Computation()
        computation.company = company
        computation.generated_by = models.User.objects.get(id=bson.ObjectId(computation_create.generated_by.id))
        computation_create.__delattr__("generated_by")
        for field, field_type in models.Computation._fields.items():
            if hasattr(computation_create, field):
                setattr(computation, field, getattr(computation_create, field))
        computation.save()
        computation.reload()
        return computation
    except Exception as e:
        raise e
    
async def update_obj(model: models.BaseDocument, id: str, obj_in: schemas.BaseModel):
    try:
        obj = await get_obj_or_404(model, id)
        for field, field_type in model._fields.items():
            if isinstance(field_type, mongoengine.ReferenceField) and hasattr(obj_in, field) and getattr(obj_in, field):
                if hasattr(obj_in, field):
                    setattr(obj, field, model._fields[field].document_type.objects.get(id=bson.ObjectId(getattr(obj_in, field).id)))
                    obj.save()
                    obj_in.__delattr__(field)
            elif isinstance(field_type, mongoengine.ListField) and isinstance(field_type.field, mongoengine.ReferenceField) and hasattr(obj_in, field):
                if hasattr(obj_in, field):
                    setattr(obj, field, [model._fields[field].field.document_type.objects.get(id=bson.ObjectId(item.id)) for item in getattr(obj_in, field)])
                    obj.save()
                    obj_in.__delattr__(field)
        obj.update(**obj_in.model_dump(exclude_unset=True))
        obj.reload()
        return obj
    except Exception as e:
        raise e
    
async def delete_obj(model: models.BaseDocument, id: str):
    try:
        obj = await get_obj_or_404(model, id)
        obj.delete()
        return None
    except Exception as e:
        raise e
    
async def paginate(
        model: models.BaseDocument, 
        schema: schemas.BaseModel, 
        q: str = None,
        page: int = 1, 
        size: int = 10, 
        sort_by: str = "created_at,desc",
        **params
        ) -> schemas.ListResponse:
    try:
        if q:
            # TODO: Search needs filtering to handle searches within constrained domains like staff in a company
            data = await search_objs(model, q)
        elif params and len(params) > 0:
            data = await filter_objs(model=model,params=params,sort_by=sort_by)
        else:
            data = await filter_objs(model=model, params={},sort_by=sort_by)
        
        offset = (page - 1) * size
        total = len(data)
        paginated_items = data[offset:offset + size]
        paginated_items = [schema.model_validate(item.to_dict()) for item in paginated_items]
        return schemas.ListResponse(**{
            "total": total,
            "page": page,
            "size": size,
            "data": paginated_items
        })
    except Exception as e:
        raise e