# Support Chatbot Design

## Goal

Build a customer support chatbot that helps customers get fast, accurate answers to their requests. The chatbot should understand customer questions, search product and support knowledge, respond conversationally, and guide customers to the products, documents, or next actions they need.

The system will expose REST APIs over HTTP and use Server-Sent Events (SSE) for streaming chatbot responses.

## Main Use Cases

- Customer asks about a product, price, availability, variant, policy, or document.
- Customer searches for products or support information.
- Customer continues an existing support conversation.
- Customer receives a streamed chatbot answer instead of waiting for the full response.
- Customer gives feedback on whether an answer was helpful.
- Support/admin users manage products, documents, and indexed knowledge chunks.

## Users

- Customer: asks questions, searches, starts conversations, gives feedback.
- Support agent: reviews conversations and feedback.
- Admin: manages products, documents, prices, and availability data.

## API Style

- Protocol: HTTP
- Style: REST API
- Request/response format: JSON
- Streaming: SSE for chat responses
- Authentication: token-based authentication, such as JWT

## Suggested Endpoints

### Authentication

`POST /auth/login`

Logs in a user and returns an access token.

`POST /auth/register`

Creates a new customer account.

`POST /auth/logout`

Invalidates the current session or token.

### Users

`GET /users/me`

Returns the current authenticated user.

`GET /users/{id}`

Returns user details for support/admin use.

`PATCH /users/{id}`

Updates user profile data.

### Products

`GET /products`

Returns a list of products with filters such as category, keyword, price range, and availability.

`GET /products/{id}`

Returns product details.

`GET /products/{id}/variants`

Returns product variants such as size, color, model, or package.

`GET /products/{id}/availability`

Returns stock and availability information for a product.

### Prices

`GET /prices`

Returns product prices. Supports filters such as product id, variant id, currency, and region.

### Documents

`GET /documents`

Returns support documents, manuals, FAQs, policies, or help-center articles.

`POST /documents`

Creates or uploads a new document.

`GET /documents/{id}`

Returns one document.

`GET /documents/{id}/chunks`

Returns the indexed chunks used for retrieval.

### Conversations

`GET /conversations`

Returns conversations for the current user or for support/admin review.

`POST /conversations`

Creates a new conversation.

`GET /conversations/{id}`

Returns conversation details.

`GET /conversations/{id}/messages`

Returns messages in a conversation.

`POST /conversations/{id}/messages`

Adds a message to an existing conversation.

### Chat

`POST /chat`

Sends a customer message to the chatbot and returns a normal JSON response.

`GET /chat/stream`

Streams the chatbot response using SSE.

Example SSE events:

```text
event: token
data: {"text":"Hello"}

event: source
data: {"document_id":"doc_123","title":"Return Policy"}

event: done
data: {"message_id":"msg_456"}
```

### Search

`GET /search`

Searches products, documents, and support knowledge.

Example query parameters:

```text
/search?q=refund policy&type=documents
/search?q=wireless headphones&type=products
```

### Feedback

`POST /feedback`

Stores customer feedback for a chatbot answer.

Example request:

```json
{
  "conversation_id": "conv_123",
  "message_id": "msg_456",
  "rating": 1,
  "comment": "The answer helped me find the right product."
}
```

## Chat Flow

1. Customer sends a message through `/chat` or `/chat/stream`.
2. System authenticates the user if required.
3. System stores the customer message in the conversation.
4. System searches relevant product data, availability, prices, and document chunks.
5. System sends the retrieved context to the chatbot model.
6. Chatbot generates a helpful answer.
7. If streaming is enabled, tokens are sent to the client using SSE.
8. Final answer is saved as a message.
9. Customer can submit feedback through `/feedback`.

## Retrieval Design

The chatbot should use retrieval augmented generation so answers are grounded in real business data.

Retrieval sources:

