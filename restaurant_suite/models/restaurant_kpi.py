from odoo import api, models


class RestaurantKPI(models.Model):
    _name = 'restaurant.kpi'
    _description = 'Restaurant KPI Engine'
    _auto = False
    _transient = True
    _log_access = True

    @api.model
    def get_dashboard_data(self, date_from, date_to, company_id=None):
        company_filter = 'AND company_id = %s' if company_id else ''
        params = [date_from, date_to] + ([company_id] if company_id else [])

        self.env.cr.execute(
            f"""
            SELECT COALESCE(SUM(amount_total),0), COALESCE(SUM(covers),0), COUNT(id)
            FROM pos_order
            WHERE state IN ('paid','done','invoiced')
              AND date_order::date >= %s AND date_order::date <= %s {company_filter}
            """,
            params,
        )
        revenue, covers, orders = self.env.cr.fetchone()
        revenue = float(revenue or 0)
        covers = int(covers or 0)
        orders = int(orders or 0)

        food_cost = self._compute_total_food_cost(date_from, date_to, company_id)
        waste_value = self._compute_waste_value(date_from, date_to, company_id)

        return {
            'revenue': round(revenue, 2),
            'covers': covers,
            'orders': orders,
            'revenue_per_cover': round(revenue / covers, 2) if covers else 0,
            'food_cost': round(food_cost, 2),
            'food_cost_pct': round(food_cost / revenue * 100, 1) if revenue else 0,
            'waste_value': round(waste_value, 2),
            'top_items': self._get_top_items(date_from, date_to, company_id),
            'hourly_revenue': self._get_hourly_curve(date_from, date_to, company_id),
            'daily_revenue': self._get_daily_revenue(date_from, date_to, company_id),
        }

    def _compute_total_food_cost(self, date_from, date_to, company_id=None):
        company_filter = 'AND po.company_id = %s' if company_id else ''
        params = [date_from, date_to] + ([company_id] if company_id else [])

        self.env.cr.execute(
            f"""
            SELECT COALESCE(SUM(
                pol.qty * mbl.product_qty / NULLIF(mbl.yield_ratio, 0) * ing_tmpl.standard_price
            ), 0)
            FROM pos_order_line pol
            JOIN pos_order po ON po.id = pol.order_id
            JOIN product_product sold_pp ON sold_pp.id = pol.product_id
            JOIN mrp_bom mb ON mb.product_tmpl_id = sold_pp.product_tmpl_id
                           AND mb.type = 'phantom' AND mb.active = true
            JOIN mrp_bom_line mbl ON mbl.bom_id = mb.id
            JOIN product_product ing_pp ON ing_pp.id = mbl.product_id
            JOIN product_template ing_tmpl ON ing_tmpl.id = ing_pp.product_tmpl_id
            WHERE po.state IN ('paid','done','invoiced')
              AND po.date_order::date >= %s AND po.date_order::date <= %s {company_filter}
            """,
            params,
        )
        return float(self.env.cr.fetchone()[0] or 0)

    def _compute_waste_value(self, date_from, date_to, company_id=None):
        company_filter = 'AND ss.company_id = %s' if company_id else ''
        params = [date_from, date_to] + ([company_id] if company_id else [])

        self.env.cr.execute(
            f"""
            SELECT COALESCE(SUM(ss.scrap_qty * pt.standard_price), 0)
            FROM stock_scrap ss
            JOIN product_product pp ON pp.id = ss.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE ss.state = 'done'
              AND ss.date_done::date >= %s AND ss.date_done::date <= %s {company_filter}
            """,
            params,
        )
        return float(self.env.cr.fetchone()[0] or 0)

    def _get_top_items(self, date_from, date_to, company_id=None, limit=10):
        company_filter = 'AND po.company_id = %s' if company_id else ''
        params = [date_from, date_to] + ([company_id] if company_id else []) + [limit]

        self.env.cr.execute(
            f"""
            SELECT
                COALESCE(pt.name->>'en_US', pt.name->>'fr_FR', pt.default_code, 'Product') AS name,
                SUM(pol.qty) AS qty,
                SUM(pol.price_subtotal) AS revenue,
                AVG(pol.price_unit) AS avg_price,
                AVG(pt.standard_price) AS std_cost
            FROM pos_order_line pol
            JOIN pos_order po ON po.id = pol.order_id
            JOIN product_product pp ON pp.id = pol.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE po.state IN ('paid','done','invoiced')
              AND po.date_order::date >= %s AND po.date_order::date <= %s {company_filter}
            GROUP BY pt.id
            ORDER BY SUM(pol.price_subtotal) DESC
            LIMIT %s
            """,
            params,
        )

        rows = self.env.cr.fetchall()
        return [
            {
                'name': row[0],
                'qty': round(float(row[1] or 0), 1),
                'revenue': round(float(row[2] or 0), 2),
                'avg_price': round(float(row[3] or 0), 2),
                'std_cost': round(float(row[4] or 0), 2),
                'margin': round(float(row[3] or 0) - float(row[4] or 0), 2),
            }
            for row in rows
        ]

    def _get_hourly_curve(self, date_from, date_to, company_id=None):
        company_filter = 'AND company_id = %s' if company_id else ''
        params = [date_from, date_to] + ([company_id] if company_id else [])

        self.env.cr.execute(
            f"""
            SELECT EXTRACT(HOUR FROM date_order AT TIME ZONE 'Europe/Paris')::int AS hour,
                   COALESCE(SUM(amount_total), 0) AS revenue
            FROM pos_order
            WHERE state IN ('paid','done','invoiced')
              AND date_order::date >= %s AND date_order::date <= %s {company_filter}
            GROUP BY 1 ORDER BY 1
            """,
            params,
        )
        return [{'hour': row[0], 'revenue': round(float(row[1]), 2)} for row in self.env.cr.fetchall()]

    def _get_daily_revenue(self, date_from, date_to, company_id=None):
        company_filter = 'AND company_id = %s' if company_id else ''
        params = [date_from, date_to] + ([company_id] if company_id else [])

        self.env.cr.execute(
            f"""
            SELECT date_order::date AS day, COALESCE(SUM(amount_total), 0) AS revenue
            FROM pos_order
            WHERE state IN ('paid','done','invoiced')
              AND date_order::date >= %s AND date_order::date <= %s {company_filter}
            GROUP BY 1 ORDER BY 1
            """,
            params,
        )
        return [{'date': str(row[0]), 'revenue': round(float(row[1]), 2)} for row in self.env.cr.fetchall()]
