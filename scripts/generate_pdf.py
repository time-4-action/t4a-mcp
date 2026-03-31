from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ── Palette ───────────────────────────────────────────────────────────────────
DARK         = colors.HexColor("#0F172A")
ACCENT       = colors.HexColor("#6366F1")
ACCENT_LIGHT = colors.HexColor("#EEF2FF")
ACCENT_MID   = colors.HexColor("#818CF8")
MID          = colors.HexColor("#334155")
MUTED        = colors.HexColor("#94A3B8")
WHITE        = colors.white
ROW_ALT      = colors.HexColor("#F8FAFC")
TAG_BG       = colors.HexColor("#F1F5F9")
TAG_TXT      = colors.HexColor("#475569")

doc = SimpleDocTemplate(
    "rolesummary.pdf",
    pagesize=A4,
    leftMargin=16*mm, rightMargin=16*mm,
    topMargin=16*mm, bottomMargin=16*mm,
)

W = A4[0] - 32*mm

# ── Styles ────────────────────────────────────────────────────────────────────
def ps(name, **kw):
    return ParagraphStyle(name, **kw)

title_s  = ps("T",  fontName="Helvetica-Bold",    fontSize=20, textColor=WHITE,        alignment=TA_CENTER)
sub_s    = ps("S",  fontName="Helvetica",          fontSize=9,  textColor=colors.HexColor("#A5B4FC"), alignment=TA_CENTER)
h2_s     = ps("H2", fontName="Helvetica-Bold",    fontSize=11, textColor=ACCENT,       spaceBefore=12, spaceAfter=4)
note_s   = ps("N",  fontName="Helvetica-Oblique", fontSize=7.5,textColor=MUTED,        alignment=TA_CENTER)
tool_s   = ps("TL", fontName="Courier-Bold",      fontSize=8.5,textColor=DARK)
desc_s   = ps("D",  fontName="Helvetica",         fontSize=8,  textColor=MID,          leading=11)
tag_s    = ps("TG", fontName="Helvetica",         fontSize=7,  textColor=TAG_TXT)
hdr_s    = ps("HR", fontName="Helvetica-Bold",    fontSize=8,  textColor=WHITE,        alignment=TA_CENTER)
role_s   = ps("RL", fontName="Helvetica-Bold",    fontSize=8.5,textColor=DARK)
chk_s    = ps("CK", fontName="Helvetica-Bold",    fontSize=11, alignment=TA_CENTER)
perm_hdr = ps("PH", fontName="Helvetica-Bold",    fontSize=7.5,textColor=WHITE,        alignment=TA_CENTER)

story = []

# ═══════════════════════════════════════════════════════════════════════════════
# HERO
# ═══════════════════════════════════════════════════════════════════════════════
hero = Table(
    [[Paragraph("Role &amp; Permission Summary", title_s)],
     [Paragraph("MCP Server &nbsp;·&nbsp; MetaKocka AI Agent &nbsp;·&nbsp; Access Control", sub_s)]],
    colWidths=[W]
)
hero.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,-1), DARK),
    ("TOPPADDING",   (0,0), (-1,-1), 14),
    ("BOTTOMPADDING",(0,0), (-1,-1), 14),
    ("LEFTPADDING",  (0,0), (-1,-1), 18),
    ("RIGHTPADDING", (0,0), (-1,-1), 18),
]))
story.append(hero)
story.append(Spacer(1, 10))

# ═══════════════════════════════════════════════════════════════════════════════
# MATRIX
# ═══════════════════════════════════════════════════════════════════════════════
story.append(Paragraph("Role × Permission Matrix", h2_s))

PERMS = [
    "products\n:read",
    "warehouse\n:read",
    "documents\n:read",
    "partners\n:read",
    "delivery:\npricelists\n:read",
]
ROLES = [
    ("mk-viewer",       [True,  True,  True,  True,  False]),
    ("mk-sales_rep",    [True,  True,  True,  True,  True ]),
    ("mk-warehouse_op", [True,  True,  True,  False, True ]),
    ("mk-accountant",   [False, False, True,  False, False]),
    ("mk-manager",      [True,  True,  True,  True,  True ]),
    ("mk-admin",        [True,  True,  True,  True,  True ]),
]

col_w = [36*mm] + [(W - 36*mm) / len(PERMS)] * len(PERMS)

hdr_row = [Paragraph("<b>Role</b>", hdr_s)]
for p in PERMS:
    hdr_row.append(Paragraph(f"<b>{p}</b>", perm_hdr))

mx_data = [hdr_row]
for role, perms in ROLES:
    row = [Paragraph(f"<b>{role}</b>", role_s)]
    for v in perms:
        row.append(Paragraph(
            '<font color="#22C55E"><b>✓</b></font>' if v else '<font color="#CBD5E1">—</font>',
            chk_s
        ))
    mx_data.append(row)