- Product catalog
- Product variants
- Availability data
- Price data
- Help-center documents
- Document chunks
- Previous conversation context

The chatbot should cite or reference relevant documents or products when useful.

## Databases

### Relational Database

Use a relational database such as PostgreSQL for structured application data.

Suggested tables:

- `users`
- `products`
- `product_variants`
- `product_availability`
- `prices`
- `documents`
- `document_chunks`
- `conversations`
- `messages`
- `feedback`

### Vector Database

Use a vector database for semantic search over documents and support knowledge.

Suggested options:

- ChromaDB
- pgvector with PostgreSQL
- Pinecone
- Weaviate

For this project, ChromaDB is a good fit if the system remains local or lightweight. PostgreSQL with pgvector is a good fit if structured data and vector search should live in the same database.

### Cache

Use Redis if the system needs faster repeated access to:

- Product availability
- Price lookups
- Chat session state
- Rate limiting data
- Frequently searched documents

## Suggested Data Model

### users

- `id`
- `name`
- `email`
- `password_hash`
- `role`
- `created_at`
- `updated_at`

### products

- `id`
- `name`
- `description`
- `category`
- `brand`
- `status`
- `created_at`
- `updated_at`

### product_variants

- `id`
- `product_id`
- `name`
- `sku`
- `attributes`
- `created_at`
- `updated_at`

### product_availability

- `id`
- `product_id`
- `variant_id`
- `quantity`
- `status`
- `location`
- `updated_at`

### prices

- `id`
- `product_id`
- `variant_id`
- `amount`
- `currency`
- `region`
- `valid_from`
- `valid_to`

### documents

- `id`
- `title`
- `type`
- `source`
- `content`
- `created_at`
- `updated_at`

### document_chunks

- `id`
- `document_id`
- `chunk_index`
- `content`
- `embedding_id`
- `metadata`
- `created_at`

### conversations

- `id`
- `user_id`
- `status`
- `created_at`
- `updated_at`

### messages

- `id`
- `conversation_id`
- `sender`
- `content`
- `sources`
- `created_at`

### feedback

- `id`
- `user_id`
- `conversation_id`
- `message_id`
- `rating`
- `comment`
- `created_at`

## Chatbot Behavior

The chatbot should:

- Answer clearly and politely.
- Ask a follow-up question when the request is unclear.
- Use product, price, availability, and document data before guessing.
- Say when it does not know the answer.
- Suggest relevant products or documents.
- Keep answers short unless the customer asks for more detail.
- Escalate to a human support agent when needed.

The chatbot should not:

- Invent prices, availability, or policies.
- Expose private user data.
- Give unsupported answers when no source exists.
- Continue a conversation that violates safety or business rules.

## SSE Streaming Response Design

The streaming endpoint should return:

- `token` events for partial assistant text.
- `source` events for retrieved documents or products.
- `error` events when generation fails.
- `done` event when the answer is complete.

Headers:

```http
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

## Security

- Use HTTPS in production.
- Store passwords using a secure hash.
- Validate all request inputs.
- Use authentication and authorization for protected endpoints.
- Restrict admin-only endpoints.
- Rate limit `/chat`, `/chat/stream`, `/search`, and `/auth/login`.
- Avoid storing sensitive personal data in model prompts unless required.

## Observability

Track:

- API latency
- Chat response latency
- Retrieval quality
- Failed requests
- SSE disconnects
- User feedback ratings
- Most common customer questions
- Escalation rate

## Success Metrics

- Customers find answers faster.
- Fewer repeated support tickets.
- High helpfulness score from `/feedback`.
- Accurate product and document recommendations.
- Low hallucination rate.
- Stable streaming response performance.

## Future Improvements

- Human support handoff.
- Admin dashboard for conversations and feedback.
- Product recommendation ranking.
- Multi-language support.
- Analytics dashboard.
- Automated document ingestion pipeline.
- Hybrid search combining keyword search and vector search.
