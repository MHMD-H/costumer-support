"""Closed dashboard authorization values and the Task 7 role matrix."""

from enum import StrEnum


class Role(StrEnum):
    STORE_OWNER = "store_owner"
    ADMIN = "admin"
    MARKETING_MANAGER = "marketing_manager"
    TEAM_MEMBER = "team_member"


class Permission(StrEnum):
    VIEW_USERS = "view_users"
    MANAGE_USERS = "manage_users"
    VIEW_PERMISSIONS = "view_permissions"
    MANAGE_PERMISSIONS = "manage_permissions"
    VIEW_TENANT = "view_tenant"
    MANAGE_TENANT = "manage_tenant"
    VIEW_PRODUCTS = "view_products"
    MANAGE_PRODUCTS = "manage_products"
    VIEW_ORDERS = "view_orders"
    VIEW_SALES = "view_sales"
    VIEW_CAMPAIGNS = "view_campaigns"
    MANAGE_CAMPAIGNS = "manage_campaigns"
    VIEW_DOCUMENTS = "view_documents"
    UPLOAD_DOCUMENTS = "upload_documents"
    MANAGE_DOCUMENTS = "manage_documents"
    VIEW_CONVERSATIONS = "view_conversations"
    CREATE_CONVERSATIONS = "create_conversations"
    USE_DASHBOARD_CHAT = "use_dashboard_chat"
    SEARCH_KNOWLEDGE = "search_knowledge"
    SUBMIT_FEEDBACK = "submit_feedback"
    USE_AGENT_TOOLS = "use_agent_tools"
    CONNECT_SHOPIFY_STORE = "connect_shopify_store"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.STORE_OWNER: frozenset(Permission),
    Role.ADMIN: frozenset({
        Permission.VIEW_USERS, Permission.MANAGE_USERS, Permission.VIEW_PERMISSIONS,
        Permission.MANAGE_PERMISSIONS, Permission.VIEW_TENANT, Permission.MANAGE_TENANT,
        Permission.VIEW_PRODUCTS, Permission.MANAGE_PRODUCTS, Permission.VIEW_ORDERS,
        Permission.VIEW_SALES, Permission.VIEW_CAMPAIGNS, Permission.VIEW_DOCUMENTS,
        Permission.UPLOAD_DOCUMENTS, Permission.MANAGE_DOCUMENTS,
        Permission.VIEW_CONVERSATIONS, Permission.CREATE_CONVERSATIONS,
        Permission.USE_DASHBOARD_CHAT, Permission.SEARCH_KNOWLEDGE,
        Permission.SUBMIT_FEEDBACK, Permission.USE_AGENT_TOOLS,
    }),
    Role.MARKETING_MANAGER: frozenset({
        Permission.VIEW_USERS, Permission.VIEW_PRODUCTS, Permission.MANAGE_PRODUCTS,
        Permission.VIEW_ORDERS, Permission.VIEW_SALES, Permission.VIEW_CAMPAIGNS,
        Permission.MANAGE_CAMPAIGNS, Permission.VIEW_DOCUMENTS,
        Permission.UPLOAD_DOCUMENTS, Permission.MANAGE_DOCUMENTS,
        Permission.VIEW_CONVERSATIONS, Permission.CREATE_CONVERSATIONS,
        Permission.USE_DASHBOARD_CHAT, Permission.SEARCH_KNOWLEDGE,
        Permission.SUBMIT_FEEDBACK, Permission.USE_AGENT_TOOLS,
    }),
    Role.TEAM_MEMBER: frozenset({
        Permission.VIEW_USERS, Permission.VIEW_PRODUCTS,
        Permission.USE_DASHBOARD_CHAT, Permission.SEARCH_KNOWLEDGE,
        Permission.USE_AGENT_TOOLS,
    }),
}


ROLE_GRANTABLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.TEAM_MEMBER: frozenset({
        Permission.MANAGE_PRODUCTS, Permission.VIEW_ORDERS, Permission.VIEW_SALES,
        Permission.VIEW_CAMPAIGNS, Permission.MANAGE_CAMPAIGNS,
        Permission.CREATE_CONVERSATIONS, Permission.SUBMIT_FEEDBACK,
    }),
}
