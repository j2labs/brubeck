from request_handling import JSONMessageHandler, FourOhFourException

from dictshield.base import ShieldException

import ujson as json


class AutoAPIBase(JSONMessageHandler):
    """AutoAPIBase generates a JSON REST API for you. *high five!*
    I also read this link for help in propertly defining the behavior of HTTP
    PUT and POST: http://stackoverflow.com/questions/630453/put-vs-post-in-rest
    """
    
    model = None
    queries = None

    _PAYLOAD_DATA = 'data'
    _PAYLOAD_STATUS = 'status'
    _PAYLOAD_MULTISTATUS = 'multistatus'

    ###
    ### Input Handling
    ###

    ### Section TODO:
    ### * investigate unicode handling bug in ujson

    def _get_body_as_data(self):
        """Returns the body data based on the content_type requested by the
        client.
        """
        if self.message.content_type == 'application/json':
            body = self.message.body
        else:
            body = self.get_argument('data')
        if body:
            body = json.loads(body)
        return body

    def _convert_to_id(self, datum):
        """`datum` in this function is an id that needs to be validated and
        converted to it's native type.
        """
        try:
            converted = self.model.id.validate(datum)  # interface might change
            return (True, converted)
        except Exception, e:
            return (False, e)

    def _convert_to_model(self, datum):
        """Handles the details of converting some data into a model or
        information about why data was invalid.
        """
        try:
            converted = self.model(**datum)
            converted.validate()
            return (True, converted)
        except Exception, e:
            return (False, e)

    def _convert_item_or_list(self, body_data, is_list, converter):
        """This function takes the output of a _get_body* function and checks
        it against the model for inputs.

        In some cases this is a list of IDs or in others it's a complete
        document. The details of this are controlled by the `converter`
        function, provided as the last argument.

        If a list is provided, the output is a boolean and a list of
        two-tuples, each containing a boolean and the converted datum, as
        provided by the `converter` function.

        If a single item is provided as input the converter function is called
        and the output is returned.
        """
        if not body_data:
            return (True, None)

        if is_list:
            results = list()
            all_valid = True
            for idd in body_data:
                (is_valid, data) = converter(idd)
                if not is_valid:
                    all_valid = False
                results.append((is_valid, data))
            return (all_valid, results)
        else:
            (is_valid, data) = converter(body_data)
            return (is_valid, data)
    
    ###
    ### Output Processing
    ###

    def _crud_to_http(self, crud_status):
        """Translates the crud status returned by a `QuerySet` into the status
        used for HTTP.
        """
        if self.queries.MSG_FAILED == crud_status:
            status_code = self._FAILED_CODE
        elif self.queries.MSG_CREATED == crud_status:
            status_code = self._CREATED_CODE
        elif self.queries.MSG_UPDATED == crud_status:
            status_code = self._UPDATED_CODE
        elif self.queries.MSG_OK == crud_status:
            status_code = self._SUCCESS_CODE
        elif len(crud_status) == 0:
            status_code = self._SUCCESS_CODE
        else:
            status_code = self._SERVER_ERROR
        return status_code

    def _make_presentable(self, datum):
        """This function takes either a model instance or a dictionary
        representation of some model and returns a dictionary one safe for
        transmitting as payload.
        """
        if isinstance(datum, dict):
            iid = str(datum.get('_id'))
            instance = self.model(**datum).to_json(encode=False)
        else:
            iid = str(datum.id)
            instance = datum.to_json(encode=False)

        data = self.model.make_json_ownersafe(instance, encode=False)
        data['id'] = iid  ### External representations use id field 'id'

        return data

    def _add_status(self, datum, status_code):
        """Passed a status tuples of the form (status code, processed model),
        it generates the status structure to carry info about the processing.
        """
        datum[self._STATUS_CODE] = status_code
        status_msg = self._response_codes.get(status_code,
                                              str(status_code))
        datum[self._STATUS_MSG] = status_msg
        return datum

    def _parse_crud_datum(self, crud_datum):
        """Parses the result of some crud operation into an HTTP-ready
        datum instead.
        """
        (crud_status, datum) = crud_datum
        data = self._make_presentable(datum)
        http_status_code = self._crud_to_http(crud_status)
        data = self._add_status(data, http_status_code)
        return (http_status_code, data)

    def _generate_response(self, status_data):
        """Parses crud data and generates the full HTTP response. The idea here
        is to translate the results of some crud operation into something
        appropriate for HTTP.

        `status_data` is ambiguously named because it might be a list and it
        might be a single item. This will likely be altered when the crud
        interface's ambiguous functions go away too.
        """
        ### Case 1: `status_data` is a list
        if isinstance(status_data, list):
            ### Aggregate all the statuses and collect the data items in a list
            statuses = set()
            data_list = list()
            for status_datum in status_data:
                (http_status_code, data) = self._parse_crud_datum(status_datum)
                data_list.append(data)
                statuses.add(http_status_code)

            ### If no statuses are found, just use 200
            if len(statuses) == 0:
                http_status_code = self._SUCCESS_CODE
            ### If more than one status, use HTTP 207
            elif len(statuses) > 1:
                http_status_code = self._MULTI_CODE
            ### If only one status is there, use it for the HTTP status
            else:
                http_status_code = statuses.pop()

            self.add_to_payload(self._PAYLOAD_DATA, data_list)
            return self.render(status_code=http_status_code)
        
        ### Case 2: `status_data` is a single item
        else:
            (http_status_code, data) = self._parse_crud_datum(status_data)

            self.add_to_payload(self._PAYLOAD_DATA, data)
            return self.render(status_code=http_status_code)

    ###
    ### Validation
    ###

    def url_matches_body(self, ids, shields):
        """ We want to make sure that if the request asks for a specific few
        resources, those resources and only those resources are in the body
        """
        if not ids:
            return True

        if isinstance(shields, list):
            for item_id, shield in zip(ids, shields):
                if item_id != str(shield.id):  # enforce a good request
                    return False
        else:
            return ids != str(shields)

        return True

    ###
    ### HTTP methods
    ###

    ### Section TODO:
    ### * Cleaner handling of list vs single
    ### * Clean handling of how status info is or isn't used
    ### * Check handling of multiple listed ids

    def get(self, ids=""):
        """Handles read - either with a filter (ids) or a total list
        """
        
        try:
            ### Setup environment
            is_list = isinstance(ids, list)
            
            # Convert arguments
            (valid, data) = self._convert_item_or_list(ids, is_list,
                                                       self._convert_to_id)

            # CRUD stuff
            if is_list:
                valid_ids = list()
                errors_ids = list()
                for status in data:
                    (is_valid, idd) = status
                    if is_valid:
                        valid_ids.append(idd)
                    else:
                        error_ids.append(idd)
                models = self.queries.read(valid_ids)
                response_data = models
            else:
                datum_tuple = self.queries.read(data)
                response_data = datum_tuple
            # Handle status update
            return self._generate_response(response_data)
        
        except FourOhFourException:
            return self.render(status_code=self._NOT_FOUND)
        
    def post(self, ids=""):
        body_data = self._get_body_as_data()
        is_list = isinstance(body_data, list)

        # Convert arguments
        (valid, data) = self._convert_item_or_list(body_data, is_list,
                                                   self._convert_to_model)

        if not valid:
            return self.render(status_code=self._FAILED_CODE)

        ### If no ids, we attempt to create the data
        if ids == "":
            statuses = self.queries.create(data)
            return self._generate_response(statuses)
        else:
            if isinstance(ids, list):
                items = ids
            else:
                items = ids.split(self.application.MULTIPLE_ITEM_SEP)

            ### TODO: add informative error message
            if not self.url_matches_body(items, data):
                return self.render(status_code=self._FAILED_CODE)

            statuses = self.queries.update(data)
            return self._generate_response(statuses)

    def put(self, ids=""):
        """Follows roughly the same logic as `post` but exforces that the items
        must already exist.
        """
        body_data = self._get_body_as_data()
        is_list = isinstance(body_data, list)

        # Convert arguments
        (valid, data) = self._convert_item_or_list(body_data, is_list,
                                                   self._convert_to_model)

        if not valid:
            return self.render(status_code=self._FAILED_CODE)

        ### TODO: add informative error message
        items = ids.split(self.application.MULTIPLE_ITEM_SEP)

        if not self.url_matches_body(items, data):
            return self.render(status_code=self._FAILED_CODE)

        crud_statuses = self.queries.update(data)
        return self._generate_response(crud_statuses)

    def delete(self, ids=""):
        """ Handles delete for 1 or many items. Since this doesn't take a
        postbody, and just item ids, pass those on directly to destroy
        """
        body_data = self._get_body_as_data()
        is_list = isinstance(body_data, list)
        crud_statuses = list()

        # Convert arguments
        (valid, data) = self._convert_item_or_list(body_data, is_list,
                                                   self._convert_to_model)

        if not valid:
            return self.render(status_code=400)

        if ids:
            item_ids = ids.split(self.application.MULTIPLE_ITEM_SEP)
            try:
                crud_statuses = self.queries.destroy(item_ids)
            except FourOhFourException:
                return self.render(status_code=self._NOT_FOUND)
            
        return self._generate_response(crud_statuses)
        
