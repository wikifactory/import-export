from gql import gql

repository_zip_query = gql(
    """
    query RepositoryZip($space: String, $slug: String) {
        project(space: $space, slug: $slug) {
            result {
                id
                slug
                contributionUpstream {
                    id
                    zipArchiveUrl
                }
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
