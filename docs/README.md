# T4A MCP Server Documentation

Welcome to the T4A MCP Server documentation. Use the guides below to get started, understand the architecture, and reference API details.

---

## Getting Started

| Guide | Description |
|---|---|
| [Getting Started](getting-started.md) | Prerequisites, local setup, first run |
| [Environment Variables](environment-variables.md) | All configuration options |
| [Deployment](deployment.md) | Docker, production, and update workflow |

## Architecture & Design

| Guide | Description |
|---|---|
| [Architecture](architecture.md) | System overview, data flow, subsystems |
| [Knowledge Base Internals](knowledge-base-internals.md) | RAG pipeline deep-dive: parse, chunk, enrich, embed, retrieve |

## Authentication & Authorization

| Guide | Description |
|---|---|
| [Auth Overview](auth/overview.md) | How JWT validation and RBAC work on the server |
| [Auth End-to-End](auth/end-to-end.md) | Full client + server walkthrough (Next.js + MCP) |
| [Auth0 Setup Guide](auth/setup-guide.md) | Configuring Auth0 API, permissions, and roles |
| [Roles & Permissions](auth/roles-and-permissions.md) | Role definitions and scope assignments |

## API & Tools Reference

| Guide | Description |
|---|---|
| [MCP Tools Reference](api/tools-reference.md) | Every tool: parameters, permissions, behavior |
| [Tools & Permissions Matrix](api/tools-permissions.md) | Tool-to-scope and role-to-scope matrices |
| [Admin API](api/admin-api.md) | Knowledge base admin endpoints (upload, index, search) |
| [Roadmap](api/roadmap.md) | Planned features and implementation priority |

## MetaKocka ERP Reference

| Guide | Description |
|---|---|
| [MetaKocka API Docs](metakocka/) | Full MetaKocka REST API reference (products, documents, partners, warehouse, etc.) |
