from kubernetes import client
from kubernetes.client.rest import ApiException
from primazactl.utils import logger


class AccessReview(object):

    user: str = None
    api_client: client
    full_verbs: [] = None
    service_account_namespace: str = None
    access_namespace: str = None

    def __init__(self, api_client: client,
                 service_account_name: str,
                 service_account_namespace: str,
                 access_namespace: str):
        self.user = f"system:serviceaccount:" \
                        f"{service_account_namespace}:" \
                        f"{service_account_name}"
        self.service_account_namespace = service_account_namespace
        self.access_namespace = access_namespace
        self.api_client = api_client
        self.full_verbs = self.get_full_verbs()

    def split_verbs(self, verbs):
        can_verbs = []
        cannot_verbs = []
        # Based on allowed verbs, determine not allowed verbs
        for verb in self.full_verbs:
            if verb in verbs:
                can_verbs.append(verb)
            else:
                cannot_verbs.append(verb)
        return can_verbs, cannot_verbs

    def check_access(self,
                     policy: client.V1PolicyRule) -> []:

        logger.log_info(f"User: {self.user}")

        # replace empty fields with None to enable for loops
        api_groups = policy.api_groups if policy.api_groups \
            else ["None"]
        resource_names = policy.resource_names if policy.resource_names \
            else ["None"]

        can_reviews = []
        cannot_reviews = []

        for resource in policy.resources:
            for api_group in api_groups:
                if api_group == "None":
                    api_group = None
                for resource_name in resource_names:
                    if resource_name == "None":
                        resource_name = None
                    can_verbs, cannot_verbs = self.split_verbs(policy.verbs)
                    can_reviews.extend(self.__get_access_reviews(
                        can_verbs, resource, resource_name, api_group))
                    # do not save cannot verbs if a resource name is present.
                    # this avoids failures a different policy provides general
                    # access to the resource name.
                    # e.g: one policy provides create deployments access and
                    # another provides delete of only specific deployments
                    if not resource_name and cannot_verbs:
                        cannot_reviews.extend(self.__get_access_reviews(
                            cannot_verbs, resource, resource_name, api_group))

        error_messages = []
        for review in can_reviews:
            error_message = self.__check_access(review, True)
            if error_message:
                error_messages.append(error_message)
        for review in cannot_reviews:
            error_message = self.__check_access(review, False)
            if error_message:
                error_messages.append(error_message)

        logger.log_info(f"Errors: {error_messages}")

        return error_messages

    def __get_access_reviews(self, verbs: [], resource: str,
                             resource_name: str, group: str):

        accesses = []
        for verb in verbs:
            accesses.append(
                client.V1SubjectAccessReviewSpec(
                    resource_attributes=client.V1ResourceAttributes(
                        namespace=self.access_namespace,
                        verb=verb,
                        resource=resource,
                        group=group,
                        name=resource_name,
                    ),
                    user=self.user,
                )
            )
        return accesses

    def __check_access(self, access_review, expect_access):

        status = self.check_user_access(access_review)
        attributes = access_review.resource_attributes
        msg = f"access: {status.allowed}, " \
              f"namespace: {attributes.namespace}, " \
              f"verb: {attributes.verb}, " \
              f"resource: {attributes.resource}, " \
              f"name: {attributes.name}"

        if status.allowed == expect_access:
            logger.log_info(f" PASS: {msg}")
            return None
        else:
            logger.log_error(f"  FAIL: {msg} ")
            return f"[ERROR]: {self.user} access error: {msg}"

    def get_full_verbs(self):
        api_instance = client.AdmissionregistrationV1Api(self.api_client)
        try:
            api_resources = api_instance.get_api_resources()
            return api_resources.resources[0].verbs
        except ApiException as e:
            logger.log_error("Exception when calling "
                             "get_api_resources: %s\n" % e)
            raise e

    def check_user_access(self, access_review: client.V1SubjectAccessReview) \
            -> client.V1SubjectAccessReviewStatus:

        try:
            authv1 = client.AuthorizationV1Api(self.api_client)
            body = client.V1SubjectAccessReview(
                spec=access_review
            )
            response = authv1.create_subject_access_review(body)
            return response.status
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "create_subject_access_review: "
                                 "%s\n" % e)
                raise e