mx = Table(mx_data, colWidths=col_w, rowHeights=[10*mm] + [9*mm]*len(ROLES))
mx.setStyle(TableStyle([
    ("BACKGROUND",    (0,0),  (-1,0),  ACCENT),
    ("ROWBACKGROUNDS",(0,1),  (-1,-1), [WHITE, ROW_ALT]),
    ("BACKGROUND",    (0,1),  (0,-1),  ACCENT_LIGHT),
    ("GRID",          (0,0),  (-1,-1), 0.4, colors.HexColor("#E2E8F0")),
    ("LINEBELOW",     (0,0),  (-1,0),  1.2, ACCENT),
    ("BOX",           (0,0),  (-1,-1), 1,   colors.HexColor("#CBD5E1")),
    ("VALIGN",        (0,0),  (-1,-1), "MIDDLE"),
    ("ALIGN",         (1,0),  (-1,-1), "CENTER"),
    ("ALIGN",         (0,0),  (0,-1),  "LEFT"),
    ("TOPPADDING",    (0,0),  (-1,-1), 5),
    ("BOTTOMPADDING", (0,0),  (-1,-1), 5),
    ("LEFTPADDING",   (0,0),  (0,-1),  8),
    ("RIGHTPADDING",  (0,0),  (-1,-1), 4),
]))
story.append(mx)
story.append(Spacer(1, 10))

# ═══════════════════════════════════════════════════════════════════════════════
# TOOL GROUPS  — each tool gets: name + rich description + "what you get back"
# ═══════════════════════════════════════════════════════════════════════════════
story.append(Paragraph("Tool Reference", h2_s))

# Structure: (group_label, permission, roles_list, [ (tool_name, short_desc, returns_hint) ])
GROUPS = [
    (
        "Products", "products:read",
        ["mk-viewer", "mk-sales_rep", "mk-warehouse_op", "mk-manager", "mk-admin"],
        [
            ("identify_product",
             "Free-text search across the product vector store. Find products by name, code, EAN, or any description keyword. Pass a query string and optionally how many results you want.",
             "Top N matches — name, SKU (code), EAN, relevance score"),

            ("get_product_price",
             "Look up the exact price of a SKU from a named pricelist (e.g. 'RRP 2026'). Returns net price, VAT percentage, VAT amount, and gross price. On failure, lists all available pricelists.",
             "Net price · VAT breakdown · Gross price"),

            ("get_product_pricelists",
             "Returns every configured pricelist and its price for a given SKU in one call. Use this to compare RRP vs. wholesale vs. partner pricing or when you don't know which pricelist to use.",
             "All pricelists + price per pricelist for the SKU"),

            ("list_pricelists",
             "Lists all pricelist names that exist in MetaKocka (not product-specific). Useful before calling get_product_price when the user hasn't specified a pricelist.",
             "Array of pricelist name strings"),

            ("get_product_url",
             "Generates a direct product search URL on patrikinternational.com for a given SKU. Use to give users a clickable link to see the product on the webshop.",
             "URL to patrikinternational.com search for that SKU"),

            ("get_product_variants",
             "Returns the parent product and all its variants — every size, colour, and version — with individual SKUs, EANs, and full names. Also includes detailed product descriptions.",
             "Parent info + list of variant SKUs, EANs, names"),
        ]
    ),
    (
        "Warehouse", "warehouse:read",
        ["mk-viewer", "mk-sales_rep", "mk-warehouse_op", "mk-manager", "mk-admin"],
        [
            ("get_product_stock",
             "Checks live stock for a single SKU in the configured (or a specified) warehouse. Returns available quantity, reserved amount, and microlocation within the warehouse.",
             "Available qty · Reserved qty · Microlocation"),

            ("get_warehouse_list",
             "Fetches all warehouses configured in MetaKocka — their internal mark (used in orders), display name, address, type, and whether they are active or included in stock aggregates.",
             "Warehouse list — mark, name, address, active flag"),

            ("get_warehouse_stock",
             "Bulk cross-warehouse stock query. Filter by warehouse IDs and/or a comma-separated list of SKUs to get stock levels, reservations, and free amounts across all locations at once.",
             "Stock entries per SKU per warehouse — amount, reserved, free"),
        ]
    ),
    (
        "Documents", "documents:read",
        ["mk-viewer", "mk-sales_rep", "mk-warehouse_op", "mk-accountant", "mk-manager", "mk-admin"],
        [
            ("search_documents",
             "Search any MetaKocka document type (sales orders, invoices, purchase orders, warehouse docs, complaints, etc.) with rich filters: date range, partner name/email/VAT, status, product SKU, payment status, and more. Returns paginated IDs and document codes.",
             "Paginated list of mk_id + count_code (+ status if requested)"),

            ("get_document",
             "Fetch a single document in full detail by its internal ID, human-readable code (e.g. 'PP-12345'), or buyer reference. Supports all doc types: orders, invoices, delivery notes, packing lists, complaints, work orders, and more. Slim mode returns key fields; full mode returns every raw field.",
             "Full document — partner, lines, prices, status, dates, tracking"),

            ("get_invoice_attachments",
             "Lists all files (PDFs, scans, etc.) attached to a specific invoice or bill. Works for domestic/foreign sales bills, purchase bills, credit notes, and sales orders. Provide either the internal ID or the document code.",
             "List of attachment file URLs for the invoice"),
        ]
    ),
    (
        "Partners", "partners:read",
        ["mk-viewer", "mk-sales_rep", "mk-manager", "mk-admin"],
        [
            ("get_partner",
             "Search MetaKocka partners (customers and suppliers) by any combination of: internal ID, full or partial name, VAT/tax number, email address, or phone number. Optionally include configured discount rules per product category.",
             "Matching partners — contact details, addresses, optional discounts"),
        ]
    ),
    (
        "Delivery", "delivery:pricelists:read",
        ["mk-sales_rep", "mk-warehouse_op", "mk-manager", "mk-admin"],
        [
            ("get_delivery_service_pricelists",
             "Fetches all carrier price lists configured in MetaKocka (e.g. GLS Slovenija, GLS Italy). For each service, returns transport cost, cash-on-delivery cost, return cost, and pricing tiers by package weight bracket.",
             "Carrier list — transport / COD / return costs by weight tier"),
        ]
    ),
    (
        "No permission required", "open to all authenticated users",
        ["all roles"],
        [
            ("discover_document_filters",
             "Returns the exact filter 'type' strings accepted by search_documents for a given doc_type. Call this before searching when you are unsure which filter keys are valid — avoids trial-and-error API errors.",
             "Map of doc_type to available filter types and their value format"),

            ("get_document_url",
             "Generates a direct MetaKocka back-office UI link for any document (order, invoice, delivery note, packing list, transfer order, etc.) using its internal mk_id. Paste the URL in a browser to open the document directly.",
             "Deep-link URL into the MetaKocka UI"),
        ]
    ),
]

