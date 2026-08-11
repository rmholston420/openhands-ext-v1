# planner-medium-08-graphql-migration

## Task summary
Plan the addition of a GraphQL API layer alongside an existing REST API, exposing the same core resources (users, orders, products) but through GraphQL queries, without deprecating the REST endpoints yet.

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Add a GraphQL library dependency (strawberry-graphql or ariadne) integrated with the existing web framework.", "deps": []},
    {"id": "s2", "desc": "Define GraphQL types (User, Order, Product) mirroring the existing REST schemas, using the same Pydantic models as source of truth where possible.", "deps": ["s1"]},
    {"id": "s3", "desc": "Refactor data-fetching logic into a service layer (if not already) so both REST endpoints and GraphQL resolvers call the same underlying functions.", "deps": ["s2"]},
    {"id": "s4", "desc": "Implement GraphQL Query root resolvers: user(id), users(filter), order(id), orders(userId, status), product(id), products(filter), calling into the service layer.", "deps": ["s3"]},
    {"id": "s5", "desc": "Address N+1 query risk by adding DataLoader pattern for relational fields like Order.user and User.orders.", "deps": ["s4"]},
    {"id": "s6", "desc": "Mount the GraphQL endpoint at /graphql alongside existing REST routes; leave REST routes unchanged.", "deps": ["s4"]},
    {"id": "s7", "desc": "Add pytest coverage: query each root resolver, verify DataLoader batching (single DB query for N related items), verify REST endpoints still work.", "deps": ["s5", "s6"]}
  ]
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | 5-7 steps: library → types → service layer → resolvers → DataLoader → mount → tests. Service layer sharing addresses code duplication. DataLoader addresses N+1. REST preserved. |
| 70-89 | GraphQL added but service-layer refactor missing (code duplication between REST and GraphQL) OR DataLoader missing (N+1 waiting to happen). |
| 40-69 | Basic GraphQL surface but tests don't verify REST-still-works OR resolvers hit DB directly without DataLoader. |
| 10-39 | GraphQL mentioned but resolves through calling REST endpoints internally (anti-pattern; double the latency). |
| 0-9 | <3 steps or invalid schema. |

## Notes
Tests planner's handling of a coexisting-APIs migration. Key discriminators: (a) does the plan address code duplication via a service layer? (b) does it address N+1 via DataLoader? (c) does it preserve the existing REST surface?
