from request_handling import JSONMessageHandler, FourOhFourException

from dictshield.base import ShieldException

import ujson as json


class AutoAPIBase(JSONMessageHandler):
    model = None
    queries = None

    #_STATUS_CREATED = 201  # self._CREATED_CODE
    #_STATUS_UPDATED = 200  # self._UPDATED_CODE
    #_STATUS_FAILED = 400    # self._FAILED_CODE
    #_STATUS_ERROR = 500    # self._SERVER_ERROR

    _PAYLOAD_DATA = 'data'
    _PAYLOAD_STATUS = 'status'
    _PAYLOAD_MULTISTATUS = 'multistatus'

    ###
    ### Content Handling
    ###

    ### Section TODO:
    ### * investigate unicode handling bug in ujson

    def _get_body_as_data(self):
        """Returns the body data based on the content_type requested by the
        client.
        """
        if self.message.content_type == 'application/json':
            one_or_many = self.message.body
        else:
            one_or_many = self.get_argument('data')
        return one_or_many

    def _convert_to_id(self, datum):
        """`datum` in this function is an id that needs to be validated and
        converted to it's native type.
        """
        try:
            converted = self.model.id.validate(datum)
            return (True, converted)
        except ShieldException, se:
            return (False, se)

    def _convert_to_model(self, datum):
        """Handles the details of converting some data into a model or
        information about why data was invalid.
        """
        try:
            converted = self.model(**datum)
            converted.validate()
            return (True, converted)
        except ShieldException, se:
            return (False, se)

    ###
    ### Status Generation
    ###

    def uri_for_model(self, model):
        return str(model.id)    
    
    def _create_response(self, status_tuple):
        print '_create_response'
        print '- statuses t:', type(status_tuple)
        print '- statuses d:', status_tuple
        print

        (status_code, data) = status_tuple
        
        if isinstance(data, list):
            response = self._create_multi_status(data)
        else:
            response = self._create_status(data)
        return response

    def _create_status(self, status, http_200=False, status_dict=None):
        """Passed a status tuples of the form (status code, processed model),
        it generates the status structure to carry info about the processing.
        """
        print '_create_status'
        print '- status t:', type(status)
        print '- status d:', status
        print
        
        status_code, model = status
        
        data = model.to_json(encode=False)  ### don't double encode

        self.add_to_payload(self._PAYLOAD_DATA, data)

        if http_200:
            status_code = 200

        return self.render(status_code=status_code)

    def _create_multi_status(self, statuses):
        """Passed a list of shields and the state they're in, and creates a
        response
        """
        print '_create_multi_status'
        print '- statuses t:', type(statuses)
        print '- statuses d:', statuses
        print

        status_set = []

        for status in statuses:
            status_code, model = status
            model_data = {
                'status': status_code,
                'id': str(model.id),
                'href': self.uri_for_shield(model)
            }
            status_set.append(model_data)

        ### encode=False prevents double encoding
        data = [shield.to_json(encode=False)
                for shield in map(lambda t: t[1], statuses)]

        self.add_to_payload(self._PAYLOAD_DATA, data)
        status_code = self._get_status_code(statuses)
        if status_code == 207:
            self.add_to_payload(self._PAYLOAD_MULTISTATUS, status_set)
        
        return self.render(status_code=status_code)

    def _get_status_code(self, statuses):
        """Creates the status code we should be returning based on our
        successes and failures
        """
        print '_get_status_code'
        print '- statuses t:', type(statuses)
        print '- statuses d:', statuses
        print
        kinds =  set(map(lambda t: t[0], statuses))
        
        if len(kinds) > 1:
            status_code = 207  # multistatus!
        else:
            if 'failed' in kinds:
                status_code = 400
            elif 'created' in kinds:
                status_code = 201
            else:
                status_code = 200
        return status_code

    ###
    ### Validation
    ###

    def _pre_alter_validation(self):
        """Creates the shield objcts and validates that they're in the right
        format if they're not, adds the error list to the payload
        """
        print '_pre_alter_validation'

        model_or_models = self._get_model_from_body()

        def check_invalid(shield):
            try:
                shield.validate()
                return True, shield
            except ShieldException:
                error_dict = {
                    'status_code': 422,
                    'id': shield.id,
                    'error': 'Bad data',
                    'href': self.uri_for_shield(shield)
                }
                return False, error_dict

        if not isinstance(model_or_models, list):
            valid, data = check_invalid(model_or_models)
            if valid:
                ### Shield, no error
                return data, None
            else:
                self.add_to_payload(self._PAYLOAD_STATUS, json.dumps(data))
                ### No data, error
                return None, data
        else:
            validated_tuples = map(check_invalid, model_or_models)
            error_shields = []
            valid_shields = []
            for valid, data in validated_tuples:
                if valid:
                    valid_shields.append(data)
                else:
                    error_shields.append(data)
                    
            self.add_to_payload(self._PAYLOAD_MULTISTATUS,
                                json.dumps(error_shields))

            ### Shields, error data
            return valid_shields, error_shields

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
    

    def get(self, ids=""):
        """Handles read - either with a filter (ids) or a total list
        """
        try:
            ### Setup environment
            body_data = self._get_body_as_data()
            is_list = isinstance(body_data, list)
            print 'DATA ::', body_data
            
            def converter(idd):
                if idd:
                    new_id = self._convert_to_id(idd)
                    print 'NEW ID:', new_id
                    return new_id

            (valid, data) = self._convert_item_or_list(body_data, is_list,
                                                       converter)
            print 'Valid: ', valid
            print 'DATA1: ', data

            if is_list:
                valid_ids = list()
                errors_ids = list()
                for status in data:
                    (is_valid, idd) = status
                    if is_valid:
                        valid_ids.append(idd)
                    else:
                        error_ids.append(idd)
                print 'QUERIES multi:', self.queries
                models = self.queries.read(valid_ids)
                response_data = [(200, model) for model in models]
            else:
                print 'QUERIES single:', self.queries
                model = self.queries.read(data)
                response_data = (200, model)
            print 'RESP:', response_data
            return self._create_response(response_data)
        
        except FourOhFourException:
            return self.render(status_code=404)
        
    def post(self, ids=""):
        """Handles create if ids is missing, else updates the items.

        Items should be represented as objects inside a list, pegged to the
        global object - the global object name defaults to data but can be
        changed by overriding the _get_shields_from_postbody method

        e.g.
        {
            'data' : [
                {
                    'mysamplekey1': somesamplevalue,
                    'mysamplekey2': somesamplevalue,
                },
                {
                    'mysamplekey1': somesamplevalue,
                    'mysamplekey2': somesamplevalue,
                },
            ]
        }

        This keeps the interface constant if you're passing a single item or a
        list of items. We only want to deal with sequences!
        """
        shields, invalid = self._pre_alter_validation()

        if invalid:
            return self.render(status_code=400)

        if ids == "":
            statuses = self.create(shields)
            return self._create_response(statuses)
        else:
            if isinstance(shields, list):
                items = ids
            else:
                items = ids.split(self.application.MULTIPLE_ITEM_SEP)

            ### TODO: add informative error message
            if not self.url_matches_body(items, shields):
                return self.render(status_code=400)

            statuses = self.update(shields)
            return self._create_response(statuses)

    def put(self, ids):
        """Follows roughly the same logic as `post` but exforces that the items
        must already exist.
        """
        shields, invalid = self._pre_alter_validation()

        if invalid:
            return self.render(status_code=400)

        ### TODO: add informative error message
        items = ids.split(self.application.MULTIPLE_ITEM_SEP)

        if not self.url_matches_body(items, shields):
            return self.render(status_code=400)

        successes, failures = self.update(shields)
        return self._create_response(successes, failures)

    def delete(self, ids):
        """ Handles delete for 1 or many items. Since this doesn't take a
        postbody, and just item ids, pass those on directly to destroy
        """
        item_ids = ids.split(self.application.MULTIPLE_ITEM_SEP)

        if ids:
            try:
                statuses = self.destroy(item_ids)
            except FourOhFourException:
                return self.render(status_code=404)

        if isinstance(statuses, list):
            list_status = self._get_status_code(statuses)

            status = []
            for status_code, shield in statuses:
                if isinstance(shield, dict):
                    status.append({'status': status_code, 'id': shield['_id']})
                else:
                    status.append({'status': status_code, 'id': shield.id})
            if list_status == 207:
                self.add_to_payload(self._PAYLOAD_MULTISTATUS, json.dumps(status))
        else:
            status_code, sheild = statuses
            status = {'status': status_code, 'id': shield.id}
            self.add_to_payload(self._PAYLOAD_STATUS, json.dumps(status))

        return self.render(status_code=status_code)

    ###
    ### CRUD operations
    ###

    ### Section TODO:
    ### * Pagination
    ### * Hook in authentication
    ### * Key filtering (owner / public)
    ### * Make model instantiation an option