for group, perm, roles, tools in GROUPS:
    # Group header bar
    gh = Table([[
        Paragraph(f"<b>{group}</b>",
                  ps("gh", fontName="Helvetica-Bold", fontSize=10, textColor=WHITE)),
        Paragraph(perm,
                  ps("gp", fontName="Courier",        fontSize=8,  textColor=colors.HexColor("#C7D2FE"), alignment=TA_CENTER)),
        Paragraph(", ".join(roles),
                  ps("gr", fontName="Helvetica",      fontSize=7.5,textColor=colors.HexColor("#E0E7FF"))),
    ]], colWidths=[28*mm, 52*mm, W-80*mm])
    gh.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), MID),
        ("TOPPADDING",   (0,0), (-1,-1), 7),
        ("BOTTOMPADDING",(0,0), (-1,-1), 7),
        ("LEFTPADDING",  (0,0), (0,0),   10),
        ("LEFTPADDING",  (1,0), (-1,-1), 8),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(gh)

    # Tool rows
    for i, (tname, tdesc, treturn) in enumerate(tools):
        bg = WHITE if i % 2 == 0 else ROW_ALT
        cell = Table([[
            Paragraph(tname, tool_s),
            Paragraph(tdesc, desc_s),
            Table([[Paragraph("Returns", ps("rl", fontName="Helvetica-Bold", fontSize=6.5,
                                            textColor=ACCENT_MID))],
                   [Paragraph(treturn, ps("rv", fontName="Helvetica", fontSize=7,
                                          textColor=TAG_TXT, leading=9))]],
                  colWidths=[44*mm]),
        ]], colWidths=[38*mm, W-82*mm, 44*mm])
        cell.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,-1), bg),
            ("VALIGN",       (0,0), (-1,-1), "TOP"),
            ("TOPPADDING",   (0,0), (-1,-1), 7),
            ("BOTTOMPADDING",(0,0), (-1,-1), 7),
            ("LEFTPADDING",  (0,0), (0,-1),  10),
            ("LEFTPADDING",  (1,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("LINEBELOW",    (0,0), (-1,-1), 0.3, colors.HexColor("#E2E8F0")),
            ("LINEBEFORE",   (2,0), (2,-1),  0.5, colors.HexColor("#E2E8F0")),
        ]))
        story.append(cell)

    story.append(Spacer(1, 7))

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#E2E8F0")))
story.append(Spacer(1, 4))
story.append(Paragraph(
    "mk-admin holds <b>admin:all</b> — bypasses every permission check on the MCP server.  "
    "Generated 2026-03-24.",
    note_s
))

doc.build(story)
print("Done: rolesummary.pdf")
