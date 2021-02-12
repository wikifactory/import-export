from gql import gql

file_mutation = gql(
    """
    mutation File($fileInput: FileInput) {
        file (fileData: $fileInput) {
            file {
                id
                path
                mimeType
                filename
                size
                completed
                cancelled
                isCopy
                slug
                spaceId
                uploadUrl
            }

            userErrors {
                message
                key
                code
            }

        }
    }
    """
)

operation_mutation = gql(
    """
    mutation Operation($operationData: OperationInput) {
        operation(operationData: $operationData) {
            project {
                id
            }
        }
    }
    """
)

complete_file_mutation = gql(
    """
    mutation CompleteFile($fileInput: FileInput) {
    file(fileData: $fileInput) {
        file {
            id
            path
            url
            completed
        }
        userErrors {
            message
            key
            code
        }
    }
}
    """
)

commit_contribution_mutation = gql(
    """
    mutation CommitContribution($commitData: CommitInput) {
        commit(commitData: $commitData) {
            project {
                id
                inSpace {
                    id
                    whichTypes
                }
                contributionCount
            }
            userErrors {
                message
                key
                code
            }
        }
    }
    """
)

project_query = gql(
    """query q($space:String, $slug:String) {
        project(space:$space, slug:$slug) {
            result {
                id
                space {
                    id
                }
                inSpace {
                    id
                }
            }
            userErrors {
              message
              key
              code
            }
        }
    }"""
)