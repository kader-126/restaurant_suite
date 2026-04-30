from odoo import api, fields, models


class RestaurantRecipe(models.Model):
    _name = 'restaurant.recipe'
    _description = 'Dish Recipe with Food Cost'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(related='product_id.name', store=True, readonly=False)
    product_id = fields.Many2one(
        'product.template',
        required=True,
        ondelete='cascade',
        domain=[('available_in_pos', '=', True)],
    )
    bom_id = fields.Many2one(
        'mrp.bom',
        string='Bill of Materials',
        domain="[('product_tmpl_id', '=', product_id), ('type', '=', 'phantom')]",
    )
    allergen_ids = fields.Many2many(
        'restaurant.allergen',
        string='Allergens (Recipe Level)',
        relation='recipe_allergen_rel',
        column1='recipe_id',
        column2='allergen_id',
        help='Allergens present in this recipe. Separate from per-product POS allergen tags.',
    )
    preparation_time = fields.Integer(string='Prep Time (min)', default=15)
    cooking_time = fields.Integer(string='Cooking Time (min)', default=20)
    method = fields.Html(string='Method / Plating Notes', translate=True, sanitize=False)
    image = fields.Image(string='Recipe Photo')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    selling_price = fields.Float(related='product_id.list_price', readonly=True)
    bom_cost = fields.Float(compute='_compute_bom_cost', store=True, digits='Product Price')
    food_cost_pct = fields.Float(compute='_compute_bom_cost', store=True, digits=(5, 2))
    margin = fields.Float(compute='_compute_bom_cost', store=True, digits='Product Price')
    margin_pct = fields.Float(compute='_compute_bom_cost', store=True, digits=(5, 2))

    @api.depends(
        'bom_id',
        'bom_id.bom_line_ids',
        'bom_id.bom_line_ids.product_id',
        'bom_id.bom_line_ids.product_qty',
        'bom_id.bom_line_ids.yield_ratio',
        'bom_id.bom_line_ids.product_id.standard_price',
        'product_id.list_price',
    )
    def _compute_bom_cost(self):
        for rec in self:
            cost = 0.0
            if rec.bom_id:
                for line in rec.bom_id.bom_line_ids:
                    ratio = max(line.yield_ratio, 0.01)
                    cost += line.product_id.standard_price * line.product_qty / ratio
            rec.bom_cost = cost
            price = rec.selling_price or 0.0
            rec.food_cost_pct = (cost / price * 100.0) if price else 0.0
            rec.margin = price - cost
            rec.margin_pct = ((price - cost) / price * 100.0) if price else 0.0

    def action_create_bom(self):
        self.ensure_one()
        if not self.bom_id:
            bom = self.env['mrp.bom'].create({
                'product_tmpl_id': self.product_id.id,
                'type': 'phantom',
                'company_id': self.company_id.id,
            })
            self.bom_id = bom
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.bom',
            'res_id': self.bom_id.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_print_recipe_card(self):
        return self.env.ref('restaurant_suite.action_recipe_card_report').report_action(self)

    def action_print_food_cost(self):
        return self.env.ref('restaurant_suite.action_food_cost_report').report_action(self)
