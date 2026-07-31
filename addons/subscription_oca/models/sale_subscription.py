# Copyright 2023 Domatix - Carlos Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError

logger = logging.getLogger(__name__)


class SaleSubscription(models.Model):
    _name = "sale.subscription"
    _description = "الاشتراك"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    color = fields.Integer("مؤشر اللون")
    name = fields.Char(
        compute="_compute_name",
        store=True,
        translate=True,
        string="الاسم",
    )
    sequence = fields.Integer("التسلسل")
    company_id = fields.Many2one(
        "res.company",
        "الشركة",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner", required=True, string="الشريك", index=True
    )
    fiscal_position_id = fields.Many2one(
        "account.fiscal.position",
        string="المركز الضريبي",
        domain="[('company_id', '=', company_id)]",
        check_company=True,
    )
    active = fields.Boolean(default=True, string="نشط")
    template_id = fields.Many2one(
        comodel_name="sale.subscription.template",
        required=True,
        string="قالب الاشتراك",
    )
    code = fields.Char(
        string="المرجع",
        default=lambda self: self.env["ir.sequence"].next_by_code("sale.subscription"),
    )
    in_progress = fields.Boolean(string="قيد التنفيذ", default=False)
    recurring_rule_boundary = fields.Boolean(
        string="الحدود", compute="_compute_rule_boundary", store=True
    )
    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist", required=True, string="قائمة الأسعار"
    )
    recurring_next_date = fields.Date(string="تاريخ الفاتورة التالية", default=date.today())
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="الوكيل التجاري",
        default=lambda self: self.env.user.id,
    )
    # NEW FIELD: المندوب (Salesperson) - auto-filled from partner's user_id
    salesperson_id = fields.Many2one(
        comodel_name="res.users",
        string="المندوب",
        default=lambda self: self.env.user.id,
        tracking=True,
    )
    date_start = fields.Date(string="تاريخ البدء", default=date.today())
    date = fields.Date(
        string="تاريخ الانتهاء",
        compute="_compute_rule_boundary",
        store=True,
        readonly=False,
    )
    description = fields.Text(string="الوصف", translate=True)
    sale_order_id = fields.Many2one(
        comodel_name="sale.order", string="أمر البيع الأصلي"
    )
    terms = fields.Text(
        string="الشروط والأحكام",
        compute="_compute_terms",
        store=True,
        readonly=False,
        translate=True,
    )
    invoice_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="subscription_id",
        string="الفواتير",
    )
    sale_order_ids = fields.One2many(
        comodel_name="sale.order",
        inverse_name="order_subscription_id",
        string="الطلبات",
    )
    recurring_total = fields.Monetary(
        compute="_compute_total", string="السعر المتكرر", store=True
    )
    amount_tax = fields.Monetary(compute="_compute_total", string="مبلغ الضرائب", store=True)
    amount_total = fields.Monetary(compute="_compute_total", string="الإجمالي", store=True)
    tag_ids = fields.Many2many(comodel_name="sale.subscription.tag", string="العلامات")
    image = fields.Binary("الصورة", related="user_id.image_512", store=True)
    journal_id = fields.Many2one(comodel_name="account.journal", string="السجل")
    currency_id = fields.Many2one(
        related="pricelist_id.currency_id",
        depends=["pricelist_id"],
        store=True,
        ondelete="restrict",
        string="العملة",
    )

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        stage_ids = stages.search([], order=stages._order)
        return stage_ids

    stage_id = fields.Many2one(
        comodel_name="sale.subscription.stage",
        string="المرحلة",
        tracking=True,
        group_expand="_read_group_stage_ids",
        store=True,
    )
    stage_type = fields.Selection(
        related="stage_id.type",
    )
    sale_subscription_line_ids = fields.One2many(
        comodel_name="sale.subscription.line",
        inverse_name="sale_subscription_id",
        string="بنود الاشتراك",
    )
    sale_order_ids_count = fields.Integer(
        compute="_compute_sale_order_ids_count", string="أوامر البيع"
    )
    account_invoice_ids_count = fields.Integer(
        compute="_compute_account_invoice_ids_count", string="عدد الفواتير"
    )
    close_reason_id = fields.Many2one(
        comodel_name="sale.subscription.close.reason", string="سبب الإغلاق"
    )
    crm_team_id = fields.Many2one(comodel_name="crm.team", string="فريق المبيعات")
    to_renew = fields.Boolean(default=False, string="للتجديد")

    @api.model
    def cron_subscription_management(self):
        today = date.today()
        for subscription in self.search([], order="recurring_next_date asc"):
            subscription = subscription.with_company(subscription.company_id)
            if subscription.in_progress:
                if (
                        subscription.recurring_next_date <= today
                        and subscription.sale_subscription_line_ids
                ):
                    try:
                        subscription.generate_invoice()
                    except Exception:
                        logger.exception("Error on subscription invoice generate")
                if (
                        not subscription.recurring_rule_boundary
                        and subscription.date <= today
                ):
                    subscription.close_subscription()
            elif (
                    subscription.date_start <= today and subscription.stage_id.type == "pre"
            ):
                subscription.action_start_subscription()
                subscription.generate_invoice()

    @api.depends("sale_subscription_line_ids")
    def _compute_total(self):
        for record in self:
            recurring_total = amount_tax = 0.0
            for order_line in record.sale_subscription_line_ids:
                recurring_total += order_line.price_subtotal
                amount_tax += order_line.amount_tax_line_amount
            record.update(
                {
                    "recurring_total": recurring_total,
                    "amount_tax": amount_tax,
                    "amount_total": recurring_total + amount_tax,
                }
            )

    @api.depends("template_id", "code")
    def _compute_name(self):
        for record in self:
            template_code = record.template_id.code if record.template_id.code else ""
            code = record.code if record.code else ""
            slash = "/" if template_code and code else ""
            record.name = f"{template_code}{slash}{code}"

    @api.depends("template_id", "date_start")
    def _compute_rule_boundary(self):
        for record in self:
            if record.template_id.recurring_rule_boundary == "unlimited":
                record.date = False
                record.recurring_rule_boundary = True
            else:
                if record.date_start:
                    record.date = (
                            relativedelta(months=+record.template_id.recurring_rule_count)
                            + record.date_start
                    )
                    record.recurring_rule_boundary = False
                else:
                    record.date = False

    @api.depends("template_id")
    def _compute_terms(self):
        for record in self:
            record.terms = record.template_id.description

    @api.onchange("template_id", "date_start")
    def _onchange_template_id(self):
        if self.date_start and self.template_id:
            self._calculate_recurring_next_date(self.date_start)

    def _calculate_recurring_next_date(self, start_date):
        """Calculate the next recurring date based on start date and template"""
        if self.template_id and start_date:
            # Ensure start_date is a date object
            if isinstance(start_date, str):
                start_date = fields.Date.to_date(start_date)
            if start_date:
                type_interval = self.template_id.recurring_rule_type
                interval = int(self.template_id.recurring_interval)
                # Add the interval to the start date
                self.recurring_next_date = start_date + relativedelta(
                    **{type_interval: interval}
                )

    @api.onchange("partner_id")
    def onchange_partner_id(self):
        self.pricelist_id = self.partner_id.property_product_pricelist
        # Auto-fill salesperson from partner's user_id
        if self.partner_id and self.partner_id.user_id:
            self.salesperson_id = self.partner_id.user_id.id
            # Also auto-set crm_team_id based on the salesperson
            self._onchange_salesperson_id()

    @api.onchange("partner_id", "company_id")
    def onchange_partner_id_fpos(self):
        self.fiscal_position_id = (
            self.env["account.fiscal.position"]
            .with_company(self.company_id)
            ._get_fiscal_position(self.partner_id)
        )

    @api.onchange("salesperson_id")
    def _onchange_salesperson_id(self):
        """Auto-set crm_team_id based on salesperson's team"""
        if self.salesperson_id:
            # Get the sales team from the salesperson
            team = self.env['crm.team'].search([
                ('user_id', '=', self.salesperson_id.id)
            ], limit=1)
            if team:
                self.crm_team_id = team.id
            else:
                # If no team found, try to get from user's default team
                user_team = self.salesperson_id.sale_team_id
                if user_team:
                    self.crm_team_id = user_team.id

    def action_start_subscription(self):
        self.close_reason_id = False
        in_progress_stage = self.env["sale.subscription.stage"].search(
            [("type", "=", "in_progress")], limit=1
        )
        self.stage_id = in_progress_stage

        # When starting subscription, set recurring_next_date from date_start
        if self.date_start and self.template_id:
            self._calculate_recurring_next_date(self.date_start)

    def action_close_subscription(self):
        return {
            "view_type": "form",
            "view_mode": "form",
            "res_model": "close.reason.wizard",
            "type": "ir.actions.act_window",
            "target": "new",
            "res_id": False,
        }

    def close_subscription(self, close_reason_id=False):
        self.ensure_one()
        self.recurring_next_date = False
        closed_stage = self.env["sale.subscription.stage"].search(
            [("type", "=", "post")], limit=1
        )
        self.write(
            {
                "close_reason_id": close_reason_id,
                "stage_id": closed_stage,
            }
        )

    def _prepare_sale_order(self, line_ids=False):
        self.ensure_one()
        return {
            "partner_id": self.partner_id.id,
            "fiscal_position_id": self.fiscal_position_id.id,
            "date_order": datetime.now(),
            "payment_term_id": self.partner_id.property_payment_term_id.id,
            "user_id": self.user_id.id,
            "origin": self.name,
            "order_line": line_ids,
        }

    def _prepare_account_move(self, line_ids):
        self.ensure_one()
        # FIX: Use date_start as invoice date
        invoice_date = self.date_start or self.recurring_next_date or date.today()

        values = {
            "partner_id": self.partner_id.id,
            "invoice_date": invoice_date,
            "invoice_payment_term_id": self.partner_id.property_payment_term_id.id,
            "invoice_origin": self.name,
            "invoice_user_id": self.user_id.id,
            "partner_bank_id": self.company_id.partner_id.bank_ids[:1].id,
            "invoice_line_ids": line_ids,
            "subscription_id": self.id,
        }
        if self.journal_id:
            values["journal_id"] = self.journal_id.id
        return values

    def create_invoice(self):
        if not self.env["account.move"].has_access("create"):
            try:
                self.check_access("write")
            except AccessError:
                return self.env["account.move"]
        line_ids = []
        for line in self.sale_subscription_line_ids:
            line_values = line._prepare_account_move_line()
            line_ids.append(Command.create(line_values))
        invoice_values = self._prepare_account_move(line_ids)
        invoice_id = (
            self.env["account.move"]
            .sudo()
            .with_context(default_move_type="out_invoice", journal_type="sale")
            .create(invoice_values)
        )
        return invoice_id

    def create_sale_order(self):
        if not self.env["sale.order"].has_access("create"):
            try:
                self.check_access("write")
            except AccessError:
                return self.env["sale.order"]
        line_ids = []
        for line in self.sale_subscription_line_ids:
            line_values = line._prepare_sale_order_line()
            line_ids.append(Command.create(line_values))
        values = self._prepare_sale_order(line_ids)
        order_id = self.env["sale.order"].sudo().create(values)
        self.write({"sale_order_ids": [Command.link(order_id.id)]})
        return order_id

    def generate_invoice(self):
        invoice_number = ""
        message_body = ""
        msg_static = self.env._("تم إنشاء فاتورة بالمرجع")
        if self.template_id.invoicing_mode in ["draft", "invoice", "invoice_send"]:
            invoice = self.create_invoice()
            if self.template_id.invoicing_mode != "draft":
                invoice.action_post()
                mail_template = self.template_id.invoice_mail_template_id
                self.env["account.move.send"]._generate_and_send_invoices(
                    invoice, mail_template=mail_template, sending_methods=["email"]
                )
                invoice_number = invoice.name
                message_body = (
                    f"<b>{msg_static}</b> "
                    f"<a href=# data-oe-model=account.move data-oe-id={invoice.id}>"
                    f"{invoice_number}"
                    "</a>"
                )

        if self.template_id.invoicing_mode == "sale_and_invoice":
            order_id = self.create_sale_order()
            order_id.action_confirm()
            order_id.action_lock()
            new_invoice = order_id._create_invoices()
            new_invoice.action_post()
            new_invoice.invoice_origin = order_id.name + ", " + self.name
            invoice_number = new_invoice.name
            message_body = (
                    "<b>%s</b> <a href=# data-oe-model=account.move data-oe-id=%d>%s</a>"
                    % (msg_static, new_invoice.id, invoice_number)
            )
        if not invoice_number:
            invoice_number = self.env._("للتحقق")
            message_body = f"<b>{msg_static}</b> {invoice_number}"

        # Calculate next recurring date after generating invoice
        if self.date_start and self.template_id:
            self._calculate_recurring_next_date(self.recurring_next_date)
        self.message_post(body=Markup(message_body))

    def manual_invoice(self):
        invoice_id = self.create_invoice()
        # Calculate next recurring date after manual invoice
        if self.date_start and self.template_id:
            self._calculate_recurring_next_date(self.recurring_next_date)
        context = dict(self.env.context)
        context["form_view_initial_mode"] = "edit"
        return {
            "name": self.name,
            "views": [
                (self.env.ref("account.view_move_form").id, "form"),
                (self.env.ref("account.view_move_tree").id, "list"),
            ],
            "view_type": "form",
            "view_mode": "form",
            "res_model": "account.move",
            "res_id": invoice_id.id,
            "type": "ir.actions.act_window",
            "context": context,
        }

    @api.depends("invoice_ids", "sale_order_ids.invoice_ids")
    def _compute_account_invoice_ids_count(self):
        for record in self:
            record.account_invoice_ids_count = len(record.invoice_ids) + len(
                record.sale_order_ids.invoice_ids
            )

    def action_view_account_invoice_ids(self):
        return {
            "name": self.name,
            "views": [
                (self.env.ref("account.view_move_tree").id, "list"),
                (self.env.ref("account.view_move_form").id, "form"),
            ],
            "view_type": "form",
            "view_mode": "list,form",
            "res_model": "account.move",
            "type": "ir.actions.act_window",
            "domain": [
                ("id", "in", self.invoice_ids.ids + self.sale_order_ids.invoice_ids.ids)
            ],
            "context": self.env.context,
        }

    def _compute_sale_order_ids_count(self):
        data = self.env["sale.order"].read_group(
            domain=[("order_subscription_id", "in", self.ids)],
            fields=["order_subscription_id"],
            groupby=["order_subscription_id"],
        )
        count_dict = {
            item["order_subscription_id"][0]: item["order_subscription_id_count"]
            for item in data
        }
        for record in self:
            record.sale_order_ids_count = count_dict.get(record.id, 0)

    def action_view_sale_order_ids(self):
        active_ids = self.sale_order_ids.ids
        return {
            "name": self.name,
            "view_type": "form",
            "view_mode": "list,form",
            "res_model": "sale.order",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", active_ids)],
            "context": self.env.context,
        }

    def _ensure_date_object(self, date_value):
        """Helper method to ensure a value is a date object"""
        if not date_value:
            return None
        if isinstance(date_value, date):
            return date_value
        if isinstance(date_value, datetime):
            return date_value.date()
        if isinstance(date_value, str):
            try:
                return fields.Date.to_date(date_value)
            except Exception:
                return None
        return None

    def _check_dates(self, start, next_invoice):
        """Check if start date is after next invoice date"""
        start_date = self._ensure_date_object(start)
        next_date = self._ensure_date_object(next_invoice)
        if start_date and next_date:
            if start_date > next_date:
                return True
        return False

    def write(self, values):
        # Handle date_start changes
        if "date_start" in values:
            date_start = values["date_start"]
            if date_start and self.template_id:
                # Ensure date_start is a date object
                if isinstance(date_start, str):
                    date_start = fields.Date.to_date(date_start)
                if date_start:
                    # Recalculate recurring_next_date based on new date_start
                    type_interval = self.template_id.recurring_rule_type
                    interval = int(self.template_id.recurring_interval)
                    values["recurring_next_date"] = date_start + relativedelta(
                        **{type_interval: interval}
                    )
                    # Also recalculate date (finish date) if limited
                    if self.template_id.recurring_rule_boundary != "unlimited":
                        values["date"] = date_start + relativedelta(
                            months=+self.template_id.recurring_rule_count
                        )

        res = super().write(values)

        # Handle stage changes
        if "stage_id" in values:
            for record in self:
                if record.stage_id:
                    if record.stage_id.type == "in_progress":
                        record.in_progress = True
                        if not record.date_start:
                            record.date_start = date.today()
                        # Calculate recurring_next_date from date_start
                        if record.date_start and record.template_id:
                            record._calculate_recurring_next_date(record.date_start)
                    elif record.stage_id.type == "post":
                        record.close_reason_id = values.get("close_reason_id", False)
                        record.in_progress = False
                    else:
                        record.in_progress = False

        return res

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            # Auto-set salesperson from partner's user_id if not provided
            if "salesperson_id" not in values and "partner_id" in values:
                partner = self.env['res.partner'].browse(values["partner_id"])
                if partner and partner.user_id:
                    values["salesperson_id"] = partner.user_id.id
                else:
                    values["salesperson_id"] = self.env.user.id

            # Set crm_team_id from salesperson if not provided
            if "crm_team_id" not in values and "salesperson_id" in values:
                salesperson = self.env['res.users'].browse(values["salesperson_id"])
                if salesperson:
                    team = self.env['crm.team'].search([
                        ('user_id', '=', salesperson.id)
                    ], limit=1)
                    if team:
                        values["crm_team_id"] = team.id
                    elif salesperson.sale_team_id:
                        values["crm_team_id"] = salesperson.sale_team_id.id

            # Handle date_start and recurring_next_date
            if "date_start" in values and "template_id" in values:
                date_start = values["date_start"]
                if isinstance(date_start, str):
                    date_start = fields.Date.to_date(date_start)
                if date_start:
                    template = self.env["sale.subscription.template"].browse(values["template_id"])
                    if template:
                        type_interval = template.recurring_rule_type
                        interval = int(template.recurring_interval)
                        values["recurring_next_date"] = date_start + relativedelta(
                            **{type_interval: interval}
                        )
                        # Calculate finish date if limited
                        if template.recurring_rule_boundary != "unlimited":
                            values["date"] = date_start + relativedelta(
                                months=+template.recurring_rule_count
                            )

            # Check and adjust dates if needed
            if "date_start" in values and "recurring_next_date" in values:
                if self._check_dates(values["date_start"], values["recurring_next_date"]):
                    values["date_start"] = values["recurring_next_date"]

            # Set default stage
            if "stage_id" not in values:
                values["stage_id"] = (
                    self.env["sale.subscription.stage"]
                    .search([("type", "=", "draft")], order="sequence desc", limit=1)
                    .id
                )
        return super().create(vals_list)