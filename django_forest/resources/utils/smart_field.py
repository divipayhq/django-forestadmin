from django_forest.utils.collection import Collection
from django_forest.utils.schema import Schema


class SmartFieldMixin:
    def _handle_get_method(self, smart_field, item, resource):
        if 'get' in smart_field:
            method = smart_field['get']
            if isinstance(method, str):
                setattr(item, smart_field['field'], getattr(Collection._registry[resource], method)(item))
            elif callable(method):
                setattr(item, smart_field['field'], method(item))

    def _handle_set_method(self, smart_field, instance, value, resource):
        if 'set' in smart_field:
            method = smart_field['set']
            if isinstance(method, str):
                instance = getattr(Collection._registry[resource], method)(instance, value)
            elif callable(method):
                instance = method(instance, value)
        return instance

    def _add_smart_fields(self, item, smart_fields, resource):
        for smart_field in smart_fields:
            self._handle_get_method(smart_field, item, resource)

    def _get_smart_fields_for_request(self, collection, params):

        def is_virtual(field):
            return field.get('is_virtual')

        def include_field(field, required_fields):
            return is_virtual(field) and field['field'] in required_fields

        # Either none provided, or a list of smart field names
        queried_fields = (params or {}).get('fields', {}).get(collection.get('name'))

        if queried_fields is None:
            return [field for field in collection['fields'] if is_virtual(field)]

        return [field for field in collection['fields'] if include_field(field, set(queried_fields))]

    def handle_smart_fields(self, queryset, resource, params, many=False):
        collection = Schema.get_collection(resource)

        # Rather than calculate and then filter out smart fields, we want to ignore them entirely
        smart_fields = self._get_smart_fields_for_request(collection, params)

        # Don't bother adding anything if there are no smart fields
        if smart_fields and many:
            for item in queryset:
                self._add_smart_fields(item, smart_fields, resource)
        elif smart_fields:
            self._add_smart_fields(queryset, smart_fields, resource)

    def update_smart_fields(self, instance, body, resource):
        collection = Schema.get_collection(resource)
        smart_fields = [x for x in collection['fields'] if x['is_virtual']]
        for smart_field in smart_fields:
            if smart_field['field'] in body['data']['attributes'].keys():
                value = body['data']['attributes'][smart_field['field']]
                instance = self._handle_set_method(smart_field, instance, value, resource)
        return instance
