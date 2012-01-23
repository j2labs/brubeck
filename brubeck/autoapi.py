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

    def uri_for_model(self, model):
        return str(model['_id'])
    
    #def _create_response(self, status_tuple):
    def _generate_response(self, status_data):
        print '_generate_response'
        print '- statuses type:', type(status_data)
        print '- statuses data:', status_data
        print
        #(status_code, data) = status_
        
        if isinstance(status_data, list):
            response = self._add_multi_status(status_data)
        else:
            response = self._add_status(status_data)

        print 'RETURNING:\n', response
        return response

    #def _create_status(self, status, http_200=False, status_dict=None):
    def _add_status(self, status, http_200=False, status_dict=None):
        """Passed a status tuples of the form (status code, processed model),
        it generates the status structure to carry info about the processing.
        """
        print '_add_status'
        print '- status TYPE:', type(status)
        print '- status DATA:', status
        print

        status_code, model = status
        
        data = model.to_json(encode=False)  ### don't double encode

        self.add_to_payload(self._PAYLOAD_DATA, data)

        if http_200:
            status_code = 200

        return self.render(status_code=status_code)

    #def _create_multi_status(self, statuses):
    def _add_multi_status(self, statuses):
        """Passed a list of shields and the state they're in, and creates a
        response
        """
        print '_add_multi_status'
        print '- statuses TYPE:', type(statuses)
        print '- statuses DATA:', statuses
        print

        status_set = []
        #(status_code, data) = statuses

        for status in statuses:
            print 'DATA:', status
            status_code, model = status
            model_data = {
                'status': status_code,
                'id': str(model['_id']),
                'href': self.uri_for_model(model)
            }
            status_set.append(model_data)

        ### encode=False prevents double encoding
        #data = [shield.to_json(encode=False)
        #        for shield in map(lambda t: t[1], statuses)]
        safe_data = [self.model(**datum).to_json(encode=False)
                     for datum in map(lambda t: t[1], statuses)]

        self.add_to_payload(self._PAYLOAD_DATA, safe_data)
        status_code = self._get_status_code(statuses)
        if status_code == 207:
            self.add_to_payload(self._PAYLOAD_MULTISTATUS, status_set)
        
        return self.render(status_code=status_code)

    def _get_status_code(self, statuses):
        """Creates the status code returned at the HTTP level, based on our
        successes and failures. If multiple results are found, a 207 status
        code is used.
        """
        print '_get_status_code'
        print '- statuses t:', type(statuses)
        print '- statuses d:', statuses
        print
        #(status_code, data) = statuses
        kinds =  set(map(lambda t: t[0], statuses))
        print 'KINDS:', kinds
        
        if len(kinds) > 1:
            status_code = 207  # multistatus!
        else:
            print self._UPDATED_CODE

            if self.queries.MSG_FAILED in kinds:
                status_code = self._FAILED_CODE
            elif self.queries.MSG_CREATED in kinds:
                status_code = self._CREATED_CODE
            elif self.queries.MSG_UPDATED in kinds:
                status_code = self._UPDATED_CODE
            elif self.queries.MSG_OK in kinds:
                status_code = self._SUCCESS_CODE
            else:
                status_code = self._SERVER_ERROR

        return status_code

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
            body_data = self._get_body_as_data()
            is_list = isinstance(body_data, list)
            
            # Convert arguments
            (valid, data) = self._convert_item_or_list(body_data, is_list,
                                                       self._convert_to_id)
            print 'Valid: ', valid
            print 'DATA1: ', data

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
                print 'MODELS: ', models
                #response_data = [(200, model) for model in models]
                response_data = models
            else:
                datum_tuple = self.queries.read(data)
                print 'MODELS: ', datum_tuple
                #response_data = [(200, datum[1]) for datum in datum_tuple]
                response_data = datum_tuple
            print 'RESP:', response_data

            # Handle status update
            
            return self._generate_response(response_data)
        
        except FourOhFourException:
            return self.render(status_code=404)
        
    def post(self, ids=""):
        body_data = self._get_body_as_data()
        is_list = isinstance(body_data, list)
        print 'body_data:', body_data

        # Convert arguments
        (valid, data) = self._convert_item_or_list(body_data, is_list,
                                                   self._convert_to_model)

        if not valid:
            return self.render(status_code=400)

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
                return self.render(status_code=400)

            statuses = self.queries.update(data)
            return self._generate_response(statuses)

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
        return self._generate_response(successes, failures)

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
        
